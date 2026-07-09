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


def _minutes(t: Time) -> int:
    """Minutes since midnight for a time-of-day (the planner's unit of math)."""
    return t.hour * 60 + t.minute


def _time_from_minutes(m: int) -> Time:
    """Inverse of _minutes(), clamped into a single day [00:00, 23:59]."""
    m = max(0, min(m, 23 * 60 + 59))
    return Time(hour=m // 60, minute=m % 60)


def _time_key(s: "Schedule") -> Time:
    """Sort key for an occurrence's time that pushes un-placed (flexible)
    occurrences to the end: a None time is treated as the latest possible time."""
    return s.time_of_day if s.time_of_day is not None else Time.max


@dataclass
class Schedule:
    task: "Task"
    time_of_day: Time | None = None
    recurrence: str = "once"
    completed: bool = False
    due_date: date = field(default_factory=date.today)
    time_is_auto: bool = False  # True once build_day_plan() placed this slot

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

# Ordering weight for the day planner: lower sorts earlier, so "high" is placed
# first and gets the pick of the free slots. Keys mirror VALID_PRIORITIES.
_PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}


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
class PlannedItem:
    """One task's place in a day plan.

    Produced by Scheduler.build_day_plan(): it pairs an occurrence with the
    start/end the plan gave it and a human-readable `reason`. `anchored` records
    whether the owner fixed the time (a hard constraint the planner kept) or the
    planner chose it by priority.
    """

    schedule: Schedule
    start: Time
    end: Time
    reason: str
    anchored: bool


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
        # idempotent and free of duplicates. A slot the planner auto-placed is
        # keyed as its original flexible (None) slot — otherwise a flexible daily
        # task placed at, say, 09:00 today would spawn a second bogus 09:00 series.
        def slot_key(s: Schedule) -> tuple[Time | None, str]:
            return (None if s.time_is_auto else s.time_of_day, s.recurrence)

        frontier: dict[tuple[Time | None, str], Schedule] = {}
        for schedule in task.schedules:
            key = slot_key(schedule)
            if key not in frontier or schedule.due_date > frontier[key].due_date:
                frontier[key] = schedule

        created = 0
        for cursor in list(frontier.values()):
            next_date = cursor.next_due_date()  # None for non-recurring slots
            while next_date is not None and next_date <= through:
                cursor = Schedule(
                    task=task,
                    # A flexible slot stays flexible on future days: the planner
                    # re-decides each day's time. Only owner-set times carry over.
                    time_of_day=None if cursor.time_is_auto else cursor.time_of_day,
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
        true chronological timeline. Flexible occurrences (no time yet, awaiting
        build_day_plan) sort last, after every placed time.
        """
        return sorted(self._all_occurrences(), key=_time_key)

    def sort_by_datetime(self) -> list[Schedule]:
        """Return every occurrence in true chronological order (date, then time).

        This is the general timeline sort for a multi-day calendar: it orders by
        due_date first and breaks ties by time_of_day. Flexible occurrences (no
        time yet) sort to the end of their day, after every placed time.
        """
        return sorted(
            self._all_occurrences(), key=lambda s: (s.due_date, _time_key(s))
        )

    def occurrences_for_day(self, day: date | None = None) -> list[Schedule]:
        """Return one date's *placed* occurrences in chronological (time) order.

        Backs the app's "Today" checklist: it windows the full calendar to a
        single date while preserving the (date, time) ordering of
        sort_by_datetime(), which within one date reduces to time-of-day order.
        Flexible occurrences (time_of_day is None) are excluded — they only join
        the timeline once build_day_plan() assigns them a time. Defaults to today.
        """
        day = day if day is not None else date.today()
        return [
            s
            for s in self.sort_by_datetime()
            if s.due_date == day and s.time_of_day is not None
        ]

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

        Flexible occurrences (time_of_day is None) are skipped — they have no
        window to clash until build_day_plan() places them.
        """
        occurrences = [o for o in self._all_occurrences() if o.time_of_day is not None]
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

    def build_day_plan(
        self,
        day: date | None = None,
        *,
        day_start: Time = Time(8, 0),
        day_end: Time = Time(22, 0),
    ) -> list[PlannedItem]:
        """Build an ordered, priority-aware plan for a single day.

        This is the "smart" schedule the assignment asks for: it chooses and
        orders the day's *pending* tasks under two constraints —

        * **Owner-set times are hard anchors.** If a task already has a time, the
          plan keeps it there.
        * **Priority orders the rest.** Tasks the owner left flexible
          (time_of_day is None) are placed high→medium→low into the earliest
          free gap that clears the anchors, so important care happens first.

        Placement writes the chosen time back onto the Schedule (marking it
        time_is_auto) and is *sticky*: once PawPal assigns a time it is treated
        exactly like an owner-set time — a fixed commitment that seeds the busy
        intervals and is never moved on a later call. So completing or adding a
        task never reshuffles times already decided; only still-flexible tasks
        get placed, routed around every existing commitment. Owner anchors are
        likewise never moved. (A consequence: a high-priority task added after
        the plan exists does not preempt an already-committed slot — it takes
        the next free one.)

        Flexible tasks are packed within [day_start, day_end) by
        duration_minutes; a zero-duration task takes an instant and does not
        advance the fill cursor, so two can share a moment (they will then show
        up in detect_conflicts, by design). A task with no room left before
        day_end is still placed (right after the last commitment) and its reason
        says the day is overbooked — nothing is silently dropped.

        Returns PlannedItems ordered by start time, each carrying a reason that
        explains why the task was chosen and when it happens. Defaults to today.
        """
        day = day if day is not None else date.today()

        # This day's pending occurrences (completed ones drop off the plan).
        pending = [
            occ
            for occ in self._all_occurrences()
            if occ.due_date == day and not occ.completed
        ]
        # Only tasks still without a time get placed, high→medium→low (longer
        # first, then name, for a deterministic order). Anything already timed —
        # owner-set OR a prior auto-placement — is a fixed commitment.
        flexible = sorted(
            (o for o in pending if o.time_of_day is None),
            key=lambda o: (
                _PRIORITY_RANK[o.task.priority],
                -o.task.duration_minutes,
                o.task.name,
            ),
        )

        start_min, end_min = _minutes(day_start), _minutes(day_end)

        def describe(occ: Schedule) -> str:
            return f"{occ.task.pet.name}'s {occ.task.name}"

        def hhmm(minute: int) -> str:
            return f"{_time_from_minutes(minute):%H:%M}"

        # Occupied intervals as (start_min, end_min, label), seeded with every
        # existing commitment (owner anchors and prior auto-placements alike).
        busy: list[tuple[int, int, str]] = [
            (_minutes(o.time_of_day),
             _minutes(o.time_of_day) + o.task.duration_minutes,
             describe(o))
            for o in pending
            if o.time_of_day is not None
        ]

        # Place each flexible task in the earliest gap that clears every busy
        # interval, then commit it (write the time, mark it auto) so later tasks
        # this call — and every future call — treat it as fixed.
        for occ in flexible:
            dur = occ.task.duration_minutes
            cursor = start_min
            moved = True
            while moved:
                moved = False
                for bs, be, _ in busy:
                    if cursor < be and bs < cursor + dur:
                        cursor = be
                        moved = True
            occ.time_of_day = _time_from_minutes(cursor)
            occ.time_is_auto = True
            busy.append((cursor, cursor + dur, describe(occ)))

        # Every pending occurrence now has a time. Emit items in start order,
        # explaining each: owner anchors say "you set this", auto-scheduled tasks
        # are described by the commitment they follow.
        items: list[PlannedItem] = []
        prev: tuple[int, int, str] | None = None  # (start, end, label) preceding
        for occ in sorted(
            pending, key=lambda o: (_minutes(o.time_of_day), o.task.name)
        ):
            s = _minutes(occ.time_of_day)
            e = s + occ.task.duration_minutes
            pr = occ.task.priority
            when = f"{occ.time_of_day:%H:%M}"

            if not occ.time_is_auto:
                reason = f"[{pr} priority] Fixed at {when} — you set this time."
            elif e > end_min:
                reason = (
                    f"[{pr} priority] Auto-scheduled at {when} — no free slot "
                    f"before {day_end:%H:%M}, the day is overbooked."
                )
            elif prev is not None and s > start_min:
                ps, pe, plabel = prev
                reason = (
                    f"[{pr} priority] Auto-scheduled at {when}, after "
                    f"{plabel} ({hhmm(ps)}–{hhmm(pe)})."
                )
            else:
                reason = (
                    f"[{pr} priority] Auto-scheduled at {when}, "
                    f"at the start of the day."
                )

            items.append(
                PlannedItem(
                    schedule=occ,
                    start=occ.time_of_day,
                    end=_time_from_minutes(e),
                    reason=reason,
                    anchored=not occ.time_is_auto,
                )
            )
            prev = (s, e, describe(occ))

        items.sort(key=lambda it: it.start)
        return items

    def replan_day(
        self,
        day: date | None = None,
        *,
        day_start: Time = Time(8, 0),
        day_end: Time = Time(22, 0),
    ) -> list[PlannedItem]:
        """Discard PawPal's own past time choices for `day` and plan afresh.

        build_day_plan() is sticky: it never moves a time it already assigned,
        which keeps everyday interactions stable. This is the deliberate escape
        hatch — it releases every auto-assigned slot on `day` back to flexible
        (owner-set anchors are left untouched) and re-runs the planner, so times
        are recomputed from scratch by current priority. Wire it to an explicit
        "Re-plan" action, never to an automatic rerun. Defaults to today.
        """
        day = day if day is not None else date.today()
        for occ in self._all_occurrences():
            if occ.due_date == day and occ.time_is_auto:
                occ.time_of_day = None
                occ.time_is_auto = False
        return self.build_day_plan(day, day_start=day_start, day_end=day_end)

    def explain_plan(self, day: date | None = None) -> list[str]:
        """Render build_day_plan() as display-ready lines for the UI.

        Each line reads: "<window>  <pet>: <task> (<n> min) — <reason>", so the
        owner sees both the timetable and why each task landed where it did.
        Defaults to today.
        """
        lines: list[str] = []
        for item in self.build_day_plan(day):
            task = item.schedule.task
            dur = task.duration_minutes
            window = (
                f"{item.start:%H:%M}"
                if dur == 0
                else f"{item.start:%H:%M}–{item.end:%H:%M}"
            )
            lines.append(
                f"{window}  {task.pet.name}: {task.name} ({dur} min) — {item.reason}"
            )
        return lines
