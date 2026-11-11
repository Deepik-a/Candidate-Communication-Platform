"""
Standalone Dummy Communication Service with Interactive Black-Screen Web Simulator.
Independent microservice running separately from the main application on port 9000.
Features:
- Secured with Secret Key authentication (Access restricted to authorized users)
- Automatic message status progression: Delivered after 5 seconds and Read after 10 seconds
- Sleek Black-Screen Cyber/Terminal UI
- Outbound Webhook dispatch to Candidate Communication Platform (port 8000)
- Duplicate webhook simulation for idempotency testing (Requirement #7)
"""

import os
import sys
import json
import uuid
import time
import threading
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# ── Load .env File if Present ──────────────────────────────────────────────────
def load_env_file():
    """Lightweight .env file loader (standard library only)."""
    candidates = [
        os.path.join(os.path.dirname(__file__), ".env"),
        os.path.join(os.path.dirname(__file__), "..", ".env"),
        os.path.join(os.path.dirname(__file__), "..", "backend", ".env"),
        os.path.join(os.getcwd(), ".env"),
        os.path.join(os.getcwd(), "backend", ".env"),
    ]
    for env_path in candidates:
        if os.path.isfile(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k, v = k.strip(), v.strip().strip("'\"")
                            if k not in os.environ:
                                os.environ[k] = v
            except Exception:
                pass

load_env_file()

# ── Secret Key Security Configuration ──────────────────────────────────────────
# Authorized users must type this secret key to unlock the Black-Screen UI
DUMMY_SECRET_KEY = (
    os.environ.get("DUMMY_PROVIDER_SECRET_KEY")
    or os.environ.get("DUMMY_SECRET_KEY")
    or "candidate-secret-key-2026"
)

# ── In-Memory Database ─────────────────────────────────────────────────────────
# message_id -> { id, recipient, content, channel, status, created_at, error, timestamp, delivered_at, read_at }
MESSAGES_DB = {}

def resolve_default_webhook_url():
    url = os.environ.get("WEBHOOK_URL") or os.environ.get("BACKEND_WEBHOOK_URL")
    if not url:
        backend_host = os.environ.get("BACKEND_URL")
        if backend_host:
            url = backend_host.rstrip("/") + "/api/v1/communications/webhook/"
    return url or "http://localhost:8000/api/v1/communications/webhook/"

# Simulation configuration
SIM_CONFIG = {
    "mode": "normal",  # 'normal' | 'always_fail' | 'temporary_failure' | 'rate_limit' | 'delivery_failure'
    "temporary_failure_count": 0,
    "temporary_failure_threshold": 2,
    "rate_limit_active": False,
    "webhook_url": resolve_default_webhook_url(),
    "auto_update_enabled": True,
}

WEBHOOK_LOGS = []


# ── Webhook Dispatcher ────────────────────────────────────────────────────────
def dispatch_webhook_to_backend(payload: dict) -> dict:
    """Dispatches a status update webhook directly to the backend platform."""
    url = SIM_CONFIG.get("webhook_url", "http://localhost:8000/api/v1/communications/webhook/")
    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data_bytes,
        headers={"Content-Type": "application/json", "User-Agent": "DummyProvider-WebhookDispatcher/2.0"},
        method="POST",
    )
    result = {}
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            resp_body = response.read().decode("utf-8")
            try:
                body_json = json.loads(resp_body)
            except Exception:
                body_json = {"raw": resp_body}

            backend_success = body_json.get("success") if isinstance(body_json, dict) else True
            result = {
                "success": (response.status == 200 and backend_success is not False),
                "code": response.status,
                "body": body_json,
                "error": body_json.get("detail") if (isinstance(body_json, dict) and backend_success is False) else None
            }
    except urllib.error.HTTPError as he:
        result = {"success": False, "code": he.code, "error": f"HTTP {he.code}: {he.reason}"}
    except Exception as ex:
        result = {"success": False, "error": f"Connection failed to {url}: {str(ex)}"}

    log_entry = {
        "timestamp": time.strftime("%H:%M:%S"),
        "payload": payload,
        "target_url": url,
        "result": result,
    }
    WEBHOOK_LOGS.insert(0, log_entry)
    if len(WEBHOOK_LOGS) > 30:
        WEBHOOK_LOGS.pop()

    return result


# ── Automatic Status Update Scheduler (5s Delivered, 10s Read) ────────────────
def schedule_automatic_status_updates(msg_id: str):
    """
    Schedules automatic transitions:
    - Delivered after 5 seconds
    - Read after 10 seconds (5 seconds after delivered)
    Fires real-time webhooks to the platform at each step.
    """
    if not SIM_CONFIG.get("auto_update_enabled", True):
        return

    def advance_to_delivered():
        msg = MESSAGES_DB.get(msg_id)
        if not msg:
            return
        if msg.get("status") == "sent":
            msg["status"] = "delivered"
            msg["delivered_at"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            print(f"[{time.strftime('%H:%M:%S')}] [AUTO-UPDATE] Message {msg_id} -> DELIVERED (5s). Firing webhook...")
            dispatch_webhook_to_backend({
                "reference_id": msg_id,
                "status": "delivered",
            })

    def advance_to_read():
        msg = MESSAGES_DB.get(msg_id)
        if not msg:
            return
        if msg.get("status") in ("sent", "delivered"):
            msg["status"] = "read"
            msg["read_at"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            print(f"[{time.strftime('%H:%M:%S')}] [AUTO-UPDATE] Message {msg_id} -> READ (10s). Firing webhook...")
            dispatch_webhook_to_backend({
                "reference_id": msg_id,
                "status": "read",
            })

    # Timer 1: 5.0 seconds -> Delivered
    t1 = threading.Timer(5.0, advance_to_delivered)
    t1.daemon = True
    t1.start()

    # Timer 2: 10.0 seconds -> Read
    t2 = threading.Timer(10.0, advance_to_read)
    t2.daemon = True
    t2.start()


# ── Authorization Verification ────────────────────────────────────────────────
def is_authorized(headers: dict, query_params: dict = None) -> bool:
    """Verifies that the request supplies the authorized secret key."""
    # 1. Check X-Secret-Key header
    secret_hdr = headers.get("X-Secret-Key")
    if secret_hdr and secret_hdr.strip() == DUMMY_SECRET_KEY:
        return True

    # 2. Check Authorization: Bearer <key>
    auth_hdr = headers.get("Authorization")
    if auth_hdr and auth_hdr.startswith("Bearer "):
        token = auth_hdr.split(" ", 1)[1].strip()
        if token == DUMMY_SECRET_KEY:
            return True

    # 3. Check Cookie: dummy_secret_key=<key>
    cookies = headers.get("Cookie", "")
    for c in cookies.split(";"):
        c = c.strip()
        if c.startswith("dummy_secret_key="):
            val = c.split("=", 1)[1].strip()
            if val == DUMMY_SECRET_KEY:
                return True

    # 4. Check Query Parameter: ?key=<key>
    if query_params and query_params.get("key", [""])[0] == DUMMY_SECRET_KEY:
        return True

    return False


# ── Black-Screen Web UI ────────────────────────────────────────────────────────
HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Dummy Provider Simulator | Black-Screen Console</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      background-color: #030712;
      color: #f3f4f6;
      min-height: 100vh;
      line-height: 1.5;
    }
    code, pre, .mono { font-family: 'JetBrains Mono', monospace; }

    /* ── AUTH LOCK SCREEN ── */
    #auth-screen {
      position: fixed;
      inset: 0;
      background: #030712;
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 9999;
      padding: 20px;
    }
    .auth-card {
      width: 100%;
      max-width: 460px;
      background: #0b0f19;
      border: 1px solid #1f293d;
      border-radius: 12px;
      padding: 32px 28px;
      box-shadow: 0 20px 50px rgba(0, 0, 0, 0.8), 0 0 40px rgba(16, 185, 129, 0.05);
      text-align: center;
    }
    .auth-icon {
      width: 56px;
      height: 56px;
      border-radius: 50%;
      background: rgba(16, 185, 129, 0.1);
      border: 1px solid rgba(16, 185, 129, 0.3);
      display: inline-flex;
      align-items: center;
      justify-content: center;
      font-size: 26px;
      margin-bottom: 16px;
    }
    .auth-title {
      font-size: 1.25rem;
      font-weight: 700;
      color: #f9fafb;
      letter-spacing: -0.01em;
    }
    .auth-subtitle {
      font-size: 0.8125rem;
      color: #9ca3af;
      margin-top: 6px;
      margin-bottom: 24px;
    }
    .auth-input-group {
      position: relative;
      margin-bottom: 16px;
      text-align: left;
    }
    .auth-label {
      display: block;
      font-size: 0.75rem;
      font-weight: 600;
      color: #9ca3af;
      margin-bottom: 6px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    .auth-input {
      width: 100%;
      background: #030712;
      border: 1px solid #374151;
      border-radius: 8px;
      padding: 12px 14px;
      color: #10b981;
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.95rem;
      outline: none;
      transition: all 0.2s ease;
    }
    .auth-input:focus {
      border-color: #10b981;
      box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.15);
    }
    .auth-btn {
      width: 100%;
      background: #10b981;
      color: #030712;
      font-weight: 700;
      font-size: 0.875rem;
      border: none;
      border-radius: 8px;
      padding: 12px;
      cursor: pointer;
      transition: all 0.15s ease;
      letter-spacing: 0.02em;
    }
    .auth-btn:hover {
      background: #059669;
      box-shadow: 0 0 20px rgba(16, 185, 129, 0.35);
    }
    .auth-hint {
      margin-top: 20px;
      padding: 10px 14px;
      border-radius: 6px;
      background: rgba(31, 41, 55, 0.6);
      border: 1px dashed #374151;
      font-size: 0.75rem;
      color: #9ca3af;
    }
    .auth-hint code {
      color: #10b981;
      font-weight: 600;
      background: rgba(16, 185, 129, 0.1);
      padding: 2px 6px;
      border-radius: 4px;
    }
    .auth-error {
      display: none;
      color: #f87171;
      background: rgba(239, 68, 68, 0.1);
      border: 1px solid rgba(239, 68, 68, 0.3);
      padding: 8px 12px;
      border-radius: 6px;
      font-size: 0.75rem;
      margin-bottom: 14px;
    }

    /* ── MAIN DASHBOARD (BLACK SCREEN) ── */
    #dashboard-app {
      display: none;
      padding: 24px;
      max-width: 1100px;
      margin: 0 auto;
    }
    .header {
      background: #0b0f19;
      border: 1px solid #1f293d;
      border-radius: 12px;
      padding: 20px 24px;
      margin-bottom: 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 16px;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
    }
    .title-group h1 {
      font-size: 1.25rem;
      font-weight: 700;
      color: #f9fafb;
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .title-group p {
      font-size: 0.8125rem;
      color: #9ca3af;
      margin-top: 4px;
    }
    .status-badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: rgba(16, 185, 129, 0.12);
      color: #10b981;
      font-size: 0.72rem;
      font-weight: 600;
      padding: 4px 10px;
      border-radius: 20px;
      border: 1px solid rgba(16, 185, 129, 0.3);
    }
    .status-dot {
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: #10b981;
      box-shadow: 0 0 8px #10b981;
      animation: pulse 2s infinite;
    }
    @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.3; } 100% { opacity: 1; } }

    .btn {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 8px 14px;
      border-radius: 6px;
      font-size: 0.8125rem;
      font-weight: 600;
      cursor: pointer;
      border: none;
      transition: all 0.15s ease;
      text-decoration: none;
    }
    .btn-primary { background: #2563eb; color: #ffffff; }
    .btn-primary:hover { background: #1d4ed8; }
    .btn-success { background: #10b981; color: #030712; }
    .btn-success:hover { background: #059669; }
    .btn-outline {
      background: #030712;
      border: 1px solid #374151;
      color: #d1d5db;
    }
    .btn-outline:hover {
      background: #111827;
      border-color: #4b5563;
      color: #ffffff;
    }
    .btn-danger { background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.3); color: #f87171; }
    .btn-danger:hover { background: rgba(239, 68, 68, 0.25); color: #ef4444; }
    .btn-sm { padding: 4px 10px; font-size: 0.75rem; }

    /* Auto Progression Alert Banner */
    .pipeline-banner {
      background: linear-gradient(90deg, rgba(16, 185, 129, 0.08) 0%, rgba(6, 182, 212, 0.08) 100%);
      border: 1px solid rgba(16, 185, 129, 0.25);
      border-radius: 8px;
      padding: 12px 18px;
      margin-bottom: 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 12px;
      font-size: 0.8125rem;
      color: #d1d5db;
    }
    .pipeline-steps {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      font-weight: 600;
    }
    .pipeline-tag {
      padding: 3px 8px;
      border-radius: 4px;
      font-size: 0.72rem;
    }
    .tag-sent { background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }
    .tag-deliv { background: rgba(6, 182, 212, 0.15); color: #22d3ee; border: 1px solid rgba(6, 182, 212, 0.3); }
    .tag-read { background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }

    .card {
      background: #0b0f19;
      border: 1px solid #1f293d;
      border-radius: 10px;
      padding: 20px 24px;
      margin-bottom: 20px;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
    }
    .card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 16px;
      padding-bottom: 12px;
      border-bottom: 1px solid #1f293d;
    }
    .card-title {
      font-size: 0.95rem;
      font-weight: 700;
      color: #f3f4f6;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .messages-list { display: flex; flex-direction: column; gap: 12px; }
    .message-item {
      border: 1px solid #1f293d;
      border-radius: 8px;
      padding: 16px;
      background: #070a12;
      display: flex;
      flex-direction: column;
      gap: 12px;
      transition: border-color 0.2s, box-shadow 0.2s;
    }
    .message-item:hover {
      border-color: #374151;
      box-shadow: 0 4px 15px rgba(0, 0, 0, 0.4);
    }
    .message-item.status-read { border-left: 4px solid #10b981; }
    .message-item.status-delivered { border-left: 4px solid #06b6d4; }
    .message-item.status-sent { border-left: 4px solid #f59e0b; }
    .message-item.status-failed { border-left: 4px solid #ef4444; }

    .msg-top {
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 8px;
    }
    .msg-recipient {
      font-weight: 600;
      font-size: 0.875rem;
      color: #f9fafb;
    }
    .msg-ref {
      font-size: 0.75rem;
      color: #9ca3af;
      font-family: 'JetBrains Mono', monospace;
      background: #111827;
      padding: 2px 6px;
      border-radius: 4px;
      border: 1px solid #1f293d;
    }
    .msg-channel {
      font-size: 0.72rem;
      font-weight: 600;
      text-transform: uppercase;
      padding: 2px 8px;
      border-radius: 12px;
      background: rgba(6, 182, 212, 0.1);
      color: #22d3ee;
      border: 1px solid rgba(6, 182, 212, 0.3);
    }
    .msg-body {
      font-size: 0.875rem;
      color: #e5e7eb;
      line-height: 1.5;
      background: #030712;
      border: 1px solid #1f293d;
      padding: 10px 14px;
      border-radius: 6px;
    }
    .msg-actions {
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 8px;
      padding-top: 4px;
    }
    .msg-time {
      font-size: 0.75rem;
      color: #6b7280;
    }
    .msg-btn-group { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }

    /* Badges */
    .pill {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      padding: 3px 10px;
      border-radius: 20px;
      font-size: 0.72rem;
      font-weight: 600;
    }
    .pill-read { background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.35); }
    .pill-delivered { background: rgba(6, 182, 212, 0.15); color: #22d3ee; border: 1px solid rgba(6, 182, 212, 0.35); }
    .pill-sent { background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.35); }
    .pill-failed { background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.35); }

    .countdown-pill {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 3px 8px;
      border-radius: 4px;
      background: rgba(31, 41, 55, 0.8);
      border: 1px solid #374151;
      font-size: 0.72rem;
      font-family: 'JetBrains Mono', monospace;
      color: #38bdf8;
    }

    .empty-state { text-align: center; padding: 48px 20px; color: #6b7280; }
    .empty-state p { font-size: 0.875rem; margin-top: 8px; color: #9ca3af; }

    .log-box {
      max-height: 220px;
      overflow-y: auto;
      background: #030712;
      border: 1px solid #1f293d;
      color: #94a3b8;
      border-radius: 6px;
      padding: 12px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.75rem;
    }
    .log-entry { margin-bottom: 6px; border-bottom: 1px solid #111827; padding-bottom: 4px; }
    .log-success { color: #34d399; }
    .log-error { color: #f87171; }

    .toast {
      position: fixed;
      bottom: 24px;
      right: 24px;
      background: #10b981;
      color: #030712;
      padding: 12px 18px;
      border-radius: 8px;
      font-size: 0.8125rem;
      font-weight: 700;
      display: none;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5), 0 0 20px rgba(16, 185, 129, 0.3);
      z-index: 10000;
    }
  </style>
</head>
<body>

  <!-- ── 1. AUTH LOCK SCREEN (Requires typing secret key) ── -->
  <div id="auth-screen">
    <div class="auth-card">
      <div class="auth-icon">🛡️</div>
      <h2 class="auth-title">RESTRICTED ACCESS</h2>
      <p class="auth-subtitle">Dummy Communication Provider Simulator | Port 9000</p>

      <div id="auth-error-msg" class="auth-error">
        ✕ Access Denied: Incorrect Secret Key
      </div>

      <form onsubmit="handleAuthSubmit(event)">
        <div class="auth-input-group">
          <label class="auth-label" for="secret-key-input">Type Secret Key</label>
          <input
            type="password"
            id="secret-key-input"
            class="auth-input"
            placeholder="Type secret key to authenticate"
            autocomplete="current-password"
            autofocus
            required
          />
        </div>
        <button type="submit" class="auth-btn">Authorize & Unlock Console →</button>
      </form>

      <div class="auth-hint">
        Default Secret Key: <code>candidate-secret-key-2026</code>
      </div>
    </div>
  </div>

  <!-- ── 2. BLACK SCREEN CONSOLE DASHBOARD ── -->
  <div id="dashboard-app">
    <!-- Header -->
    <div class="header">
      <div class="title-group">
        <h1>
          <span>📡 Dummy Provider Console</span>
          <span class="status-badge"><span class="status-dot"></span> Port 9000 Online</span>
          <span class="status-badge" style="background: rgba(59, 130, 246, 0.12); color: #60a5fa; border-color: rgba(59, 130, 246, 0.3);">
            🔒 Authenticated
          </span>
        </h1>
        <p>Candidate Handset & Telephony Receiver Simulation | Webhook: <code>http://localhost:8000/api/v1/communications/webhook/</code></p>
      </div>
      <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
        <button class="btn btn-outline" onclick="fetchMessages()">↻ Refresh</button>
        <button class="btn btn-success" onclick="readAllMessages()">✓ Mark All as Read</button>
        <button class="btn btn-danger" onclick="lockConsole()">🔒 Lock Console</button>
      </div>
    </div>

    <!-- Automatic Message Status Pipeline Banner -->
    <div class="pipeline-banner">
      <div class="pipeline-steps">
        <span>⚡ Automatic Status Pipeline:</span>
        <span class="pipeline-tag tag-sent">1. Sent (0s)</span>
        <span>➔</span>
        <span class="pipeline-tag tag-deliv">2. Delivered (5s)</span>
        <span>➔</span>
        <span class="pipeline-tag tag-read">3. Read (10s)</span>
      </div>
      <div style="display: flex; align-items: center; gap: 8px;">
        <span style="color: #10b981;">● Real-time Webhooks Active</span>
      </div>
    </div>

    <!-- Backend Webhook Configuration Card -->
    <div class="card" style="border: 1px solid #1e3a5f; background: #070e1b;">
      <div class="card-header" style="border-bottom: 1px solid #1e2d42; margin-bottom: 10px;">
        <div class="card-title" style="color: #38bdf8; font-size: 0.95rem;">🔗 Backend Webhook Target URL</div>
      </div>
      <p style="font-size: 0.8125rem; color: #94a3b8; margin-bottom: 12px;">
        Webhooks from this simulator update the candidate portal in real-time:
      </p>
      <div style="display: flex; gap: 8px; flex-wrap: wrap;">
        <input
          type="text"
          id="target-webhook-url"
          placeholder="http://localhost:8000/api/v1/communications/webhook/"
          style="flex: 1; min-width: 280px; padding: 10px 14px; border: 1px solid #374151; border-radius: 6px; font-size: 0.8125rem; background: #030712; color: #f3f4f6; font-family: monospace;"
        >
        <button class="btn btn-primary" onclick="saveWebhookUrl()">Save Target URL</button>
      </div>
    </div>

    <!-- Incoming Messages Card -->
    <div class="card">
      <div class="card-header">
        <div class="card-title">
          📥 Candidate Inbound Messages (<span id="msg-count">0</span>)
        </div>
        <div style="display: flex; align-items: center; gap: 12px; font-size: 0.8125rem; color: #9ca3af;">
          <label style="display: flex; align-items: center; gap: 6px; cursor: pointer;">
            <input type="checkbox" id="auto-refresh" checked> Auto-refresh (every 1s)
          </label>
        </div>
      </div>

      <div id="messages-container" class="messages-list">
        <div class="empty-state">
          <h3>No messages received yet</h3>
          <p>Send a message from the Candidate Communication Platform dashboard, and it will appear here in real-time with automatic 5s / 10s status updates!</p>
        </div>
      </div>
    </div>

    <!-- Manual Webhook Dispatcher -->
    <div class="card">
      <div class="card-header">
        <div class="card-title">⚡ Instant Webhook Trigger</div>
      </div>
      <p style="font-size: 0.8125rem; color: #9ca3af; margin-bottom: 12px;">
        Quickly send a webhook event to the platform for any candidate or message ID to advance its status:
      </p>
      <div style="display: flex; gap: 8px; flex-wrap: wrap;">
        <input
          type="text"
          id="manual-ref"
          placeholder="Message Reference ID (e.g. sent_12345) or Candidate ID"
          style="flex: 1; min-width: 220px; padding: 10px 14px; border: 1px solid #374151; border-radius: 6px; font-size: 0.8125rem; background: #030712; color: #f3f4f6;"
        >
        <button class="btn btn-outline" onclick="triggerManualWebhook('delivered')">Mark as DELIVERED</button>
        <button class="btn btn-success" onclick="triggerManualWebhook('read')">Mark as READ (✓ read)</button>
      </div>
    </div>

    <!-- Recent Webhook Dispatches Terminal -->
    <div class="card">
      <div class="card-header">
        <div class="card-title">📜 Webhook Dispatch Activity Log</div>
        <button class="btn btn-outline btn-sm" onclick="clearLogs()">Clear</button>
      </div>
      <div id="webhook-logs" class="log-box">
        <div style="color: #6b7280;">No webhooks dispatched in this session yet.</div>
      </div>
    </div>
  </div>

  <div id="toast" class="toast">Status updated and webhook dispatched!</div>

  <script>
    let autoRefreshInterval = null;
    let storedSecretKey = sessionStorage.getItem('dummy_secret_key') || localStorage.getItem('dummy_secret_key') || '';

    // ── Authentication Handling ──
    async function verifyAndLogin(key) {
      const errBox = document.getElementById('auth-error-msg');
      errBox.style.display = 'none';

      try {
        const res = await fetch('/api/auth/verify', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ secret_key: key })
        });
        const data = await res.json();
        if (res.ok && data.authenticated) {
          storedSecretKey = key;
          sessionStorage.setItem('dummy_secret_key', key);
          localStorage.setItem('dummy_secret_key', key);
          document.getElementById('auth-screen').style.display = 'none';
          document.getElementById('dashboard-app').style.display = 'block';
          fetchMessages();
          startAutoRefresh();
        } else {
          errBox.textContent = '✕ ' + (data.error || 'Access Denied: Invalid Secret Key');
          errBox.style.display = 'block';
        }
      } catch (e) {
        errBox.textContent = '✕ Connection error verifying key: ' + e;
        errBox.style.display = 'block';
      }
    }

    function handleAuthSubmit(e) {
      e.preventDefault();
      const input = document.getElementById('secret-key-input');
      const val = input.value.trim();
      if (!val) return;
      verifyAndLogin(val);
    }

    function lockConsole() {
      sessionStorage.removeItem('dummy_secret_key');
      localStorage.removeItem('dummy_secret_key');
      storedSecretKey = '';
      clearInterval(autoRefreshInterval);
      document.getElementById('dashboard-app').style.display = 'none';
      document.getElementById('auth-screen').style.display = 'flex';
      document.getElementById('secret-key-input').value = '';
      document.getElementById('auth-error-msg').style.display = 'none';
    }

    function getAuthHeaders() {
      return {
        'Content-Type': 'application/json',
        'X-Secret-Key': storedSecretKey,
      };
    }

    function showToast(msg) {
      const toast = document.getElementById('toast');
      toast.textContent = msg;
      toast.style.display = 'block';
      setTimeout(() => { toast.style.display = 'none'; }, 3000);
    }

    // ── Message Fetching & Rendering ──
    async function fetchMessages() {
      if (!storedSecretKey) return;
      try {
        const res = await fetch('/api/messages', { headers: getAuthHeaders() });
        if (res.status === 401) {
          lockConsole();
          return;
        }
        const data = await res.json();
        document.getElementById('msg-count').textContent = data.count || 0;
        const targetInput = document.getElementById('target-webhook-url');
        if (data.webhook_url && targetInput && !targetInput.value) {
          targetInput.value = data.webhook_url;
        }
        renderMessages(data.messages || []);
        renderLogs(data.logs || []);
      } catch (e) {
        console.error('Failed to fetch messages', e);
      }
    }

    async function saveWebhookUrl() {
      const url = document.getElementById('target-webhook-url').value.trim();
      if (!url) {
        alert('Please enter a valid webhook URL.');
        return;
      }
      try {
        const res = await fetch('/api/config/webhook-url', {
          method: 'POST',
          headers: getAuthHeaders(),
          body: JSON.stringify({ webhook_url: url })
        });
        const data = await res.json();
        showToast('Webhook target updated: ' + data.webhook_url);
        fetchMessages();
      } catch (e) {
        alert('Failed to update URL: ' + e);
      }
    }

    function renderMessages(messages) {
      const container = document.getElementById('messages-container');
      if (!messages || messages.length === 0) {
        container.innerHTML = `
          <div class="empty-state">
            <h3>No messages received yet</h3>
            <p>Send a message from the Candidate Communication Platform dashboard, and it will appear here in real-time with automatic 5s / 10s status updates!</p>
          </div>
        `;
        return;
      }

      const now = Date.now() / 1000;

      container.innerHTML = messages.map(msg => {
        const status = (msg.status || 'sent').toLowerCase();
        const statusClass = 'status-' + status;

        let pillHtml = '';
        let countdownHtml = '';
        const elapsed = now - (msg.timestamp || now);

        if (status === 'read') {
          pillHtml = '<span class="pill pill-read">✓ Read</span>';
          countdownHtml = '<span class="countdown-pill" style="color: #34d399;">✓ Auto-Progress Complete (Read)</span>';
        } else if (status === 'delivered') {
          pillHtml = '<span class="pill pill-delivered">✓ Delivered</span>';
          const remainingRead = Math.max(0, Math.ceil(10 - elapsed));
          if (remainingRead > 0) {
            countdownHtml = `<span class="countdown-pill">⏳ Auto-Reading in ${remainingRead}s...</span>`;
          } else {
            countdownHtml = `<span class="countdown-pill">⏳ Transitioning to Read...</span>`;
          }
        } else if (status === 'failed') {
          pillHtml = '<span class="pill pill-failed">✕ Failed</span>';
          countdownHtml = '<span class="countdown-pill" style="color: #f87171;">✕ Failed Transmission</span>';
        } else {
          // Sent
          pillHtml = '<span class="pill pill-sent">Sent</span>';
          const remainingDeliv = Math.max(0, Math.ceil(5 - elapsed));
          const remainingRead = Math.max(0, Math.ceil(10 - elapsed));
          countdownHtml = `<span class="countdown-pill">⏳ Delivering in ${remainingDeliv}s | Read in ${remainingRead}s</span>`;
        }

        const isRead = status === 'read';

        return `
          <div class="message-item ${statusClass}">
            <div class="msg-top">
              <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                <span class="msg-recipient">📱 ${msg.recipient}</span>
                <span class="msg-channel">${msg.channel || 'SMS'}</span>
                <span class="msg-ref">${msg.id}</span>
              </div>
              <div style="display: flex; align-items: center; gap: 8px;">
                ${countdownHtml}
                ${pillHtml}
              </div>
            </div>
            <div class="msg-body">${msg.content}</div>
            <div class="msg-actions">
              <span class="msg-time">Received: ${msg.created_at || 'Just now'}</span>
              <div class="msg-btn-group">
                ${!isRead ? `
                  <button class="btn btn-outline btn-sm" onclick="advanceStatus('${msg.id}', 'delivered')">Mark Delivered</button>
                  <button class="btn btn-success btn-sm" onclick="advanceStatus('${msg.id}', 'read')">📖 Read Message</button>
                ` : `
                  <span style="font-size: 0.75rem; color: #10b981; font-weight: 600;">✓ Message Read by Candidate</span>
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
        const errDetail = l.result && l.result.error ? ` (${l.result.error})` : '';
        return `
          <div class="log-entry">
            <span style="color: #64748b;">[${l.timestamp}]</span>
            <span style="color: #38bdf8;">WEBHOOK POST</span> ->
            <code>${JSON.stringify(l.payload)}</code>
            <span class="${isOk ? 'log-success' : 'log-error'}">${isOk ? '✓ HTTP 200 OK' : '✕ FAIL' + errDetail}</span>
          </div>
        `;
      }).join('');
    }

    async function advanceStatus(msgId, status) {
      try {
        const res = await fetch(`/api/messages/${msgId}/status`, {
          method: 'POST',
          headers: getAuthHeaders(),
          body: JSON.stringify({ status })
        });
        const data = await res.json();
        showToast(`Message marked as ${status.toUpperCase()}! Webhook dispatched.`);
        fetchMessages();
      } catch (e) {
        alert('Failed to update status: ' + e);
      }
    }

    async function readAllMessages() {
      try {
        const res = await fetch('/api/messages/read-all', {
          method: 'POST',
          headers: getAuthHeaders()
        });
        showToast('All messages marked as READ! Webhooks dispatched.');
        fetchMessages();
      } catch (e) {
        alert('Failed: ' + e);
      }
    }

    async function simulateDuplicate(msgId) {
      try {
        const res = await fetch(`/messages/${msgId}/simulate-duplicate-webhook`, {
          method: 'POST',
          headers: getAuthHeaders()
        });
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
        alert('Please enter a Reference ID or Message ID.');
        return;
      }
      try {
        const res = await fetch('/api/webhook/manual', {
          method: 'POST',
          headers: getAuthHeaders(),
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

    // Auto-refresh control (every 1 second for crisp countdown display)
    document.getElementById('auto-refresh').addEventListener('change', (e) => {
      if (e.target.checked) {
        startAutoRefresh();
      } else {
        clearInterval(autoRefreshInterval);
      }
    });

    function startAutoRefresh() {
      clearInterval(autoRefreshInterval);
      autoRefreshInterval = setInterval(fetchMessages, 1000);
    }

    // Check existing authentication on page load
    if (storedSecretKey) {
      verifyAndLogin(storedSecretKey);
    }
  </script>
</body>
</html>
"""


# ── HTTP Request Handler ──────────────────────────────────────────────────────
class DummyCommunicationHandler(BaseHTTPRequestHandler):
    def _send_json(self, status_code: int, data: dict):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Secret-Key")
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
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Secret-Key")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        qparams = parse_qs(parsed.query)

        # 1. Web UI: Root path for browsers
        if parsed.path in ("/", "/ui", "/inbox") or self.headers.get("Accept", "").find("text/html") != -1:
            self._send_html(200, HTML_PAGE)
            return

        # 2. Healthcheck (Public machine-to-machine monitoring)
        if parsed.path == "/health":
            statuses = [m.get("status") for m in MESSAGES_DB.values()]
            self._send_json(200, {
                "service": "Dummy Independent Communication Provider",
                "status": "healthy" if SIM_CONFIG.get("mode") == "normal" else "degraded",
                "version": "2.1.0",
                "secured_with_secret_key": True,
                "auto_progression": "Delivered (5s) -> Read (10s)",
                "stored_messages": len(MESSAGES_DB),
                "messages_sent": sum(1 for s in statuses if s in ("sent", "delivered", "read")),
                "messages_delivered": sum(1 for s in statuses if s in ("delivered", "read")),
                "messages_read": sum(1 for s in statuses if s == "read"),
                "messages_failed": sum(1 for s in statuses if s == "failed"),
                "simulation_config": SIM_CONFIG,
            })
            return

        # 3. Secured API: Messages list & logs (Requires Secret Key)
        if parsed.path in ("/api/messages", "/messages"):
            if not is_authorized(self.headers, qparams):
                self._send_json(401, {
                    "error": "Unauthorized: Access Denied. Valid secret key required.",
                    "authenticated": False
                })
                return

            msg_list = sorted(list(MESSAGES_DB.values()), key=lambda x: x.get("timestamp", 0), reverse=True)
            self._send_json(200, {
                "count": len(MESSAGES_DB),
                "messages": msg_list,
                "logs": WEBHOOK_LOGS[:20],
                "webhook_url": SIM_CONFIG.get("webhook_url"),
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

        # ── Secret Key Verification Endpoint: /api/auth/verify ─────────────────
        if parsed.path == "/api/auth/verify":
            candidate_key = payload.get("secret_key", "").strip()
            if candidate_key == DUMMY_SECRET_KEY:
                self._send_json(200, {
                    "authenticated": True,
                    "message": "Authorization successful."
                })
            else:
                self._send_json(401, {
                    "authenticated": False,
                    "error": "Access Denied: Incorrect Secret Key."
                })
            return

        # ── Send Message Endpoint: /messages/send ─────────────────────────────
        # Called by Candidate Communication Platform backend when dispatching SMS/WhatsApp
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
            now_ts = time.time()

            if is_invalid_recipient:
                record = {
                    "id": msg_id,
                    "recipient": recipient,
                    "content": content,
                    "channel": channel,
                    "status": "failed",
                    "error": "Invalid recipient MSISDN: Unallocated number or destination not reachable.",
                    "created_at": created_at,
                    "timestamp": now_ts,
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
                    "timestamp": now_ts,
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

            # Successful initial dispatch ("sent")
            initial_status = "sent"
            record = {
                "id": msg_id,
                "recipient": recipient,
                "content": content,
                "channel": channel,
                "status": initial_status,
                "error": None,
                "created_at": created_at,
                "timestamp": now_ts,
                "auto_update": True,
            }
            MESSAGES_DB[msg_id] = record

            # Schedule automatic progression: Delivered in 5s -> Read in 10s
            schedule_automatic_status_updates(msg_id)

            self._send_json(201, {
                "success": True,
                "reference_id": msg_id,
                "status": initial_status,
                "provider": "dummy-service",
                "created_at": created_at,
                "auto_progression": "Delivered after 5s, Read after 10s",
                "message": "Message accepted by dummy provider. Auto-progression scheduled.",
            })
            return

        # ── Secured Endpoints (Require Secret Key) ─────────────────────────────
        if not is_authorized(self.headers):
            self._send_json(401, {
                "error": "Unauthorized: Valid secret key required for UI control actions.",
                "authenticated": False
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
                if new_status == "delivered":
                    msg["delivered_at"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                elif new_status == "read":
                    msg["read_at"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

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
                    msg["read_at"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
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
                if new_status == "delivered":
                    MESSAGES_DB[ref]["delivered_at"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                elif new_status == "read":
                    MESSAGES_DB[ref]["read_at"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

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

        # 6. Update Webhook URL configuration
        if parsed.path == "/api/config/webhook-url":
            new_url = payload.get("webhook_url", "").strip()
            if new_url:
                SIM_CONFIG["webhook_url"] = new_url
                self._send_json(200, {"success": True, "webhook_url": new_url})
                return
            self._send_json(400, {"error": "Missing webhook_url in request payload"})
            return

        self._send_json(404, {"error": "Not found"})

    def log_message(self, format, *args):
        # Silence routine access logs
        pass


def run(port=9000):
    server_address = ("", port)
    httpd = HTTPServer(server_address, DummyCommunicationHandler)
    print("===========================================================")
    print(f" 📡 Dummy Communication Provider Simulator running on port {port}")
    print(f" 🖥️  Black-Screen Web UI: http://localhost:{port}/")
    print(f" 🔐 Secret Key Security: Active")
    print(f" 🔑 Default Secret Key:  {DUMMY_SECRET_KEY}")
    print(f" ⚡ Auto Status Progression: Delivered after 5s | Read after 10s")
    print(f" 🔗 Backend Webhook Target: {SIM_CONFIG['webhook_url']}")
    print("===========================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down dummy communication service.")
        httpd.server_close()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", sys.argv[1] if len(sys.argv) > 1 else 9000))
    run(port)
