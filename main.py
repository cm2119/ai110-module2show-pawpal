"""PawPal+ demo script.

Builds a small PawPal+ world, lets the priority-aware planner lay out the day,
then prints a per-pet daily plan in the assignment's target format:

    Daily plan for Biscuit (Golden Retriever):
      08:00 — Morning walk (30 min) [priority: high]
      09:00 — Feeding (10 min) [priority: high]

Any schedule conflicts the planner leaves (e.g. two tasks pinned to the same
time) are reported afterwards as warnings instead of crashing.
"""

from datetime import time as Time

from pawpal_system import Owner, Pet, PlannedItem, Schedule, Scheduler, Task


def add_task(
    pet: Pet,
    name: str,
    duration_minutes: int,
    priority: str,
    *,
    hour: int | None = None,
    minute: int = 0,
) -> Task:
    """Create a daily task on `pet`.

    Pass `hour` to pin the occurrence to a fixed time (an owner anchor the
    planner keeps); omit it to leave the time flexible so build_day_plan()
    places it by priority.
    """
    task = Task(
        name=name,
        type="daily",
        pet=pet,
        duration_minutes=duration_minutes,
        priority=priority,
    )
    time_of_day = Time(hour, minute) if hour is not None else None
    task.add_schedule(Schedule(task=task, time_of_day=time_of_day, recurrence="daily"))
    pet.add_task(task)
    return task


def format_plan_line(item: PlannedItem) -> str:
    """Render one planned item as 'HH:MM — Task (N min) [priority: level]'."""
    task = item.schedule.task
    return (
        f"{item.start:%H:%M} — {task.name} "
        f"({task.duration_minutes} min) [priority: {task.priority}]"
    )


def print_day_plan(scheduler: Scheduler) -> None:
    """Print the day plan grouped by pet, one section per pet."""
    plan = scheduler.build_day_plan()
    for pet in scheduler.owner.pets:
        items = [it for it in plan if it.schedule.task.pet is pet]
        if not items:
            continue
        breed = pet.breed or "unknown breed"
        print(f"Daily plan for {pet.name} ({breed}):")
        for item in items:
            print(f"  {format_plan_line(item)}")
        print()


def main() -> None:
    owner = Owner(name="Cristina")
    bella = Pet(name="Bella", weight=12.5, breed="Beagle")
    milo = Pet(name="Milo", weight=4.2, breed="Tabby Cat")
    owner.add_pet(bella)
    owner.add_pet(milo)

    # Three tasks are pinned to the same 08:00 slot -> one cross-pet clash
    # (Bella vs Milo) and one same-pet clash (both of Bella's), so the plan
    # below surfaces conflict warnings for an evaluator to see.
    add_task(bella, "Morning walk", 30, "high", hour=8, minute=0)
    add_task(bella, "Give medicine", 10, "high", hour=8, minute=0)
    add_task(milo, "Morning feeding", 15, "high", hour=8, minute=0)
    # A non-conflicting task at a different time.
    add_task(bella, "Evening feeding", 10, "medium", hour=18, minute=0)

    scheduler = Scheduler(owner=owner)

    print(f"Owner: {owner.name}\n")
    print_day_plan(scheduler)

    conflicts = scheduler.detect_conflicts()
    if conflicts:
        print(f"WARNING: {len(conflicts)} schedule conflict(s) detected:")
        for message in conflicts:
            print(f"  - {message}")
    else:
        print("No schedule conflicts.")


if __name__ == "__main__":
    main()
