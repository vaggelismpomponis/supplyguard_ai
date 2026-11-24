#!/usr/bin/env python3
"""Tiny independently deployable external information service (wrap as an MCP server or call over HTTP).
   GET /alerts?region=TW  ->  JSON list of risk alerts.    Run: python external_info_service.py 8099"""
import json, sys, os
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
FEED = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "risk_feed.json")))
class H(BaseHTTPRequestHandler):
    def do_GET(self):
        q = parse_qs(urlparse(self.path).query).get("region", [None])[0]
        b = json.dumps([a for a in FEED["alerts"] if q is None or a["region"] == q]).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(b)
HTTPServer(("0.0.0.0", int(sys.argv[1]) if len(sys.argv) > 1 else 8099), H).serve_forever()
