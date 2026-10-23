"""Parse ChaoXing course and assignment HTML pages."""

import datetime
import re

from bs4 import BeautifulSoup

from chaoxing_stalker.assignment_types import Assignment, Course


def get_hidden_input_values(html: str, input_ids: list[str]) -> dict[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    values = {}
    for input_id in input_ids:
        element = soup.find("input", {"id": input_id})
        values[input_id] = element.get("value", "") if element else ""
    return values


def parse_courses(html: str) -> list[Course]:
    soup = BeautifulSoup(html, "html.parser")
    courses = []
    for element in soup.find_all("li", class_="course"):
        course_id = (element.get("courseid") or "").strip()
        class_id = (element.get("clazzid") or "").strip()
        person_id = (element.get("personid") or "").strip()
        name_element = element.find("span", class_="course-name")
        name = name_element.get("title", "") if name_element else ""

        if course_id and class_id:
            courses.append(
                {
                    "course_id": course_id,
                    "class_id": class_id,
                    "cpi": person_id,
                    "name": name,
                }
            )
    return courses


def parse_work_enc(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    element = soup.find("input", {"id": "workEnc"})
    if element is None:
        raise RuntimeError("无法获取 workEnc，页面结构可能已变更")
    return element.get("value", "")


def parse_assignments(html: str) -> list[Assignment]:
    soup = BeautifulSoup(html, "html.parser")
    assignments = []
    for element in soup.select("div.bottomList ul li"):
        data_url = element.get("data", "").strip()
        title_element = element.find("p", class_="overHidden2")
        status_element = element.find("p", class_="status")
        time_element = element.find("div", class_="time")
        card_text = element.get_text(" ", strip=True)
        deadline = _extract_explicit_deadline(card_text)
        remaining_time = time_element.get_text(strip=True) if time_element else ""
        work_id, answer_id = parse_task_url(data_url)
        assignments.append(
            {
                "title": title_element.get_text(strip=True) if title_element else "",
                "status": status_element.get_text(strip=True) if status_element else "",
                "work_id": work_id,
                "answer_id": answer_id,
                "deadline": deadline,
                "remaining_time": remaining_time,
                "url": data_url,
            }
        )
    return assignments


def is_unsubmitted(item: Assignment) -> bool:
    status = item.get("status", "").strip()
    if not status:
        return False
    status_lower = status.lower()
    if not (("to be" in status_lower and "submit" in status_lower) or "未交" in status):
        return False
    remaining_time = item.get("remaining_time", item.get("deadline", ""))
    return "剩余" in remaining_time


_DEADLINE_PATTERN = re.compile(
    r"(?<!\d)(\d{4})[-/.年](\d{1,2})[-/.月](\d{1,2})日?"
    r"(?:[ T]*(\d{1,2}):(\d{2})(?::(\d{2}))?)?"
)


def _extract_explicit_deadline(text: str) -> str:
    match = _DEADLINE_PATTERN.search(text)
    if not match:
        return ""
    year, month, day, hour, minute, second = match.groups()
    try:
        date = datetime.date(int(year), int(month), int(day))
    except ValueError:
        return ""
    result = date.isoformat()
    if hour is not None:
        result += f" {int(hour):02d}:{minute}"
        if second is not None:
            result += f":{second}"
    return result


def parse_assignment_deadline(
    html: str, now: datetime.datetime | None = None
) -> str:
    """Parse the end of the answer period from an assignment detail page."""
    text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)

    # ChaoXing's detail page commonly shows a yearless range such as:
    # 作答时间: 10-20 08:00 至 10-30 23:59
    range_match = re.search(
        r"作答时间\s*[:：]?\s*\d{1,2}[-/.月]\d{1,2}日?\s*\d{1,2}:\d{2}"
        r"\s*(?:至|到|—|~|～)\s*(\d{1,2})[-/.月](\d{1,2})日?\s*(\d{1,2}):(\d{2})",
        text,
    )
    if range_match:
        month, day, hour, minute = (int(part) for part in range_match.groups())
        return _format_yearless_deadline(month, day, hour, minute, now)

    # If the page includes full years, the final date in its time range is due.
    explicit_dates = list(_DEADLINE_PATTERN.finditer(text))
    if explicit_dates:
        matched = explicit_dates[-1]
        return _format_explicit_match(matched)
    return ""


def _format_explicit_match(match: re.Match[str]) -> str:
    year, month, day, hour, minute, second = match.groups()
    try:
        date = datetime.date(int(year), int(month), int(day))
    except ValueError:
        return ""
    result = date.isoformat()
    if hour is not None:
        result += f" {int(hour):02d}:{minute}"
        if second is not None:
            result += f":{second}"
    return result


def _format_yearless_deadline(
    month: int,
    day: int,
    hour: int,
    minute: int,
    now: datetime.datetime | None,
) -> str:
    reference = now or datetime.datetime.now()
    candidates = []
    for year in range(reference.year - 1, reference.year + 3):
        try:
            candidates.append(datetime.datetime(year, month, day, hour, minute))
        except ValueError:
            continue
    if not candidates:
        return ""
    future = [candidate for candidate in candidates if candidate >= reference]
    deadline = min(future) if future else max(candidates)
    return deadline.strftime("%Y-%m-%d %H:%M")


def parse_task_url(url: str) -> tuple[str, str]:
    work_id_match = re.search(r"workId=(\d+)", url) if url else None
    answer_id_match = re.search(r"answerId=(\d+)", url) if url else None
    work_id = work_id_match.group(1) if work_id_match else ""
    answer_id = answer_id_match.group(1) if answer_id_match else ""
    return work_id, answer_id
