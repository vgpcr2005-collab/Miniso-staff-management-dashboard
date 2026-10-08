import hashlib
import hmac
import json
import math
import mimetypes
import os
import re
import secrets
import sqlite3
import time
import traceback
from contextlib import contextmanager
from datetime import datetime
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parent
WEB_ROOT = ROOT / "web"
DATABASE_PATH = Path(os.environ.get("DATABASE_PATH", ROOT / "data" / "miniso-dashboard.sqlite3"))
SESSION_COOKIE = "miniso_session"
SESSION_DURATION = 7 * 24 * 60 * 60
PASSWORD_ITERATIONS = 310_000
MAX_REQUEST_SIZE = 1_000_000
USERNAME_PATTERN = re.compile(r"^[a-z0-9_-]{3,40}$")
MONTH_PATTERN = re.compile(r"^\d{4}-\d{2}$")
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def connect_database():
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def database():
    connection = connect_database()
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def initialize_database():
    with database() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                salt BLOB NOT NULL,
                password_hash BLOB NOT NULL,
                state_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                expires_at INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS sessions_expiry ON sessions(expires_at);
            """
        )


def initial_state():
    month = datetime.now().strftime("%Y-%m")
    month_start = f"{month}-01"
    return {
        "staff": [
            {"id": "S001", "name": "Ravi Kumar", "department": "Sales", "status": "Active", "defaultTarget": 100000},
            {"id": "S002", "name": "Priya Sharma", "department": "Sales", "status": "Active", "defaultTarget": 120000},
            {"id": "S003", "name": "Arun Kumar", "department": "Sales", "status": "Active", "defaultTarget": 90000},
        ],
        "targets": [
            {"staffId": "S001", "month": month, "amount": 100000},
            {"staffId": "S002", "month": month, "amount": 120000},
            {"staffId": "S003", "month": month, "amount": 90000},
        ],
        "sales": [
            {"id": "SALE001", "staffId": "S001", "date": month_start, "product": "Product A", "quantity": 1, "amount": 5000, "paymentStatus": "Completed"},
            {"id": "SALE002", "staffId": "S001", "date": month_start, "product": "Product B", "quantity": 1, "amount": 8000, "paymentStatus": "Completed"},
            {"id": "SALE003", "staffId": "S001", "date": month_start, "product": "Travel Bag", "quantity": 1, "amount": 72000, "paymentStatus": "Completed"},
            {"id": "SALE004", "staffId": "S002", "date": month_start, "product": "Product C", "quantity": 1, "amount": 10000, "paymentStatus": "Completed"},
            {"id": "SALE005", "staffId": "S002", "date": month_start, "product": "Beauty Kit", "quantity": 2, "amount": 120000, "paymentStatus": "Completed"},
            {"id": "SALE006", "staffId": "S003", "date": month_start, "product": "Storage Box", "quantity": 1, "amount": 40000, "paymentStatus": "Completed"},
        ],
        "rules": [
            {"threshold": 80, "reward": 1000},
            {"threshold": 100, "reward": 2000},
            {"threshold": 110, "reward": 3000},
            {"threshold": 120, "reward": 5000},
        ],
    }


def validate_state(value):
    if not isinstance(value, dict):
        raise ValueError("Dashboard data must be an object.")
    staff = value.get("staff")
    targets = value.get("targets")
    sales = value.get("sales")
    rules = value.get("rules")
    if not all(isinstance(items, list) for items in (staff, targets, sales, rules)):
        raise ValueError("Dashboard data is missing staff, targets, sales, or rules.")
    if len(staff) > 5000 or len(targets) > 50000 or len(sales) > 100000 or len(rules) != 4:
        raise ValueError("Dashboard data exceeds supported limits or has invalid rules.")

    clean_staff = []
    staff_ids = set()
    staff_names = set()
    for person in staff:
        if not isinstance(person, dict):
            raise ValueError("Each staff member must be an object.")
        staff_id = _text(person.get("id"), "Staff ID", 40)
        name = _text(person.get("name"), "Staff name", 80)
        department = _text(person.get("department"), "Department", 60)
        status = person.get("status")
        target = _number(person.get("defaultTarget"), "Default target", minimum=0)
        name_key = name.casefold()
        if status not in ("Active", "Inactive") or staff_id in staff_ids or name_key in staff_names:
            raise ValueError("Staff name, status, or ID is invalid.")
        staff_ids.add(staff_id)
        staff_names.add(name_key)
        clean_staff.append({
            "id": staff_id,
            "name": name,
            "department": department,
            "status": status,
            "defaultTarget": target,
        })

    clean_targets = []
    target_keys = set()
    for target in targets:
        if not isinstance(target, dict):
            raise ValueError("Each target must be an object.")
        staff_id = _text(target.get("staffId"), "Target staff ID", 40)
        month = target.get("month")
        if staff_id not in staff_ids or not isinstance(month, str) or not MONTH_PATTERN.fullmatch(month):
            raise ValueError("Target staff or month is invalid.")
        try:
            datetime.strptime(month, "%Y-%m")
        except ValueError as error:
            raise ValueError("Target month is invalid.") from error
        target_key = (staff_id, month)
        if target_key in target_keys:
            raise ValueError("A staff member can only have one target per month.")
        target_keys.add(target_key)
        clean_targets.append({
            "staffId": staff_id,
            "month": month,
            "amount": _number(target.get("amount"), "Target amount", minimum=0, exclusive=True),
        })

    clean_sales = []
    sale_ids = set()
    for sale in sales:
        if not isinstance(sale, dict):
            raise ValueError("Each sale must be an object.")
        sale_id = _text(sale.get("id"), "Sale ID", 40)
        staff_id = _text(sale.get("staffId"), "Sale staff ID", 40)
        date = sale.get("date")
        product = _text(sale.get("product"), "Product", 100)
        quantity = _number(sale.get("quantity"), "Quantity", minimum=1)
        status = sale.get("paymentStatus")
        if (
            staff_id not in staff_ids
            or not isinstance(date, str)
            or not DATE_PATTERN.fullmatch(date)
            or status not in ("Completed", "Pending", "Refunded")
            or sale_id in sale_ids
            or not quantity.is_integer()
        ):
            raise ValueError("Sale ID, staff, date, quantity, or payment status is invalid.")
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError as error:
            raise ValueError("Sale date is invalid.") from error
        sale_ids.add(sale_id)
        clean_sales.append({
            "id": sale_id,
            "staffId": staff_id,
            "date": date,
            "product": product,
            "quantity": int(quantity),
            "amount": _number(sale.get("amount"), "Sale amount", minimum=0, exclusive=True),
            "paymentStatus": status,
        })

    clean_rules = []
    for rule in rules:
        if not isinstance(rule, dict):
            raise ValueError("Each incentive rule must be an object.")
        clean_rules.append({
            "threshold": _number(rule.get("threshold"), "Rule threshold", minimum=0, exclusive=True),
            "reward": _number(rule.get("reward"), "Rule reward", minimum=0),
        })
    if any(clean_rules[index]["threshold"] <= clean_rules[index - 1]["threshold"] for index in range(1, 4)):
        raise ValueError("Incentive thresholds must be strictly increasing.")
    return {"staff": clean_staff, "targets": clean_targets, "sales": clean_sales, "rules": clean_rules}


def _text(value, label, maximum):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"{label} is invalid.")
    return value.strip()


def _number(value, label, minimum, exclusive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number.")
    below_minimum = value <= minimum if exclusive else value < minimum
    if below_minimum:
        raise ValueError(f"{label} is outside the allowed range.")
    return float(value)


class DashboardHandler(BaseHTTPRequestHandler):
    server_version = "MINISO-Dashboard"

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/api/session":
            user = self.current_user()
            self.send_json(200, {"authenticated": user is not None, "user": self.public_user(user) if user else None})
        elif path == "/api/state":
            user = self.require_user()
            if user:
                with database() as connection:
                    row = connection.execute("SELECT state_json FROM users WHERE id = ?", (user["id"],)).fetchone()
                self.send_json(200, json.loads(row["state_json"]))
        elif path.startswith("/api/"):
            self.send_json(404, {"error": "API endpoint not found."})
        else:
            self.serve_static(path)

    def do_POST(self):
        path = urlsplit(self.path).path
        if not self.check_origin():
            return
        try:
            body = self.read_json()
            if path == "/api/register":
                self.register(body)
            elif path == "/api/login":
                self.login(body)
            elif path == "/api/logout":
                self.logout()
            else:
                self.send_json(404, {"error": "API endpoint not found."})
        except ValueError as error:
            self.send_json(400, {"error": str(error)})
        except sqlite3.IntegrityError:
            self.send_json(409, {"error": "That username is already registered."})
        except Exception:
            traceback.print_exc()
            self.send_json(500, {"error": "The server could not complete this request."})

    def do_PUT(self):
        if urlsplit(self.path).path != "/api/state":
            self.send_json(404, {"error": "API endpoint not found."})
            return
        if not self.check_origin():
            return
        user = self.require_user()
        if not user:
            return
        try:
            state = validate_state(self.read_json())
            with database() as connection:
                connection.execute(
                    "UPDATE users SET state_json = ? WHERE id = ?",
                    (json.dumps(state, separators=(",", ":")), user["id"]),
                )
            self.send_json(200, {"saved": True})
        except ValueError as error:
            self.send_json(400, {"error": str(error)})
        except Exception:
            traceback.print_exc()
            self.send_json(500, {"error": "The server could not save dashboard data."})

    def register(self, body):
        name = body.get("name")
        username = body.get("username")
        password = body.get("password")
        if not isinstance(name, str) or not 2 <= len(name.strip()) <= 80:
            raise ValueError("Enter a name between 2 and 80 characters.")
        if not isinstance(username, str) or not USERNAME_PATTERN.fullmatch(username):
            raise ValueError("Username must be 3–40 characters and use letters, numbers, _ or -.")
        if not isinstance(password, str) or len(password) < 8 or len(password) > 1024:
            raise ValueError("Password must contain 8–1024 characters.")
        salt = secrets.token_bytes(16)
        password_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PASSWORD_ITERATIONS)
        with database() as connection:
            cursor = connection.execute(
                "INSERT INTO users (username, name, salt, password_hash, state_json) VALUES (?, ?, ?, ?, ?)",
                (username, name.strip(), salt, password_hash, json.dumps(initial_state(), separators=(",", ":"))),
            )
            user = {"id": cursor.lastrowid, "username": username, "name": name.strip()}
        self.create_session(user["id"])
        self.send_json(201, {"user": self.public_user(user)}, self.session_cookie_headers())

    def login(self, body):
        username = body.get("username")
        password = body.get("password")
        if not isinstance(username, str) or not isinstance(password, str):
            raise ValueError("Enter your username and password.")
        with database() as connection:
            user = connection.execute(
                "SELECT id, username, name, salt, password_hash FROM users WHERE username = ?",
                (username,),
            ).fetchone()
        if not user:
            hashlib.pbkdf2_hmac("sha256", password.encode(), b"miniso-invalid-user", PASSWORD_ITERATIONS)
            self.send_json(401, {"error": "Username or password is incorrect."})
            return
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), user["salt"], PASSWORD_ITERATIONS)
        if not hmac.compare_digest(candidate, user["password_hash"]):
            self.send_json(401, {"error": "Username or password is incorrect."})
            return
        self.create_session(user["id"])
        self.send_json(200, {"user": self.public_user(user)}, self.session_cookie_headers())

    def logout(self):
        user, token = self.session_identity()
        if token:
            with database() as connection:
                connection.execute("DELETE FROM sessions WHERE token_hash = ?", (self.hash_token(token),))
        self.send_json(200, {"authenticated": False}, [("Set-Cookie", self.expired_cookie())])

    def create_session(self, user_id):
        token = secrets.token_urlsafe(32)
        with database() as connection:
            connection.execute("DELETE FROM sessions WHERE expires_at <= ?", (int(time.time()),))
            connection.execute(
                "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
                (self.hash_token(token), user_id, int(time.time()) + SESSION_DURATION),
            )
        self.pending_cookie = token

    def session_identity(self):
        cookie = SimpleCookie()
        cookie.load(self.headers.get("Cookie", ""))
        morsel = cookie.get(SESSION_COOKIE)
        token = morsel.value if morsel else None
        if not token:
            return None, None
        with database() as connection:
            user = connection.execute(
                """
                SELECT users.id, users.username, users.name
                FROM sessions JOIN users ON users.id = sessions.user_id
                WHERE sessions.token_hash = ? AND sessions.expires_at > ?
                """,
                (self.hash_token(token), int(time.time())),
            ).fetchone()
        return user, token

    def current_user(self):
        user, _ = self.session_identity()
        return user

    def require_user(self):
        user = self.current_user()
        if not user:
            self.send_json(401, {"error": "Please sign in to continue."})
        return user

    @staticmethod
    def public_user(user):
        return {"username": user["username"], "name": user["name"]}

    @staticmethod
    def hash_token(token):
        return hashlib.sha256(token.encode()).hexdigest()

    def session_cookie_headers(self):
        secure = "; Secure" if self.headers.get("X-Forwarded-Proto", "").lower() == "https" else ""
        cookie = (
            f"{SESSION_COOKIE}={self.pending_cookie}; Path=/; HttpOnly; SameSite=Lax"
            f"; Max-Age={SESSION_DURATION}{secure}"
        )
        return [("Set-Cookie", cookie)]

    def expired_cookie(self):
        secure = "; Secure" if self.headers.get("X-Forwarded-Proto", "").lower() == "https" else ""
        return f"{SESSION_COOKIE}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0{secure}"

    def check_origin(self):
        origin = self.headers.get("Origin")
        if not origin:
            return True
        expected_scheme = self.headers.get("X-Forwarded-Proto", "http").split(",")[0].strip()
        expected_host = self.headers.get("Host", "")
        received = urlsplit(origin)
        if received.scheme == expected_scheme and received.netloc == expected_host:
            return True
        self.send_json(403, {"error": "Cross-origin requests are not allowed."})
        return False

    def read_json(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as error:
            raise ValueError("Request length is invalid.") from error
        if length <= 0 or length > MAX_REQUEST_SIZE:
            raise ValueError("Request body is empty or too large.")
        try:
            body = json.loads(self.rfile.read(length))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("Request body must contain valid JSON.") from error
        if not isinstance(body, dict):
            raise ValueError("Request body must be a JSON object.")
        return body

    def send_json(self, status, payload, headers=None):
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for key, value in headers or []:
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def serve_static(self, url_path):
        decoded = unquote(url_path)
        relative = "index.html" if decoded in ("", "/") else decoded.lstrip("/")
        requested = (WEB_ROOT / relative).resolve()
        if not requested.is_relative_to(WEB_ROOT) or not requested.is_file():
            self.send_error(404, "Not found")
            return
        content = requested.read_bytes()
        content_type = mimetypes.guess_type(requested.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format_string, *args):
        print(f"{self.log_date_time_string()} {self.address_string()} {format_string % args}")


def main():
    initialize_database()
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), DashboardHandler)
    print(f"MINISO dashboard server listening on port {port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping dashboard server.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
