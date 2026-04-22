"""Microsoft 365 work-context integration."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional

from gtd_dashboard.models import Task, TaskStatus


@dataclass
class M365Task:
    """Represents a task from Microsoft 365 work-context."""
    
    id: str
    title: str
    source: str  # 'todo', 'email', 'calendar'
    created_date: datetime
    due_date: Optional[datetime] = None
    is_completed: bool = False
    importance: str = "normal"  # 'low', 'normal', 'high'
    url: Optional[str] = None
    
    def to_gtd_task(self, context_date: datetime, source_file: Path) -> Task:
        """Convert M365 task to GTD Task."""
        status = TaskStatus.DONE if self.is_completed else TaskStatus.TODO
        
        return Task(
            id=f"m365-{self.id}",
            content=f"[M365 {self.source}] {self.title}",
            status=status,
            source_file=source_file,
            date=context_date,
            line_number=0,
            raw_line=self.title,
            priority="A" if self.importance == "high" else None,
        )


class WorkContextParser:
    """Parser for work-context/daily/ files containing M365 data."""
    
    def __init__(self, work_context_path: Path) -> None:
        """Initialize parser.
        
        Args:
            work_context_path: Path to work-context/daily/ directory
        """
        self.work_context_path = Path(work_context_path)
    
    def _extract_date_from_filename(self, filename: str) -> Optional[datetime]:
        """Extract date from filename like YYYY-MM-DD.md."""
        match = re.match(r'(\d{4})-(\d{2})-(\d{2})\.md$', filename)
        if match:
            year, month, day = map(int, match.groups())
            try:
                return datetime(year, month, day)
            except ValueError:
                return None
        return None
    
    def _parse_todo_section(self, content: str, file_date: datetime, source_file: Path) -> Iterator[M365Task]:
        """Parse To Do section from work-context file."""
        # Look for "### To Do - Open / In Focus" section
        todo_match = re.search(
            r'### To Do - Open / In Focus\n(.*?)(?=###|$)',
            content,
            re.DOTALL
        )
        
        if not todo_match:
            return
        
        section = todo_match.group(1)
        
        # Match task lines: - [ ] Task title or - [x] Task title
        for match in re.finditer(r'- \[([ x])\]\s*(.+?)(?=\n- \[|$)', section, re.DOTALL):
            is_completed = match.group(1) == 'x'
            title = match.group(2).strip().replace('\n', ' ')
            
            if not title or title.startswith('('):
                continue
            
            yield M365Task(
                id=f"todo-{hash(title) % 100000:05d}",
                title=title,
                source="todo",
                created_date=file_date,
                is_completed=is_completed,
                importance="normal"
            )
    
    def _parse_flagged_emails(self, content: str, file_date: datetime, source_file: Path) -> Iterator[M365Task]:
        """Parse flagged emails section."""
        email_match = re.search(
            r'### Flagged / Important Emails\n(.*?)(?=###|$)',
            content,
            re.DOTALL
        )
        
        if not email_match:
            return
        
        section = email_match.group(1)
        
        # Skip if "No flagged emails"
        if "No flagged emails" in section:
            return
        
        # Parse email entries
        for line in section.split('\n'):
            line = line.strip()
            if not line or line.startswith('-') and 'from' in line.lower():
                # Extract subject and sender
                match = re.search(r'["\'](.+?)["\'].*from\s+(.+?)(?:\s|$)', line)
                if match:
                    subject = match.group(1)
                    sender = match.group(2)
                    
                    yield M365Task(
                        id=f"email-{hash(subject) % 100000:05d}",
                        title=f"Email: {subject} (from {sender})",
                        source="email",
                        created_date=file_date,
                        is_completed=False,
                        importance="high"
                    )
    
    def _parse_completed_tasks(self, content: str, file_date: datetime, source_file: Path) -> Iterator[M365Task]:
        """Parse completed tasks section."""
        completed_match = re.search(
            r'### Completed Today.*?\n(.*?)(?=###|$)',
            content,
            re.DOTALL
        )
        
        if not completed_match:
            return
        
        section = completed_match.group(1)
        
        # Skip if "no completed tasks"
        if "no completed tasks" in section.lower():
            return
        
        # Parse completed items
        for match in re.finditer(r'- \[x\]\s*(.+?)(?=\n- \[|$)', section, re.DOTALL):
            title = match.group(1).strip().replace('\n', ' ')
            
            if not title or title.startswith('('):
                continue
            
            yield M365Task(
                id=f"done-{hash(title) % 100000:05d}",
                title=title,
                source="todo",
                created_date=file_date,
                is_completed=True,
                importance="normal"
            )
    
    def parse_file(self, file_path: Path) -> list[M365Task]:
        """Parse a single work-context file."""
        tasks = []
        
        date = self._extract_date_from_filename(file_path.name)
        if not date:
            return tasks
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except (IOError, OSError):
            return tasks
        
        # Collect all M365 tasks
        for task in self._parse_todo_section(content, date, file_path):
            tasks.append(task)
        
        for task in self._parse_flagged_emails(content, date, file_path):
            tasks.append(task)
        
        for task in self._parse_completed_tasks(content, date, file_path):
            tasks.append(task)
        
        return tasks
    
    def parse_all(self) -> Iterator[M365Task]:
        """Parse all work-context files."""
        if not self.work_context_path.exists():
            return
        
        files = list(self.work_context_path.glob('*.md'))
        
        for file_path in files:
            yield from self.parse_file(file_path)
    
    def get_tasks_as_gtd(self, days: Optional[int] = None) -> Iterator[Task]:
        """Get all M365 tasks converted to GTD Task format."""
        from datetime import timedelta
        
        cutoff = None
        if days:
            cutoff = datetime.now() - timedelta(days=days)
        
        for m365_task in self.parse_all():
            if cutoff and m365_task.created_date < cutoff:
                continue
            
            source_file = self.work_context_path / f"{m365_task.created_date.strftime('%Y-%m-%d')}.md"
            yield m365_task.to_gtd_task(m365_task.created_date, source_file)


class WorkContextMerger:
    """Merges GTD tasks with Microsoft 365 work-context data."""
    
    def __init__(
        self, 
        gtd_tasks: list[Task],
        work_context_path: Path,
        days: Optional[int] = 7
    ) -> None:
        """Initialize merger.
        
        Args:
            gtd_tasks: List of GTD tasks from daily notes
            work_context_path: Path to work-context/daily/ directory
            days: Only include M365 tasks from last N days
        """
        self.gtd_tasks = gtd_tasks
        self.work_context_path = work_context_path
        self.days = days
    
    def merge(self) -> list[Task]:
        """Merge GTD tasks with M365 tasks, avoiding duplicates."""
        # Get M365 tasks
        parser = WorkContextParser(self.work_context_path)
        m365_tasks = list(parser.get_tasks_as_gtd(self.days))
        
        # Create set of existing content hashes for deduplication
        existing_content = {self._normalize_content(t.content) for t in self.gtd_tasks}
        
        # Add M365 tasks that aren't duplicates
        merged = list(self.gtd_tasks)
        for m365_task in m365_tasks:
            normalized = self._normalize_content(m365_task.content)
            if normalized not in existing_content:
                merged.append(m365_task)
                existing_content.add(normalized)
        
        return merged
    
    def _normalize_content(self, content: str) -> str:
        """Normalize content for deduplication comparison."""
        # Remove M365 prefix, lowercase, remove extra spaces
        content = re.sub(r'\[M365 \w+\]\s*', '', content)
        content = content.lower().strip()
        content = re.sub(r'\s+', ' ', content)
        return content
