"""HTTP client coordinating ChaoXing login and assignment requests."""

from urllib.parse import urljoin

import requests

from chaoxing_stalker.assignment_types import Assignment, Course
from chaoxing_stalker.chaoxing.auth import login
from chaoxing_stalker.chaoxing.parser import (
    is_unsubmitted,
    parse_assignment_deadline,
    parse_assignments,
    parse_courses,
    parse_work_enc,
)


class ChaoXingClient:
    BASE_PASSPORT = "https://passport2.chaoxing.com"
    BASE_I = "https://i.chaoxing.com"
    BASE_MOOC = "https://mooc1.chaoxing.com"
    BASE_MOOC1 = "https://mooc1-1.chaoxing.com"
    AES_KEY = "u2oh6Vu^HWe4_AES"

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            }
        )
        self._logged_in = False

    def get_unsubmitted_assignments(self) -> list[Assignment]:
        if not self._logged_in:
            self._login()

        courses = self._get_courses()
        results = []
        for course in courses:
            try:
                assignments = self._get_assignments_for_course(course)
                for assignment in assignments:
                    if is_unsubmitted(assignment):
                        deadline = assignment.get("deadline", "")
                        if assignment.get("url"):
                            try:
                                detail_url = urljoin(
                                    f"{self.BASE_MOOC}/", assignment["url"]
                                )
                                detail = self.session.get(detail_url)
                                detail.encoding = "utf-8"
                                deadline = (
                                    parse_assignment_deadline(detail.text) or deadline
                                )
                            except Exception as error:
                                print(
                                    f"[WARN] 查询作业 '{assignment.get('title', '')}' "
                                    f"截止时间失败: {error}"
                                )
                        results.append(
                            {
                                "course_name": course["name"],
                                "course_id": course["course_id"],
                                "class_id": course["class_id"],
                                "title": assignment["title"],
                                "work_id": assignment["work_id"],
                                "answer_id": assignment.get("answer_id", ""),
                                "deadline": deadline,
                                "url": assignment.get("url", ""),
                            }
                        )
            except Exception as error:
                print(f"[WARN] 查询课程 '{course['name']}' 失败: {error}")
        return results

    def _login(self) -> None:
        login(
            self.session,
            self.username,
            self.password,
            self.BASE_PASSPORT,
            self.BASE_I,
            self.AES_KEY,
        )
        self._logged_in = True

    def _get_courses(self) -> list[Course]:
        url = f"{self.BASE_MOOC1}/mooc-ans/visit/courselistdata"
        response = self.session.get(
            url,
            params={"courseType": 1, "courseFolderId": 0, "query": ""},
            allow_redirects=True,
        )
        response.encoding = "utf-8"
        courses = parse_courses(response.text)
        print(f"[INFO] 获取到 {len(courses)} 门课程")
        return courses

    def _get_work_enc(self, course: Course) -> str:
        response = self.session.get(
            f"{self.BASE_MOOC}/mooc-ans/visit/stucoursemiddle",
            params={
                "courseid": course["course_id"],
                "clazzid": course["class_id"],
                "vc": 1,
                "cpi": course["cpi"],
                "ismooc2": 1,
                "v": 2,
            },
        )
        response.encoding = "utf-8"
        return parse_work_enc(response.text)

    def _get_assignments_for_course(self, course: Course) -> list[Assignment]:
        work_enc = self._get_work_enc(course)
        response = self.session.get(
            f"{self.BASE_MOOC}/mooc2/work/list",
            params={
                "courseId": course["course_id"],
                "classId": course["class_id"],
                "cpi": course["cpi"],
                "enc": work_enc,
                "ut": "s",
                "status": 1,
            },
        )
        response.encoding = "utf-8"
        assignments = parse_assignments(response.text)
        print(f"  ├─ {course['name']}: {len(assignments)} 个未完成作业")
        return assignments
