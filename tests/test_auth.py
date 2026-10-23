import unittest

from chaoxing_stalker.chaoxing.auth import encrypt_by_aes, login


class FakeResponse:
    def __init__(self, text="", url="https://i.chaoxing.com/base", payload=None):
        self.text = text
        self.url = url
        self.encoding = None
        self.payload = payload or {}

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self):
        self.calls = []
        self.responses = [
            FakeResponse(
                '<input id="fid" value="1"><input id="refer" value="home">'
                '<input id="t" value="token">'
            ),
            FakeResponse(payload={"status": True, "url": "https://i.chaoxing.com"}),
            FakeResponse(),
            FakeResponse(url="https://i.chaoxing.com/base"),
        ]

    def get(self, url, **kwargs):
        self.calls.append(("get", url, kwargs))
        return self.responses.pop(0)

    def post(self, url, **kwargs):
        self.calls.append(("post", url, kwargs))
        return self.responses.pop(0)


class AuthTests(unittest.TestCase):
    def test_aes_encryption_is_deterministic(self):
        first = encrypt_by_aes("password", "u2oh6Vu^HWe4_AES")
        self.assertEqual(first, encrypt_by_aes("password", "u2oh6Vu^HWe4_AES"))
        self.assertTrue(first)

    def test_login_uses_hidden_fields_and_confirms_home_page(self):
        session = FakeSession()
        login(
            session,
            "user",
            "password",
            "https://passport.example.com",
            "https://home.example.com",
            "u2oh6Vu^HWe4_AES",
        )
        self.assertEqual([call[0] for call in session.calls], ["get", "post", "get", "get"])
        payload = session.calls[1][2]["data"]
        self.assertEqual(payload["fid"], "1")
        self.assertEqual(payload["refer"], "home")
        self.assertEqual(payload["t"], "token")

    def test_login_failure_raises_runtime_error(self):
        session = FakeSession()
        session.responses[1] = FakeResponse(payload={"status": False, "msg": "denied"})
        with self.assertRaisesRegex(RuntimeError, "denied"):
            login(
                session,
                "user",
                "password",
                "https://passport.example.com",
                "https://home.example.com",
                "u2oh6Vu^HWe4_AES",
            )


if __name__ == "__main__":
    unittest.main()
