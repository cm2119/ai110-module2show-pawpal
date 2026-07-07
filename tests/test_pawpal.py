"""Tests for core PawPal+ behaviors."""

from pawpal_system import Owner, Pet, Scheduler, Task


def test_mark_done_changes_task_status():
    """Task Completion: mark_done() flips a task's completed status."""
    owner = Owner(name="Cristina")
    pet = Pet(name="Bella", weight=12.5)
    owner.add_pet(pet)
    task = Task(name="Morning walk", type="daily", pet=pet)
    pet.add_task(task)

    scheduler = Scheduler(owner=owner)
    assert task.completed is False

    scheduler.mark_done(task)

    assert task.completed is True


def test_add_task_increases_pet_task_count():
    """Task Addition: adding a task to a Pet increases its task count."""
    pet = Pet(name="Milo", weight=4.2)
    assert len(pet.tasks) == 0

    pet.add_task(Task(name="Feeding", type="daily", pet=pet))

    assert len(pet.tasks) == 1
