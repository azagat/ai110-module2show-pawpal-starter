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
from datetime import date, time
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


class TaskStatus(Enum):
    """Where a task is in its life cycle.

    ``PENDING`` tasks are the only ones the scheduler will try to place;
    ``DONE`` and ``SKIPPED`` are kept around for history and filtering.
    """

    PENDING = "pending"
    DONE = "done"
    SKIPPED = "skipped"


class Recurrence(Enum):
    """How often a task repeats.

    ``NONE`` is a one-off. ``DAILY``/``WEEKLY`` repeat relative to the task's
    ``start_date`` anchor (see ``Task.occurs_on``). ``EVERY_N_DAYS`` uses the
    task's ``interval_days`` so the owner can say "every 3 days".
    """

    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    EVERY_N_DAYS = "every_n_days"


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

    def tasks_for(self, pet: "Pet | str") -> list["Task"]:
        """All tasks belonging to one pet (accepts a Pet or its name)."""
        return filter_tasks(self.all_tasks(), pet=pet)


@dataclass
class Task:
    title: str
    duration_minutes: int
    priority: Priority = Priority.MEDIUM
    fixed_time: time | None = None
    is_flexible: bool = True
    pet: Pet | None = None
    owner: Owner | None = None
    status: TaskStatus = TaskStatus.PENDING
    recurrence: Recurrence = Recurrence.NONE
    start_date: date | None = None
    interval_days: int = 1

    @property
    def is_fixed(self) -> bool:
        """True when the task is pinned to a specific time and cannot move."""
        return self.fixed_time is not None and not self.is_flexible

    @property
    def completed(self) -> bool:
        """Backwards-compatible view of status: True only when done."""
        return self.status is TaskStatus.DONE

    def mark_complete(self) -> None:
        """Mark this task as done."""
        self.status = TaskStatus.DONE

    def mark_incomplete(self) -> None:
        """Mark this task as not yet done (back to pending)."""
        self.status = TaskStatus.PENDING

    def mark_skipped(self) -> None:
        """Mark this task as intentionally skipped for the day."""
        self.status = TaskStatus.SKIPPED

    def occurs_on(self, target: date) -> bool:
        """True if this task should appear on ``target``.

        A non-recurring task occurs on its ``start_date`` (or on any day if it
        has no anchor). Recurring tasks repeat forward from ``start_date``:
        ``DAILY`` every day, ``WEEKLY`` every 7 days, and ``EVERY_N_DAYS`` every
        ``interval_days`` days. Recurring tasks with no anchor are treated as
        occurring every day.
        """
        if self.recurrence is Recurrence.NONE:
            return self.start_date is None or self.start_date == target
        if self.start_date is None:
            return True
        if target < self.start_date:
            return False
        delta = (target - self.start_date).days
        if self.recurrence is Recurrence.DAILY:
            return True
        if self.recurrence is Recurrence.WEEKLY:
            return delta % 7 == 0
        if self.recurrence is Recurrence.EVERY_N_DAYS:
            return delta % max(1, self.interval_days) == 0
        return False


@dataclass
class DayWindow:
    start: time
    end: time

    def total_minutes(self) -> int:
        """Length of the available window in minutes (0 if end precedes start)."""
        return max(0, _to_minutes(self.end) - _to_minutes(self.start))

    def is_valid(self) -> bool:
        """True when the window actually has time in it (end after start).

        Guards against a silently empty schedule when a window is entered
        backwards (e.g. 6pm–8am); overnight windows are not supported.
        """
        return _to_minutes(self.end) > _to_minutes(self.start)


@dataclass
class ScheduledTask:
    task: Task
    start: time
    end: time
    reason: str = ""


@dataclass
class UnscheduledTask:
    """A task the scheduler could not place, with the reason why."""

    task: Task
    reason: str = ""


@dataclass
class Plan:
    items: list[ScheduledTask] = field(default_factory=list)
    unscheduled: list[UnscheduledTask] = field(default_factory=list)

    def total_scheduled_minutes(self) -> int:
        """Total minutes of care work actually placed in the day."""
        return sum(
            _to_minutes(item.end) - _to_minutes(item.start) for item in self.items
        )

    def free_minutes(self, window: "DayWindow") -> int:
        """Minutes still open in ``window`` after placing the scheduled tasks."""
        return max(0, window.total_minutes() - self.total_scheduled_minutes())

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
            for entry in self.unscheduled:
                task = entry.task
                why = f" — {entry.reason}" if entry.reason else ""
                lines.append(
                    f"  — {task.title} "
                    f"[{task.priority.name.lower()}, {task.duration_minutes} min]{why}"
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

        pending = [t for t in tasks if t.status is TaskStatus.PENDING]
        win_start = _to_minutes(window.start)
        win_end = _to_minutes(window.end)

        # Busy intervals as (start_min, end_min); kept sorted by start.
        busy: list[tuple[int, int]] = []

        # --- 1. Place pinned tasks -------------------------------------- #
        fixed = [t for t in pending if t.is_fixed]
        flexible = [t for t in pending if not t.is_fixed]

        # Cache each pinned task's start-minute once instead of recomputing it.
        fixed_starts = {id(t): _to_minutes(t.fixed_time) for t in fixed}  # type: ignore[arg-type]
        fixed.sort(key=lambda t: fixed_starts[id(t)])
        for task in fixed:
            start = fixed_starts[id(task)]
            end = start + task.duration_minutes
            if start < win_start or end > win_end:
                plan.unscheduled.append(
                    UnscheduledTask(
                        task,
                        reason=f"pinned to {task.fixed_time.strftime('%H:%M')}, "  # type: ignore[union-attr]
                        "which is outside the day window",
                    )
                )
                continue
            if self._overlaps(start, end, busy):
                plan.unscheduled.append(
                    UnscheduledTask(
                        task,
                        reason=f"time conflict at {task.fixed_time.strftime('%H:%M')} "  # type: ignore[union-attr]
                        "with an earlier pinned task",
                    )
                )
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
                plan.unscheduled.append(
                    UnscheduledTask(
                        task, reason="no open slot long enough in the remaining free time"
                    )
                )
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


# --------------------------------------------------------------------------- #
# Task list helpers: sorting, filtering, and conflict detection
#
# These are pure functions on plain task lists, kept out of the Scheduler so the
# UI (or anything else) can reuse them without building a full plan.
# --------------------------------------------------------------------------- #

# Unpinned tasks (no fixed_time) sort after every pinned task in a time sort.
_UNPINNED_SORT_KEY = 24 * 60 + 1


def sort_tasks(tasks: list[Task], by: str = "time") -> list[Task]:
    """Return a new list of ``tasks`` in a stable, predictable order.

    ``by="time"``     — by fixed_time (unpinned tasks last), then priority
                        (high first), then title.
    ``by="priority"`` — by priority (high first), then fixed_time, then title.

    The input list is not mutated.
    """

    def time_key(t: Task) -> int:
        return _to_minutes(t.fixed_time) if t.fixed_time is not None else _UNPINNED_SORT_KEY

    if by == "priority":
        return sorted(tasks, key=lambda t: (-t.priority.value, time_key(t), t.title))
    if by == "time":
        return sorted(tasks, key=lambda t: (time_key(t), -t.priority.value, t.title))
    raise ValueError(f"unknown sort key: {by!r} (expected 'time' or 'priority')")


def filter_tasks(
    tasks: list[Task],
    *,
    pet: "Pet | str | None" = None,
    status: TaskStatus | None = None,
    priority: Priority | None = None,
    on_date: date | None = None,
) -> list[Task]:
    """Return the tasks matching every supplied criterion (single pass).

    All filters are optional and combined with AND. ``pet`` accepts a ``Pet``
    or a pet name; ``on_date`` keeps only tasks that recur/fall on that date.
    """
    pet_name = pet.name if isinstance(pet, Pet) else pet

    def keep(t: Task) -> bool:
        if pet_name is not None and (t.pet is None or t.pet.name != pet_name):
            return False
        if status is not None and t.status is not status:
            return False
        if priority is not None and t.priority is not priority:
            return False
        if on_date is not None and not t.occurs_on(on_date):
            return False
        return True

    return [t for t in tasks if keep(t)]


@dataclass
class Conflict:
    """Two pinned tasks whose time slots overlap."""

    a: Task
    b: Task

    def describe(self) -> str:
        """Human-readable one-liner for the owner."""
        a_time = self.a.fixed_time.strftime("%H:%M") if self.a.fixed_time else "?"
        b_time = self.b.fixed_time.strftime("%H:%M") if self.b.fixed_time else "?"
        return f"'{self.a.title}' ({a_time}) overlaps '{self.b.title}' ({b_time})"


def detect_conflicts(tasks: list[Task]) -> list[Conflict]:
    """Find overlapping pairs among pinned, pending tasks.

    Only fixed (pinned) tasks can truly conflict — flexible tasks are moved by
    the scheduler. Tasks are sorted by start time and swept once: because the
    list is sorted, the inner loop can stop as soon as a later task starts after
    the current one ends, so this is close to O(n log n) rather than O(n²).
    """
    pinned = sorted(
        (t for t in tasks if t.is_fixed and t.status is TaskStatus.PENDING),
        key=lambda t: _to_minutes(t.fixed_time),  # type: ignore[arg-type]
    )
    conflicts: list[Conflict] = []
    for i, a in enumerate(pinned):
        a_start = _to_minutes(a.fixed_time)  # type: ignore[arg-type]
        a_end = a_start + a.duration_minutes
        for b in pinned[i + 1 :]:
            b_start = _to_minutes(b.fixed_time)  # type: ignore[arg-type]
            if b_start >= a_end:
                break  # sorted by start: nothing later can overlap `a`
            conflicts.append(Conflict(a, b))
    return conflicts
