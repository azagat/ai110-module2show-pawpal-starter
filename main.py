"""PawPal+ demo script.

Builds a small owner/pet/task setup and prints today's schedule to the
terminal. Run with:  python main.py
"""

from datetime import time

from pawpal_system import (
    Owner,
    Pet,
    Task,
    Priority,
    DayWindow,
    Scheduler,
)


def build_owner() -> Owner:
    """Create an owner with two pets."""
    owner = Owner(name="Jordan", age=29)

    mochi = Pet(name="Mochi", species="dog", breed="Shiba Inu", age=3, preferred_food="kibble")
    biscuit = Pet(name="Biscuit", species="cat", breed="Tabby", age=5, preferred_food="wet food")

    owner.add_pet(mochi)
    owner.add_pet(biscuit)
    return owner


def build_tasks(owner: Owner) -> list[Task]:
    """Create several care tasks at different times for the owner's pets."""
    mochi, biscuit = owner.pets

    tasks = [
        Task("Morning walk", duration_minutes=30, priority=Priority.HIGH,
             fixed_time=time(8, 0), is_flexible=False, pet=mochi, owner=owner),
        Task("Breakfast", duration_minutes=10, priority=Priority.HIGH,
             fixed_time=time(9, 0), is_flexible=False, pet=biscuit, owner=owner),
        Task("Litter box cleanup", duration_minutes=15, priority=Priority.MEDIUM,
             fixed_time=time(10, 0), is_flexible=False, pet=biscuit, owner=owner),
        Task("Afternoon play", duration_minutes=45, priority=Priority.MEDIUM,
             pet=mochi, owner=owner),
        Task("Grooming", duration_minutes=30, priority=Priority.LOW,
             pet=biscuit, owner=owner),
    ]
    return tasks


def main() -> None:
    owner = build_owner()
    tasks = build_tasks(owner)

    window = DayWindow(start=time(8, 0), end=time(12, 0))
    plan = Scheduler().build_plan(tasks, window)

    print("=" * 44)
    print(f"Today's Schedule for {owner.name}")
    print(f"(pets: {', '.join(p.name for p in owner.pets)})")
    print("=" * 44)
    print(plan.explain())
    print("=" * 44)


if __name__ == "__main__":
    main()
