"""Shared data shapes used by the assignment checker."""

from typing import TypedDict


class Assignment(TypedDict, total=False):
    """A scraped assignment; course fields are added after course parsing."""

    course_name: str
    course_id: str
    class_id: str
    title: str
    status: str
    work_id: str
    answer_id: str
    deadline: str
    remaining_time: str
    url: str


class Course(TypedDict):
    course_id: str
    class_id: str
    cpi: str
    name: str
