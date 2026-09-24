import http.client
import json
import threading
import unittest

from app import create_server


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = create_server(port=0)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def request(self, method, path, body=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        headers = {"Content-Type": "application/json"}
        connection.request(method, path, body=json.dumps(body) if body else None, headers=headers)
        response = connection.getresponse()
        payload = json.loads(response.read().decode("utf-8"))
        connection.close()
        return response.status, payload

    def test_bootstrap_endpoint(self):
        status, payload = self.request("GET", "/api/bootstrap")
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["stats"]["job_count"], 6)

    def test_match_endpoint(self):
        status, payload = self.request(
            "POST",
            "/api/match",
            {"job_id": "J006", "resume_text": "本科，3年经验，熟悉Python、NLP、PyTorch和大语言模型应用"},
        )
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertIn("total_score", payload["result"])

    def test_invalid_job_returns_readable_error(self):
        status, payload = self.request("POST", "/api/rank", {"job_id": "UNKNOWN"})
        self.assertEqual(status, 400)
        self.assertFalse(payload["ok"])
        self.assertIn("岗位", payload["error"])


if __name__ == "__main__":
    unittest.main()
