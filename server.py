from http.server import HTTPServer, SimpleHTTPRequestHandler
import os
import json
import uuid

DATA_PATH = os.path.join(os.getcwd(), "data")
DB_FILE = os.path.join(DATA_PATH, "db.json")

def ensure_db():
    os.makedirs(DATA_PATH, exist_ok=True)
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f:
            json.dump({"students": {}}, f)

def read_db():
    ensure_db()
    with open(DB_FILE, "r") as f:
        return json.load(f)

def write_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f)

class AppHandler(SimpleHTTPRequestHandler):
    def _json_response(self, status=200, payload=None):
        body = json.dumps(payload or {}).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length > 0 else b""
        try:
            return json.loads(raw.decode("utf-8")) if raw else {}
        except json.JSONDecodeError:
            return {}

    def do_POST(self):
        if self.path == "/api/login":
            payload = self._read_json()
            name = (payload.get("name") or "").strip()
            class_code = (payload.get("classCode") or "A").strip()
            if not name:
                return self._json_response(400, {"error": "name required"})
            db = read_db()
            # find existing
            for sid, s in db["students"].items():
                if s.get("name") == name and s.get("classCode") == class_code:
                    return self._json_response(200, {"studentId": sid, "name": name, "classCode": class_code})
            # create new
            sid = uuid.uuid4().hex
            db["students"][sid] = {
                "name": name,
                "classCode": class_code,
                "scores": {"maths": 0, "english": 0, "science": 0},
                "questions": {"maths": 0, "english": 0, "science": 0},
                "lastUpdated": None,
            }
            write_db(db)
            return self._json_response(200, {"studentId": sid, "name": name, "classCode": class_code})

        if self.path == "/api/progress":
            payload = self._read_json()
            sid = payload.get("studentId")
            subject = payload.get("subject")
            score_total = payload.get("scoreTotal")
            questions_count = payload.get("questionsCount")
            if not sid or subject not in ("maths", "english", "science"):
                return self._json_response(400, {"error": "invalid payload"})
            db = read_db()
            student = db["students"].get(sid)
            if not student:
                return self._json_response(404, {"error": "student not found"})
            if isinstance(score_total, int) and score_total >= 0:
                student["scores"][subject] = score_total
            if isinstance(questions_count, int) and questions_count >= 0:
                student["questions"][subject] = questions_count
            student["lastUpdated"] = __import__("time").strftime("%Y-%m-%d %H:%M:%S")
            write_db(db)
            return self._json_response(200, {"ok": True})

        return super().do_POST()

    def do_GET(self):
        if self.path == "/api/students":
            db = read_db()
            # summarize
            items = []
            for sid, s in db["students"].items():
                item = {"studentId": sid, "name": s["name"], "classCode": s["classCode"], "scores": s.get("scores", {}), "questions": s.get("questions", {}), "lastUpdated": s["lastUpdated"]}
                items.append(item)
            return self._json_response(200, {"students": items})
        return super().do_GET()

def run(server_class=HTTPServer, handler_class=AppHandler, port=8000):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f"Starting server on port {port}...")
    print(f"Serving files from: {os.getcwd()}")
    ensure_db()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    print("Server stopped.")

if __name__ == '__main__':
    run()
