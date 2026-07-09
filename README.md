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
#My example first draft:
Owner: Cristina
  Pet: Bella (12.5 kg)
    Task: Morning walk [daily] at 07:30
    Task: Evening feeding [daily] at 18:00
  Pet: Milo (4.2 kg)
    Task: Litter box change [weekly] at 12:15


```Ideal output:
# e.g.:
# Daily plan for Biscuit (Golden Retriever):
#   08:00 — Morning walk (30 min) [priority: high]
#   09:00 — Feeding (10 min) [priority: high]
#   ...
```

## 🧪 Testing PawPal+
My tests include verifying tasks for today are shown in chronological order, testing back-to-back scheduling works, testing whether a warning is given if a duration of a previous task overlaps with a new one. As well as testing that one off tasks are allowed besides (daily, weekly) tasks.

My confidence level is 3 out of 5 stars regarding system reliability. I noted trade offs that AI warned about what is out of scope for the system like midnight scheduling overlapping between a previous and next day (not showing up on next day). I believe it addresses basic needs and functionality.
```bash
# Run the full test suite:
pytest
================================================================= 25 passed in 0.21s =================================================================
# Run with coverage:
pytest --cov
```

Sample test output:

```
# Paste your pytest output here

(.venv) PS C:\Users\crist\OneDrive\AI Course 2026\ai110-module2show-pawpal> python -m pytest
================================================================ test session starts =================================================================
platform win32 -- Python 3.13.13, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\crist\OneDrive\AI Course 2026\ai110-module2show-pawpal
collected 25 items                                                                                                                                    

tests\test_pawpal.py .........................                                                                                                  [100%]

================================================================= 25 passed in 0.10s =================================================================


```

## 📐 Smarter Scheduling

> Fill in once you've implemented scheduling logic.

### Priority-aware day planning
`build_day_plan()` — Produces an ordered daily plan under two rules: owner-set
times are **hard anchors** (never moved), and remaining flexible tasks are placed
high → medium → low (ties broken by longer duration, then name). Each task is slotted
into the **earliest free gap** that clears all existing commitments (a greedy
first-fit over busy intervals). Placement is **sticky** — once PawPal assigns a time
it is treated like an owner anchor and is never reshuffled by a later call, so
completing or adding a task doesn't disturb decided times. Overbooked tasks (no room
before `day_end`) are still placed rather than dropped, and flagged as such.

### Re-planning (escape hatch)
`replan_day()` — Deliberately releases every *auto-assigned* slot for a day back to
flexible (leaving owner anchors intact) and re-runs the planner from scratch by
current priority. Intended for an explicit "Re-plan" action, not automatic reruns.

### Plan explanations
`explain_plan()`, `PlannedItem.reason` — Every planned task carries a
human-readable reason ("Fixed at 07:30 — you set this time", "Auto-scheduled at
09:00, after Bella's walk", "…the day is overbooked"), so the reviewer/owner sees
*why* each task landed where it did.

### Sorting
`sort_by_time()`, `sort_by_datetime()` — Order occurrences by time-of-day (single-day
rhythm) or true (date, time) chronological order (multi-day timeline). Flexible
occurrences with no time yet sort **last**, after every placed time.

### Conflict detection
`detect_conflicts()` — Flags occurrences whose `[start, start + duration)` windows
overlap (same pet or different pets). Same start time always conflicts (so
zero-duration tasks clash); back-to-back tasks (one ends exactly as the next begins)
do **not**. Compares only occurrences on the same date, so a recurring task never
conflicts with itself across days. Returns plain-text warnings, never raises.
*Out of scope:* midnight-crossing durations are not wrapped to the next day.

### Recurring tasks
`generate_occurrences()`, `_extend_task()`, `Schedule.next_due_date()` — Materializes
daily/weekly occurrences forward to a horizon date. **Idempotent**: it resumes from
the latest occurrence per (time, recurrence) slot, so re-running adds no duplicates.
Independent of completion — a skipped day still leaves a due occurrence. Supports
`daily`, `weekly`, and `once`; `monthly` is deliberately rejected at construction
(a fixed day-count can't represent 28–31 day months).

### Filtering & per-day status
`get_pending_tasks()`, `filter_by_status()`, `filter_by_pet()` — Filter tasks by
today's pending occurrences, aggregate completion status, or by pet (matched by
identity). Note the per-day vs. aggregate distinction: `get_pending_tasks()` empties
once a day's occurrences are done, while `filter_by_status()` reads the aggregate
`Task.is_done`.

### Per-occurrence completion
`mark_done()`, `Schedule.completed`, `Task.is_done_on()` — Completion lives on each
`Schedule`, so marking the 07:30 feeding done leaves the 18:00 feeding pending.
`is_done_on()` answers the per-day question ("did I feed Bella today?").


| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Task sorting |_all_occurrences(),sort_by_time(), sort_by_datetime() | e.g., by each task's specific schedule (date, time). Might clash with regard to duration |
| Filtering | filter_by_pet(), filter_by_status() | Filter by pet, or task completion status. |
| Conflict handling |detect_conflicts() | Overlapping time slots |
| Recurring tasks | _extend_task(), generate_occurrences() | daily vs. weekly |

## 📸 Demo Walkthrough

Describe your app in numbered steps so a reader can follow along without watching a video:

1. Add pet(s) by including relevant info ->
2.  Add first task to specific pet with prompted info and decide if there is a specific time for task or to let the scheduler decide
3. Add several tasks that differ in priority/duration, if adding a task with a time that clashes with a previous one, a warning should pop up 
4. The option to re-plan a schedule becomes available and effective only when more tasks are added
5. Check off tasks by clicking their respective checkmark from Today's summary; the smart schedule updates accordingly. Upcoming shows up for recurring tasks as well when they were added in Step 2

## 📸 Demo Walkthrough 

1. Enter owner and pet info (name, species, breed, weight) and click **Add pet**. Repeat for multiple pets.

2. Add a task to a chosen pet — set duration, priority, type (daily/weekly/once), and either pick a time or tick **"Let PawPal choose the time"** to leave it flexible.

3. Add several tasks with different priorities and durations. In the **Schedule** section, the **🧠 Smart Plan for Today** orders them (owner-set times stay fixed; flexible ones are placed high-priority-first into the earliest free slot) and prints a short reason for each — this is the plan explanation.

4. If any of today's tasks overlap in time, a conflict warning appears above the checklist.

5. Because assigned times are "sticky" and never shuffle on their own, use **🔄 Re-plan day** to recompute today from scratch by current priority (handy after adding a high-priority task).

6. Check off tasks in the **Today** checklist; the pending count and task table update. **Upcoming** shows the recurring tasks materialized forward through the 7-day horizon.


## CLI output from running main.py
Owner: Cristina

Daily plan for Bella (Beagle):
  08:00 — Give medicine (10 min) [priority: high]
  08:00 — Morning walk (30 min) [priority: high]
  18:00 — Evening feeding (10 min) [priority: medium]

Daily plan for Milo (Tabby Cat):
  08:00 — Morning feeding (15 min) [priority: high]

WARNING: 3 schedule conflict(s) detected:
  - Conflict on 2026-07-08: Bella's Give medicine (08:00–08:10) overlaps Bella's Morning walk (08:00–08:30)
  - Conflict on 2026-07-08: Bella's Give medicine (08:00–08:10) overlaps Milo's Morning feeding (08:00–08:15)
  - Conflict on 2026-07-08: Bella's Morning walk (08:00–08:30) overlaps Milo's Morning feeding (08:00–08:15)


**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->


