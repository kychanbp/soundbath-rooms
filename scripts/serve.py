"""Local web server for the world. It takes many connections at once, which phones need while a room loads."""
import http.server, os, sys
class Handler(http.server.SimpleHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map, '.m4a': 'audio/mp4', '.gltf': 'model/gltf+json', '.glb': 'model/gltf-binary', '.js': 'text/javascript'}
    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache'); super().end_headers()
    def log_message(self, *a): pass
class Server(http.server.ThreadingHTTPServer):
    request_queue_size = 256; daemon_threads = True
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'web'))
Server(('', int(sys.argv[1]) if len(sys.argv) > 1 else 8000), Handler).serve_forever()
