"""Stand-in for the n8n OTP webhook during UI tests: accepts the same request, writes the code to
a JSON-lines file instead of e-mailing it, and answers like the real workflow ({"ok": true})."""
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT, LOG, SECRET = int(sys.argv[1]), sys.argv[2], sys.argv[3]


class Hook(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["content-length"])))
        ok = self.headers.get("x-otp-secret") == SECRET
        if ok:
            with open(LOG, "a") as f:
                f.write(json.dumps({"to": body["to"], "code": body["code"]}) + "\n")
        out = json.dumps({"ok": True, "channel": "email"} if ok else {"ok": False, "reason": "bad shared secret"})
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.end_headers()
        self.wfile.write(out.encode())

    def log_message(self, *a):
        pass


HTTPServer(("127.0.0.1", PORT), Hook).serve_forever()
