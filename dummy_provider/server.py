"""
Standalone Dummy Communication Service.
Independent microservice running separately from the main application.
Allows the platform to:
- Send messages
- Return a message / reference ID
- Provide message status updates (polling and webhook simulation)
- Simulate successful messages
- Simulate failed messages (invalid number, recipient rejected)
- Simulate temporary provider failures (503 Service Unavailable / Gateway Timeout)
- Configurable failure simulation modes and delivery latency
"""

import json
import uuid
import time
import random
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# In-memory store for message records
# message_id -> { id, recipient, content, channel, status, created_at, error, ... }
MESSAGES_DB = {}

# Simulation configuration
SIM_CONFIG = {
    "mode": "normal",  # 'normal' | 'always_fail' | 'temporary_failure' | 'random_fail'
    "temporary_failure_count": 0,
    "temporary_failure_threshold": 2, # Fails N times then recovers
}


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
                "version": "1.0.0",
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

                # If status was 'sent', simulate advancement to 'delivered' or 'read' over time
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

            if not recipient or not content:
                self._send_json(400, {"error": "Missing 'recipient' or 'content' in payload"})
                return

            # Check for simulated temporary provider failure (e.g. gateway timeout or 503)
            sim_mode = payload.get("simulate_mode", SIM_CONFIG["mode"])
            if sim_mode == "temporary_failure" or "[temp_fail]" in content.lower():
                SIM_CONFIG["temporary_failure_count"] += 1
                if SIM_CONFIG["temporary_failure_count"] <= SIM_CONFIG["temporary_failure_threshold"]:
                    self._send_json(503, {
                        "error": "Temporary Provider Failure: Downstream telecom network unavailable. Retryable.",
                        "retry_after_seconds": 5,
                        "code": "DOWNSTREAM_TIMEOUT",
                    })
                    return
                else:
                    # Self-healed after threshold
                    SIM_CONFIG["temporary_failure_count"] = 0

            # Check for simulated permanent failure
            is_explicit_fail = (
                sim_mode == "always_fail"
                or "[fail]" in content.lower()
                or recipient.startswith("0000")
                or "fail" in recipient.lower()
            )

            msg_id = f"dummy_{channel}_{uuid.uuid4().hex[:12]}"
            created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

            if is_explicit_fail:
                record = {
                    "id": msg_id,
                    "recipient": recipient,
                    "content": content,
                    "channel": channel,
                    "status": "failed",
                    "error": "Recipient carrier rejected message: Inactive subscriber or invalid MSISDN.",
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

            # Successful dispatch: defaults to 'sent' or 'delivered'
            initial_status = "delivered" if channel == "whatsapp" else "sent"
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

        # 2. Simulation control endpoint: /simulate/configure
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
            SIM_CONFIG["temporary_failure_count"] = 0

            self._send_json(200, {
                "message": "Simulation configuration updated",
                "config": SIM_CONFIG,
            })
            return

        # 3. Reset store: /reset
        if parsed.path == "/reset":
            MESSAGES_DB.clear()
            SIM_CONFIG["temporary_failure_count"] = 0
            self._send_json(200, {"message": "Dummy provider storage cleared"})
            return

        self._send_json(404, {"error": "Not found"})

    def do_PATCH(self):
        # Update status directly (for tests or webhook simulation)
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
        # Concise logging
        print(f"[DummyProvider] {self.command} {self.path} - {args[1]}")


def run(port=9000):
    server_address = ("", port)
    httpd = HTTPServer(server_address, DummyCommunicationHandler)
    print(f"===========================================================")
    print(f" Independent Dummy Communication Provider running on port {port}")
    print(f" Endpoint: http://localhost:{port}/messages/send")
    print(f" Status:   http://localhost:{port}/messages/<id>/status")
    print(f" Health:   http://localhost:{port}/health")
    print(f"===========================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down dummy communication service.")
        httpd.server_close()


if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9000
    run(port)
