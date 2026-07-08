"""Tests for core PawPal+ behaviors."""

from datetime import date, time as Time, timedelta

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
    (monthly does not generate) is done only once every occurrence is done."""
    owner = Owner(name="Cristina")
    pet = Pet(name="Bella", weight=12.5)
    owner.add_pet(pet)
    task = Task(name="Vet checkup", type="monthly", pet=pet)
    morning = Schedule(task=task, time_of_day=Time(9, 0), recurrence="monthly")
    evening = Schedule(task=task, time_of_day=Time(17, 0), recurrence="monthly")
    task.add_schedule(morning)
    task.add_schedule(evening)
    pet.add_task(task)

    scheduler = Scheduler(owner=owner)
    assert task.is_done is False

    scheduler.mark_done(morning)
    assert task.is_done is False  # evening still pending

    scheduler.mark_done(evening)
    assert task.is_done is True
    # monthly never generates successors even when asked.
    assert scheduler.generate_occurrences(date(2026, 12, 31)) == 0
    assert len(task.schedules) == 2


def test_is_done_true_when_all_occurrences_done():
    """Completion aggregation, isolated from recurrence: a non-recurring task
    (monthly does not auto-spawn) is done only once every occurrence is done."""
    owner = Owner(name="Cristina")
    pet = Pet(name="Bella", weight=12.5)
    owner.add_pet(pet)
    task = Task(name="Vet checkup", type="monthly", pet=pet)
    morning = Schedule(task=task, time_of_day=Time(9, 0), recurrence="monthly")
    evening = Schedule(task=task, time_of_day=Time(17, 0), recurrence="monthly")
    task.add_schedule(morning)
    task.add_schedule(evening)
    pet.add_task(task)

    scheduler = Scheduler(owner=owner)
    assert task.is_done is False

    scheduler.mark_done(morning)
    assert task.is_done is False  # evening still pending

    scheduler.mark_done(evening)
    assert task.is_done is True
    assert len(task.schedules) == 2  # monthly never spawned successors


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
