import json
import sqlite3
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path

import server


class DashboardServerTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.original_database_path = server.DATABASE_PATH
        server.DATABASE_PATH = Path(self.temp_directory.name) / "test.sqlite3"
        server.initialize_database()
        self.httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.DashboardHandler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.httpd.server_port}"
        self.client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join()
        server.DATABASE_PATH = self.original_database_path
        self.temp_directory.cleanup()

    def request(self, path, method="GET", payload=None, client=None, headers=None):
        data = json.dumps(payload).encode() if payload is not None else None
        request = urllib.request.Request(
            self.base_url + path,
            data=data,
            method=method,
            headers={"Content-Type": "application/json", **(headers or {})},
        )
        try:
            response = (client or self.client).open(request)
        except urllib.error.HTTPError as error:
            response = error
        return response.status, json.loads(response.read()), response.headers

    def register(self, client, username):
        return self.request(
            "/api/register",
            "POST",
            {"name": username.title(), "username": username, "password": "correct horse battery"},
            client,
        )

    def test_registration_login_and_dashboard_data_are_server_persisted_and_isolated(self):
        status, registered, headers = self.register(self.client, "first_user")
        self.assertEqual(status, 201)
        self.assertEqual(headers.get_content_type(), "application/json")
        self.assertEqual(registered["user"]["username"], "first_user")
        self.assertIn("HttpOnly", headers["Set-Cookie"])
        self.assertIn("SameSite=Lax", headers["Set-Cookie"])

        status, first_state, _ = self.request("/api/state")
        self.assertEqual(status, 200)
        first_state["sales"][0]["amount"] = 4321
        self.assertEqual(self.request("/api/state", "PUT", first_state)[0], 200)

        second_client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))
        self.assertEqual(self.register(second_client, "second_user")[0], 201)
        status, second_state, _ = self.request("/api/state", client=second_client)
        self.assertEqual(status, 200)
        self.assertNotEqual(second_state["sales"][0]["amount"], 4321)

        self.assertEqual(self.request("/api/logout", "POST", {}, self.client)[0], 200)
        self.assertFalse(self.request("/api/session")[1]["authenticated"])
        self.assertEqual(
            self.request(
                "/api/login",
                "POST",
                {"username": "first_user", "password": "correct horse battery"},
            )[0],
            200,
        )
        status, restored_state, _ = self.request("/api/state")
        self.assertEqual(status, 200)
        self.assertEqual(restored_state["sales"][0]["amount"], 4321)

    def test_rejects_unauthorized_cross_origin_and_invalid_dashboard_updates(self):
        self.assertEqual(self.request("/api/state")[0], 401)
        self.assertEqual(
            self.request(
                "/api/register",
                "POST",
                {"name": "Test User", "username": "valid_user", "password": "correct horse battery"},
                headers={"Origin": "https://attacker.example"},
            )[0],
            403,
        )
        self.register(self.client, "valid_user")
        status, payload, _ = self.request("/api/state", "PUT", {"staff": []})
        self.assertEqual(status, 400)
        self.assertIn("missing staff", payload["error"])
        _, state, _ = self.request("/api/state")
        state["targets"][0]["amount"] = 0
        status, payload, _ = self.request("/api/state", "PUT", state)
        self.assertEqual(status, 400)
        self.assertIn("Target amount", payload["error"])
        self.assertEqual(
            self.request(
                "/api/login",
                "POST",
                {"username": "valid_user", "password": "incorrect password"},
            )[0],
            401,
        )

    def test_duplicate_registration_is_rejected(self):
        self.assertEqual(self.register(self.client, "duplicate")[0], 201)
        other_client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))
        status, payload, _ = self.register(other_client, "duplicate")
        self.assertEqual(status, 409)
        self.assertIn("already registered", payload["error"])

    def test_company_invitations_share_records_and_enforce_roles(self):
        status, owner, _ = self.register(self.client, "company_owner")
        self.assertEqual(status, 201)
        self.assertEqual(owner["user"]["role"], "admin")

        status, invitation, _ = self.request(
            "/api/company/invitations",
            "POST",
            {"role": "manager"},
        )
        self.assertEqual(status, 201)
        token = invitation["invitation"]["token"]

        manager_client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))
        status, manager, _ = self.request(
            "/api/register",
            "POST",
            {
                "name": "Company Manager",
                "username": "company_manager",
                "password": "correct horse battery",
                "inviteToken": token,
            },
            manager_client,
        )
        self.assertEqual(status, 201)
        self.assertEqual(manager["user"]["role"], "manager")
        self.assertEqual(manager["user"]["companyName"], owner["user"]["companyName"])
        self.assertEqual(
            self.request(
                "/api/company/invitations",
                "POST",
                {"role": "manager"},
                manager_client,
            )[0],
            403,
        )
        _, members, _ = self.request("/api/company/members", client=manager_client)
        self.assertEqual(sorted(member["role"] for member in members["members"]), ["admin", "manager"])

        status, created_staff, _ = self.request(
            "/api/staff",
            "POST",
            {"name": "New Employee", "department": "Sales", "defaultTarget": 1000},
            manager_client,
        )
        self.assertEqual(status, 201)
        self.assertEqual(created_staff["staff"]["id"], "S004")
        _, shared_staff, _ = self.request("/api/staff")
        self.assertEqual(shared_staff["staff"][-1]["name"], "New Employee")

        staff_invitation_status, staff_invitation, _ = self.request(
            "/api/company/invitations",
            "POST",
            {"role": "staff"},
            manager_client,
        )
        self.assertEqual(staff_invitation_status, 201)
        staff_client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))
        status, staff_user, _ = self.request(
            "/api/register",
            "POST",
            {
                "name": "Read Only Employee",
                "username": "readonly_employee",
                "password": "correct horse battery",
                "inviteToken": staff_invitation["invitation"]["token"],
            },
            staff_client,
        )
        self.assertEqual(status, 201)
        self.assertEqual(staff_user["user"]["role"], "staff")
        status, initial, _ = self.request("/api/state", client=staff_client)
        self.assertEqual(status, 200)
        self.assertEqual(self.request("/api/state", "PUT", initial, staff_client)[0], 403)
        self.assertEqual(
            self.request(
                "/api/staff",
                "POST",
                {"name": "Blocked Employee", "department": "Sales", "defaultTarget": 0},
                staff_client,
            )[0],
            403,
        )
        report_month = initial["targets"][0]["month"]
        status, report, _ = self.request(f"/api/reports/monthly?month={report_month}", client=staff_client)
        self.assertEqual(status, 200)
        self.assertGreater(report["totalSales"], 0)

        other_client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))
        self.assertEqual(self.register(other_client, "private_company")[0], 201)
        _, isolated_staff, _ = self.request("/api/staff", client=other_client)
        self.assertEqual(len(isolated_staff["staff"]), 3)

        self.assertEqual(
            self.request(
                "/api/register",
                "POST",
                {
                    "name": "Duplicate Invitation",
                    "username": "duplicate_invite",
                    "password": "correct horse battery",
                    "inviteToken": token,
                },
                urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar())),
            )[0],
            400,
        )

    def test_staff_and_sales_crud_and_monthly_report(self):
        self.register(self.client, "crud_manager")
        status, staff, _ = self.request(
            "/api/staff",
            "POST",
            {"name": "CRUD Employee", "department": "Sales", "defaultTarget": 1000},
        )
        self.assertEqual(status, 201)
        staff_id = staff["staff"]["id"]
        self.assertEqual(
            self.request(
                f"/api/staff/{staff_id}",
                "PUT",
                {"name": "Updated Employee", "department": "Retail", "status": "Active", "defaultTarget": 2000},
            )[0],
            200,
        )
        month = self.request("/api/state")[1]["targets"][0]["month"]
        status, sale, _ = self.request(
            "/api/sales",
            "POST",
            {
                "staffId": staff_id,
                "date": f"{month}-02",
                "product": "Test Product",
                "quantity": 2,
                "amount": 1500,
                "paymentStatus": "Completed",
            },
        )
        self.assertEqual(status, 201)
        sale_id = sale["sale"]["id"]
        status, report, _ = self.request(f"/api/reports/monthly?month={month}")
        self.assertEqual(status, 200)
        self.assertEqual(report["totalSales"], 256500)
        self.assertEqual(report["unitsSold"], 9)
        self.assertEqual(
            self.request(
                f"/api/sales/{sale_id}",
                "PUT",
                {"amount": 2000, "paymentStatus": "Pending"},
            )[0],
            200,
        )
        status, report, _ = self.request(f"/api/reports/monthly?month={month}")
        self.assertEqual(status, 200)
        self.assertEqual(report["totalSales"], 255000)
        self.assertEqual(self.request(f"/api/staff/{staff_id}", "DELETE")[0], 409)
        self.assertEqual(self.request(f"/api/sales/{sale_id}", "DELETE")[0], 200)
        self.assertEqual(self.request(f"/api/staff/{staff_id}", "DELETE")[0], 200)
        self.assertEqual(self.request("/api/reports/monthly?month=2026-13")[0], 400)

    def test_static_dashboard_is_served_by_backend(self):
        response = self.client.open(self.base_url + "/")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.headers.get_content_type(), "text/html")
        self.assertEqual(response.headers.get("Cache-Control"), "no-store")
        self.assertIn("MINISO Staff Performance Dashboard", response.read().decode())

    def test_unknown_api_route_returns_json_error(self):
        status, payload, headers = self.request("/api/missing")
        self.assertEqual(status, 404)
        self.assertEqual(headers.get_content_type(), "application/json")
        self.assertEqual(payload["error"], "API endpoint not found.")

    def test_attendance_is_validated_persisted_and_legacy_state_is_accepted(self):
        self.register(self.client, "attendance_user")
        status, state, _ = self.request("/api/state")
        self.assertEqual(status, 200)

        state.pop("attendance")
        status, _, _ = self.request("/api/state", "PUT", state)
        self.assertEqual(status, 200)

        status, state, _ = self.request("/api/state")
        self.assertEqual(status, 200)
        state["attendance"] = [
            {"staffId": "S001", "date": "2026-10-08", "status": "Present"},
            {"staffId": "S001", "date": "2026-10-09", "status": "Half Day"},
        ]
        self.assertEqual(self.request("/api/state", "PUT", state)[0], 200)
        _, saved_state, _ = self.request("/api/state")
        self.assertEqual(saved_state["attendance"], state["attendance"])

        state["attendance"].append({"staffId": "S001", "date": "2026-10-08", "status": "Leave"})
        status, payload, _ = self.request("/api/state", "PUT", state)
        self.assertEqual(status, 400)
        self.assertIn("Attendance", payload["error"])

    def test_state_endpoint_normalizes_double_encoded_state_and_rejects_corrupt_state(self):
        self.register(self.client, "state_format_user")
        with server.database() as connection:
            row = connection.execute(
                "SELECT companies.state_json FROM users JOIN companies ON companies.id = users.company_id WHERE username = ?",
                ("state_format_user",),
            ).fetchone()
            connection.execute(
                "UPDATE companies SET state_json = ? WHERE id = (SELECT company_id FROM users WHERE username = ?)",
                (json.dumps(row["state_json"]), "state_format_user"),
            )

        status, state, _ = self.request("/api/state")
        self.assertEqual(status, 200)
        self.assertIsInstance(state, dict)
        self.assertEqual(state["attendance"], [])

        with server.database() as connection:
            connection.execute(
                "UPDATE companies SET state_json = ? WHERE id = (SELECT company_id FROM users WHERE username = ?)",
                ("[]", "state_format_user"),
            )
        status, payload, headers = self.request("/api/state")
        self.assertEqual(status, 500)
        self.assertEqual(headers.get_content_type(), "application/json")
        self.assertIn("Saved dashboard data", payload["error"])

    def test_existing_user_data_migrates_to_a_private_admin_company(self):
        legacy_database = Path(self.temp_directory.name) / "legacy.sqlite3"
        legacy_state = json.dumps(server.initial_state(), separators=(",", ":"))
        connection = sqlite3.connect(legacy_database)
        try:
            connection.execute(
                """
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    salt BLOB NOT NULL,
                    password_hash BLOB NOT NULL,
                    state_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "INSERT INTO users (username, name, salt, password_hash, state_json) VALUES (?, ?, ?, ?, ?)",
                ("legacy_admin", "Legacy Admin", b"salt", b"hash", legacy_state),
            )
            connection.commit()
        finally:
            connection.close()

        server.DATABASE_PATH = legacy_database
        server.initialize_database()
        with server.database() as connection:
            user = connection.execute(
                """
                SELECT users.role, companies.name AS company_name, companies.state_json
                FROM users JOIN companies ON companies.id = users.company_id
                WHERE users.username = ?
                """,
                ("legacy_admin",),
            ).fetchone()
        self.assertEqual(user["role"], "admin")
        self.assertEqual(user["company_name"], "Legacy Admin's company")
        self.assertEqual(json.loads(user["state_json"]), json.loads(legacy_state))


if __name__ == "__main__":
    unittest.main()
