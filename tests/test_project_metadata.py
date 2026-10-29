"""Person references must not become project aggregation keys."""

from pathlib import Path

import pytest

from gtd_dashboard.aggregator import TaskAggregator
from gtd_dashboard.parser import TaskParser


@pytest.mark.parametrize("person_link", ["[[people/John-Smith]]", "[[people.John-Smith]]"])
@pytest.mark.parametrize("project_link", ["[[projects/bifrost]]", "[[bifrost]]"])
def test_person_before_project_does_not_steal_group(
    tmp_path: Path, person_link: str, project_link: str
) -> None:
    note = tmp_path / "2026-10-01.md"
    note.write_text(
        f"- TODO Ask {person_link} about {project_link}\n"
        f"- LATER {project_link} Schedule review\n",
        encoding="utf-8",
    )
    tasks = TaskParser(tmp_path).parse_single(note)
    assert len(tasks) == 2
    assert tasks[0].person == "John Smith"
    assert all(t.project == "bifrost" for t in tasks)
    aggregator = TaskAggregator(tasks)
    assert aggregator.by_project("bifrost") == tasks
    assert aggregator.group_by_project() == {"bifrost": tasks}
    assert aggregator.get_stats()["projects"] == 1


@pytest.mark.parametrize("person_link", ["[[people/John-Smith]]", "[[people.John-Smith]]"])
def test_person_only_task_has_no_project(tmp_path: Path, person_link: str) -> None:
    note = tmp_path / "2026-10-01.md"
    note.write_text(f"- WAITING-FOR Reply from {person_link}\n", encoding="utf-8")
    tasks = TaskParser(tmp_path).parse_single(note)
    assert len(tasks) == 1
    assert tasks[0].person == "John Smith"
    assert tasks[0].project is None
    assert TaskAggregator(tasks).group_by_project() == {"No Project": tasks}
