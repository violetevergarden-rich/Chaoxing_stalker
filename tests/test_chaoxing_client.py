import datetime
import unittest
from unittest.mock import Mock

from chaoxing_stalker.chaoxing.client import ChaoXingClient


class ChaoXingClientTests(unittest.TestCase):
    def test_fetches_assignment_detail_and_returns_absolute_deadline(self):
        client = ChaoXingClient("user", "password")
        client._logged_in = True
        course = {
            "name": "Math",
            "course_id": "10",
            "class_id": "20",
            "cpi": "30",
        }
        assignment = {
            "title": "Homework",
            "status": "未交",
            "work_id": "42",
            "answer_id": "7",
            "deadline": "",
            "remaining_time": "剩余 1 天",
            "url": "/mooc-ans/mooc2/work/task?workId=42&answerId=7",
        }
        client._get_courses = Mock(return_value=[course])
        client._get_assignments_for_course = Mock(return_value=[assignment])
        detail_response = Mock()
        detail_response.text = "<p>作答时间: 10-20 08:00 至 10-30 23:59</p>"
        client.session.get = Mock(return_value=detail_response)

        assignments = client.get_unsubmitted_assignments()

        self.assertTrue(assignments[0]["deadline"].endswith("23:59"))
        self.assertTrue(
            assignments[0]["deadline"].startswith(str(datetime.datetime.now().year))
        )
        client.session.get.assert_called_once_with(
            "https://mooc1.chaoxing.com/mooc-ans/mooc2/work/task?workId=42&answerId=7"
        )

if __name__ == "__main__":
    unittest.main()
