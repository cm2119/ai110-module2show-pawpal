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

    # Manage pets: edit a pet's info in place or remove it entirely. Both wire
    # straight to the backend (Pet.edit_info / Owner.remove_pet); a rerun then
    # refreshes every downstream read — the tasks table and the scheduler all
    # walk owner.pets, so the change propagates on its own.
    with st.expander("Manage pets"):
        manage_name = st.selectbox(
            "Select a pet to manage",
            [pet.name for pet in owner.pets],
            key="manage_pet",
        )
        managed_pet = next(pet for pet in owner.pets if pet.name == manage_name)

        # Edit form: fields are pre-filled from the selected pet. They carry no
        # widget key, so picking a different pet re-seeds them from that pet's
        # current values on the next rerun.
        with st.form("edit_pet_form"):
            new_name = st.text_input("Name", value=managed_pet.name)
            new_weight = st.number_input(
                "Weight (kg)",
                min_value=0.1,
                max_value=200.0,
                value=float(managed_pet.weight),
            )
            new_breed = st.text_input("Breed", value=managed_pet.breed)
            if st.form_submit_button("Save changes"):
                managed_pet.edit_info(
                    name=new_name, weight=float(new_weight), breed=new_breed
                )
                # A rename means the old name is no longer a valid selectbox
                # option; drop the stored value so Streamlit doesn't try to
                # restore it and error out.
                st.session_state.pop("manage_pet", None)
                st.success(f"Updated {new_name}.")
                st.rerun()

        # Removing a pet also drops its tasks (they live on the pet), so gate it
        # behind a confirm checkbox — a stray click shouldn't wipe a pet and its
        # whole care plan.
        confirm_remove = st.checkbox(
            f"Confirm removal of {managed_pet.name}", key="confirm_remove"
        )
        if st.button("Remove pet", disabled=not confirm_remove):
            owner.remove_pet(managed_pet)
            # Clear widget state tied to the now-gone pet so the selectbox and
            # checkbox don't try to restore values that are no longer valid.
            st.session_state.pop("manage_pet", None)
            st.session_state.pop("confirm_remove", None)
            st.success(f"Removed {manage_name} from {owner.name}'s pets.")
            st.rerun()
else:
    st.info("No pets yet. Add one above.")

# One Scheduler instance drives every read below (the tasks table and the
# calendar), so the UI talks to a single layer. It must be created here, above
# the tasks table, because that table now reads through it. `today` is defined
# here too since the tasks table reports per-day completion (is_done_on).
scheduler = Scheduler(owner=owner)
today = date.today()

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
        task_type = st.selectbox("Type", ["daily", "weekly", "once"])
    with col_time:
        # A flexible task has no owner-set time; the smart planner assigns one
        # by priority. Ticking the box disables (and ignores) the time picker.
        flexible_time = st.checkbox("Let PawPal choose the time")
        picked_time = st.time_input(
            "Time of day", value=time(8, 0), disabled=flexible_time
        )
    time_of_day = None if flexible_time else picked_time

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
        when = (
            "with no fixed time (PawPal will schedule it)"
            if time_of_day is None
            else f"at {time_of_day.strftime('%H:%M')}"
        )
        st.success(f"Added '{task_title}' {when} to {selected_pet.name}.")

    all_tasks = scheduler.get_all_tasks()
    if all_tasks:
        st.write("Current tasks:")

        # Filter the table by pet. Only worth offering once there's more than
        # one pet; "All pets" keeps the full list, otherwise Scheduler
        # .filter_by_pet narrows it to the chosen pet (matched by identity).
        # This scopes only the table below — the remove control still sees every
        # task via all_tasks.
        displayed_tasks = all_tasks
        if len(owner.pets) > 1:
            filter_choice = st.selectbox(
                "Filter tasks by pet",
                ["All pets"] + [pet.name for pet in owner.pets],
                key="task_filter_pet",
            )
            if filter_choice != "All pets":
                chosen_pet = next(
                    pet for pet in owner.pets if pet.name == filter_choice
                )
                displayed_tasks = scheduler.filter_by_pet(chosen_pet)

        if displayed_tasks:
            st.table(
                [
                    {
                        "pet": task.pet.name,
                        "title": task.name,
                        "type": task.type,
                        "duration_minutes": task.duration_minutes,
                        "priority": task.priority,
                        "done_today": task.is_done_on(today),
                    }
                    for task in displayed_tasks
                ]
            )
        else:
            st.info(f"No tasks for {filter_choice} yet.")

        # Remove a task: wires straight to Pet.remove_task. Options are indexes
        # into all_tasks (not names) so two same-named tasks stay distinct, and
        # a format_func renders a readable label for each. Removing a task drops
        # its schedules too, so it leaves the calendar on the next rerun.
        with st.expander("Remove a task"):
            def task_label(i: int) -> str:
                t = all_tasks[i]
                return f"{t.pet.name}: {t.name} ({t.type}, {t.priority})"

            remove_idx = st.selectbox(
                "Select a task to remove",
                range(len(all_tasks)),
                format_func=task_label,
                key="remove_task_idx",
            )
            task_to_remove = all_tasks[remove_idx]
            if st.button("Remove task"):
                task_to_remove.pet.remove_task(task_to_remove)
                # The index may now be out of range; drop it so the selectbox
                # re-initializes cleanly against the shorter list.
                st.session_state.pop("remove_task_idx", None)
                st.success(
                    f"Removed '{task_to_remove.name}' from {task_to_remove.pet.name}."
                )
                st.rerun()
    else:
        st.info("No tasks yet. Add one above.")

st.divider()

st.subheader("Schedule")

# scheduler and today are created once above the tasks table; reused here.
horizon = today + timedelta(days=SCHEDULE_HORIZON_DAYS)

# Materialize the recurring calendar up front. This is idempotent and runs on
# every rerun, so the schedule stays filled to the horizon regardless of what
# has been completed — a skipped day still shows a due occurrence.
scheduler.generate_occurrences(horizon)

all_occurrences = scheduler.sort_by_datetime()
if not all_occurrences:
    st.info("No scheduled occurrences yet. Add a task with a time above.")
else:
    # Smart plan for today: order today's pending tasks by priority and assign
    # a time to any the owner left flexible. This runs first because it writes
    # times onto flexible occurrences — conflict detection and the checklist
    # below both read those placed times.
    st.markdown("### 🧠 Smart Plan for Today")
    st.caption(
        "Owner-set times are kept as fixed anchors; tasks with no time are "
        "placed by priority (high first) into the earliest free slot. Once a "
        "time is chosen it stays put — use *Re-plan day* to recompute from scratch."
    )
    # Re-plan is the escape hatch: build_day_plan is sticky (chosen times never
    # move), so this button explicitly releases PawPal's auto-assigned times and
    # rebuilds by current priority. Owner-set anchors are untouched.
    if st.button("🔄 Re-plan day"):
        scheduler.replan_day(today)
    plan_lines = scheduler.explain_plan(today)
    if plan_lines:
        for line in plan_lines:
            st.write(f"- {line}")
    else:
        st.caption("Nothing pending to plan for today.")

    # Warn about clashing occurrences for today (tasks whose time windows
    # overlap, or that start at the same time).
    for message in scheduler.detect_conflicts(today):
        st.warning(message)

    # Today's checklist: per-occurrence completion for the current day.
    st.markdown(f"**Today — {today}**")
    today_occurrences = scheduler.occurrences_for_day(today)
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
        # Write completion via on_change so it lands *before* the script reruns
        # top-to-bottom. The tasks table above reads is_done_on(today), so the
        # write must precede that read or the table lags one interaction behind.
        st.checkbox(
            label,
            value=occ.completed,
            key=key,
            on_change=lambda occ=occ, key=key: scheduler.mark_done(
                occ, st.session_state[key]
            ),
        )

    pending_today = scheduler.get_pending_tasks(today)
    st.caption(
        f"{len(pending_today)} task(s) still pending today."
        if pending_today
        else "All of today's tasks are done. 🎉"
    )

    # Upcoming timeline through the horizon (read-only). Re-sort here because
    # the plan above just assigned times to today's flexible tasks. Future days
    # stay flexible until their own plan runs, so those show "— (flexible)".
    st.markdown(f"**Upcoming — through {horizon}**")
    upcoming = [
        s for s in scheduler.sort_by_datetime() if today <= s.due_date <= horizon
    ]
    st.table(
        [
            {
                "date": s.due_date.isoformat(),
                "time": s.time_of_day.strftime("%H:%M") if s.time_of_day else "— (flexible)",
                "pet": s.task.pet.name,
                "task": s.task.name,
                "recurrence": s.recurrence,
                "done": s.completed,
            }
            for s in upcoming
        ]
    )
