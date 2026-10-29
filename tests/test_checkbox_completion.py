"""Regression tests for completed Logseq checkboxes."""

from pathlib import Path

import pytest

from gtd_dashboard.aggregator import TaskAggregator
from gtd_dashboard.models import TaskStatus
from gtd_dashboard.parser import TaskParser


@pytest.mark.parametrize("check", ["x", "X"])
@pytest.mark.parametrize("marker", ["TODO", "NOW", "LATER", "WAITING-FOR", "SOMEDAY"])
def test_checked_marker_is_completed(tmp_path: Path, check: str, marker: str) -> None:
    note = tmp_path / "2026-10-01.md"
    note.write_text(f"- [{check}] {marker}: Send résumé\n", encoding="utf-8")
    tasks = TaskParser(tmp_path).parse_single(note)

    assert len(tasks) == 1
    assert tasks[0].status == TaskStatus.DONE
    assert tasks[0].content == "Send résumé"
    assert tasks[0].waiting_since is None
    assert TaskAggregator(tasks).active() == []


@pytest.mark.parametrize(
    ("marker", "status"),
    [("TODO", TaskStatus.TODO), ("LATER", TaskStatus.LATER), ("WAITING-FOR", TaskStatus.WAITING)],
)
def test_unchecked_marker_keeps_status(tmp_path: Path, marker: str, status: TaskStatus) -> None:
    note = tmp_path / "2026-10-01.md"
    note.write_text(f"- [ ] {marker}: Send résumé\n", encoding="utf-8")
    tasks = TaskParser(tmp_path).parse_single(note)
    assert len(tasks) == 1
    assert tasks[0].status == status
    assert tasks[0].content == "Send résumé"
