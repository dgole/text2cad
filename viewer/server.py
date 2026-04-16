"""
Minimal STL viewer server.

Run from the project root:
    python viewer/server.py

Then open http://localhost:8321 in your browser.
"""
from __future__ import annotations

import json
import os
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

PORT = 8321
PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Handler(SimpleHTTPRequestHandler):
    """Serves static files from viewer/ and provides a JSON API."""

    def __init__(self, *args, **kwargs):
        # Serve files relative to the project root so STLs are accessible
        super().__init__(*args, directory=str(PROJECT_ROOT), **kwargs)

    def do_GET(self):
        # --- API: list parts and their STL files ---
        if self.path == "/api/parts":
            parts: dict[str, list[str]] = {}
            projects_dir = PROJECT_ROOT / "projects"
            for child in sorted(projects_dir.iterdir()):
                output_dir = child / "output"
                if child.is_dir() and output_dir.is_dir():
                    stls = sorted(
                        f.name for f in output_dir.iterdir() if f.suffix.lower() == ".stl"
                    )
                    if stls:
                        parts[child.name] = stls
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(parts).encode())
            return

        # --- Serve index.html for bare /  ---
        if self.path == "/":
            self.path = "/viewer/index.html"

        super().do_GET()


def main():
    server = HTTPServer(("127.0.0.1", PORT), Handler)
    print(f"STL Viewer running at  http://localhost:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()


if __name__ == "__main__":
    main()
