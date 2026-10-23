"""ChaoXing login flow and password encryption."""

import base64
from urllib.parse import unquote

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

from chaoxing_stalker.chaoxing.parser import get_hidden_input_values


def encrypt_by_aes(message: str, key: str) -> str:
    key_bytes = key.encode("utf-8")
    cipher = AES.new(key_bytes, AES.MODE_CBC, key_bytes)
    encrypted = cipher.encrypt(pad(message.encode("utf-8"), AES.block_size))
    return base64.b64encode(encrypted).decode("utf-8")


def login(
    session,
    username: str,
    password: str,
    passport_base: str,
    home_base: str,
    aes_key: str,
) -> None:
    print("[INFO] 正在登录...")
    response = session.get(
        f"{passport_base}/login",
        params={"refer": home_base},
        allow_redirects=True,
    )
    response.encoding = "utf-8"

    hidden_values = get_hidden_input_values(
        response.text,
        [
            "fid",
            "refer",
            "t",
            "forbidotherlogin",
            "validate",
            "doubleFactorLogin",
            "independentId",
            "independentNameId",
        ],
    )
    login_data = {
        "fid": hidden_values["fid"],
        "uname": encrypt_by_aes(username, aes_key),
        "password": encrypt_by_aes(password, aes_key),
        "refer": hidden_values["refer"],
        "t": hidden_values["t"],
        "forbidotherlogin": hidden_values["forbidotherlogin"],
        "validate": hidden_values["validate"],
        "doubleFactorLogin": hidden_values["doubleFactorLogin"],
        "independentId": hidden_values["independentId"],
        "independentNameId": hidden_values["independentNameId"],
    }

    response = session.post(
        f"{passport_base}/fanyalogin",
        data=login_data,
        allow_redirects=False,
    )
    result = response.json()
    if not result.get("status"):
        raise RuntimeError(f"登录失败: {result.get('msg', '未知错误')}")

    redirect_url = unquote(result.get("url", home_base))
    session.get(redirect_url, allow_redirects=True)

    response = session.get(f"{home_base}/base", allow_redirects=True)
    if "login" in response.url.lower():
        raise RuntimeError("登录验证失败，请检查账号和密码")

    print("[INFO] 登录成功")
