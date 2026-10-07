import csv
import hashlib
import hmac
import io
import json
import calendar
import mimetypes
import os
import secrets
import sqlite3
import threading
import time
from datetime import date, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

ROOT = Path(__file__).resolve().parent
WEB_ROOT = ROOT / "web"
DB_PATH = ROOT / "data" / "miniso.sqlite3"
PORT = int(os.environ.get("PORT", "8000"))
SESSION_TTL = 8 * 60 * 60
SESSIONS = {}
SESSION_LOCK = threading.Lock()
PASSWORD_ITERATIONS = 240_000
DEFAULT_RULES = [(70, 500), (90, 1000), (100, 2000), (110, 3500), (120, 5000)]


def connect_db():
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 10000")
    return connection


def hash_password(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS)
    return f"{salt.hex()}:{digest.hex()}"


def verify_password(password, stored):
    try:
        salt_hex, digest_hex = stored.split(":", 1)
        salt = bytes.fromhex(salt_hex)
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS)
        return hmac.compare_digest(candidate.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def initialize_database():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with connect_db() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS staff (
                staff_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                phone TEXT NOT NULL DEFAULT '',
                email TEXT NOT NULL DEFAULT '',
                department TEXT NOT NULL,
                joining_date TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Active',
                default_target REAL NOT NULL CHECK(default_target > 0),
                daily_target REAL NOT NULL CHECK(daily_target > 0),
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS targets (
                staff_id TEXT NOT NULL REFERENCES staff(staff_id) ON DELETE CASCADE,
                month TEXT NOT NULL,
                sales_target REAL NOT NULL CHECK(sales_target > 0),
                PRIMARY KEY(staff_id, month)
            );
            CREATE TABLE IF NOT EXISTS sales (
                sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
                staff_id TEXT NOT NULL REFERENCES staff(staff_id) ON DELETE CASCADE,
                sale_date TEXT NOT NULL,
                product TEXT NOT NULL,
                quantity INTEGER NOT NULL CHECK(quantity > 0),
                amount REAL NOT NULL CHECK(amount > 0),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS incentive_rules (
                min_achievement REAL PRIMARY KEY CHECK(min_achievement >= 0),
                incentive REAL NOT NULL CHECK(incentive >= 0)
            );
            CREATE TABLE IF NOT EXISTS incentive_approvals (
                staff_id TEXT NOT NULL REFERENCES staff(staff_id) ON DELETE CASCADE,
                period TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('Pending', 'Approved')),
                approved_by TEXT,
                approved_at TEXT,
                PRIMARY KEY(staff_id, period)
            );
            CREATE INDEX IF NOT EXISTS idx_sales_staff_date ON sales(staff_id, sale_date);
            """
        )
        columns = {row[1] for row in db.execute("PRAGMA table_info(staff)")}
        if "daily_target" not in columns:
            db.execute("ALTER TABLE staff ADD COLUMN daily_target REAL")
        current_month_days = calendar.monthrange(date.today().year, date.today().month)[1]
        if db.execute("SELECT COUNT(*) FROM staff WHERE daily_target IS NULL OR daily_target <= 0").fetchone()[0] > 0:
            db.execute("UPDATE staff SET daily_target=default_target / ? WHERE daily_target IS NULL OR daily_target <= 0", (current_month_days,))
        if db.execute("SELECT COUNT(*) FROM staff").fetchone()[0] == 0:
            month = date.today().strftime("%Y-%m")
            previous_months = []
            cursor = date.today().replace(day=1)
            for offset in range(3, 0, -1):
                year = cursor.year
                month_number = cursor.month - offset
                while month_number <= 0:
                    month_number += 12
                    year -= 1
                previous_months.append(date(year, month_number, 1).strftime("%Y-%m"))

            demo_staff = [
                ("S101", "Harsha Rao", "Sales", 4000, "harsha", "staff123"),
                ("S102", "Rahul Kumar", "Sales", 3600, "rahul", "staff123"),
                ("S103", "Priya Sharma", "Beauty", 3200, "priya", "staff123"),
                ("S104", "Ankit Verma", "Store", 3000, "ankit", "staff123"),
            ]
            for staff_id, name, department, daily_target, username, password in demo_staff:
                db.execute(
                    "INSERT INTO staff(staff_id,name,department,joining_date,default_target,daily_target,username,password_hash) VALUES(?,?,?,?,?,?,?)",
                    (staff_id, name, department, date.today().isoformat(), daily_target, daily_target, username, hash_password(password)),
                )
                for target_month in previous_months + [month]:
                    db.execute("INSERT INTO targets(staff_id,month,sales_target) VALUES(?,?,?)", (staff_id, target_month, daily_target))

            demo_sales = [
                ("S101", 1.26, "Water Bottle"), ("S101", 0.64, "Travel Bag"),
                ("S102", 1.08, "Toy Set"), ("S103", 0.96, "Beauty Kit"),
                ("S104", 0.51, "Storage Box"),
            ]
            for staff_id, factor, product in demo_sales:
                staff = next(row for row in demo_staff if row[0] == staff_id)
                amount = round(staff[3] * factor)
                db.execute(
                    "INSERT INTO sales(staff_id,sale_date,product,quantity,amount) VALUES(?,?,?,?,?)",
                    (staff_id, date.today().replace(day=max(1, min(5, date.today().day))).isoformat(), product, 1, amount),
                )
            db.execute(
                "INSERT INTO staff(staff_id,name,department,joining_date,default_target,daily_target,username,password_hash) VALUES(?,?,?,?,?,?,?)",
                ("ADMIN", "Store Administrator", "Management", date.today().isoformat(), 1, 1, "admin", hash_password("admin123")),
            )
            db.execute(
                "INSERT INTO staff(staff_id,name,department,joining_date,default_target,daily_target,username,password_hash) VALUES(?,?,?,?,?,?,?)",
                ("MANAGER", "Store Manager", "Management", date.today().isoformat(), 1, 1, "manager", hash_password("manager123")),
            )
        if db.execute("SELECT COUNT(*) FROM incentive_rules").fetchone()[0] == 0:
            db.executemany("INSERT INTO incentive_rules(min_achievement,incentive) VALUES(?,?)", DEFAULT_RULES)


def parse_period(period):
    today = date.today()
    if not period:
        period = today.strftime("%Y-%m")
    if len(period) == 7 and period[4:6] == "-Q" and period[6] in "1234":
        year = int(period[:4])
        first_month = (int(period[6]) - 1) * 3 + 1
        start = date(year, first_month, 1)
        end = date(year + (first_month == 10), 1 if first_month == 10 else first_month + 3, 1)
        months = [date(year, first_month + index, 1).strftime("%Y-%m") for index in range(3)]
        return period, start, end, months
    if len(period) == 7 and period[4] == "-":
        start = date.fromisoformat(period + "-01")
        if start.strftime("%Y-%m") != period:
            raise ValueError("Period must be a valid YYYY-MM month.")
        if start.month == 12:
            end = date(start.year + 1, 1, 1)
        else:
            end = date(start.year, start.month + 1, 1)
        return period, start, end, [period]
    raise ValueError("Period must be a month (YYYY-MM) or quarter (YYYY-Q1 to YYYY-Q4).")


def performance_level(achievement):
    if achievement >= 110:
        return "Excellent"
    if achievement >= 100:
        return "Good"
    if achievement >= 70:
        return "Average"
    return "Below Target"


def calculate_incentive(achievement, rules):
    eligible = [rule for rule in rules if achievement >= rule["minAchievement"]]
    return eligible[0]["incentive"] if eligible else 0


def build_report(db, period, actor, scope="overall", department=None, staff_filter=None):
    period, start, end, months = parse_period(period)
    parameters = [start.isoformat(), end.isoformat()]
    query = "SELECT staff_id,name,department,default_target,daily_target,status FROM staff WHERE status='Active' AND staff_id NOT IN ('ADMIN','MANAGER')"
    if actor["role"] == "staff":
        query += " AND staff_id=?"
        parameters.append(actor["staffId"])
    if staff_filter:
        query += " AND staff_id=?"
        parameters.append(staff_filter)
    if department:
        query += " AND department=?"
        parameters.append(department)
    query += " ORDER BY name COLLATE NOCASE"
    staff_rows = db.execute(query, parameters[2:]).fetchall()
    rule_rows = db.execute("SELECT min_achievement,incentive FROM incentive_rules ORDER BY min_achievement DESC").fetchall()
    rules = [{"minAchievement": row[0], "incentive": row[1]} for row in rule_rows]
    result = []
    for staff in staff_rows:
        sales = db.execute(
            "SELECT COALESCE(SUM(amount),0) FROM sales WHERE staff_id=? AND sale_date>=? AND sale_date<?",
            (staff["staff_id"], start.isoformat(), end.isoformat()),
        ).fetchone()[0]
        target = 0
        for month in months:
            month_start = date.fromisoformat(month + "-01")
            month_target = db.execute(
                "SELECT sales_target FROM targets WHERE staff_id=? AND month=?",
                (staff["staff_id"], month),
            ).fetchone()
            target += month_target[0] if month_target else staff["daily_target"] * calendar.monthrange(month_start.year, month_start.month)[1]
        achievement = (sales / target * 100) if target else 0
        approval = db.execute(
            "SELECT status,approved_by,approved_at FROM incentive_approvals WHERE staff_id=? AND period=?",
            (staff["staff_id"], period),
        ).fetchone()
        incentive = calculate_incentive(achievement, rules)
        result.append({
            "staffId": staff["staff_id"], "name": staff["name"], "department": staff["department"],
            "target": target, "sales": sales, "achievement": achievement,
            "level": performance_level(achievement), "incentive": incentive,
            "approval": approval["status"] if approval else "Pending",
            "approvedBy": approval["approved_by"] if approval else None,
            "months": len(months),
        })
    return period, start, end, months, result, rules


def dashboard_payload(db, actor, period):
    period, start, end, months, rows, rules = build_report(db, period, actor)
    total_sales = sum(row["sales"] for row in rows)
    total_target = sum(row["target"] for row in rows)
    total_incentive = sum(row["incentive"] for row in rows)
    average = total_sales / total_target * 100 if total_target else 0
    top = sorted(rows, key=lambda row: (-row["achievement"], row["name"]))[:5]
    alerts = []
    for row in rows:
        if row["achievement"] < 60:
            alerts.append({"tone": "critical", "message": f"{row['name']} is below 60% of target."})
        elif row["achievement"] < 75:
            alerts.append({"tone": "warning", "message": f"{row['name']} has reached {row['achievement']:.0f}% of target."})
        elif row["achievement"] >= 120:
            alerts.append({"tone": "success", "message": f"{row['name']} exceeded target by {row['achievement'] - 100:.0f}%."})
    qualified = sum(1 for row in rows if row["incentive"] > 0)

    trend = []
    trend_anchor = start.replace(day=1)
    for offset in range(5, -1, -1):
        year = trend_anchor.year
        month_number = trend_anchor.month - offset
        while month_number <= 0:
            month_number += 12
            year -= 1
        month_date = date(year, month_number, 1)
        month_key = month_date.strftime("%Y-%m")
        next_month = date(year + (month_date.month == 12), 1 if month_date.month == 12 else month_date.month + 1, 1)
        staff_filter = " AND staff_id=?" if actor["role"] == "staff" else " AND staff_id NOT IN ('ADMIN','MANAGER')"
        sales_parameters = (month_date.isoformat(), next_month.isoformat(), actor["staffId"]) if actor["role"] == "staff" else (month_date.isoformat(), next_month.isoformat())
        sales_total = db.execute(
            "SELECT COALESCE(SUM(amount),0) FROM sales WHERE sale_date>=? AND sale_date<?" + staff_filter,
            sales_parameters,
        ).fetchone()[0]
        target_filter = " AND s.staff_id=?" if actor["role"] == "staff" else " AND s.staff_id NOT IN ('ADMIN','MANAGER')"
        target_parameters = (actor["staffId"],) if actor["role"] == "staff" else ()
        target_total = db.execute(
            "SELECT COALESCE(SUM(COALESCE(s.daily_target, s.default_target)),0) FROM staff s WHERE s.status='Active'" + target_filter,
            target_parameters,
        ).fetchone()[0] * calendar.monthrange(month_date.year, month_date.month)[1]
        trend.append({"month": month_key, "sales": sales_total, "target": target_total})

    period_label = start.strftime("%B %Y") if len(period) == 7 and "Q" not in period else f"Q{period[-1]} {period[:4]}"
    return {
        "user": {"username": actor["username"], "name": actor["name"], "role": actor["role"], "staffId": actor["staffId"]},
        "period": period, "periodLabel": period_label, "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "stats": {"staff": len(rows), "sales": total_sales, "target": total_target, "achievement": average, "incentive": total_incentive, "qualified": qualified},
        "rows": rows, "leaderboard": top, "alerts": alerts, "trend": trend, "rules": rules,
    }


class AppHandler(BaseHTTPRequestHandler):
    server_version = "MinisoPerformance/1.0"

    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args))

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self';")
        super().end_headers()

    def send_json(self, data, status=200, headers=None):
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        if headers:
            for key, value in headers.items():
                self.send_header(key, value)
        self.end_headers()
        self.wfile.write(payload)

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length > 1_000_000:
            raise ValueError("Request is too large.")
        raw = self.rfile.read(length)
        if not raw:
            return {}
        value = json.loads(raw.decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("A JSON object is required.")
        return value

    def get_actor(self):
        cookie = self.headers.get("Cookie", "")
        session_id = None
        for part in cookie.split(";"):
            name, separator, value = part.strip().partition("=")
            if separator and name == "miniso_session":
                session_id = value
                break
        if not session_id:
            return None
        now = time.time()
        with SESSION_LOCK:
            for key, session in list(SESSIONS.items()):
                if session["expires"] <= now:
                    del SESSIONS[key]
            session = SESSIONS.get(session_id)
            if session:
                session["expires"] = now + SESSION_TTL
                return session["actor"]
        return None

    def require_actor(self, roles=None):
        actor = self.get_actor()
        if not actor:
            self.send_json({"error": "Please log in to continue."}, 401)
            return None
        if roles and actor["role"] not in roles:
            self.send_json({"error": "Your account does not have permission for this action."}, 403)
            return None
        return actor

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        if parsed.path.startswith("/api/"):
            self.handle_api_get(parsed.path, params)
            return
        self.serve_static(parsed.path)

    def do_POST(self):
        parsed = urlparse(self.path)
        if not parsed.path.startswith("/api/"):
            self.send_json({"error": "Not found."}, 404)
            return
        try:
            body = self.read_json()
            self.handle_api_post(parsed.path, body)
        except (ValueError, json.JSONDecodeError) as error:
            self.send_json({"error": str(error) or "Invalid request."}, 400)
        except sqlite3.IntegrityError as error:
            self.send_json({"error": "The record conflicts with existing data or contains invalid values."}, 409)
        except Exception as error:
            print("Request failed:", repr(error))
            self.send_json({"error": "The server could not complete the request."}, 500)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/staff/"):
            actor = self.require_actor(["admin"])
            if not actor:
                return
            staff_id = unquote(parsed.path.rsplit("/", 1)[-1])
            if staff_id in {"ADMIN", "MANAGER"}:
                self.send_json({"error": "System accounts cannot be removed."}, 400)
                return
            with connect_db() as db:
                cursor = db.execute("DELETE FROM staff WHERE staff_id=?", (staff_id,))
                if cursor.rowcount == 0:
                    self.send_json({"error": "Staff member not found."}, 404)
                    return
            self.send_json({"ok": True})
            return
        self.send_json({"error": "Not found."}, 404)

    def serve_static(self, requested):
        requested = unquote(requested)
        if requested == "/":
            requested = "/index.html"
        candidate = (WEB_ROOT / requested.lstrip("/")).resolve()
        if WEB_ROOT not in candidate.parents or not candidate.is_file():
            self.send_json({"error": "Not found."}, 404)
            return
        content = candidate.read_bytes()
        content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type in {"application/javascript", "application/json"}:
            content_type += "; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def handle_api_get(self, path, params):
        if path == "/api/session":
            actor = self.get_actor()
            self.send_json({"user": {"username": actor["username"], "name": actor["name"], "role": actor["role"], "staffId": actor["staffId"]} if actor else None})
            return
        actor = self.require_actor()
        if not actor:
            return
        period = params.get("period", [date.today().strftime("%Y-%m")])[0]
        try:
            if path == "/api/dashboard":
                with connect_db() as db:
                    self.send_json(dashboard_payload(db, actor, period))
                return
            if path == "/api/staff":
                if actor["role"] == "staff":
                    self.send_json({"rows": []})
                    return
                with connect_db() as db:
                    month = params.get("month", [date.today().strftime("%Y-%m")])[0]
                    rows = db.execute("SELECT s.staff_id,s.name,s.phone,s.email,s.department,s.joining_date,s.status,s.default_target,s.daily_target AS target,s.username FROM staff s WHERE s.status='Active' AND s.staff_id NOT IN ('ADMIN','MANAGER') ORDER BY s.name COLLATE NOCASE").fetchall()
                    self.send_json({"rows": [dict(row) for row in rows]})
                return
            if path == "/api/rules":
                if actor["role"] != "admin":
                    self.send_json({"error": "Only administrators can manage incentive rules."}, 403)
                    return
                with connect_db() as db:
                    rows = db.execute("SELECT min_achievement,incentive FROM incentive_rules ORDER BY min_achievement").fetchall()
                self.send_json({"rows": [{"minAchievement": row[0], "incentive": row[1]} for row in rows]})
                return
            if path == "/api/report":
                if actor["role"] == "staff":
                    staff_filter = actor["staffId"]
                    scope = "individual"
                else:
                    staff_filter = params.get("staffId", [None])[0]
                    scope = params.get("scope", ["overall"])[0]
                department = params.get("department", [None])[0]
                with connect_db() as db:
                    period, start, end, months, rows, rules = build_report(db, period, actor, scope, department, staff_filter)
                    total_sales = sum(row["sales"] for row in rows)
                    total_target = sum(row["target"] for row in rows)
                    payload = {"period": period, "periodLabel": start.strftime("%B %Y") if len(period) == 7 and "Q" not in period else f"Q{period[-1]} {period[:4]}", "generatedAt": datetime.now().isoformat(timespec="seconds"), "type": scope, "rows": rows, "summary": {"staff": len(rows), "sales": total_sales, "target": total_target, "achievement": total_sales / total_target * 100 if total_target else 0, "incentive": sum(row["incentive"] for row in rows)}}
                    self.send_json(payload)
                return
            if path.startswith("/api/profile/"):
                staff_id = unquote(path.rsplit("/", 1)[-1])
                if actor["role"] == "staff" and staff_id != actor["staffId"]:
                    self.send_json({"error": "You can only view your own profile."}, 403)
                    return
                with connect_db() as db:
                    period, start, end, months, rows, rules = build_report(db, period, actor, staff_filter=staff_id)
                    if not rows:
                        self.send_json({"error": "Staff member not found."}, 404)
                        return
                    history = []
                    anchor = start.replace(day=1)
                    for offset in range(5, -1, -1):
                        year = anchor.year
                        month_number = anchor.month - offset
                        while month_number <= 0:
                            month_number += 12
                            year -= 1
                        month_start = date(year, month_number, 1)
                        next_month = date(year + (month_start.month == 12), 1 if month_start.month == 12 else month_start.month + 1, 1)
                        sale_total = db.execute("SELECT COALESCE(SUM(amount),0) FROM sales WHERE staff_id=? AND sale_date>=? AND sale_date<?", (staff_id, month_start.isoformat(), next_month.isoformat())).fetchone()[0]
                        target_value = rows[0]["daily_target"] * calendar.monthrange(month_start.year, month_start.month)[1]
                        history.append({"label": month_start.strftime("%B %Y"), "sales": sale_total, "achievement": sale_total / target_value * 100 if target_value else 0})
                    self.send_json({"current": rows[0], "history": history})
                return
            if path == "/api/departments":
                with connect_db() as db:
                    rows = db.execute("SELECT DISTINCT department FROM staff WHERE status='Active' AND staff_id NOT IN ('ADMIN','MANAGER') ORDER BY department").fetchall()
                self.send_json({"rows": [row[0] for row in rows]})
                return
        except ValueError as error:
            self.send_json({"error": str(error)}, 400)
            return
        self.send_json({"error": "Not found."}, 404)

    def handle_api_post(self, path, body):
        if path == "/api/register":
            name = str(body.get("name", "")).strip()
            username = str(body.get("username", "")).strip().lower()
            password = str(body.get("password", ""))
            if len(name) < 2 or len(name) > 100:
                self.send_json({"error": "Enter a full name between 2 and 100 characters."}, 400)
                return
            if not username or len(username) < 3 or len(username) > 40 or not username.replace("_", "").replace("-", "").isalnum():
                self.send_json({"error": "Username must be 3-40 characters and contain only letters, numbers, underscores, or hyphens."}, 400)
                return
            if len(password) < 8:
                self.send_json({"error": "Password must contain at least 8 characters."}, 400)
                return
            with connect_db() as db:
                existing = db.execute("SELECT 1 FROM staff WHERE lower(username)=?", (username,)).fetchone()
                if existing:
                    self.send_json({"error": "That username is already registered."}, 409)
                    return
                staff_id = f"REG-{secrets.token_hex(4).upper()}"
                joining_date = date.today().isoformat()
                month = joining_date[:7]
                daily_target = 100000 / calendar.monthrange(date.today().year, date.today().month)[1]
                db.execute(
                    "INSERT INTO staff(staff_id,name,department,joining_date,default_target,daily_target,username,password_hash) VALUES(?,?,?,?,?,?,?,?)",
                    (staff_id, name, "General", joining_date, daily_target, daily_target, username, hash_password(password)),
                )
            actor = {"username": username, "name": name, "role": "staff", "staffId": staff_id}
            self.send_json({"user": actor}, status=201)
            return
        if path == "/api/login":
            username = str(body.get("username", "")).strip().lower()
            password = str(body.get("password", ""))
            if not username or not password:
                self.send_json({"error": "Enter both username and password."}, 400)
                return
            with connect_db() as db:
                row = db.execute("SELECT staff_id,name,username,password_hash FROM staff WHERE lower(username)=? AND status='Active'", (username,)).fetchone()
            if not row or not verify_password(password, row["password_hash"]):
                self.send_json({"error": "Username or password is incorrect."}, 401)
                return
            role = {"ADMIN": "admin", "MANAGER": "manager"}.get(row["staff_id"], "staff")
            session_id = secrets.token_urlsafe(32)
            actor = {"username": row["username"], "name": row["name"], "role": role, "staffId": row["staff_id"]}
            with SESSION_LOCK:
                SESSIONS[session_id] = {"actor": actor, "expires": time.time() + SESSION_TTL}
            self.send_json({"user": actor}, headers={"Set-Cookie": f"miniso_session={session_id}; HttpOnly; SameSite=Strict; Path=/; Max-Age={SESSION_TTL}"})
            return
        if path == "/api/logout":
            cookie = self.headers.get("Cookie", "")
            session_id = next((part.strip().split("=", 1)[1] for part in cookie.split(";") if part.strip().startswith("miniso_session=")), None)
            if session_id:
                with SESSION_LOCK:
                    SESSIONS.pop(session_id, None)
            self.send_json({"ok": True}, headers={"Set-Cookie": "miniso_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0"})
            return
        actor = self.require_actor()
        if not actor:
            return
        if path == "/api/staff":
            if actor["role"] != "admin":
                self.send_json({"error": "Only administrators can add staff."}, 403)
                return
            name = str(body.get("name", "")).strip()
            department = str(body.get("department", "")).strip()
            username = str(body.get("username", "")).strip().lower()
            password = str(body.get("password", ""))
            phone = str(body.get("phone", "")).strip()
            email = str(body.get("email", "")).strip()
            target = float(body.get("target", 0))
            if not name or not department or not username or len(password) < 8 or target <= 0:
                self.send_json({"error": "Enter all required values, a positive daily target, and a password of at least 8 characters."}, 400)
                return
            staff_id = f"S{secrets.token_hex(4).upper()}"
            joining_date = date.today().isoformat()
            with connect_db() as db:
                if db.execute("SELECT 1 FROM staff WHERE lower(username)=?", (username,)).fetchone():
                    self.send_json({"error": "That username is already registered."}, 409)
                    return
                db.execute("INSERT INTO staff(staff_id,name,phone,email,department,joining_date,default_target,daily_target,username,password_hash) VALUES(?,?,?,?,?,?,?,?,?,?)", (staff_id,name,phone,email,department,joining_date,target,target,username,hash_password(password)))
            self.send_json({"ok": True, "staffId": staff_id}, 201)
            return
        if path == "/api/target":
            if actor["role"] != "admin":
                self.send_json({"error": "Only administrators can set sales targets."}, 403)
                return
            staff_id = str(body.get("staffId", "")).strip().upper()
            target = float(body.get("target", 0))
            if target <= 0:
                self.send_json({"error": "The daily target must be positive."}, 400)
                return
            with connect_db() as db:
                exists = db.execute("SELECT 1 FROM staff WHERE staff_id=? AND status='Active' AND staff_id NOT IN ('ADMIN','MANAGER')", (staff_id,)).fetchone()
                if not exists:
                    self.send_json({"error": "Staff member not found."}, 404)
                    return
                db.execute("UPDATE staff SET default_target=?, daily_target=? WHERE staff_id=?", (target, target, staff_id))
            self.send_json({"ok": True})
            return
        if path == "/api/sales":
            if actor["role"] != "staff":
                self.send_json({"error": "Only staff accounts can enter sales."}, 403)
                return
            try:
                sale_date = date.fromisoformat(str(body.get("date", "")))
                quantity = int(body.get("quantity", 0))
                amount = float(body.get("amount", 0))
            except (ValueError, TypeError):
                self.send_json({"error": "Enter a valid date, quantity, and amount."}, 400)
                return
            product = str(body.get("product", "")).strip()
            if not product or quantity <= 0 or amount <= 0:
                self.send_json({"error": "Product, quantity, and a positive sale amount are required."}, 400)
                return
            if sale_date > date.today():
                self.send_json({"error": "Sales date cannot be in the future."}, 400)
                return
            with connect_db() as db:
                db.execute("INSERT INTO sales(staff_id,sale_date,product,quantity,amount) VALUES(?,?,?,?,?)", (actor["staffId"],sale_date.isoformat(),product,quantity,amount))
            self.send_json({"ok": True}, 201)
            return
        if path == "/api/rules":
            if actor["role"] != "admin":
                self.send_json({"error": "Only administrators can configure incentive rules."}, 403)
                return
            rules = body.get("rules")
            if not isinstance(rules, list) or not rules:
                self.send_json({"error": "Provide at least one incentive tier."}, 400)
                return
            try:
                cleaned = [(float(item["minAchievement"]), float(item["incentive"])) for item in rules]
            except (KeyError, TypeError, ValueError):
                self.send_json({"error": "Each tier needs a valid achievement percentage and incentive amount."}, 400)
                return
            if any(minimum < 0 or amount < 0 for minimum, amount in cleaned) or len({minimum for minimum, _ in cleaned}) != len(cleaned):
                self.send_json({"error": "Tier percentages must be unique and values cannot be negative."}, 400)
                return
            with connect_db() as db:
                db.execute("DELETE FROM incentive_rules")
                db.executemany("INSERT INTO incentive_rules(min_achievement,incentive) VALUES(?,?)", cleaned)
            self.send_json({"ok": True})
            return
        if path == "/api/approval":
            if actor["role"] not in {"admin", "manager"}:
                self.send_json({"error": "Only managers or administrators can approve incentives."}, 403)
                return
            staff_id = str(body.get("staffId", ""))
            period = str(body.get("period", ""))
            approved = bool(body.get("approved", False))
            if not approved:
                self.send_json({"error": "An approval action must be confirmed."}, 400)
                return
            try:
                parse_period(period)
            except ValueError as error:
                self.send_json({"error": str(error)}, 400)
                return
            with connect_db() as db:
                exists = db.execute("SELECT 1 FROM staff WHERE staff_id=? AND status='Active'", (staff_id,)).fetchone()
                if not exists:
                    self.send_json({"error": "Staff member not found."}, 404)
                    return
                db.execute("INSERT INTO incentive_approvals(staff_id,period,status,approved_by,approved_at) VALUES(?,?,'Approved',?,?) ON CONFLICT(staff_id,period) DO UPDATE SET status='Approved',approved_by=excluded.approved_by,approved_at=excluded.approved_at", (staff_id,period,actor["name"],datetime.now().isoformat(timespec="seconds")))
            self.send_json({"ok": True})
            return
        self.send_json({"error": "Not found."}, 404)

    def do_OPTIONS(self):
        self.send_json({"error": "Method not allowed."}, 405)


def main():
    initialize_database()
    server = ThreadingHTTPServer(("127.0.0.1", PORT), AppHandler)
    print(f"MINISO dashboard: http://localhost:{PORT}")
    print("Demo logins: admin/admin123, manager/manager123, harsha/staff123")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping MINISO dashboard.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
