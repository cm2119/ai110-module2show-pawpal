from datetime import date, time, timedelta

import streamlit as st
from pawpal_system import Owner, Pet, Schedule, Scheduler, Task

# How many days ahead to materialize the recurring calendar.
SCHEDULE_HORIZON_DAYS = 7

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

st.markdown(
    """
Welcome to **PawPal+**, a pet care planning assistant.

Add your pets and their care tasks below. Each task has a time of day and a
recurrence (daily/weekly); PawPal+ generates the upcoming calendar and lets you
check off today's tasks.
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

st.subheader("Quick Demo Inputs (UI only)")
owner_name = st.text_input("Owner name", value="Jordan")
pet_name = st.text_input("Pet name", value="Mochi")
species = st.selectbox("Species", ["dog", "cat", "other"])
breed = st.text_input("Breed", value="")
weight = st.number_input("Weight (kg)", min_value=0.1, max_value=200.0, value=5.0)

# Create the Owner once and keep it in the session vault (see tasks guard below).
if "owner" not in st.session_state:
    st.session_state.owner = Owner(name=owner_name)
owner = st.session_state.owner

if st.button("Add pet"):
    owner.add_pet(Pet(name=pet_name, weight=float(weight), breed=breed))
    st.success(f"Added {pet_name} to {owner.name}'s pets.")

if owner.pets:
    st.write("Current pets:")
    for pet in owner.pets:
        label = f"- {pet.name} ({pet.weight} kg)"
        if pet.breed:
            label += f" — {pet.breed}"
        st.write(label)
else:
    st.info("No pets yet. Add one above.")

st.markdown("### Tasks")
st.caption("Add a few tasks. These attach to a pet and feed into your scheduler.")

if not owner.pets:
    st.info("Add a pet first — tasks are assigned to a pet.")
else:
    # Choose which pet this task belongs to.
    pet_names = [pet.name for pet in owner.pets]
    selected_pet_name = st.selectbox("Assign to pet", pet_names)
    selected_pet = next(pet for pet in owner.pets if pet.name == selected_pet_name)

    col1, col2, col3 = st.columns(3)
    with col1:
        task_title = st.text_input("Task title", value="Morning walk")
    with col2:
        duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
    with col3:
        priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)
    col_type, col_time = st.columns(2)
    with col_type:
        task_type = st.selectbox("Type", ["daily", "weekly", "monthly"])
    with col_time:
        time_of_day = st.time_input("Time of day", value=time(8, 0))

    if st.button("Add task"):
        task = Task(
            name=task_title,
            type=task_type,
            pet=selected_pet,
            duration_minutes=int(duration),
            priority=priority,
        )
        # Seed a first occurrence (due today); generate_occurrences() extends it
        # forward for daily/weekly tasks. recurrence mirrors the task type.
        task.add_schedule(
            Schedule(task=task, time_of_day=time_of_day, recurrence=task_type)
        )
        selected_pet.add_task(task)
        st.success(
            f"Added '{task_title}' at {time_of_day.strftime('%H:%M')} "
            f"to {selected_pet.name}."
        )

    all_tasks = owner.get_all_tasks()
    if all_tasks:
        st.write("Current tasks:")
        st.table(
            [
                {
                    "pet": task.pet.name,
                    "title": task.name,
                    "type": task.type,
                    "duration_minutes": task.duration_minutes,
                    "priority": task.priority,
                    "completed": task.is_done,
                }
                for task in all_tasks
            ]
        )
    else:
        st.info("No tasks yet. Add one above.")

st.divider()

st.subheader("Schedule")

scheduler = Scheduler(owner=owner)
today = date.today()
horizon = today + timedelta(days=SCHEDULE_HORIZON_DAYS)

# Materialize the recurring calendar up front. This is idempotent and runs on
# every rerun, so the schedule stays filled to the horizon regardless of what
# has been completed — a skipped day still shows a due occurrence.
scheduler.generate_occurrences(horizon)

all_occurrences = scheduler.sort_by_datetime()
if not all_occurrences:
    st.info("No scheduled occurrences yet. Add a task with a time above.")
else:
    # Warn about clashing occurrences for today (two tasks at the same time).
    for message in scheduler.detect_conflicts(today):
        st.warning(message)

    # Today's checklist: per-occurrence completion for the current day.
    st.markdown(f"**Today — {today}**")
    today_occurrences = [s for s in all_occurrences if s.due_date == today]
    if not today_occurrences:
        st.caption("Nothing scheduled for today.")
    for occ in today_occurrences:
        label = (
            f"{occ.time_of_day.strftime('%H:%M')} — "
            f"{occ.task.pet.name}: {occ.task.name}"
        )
        # Key by object identity: unique per occurrence and stable across
        # reruns (occurrences persist in session_state), so two same-name tasks
        # at the same time — exactly the conflict case — don't collide.
        key = f"done::{id(occ)}"
        done = st.checkbox(label, value=occ.completed, key=key)
        scheduler.mark_done(occ, done)

    pending_today = scheduler.get_pending_tasks(today)
    st.caption(
        f"{len(pending_today)} task(s) still pending today."
        if pending_today
        else "All of today's tasks are done. 🎉"
    )

    # Upcoming timeline through the horizon (read-only). all_occurrences is
    # already in (date, time) order from sort_by_datetime(), so just window it.
    st.markdown(f"**Upcoming — through {horizon}**")
    upcoming = [s for s in all_occurrences if today <= s.due_date <= horizon]
    st.table(
        [
            {
                "date": s.due_date.isoformat(),
                "time": s.time_of_day.strftime("%H:%M"),
                "pet": s.task.pet.name,
                "task": s.task.name,
                "recurrence": s.recurrence,
                "done": s.completed,
            }
            for s in upcoming
        ]
    )
