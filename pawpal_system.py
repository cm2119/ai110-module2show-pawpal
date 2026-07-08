"""PawPal+ logic layer.

Backend classes for the PawPal+ system. The structure mirrors
diagrams/uml.mmd: an Owner has Pets, each Pet has Tasks, and each
Task has Schedules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time as Time, timedelta
from itertools import groupby

# How far ahead the next occurrence falls for each recurrence. Daily/weekly
# use fixed timedeltas because those units never vary in length. "monthly" is
# intentionally absent: a fixed number of days cannot represent months that
# range from 28 to 31 days, so monthly is not supported at all (see
# VALID_RECURRENCES).
_RECURRENCE_DELTAS = {
    "daily": timedelta(days=1),
    "weekly": timedelta(days=7),
}

# Recurrences the system accepts. "daily"/"weekly" auto-advance via
# _RECURRENCE_DELTAS; "once" is the sole non-recurring value (it has no delta,
# so next_due_date() returns None for it). "monthly" is deliberately excluded
# and is rejected at construction rather than silently never recurring.
VALID_RECURRENCES = ("daily", "weekly", "once")


@dataclass
class Schedule:
    task: "Task"
    time_of_day: Time
    recurrence: str
    completed: bool = False
    due_date: date = field(default_factory=date.today)

    def __post_init__(self) -> None:
        """Reject unsupported recurrences (e.g. "monthly") at construction."""
        if self.recurrence not in VALID_RECURRENCES:
            raise ValueError(
                f"recurrence must be one of {VALID_RECURRENCES}, "
                f"got {self.recurrence!r}"
            )

    def next_due_date(self) -> date | None:
        """Date of the next occurrence, or None if this schedule does not recur.

        Adds the recurrence's timedelta to this occurrence's due_date. Returns
        None for non-recurring schedules ("once"), so callers can tell "no
        successor" apart from a real date.
        """
        delta = _RECURRENCE_DELTAS.get(self.recurrence)
        if delta is None:
            return None
        return self.due_date + delta


VALID_PRIORITIES = ("high", "medium", "low")


@dataclass
class Task:
    name: str
    type: str  # daily, weekly
    pet: "Pet"
    duration_minutes: int = 0
    priority: str = "medium"  # high, medium, low
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

    @property
    def is_done(self) -> bool:
        """A task is done when *every* one of its occurrences is done.

        Aggregates across all dates, so a recurring task is effectively never
        done (there is always a future occurrence). For the per-day question
        "is this done today?" use is_done_on(). A task with no schedules is not
        considered done.
        """
        return bool(self.schedules) and all(s.completed for s in self.schedules)

    def occurrences_on(self, day: date) -> list[Schedule]:
        """Return this task's occurrences due on the given date."""
        return [s for s in self.schedules if s.due_date == day]

    def is_done_on(self, day: date) -> bool:
        """True if this task has occurrences due on `day` and all are complete.

        This is the per-day view an owner cares about ("did I feed Bella
        today?"). A task with nothing scheduled that day is not "done" for it —
        there was nothing to do — so this returns False.
        """
        due = self.occurrences_on(day)
        return bool(due) and all(s.completed for s in due)


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

    def get_pending_tasks(self, day: date | None = None) -> list[Task]:
        """Return tasks with an incomplete occurrence due on `day` (default today).

        This is the per-day view: unlike filter_by_status(completed=False),
        which aggregates across all dates, this list empties once the day's
        occurrences are done — so a recurring task drops off after today's
        instance is complete while future generated days remain pending.
        """
        day = day if day is not None else date.today()
        return [
            task
            for task in self.get_all_tasks()
            if any(not s.completed for s in task.occurrences_on(day))
        ]

    def filter_by_status(self, completed: bool) -> list[Task]:
        """Return tasks whose completion state matches `completed`.

        Reads the derived Task.is_done, so a multi-time task counts as
        completed only when all of its occurrences are done.
        """
        return [task for task in self.get_all_tasks() if task.is_done == completed]

    def filter_by_pet(self, pet: Pet) -> list[Task]:
        """Return tasks belonging to the given pet (matched by identity)."""
        return [task for task in self.get_all_tasks() if task.pet is pet]

    def mark_done(self, schedule: Schedule, completed: bool = True) -> None:
        """Mark a single occurrence (one time slot) done.

        Completion lives on the Schedule, so marking the 7:30 feeding done
        leaves the 18:00 feeding pending. Completion has no other side effects:
        future occurrences are materialized by generate_occurrences(), not
        here, so skipping a day never loses the task.
        """
        schedule.completed = completed

    def generate_occurrences(self, through: date) -> int:
        """Materialize recurring occurrences up to and including `through`.

        Independent of completion: every recurring slot is filled forward to
        the horizon whether or not past occurrences were done, so a skipped day
        still leaves a due occurrence rather than dropping the task. Idempotent
        — re-running with the same (or an earlier) horizon adds nothing.
        Returns the number of occurrences created.
        """
        return sum(self._extend_task(task, through) for task in self.get_all_tasks())

    def _extend_task(self, task: Task, through: date) -> int:
        """Fill each of a task's recurring (time, recurrence) slots to `through`."""
        # Find the latest materialized occurrence per recurring slot; that
        # frontier is where generation resumes, which is what makes this
        # idempotent and free of duplicates.
        frontier: dict[tuple[Time, str], Schedule] = {}
        for schedule in task.schedules:
            key = (schedule.time_of_day, schedule.recurrence)
            if key not in frontier or schedule.due_date > frontier[key].due_date:
                frontier[key] = schedule

        created = 0
        for cursor in list(frontier.values()):
            next_date = cursor.next_due_date()  # None for non-recurring slots
            while next_date is not None and next_date <= through:
                cursor = Schedule(
                    task=task,
                    time_of_day=cursor.time_of_day,
                    recurrence=cursor.recurrence,
                    due_date=next_date,
                )
                task.add_schedule(cursor)
                created += 1
                next_date = cursor.next_due_date()
        return created

    def _all_occurrences(self) -> list[Schedule]:
        """Flatten every task's schedules into a single list of occurrences."""
        return [s for task in self.get_all_tasks() for s in task.schedules]

    def sort_by_time(self) -> list[Schedule]:
        """Return every occurrence ordered by time of day, ignoring the date.

        Useful within a single day (the daily rhythm). Across multiple days it
        interleaves dates at the same clock time — use sort_by_datetime() for a
        true chronological timeline.
        """
        return sorted(self._all_occurrences(), key=lambda s: s.time_of_day)

    def sort_by_datetime(self) -> list[Schedule]:
        """Return every occurrence in true chronological order (date, then time).

        This is the general timeline sort for a multi-day calendar: it orders by
        due_date first and breaks ties by time_of_day.
        """
        return sorted(
            self._all_occurrences(), key=lambda s: (s.due_date, s.time_of_day)
        )

    def occurrences_for_day(self, day: date | None = None) -> list[Schedule]:
        """Return one date's occurrences in chronological (time) order.

        Backs the app's "Today" checklist: it windows the full calendar to a
        single date while preserving the (date, time) ordering of
        sort_by_datetime(), which within one date reduces to time-of-day order.
        Defaults to today.
        """
        day = day if day is not None else date.today()
        return [s for s in self.sort_by_datetime() if s.due_date == day]

    def detect_conflicts(self, day: date | None = None) -> list[str]:
        """Return warnings for occurrences whose time windows overlap.

        Each occurrence occupies [start, start + duration_minutes). Two care
        tasks conflict when those windows overlap, or when they share the exact
        same start time (so zero-duration tasks scheduled together still clash).
        Back-to-back tasks — one ending exactly when the next begins — do not
        conflict. Overlaps are flagged whether the tasks belong to the same pet
        or to different pets.

        A recurring task never conflicts with itself across days: only
        occurrences on the *same* date are compared. Midnight crossing is out of
        scope — a duration that would run past 23:59 is not wrapped to the next
        day. Pass `day` to check just that date (e.g. today); omit it to scan the
        whole calendar. Lightweight by design — it returns human-readable
        messages (empty list when clear) and never raises.
        """
        occurrences = self._all_occurrences()
        if day is not None:
            occurrences = [occ for occ in occurrences if occ.due_date == day]

        # Sort so occurrences on the same date are adjacent (for groupby, which
        # only groups *adjacent* equal keys) and ordered by start time; (pet,
        # task) settles ties so pairings are deterministic.
        occurrences.sort(
            key=lambda o: (o.due_date, o.time_of_day, o.task.pet.name, o.task.name)
        )

        def start_of(occ: Schedule) -> datetime:
            return datetime.combine(occ.due_date, occ.time_of_day)

        def end_of(occ: Schedule) -> datetime:
            return start_of(occ) + timedelta(minutes=occ.task.duration_minutes)

        def window(occ: Schedule) -> str:
            start, end = start_of(occ), end_of(occ)
            if end > start:
                return f"{start:%H:%M}–{end:%H:%M}"
            return f"{start:%H:%M}"  # zero-duration: a single instant

        def describe(occ: Schedule) -> str:
            return f"{occ.task.pet.name}'s {occ.task.name}"

        warnings: list[str] = []
        for _, group in groupby(occurrences, key=lambda o: o.due_date):
            day_occs = list(group)
            for i, earlier in enumerate(day_occs):
                e_start, e_end = start_of(earlier), end_of(earlier)
                for later in day_occs[i + 1:]:
                    l_start = start_of(later)
                    # day_occs is sorted by start, so l_start >= e_start. A later
                    # task that begins at or after this one ends (and strictly
                    # after it starts) is back-to-back at best — and so is every
                    # occurrence after it, hence the break.
                    if l_start > e_start and l_start >= e_end:
                        break
                    warnings.append(
                        f"Conflict on {earlier.due_date}: "
                        f"{describe(earlier)} ({window(earlier)}) overlaps "
                        f"{describe(later)} ({window(later)})"
                    )
        return warnings
