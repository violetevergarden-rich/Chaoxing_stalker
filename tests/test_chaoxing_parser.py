import datetime
import unittest

from chaoxing_stalker.chaoxing.parser import (
    is_unsubmitted,
    parse_assignments,
    parse_assignment_deadline,
    parse_courses,
    parse_task_url,
    parse_work_enc,
)


class ChaoXingParserTests(unittest.TestCase):
    def test_parses_course_attributes_and_name(self):
        html = (
            '<li class="course" courseid="10" clazzid="20" personid="30">'
            '<span class="course-name" title="Math"></span></li>'
        )
        self.assertEqual(
            parse_courses(html),
            [{"course_id": "10", "class_id": "20", "cpi": "30", "name": "Math"}],
        )

    def test_parses_assignment_and_filters_unsubmitted_before_deadline(self):
        html = (
            '<div class="bottomList"><ul><li data="/work?workId=42&answerId=7">'
            '<p class="overHidden2">Essay</p><p class="status">未交</p>'
            '<div class="deadline">截止时间：2026-10-30 23:59</div>'
            '<div class="time">剩余 1 天</div></li></ul></div>'
        )
        assignment = parse_assignments(html)[0]
        self.assertEqual(assignment["work_id"], "42")
        self.assertEqual(assignment["answer_id"], "7")
        self.assertEqual(assignment["deadline"], "2026-10-30 23:59")
        self.assertEqual(assignment["remaining_time"], "剩余 1 天")
        self.assertTrue(is_unsubmitted(assignment))

    def test_missing_explicit_deadline_stays_empty_but_remaining_time_filters(self):
        html = (
            '<div class="bottomList"><ul><li data="/work?workId=43">'
            '<p class="overHidden2">Essay</p><p class="status">未交</p>'
            '<div class="time">剩余 2 小时</div></li></ul></div>'
        )
        assignment = parse_assignments(html)[0]
        self.assertEqual(assignment["deadline"], "")
        self.assertTrue(is_unsubmitted(assignment))

    def test_reads_yearless_deadline_from_assignment_detail_time_range(self):
        html = "<p>作答时间: 10-20 08:00 至 10-30 23:59</p>"
        deadline = parse_assignment_deadline(
            html, now=datetime.datetime(2026, 10, 23, 12, 0)
        )
        self.assertEqual(deadline, "2026-10-30 23:59")

    def test_reads_full_year_deadline_from_detail_page(self):
        html = "<p>作答时间: 2026-10-20 08:00 至 2026-10-30 23:59</p>"
        self.assertEqual(
            parse_assignment_deadline(html), "2026-10-30 23:59"
        )

    def test_rejects_submitted_or_expired_assignments(self):
        self.assertFalse(is_unsubmitted({"status": "已提交", "deadline": "剩余 1 天"}))
        self.assertFalse(is_unsubmitted({"status": "未交", "deadline": "已截止"}))

    def test_missing_work_enc_raises(self):
        with self.assertRaisesRegex(RuntimeError, "workEnc"):
            parse_work_enc("<html></html>")

    def test_task_url_without_ids_returns_empty_values(self):
        self.assertEqual(parse_task_url("/work/list"), ("", ""))


if __name__ == "__main__":
    unittest.main()
