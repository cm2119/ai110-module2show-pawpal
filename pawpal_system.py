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

    def add_time(self, time: Time) -> None:
        ...


@dataclass
class Task:
    name: str
    type: str
    pet: "Pet"
    schedules: list[Schedule] = field(default_factory=list)

    def set_schedule(self, schedule: Schedule) -> None:
        ...


@dataclass
class Pet:
    name: str
    weight: float

    def edit_info(self, name: str, weight: float) -> None:
        ...

    def add_task(self, task: Task) -> None:
        ...


@dataclass
class Owner:
    name: str
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        ...

    def remove_pet(self, pet: Pet) -> None:
        ...
