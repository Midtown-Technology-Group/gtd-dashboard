"""Custom stale thresholds must apply to scheduled and waiting tasks."""

from datetime import datetime
from pathlib import Path

import pytest

from gtd_dashboard import models
from gtd_dashboard.aggregator import TaskAggregator
from gtd_dashboard.parser import TaskParser


class FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 10, 29, 12)


@pytest.mark.parametrize("marker", ["TODO", "LATER", "WAITING-FOR"])
@pytest.mark.parametrize(("days", "expected"), [(7, True), (10, True), (11, False), (60, False)])
def test_stale_honors_requested_threshold(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, marker: str, days: int, expected: bool
) -> None:
    monkeypatch.setattr(models, "datetime", FixedDateTime)
    note = tmp_path / "2026-10-19.md"
    note.write_text(f"- {marker} Follow up\n", encoding="utf-8")
    tasks = TaskParser(tmp_path).parse_single(note)
    assert TaskAggregator(tasks).stale(days) == (tasks if expected else [])
    assert tasks[0].is_stale is False


def test_waiting_staleness_uses_waiting_since(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(models, "datetime", FixedDateTime)
    note = tmp_path / "2026-09-01.md"
    note.write_text("- WAITING-FOR Reply\n- DONE Finished\n- NOW Working\n", encoding="utf-8")
    tasks = TaskParser(tmp_path).parse_single(note)
    tasks[0].waiting_since = datetime(2026, 10, 28)
    aggregator = TaskAggregator(tasks)
    assert aggregator.stale(7) == []
    assert aggregator.stale(1) == [tasks[0]]
    assert tasks[0].is_stale is False


def test_default_stale_threshold_stays_thirty_days(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(models, "datetime", FixedDateTime)
    for date in ["2026-09-29", "2026-09-30"]:
        (tmp_path / f"{date}.md").write_text("- LATER Appointment\n", encoding="utf-8")
    tasks = list(TaskParser(tmp_path).parse_all(parallel=False))
    assert [t.date.day for t in TaskAggregator(tasks).stale()] == [29]
    assert all(t.is_stale == (t.date.day == 29) for t in tasks)
    assert TaskAggregator(tasks).stale(60) == []
