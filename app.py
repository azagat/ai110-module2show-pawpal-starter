from datetime import date, time

import streamlit as st
from pawpal_system import (
    Owner,
    Pet,
    Task,
    Priority,
    Recurrence,
    TaskStatus,
    DayWindow,
    Scheduler,
    detect_conflicts,
    filter_tasks,
    sort_tasks,
)

PRIORITY_MAP = {"low": Priority.LOW, "medium": Priority.MEDIUM, "high": Priority.HIGH}
RECURRENCE_MAP = {
    "none": Recurrence.NONE,
    "daily": Recurrence.DAILY,
    "weekly": Recurrence.WEEKLY,
    "every N days": Recurrence.EVERY_N_DAYS,
}
STATUS_MAP = {
    "pending": TaskStatus.PENDING,
    "done": TaskStatus.DONE,
    "skipped": TaskStatus.SKIPPED,
}

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

st.markdown(
    """
Welcome to the PawPal+ app!

Use this app to add your pets, create care tasks for them, and generate a daily schedule that fits your tasks into your available time window.
"""
)

with st.expander("Scenario", expanded=True):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.

You will design and implement the scheduling logic and connect it to this Streamlit UI.
"""
    )

with st.expander("What you need to build", expanded=True):
    st.markdown(
        """
At minimum, your system should:
- Represent pet care tasks (what needs to happen, how long it takes, priority)
- Represent the pet and the owner (basic info and preferences)
- Build a plan/schedule for a day that chooses and orders tasks based on constraints
- Explain the plan (why each task was chosen and when it happens)
"""
    )

st.divider()

# --- Session vault: hold the Owner across reruns -------------------------- #
owner_name = st.text_input("Owner name", value="Jordan")
if "owner" not in st.session_state:
    st.session_state.owner = Owner(name=owner_name)
owner = st.session_state.owner
owner.name = owner_name  # keep in sync with the input

# --- Adding a Pet --------------------------------------------------------- #
st.subheader("Add a Pet")
pcol1, pcol2 = st.columns(2)
with pcol1:
    pet_name = st.text_input("Pet name", value="Mochi")
with pcol2:
    species = st.selectbox("Species", ["dog", "cat", "other"])

if st.button("Add pet"):
    owner.add_pet(Pet(name=pet_name, species=species))
    st.success(f"Added {pet_name} the {species}.")

if owner.pets:
    st.write("Current pets:")
    st.table([{"name": p.name, "species": p.species} for p in owner.pets])
else:
    st.info("No pets yet. Add one above.")

st.divider()

# --- Scheduling a Task ---------------------------------------------------- #
st.subheader("Add a Task")
st.caption("Tasks are attached to a pet and fed into the scheduler.")

if not owner.pets:
    st.warning("Add a pet first, then you can add tasks for it.")
else:
    which_pet = st.selectbox("For which pet?", [p.name for p in owner.pets])

    col1, col2, col3 = st.columns(3)
    with col1:
        task_title = st.text_input("Task title", value="Morning walk")
    with col2:
        duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
    with col3:
        priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)

    pin_it = st.checkbox("Pin to a specific time")
    fixed_time = st.time_input("Fixed time", value=time(8, 0)) if pin_it else None

    rcol1, rcol2, rcol3 = st.columns(3)
    with rcol1:
        recurrence = st.selectbox("Repeats", list(RECURRENCE_MAP.keys()))
    recurs = RECURRENCE_MAP[recurrence] is not Recurrence.NONE
    with rcol2:
        start_date = (
            st.date_input("Starts on", value=date.today()) if recurs else None
        )
    with rcol3:
        interval_days = st.number_input(
            "Every N days",
            min_value=1,
            max_value=30,
            value=2,
            disabled=RECURRENCE_MAP[recurrence] is not Recurrence.EVERY_N_DAYS,
        )

    if st.button("Add task"):
        pet = next(p for p in owner.pets if p.name == which_pet)
        pet.add_task(
            Task(
                title=task_title,
                duration_minutes=int(duration),
                priority=PRIORITY_MAP[priority],
                fixed_time=fixed_time,
                is_flexible=not pin_it,
                recurrence=RECURRENCE_MAP[recurrence],
                start_date=start_date,
                interval_days=int(interval_days),
            )
        )
        st.success(f"Added '{task_title}' for {which_pet}.")

    all_tasks = owner.all_tasks()
    if all_tasks:
        st.write("Current tasks:")

        # --- Filter + sort controls ------------------------------------- #
        fcol1, fcol2 = st.columns(2)
        with fcol1:
            pet_filter = st.selectbox(
                "Filter by pet", ["all"] + [p.name for p in owner.pets]
            )
        with fcol2:
            status_filter = st.selectbox(
                "Filter by status", ["all"] + list(STATUS_MAP.keys())
            )

        shown = filter_tasks(
            all_tasks,
            pet=None if pet_filter == "all" else pet_filter,
            status=None if status_filter == "all" else STATUS_MAP[status_filter],
        )
        shown = sort_tasks(shown, by="time")  # earliest pinned first, unpinned last

        if shown:
            st.table(
                [
                    {
                        "pet": t.pet.name if t.pet else "",
                        "title": t.title,
                        "duration_minutes": t.duration_minutes,
                        "priority": t.priority.name.lower(),
                        "fixed_time": t.fixed_time.strftime("%H:%M") if t.fixed_time else "—",
                        "repeats": t.recurrence.value,
                        "status": t.status.value,
                    }
                    for t in shown
                ]
            )
        else:
            st.info("No tasks match the current filters.")

        # --- Update a task's status ------------------------------------- #
        labels = [
            f"{i}: {t.title} ({t.pet.name if t.pet else '—'})"
            for i, t in enumerate(all_tasks)
        ]
        scol1, scol2, scol3, scol4 = st.columns([3, 1, 1, 1])
        with scol1:
            chosen = st.selectbox("Update status for", labels)
        chosen_task = all_tasks[labels.index(chosen)]
        with scol2:
            if st.button("Done"):
                chosen_task.mark_complete()
                st.rerun()
        with scol3:
            if st.button("Skip"):
                chosen_task.mark_skipped()
                st.rerun()
        with scol4:
            if st.button("Reset"):
                chosen_task.mark_incomplete()
                st.rerun()
    else:
        st.info("No tasks yet. Add one above.")

st.divider()

# --- Build the schedule --------------------------------------------------- #
st.subheader("Build Schedule")
st.caption("Places all tasks within your available window using the Scheduler.")

wcol1, wcol2, wcol3 = st.columns(3)
with wcol1:
    day_start = st.time_input("Day starts", value=time(8, 0))
with wcol2:
    day_end = st.time_input("Day ends", value=time(18, 0))
with wcol3:
    plan_date = st.date_input("Plan for", value=date.today())

if st.button("Generate schedule"):
    window = DayWindow(start=day_start, end=day_end)

    if not window.is_valid():
        st.error("The day window must end after it starts (overnight windows aren't supported).")
        st.stop()

    # Only tasks that actually occur on the chosen date (handles recurrence).
    tasks_today = filter_tasks(owner.all_tasks(), on_date=plan_date)

    conflicts = detect_conflicts(tasks_today)
    if conflicts:
        st.warning("Heads up — these pinned tasks overlap:")
        for c in conflicts:
            st.write(f"• {c.describe()}")

    plan = Scheduler().build_plan(tasks_today, window)

    if plan.items:
        st.write(f"### Today's Schedule for {owner.name}")
        st.caption(
            f"{plan.total_scheduled_minutes()} min scheduled · "
            f"{plan.free_minutes(window)} min free"
        )
        st.table(
            [
                {
                    "start": item.start.strftime("%H:%M"),
                    "end": item.end.strftime("%H:%M"),
                    "task": item.task.title,
                    "pet": item.task.pet.name if item.task.pet else "",
                    "priority": item.task.priority.name.lower(),
                    "why": item.reason,
                }
                for item in plan.items
            ]
        )
    else:
        st.info("Nothing could be scheduled in this window.")

    if plan.unscheduled:
        st.warning("Could not fit these tasks:")
        st.table(
            [
                {
                    "title": entry.task.title,
                    "duration_minutes": entry.task.duration_minutes,
                    "priority": entry.task.priority.name.lower(),
                    "why": entry.reason,
                }
                for entry in plan.unscheduled
            ]
        )

    with st.expander("Explanation"):
        st.text(plan.explain())
