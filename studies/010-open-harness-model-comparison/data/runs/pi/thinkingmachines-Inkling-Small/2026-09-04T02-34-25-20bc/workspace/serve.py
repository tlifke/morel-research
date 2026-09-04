import http.server, socketserver, os, webbrowser, threading, sys, time

def build_index():
    # generate contracts.json
    files = sorted([f for f in os.listdir('contract_text') if f.endswith('.txt')])
    ids = [f[:-4] for f in files]
    import json
    with open('contracts.json', 'w') as out:
        json.dump({"contracts": ids}, out)
    # generate data.json (ground truth parsed) for faster loading
    gt = {}
    with open('contract_ground_truth') as f:
        for line in f:
            rec = json.loads(line)
            gt[rec['contract_id']] = rec['gold']
    with open('data.json', 'w') as out:
        json.dump(gt, out)

class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

if __name__ == '__main__':
    build_index()
    # open server on a free port
    with socketserver.TCPServer(("", 0), Handler) as httpd:
        port = httpd.server_address[1]
        print(f"Serving at http://localhost:{port}")
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        # open browser
        webbrowser.open(f"http://localhost:{port}/index.html")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            httpd.shutdown()
