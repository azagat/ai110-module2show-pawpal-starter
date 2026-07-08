# Logic layer - where backend classes live
"""PawPal+ domain model.

Implements the scheduling logic for a pet-care planning assistant.
Kept in sync with diagrams/uml.mmd.

Layers:
  * Medication / Pet / Owner  -> what care is needed and who it's for
  * Task / Priority           -> a single unit of care work
  * DayWindow                 -> how much time the owner has today
  * Scheduler / Plan          -> the "brain" that places tasks in the day
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import time
from enum import Enum


# --------------------------------------------------------------------------- #
# Small time helpers (a time-of-day is just minutes from midnight)
# --------------------------------------------------------------------------- #
def _to_minutes(t: time) -> int:
    """Minutes since midnight for a time-of-day."""
    return t.hour * 60 + t.minute


def _to_time(minutes: int) -> time:
    """Convert minutes since midnight back into a time (clamped to 0..1439)."""
    minutes = max(0, min(minutes, 24 * 60 - 1))
    return time(hour=minutes // 60, minute=minutes % 60)


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
        """Expand this medication into one pinned Task per preferred time.

        A medication is time-sensitive, so each dose becomes a HIGH-priority,
        non-flexible task. If explicit ``preferred_times`` are given, one task
        is pinned to each of them. Otherwise ``times_per_day`` unpinned (but
        still high-priority) tasks are produced for the scheduler to place.
        """
        tasks: list[Task] = []
        if self.preferred_times:
            for t in self.preferred_times:
                tasks.append(
                    Task(
                        title=f"Give {self.name} ({self.dose})",
                        duration_minutes=5,
                        priority=Priority.HIGH,
                        fixed_time=t,
                        is_flexible=False,
                    )
                )
        else:
            for i in range(max(0, self.times_per_day)):
                tasks.append(
                    Task(
                        title=f"Give {self.name} ({self.dose}) — dose {i + 1}",
                        duration_minutes=5,
                        priority=Priority.HIGH,
                        fixed_time=None,
                        is_flexible=True,
                    )
                )
        return tasks


@dataclass
class Pet:
    name: str
    species: str
    breed: str = ""
    age: int = 0
    preferred_food: str = ""
    medications: list[Medication] = field(default_factory=list)
    tasks: list["Task"] = field(default_factory=list)

    def add_medication(self, med: Medication) -> None:
        """Register a medication this pet needs."""
        self.medications.append(med)

    def add_task(self, task: "Task") -> None:
        """Attach a care task directly to this pet."""
        task.pet = self
        self.tasks.append(task)

    def generate_tasks(self) -> list["Task"]:
        """Every task for this pet: explicit tasks plus medication doses.

        All tasks are linked back to the pet so the scheduler and UI can group
        by pet.
        """
        tasks: list[Task] = []
        for task in self.tasks:
            task.pet = self
            tasks.append(task)
        for med in self.medications:
            for task in med.generate_tasks():
                task.pet = self
                tasks.append(task)
        return tasks


@dataclass
class Owner:
    name: str
    age: int = 0
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this owner's care list."""
        self.pets.append(pet)

    def all_tasks(self) -> list["Task"]:
        """Every care task across all of this owner's pets.

        Each task is tagged with both the pet it's for and this owner, so the
        scheduler can reason about tasks from multiple pets at once.
        """
        tasks: list[Task] = []
        for pet in self.pets:
            for task in pet.generate_tasks():
                task.owner = self
                tasks.append(task)
        return tasks


@dataclass
class Task:
    title: str
    duration_minutes: int
    priority: Priority = Priority.MEDIUM
    fixed_time: time | None = None
    is_flexible: bool = True
    pet: Pet | None = None
    owner: Owner | None = None
    completed: bool = False

    @property
    def is_fixed(self) -> bool:
        """True when the task is pinned to a specific time and cannot move."""
        return self.fixed_time is not None and not self.is_flexible

    def mark_complete(self) -> None:
        """Mark this task as done."""
        self.completed = True

    def mark_incomplete(self) -> None:
        """Mark this task as not yet done."""
        self.completed = False


@dataclass
class DayWindow:
    start: time
    end: time

    def total_minutes(self) -> int:
        """Length of the available window in minutes (0 if end precedes start)."""
        return max(0, _to_minutes(self.end) - _to_minutes(self.start))


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
        lines: list[str] = []
        if self.items:
            lines.append("Planned tasks:")
            for item in self.items:
                pet = f" for {item.task.pet.name}" if item.task.pet else ""
                lines.append(
                    f"  {item.start.strftime('%H:%M')}–{item.end.strftime('%H:%M')} "
                    f"— {item.task.title}{pet} "
                    f"[{item.task.priority.name.lower()}] — {item.reason}"
                )
        else:
            lines.append("Planned tasks: none.")

        if self.unscheduled:
            lines.append("")
            lines.append("Could not schedule:")
            for task in self.unscheduled:
                lines.append(
                    f"  — {task.title} "
                    f"[{task.priority.name.lower()}, {task.duration_minutes} min]"
                )
        return "\n".join(lines)


class Scheduler:
    """The brain: retrieves, organizes, and places tasks across pets."""

    def build_plan(self, tasks: list[Task], window: DayWindow) -> Plan:
        """Order and place tasks within the day window and return a Plan.

        Strategy:
          1. Pinned tasks (``is_fixed``) claim their exact slot first. Any that
             fall outside the window or collide with an earlier pinned task are
             left unscheduled.
          2. Remaining flexible tasks are sorted by priority (high → low), then
             by duration (longest first so big-ticket items aren't crowded out),
             and greedily dropped into the earliest free gap that fits.
          3. Anything that can't fit the remaining free time is reported back in
             ``Plan.unscheduled`` rather than silently dropped.
        """
        plan = Plan()

        pending = [t for t in tasks if not t.completed]
        win_start = _to_minutes(window.start)
        win_end = _to_minutes(window.end)

        # Busy intervals as (start_min, end_min); kept sorted by start.
        busy: list[tuple[int, int]] = []

        # --- 1. Place pinned tasks -------------------------------------- #
        fixed = [t for t in pending if t.is_fixed]
        flexible = [t for t in pending if not t.is_fixed]

        fixed.sort(key=lambda t: _to_minutes(t.fixed_time))  # type: ignore[arg-type]
        for task in fixed:
            start = _to_minutes(task.fixed_time)  # type: ignore[arg-type]
            end = start + task.duration_minutes
            if start < win_start or end > win_end:
                plan.unscheduled.append(task)
                continue
            if self._overlaps(start, end, busy):
                plan.unscheduled.append(task)
                continue
            busy.append((start, end))
            busy.sort()
            plan.items.append(
                ScheduledTask(
                    task=task,
                    start=_to_time(start),
                    end=_to_time(end),
                    reason=f"pinned to {task.fixed_time.strftime('%H:%M')}",  # type: ignore[union-attr]
                )
            )

        # --- 2. Place flexible tasks by priority, then longest first ---- #
        flexible.sort(key=lambda t: (-t.priority.value, -t.duration_minutes, t.title))
        for task in flexible:
            slot = self._first_fit(task.duration_minutes, win_start, win_end, busy)
            if slot is None:
                plan.unscheduled.append(task)
                continue
            start, end = slot
            busy.append((start, end))
            busy.sort()
            plan.items.append(
                ScheduledTask(
                    task=task,
                    start=_to_time(start),
                    end=_to_time(end),
                    reason=f"{task.priority.name.lower()} priority, placed in earliest open slot",
                )
            )

        plan.items.sort(key=lambda s: _to_minutes(s.start))
        return plan

    @staticmethod
    def _overlaps(start: int, end: int, busy: list[tuple[int, int]]) -> bool:
        """True if [start, end) intersects any existing busy interval."""
        return any(start < b_end and b_start < end for b_start, b_end in busy)

    @staticmethod
    def _first_fit(
        duration: int, win_start: int, win_end: int, busy: list[tuple[int, int]]
    ) -> tuple[int, int] | None:
        """Earliest [start, start+duration) gap inside the window, or None."""
        if duration <= 0 or duration > (win_end - win_start):
            return None
        cursor = win_start
        for b_start, b_end in busy:  # busy is kept sorted by start
            if cursor + duration <= b_start:
                return (cursor, cursor + duration)
            cursor = max(cursor, b_end)
        if cursor + duration <= win_end:
            return (cursor, cursor + duration)
        return None
