import os
import sys
import json
import subprocess
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler

PORT = int(os.environ.get("PORT", 3000))
PROJECT_DIR = Path(__file__).parent


class NewsAgentHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        sys.stdout.write(f"[{self.log_date_time_string()}] {format % args}\n")
        sys.stdout.flush()

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            index_path = PROJECT_DIR / "index.html"
            if index_path.exists():
                content = index_path.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return

        if self.path == "/api/status":
            self.send_json({
                "status": "online",
                "gemini_api_key_configured": bool(os.environ.get("GEMINI_API_KEY")),
                "gemini_model": os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
                "has_news_json": (PROJECT_DIR / "news.json").exists(),
                "has_daily_briefing": (PROJECT_DIR / "daily_briefing.md").exists(),
                "has_ai_briefing": (PROJECT_DIR / "ai_briefing.md").exists(),
            })
            return

        if self.path == "/api/reports":
            reports = {}
            for filename in ["news.json", "daily_briefing.md", "ai_briefing.md"]:
                filepath = PROJECT_DIR / filename
                if filepath.exists():
                    try:
                        reports[filename] = filepath.read_text(encoding="utf-8")
                    except Exception as e:
                        reports[filename] = f"Error reading file: {e}"
                else:
                    reports[filename] = None
            self.send_json(reports)
            return

        return super().do_GET()

    def do_POST(self):
        if self.path == "/api/run-collector":
            output = self.execute_script("news_collector.py")
            self.send_json(output)
            return

        if self.path == "/api/run-analyzer":
            output = self.execute_script("ai_news_analyzer.py")
            self.send_json(output)
            return

        self.send_response(404)
        self.end_headers()

    def send_json(self, data):
        response_bytes = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.end_headers()
        self.wfile.write(response_bytes)

    def execute_script(self, script_name):
        script_path = PROJECT_DIR / script_name
        if not script_path.exists():
            return {"success": False, "error": f"{script_name} not found"}

        try:
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(PROJECT_DIR),
                env=os.environ.copy()
            )
            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


def run_server():
    server_address = ("0.0.0.0", PORT)
    httpd = HTTPServer(server_address, NewsAgentHandler)
    print(f"AI News Agent Server started on port {PORT}", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.", flush=True)
        httpd.server_close()


if __name__ == "__main__":
    run_server()
