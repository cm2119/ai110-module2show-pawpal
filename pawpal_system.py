"""PawPal+ logic layer.

Backend classes for the PawPal+ system. The structure mirrors
diagrams/uml.mmd: an Owner has Pets, each Pet has Tasks, and each
Task has Schedules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import time as Time


@dataclass
class Schedule:
    task: "Task"
    time_of_day: Time
    recurrence: str


VALID_PRIORITIES = ("high", "medium", "low")


@dataclass
class Task:
    name: str
    type: str  # daily, weekly, monthly
    pet: "Pet"
    duration_minutes: int = 0
    priority: str = "medium"  # high, medium, low
    completed: bool = False
    schedules: list[Schedule] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate that priority is one of the allowed values."""
        if self.priority not in VALID_PRIORITIES:
            raise ValueError(
                f"priority must be one of {VALID_PRIORITIES}, got {self.priority!r}"
            )

    def add_schedule(self, schedule: Schedule) -> None:
        """Attach a schedule to this task."""
        self.schedules.append(schedule)


@dataclass
class Pet:
    name: str
    weight: float
    breed: str = ""
    tasks: list[Task] = field(default_factory=list)

    def edit_info(self, name: str, weight: float, breed: str | None = None) -> None:
        """Update the pet's name, weight, and optionally its breed."""
        self.name = name
        self.weight = weight
        if breed is not None:
            self.breed = breed

    def add_task(self, task: Task) -> None:
        """Add a task to this pet's task list."""
        self.tasks.append(task)


@dataclass
class Owner:
    name: str
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Register a pet with this owner."""
        self.pets.append(pet)

    def remove_pet(self, pet: Pet) -> None:
        """Remove a pet from this owner if present."""
        if pet in self.pets:
            self.pets.remove(pet)

    def get_all_tasks(self) -> list[Task]:
        """Return every task across all of the owner's pets."""
        return [task for pet in self.pets for task in pet.tasks]


@dataclass
class Scheduler:
    owner: Owner

    def get_all_tasks(self) -> list[Task]:
        """Single entry point for task retrieval; delegates to the Owner."""
        return self.owner.get_all_tasks()

    def get_pending_tasks(self) -> list[Task]:
        """Return only the tasks that have not been completed yet."""
        return [task for task in self.get_all_tasks() if not task.completed]

    def mark_done(self, task: Task, completed: bool = True) -> None:
        """Update a task's completion state."""
        task.completed = completed
