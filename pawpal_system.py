# Logic layer - where backend classes live
"""PawPal+ domain model — class skeletons.

These stubs mirror diagrams/uml.mmd. They define structure only; the
scheduling logic is intentionally left unimplemented (see NotImplementedError).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import time
from enum import Enum


class Priority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3


@dataclass
class Medication:
    name: str
    dose: str
    times_per_day: int
    preferred_times: list[time] = field(default_factory=list)

    def generate_tasks(self) -> list["Task"]:
        """Expand this medication into one pinned Task per preferred time."""
        raise NotImplementedError


@dataclass
class Pet:
    name: str
    species: str
    breed: str = ""
    age: int = 0
    preferred_food: str = ""
    medications: list[Medication] = field(default_factory=list)

    def add_medication(self, med: Medication) -> None:
        raise NotImplementedError


@dataclass
class Owner:
    name: str
    age: int = 0
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        raise NotImplementedError


@dataclass
class Task:
    title: str
    duration_minutes: int
    priority: Priority = Priority.MEDIUM
    fixed_time: time | None = None
    is_flexible: bool = True
    pet: Pet | None = None
    owner: Owner | None = None


@dataclass
class DayWindow:
    start: time
    end: time

    def total_minutes(self) -> int:
        raise NotImplementedError


@dataclass
class ScheduledTask:
    task: Task
    start: time
    end: time
    reason: str = ""


@dataclass
class Plan:
    items: list[ScheduledTask] = field(default_factory=list)
    unscheduled: list[Task] = field(default_factory=list)

    def explain(self) -> str:
        """Return a human-readable summary of why each task landed where it did."""
        raise NotImplementedError


class Scheduler:
    def build_plan(self, tasks: list[Task], window: DayWindow) -> Plan:
        """Order/place tasks within the day window and return a Plan."""
        raise NotImplementedError
