from http.server import BaseHTTPRequestHandler, HTTPServer
import json

class RelayHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers["Content-Length"])
        body = self.rfile.read(content_length)
        data = json.loads(body)
        response = {"status": "received", "payload": data}
        self.send_response(200)
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())

def run_server(port=8080):
    server = HTTPServer(("", port), RelayHandler)
    print(f"OpenWispr Relay running on port {port}")
    server.serve_forever()
