"""Data models for GTD Dashboard."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional


class TaskStatus(str, Enum):
    """GTD task status markers."""
    
    NOW = "NOW"  # Currently doing
    DOING = "DOING"  # Alias for NOW
    LATER = "LATER"  # Scheduled for later
    TODO = "TODO"  # Next action
    NEXT = "NEXT"  # Alias for TODO
    WAITING = "WAITING-FOR"  # Waiting for someone/something
    WAITING_FOR = "WAITING-FOR"
    SOMEDAY = "SOMEDAY"  # Someday/maybe
    MAYBE = "MAYBE"
    DONE = "DONE"  # Completed
    CANCELLED = "CANCELLED"  # Cancelled
    IN_PROGRESS = "IN-PROGRESS"


@dataclass
class Task:
    """Represents a GTD task extracted from Logseq."""
    
    id: str  # Unique identifier (derived from content hash + date)
    content: str  # Task text content
    status: TaskStatus  # GTD status
    source_file: Path  # Source daily note file
    date: datetime  # Date from filename
    line_number: int  # Line number in source file
    raw_line: str  # Original line text
    
    # Optional metadata
    project: Optional[str] = None
    person: Optional[str] = None
    priority: Optional[str] = None
    deadline: Optional[datetime] = None
    tags: list[str] = field(default_factory=list)
    
    # Aging tracking for WAITING-FOR
    waiting_since: Optional[datetime] = None
    
    # Completion tracking
    completed_at: Optional[datetime] = None
    
    def __post_init__(self) -> None:
        """Extract metadata from content after initialization."""
        self._extract_metadata()
    
    def _extract_metadata(self) -> None:
        """Extract projects, people, tags from task content."""
        # Extract [[projects/name]] or [[project]] links
        project_matches = re.findall(r'\[\[projects/([^\]]+)\]\]|\[\[([^\]]+)\]\]', self.content)
        for match in project_matches:
            proj = match[0] or match[1]
            if proj and not self.project:
                self.project = proj
                break
        
        # Extract [[people/name]] or @mentions
        person_matches = re.findall(r'\[\[people/([^\]|]+)\]\]|\[\[people\.([^\]]+)\]\]|@(\w+)', self.content)
        for match in person_matches:
            person = match[0] or match[1] or match[2]
            if person and not self.person:
                self.person = person.replace('-', ' ').title()
                break
        
        # Extract #tags
        self.tags = re.findall(r'#(\w+)', self.content)
        
        # Extract priority (e.g., [A], [B], [C])
        priority_match = re.search(r'\[([ABC])\]', self.content)
        if priority_match:
            self.priority = priority_match.group(1)
    
    @property
    def age_days(self) -> Optional[int]:
        """Calculate age in days for waiting items."""
        if self.status in (TaskStatus.WAITING, TaskStatus.WAITING_FOR) and self.waiting_since:
            return (datetime.now() - self.waiting_since).days
        return None
    
    @property
    def is_stale(self, stale_days: int = 30) -> bool:
        """Check if task is stale (30+ days old without status change)."""
        age = self.age_days
        if age is not None:
            return age >= stale_days
        # For non-waiting tasks, check if they're old TODOs
        if self.status in (TaskStatus.TODO, TaskStatus.LATER):
            days_since_created = (datetime.now() - self.date).days
            return days_since_created >= stale_days
        return False
    
    @property
    def aging_indicator(self) -> str:
        """Return visual indicator for aging WAITING-FOR items."""
        age = self.age_days
        if age is None:
            return ""
        if age < 3:
            return "🟢"
        elif age < 7:
            return "🟡"
        elif age < 14:
            return "🟠"
        else:
            return "🔴"
    
    @property
    def display_content(self) -> str:
        """Return cleaned content for display."""
        # Remove markdown links but keep text
        content = re.sub(r'\[\[([^\]]+)\]\]', r'\1', self.content)
        # Remove checkbox markers
        content = re.sub(r'^- \[.\]\s*', '', content)
        # Remove status markers
        content = re.sub(r'\b(NOW|LATER|TODO|DONE|WAITING-FOR|SOMEDAY|MAYBE|DOING|IN-PROGRESS)\b\s*', '', content)
        return content.strip()
    
    def to_dict(self) -> dict:
        """Convert task to dictionary for export."""
        return {
            "id": self.id,
            "content": self.content,
            "display_content": self.display_content,
            "status": self.status.value,
            "source_file": str(self.source_file),
            "date": self.date.isoformat(),
            "line_number": self.line_number,
            "project": self.project,
            "person": self.person,
            "priority": self.priority,
            "tags": self.tags,
            "age_days": self.age_days,
            "is_stale": self.is_stale,
            "aging_indicator": self.aging_indicator,
        }
