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
from urllib.parse import parse_qs, unquote, urlsplit


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
                state_json TEXT NOT NULL,
                company_id INTEGER REFERENCES companies(id),
                role TEXT NOT NULL DEFAULT 'admin'
            );
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                state_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                expires_at INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS sessions_expiry ON sessions(expires_at);
            CREATE TABLE IF NOT EXISTS invitations (
                token_hash TEXT PRIMARY KEY,
                company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
                role TEXT NOT NULL CHECK (role IN ('manager', 'staff')),
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at INTEGER NOT NULL,
                expires_at INTEGER NOT NULL,
                used_at INTEGER
            );
            """
        )
        user_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(users)")
        }
        if "company_id" not in user_columns:
            connection.execute("ALTER TABLE users ADD COLUMN company_id INTEGER REFERENCES companies(id)")
        if "role" not in user_columns:
            connection.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'admin'")
        for user in connection.execute(
            "SELECT id, name, state_json FROM users WHERE company_id IS NULL"
        ).fetchall():
            cursor = connection.execute(
                "INSERT INTO companies (name, state_json) VALUES (?, ?)",
                (f"{user['name']}'s company", user["state_json"]),
            )
            connection.execute(
                "UPDATE users SET company_id = ? WHERE id = ?",
                (cursor.lastrowid, user["id"]),
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
        "attendance": [],
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
    attendance = value.get("attendance", [])
    rules = value.get("rules")
    if not all(isinstance(items, list) for items in (staff, targets, sales, attendance, rules)):
        raise ValueError("Dashboard data is missing staff, targets, sales, attendance, or rules.")
    if len(staff) > 5000 or len(targets) > 50000 or len(sales) > 100000 or len(attendance) > 100000 or len(rules) != 4:
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

    clean_attendance = []
    attendance_keys = set()
    for record in attendance:
        if not isinstance(record, dict):
            raise ValueError("Each attendance record must be an object.")
        staff_id = _text(record.get("staffId"), "Attendance staff ID", 40)
        date = record.get("date")
        status = record.get("status")
        if (
            staff_id not in staff_ids
            or not isinstance(date, str)
            or not DATE_PATTERN.fullmatch(date)
            or status not in ("Present", "Absent", "Half Day", "Leave")
            or (staff_id, date) in attendance_keys
        ):
            raise ValueError("Attendance staff, date, status, or duplicate record is invalid.")
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError as error:
            raise ValueError("Attendance date is invalid.") from error
        attendance_keys.add((staff_id, date))
        clean_attendance.append({"staffId": staff_id, "date": date, "status": status})

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
    return {
        "staff": clean_staff,
        "targets": clean_targets,
        "sales": clean_sales,
        "attendance": clean_attendance,
        "rules": clean_rules,
    }


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
        parsed_path = urlsplit(self.path)
        path = parsed_path.path
        if path == "/api/session":
            user = self.current_user()
            self.send_json(200, {"authenticated": user is not None, "user": self.public_user(user) if user else None})
        elif path == "/api/state":
            user = self.require_user()
            if user:
                state = self.load_company_state(user)
                if state is not None:
                    self.send_json(200, state)
        elif path in ("/api/staff", "/api/sales"):
            user = self.require_user()
            if user:
                state = self.load_company_state(user)
                if state is not None:
                    key = path.rsplit("/", 1)[-1]
                    self.send_json(200, {key: state[key]})
        elif path == "/api/reports/monthly":
            user = self.require_user()
            if user:
                month = parse_qs(parsed_path.query).get("month", [datetime.now().strftime("%Y-%m")])[0]
                try:
                    state = self.load_company_state(user)
                    if state is None:
                        return
                    report = self.monthly_report(state, month)
                except ValueError as error:
                    self.send_json(400, {"error": str(error)})
                    return
                if report is not None:
                    self.send_json(200, report)
        elif path == "/api/company/members":
            user = self.require_role(("admin", "manager"))
            if user:
                with database() as connection:
                    members = connection.execute(
                        "SELECT username, name, role FROM users WHERE company_id = ? ORDER BY name COLLATE NOCASE",
                        (user["company_id"],),
                    ).fetchall()
                self.send_json(200, {"members": [dict(member) for member in members]})
        elif path == "/api/company/invitations":
            user = self.require_role(("admin", "manager"))
            if user:
                with database() as connection:
                    invitations = connection.execute(
                        """
                        SELECT role, created_at, expires_at, used_at
                        FROM invitations
                        WHERE company_id = ? AND expires_at > ? AND used_at IS NULL
                        ORDER BY created_at DESC
                        """,
                        (user["company_id"], int(time.time())),
                    ).fetchall()
                self.send_json(200, {"invitations": [dict(invitation) for invitation in invitations]})
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
            elif path == "/api/company/invitations":
                user = self.require_role(("admin", "manager"))
                if user:
                    self.create_invitation(user, body)
            elif path == "/api/staff":
                user = self.require_role(("admin", "manager"))
                if user:
                    self.create_staff(user, body)
            elif path == "/api/sales":
                user = self.require_role(("admin", "manager"))
                if user:
                    self.create_sale(user, body)
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
        path = urlsplit(self.path).path
        if path.startswith("/api/staff/") or path.startswith("/api/sales/"):
            if not self.check_origin():
                return
            user = self.require_role(("admin", "manager"))
            if not user:
                return
            try:
                item_id = unquote(path.rsplit("/", 1)[-1])
                if path.startswith("/api/staff/"):
                    self.update_staff(user, item_id, self.read_json())
                else:
                    self.update_sale(user, item_id, self.read_json())
            except ValueError as error:
                self.send_json(400, {"error": str(error)})
            except Exception:
                traceback.print_exc()
                self.send_json(500, {"error": "The server could not update this record."})
            return
        if path != "/api/state":
            self.send_json(404, {"error": "API endpoint not found."})
            return
        if not self.check_origin():
            return
        user = self.require_role(("admin", "manager"))
        if not user:
            return
        try:
            state = validate_state(self.read_json())
            with database() as connection:
                connection.execute(
                    "UPDATE companies SET state_json = ? WHERE id = ?",
                    (json.dumps(state, separators=(",", ":")), user["company_id"]),
                )
            self.send_json(200, {"saved": True})
        except ValueError as error:
            self.send_json(400, {"error": str(error)})
        except Exception:
            traceback.print_exc()
            self.send_json(500, {"error": "The server could not save dashboard data."})

    def do_DELETE(self):
        path = urlsplit(self.path).path
        if not (path.startswith("/api/staff/") or path.startswith("/api/sales/")):
            self.send_json(404, {"error": "API endpoint not found."})
            return
        if not self.check_origin():
            return
        user = self.require_role(("admin", "manager"))
        if not user:
            return
        try:
            item_id = unquote(path.rsplit("/", 1)[-1])
            if path.startswith("/api/staff/"):
                self.delete_staff(user, item_id)
            else:
                self.delete_sale(user, item_id)
        except ValueError as error:
            self.send_json(409, {"error": str(error)})
        except Exception:
            traceback.print_exc()
            self.send_json(500, {"error": "The server could not delete this record."})

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
        company_name = body.get("companyName")
        if company_name is not None and not isinstance(company_name, str):
            raise ValueError("Company name is invalid.")
        if isinstance(company_name, str) and company_name.strip():
            company_name = _text(company_name, "Company name", 80)
        else:
            company_name = f"{name.strip()}'s company"
        invite_token = body.get("inviteToken")
        if isinstance(invite_token, str) and not invite_token.strip():
            invite_token = None
        elif invite_token is not None and (not isinstance(invite_token, str) or not 20 <= len(invite_token) <= 128):
            raise ValueError("Invitation token is invalid.")
        salt = secrets.token_bytes(16)
        password_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PASSWORD_ITERATIONS)
        with database() as connection:
            company_id = None
            role = "admin"
            invitation = None
            if invite_token:
                invitation = connection.execute(
                    """
                    SELECT company_id, role FROM invitations
                    WHERE token_hash = ? AND used_at IS NULL AND expires_at > ?
                    """,
                    (self.hash_token(invite_token), int(time.time())),
                ).fetchone()
                if not invitation:
                    raise ValueError("Invitation is invalid, expired, or already used.")
                company_id = invitation["company_id"]
                role = invitation["role"]
            else:
                cursor = connection.execute(
                    "INSERT INTO companies (name, state_json) VALUES (?, ?)",
                    (company_name, json.dumps(initial_state(), separators=(",", ":"))),
                )
                company_id = cursor.lastrowid
            cursor = connection.execute(
                """
                INSERT INTO users (username, name, salt, password_hash, state_json, company_id, role)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (username, name.strip(), salt, password_hash, json.dumps(initial_state(), separators=(",", ":")), company_id, role),
            )
            user_id = cursor.lastrowid
            if invitation:
                updated = connection.execute(
                    "UPDATE invitations SET used_at = ? WHERE token_hash = ? AND used_at IS NULL AND expires_at > ?",
                    (int(time.time()), self.hash_token(invite_token), int(time.time())),
                )
                if updated.rowcount != 1:
                    raise ValueError("Invitation has already been used.")
            user = {
                "id": user_id,
                "username": username,
                "name": name.strip(),
                "company_id": company_id,
                "company_name": company_name if not invitation else None,
                "role": role,
            }
            if invitation:
                company = connection.execute(
                    "SELECT name FROM companies WHERE id = ?",
                    (company_id,),
                ).fetchone()
                user["company_name"] = company["name"]
        self.create_session(user["id"])
        self.send_json(201, {"user": self.public_user(user)}, self.session_cookie_headers())

    def login(self, body):
        username = body.get("username")
        password = body.get("password")
        if not isinstance(username, str) or not isinstance(password, str):
            raise ValueError("Enter your username and password.")
        with database() as connection:
            user = connection.execute(
                """
                SELECT users.id, users.username, users.name, users.salt, users.password_hash,
                       users.company_id, users.role, companies.name AS company_name
                FROM users JOIN companies ON companies.id = users.company_id
                WHERE users.username = ?
                """,
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
                SELECT users.id, users.username, users.name, users.company_id,
                       users.role, companies.name AS company_name
                FROM sessions
                JOIN users ON users.id = sessions.user_id
                JOIN companies ON companies.id = users.company_id
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

    def require_role(self, roles):
        user = self.require_user()
        if user and user["role"] not in roles:
            self.send_json(403, {"error": "Your role does not have permission to perform this action."})
            return None
        return user

    @staticmethod
    def public_user(user):
        return {
            "username": user["username"],
            "name": user["name"],
            "companyName": user["company_name"],
            "role": user["role"],
        }

    def load_company_state(self, user):
        with database() as connection:
            row = connection.execute(
                "SELECT state_json FROM companies WHERE id = ?",
                (user["company_id"],),
            ).fetchone()
        try:
            saved_state = json.loads(row["state_json"])
            if isinstance(saved_state, str):
                saved_state = json.loads(saved_state)
            return validate_state(saved_state)
        except (TypeError, ValueError, json.JSONDecodeError, KeyError):
            print(f"Invalid saved dashboard state for company {user['company_id']}.")
            self.send_json(500, {"error": "Saved dashboard data is invalid and could not be loaded."})
            return None

    @staticmethod
    def monthly_report(state, month):
        if not isinstance(month, str) or not MONTH_PATTERN.fullmatch(month):
            raise ValueError("Month must use YYYY-MM format.")
        try:
            datetime.strptime(month, "%Y-%m")
        except ValueError as error:
            raise ValueError("Month is invalid.") from error
        sales = [
            sale for sale in state["sales"]
            if sale["date"].startswith(month) and sale["paymentStatus"] == "Completed"
        ]
        staff_reports = []
        for person in state["staff"]:
            target = next(
                (item["amount"] for item in state["targets"]
                 if item["staffId"] == person["id"] and item["month"] == month),
                person["defaultTarget"],
            )
            amount = sum(sale["amount"] for sale in sales if sale["staffId"] == person["id"])
            achievement = amount / target * 100 if target else 0
            reward = max(
                (rule["reward"] for rule in state["rules"] if achievement >= rule["threshold"]),
                default=0,
            )
            staff_reports.append({
                "staffId": person["id"],
                "name": person["name"],
                "target": target,
                "sales": amount,
                "achievementPercent": round(achievement, 2),
                "incentive": reward,
            })
        return {
            "month": month,
            "totalSales": sum(sale["amount"] for sale in sales),
            "saleCount": len(sales),
            "unitsSold": sum(sale["quantity"] for sale in sales),
            "staff": staff_reports,
        }

    def save_company_state(self, user, state):
        with database() as connection:
            connection.execute(
                "UPDATE companies SET state_json = ? WHERE id = ?",
                (json.dumps(state, separators=(",", ":")), user["company_id"]),
            )

    def create_invitation(self, user, body):
        role = body.get("role")
        if role not in ("manager", "staff"):
            raise ValueError("Invitations can only be created for manager or staff roles.")
        if user["role"] == "manager" and role != "staff":
            self.send_json(403, {"error": "Managers can only invite staff members."})
            return
        expires_in_hours = body.get("expiresInHours", 24)
        if isinstance(expires_in_hours, bool) or not isinstance(expires_in_hours, int) or not 1 <= expires_in_hours <= 168:
            raise ValueError("Invitation expiry must be between 1 and 168 hours.")
        token = secrets.token_urlsafe(32)
        now = int(time.time())
        with database() as connection:
            connection.execute(
                """
                INSERT INTO invitations (token_hash, company_id, role, created_by, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    self.hash_token(token),
                    user["company_id"],
                    role,
                    user["id"],
                    now,
                    now + expires_in_hours * 60 * 60,
                ),
            )
        self.send_json(201, {
            "invitation": {
                "token": token,
                "role": role,
                "expiresAt": now + expires_in_hours * 60 * 60,
            },
        })

    def create_staff(self, user, body):
        state = self.load_company_state(user)
        if state is None:
            return
        staff_id = body.get("id")
        if staff_id is None:
            staff_id = self.next_id("S", (person["id"] for person in state["staff"]))
        person = {
            "id": staff_id,
            "name": body.get("name"),
            "department": body.get("department"),
            "status": body.get("status", "Active"),
            "defaultTarget": body.get("defaultTarget", 0),
        }
        updated = validate_state({**state, "staff": [*state["staff"], person]})
        saved = updated["staff"][-1]
        self.save_company_state(user, updated)
        self.send_json(201, {"staff": saved})

    def update_staff(self, user, staff_id, body):
        state = self.load_company_state(user)
        if state is None:
            return
        for index, person in enumerate(state["staff"]):
            if person["id"] == staff_id:
                updated_person = {**person, **body, "id": staff_id}
                state["staff"][index] = updated_person
                updated = validate_state(state)
                self.save_company_state(user, updated)
                self.send_json(200, {"staff": updated["staff"][index]})
                return
        self.send_json(404, {"error": "Staff member not found."})

    def delete_staff(self, user, staff_id):
        state = self.load_company_state(user)
        if state is None:
            return
        if not any(person["id"] == staff_id for person in state["staff"]):
            self.send_json(404, {"error": "Staff member not found."})
            return
        related = any(
            record["staffId"] == staff_id
            for key in ("targets", "sales", "attendance")
            for record in state[key]
        )
        if related:
            raise ValueError("Staff with sales, targets, or attendance records cannot be deleted.")
        state["staff"] = [person for person in state["staff"] if person["id"] != staff_id]
        self.save_company_state(user, state)
        self.send_json(200, {"deleted": True})

    def create_sale(self, user, body):
        state = self.load_company_state(user)
        if state is None:
            return
        sale_id = body.get("id")
        if sale_id is None:
            sale_id = self.next_id("SALE", (sale["id"] for sale in state["sales"]))
        sale = {
            "id": sale_id,
            "staffId": body.get("staffId"),
            "date": body.get("date"),
            "product": body.get("product"),
            "quantity": body.get("quantity"),
            "amount": body.get("amount"),
            "paymentStatus": body.get("paymentStatus", "Completed"),
        }
        updated = validate_state({**state, "sales": [*state["sales"], sale]})
        saved = updated["sales"][-1]
        self.save_company_state(user, updated)
        self.send_json(201, {"sale": saved})

    def update_sale(self, user, sale_id, body):
        state = self.load_company_state(user)
        if state is None:
            return
        for index, sale in enumerate(state["sales"]):
            if sale["id"] == sale_id:
                updated_sale = {**sale, **body, "id": sale_id}
                state["sales"][index] = updated_sale
                updated = validate_state(state)
                self.save_company_state(user, updated)
                self.send_json(200, {"sale": updated["sales"][index]})
                return
        self.send_json(404, {"error": "Sale not found."})

    def delete_sale(self, user, sale_id):
        state = self.load_company_state(user)
        if state is None:
            return
        if not any(sale["id"] == sale_id for sale in state["sales"]):
            self.send_json(404, {"error": "Sale not found."})
            return
        state["sales"] = [sale for sale in state["sales"] if sale["id"] != sale_id]
        self.save_company_state(user, state)
        self.send_json(200, {"deleted": True})

    @staticmethod
    def next_id(prefix, existing_ids):
        used = set()
        for value in existing_ids:
            match = re.fullmatch(rf"{re.escape(prefix)}(\d+)", value)
            if match:
                used.add(int(match.group(1)))
        return f"{prefix}{max(used, default=0) + 1:03d}"

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
        self.send_header("Cache-Control", "no-store")
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
