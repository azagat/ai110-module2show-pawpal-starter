"""Tests for core PawPal+ behaviors.

Run from the project root with:  pytest
"""

import os
import sys

# Make the project root importable when running pytest from anywhere.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pawpal_system import Pet, Task, Priority


def test_mark_complete_changes_status():
    """Calling mark_complete() flips a task from incomplete to complete."""
    task = Task("Morning walk", duration_minutes=30, priority=Priority.HIGH)

    assert task.completed is False  # tasks start out incomplete

    task.mark_complete()

    assert task.completed is True


def test_add_task_increases_pet_task_count():
    """Adding a task to a Pet increases that pet's task count."""
    pet = Pet(name="Mochi", species="dog")

    assert len(pet.tasks) == 0

    pet.add_task(Task("Feeding", duration_minutes=10))

    assert len(pet.tasks) == 1
