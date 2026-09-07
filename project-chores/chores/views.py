from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from . import services
from .models import Assignment, OneOffTask


def dashboard(request):
    assignments = services.sync_current_assignments()
    rows = [
        {'assignment': assignment, 'streak': services.member_streak(assignment.member)}
        for assignment in assignments
    ]
    return render(request, 'chores/dashboard.html', {
        'rows': rows,
        'days_left': services.days_left_in_week(),
    })


@require_POST
def complete_assignment(request, pk):
    assignment = get_object_or_404(Assignment, pk=pk)
    services.complete(assignment)
    return redirect('dashboard')


@require_POST
def skip_assignment(request, pk):
    assignment = get_object_or_404(Assignment, pk=pk)
    note = request.POST.get('note', '').strip()
    try:
        services.skip(assignment, note)
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect('dashboard')


def history(request):
    entries = Assignment.objects.exclude(status=Assignment.Status.ASSIGNED).order_by('-week_start')
    return render(request, 'chores/history.html', {'entries': entries})


def backlog(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        try:
            services.add_one_off_task(title)
        except ValueError as exc:
            messages.error(request, str(exc))
        return redirect('backlog')

    tasks = OneOffTask.objects.all()
    return render(request, 'chores/backlog.html', {'tasks': tasks})


@require_POST
def complete_task(request, pk):
    task = get_object_or_404(OneOffTask, pk=pk)
    services.complete_one_off_task(task)
    return redirect('backlog')


@require_POST
def skip_task(request, pk):
    task = get_object_or_404(OneOffTask, pk=pk)
    note = request.POST.get('note', '').strip()
    try:
        services.skip_one_off_task(task, note)
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect('backlog')
