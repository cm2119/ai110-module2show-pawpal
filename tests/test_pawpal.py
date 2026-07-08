"""Tests for core PawPal+ behaviors."""

from datetime import date, time as Time, timedelta

import pytest

from pawpal_system import Owner, Pet, Schedule, Scheduler, Task


def test_mark_done_completes_without_generating():
    """mark_done only flips completion; it does not create occurrences.
    Materializing future days is generate_occurrences()'s job."""
    owner = Owner(name="Cristina")
    pet = Pet(name="Bella", weight=12.5)
    owner.add_pet(pet)
    task = Task(name="Morning walk", type="daily", pet=pet)
    schedule = Schedule(task=task, time_of_day=Time(7, 30), recurrence="daily")
    task.add_schedule(schedule)
    pet.add_task(task)

    scheduler = Scheduler(owner=owner)
    scheduler.mark_done(schedule)

    assert schedule.completed is True
    assert len(task.schedules) == 1  # no new occurrence created


def test_generate_occurrences_fills_horizon_regardless_of_completion():
    """Date-driven generation materializes every day through the horizon
    whether or not past days were completed, and is idempotent."""
    owner = Owner(name="Cristina")
    pet = Pet(name="Bella", weight=12.5)
    owner.add_pet(pet)
    task = Task(name="Feeding", type="daily", pet=pet)
    today = date(2026, 7, 7)
    seed = Schedule(
        task=task, time_of_day=Time(7, 45), recurrence="daily", due_date=today
    )
    task.add_schedule(seed)
    pet.add_task(task)

    scheduler = Scheduler(owner=owner)
    horizon = today + timedelta(days=3)

    created = scheduler.generate_occurrences(horizon)
    # seed (today) + 3 generated days (+1, +2, +3).
    assert created == 3
    assert len(task.schedules) == 4
    due_dates = sorted(s.due_date for s in task.schedules)
    assert due_dates == [today + timedelta(days=n) for n in range(4)]
    assert all(not s.completed for s in task.schedules)  # generation != completion

    # Completing one day does not change generation; re-running is idempotent.
    scheduler.mark_done(seed)
    assert scheduler.generate_occurrences(horizon) == 0
    assert len(task.schedules) == 4


def test_is_done_true_when_all_occurrences_done():
    """Completion aggregation, isolated from recurrence: a non-recurring task
    ("once" does not generate successors) is done only once every occurrence
    is done."""
    owner = Owner(name="Cristina")
    pet = Pet(name="Bella", weight=12.5)
    owner.add_pet(pet)
    task = Task(name="Vet checkup", type="once", pet=pet)
    morning = Schedule(task=task, time_of_day=Time(9, 0), recurrence="once")
    evening = Schedule(task=task, time_of_day=Time(17, 0), recurrence="once")
    task.add_schedule(morning)
    task.add_schedule(evening)
    pet.add_task(task)

    scheduler = Scheduler(owner=owner)
    assert task.is_done is False

    scheduler.mark_done(morning)
    assert task.is_done is False  # evening still pending

    scheduler.mark_done(evening)
    assert task.is_done is True
    # "once" never generates successors even when asked.
    assert scheduler.generate_occurrences(date(2026, 12, 31)) == 0
    assert len(task.schedules) == 2


def test_pending_is_date_aware_and_empties_for_the_day():
    """Option B: completing today's occurrence removes the task from today's
    pending list, while a separately generated future day stays pending."""
    owner = Owner(name="Cristina")
    pet = Pet(name="Bella", weight=12.5)
    owner.add_pet(pet)
    task = Task(name="Feeding", type="daily", pet=pet)
    today = date(2026, 7, 7)
    tomorrow = today + timedelta(days=1)
    schedule = Schedule(
        task=task, time_of_day=Time(7, 45), recurrence="daily", due_date=today
    )
    task.add_schedule(schedule)
    pet.add_task(task)

    scheduler = Scheduler(owner=owner)
    scheduler.generate_occurrences(tomorrow)  # materialize tomorrow up front
    assert task.is_done_on(today) is False
    assert scheduler.get_pending_tasks(today) == [task]

    scheduler.mark_done(schedule)

    # Done for today; today's pending list empties...
    assert task.is_done_on(today) is True
    assert scheduler.get_pending_tasks(today) == []
    # ...but tomorrow's occurrence is pending on its own date, unaffected.
    assert task.is_done_on(tomorrow) is False
    assert scheduler.get_pending_tasks(tomorrow) == [task]


def test_sort_by_datetime_orders_across_days():
    """sort_by_datetime orders by date then time; sort_by_time ignores the date.
    A late slot today must come before an early slot tomorrow."""
    owner = Owner(name="Cristina")
    pet = Pet(name="Bella", weight=12.5)
    owner.add_pet(pet)
    task = Task(name="Care", type="daily", pet=pet)
    today = date(2026, 7, 7)
    tomorrow = today + timedelta(days=1)
    evening_today = Schedule(
        task=task, time_of_day=Time(18, 0), recurrence="daily", due_date=today
    )
    morning_tomorrow = Schedule(
        task=task, time_of_day=Time(7, 0), recurrence="daily", due_date=tomorrow
    )
    # Add out of order to prove the sort does the work.
    task.add_schedule(morning_tomorrow)
    task.add_schedule(evening_today)
    pet.add_task(task)

    scheduler = Scheduler(owner=owner)

    # Chronological: today 18:00 before tomorrow 07:00.
    assert scheduler.sort_by_datetime() == [evening_today, morning_tomorrow]
    # Time-only: 07:00 sorts before 18:00 regardless of date.
    assert scheduler.sort_by_time() == [morning_tomorrow, evening_today]


def test_detect_conflicts_flags_same_slot_across_pets():
    """Two occurrences on the same date and time conflict, even across pets;
    a task at a different time does not."""
    owner = Owner(name="Cristina")
    bella = Pet(name="Bella", weight=12.5)
    milo = Pet(name="Milo", weight=4.2)
    owner.add_pet(bella)
    owner.add_pet(milo)
    today = date(2026, 7, 7)

    walk = Task(name="Walk", type="daily", pet=bella)
    walk.add_schedule(
        Schedule(task=walk, time_of_day=Time(8, 0), recurrence="daily", due_date=today)
    )
    bella.add_task(walk)

    feed = Task(name="Feed", type="daily", pet=milo)
    feed.add_schedule(
        Schedule(task=feed, time_of_day=Time(8, 0), recurrence="daily", due_date=today)
    )
    milo.add_task(feed)

    evening = Task(name="Evening", type="daily", pet=bella)
    evening.add_schedule(
        Schedule(task=evening, time_of_day=Time(18, 0), recurrence="daily", due_date=today)
    )
    bella.add_task(evening)

    conflicts = Scheduler(owner=owner).detect_conflicts()

    assert len(conflicts) == 1
    assert "08:00" in conflicts[0]
    assert "Bella's Walk" in conflicts[0]
    assert "Milo's Feed" in conflicts[0]


def test_detect_conflicts_can_scope_to_a_single_day():
    """Passing `day` restricts the check to that date, so a recurring clash
    generated across the horizon collapses to one warning for today."""
    owner = Owner(name="Cristina")
    bella = Pet(name="Bella", weight=12.5)
    milo = Pet(name="Milo", weight=4.2)
    owner.add_pet(bella)
    owner.add_pet(milo)
    today = date(2026, 7, 7)

    walk = Task(name="Walk", type="daily", pet=bella)
    walk.add_schedule(
        Schedule(task=walk, time_of_day=Time(8, 0), recurrence="daily", due_date=today)
    )
    bella.add_task(walk)
    feed = Task(name="Feed", type="daily", pet=milo)
    feed.add_schedule(
        Schedule(task=feed, time_of_day=Time(8, 0), recurrence="daily", due_date=today)
    )
    milo.add_task(feed)

    scheduler = Scheduler(owner=owner)
    scheduler.generate_occurrences(today + timedelta(days=3))  # clash on 4 days

    assert len(scheduler.detect_conflicts()) == 4  # every generated day clashes
    assert len(scheduler.detect_conflicts(today)) == 1  # scoped to today only


def test_no_conflict_for_same_time_on_different_dates():
    """A daily task at the same clock time on different days is not a conflict."""
    owner = Owner(name="Cristina")
    pet = Pet(name="Bella", weight=12.5)
    owner.add_pet(pet)
    task = Task(name="Feeding", type="daily", pet=pet)
    today = date(2026, 7, 7)
    task.add_schedule(
        Schedule(task=task, time_of_day=Time(8, 0), recurrence="daily", due_date=today)
    )
    pet.add_task(task)

    scheduler = Scheduler(owner=owner)
    scheduler.generate_occurrences(today + timedelta(days=5))  # 6 days, all 08:00

    assert scheduler.detect_conflicts() == []


def test_add_task_increases_pet_task_count():
    """Task Addition: adding a task to a Pet increases its task count."""
    pet = Pet(name="Milo", weight=4.2)
    assert len(pet.tasks) == 0

    pet.add_task(Task(name="Feeding", type="daily", pet=pet))

    assert len(pet.tasks) == 1


# --- Recurrence validation (#1): "monthly" is rejected outright ---------------


def _make_task():
    """A minimal task to hang schedules off of for recurrence tests."""
    pet = Pet(name="Bella", weight=12.5)
    return Task(name="Feeding", type="daily", pet=pet)


def test_schedule_rejects_monthly_recurrence():
    """A schedule with recurrence="monthly" is refused at construction rather
    than silently never recurring."""
    task = _make_task()
    with pytest.raises(ValueError, match="recurrence must be one of"):
        Schedule(task=task, time_of_day=Time(9, 0), recurrence="monthly")


@pytest.mark.parametrize("bad", ["", "yearly", "Daily", "week", "none"])
def test_schedule_rejects_unknown_recurrences(bad):
    """Any value outside VALID_RECURRENCES is refused, including empties,
    typos, and wrong casing."""
    task = _make_task()
    with pytest.raises(ValueError):
        Schedule(task=task, time_of_day=Time(9, 0), recurrence=bad)


@pytest.mark.parametrize("good", ["daily", "weekly", "once"])
def test_schedule_accepts_valid_recurrences(good):
    """The three supported recurrences construct without error."""
    task = _make_task()
    schedule = Schedule(task=task, time_of_day=Time(9, 0), recurrence=good)
    assert schedule.recurrence == good


def test_once_schedule_never_recurs():
    """"once" is the sole non-recurring value: it has no next occurrence and
    generate_occurrences() materializes nothing for it."""
    owner = Owner(name="Cristina")
    pet = Pet(name="Bella", weight=12.5)
    owner.add_pet(pet)
    task = Task(name="Vet visit", type="once", pet=pet)
    today = date(2026, 7, 7)
    schedule = Schedule(
        task=task, time_of_day=Time(9, 0), recurrence="once", due_date=today
    )
    task.add_schedule(schedule)
    pet.add_task(task)

    assert schedule.next_due_date() is None
    scheduler = Scheduler(owner=owner)
    assert scheduler.generate_occurrences(today + timedelta(days=30)) == 0
    assert len(task.schedules) == 1


# --- Duration-aware conflict detection (#4) ----------------------------------


def _scheduler_with_pet():
    owner = Owner(name="Cristina")
    pet = Pet(name="Bella", weight=12.5)
    owner.add_pet(pet)
    return Scheduler(owner=owner), pet


def _add_timed_task(pet, name, start, duration):
    """Attach a single-occurrence task at `start` for `duration` minutes."""
    today = date(2026, 7, 7)
    task = Task(name=name, type="daily", pet=pet, duration_minutes=duration)
    task.add_schedule(
        Schedule(task=task, time_of_day=start, recurrence="daily", due_date=today)
    )
    pet.add_task(task)
    return task


def test_detect_conflicts_flags_duration_overlap():
    """A later task that starts before an earlier task's duration elapses is a
    conflict, even though their start times differ."""
    scheduler, pet = _scheduler_with_pet()
    _add_timed_task(pet, "Walk", Time(8, 0), 30)  # 08:00–08:30
    _add_timed_task(pet, "Feed", Time(8, 15), 5)  # starts inside the walk

    conflicts = scheduler.detect_conflicts()

    assert len(conflicts) == 1
    assert "Bella's Walk" in conflicts[0]
    assert "Bella's Feed" in conflicts[0]


def test_no_conflict_for_back_to_back_tasks():
    """One task ending exactly when the next begins is a clean handoff, not a
    conflict."""
    scheduler, pet = _scheduler_with_pet()
    _add_timed_task(pet, "Walk", Time(8, 0), 30)  # ends 08:30
    _add_timed_task(pet, "Feed", Time(8, 30), 15)  # starts 08:30

    assert scheduler.detect_conflicts() == []


def test_long_task_overlaps_several_later_tasks():
    """A long task conflicts with every task that starts before it ends, and the
    scan still stops once a later task begins at/after that end."""
    scheduler, pet = _scheduler_with_pet()
    _add_timed_task(pet, "Groom", Time(8, 0), 60)  # 08:00–09:00
    _add_timed_task(pet, "Feed", Time(8, 20), 5)  # inside Groom
    _add_timed_task(pet, "Play", Time(8, 45), 5)  # inside Groom
    _add_timed_task(pet, "Nap", Time(9, 0), 5)  # back-to-back, no conflict

    conflicts = scheduler.detect_conflicts()

    # Groom×Feed and Groom×Play only; Feed/Play don't overlap each other and
    # Nap starts exactly when Groom ends.
    assert len(conflicts) == 2
    assert all("Groom" in c for c in conflicts)
    assert not any("Nap" in c for c in conflicts)


# --- Chronological ordering (sort_by_datetime) -------------------------------


def test_sort_by_datetime_returns_scrambled_calendar_in_order():
    """Across multiple pets, tasks, and days, sort_by_datetime returns every
    occurrence ordered by (date, then time), regardless of insertion order."""
    owner = Owner(name="Cristina")
    bella = Pet(name="Bella", weight=12.5)
    milo = Pet(name="Milo", weight=4.2)
    owner.add_pet(bella)
    owner.add_pet(milo)

    day1 = date(2026, 7, 7)
    day2 = date(2026, 7, 8)
    walk = Task(name="Walk", type="daily", pet=bella)
    feed = Task(name="Feed", type="daily", pet=milo)
    bella.add_task(walk)
    milo.add_task(feed)

    day1_morning = Schedule(
        task=feed, time_of_day=Time(7, 0), recurrence="daily", due_date=day1
    )
    day1_evening = Schedule(
        task=walk, time_of_day=Time(19, 0), recurrence="daily", due_date=day1
    )
    day2_dawn = Schedule(
        task=feed, time_of_day=Time(6, 30), recurrence="daily", due_date=day2
    )
    day2_evening = Schedule(
        task=walk, time_of_day=Time(18, 0), recurrence="daily", due_date=day2
    )
    # Attach in deliberately scrambled order so the sort does the work.
    for occ in (day2_dawn, day1_evening, day2_evening, day1_morning):
        occ.task.add_schedule(occ)

    ordered = Scheduler(owner=owner).sort_by_datetime()

    # Exact chronological sequence: day1 before day2; within a day, by time.
    assert ordered == [day1_morning, day1_evening, day2_dawn, day2_evening]
    # No occurrence dropped, and the (date, time) sequence is non-decreasing.
    assert len(ordered) == 4
    keys = [(o.due_date, o.time_of_day) for o in ordered]
    assert keys == sorted(keys)


def test_generated_recurring_calendar_is_chronological():
    """After generating a recurring task forward, the full occurrence list is
    returned in chronological order with one entry per day through the horizon."""
    owner = Owner(name="Cristina")
    pet = Pet(name="Bella", weight=12.5)
    owner.add_pet(pet)
    task = Task(name="Feeding", type="daily", pet=pet)
    today = date(2026, 7, 7)
    task.add_schedule(
        Schedule(task=task, time_of_day=Time(8, 0), recurrence="daily", due_date=today)
    )
    pet.add_task(task)

    scheduler = Scheduler(owner=owner)
    scheduler.generate_occurrences(today + timedelta(days=4))  # 5 days total

    ordered = scheduler.sort_by_datetime()
    keys = [(o.due_date, o.time_of_day) for o in ordered]
    assert keys == sorted(keys)  # chronological
    assert [o.due_date for o in ordered] == [
        today + timedelta(days=n) for n in range(5)
    ]


def test_occurrences_for_day_are_in_chronological_order():
    """The Today view (occurrences_for_day, which app.py renders) returns a
    single date's occurrences ordered by time, regardless of insertion order,
    and excludes other days."""
    owner = Owner(name="Cristina")
    bella = Pet(name="Bella", weight=12.5)
    milo = Pet(name="Milo", weight=4.2)
    owner.add_pet(bella)
    owner.add_pet(milo)

    today = date(2026, 7, 7)
    tomorrow = today + timedelta(days=1)
    walk = Task(name="Walk", type="daily", pet=bella)
    feed = Task(name="Feed", type="daily", pet=milo)
    bella.add_task(walk)
    milo.add_task(feed)

    noon = Schedule(
        task=walk, time_of_day=Time(12, 0), recurrence="daily", due_date=today
    )
    dawn = Schedule(
        task=feed, time_of_day=Time(6, 30), recurrence="daily", due_date=today
    )
    evening = Schedule(
        task=walk, time_of_day=Time(18, 0), recurrence="daily", due_date=today
    )
    other_day = Schedule(
        task=feed, time_of_day=Time(5, 0), recurrence="daily", due_date=tomorrow
    )
    # Attach out of order (and with tomorrow interleaved) so the sort does the work.
    for occ in (noon, other_day, evening, dawn):
        occ.task.add_schedule(occ)

    todays = Scheduler(owner=owner).occurrences_for_day(today)

    # Chronological by time, and tomorrow's earlier-clock-time slot is excluded.
    assert todays == [dawn, noon, evening]
    times = [o.time_of_day for o in todays]
    assert times == sorted(times)
