"""PawPal+ demo script.

Builds a small PawPal+ world: one Owner, two Pets, and several
scheduled Tasks, then prints everything out.
"""

from datetime import time as Time

from pawpal_system import Owner, Pet, Schedule, Task


def main() -> None:
    # Create an owner.
    owner = Owner(name="Cristina")

    # Create at least two pets and register them with the owner.
    bella = Pet(name="Bella", weight=12.5)
    milo = Pet(name="Milo", weight=4.2)
    owner.add_pet(bella)
    owner.add_pet(milo)

    # Add at least three tasks with different times.
    morning_walk = Task(name="Morning walk", type="daily", pet=bella)
    morning_walk.add_schedule(
        Schedule(task=morning_walk, time_of_day=Time(7, 30), recurrence="daily")
    )
    bella.add_task(morning_walk)

    evening_feed = Task(name="Evening feeding", type="daily", pet=bella)
    evening_feed.add_schedule(
        Schedule(task=evening_feed, time_of_day=Time(18, 0), recurrence="daily")
    )
    bella.add_task(evening_feed)

    litter_change = Task(name="Litter box change", type="weekly", pet=milo)
    litter_change.add_schedule(
        Schedule(task=litter_change, time_of_day=Time(12, 15), recurrence="weekly")
    )
    milo.add_task(litter_change)

    # Print a summary of the owner, pets, and their scheduled tasks.
    print(f"Owner: {owner.name}")
    print("Today's Tasks:")
    for pet in owner.pets:
        print(f"  Pet: {pet.name} ({pet.weight} kg)")
        for task in pet.tasks:
            times = ", ".join(
                s.time_of_day.strftime("%H:%M") for s in task.schedules
            )
            print(f"    Task: {task.name} [{task.type}] at {times}")


if __name__ == "__main__":
    main()
