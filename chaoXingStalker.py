"""
ChaoXingStalker - 超星学习通未提交作业查询工具

用法:
    stalker = ChaoXingStalker("your_username", "your_password")
    unsubmitted = stalker.get_unsubmitted_assignments()
    for item in unsubmitted:
        print(f"[{item['course_name']}] {item['title']} - 截止: {item['deadline']}")
"""

import re
import requests
from bs4 import BeautifulSoup
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import base64
from urllib.parse import unquote


class ChaoXingStalker:
    """超星学习通作业查询类"""

    BASE_PASSPORT = "https://passport2.chaoxing.com"
    BASE_I = "https://i.chaoxing.com"
    BASE_MOOC = "https://mooc1.chaoxing.com"
    BASE_MOOC1 = "https://mooc1-1.chaoxing.com"

    # AES 加密密钥（超星固定值）
    AES_KEY = "u2oh6Vu^HWe4_AES"

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        })
        self._logged_in = False
        self._courses = []

    # ── 公开方法 ──────────────────────────────────────────

    def get_unsubmitted_assignments(self) -> list[dict]:
        """
        登录并获取所有课程中状态为"未提交"的作业。
        返回列表，每个元素:
            {
                "course_name": str,   # 课程名称
                "course_id":   str,   # 课程ID
                "class_id":    str,   # 班级ID
                "title":       str,   # 作业标题
                "work_id":     str,   # 作业ID
                "answer_id":   str,   # 答题ID
                "deadline":    str,   # 剩余时间
                "url":         str,   # 作业链接
            }
        """
        if not self._logged_in:
            self._login()

        self._courses = self._get_courses()
        results = []

        for course in self._courses:
            try:
                assignments = self._get_assignments_for_course(course)
                for item in assignments:
                    if self._is_unsubmitted(item):
                        results.append({
                            "course_name": course["name"],
                            "course_id":   course["course_id"],
                            "class_id":    course["class_id"],
                            "title":       item["title"],
                            "work_id":     item["work_id"],
                            "answer_id":   item.get("answer_id", ""),
                            "deadline":    item.get("deadline", ""),
                            "url":         item.get("url", ""),
                        })
            except Exception as e:
                print(f"[WARN] 查询课程 '{course['name']}' 失败: {e}")
                continue

        return results

    # ── AES 加密 ──────────────────────────────────────────

    @staticmethod
    def _encrypt_by_aes(message: str, key: str) -> str:
        """AES-CBC 加密，返回 base64 编码字符串"""
        key_bytes = key.encode("utf-8")
        iv_bytes = key.encode("utf-8")
        message_bytes = message.encode("utf-8")
        cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
        padded = pad(message_bytes, AES.block_size)
        encrypted = cipher.encrypt(padded)
        return base64.b64encode(encrypted).decode("utf-8")

    # ── 登录 ──────────────────────────────────────────────

    def _login(self):
        """
        模拟超星 passport2 登录流程（AES 加密 + fanyalogin API）
        """
        print("[INFO] 正在登录...")

        # 1. 访问登录页，获取隐藏字段（fid, refer, t 等）
        resp = self.session.get(
            f"{self.BASE_PASSPORT}/login",
            params={"refer": "https://i.chaoxing.com"},
            allow_redirects=True,
        )
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "html.parser")

        def _get_hidden(name: str) -> str:
            el = soup.find("input", {"id": name})
            return el.get("value", "") if el else ""

        # 2. 构造登录参数，密码需要 AES 加密
        login_data = {
            "fid":               _get_hidden("fid"),
            "uname":             self._encrypt_by_aes(self.username, self.AES_KEY),
            "password":          self._encrypt_by_aes(self.password, self.AES_KEY),
            "refer":             _get_hidden("refer"),
            "t":                 _get_hidden("t"),
            "forbidotherlogin":  _get_hidden("forbidotherlogin"),
            "validate":          _get_hidden("validate"),
            "doubleFactorLogin": _get_hidden("doubleFactorLogin"),
            "independentId":     _get_hidden("independentId"),
            "independentNameId": _get_hidden("independentNameId"),
        }

        # 3. 发送登录请求
        resp = self.session.post(
            f"{self.BASE_PASSPORT}/fanyalogin",
            data=login_data,
            allow_redirects=False,
        )
        result = resp.json()

        if not result.get("status"):
            raise RuntimeError(f"登录失败: {result.get('msg', '未知错误')}")

        # 4. 跟随重定向到 i.chaoxing.com（建立跨子域 cookie）
        redirect_url = unquote(result.get("url", "https://i.chaoxing.com"))
        self.session.get(redirect_url, allow_redirects=True)

        # 5. 访问个人空间确认登录
        resp = self.session.get(f"{self.BASE_I}/base", allow_redirects=True)
        if "login" in resp.url.lower():
            raise RuntimeError("登录验证失败，请检查账号和密码")

        self._logged_in = True
        print("[INFO] 登录成功")

    # ── 获取课程列表 ──────────────────────────────────────

    def _get_courses(self) -> list[dict]:
        """
        从 courslistdata API 解析所有课程。
        interaction 页面的课程列表是通过 AJAX 动态加载的，
        实际 API 为 /mooc-ans/visit/courselistdata?courseType=1
        """
        url = f"{self.BASE_MOOC1}/mooc-ans/visit/courselistdata"
        resp = self.session.get(
            url,
            params={"courseType": 1, "courseFolderId": 0, "query": ""},
            allow_redirects=True,
        )
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "html.parser")

        courses = []
        # 课程是 <li class="course clearfix"> 带有 courseid 和 clazzid 属性
        for el in soup.find_all("li", class_="course"):
            course_id = (el.get("courseid") or "").strip()
            class_id  = (el.get("clazzid") or "").strip()
            person_id = (el.get("personid") or "").strip()

            # 课程名在 span.course-name 的 title 属性中
            name_el = el.find("span", class_="course-name")
            name = name_el.get("title", "") if name_el else ""

            if course_id and class_id:
                courses.append({
                    "course_id": course_id,
                    "class_id":  class_id,
                    "cpi":       person_id,
                    "name":      name,
                })

        print(f"[INFO] 获取到 {len(courses)} 门课程")
        return courses

    # ── 获取某课程的作业列表 ──────────────────────────────

    def _get_assignments_for_course(self, course: dict) -> list[dict]:
        """
        访问作业列表页 (status=1 未完成)，提取所有作业项。
        返回 dict 列表，包含 title / status / work_id / answer_id / deadline / url。
        """
        params = {
            "courseId": course["course_id"],
            "classId":  course["class_id"],
            "cpi":      course["cpi"],
            "status":   1,  # 未完成
        }

        resp = self.session.get(
            f"{self.BASE_MOOC}/mooc2/work/list",
            params=params,
        )
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "html.parser")

        assignments = []
        for li in soup.select("div.bottomList ul li"):
            data_url  = li.get("data", "").strip()
            title_el  = li.find("p", class_="overHidden2")
            title     = title_el.get_text(strip=True) if title_el else ""
            status_el = li.find("p", class_="status")
            status    = status_el.get_text(strip=True) if status_el else ""
            time_el   = li.find("div", class_="time")
            deadline  = time_el.get_text(strip=True) if time_el else ""

            work_id, answer_id = self._parse_task_url(data_url)

            assignments.append({
                "title":     title,
                "status":    status,
                "work_id":   work_id,
                "answer_id": answer_id,
                "deadline":  deadline,
                "url":       data_url,
            })

        print(f"  ├─ {course['name']}: {len(assignments)} 个未完成作业")
        return assignments

    # ── 辅助方法 ──────────────────────────────────────────

    @staticmethod
    def _is_unsubmitted(item: dict) -> bool:
        """
        判断作业是否为"未提交"状态。
        支持英文 "To be submitted" 和中文 "未提交"。
        """
        status = item.get("status", "").strip()
        if not status:
            return False
        status_lower = status.lower()
        # 英文: "To be submitted" → should submit
        # 中文: "未提交"
        return ("to be" in status_lower and "submit" in status_lower) or "未提交" in status

    @staticmethod
    def _parse_task_url(url: str) -> tuple[str, str]:
        """从作业 URL 中提取 workId 和 answerId"""
        work_id = answer_id = ""
        if url:
            m = re.search(r"workId=(\d+)", url)
            if m:
                work_id = m.group(1)
            m = re.search(r"answerId=(\d+)", url)
            if m:
                answer_id = m.group(1)
        return work_id, answer_id


# ── 独立使用 ─────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("用法: python chaoXingStalker.py <用户名> <密码>")
        sys.exit(1)

    username = sys.argv[1]
    password = sys.argv[2]

    stalker = ChaoXingStalker(username, password)
    results = stalker.get_unsubmitted_assignments()

    print("\n" + "=" * 60)
    print(f"未提交作业共 {len(results)} 项:\n")

    for i, item in enumerate(results, 1):
        print(f"{i}. [{item['course_name']}]")
        print(f"   作业: {item['title']}")
        print(f"   截止: {item['deadline']}")
        print(f"   链接: {item['url']}")
        print()
