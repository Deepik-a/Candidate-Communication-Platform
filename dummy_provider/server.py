"""
Standalone Dummy Communication Service with Interactive Web Simulator.
Independent microservice running separately from the main application on port 9000.
Features:
- Interactive Web UI at http://localhost:9000/ for recruiters/developers
- View incoming messages dispatched from the platform in real-time
- "Mark as Read" (or "Read Message") action that fires webhooks to Candidate Communication Platform
- "Mark as Delivered" and "Simulate Outage" actions
- Progression simulation: Sent -> Delivered -> Read
- Duplicate webhook simulation for idempotency testing (Requirement #7)
- Outbound Webhook dispatch to Candidate Communication Platform (port 8000)
"""

import json
import uuid
import time
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

# In-memory store for messages
# message_id -> { id, recipient, content, channel, status, created_at, error, timestamp }
MESSAGES_DB = {}

import os

# Simulation configuration
SIM_CONFIG = {
    "mode": "normal",  # 'normal' | 'always_fail' | 'temporary_failure' | 'rate_limit' | 'delivery_failure'
    "temporary_failure_count": 0,
    "temporary_failure_threshold": 2,
    "rate_limit_active": False,
    "webhook_url": os.environ.get("WEBHOOK_URL", os.environ.get("BACKEND_WEBHOOK_URL", "http://localhost:8000/api/v1/communications/webhook/")),
}

WEBHOOK_LOGS = []


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
    result = {}
    try:
        with urllib.request.urlopen(req, timeout=3) as response:
            resp_body = response.read().decode("utf-8")
            result = {"success": True, "code": response.status, "body": json.loads(resp_body)}
    except urllib.error.HTTPError as he:
        result = {"success": False, "code": he.code, "error": str(he)}
    except Exception as ex:
        result = {"success": False, "error": str(ex)}

    log_entry = {
        "timestamp": time.strftime("%H:%M:%S"),
        "payload": payload,
        "result": result,
    }
    WEBHOOK_LOGS.insert(0, log_entry)
    if len(WEBHOOK_LOGS) > 20:
        WEBHOOK_LOGS.pop()

    return result


HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Dummy Communication Provider Simulator</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'Inter', sans-serif; background-color: #f8fafc; color: #1e293b; padding: 24px; line-height: 1.5; }
    .container { max-width: 1000px; margin: 0 auto; }
    .header { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px 24px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; }
    .title h1 { font-size: 1.25rem; font-weight: 700; color: #0f172a; display: flex; align-items: center; gap: 8px; }
    .title p { font-size: 0.8125rem; color: #64748b; margin-top: 4px; }
    .status-badge { display: inline-flex; align-items: center; gap: 6px; background: #e8f5e9; color: #2e7d32; font-size: 0.75rem; font-weight: 600; padding: 4px 10px; border-radius: 16px; border: 1px solid #c8e6c9; }
    .status-dot { width: 8px; height: 8px; border-radius: 50%; background: #2e7d32; animation: pulse 2s infinite; }
    @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.4; } 100% { opacity: 1; } }

    .btn { display: inline-flex; align-items: center; gap: 6px; padding: 8px 14px; border-radius: 6px; font-size: 0.8125rem; font-weight: 600; cursor: pointer; border: none; transition: all 0.15s ease; text-decoration: none; }
    .btn-primary { background: #1976d2; color: #ffffff; }
    .btn-primary:hover { background: #1565c0; }
    .btn-success { background: #2e7d32; color: #ffffff; }
    .btn-success:hover { background: #1b5e20; }
    .btn-outline { background: #ffffff; border: 1px solid #cbd5e1; color: #475569; }
    .btn-outline:hover { background: #f1f5f9; border-color: #94a3b8; }
    .btn-sm { padding: 4px 10px; font-size: 0.75rem; }

    .card { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px 24px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
    .card-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; pb: 12px; border-bottom: 1px solid #f1f5f9; }
    .card-title { font-size: 1rem; font-weight: 700; color: #0f172a; }

    .messages-list { display: flex; flex-direction: column; gap: 12px; }
    .message-item { border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; background: #ffffff; display: flex; flex-direction: column; gap: 10px; transition: border-color 0.2s; }
    .message-item:hover { border-color: #93c5fd; }
    .message-item.status-read { border-left: 4px solid #2e7d32; }
    .message-item.status-delivered { border-left: 4px solid #0284c7; }
    .message-item.status-sent { border-left: 4px solid #f59e0b; }
    .message-item.status-failed { border-left: 4px solid #d32f2f; }

    .msg-top { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px; }
    .msg-recipient { font-weight: 600; font-size: 0.875rem; color: #111827; }
    .msg-ref { font-size: 0.75rem; color: #64748b; font-family: monospace; background: #f1f5f9; padding: 2px 6px; border-radius: 4px; }
    .msg-channel { font-size: 0.72rem; font-weight: 600; text-transform: uppercase; padding: 2px 8px; border-radius: 12px; background: #e0f2fe; color: #0284c7; }
    .msg-body { font-size: 0.875rem; color: #334155; line-height: 1.5; background: #f8fafc; padding: 10px 12px; border-radius: 6px; }
    .msg-actions { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px; pt: 4px; }
    .msg-time { font-size: 0.75rem; color: #94a3b8; }
    .msg-btn-group { display: flex; gap: 8px; }

    .pill { display: inline-flex; align-items: center; gap: 4px; padding: 2px 8px; border-radius: 12px; font-size: 0.72rem; font-weight: 600; }
    .pill-read { background: #e8f5e9; color: #2e7d32; border: 1px solid #c8e6c9; }
    .pill-delivered { background: #e0f2fe; color: #0284c7; border: 1px solid #bae6fd; }
    .pill-sent { background: #e1f5fe; color: #0288d1; border: 1px solid #b3e5fc; }
    .pill-failed { background: #ffebee; color: #d32f2f; border: 1px solid #ffcdd2; }

    .empty-state { text-align: center; padding: 40px 20px; color: #64748b; }
    .empty-state p { font-size: 0.875rem; margin-top: 8px; }

    .log-box { max-height: 180px; overflow-y: auto; background: #0f172a; color: #cbd5e1; border-radius: 6px; padding: 12px; font-family: monospace; font-size: 0.75rem; }
    .log-entry { margin-bottom: 6px; border-bottom: 1px solid #1e293b; padding-bottom: 4px; }
    .log-success { color: #4ade80; }
    .log-error { color: #f87171; }

    .toast { position: fixed; bottom: 20px; right: 20px; background: #2e7d32; color: #ffffff; padding: 10px 16px; border-radius: 6px; font-size: 0.8125rem; font-weight: 500; display: none; box-shadow: 0 4px 12px rgba(0,0,0,0.15); z-index: 1000; }
  </style>
</head>
<body>
  <div class="container">
    <!-- Header -->
    <div class="header">
      <div class="title">
        <h1>
          <span>📡 Dummy Communication Provider Simulator</span>
          <span class="status-badge"><span class="status-dot"></span> Port 9000 Online</span>
        </h1>
        <p>Candidate Handset & Telephony Receiver Simulation | Webhook: <code>http://localhost:8000/api/v1/communications/webhook/</code></p>
      </div>
      <div style="display: flex; gap: 8px;">
        <button class="btn btn-outline" onclick="fetchMessages()">↻ Refresh</button>
        <button class="btn btn-success" onclick="readAllMessages()">✓ Mark All as Read</button>
      </div>
    </div>

    <!-- Incoming Messages Card -->
    <div class="card">
      <div class="card-header">
        <div class="card-title">
          📥 Candidate Inbound Messages (<span id="msg-count">0</span>)
        </div>
        <div style="display: flex; align-items: center; gap: 12px; font-size: 0.8125rem; color: #64748b;">
          <label style="display: flex; align-items: center; gap: 6px; cursor: pointer;">
            <input type="checkbox" id="auto-refresh" checked> Auto-refresh (every 2s)
          </label>
        </div>
      </div>

      <div id="messages-container" class="messages-list">
        <div class="empty-state">
          <h3>No messages received yet</h3>
          <p>Send a message from the Candidate Communication Platform dashboard (e.g. to Krishna Khandelwal), and it will immediately appear here!</p>
        </div>
      </div>
    </div>

    <!-- Manual Webhook Dispatcher -->
    <div class="card">
      <div class="card-header">
        <div class="card-title">⚡ Instant Webhook Trigger</div>
      </div>
      <p style="font-size: 0.8125rem; color: #64748b; margin-bottom: 12px;">
        Quickly send a webhook event to the platform for any candidate or message ID to advance its status to <strong>READ</strong>:
      </p>
      <div style="display: flex; gap: 8px; flex-wrap: wrap;">
        <input type="text" id="manual-ref" placeholder="Message Reference ID (e.g. sent_12345 or MSG-1)" style="flex: 1; min-width: 200px; padding: 8px 12px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 0.8125rem;">
        <button class="btn btn-primary" onclick="triggerManualWebhook('read')">Mark Candidate as READ (✓ read)</button>
        <button class="btn btn-outline" onclick="triggerManualWebhook('delivered')">Mark as DELIVERED</button>
      </div>
    </div>

    <!-- Recent Webhook Dispatches -->
    <div class="card">
      <div class="card-header">
        <div class="card-title">📜 Webhook Dispatch Activity</div>
        <button class="btn btn-outline btn-sm" onclick="clearLogs()">Clear</button>
      </div>
      <div id="webhook-logs" class="log-box">
        <div style="color: #64748b;">No webhooks dispatched in this session yet.</div>
      </div>
    </div>
  </div>

  <div id="toast" class="toast">Status updated and webhook dispatched!</div>

  <script>
    let autoRefreshInterval = null;

    function showToast(msg) {
      const toast = document.getElementById('toast');
      toast.textContent = msg;
      toast.style.display = 'block';
      setTimeout(() => { toast.style.display = 'none'; }, 3000);
    }

    async function fetchMessages() {
      try {
        const res = await fetch('/api/messages');
        const data = await res.json();
        document.getElementById('msg-count').textContent = data.count || 0;
        renderMessages(data.messages || []);
        renderLogs(data.logs || []);
      } catch (e) {
        console.error('Failed to fetch messages', e);
      }
    }

    function renderMessages(messages) {
      const container = document.getElementById('messages-container');
      if (!messages || messages.length === 0) {
        container.innerHTML = `
          <div class="empty-state">
            <h3>No messages received yet</h3>
            <p>Send a message from the Candidate Communication Platform (e.g. to Krishna Khandelwal), and it will appear here in real-time!</p>
          </div>
        `;
        return;
      }

      container.innerHTML = messages.map(msg => {
        const statusClass = 'status-' + (msg.status || 'sent').toLowerCase();
        let pillHtml = '';
        if (msg.status === 'read') {
          pillHtml = '<span class="pill pill-read">✓ read</span>';
        } else if (msg.status === 'delivered') {
          pillHtml = '<span class="pill pill-delivered">✓ Delivered</span>';
        } else if (msg.status === 'failed') {
          pillHtml = '<span class="pill pill-failed">✕ Failed</span>';
        } else {
          pillHtml = '<span class="pill pill-sent">Sent</span>';
        }

        const isRead = msg.status === 'read';

        return `
          <div class="message-item ${statusClass}">
            <div class="msg-top">
              <div style="display: flex; align-items: center; gap: 8px;">
                <span class="msg-recipient">📱 ${msg.recipient}</span>
                <span class="msg-channel">${msg.channel || 'SMS'}</span>
                <span class="msg-ref">${msg.id}</span>
              </div>
              <div>${pillHtml}</div>
            </div>
            <div class="msg-body">${msg.content}</div>
            <div class="msg-actions">
              <span class="msg-time">Received: ${msg.created_at || 'Just now'}</span>
              <div class="msg-btn-group">
                ${!isRead ? `
                  <button class="btn btn-outline btn-sm" onclick="advanceStatus('${msg.id}', 'delivered')">Mark Delivered</button>
                  <button class="btn btn-success btn-sm" onclick="advanceStatus('${msg.id}', 'read')">📖 Read Message (Mark as Read)</button>
                ` : `
                  <span style="font-size: 0.75rem; color: #2e7d32; font-weight: 600;">✓ Message Read by Candidate</span>
                `}
                <button class="btn btn-outline btn-sm" onclick="simulateDuplicate('${msg.id}')" title="Test Idempotency (Requirement #7)">Duplicate Callback</button>
              </div>
            </div>
          </div>
        `;
      }).join('');
    }

    function renderLogs(logs) {
      const container = document.getElementById('webhook-logs');
      if (!logs || logs.length === 0) return;
      container.innerHTML = logs.map(l => {
        const isOk = l.result && l.result.success;
        return `
          <div class="log-entry">
            <span style="color: #64748b;">[${l.timestamp}]</span>
            <span style="color: #38bdf8;">WEBHOOK POST</span> ->
            <code>${JSON.stringify(l.payload)}</code>
            <span class="${isOk ? 'log-success' : 'log-error'}">${isOk ? '✓ HTTP 200 OK' : '✕ FAIL'}</span>
          </div>
        `;
      }).join('');
    }

    async function advanceStatus(msgId, status) {
      try {
        const res = await fetch(`/api/messages/${msgId}/status`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ status })
        });
        const data = await res.json();
        showToast(`Message marked as ${status.toUpperCase()}! Webhook dispatched to platform.`);
        fetchMessages();
      } catch (e) {
        alert('Failed to update status: ' + e);
      }
    }

    async function readAllMessages() {
      try {
        const res = await fetch('/api/messages/read-all', { method: 'POST' });
        showToast('All messages marked as READ! Webhooks dispatched.');
        fetchMessages();
      } catch (e) {
        alert('Failed: ' + e);
      }
    }

    async function simulateDuplicate(msgId) {
      try {
        const res = await fetch(`/messages/${msgId}/simulate-duplicate-webhook`, { method: 'POST' });
        const data = await res.json();
        showToast('Duplicate callback sent! Verify backend handled idempotently.');
        fetchMessages();
      } catch (e) {
        alert('Failed: ' + e);
      }
    }

    async function triggerManualWebhook(status) {
      const ref = document.getElementById('manual-ref').value.trim();
      if (!ref) {
        alert('Please enter a Reference ID or Message ID (e.g. from the candidate history drawer).');
        return;
      }
      try {
        const res = await fetch('/api/webhook/manual', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ reference_id: ref, status: status })
        });
        const data = await res.json();
        showToast(`Webhook fired for ${ref} with status ${status.toUpperCase()}!`);
        fetchMessages();
      } catch (e) {
        alert('Error: ' + e);
      }
    }

    function clearLogs() {
      document.getElementById('webhook-logs').innerHTML = '<div style="color: #64748b;">Logs cleared.</div>';
    }

    // Auto-refresh control
    document.getElementById('auto-refresh').addEventListener('change', (e) => {
      if (e.target.checked) {
        startAutoRefresh();
      } else {
        clearInterval(autoRefreshInterval);
      }
    });

    function startAutoRefresh() {
      clearInterval(autoRefreshInterval);
      autoRefreshInterval = setInterval(fetchMessages, 2000);
    }

    fetchMessages();
    startAutoRefresh();
  </script>
</body>
</html>
"""


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

    def _send_html(self, status_code: int, html_str: str):
        body = html_str.encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
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

        # 1. Web UI: Root path for browsers
        if parsed.path in ("/", "/ui", "/inbox") or self.headers.get("Accept", "").find("text/html") != -1:
            self._send_html(200, HTML_PAGE)
            return

        # 2. API: Messages list & logs
        if parsed.path in ("/api/messages", "/messages"):
            msg_list = sorted(list(MESSAGES_DB.values()), key=lambda x: x.get("timestamp", 0), reverse=True)
            self._send_json(200, {
                "count": len(MESSAGES_DB),
                "messages": msg_list,
                "logs": WEBHOOK_LOGS[:10],
            })
            return

        # 3. Healthcheck
        if parsed.path == "/health":
            statuses = [m.get("status") for m in MESSAGES_DB.values()]
            self._send_json(200, {
                "service": "Dummy Independent Communication Provider",
                "status": "healthy" if SIM_CONFIG.get("mode") == "normal" else "degraded",
                "version": "2.0.0",
                "stored_messages": len(MESSAGES_DB),
                "messages_sent": sum(1 for s in statuses if s in ("sent", "delivered", "read")),
                "messages_delivered": sum(1 for s in statuses if s in ("delivered", "read")),
                "messages_failed": sum(1 for s in statuses if s == "failed"),
                "simulation_config": SIM_CONFIG,
            })
            return

        # 4. Message status lookup by ID
        if parsed.path.startswith("/messages/"):
            parts = [p for p in parsed.path.split("/") if p]
            if len(parts) >= 2:
                msg_id = parts[1]
                msg = MESSAGES_DB.get(msg_id)
                if not msg:
                    self._send_json(404, {"error": "Message not found", "reference_id": msg_id})
                    return

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
        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length) if content_length > 0 else b"{}"
        try:
            payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}
        except Exception:
            payload = {}

        # 1. Send Message Endpoint: /messages/send
        if parsed.path == "/messages/send":
            recipient = payload.get("recipient", "").strip()
            content = payload.get("content", "").strip()
            channel = payload.get("channel", "sms").lower()
            sim_mode = payload.get("simulate_mode", SIM_CONFIG["mode"])

            # A. Rate limit simulation
            if sim_mode == "rate_limit" or "[rate_limit]" in content.lower():
                self._send_json(429, {
                    "error": "Rate limit exceeded: Provider dispatch throttle limit reached.",
                    "code": "TOO_MANY_REQUESTS",
                    "retry_after_seconds": 10,
                })
                return

            # B. Temporary provider failure
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

            # C. Invalid recipient / explicit fail
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

            msg_id = f"sent_{uuid.uuid4().hex[:8]}"
            created_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

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
                    "provider": "dummy-service",
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
                    "provider": "dummy-service",
                    "error": record["error"],
                    "created_at": created_at,
                })
                return

            # Successful dispatch with initial status "sent"
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
                "provider": "dummy-service",
                "created_at": created_at,
                "message": "Message successfully accepted by dummy provider for transmission.",
            })
            return

        # 2. Update status and dispatch webhook: /api/messages/<id>/status
        if parsed.path.startswith("/api/messages/") and parsed.path.endswith("/status"):
            parts = [p for p in parsed.path.split("/") if p]
            msg_id = parts[2]
            new_status = payload.get("status", "read")
            msg = MESSAGES_DB.get(msg_id)
            if msg:
                msg["status"] = new_status

            # Fire webhook to platform
            wh_res = dispatch_webhook_to_backend({
                "reference_id": msg_id,
                "status": new_status,
            })

            self._send_json(200, {
                "success": True,
                "message_id": msg_id,
                "status": new_status,
                "webhook": wh_res,
            })
            return

        # 3. Read All Messages: /api/messages/read-all
        if parsed.path == "/api/messages/read-all":
            updated_count = 0
            for msg_id, msg in MESSAGES_DB.items():
                if msg["status"] != "read":
                    msg["status"] = "read"
                    dispatch_webhook_to_backend({
                        "reference_id": msg_id,
                        "status": "read",
                    })
                    updated_count += 1
            self._send_json(200, {"success": True, "updated": updated_count})
            return

        # 4. Manual Webhook Trigger: /api/webhook/manual
        if parsed.path == "/api/webhook/manual":
            ref = payload.get("reference_id", "").strip()
            new_status = payload.get("status", "read")
            if ref in MESSAGES_DB:
                MESSAGES_DB[ref]["status"] = new_status

            wh_res = dispatch_webhook_to_backend({
                "reference_id": ref,
                "status": new_status,
            })
            self._send_json(200, {"success": True, "webhook": wh_res})
            return

        # 5. Duplicate Webhook simulation
        if parsed.path.startswith("/messages/") and parsed.path.endswith("/simulate-duplicate-webhook"):
            parts = [p for p in parsed.path.split("/") if p]
            msg_id = parts[1]
            status_to_send = MESSAGES_DB.get(msg_id, {}).get("status", "read")
            payload_wh = {"reference_id": msg_id, "status": status_to_send}
            first = dispatch_webhook_to_backend(payload_wh)
            second = dispatch_webhook_to_backend(payload_wh)
            self._send_json(200, {"success": True, "first": first, "second": second})
            return

        self._send_json(404, {"error": "Not found"})

    def log_message(self, format, *args):
        # Silence routine access logs
        pass


def run(port=9000):
    server_address = ("", port)
    httpd = HTTPServer(server_address, DummyCommunicationHandler)
    print("===========================================================")
    print(f" Dummy Communication Provider Simulator running on port {port}")
    print(f" Open Web UI at: http://localhost:{port}/")
    print(f" Webhook Target: {SIM_CONFIG['webhook_url']}")
    print("===========================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down dummy communication service.")
        httpd.server_close()


if __name__ == "__main__":
    import sys
    port = int(os.environ.get("PORT", sys.argv[1] if len(sys.argv) > 1 else 9000))
    run(port)
