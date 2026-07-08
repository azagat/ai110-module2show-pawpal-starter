"""Tests for core PawPal+ behaviors.

Run from the project root with:  pytest
"""

import os
import sys

# Make the project root importable when running pytest from anywhere.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date, time

from pawpal_system import (
    DayWindow,
    Owner,
    Pet,
    Priority,
    Recurrence,
    Scheduler,
    Task,
    TaskStatus,
    detect_conflicts,
    filter_tasks,
    sort_tasks,
)


def test_mark_complete_changes_status():
    """Calling mark_complete() flips a task from incomplete to complete."""
    task = Task("Morning walk", duration_minutes=30, priority=Priority.HIGH)

    assert task.completed is False  # tasks start out incomplete

    task.mark_complete()

    assert task.completed is True
    assert task.status is TaskStatus.DONE


def test_mark_skipped_is_not_completed():
    """A skipped task is neither pending nor completed."""
    task = Task("Grooming", duration_minutes=20)

    task.mark_skipped()

    assert task.status is TaskStatus.SKIPPED
    assert task.completed is False


def test_add_task_increases_pet_task_count():
    """Adding a task to a Pet increases that pet's task count."""
    pet = Pet(name="Mochi", species="dog")

    assert len(pet.tasks) == 0

    pet.add_task(Task("Feeding", duration_minutes=10))

    assert len(pet.tasks) == 1


# --- Sorting -------------------------------------------------------------- #
def test_sort_tasks_by_time_puts_earliest_first_and_unpinned_last():
    a = Task("A", 10, fixed_time=time(9, 0), is_flexible=False)
    b = Task("B", 10, fixed_time=time(7, 0), is_flexible=False)
    unpinned = Task("C", 10)

    ordered = sort_tasks([a, unpinned, b], by="time")

    assert [t.title for t in ordered] == ["B", "A", "C"]


def test_sort_tasks_does_not_mutate_input():
    tasks = [Task("A", 10, fixed_time=time(9, 0)), Task("B", 10, fixed_time=time(7, 0))]
    original = list(tasks)

    sort_tasks(tasks, by="time")

    assert tasks == original


# --- Filtering ------------------------------------------------------------ #
def test_filter_tasks_by_pet_and_status():
    mochi = Pet(name="Mochi", species="dog")
    biscuit = Pet(name="Biscuit", species="cat")
    t1 = Task("Walk", 10, pet=mochi)
    t2 = Task("Feed", 10, pet=biscuit)
    t3 = Task("Play", 10, pet=mochi)
    t3.mark_complete()

    pending_for_mochi = filter_tasks(
        [t1, t2, t3], pet="Mochi", status=TaskStatus.PENDING
    )

    assert pending_for_mochi == [t1]


def test_owner_tasks_for_returns_only_that_pets_tasks():
    owner = Owner(name="Jordan")
    mochi = Pet(name="Mochi", species="dog")
    biscuit = Pet(name="Biscuit", species="cat")
    owner.add_pet(mochi)
    owner.add_pet(biscuit)
    mochi.add_task(Task("Walk", 10))
    biscuit.add_task(Task("Feed", 10))

    result = owner.tasks_for(mochi)

    assert [t.title for t in result] == ["Walk"]


# --- Recurrence ----------------------------------------------------------- #
def test_weekly_task_only_occurs_every_seven_days():
    anchor = date(2026, 7, 6)  # a Monday
    task = Task("Bath", 30, recurrence=Recurrence.WEEKLY, start_date=anchor)

    assert task.occurs_on(anchor) is True
    assert task.occurs_on(date(2026, 7, 7)) is False
    assert task.occurs_on(date(2026, 7, 13)) is True


def test_every_n_days_respects_interval():
    anchor = date(2026, 7, 1)
    task = Task(
        "Flea meds", 5, recurrence=Recurrence.EVERY_N_DAYS, interval_days=3,
        start_date=anchor,
    )

    assert task.occurs_on(date(2026, 7, 4)) is True
    assert task.occurs_on(date(2026, 7, 5)) is False


# --- Conflict detection --------------------------------------------------- #
def test_detect_conflicts_flags_overlapping_pinned_tasks():
    a = Task("Walk", 30, fixed_time=time(8, 0), is_flexible=False)
    b = Task("Vet", 30, fixed_time=time(8, 15), is_flexible=False)
    c = Task("Feed", 10, fixed_time=time(9, 30), is_flexible=False)

    conflicts = detect_conflicts([a, b, c])

    assert len(conflicts) == 1
    assert {conflicts[0].a.title, conflicts[0].b.title} == {"Walk", "Vet"}


def test_no_conflict_for_back_to_back_tasks():
    a = Task("Walk", 30, fixed_time=time(8, 0), is_flexible=False)
    b = Task("Vet", 30, fixed_time=time(8, 30), is_flexible=False)

    assert detect_conflicts([a, b]) == []


# --- Plan summary + scheduler status handling ----------------------------- #
def test_plan_reports_scheduled_and_free_minutes():
    window = DayWindow(start=time(8, 0), end=time(9, 0))
    task = Task("Walk", 30)

    plan = Scheduler().build_plan([task], window)

    assert plan.total_scheduled_minutes() == 30
    assert plan.free_minutes(window) == 30


def test_skipped_tasks_are_not_scheduled():
    window = DayWindow(start=time(8, 0), end=time(18, 0))
    task = Task("Grooming", 30)
    task.mark_skipped()

    plan = Scheduler().build_plan([task], window)

    assert plan.items == []
