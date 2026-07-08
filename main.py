"""PawPal+ demo script.

Builds a small PawPal+ world with two tasks scheduled at the same time, then
demonstrates lightweight conflict detection: the Scheduler reports clashes as
warning messages instead of crashing.
"""

from datetime import time as Time

from pawpal_system import Owner, Pet, Schedule, Scheduler, Task


def print_timeline(scheduler: Scheduler, heading: str) -> None:
    """Print every occurrence with its date, time, and completion status."""
    print(heading)
    for schedule in scheduler.sort_by_datetime():
        print(
            f"  {schedule.due_date}  {schedule.time_of_day.strftime('%H:%M')}  "
            f"{schedule.task.pet.name}: {schedule.task.name}"
        )


def add_task(pet: Pet, name: str, hour: int, minute: int) -> Task:
    """Create a daily task on `pet` with one occurrence at the given time."""
    task = Task(name=name, type="daily", pet=pet)
    task.add_schedule(
        Schedule(task=task, time_of_day=Time(hour, minute), recurrence="daily")
    )
    pet.add_task(task)
    return task


def main() -> None:
    owner = Owner(name="Cristina")
    bella = Pet(name="Bella", weight=12.5)
    milo = Pet(name="Milo", weight=4.2)
    owner.add_pet(bella)
    owner.add_pet(milo)

    # Three tasks land on the same 08:00 slot -> one cross-pet clash
    # (Bella vs Milo) and one same-pet clash (both of Bella's).
    add_task(bella, "Morning walk", 8, 0)
    add_task(milo, "Morning feeding", 8, 0)
    add_task(bella, "Give medicine", 8, 0)
    # A non-conflicting task at a different time.
    add_task(bella, "Evening feeding", 18, 0)

    scheduler = Scheduler(owner=owner)

    print(f"Owner: {owner.name}\n")
    print_timeline(scheduler, "Scheduled occurrences:")

    conflicts = scheduler.detect_conflicts()
    print()
    if conflicts:
        print(f"WARNING: {len(conflicts)} schedule conflict(s) detected:")
        for message in conflicts:
            print(f"  - {message}")
    else:
        print("No schedule conflicts.")


if __name__ == "__main__":
    main()
