"""GTD Dashboard - Unified view of scattered GTD tasks across Logseq knowledge graphs."""

__version__ = "0.1.0"
__author__ = "Thomas Bray"
__license__ = "AGPL-3.0"

from gtd_dashboard.models import Task, TaskStatus
from gtd_dashboard.parser import TaskParser
from gtd_dashboard.aggregator import TaskAggregator

__all__ = ["Task", "TaskStatus", "TaskParser", "TaskAggregator"]
