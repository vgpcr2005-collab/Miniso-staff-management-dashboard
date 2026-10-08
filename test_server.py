import json
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

    def test_static_dashboard_is_served_by_backend(self):
        response = self.client.open(self.base_url + "/")
        self.assertEqual(response.status, 200)
        self.assertIn("MINISO Staff Performance Dashboard", response.read().decode())

    def test_unknown_api_route_returns_json_error(self):
        status, payload, headers = self.request("/api/missing")
        self.assertEqual(status, 404)
        self.assertEqual(headers.get_content_type(), "application/json")
        self.assertEqual(payload["error"], "API endpoint not found.")

if __name__ == "__main__":
    unittest.main()
