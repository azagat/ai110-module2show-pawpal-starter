# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## 🖥️ Sample Output

Paste a sample of your app's CLI or Streamlit output here so a reader can see what a generated plan looks like:

```
Planned tasks: 08:00–08:20 — Morning walk (Mochi) for Mochi [high] — pinned to 08:00 10:00–10:10 — Medication for Snow [high] — pinned to 10:00 16:00–16:20 — Bath for Mochi for Mochi [medium] — pinned to 16:00Could not schedule: — Morning walk (Snow) [high, 20 min] — time conflict at 08:00 with an earlier pinned task
```

## 🧪 Testing PawPal+

```bash
# Run the full test suite:
pytest

# Run with coverage:
pytest --cov
```

Sample test output:

```
============================================
Today's Schedule for Jordan
(pets: Mochi, Biscuit)
============================================
Planned tasks:
  08:00–08:30 — Morning walk for Mochi [high] — pinned to 08:00
  08:30–09:00 — Grooming for Biscuit [low] — low priority, placed in earliest open slot
  09:00–09:10 — Breakfast for Biscuit [high] — pinned to 09:00
  09:10–09:55 — Afternoon play for Mochi [medium] — medium priority, placed in earliest open slot
  10:00–10:15 — Litter box cleanup for Biscuit [medium] — pinned to 10:00
============================================
```

Sample pytest output:

```
==================================== 13 passed in 0.02s ====================================
```

## 📐 Smarter Scheduling

> Fill in once you've implemented scheduling logic.

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Task sorting | `sort_tasks(tasks, by="time")`, `Scheduler.build_plan` | Current-tasks list is shown earliest-pinned first, unpinned tasks last; the scheduler also orders flexible tasks by priority (high→low) then longest-first. |
| Filtering | `filter_tasks(tasks, pet=, status=, priority=, on_date=)`, `Owner.tasks_for` | App has "Filter by pet" and "Filter by status" dropdowns; a Done/Skip/Reset control changes a task's `TaskStatus` (pending/done/skipped) so only pending tasks get scheduled. |
| Conflict handling | `detect_conflicts(tasks)`, `Scheduler._overlaps` | Overlapping pinned tasks are flagged before scheduling via `Conflict.describe()`; unschedulable tasks report *why* (outside window vs. time conflict vs. no open slot). |
| Recurring tasks | `Task.occurs_on(date)`, `Recurrence` (`NONE`/`DAILY`/`WEEKLY`/`EVERY_N_DAYS`) | Task form sets a repeat rule, `Starts on` anchor date, and `Every N days` interval; the "Plan for" date filters tasks to only those occurring that day. |

## 📸 Demo Walkthrough

Describe your app in numbered steps so a reader can follow along without watching a video:

1. Input user name
2. Input pet name(s) ("Snow, dog" and "Ralph, dog")
3. Add morning walk for Snow at 8:00 daily, add afternoon walk for Ralph at a later time (12:00) - add tasks 
4. Update Snow's morning walk to done
5. Filter by status, put done (should show Snow's walk)

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->
