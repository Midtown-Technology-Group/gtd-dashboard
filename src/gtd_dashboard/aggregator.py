"""Task aggregator for grouping and filtering GTD tasks."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Iterator, Optional

from gtd_dashboard.models import Task, TaskStatus


class TaskAggregator:
    """Aggregates and filters GTD tasks."""
    
    def __init__(self, tasks: list[Task] | Iterator[Task]) -> None:
        """Initialize with tasks.
        
        Args:
            tasks: List or iterator of Task objects
        """
        if isinstance(tasks, Iterator):
            self.tasks = list(tasks)
        else:
            self.tasks = tasks
    
    def by_status(self, status: TaskStatus | list[TaskStatus]) -> list[Task]:
        """Filter tasks by status."""
        if isinstance(status, TaskStatus):
            status_list = [status]
        else:
            status_list = status
        return [t for t in self.tasks if t.status in status_list]
    
    def by_project(self, project: str) -> list[Task]:
        """Filter tasks by project."""
        return [t for t in self.tasks if t.project and project.lower() in t.project.lower()]
    
    def by_person(self, person: str) -> list[Task]:
        """Filter tasks by person."""
        return [t for t in self.tasks if t.person and person.lower() in t.person.lower()]
    
    def by_tag(self, tag: str) -> list[Task]:
        """Filter tasks by tag."""
        return [t for t in self.tasks if tag.lower() in [tg.lower() for tg in t.tags]]
    
    def by_priority(self, priority: str) -> list[Task]:
        """Filter tasks by priority."""
        return [t for t in self.tasks if t.priority == priority.upper()]
    
    def by_date_range(self, start: datetime, end: datetime) -> list[Task]:
        """Filter tasks by date range."""
        return [t for t in self.tasks if start <= t.date <= end]
    
    def stale(self, days: int = 30) -> list[Task]:
        """Get stale tasks (tasks that haven't moved in X days)."""
        return [t for t in self.tasks if t.is_stale]
    
    def waiting_with_aging(self, max_age: Optional[int] = None) -> list[Task]:
        """Get WAITING-FOR tasks sorted by age."""
        waiting = self.by_status([TaskStatus.WAITING, TaskStatus.WAITING_FOR])
        # Sort by age descending (oldest first)
        waiting.sort(key=lambda t: t.age_days or 0, reverse=True)
        if max_age is not None:
            waiting = [t for t in waiting if (t.age_days or 0) <= max_age]
        return waiting
    
    def now(self) -> list[Task]:
        """Get NOW/DOING tasks."""
        return self.by_status(TaskStatus.NOW)
    
    def later(self) -> list[Task]:
        """Get LATER tasks."""
        return self.by_status(TaskStatus.LATER)
    
    def todo(self) -> list[Task]:
        """Get TODO/NEXT tasks."""
        return self.by_status([TaskStatus.TODO])
    
    def someday(self) -> list[Task]:
        """Get SOMEDAY/MAYBE tasks."""
        return self.by_status([TaskStatus.SOMEDAY])
    
    def done(self) -> list[Task]:
        """Get DONE/CANCELLED tasks."""
        return self.by_status([TaskStatus.DONE, TaskStatus.CANCELLED])
    
    def active(self) -> list[Task]:
        """Get all active (non-completed) tasks."""
        return [t for t in self.tasks if t.status not in (TaskStatus.DONE, TaskStatus.CANCELLED)]
    
    def group_by_project(self) -> dict[str, list[Task]]:
        """Group tasks by project."""
        groups: dict[str, list[Task]] = defaultdict(list)
        for task in self.tasks:
            key = task.project or "No Project"
            groups[key].append(task)
        return dict(groups)
    
    def group_by_person(self) -> dict[str, list[Task]]:
        """Group tasks by person."""
        groups: dict[str, list[Task]] = defaultdict(list)
        for task in self.tasks:
            key = task.person or "No Person"
            groups[key].append(task)
        return dict(groups)
    
    def group_by_status(self) -> dict[str, list[Task]]:
        """Group tasks by status."""
        groups: dict[str, list[Task]] = defaultdict(list)
        for task in self.tasks:
            groups[task.status.value].append(task)
        return dict(groups)
    
    def group_by_date(self) -> dict[str, list[Task]]:
        """Group tasks by date."""
        groups: dict[str, list[Task]] = defaultdict(list)
        for task in self.tasks:
            key = task.date.strftime('%Y-%m-%d')
            groups[key].append(task)
        return dict(groups)
    
    def search(self, query: str) -> list[Task]:
        """Search tasks by content."""
        query = query.lower()
        return [
            t for t in self.tasks 
            if query in t.content.lower() 
            or query in t.display_content.lower()
            or (t.project and query in t.project.lower())
            or (t.person and query in t.person.lower())
            or any(query in tag.lower() for tag in t.tags)
        ]
    
    def get_stats(self) -> dict:
        """Get aggregate statistics."""
        total = len(self.tasks)
        active_count = len(self.active())
        done_count = len(self.done())
        stale_count = len(self.stale())
        
        status_counts: dict[str, int] = defaultdict(int)
        for task in self.tasks:
            status_counts[task.status.value] += 1
        
        project_count = len(self.group_by_project())
        person_count = len(self.group_by_person())
        
        # Calculate average age of waiting items
        waiting_tasks = self.waiting_with_aging()
        avg_waiting_age = 0
        if waiting_tasks:
            ages = [t.age_days for t in waiting_tasks if t.age_days is not None]
            if ages:
                avg_waiting_age = sum(ages) / len(ages)
        
        return {
            "total": total,
            "active": active_count,
            "done": done_count,
            "stale": stale_count,
            "by_status": dict(status_counts),
            "projects": project_count,
            "people": person_count,
            "waiting_count": len(waiting_tasks),
            "avg_waiting_age_days": round(avg_waiting_age, 1),
        }
