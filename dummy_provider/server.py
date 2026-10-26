"""
Standalone Dummy Communication Service.
Independent microservice running separately from the main application on port 9000.
Features:
- Send messages and return a unique provider reference ID
- Simulate message progression: Sent -> Delivered -> Read
- Outbound Webhook dispatch to Candidate Communication Platform
- Duplicate webhook simulation for idempotency testing (Requirement #7)
- Simulation modes for failures (Requirement #8):
  * Invalid recipient
  * Temporary provider failure (503 Service Unavailable / Gateway Timeout)
  * Rate limiting (429 Too Many Requests)
  * Message delivery failure (Carrier rejected, inactive subscriber)
  * Communication service unavailable
"""

import json
import uuid
import time
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

# In-memory store for messages
# message_id -> { id, recipient, content, channel, status, created_at, error, ... }
MESSAGES_DB = {}

# Simulation configuration
SIM_CONFIG = {
    "mode": "normal",  # 'normal' | 'always_fail' | 'temporary_failure' | 'rate_limit' | 'delivery_failure'
    "temporary_failure_count": 0,
    "temporary_failure_threshold": 2,
    "rate_limit_active": False,
    "webhook_url": "http://localhost:8000/api/v1/communications/webhook/",
}


def dispatch_webhook_to_backend(payload: dict) -> dict:
    """Dispatches a status update webhook directly to the backend platform."""
    url = SIM_CONFIG.get("webhook_url", "http://localhost:8000/api/v1/communications/webhook/")
    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data_bytes,
        headers={"Content-Type": "application/json", "User-Agent": "DummyProvider-WebhookDispatcher/1.0"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=3) as response:
            resp_body = response.read().decode("utf-8")
            return {"success": True, "code": response.status, "body": json.loads(resp_body)}
    except urllib.error.HTTPError as he:
        return {"success": False, "code": he.code, "error": str(he)}
    except Exception as ex:
        return {"success": False, "error": str(ex)}


class DummyCommunicationHandler(BaseHTTPRequestHandler):
    def _send_json(self, status_code: int, data: dict):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)

        # Healthcheck
        if parsed.path == "/health" or parsed.path == "/":
            self._send_json(200, {
                "service": "Dummy Independent Communication Provider",
                "status": "healthy",
                "version": "2.0.0",
                "stored_messages": len(MESSAGES_DB),
                "simulation_config": SIM_CONFIG,
            })
            return

        # List all messages
        if parsed.path == "/messages":
            self._send_json(200, {
                "count": len(MESSAGES_DB),
                "messages": list(MESSAGES_DB.values()),
            })
            return

        # Get message status by ID: /messages/<msg_id>/status or /messages/<msg_id>
        if parsed.path.startswith("/messages/"):
            parts = [p for p in parsed.path.split("/") if p]
            if len(parts) >= 2:
                msg_id = parts[1]
                msg = MESSAGES_DB.get(msg_id)
                if not msg:
                    self._send_json(404, {"error": "Message not found", "reference_id": msg_id})
                    return

                # Simulate automatic advancement over time: sent -> delivered -> read
                elapsed = time.time() - msg.get("timestamp", 0)
                if msg["status"] == "sent" and elapsed > 3:
                    msg["status"] = "delivered"
                if msg["status"] == "delivered" and elapsed > 6:
                    msg["status"] = "read"

                self._send_json(200, {
                    "reference_id": msg["id"],
                    "recipient": msg["recipient"],
                    "status": msg["status"],
                    "channel": msg["channel"],
                    "created_at": msg["created_at"],
                    "error": msg.get("error"),
                })
                return

        self._send_json(404, {"error": "Not found"})

    def do_POST(self):
        parsed = urlparse(self.path)

        # 1. Send Message Endpoint: /messages/send
        if parsed.path == "/messages/send":
            content_length = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(content_length)
            try:
                payload = json.loads(raw_body.decode("utf-8"))
            except Exception:
                self._send_json(400, {"error": "Invalid JSON body"})
                return

            recipient = payload.get("recipient", "").strip()
            content = payload.get("content", "").strip()
            channel = payload.get("channel", "sms").lower()
            sim_mode = payload.get("simulate_mode", SIM_CONFIG["mode"])

            # A. Check for rate limit simulation
            if sim_mode == "rate_limit" or "[rate_limit]" in content.lower():
                self._send_json(429, {
                    "error": "Rate limit exceeded: Provider dispatch throttle limit reached.",
                    "code": "TOO_MANY_REQUESTS",
                    "retry_after_seconds": 10,
                })
                return

            # B. Check for temporary provider failure (503 Service Unavailable)
            if sim_mode == "temporary_failure" or "[temp_fail]" in content.lower():
                SIM_CONFIG["temporary_failure_count"] += 1
                if SIM_CONFIG["temporary_failure_count"] <= SIM_CONFIG["temporary_failure_threshold"]:
                    self._send_json(503, {
                        "error": "Temporary Provider Failure: Downstream telecom network unavailable. Retryable.",
                        "code": "DOWNSTREAM_TIMEOUT",
                        "retry_after_seconds": 5,
                    })
                    return
                else:
                    SIM_CONFIG["temporary_failure_count"] = 0

            # C. Check for invalid recipient or explicit fail
            is_invalid_recipient = (
                not recipient
                or recipient.startswith("0000")
                or "fail_number" in recipient.lower()
                or "[invalid]" in content.lower()
            )
            is_delivery_failure = (
                sim_mode in ("delivery_failure", "always_fail")
                or "[fail]" in content.lower()
                or "fail" in recipient.lower()
            )

            msg_id = f"dummy_{channel}_{uuid.uuid4().hex[:12]}"
            created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

            if is_invalid_recipient:
                record = {
                    "id": msg_id,
                    "recipient": recipient,
                    "content": content,
                    "channel": channel,
                    "status": "failed",
                    "error": "Invalid recipient MSISDN: Unallocated number or destination not reachable.",
                    "created_at": created_at,
                    "timestamp": time.time(),
                }
                MESSAGES_DB[msg_id] = record
                self._send_json(200, {
                    "success": False,
                    "reference_id": msg_id,
                    "status": "failed",
                    "provider": "dummy-independent-service",
                    "error": record["error"],
                    "created_at": created_at,
                })
                return

            if is_delivery_failure:
                record = {
                    "id": msg_id,
                    "recipient": recipient,
                    "content": content,
                    "channel": channel,
                    "status": "failed",
                    "error": "Carrier delivery failure: Recipient handset unreachable or subscriber deactivated.",
                    "created_at": created_at,
                    "timestamp": time.time(),
                }
                MESSAGES_DB[msg_id] = record
                self._send_json(200, {
                    "success": False,
                    "reference_id": msg_id,
                    "status": "failed",
                    "provider": "dummy-independent-service",
                    "error": record["error"],
                    "created_at": created_at,
                })
                return

            # D. Successful initial dispatch
            initial_status = "sent"
            record = {
                "id": msg_id,
                "recipient": recipient,
                "content": content,
                "channel": channel,
                "status": initial_status,
                "error": None,
                "created_at": created_at,
                "timestamp": time.time(),
            }
            MESSAGES_DB[msg_id] = record

            self._send_json(201, {
                "success": True,
                "reference_id": msg_id,
                "status": initial_status,
                "provider": "dummy-independent-service",
                "created_at": created_at,
                "message": "Message successfully accepted by dummy provider for transmission.",
            })
            return

        # 2. Advance Status & Trigger Webhook: /messages/<id>/advance
        if parsed.path.startswith("/messages/") and parsed.path.endswith("/advance"):
            parts = [p for p in parsed.path.split("/") if p]
            msg_id = parts[1]
            msg = MESSAGES_DB.get(msg_id)
            if not msg:
                self._send_json(404, {"error": "Message not found in dummy provider"})
                return

            # Progression: sent -> delivered -> read
            progression = {"sent": "delivered", "delivered": "read", "read": "read"}
            current = msg.get("status", "sent")
            next_status = progression.get(current, "delivered")
            msg["status"] = next_status

            # Fire webhook callback to backend
            webhook_res = dispatch_webhook_to_backend({
                "reference_id": msg_id,
                "status": next_status,
            })

            self._send_json(200, {
                "message_id": msg_id,
                "previous_status": current,
                "current_status": next_status,
                "webhook_dispatched": webhook_res,
            })
            return

        # 3. Simulate Duplicate Webhook: /messages/<id>/simulate-duplicate-webhook
        if parsed.path.startswith("/messages/") and parsed.path.endswith("/simulate-duplicate-webhook"):
            parts = [p for p in parsed.path.split("/") if p]
            msg_id = parts[1]
            msg = MESSAGES_DB.get(msg_id)
            if not msg:
                self._send_json(404, {"error": "Message not found in dummy provider"})
                return

            status_to_send = msg.get("status", "delivered")
            payload = {"reference_id": msg_id, "status": status_to_send}
            
            # Send once
            first_call = dispatch_webhook_to_backend(payload)
            # Send immediately again (duplicate callback)
            second_call = dispatch_webhook_to_backend(payload)

            self._send_json(200, {
                "message_id": msg_id,
                "sent_status": status_to_send,
                "first_callback": first_call,
                "duplicate_callback": second_call,
                "idempotency_note": "Sent same status update twice to verify idempotent handling on backend.",
            })
            return

        # 4. Simulation Configuration: /simulate/configure
        if parsed.path == "/simulate/configure":
            content_length = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(content_length)
            try:
                payload = json.loads(raw_body.decode("utf-8"))
            except Exception:
                self._send_json(400, {"error": "Invalid JSON body"})
                return

            if "mode" in payload:
                SIM_CONFIG["mode"] = payload["mode"]
            if "temporary_failure_threshold" in payload:
                SIM_CONFIG["temporary_failure_threshold"] = int(payload["temporary_failure_threshold"])
            if "webhook_url" in payload:
                SIM_CONFIG["webhook_url"] = payload["webhook_url"]
            SIM_CONFIG["temporary_failure_count"] = 0

            self._send_json(200, {
                "message": "Simulation configuration updated",
                "config": SIM_CONFIG,
            })
            return

        # 5. Reset: /reset
        if parsed.path == "/reset":
            MESSAGES_DB.clear()
            SIM_CONFIG["temporary_failure_count"] = 0
            self._send_json(200, {"message": "Dummy provider storage cleared"})
            return

        self._send_json(404, {"error": "Not found"})

    def do_PATCH(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/messages/"):
            parts = [p for p in parsed.path.split("/") if p]
            if len(parts) >= 2:
                msg_id = parts[1]
                msg = MESSAGES_DB.get(msg_id)
                if not msg:
                    self._send_json(404, {"error": "Message not found"})
                    return
                content_length = int(self.headers.get("Content-Length", 0))
                raw_body = self.rfile.read(content_length)
                try:
                    payload = json.loads(raw_body.decode("utf-8"))
                except Exception:
                    self._send_json(400, {"error": "Invalid JSON"})
                    return
                if "status" in payload:
                    msg["status"] = payload["status"]
                self._send_json(200, {"reference_id": msg_id, "updated_status": msg["status"]})
                return
        self._send_json(404, {"error": "Not found"})

    def log_message(self, format, *args):
        print(f"[DummyProvider] {self.command} {self.path} - {args[1]}")


def run(port=9000):
    server_address = ("", port)
    httpd = HTTPServer(server_address, DummyCommunicationHandler)
    print("===========================================================")
    print(f" Independent Dummy Communication Provider running on port {port}")
    print(f" Webhook Target: {SIM_CONFIG['webhook_url']}")
    print("===========================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down dummy communication service.")
        httpd.server_close()


if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9000
    run(port)
