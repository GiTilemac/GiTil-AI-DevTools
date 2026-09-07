from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from . import services
from .models import Assignment


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
