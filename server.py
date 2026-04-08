import http.server, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
http.server.HTTPServer(("", 3339), http.server.SimpleHTTPRequestHandler).serve_forever()
