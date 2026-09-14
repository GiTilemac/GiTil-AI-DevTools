from datetime import date, timedelta

from .models import Assignment, Chore, OneOffTask


def current_week_start(today=None):
    """Monday of the current week."""
    today = today or date.today()
    return today - timedelta(days=today.weekday())


def days_left_in_week(today=None):
    """Days remaining until the current week's rotation ends (Sunday)."""
    today = today or date.today()
    return 6 - today.weekday()


def get_or_create_current_assignment(chore, today=None):
    """Return this week's Assignment for chore, creating it by advancing the rotation if missing."""
    week_start = current_week_start(today)
    assignment = chore.assignments.filter(week_start=week_start).first()
    if assignment:
        return assignment

    slots = list(chore.rotation_slots.order_by('order'))
    if not slots:
        return None

    last_assignment = chore.assignments.order_by('-week_start').first()
    next_index = 0
    if last_assignment:
        last_slot = next((s for s in slots if s.member_id == last_assignment.member_id), None)
        if last_slot:
            next_index = (slots.index(last_slot) + 1) % len(slots)

    next_member = slots[next_index].member
    return Assignment.objects.create(chore=chore, member=next_member, week_start=week_start)


def sync_current_assignments(today=None):
    """Ensure every chore has an Assignment for the current week. Returns the current assignments."""
    assignments = []
    for chore in Chore.objects.all():
        assignment = get_or_create_current_assignment(chore, today)
        if assignment:
            assignments.append(assignment)
    return assignments


def reassign(assignment, new_member, note):
    """Manually reassign a chore to a different member. A note is mandatory."""
    if not note:
        raise ValueError('A note is required when reassigning a chore.')
    assignment.member = new_member
    assignment.status = Assignment.Status.REASSIGNED
    assignment.note = note
    assignment.save()
    return assignment


def complete(assignment):
    assignment.status = Assignment.Status.COMPLETED
    assignment.save()
    return assignment


def skip(assignment, note):
    """Mark a chore skipped for the week. A note is mandatory."""
    if not note:
        raise ValueError('A note is required when skipping a chore.')
    assignment.status = Assignment.Status.SKIPPED
    assignment.note = note
    assignment.save()
    return assignment


def add_one_off_task(title):
    """Add a new one-off task. A title is mandatory."""
    if not title:
        raise ValueError('A title is required to add a task.')
    return OneOffTask.objects.create(title=title)


def complete_one_off_task(task):
    task.status = OneOffTask.Status.COMPLETED
    task.save()
    return task


def skip_one_off_task(task, note):
    """Mark a one-off task skipped. A note is mandatory."""
    if not note:
        raise ValueError('A note is required when skipping a task.')
    task.status = OneOffTask.Status.SKIPPED
    task.note = note
    task.save()
    return task


def member_streak(member):
    """Consecutive most-recent weeks where every assignment held by member was completed."""
    week_starts = (
        Assignment.objects.filter(member=member)
        .order_by('-week_start')
        .values_list('week_start', flat=True)
        .distinct()
    )
    streak = 0
    for week_start in week_starts:
        statuses = Assignment.objects.filter(member=member, week_start=week_start).values_list('status', flat=True)
        if all(status == Assignment.Status.COMPLETED for status in statuses):
            streak += 1
        else:
            break
    return streak
