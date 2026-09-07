from datetime import date

from django.contrib.messages import get_messages
from django.db import IntegrityError, transaction
from django.test import TestCase

from . import services
from .models import Assignment, Chore, Member, OneOffTask, RotationSlot


def make_rotation(chore, *members):
    for i, member in enumerate(members, start=1):
        RotationSlot.objects.create(chore=chore, member=member, order=i)


class RotationEngineTests(TestCase):
    def setUp(self):
        self.alice = Member.objects.create(name='Alice')
        self.bob = Member.objects.create(name='Bob')
        self.carol = Member.objects.create(name='Carol')
        self.dishes = Chore.objects.create(name='Dishes', difficulty='light')
        make_rotation(self.dishes, self.alice, self.bob, self.carol)

    def test_first_assignment_uses_first_rotation_slot(self):
        assignment = services.get_or_create_current_assignment(self.dishes, today=date(2026, 8, 17))
        self.assertEqual(assignment.member, self.alice)

    def test_advances_to_next_member_next_week(self):
        services.get_or_create_current_assignment(self.dishes, today=date(2026, 8, 17))
        next_assignment = services.get_or_create_current_assignment(self.dishes, today=date(2026, 8, 24))
        self.assertEqual(next_assignment.member, self.bob)

    def test_wraps_around_after_last_member(self):
        services.get_or_create_current_assignment(self.dishes, today=date(2026, 8, 17))  # Alice
        services.get_or_create_current_assignment(self.dishes, today=date(2026, 8, 24))  # Bob
        services.get_or_create_current_assignment(self.dishes, today=date(2026, 8, 31))  # Carol
        wrapped = services.get_or_create_current_assignment(self.dishes, today=date(2026, 9, 7))
        self.assertEqual(wrapped.member, self.alice)

    def test_calling_twice_in_same_week_is_idempotent(self):
        first = services.get_or_create_current_assignment(self.dishes, today=date(2026, 8, 17))
        second = services.get_or_create_current_assignment(self.dishes, today=date(2026, 8, 17))
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(Assignment.objects.filter(chore=self.dishes).count(), 1)

    def test_chore_without_rotation_slots_returns_none(self):
        bare_chore = Chore.objects.create(name='Trash', difficulty='light')
        self.assertIsNone(services.get_or_create_current_assignment(bare_chore, today=date(2026, 8, 17)))

    def test_sync_creates_assignments_for_all_chores(self):
        Chore.objects.create(name='Trash', difficulty='light')  # no rotation slots
        laundry = Chore.objects.create(name='Laundry', difficulty='medium')
        make_rotation(laundry, self.bob)

        assignments = services.sync_current_assignments(today=date(2026, 8, 17))

        chores_assigned = {a.chore.name for a in assignments}
        self.assertEqual(chores_assigned, {'Dishes', 'Laundry'})


class ReassignSkipCompleteTests(TestCase):
    def setUp(self):
        self.alice = Member.objects.create(name='Alice')
        self.bob = Member.objects.create(name='Bob')
        self.dishes = Chore.objects.create(name='Dishes', difficulty='light')
        make_rotation(self.dishes, self.alice, self.bob)
        self.assignment = services.get_or_create_current_assignment(self.dishes, today=date(2026, 8, 17))

    def test_reassign_requires_note(self):
        with self.assertRaises(ValueError):
            services.reassign(self.assignment, self.bob, '')

    def test_reassign_updates_member_status_and_note(self):
        services.reassign(self.assignment, self.bob, 'Alice is sick')
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.member, self.bob)
        self.assertEqual(self.assignment.status, Assignment.Status.REASSIGNED)
        self.assertEqual(self.assignment.note, 'Alice is sick')

    def test_skip_requires_note(self):
        with self.assertRaises(ValueError):
            services.skip(self.assignment, '')

    def test_skip_updates_status_and_note(self):
        services.skip(self.assignment, 'forgot')
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.status, Assignment.Status.SKIPPED)
        self.assertEqual(self.assignment.note, 'forgot')

    def test_complete_does_not_require_note(self):
        services.complete(self.assignment)
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.status, Assignment.Status.COMPLETED)


class StreakTests(TestCase):
    def setUp(self):
        self.alice = Member.objects.create(name='Alice')
        self.dishes = Chore.objects.create(name='Dishes', difficulty='light')
        self.laundry = Chore.objects.create(name='Laundry', difficulty='medium')

    def test_no_assignments_gives_zero_streak(self):
        self.assertEqual(services.member_streak(self.alice), 0)

    def test_counts_consecutive_completed_weeks(self):
        for offset, week in enumerate([date(2026, 8, 3), date(2026, 8, 10), date(2026, 8, 17)]):
            Assignment.objects.create(
                chore=self.dishes, member=self.alice, week_start=week,
                status=Assignment.Status.COMPLETED,
            )
        self.assertEqual(services.member_streak(self.alice), 3)

    def test_streak_stops_at_first_non_completed_week(self):
        Assignment.objects.create(
            chore=self.dishes, member=self.alice, week_start=date(2026, 8, 3),
            status=Assignment.Status.COMPLETED,
        )
        Assignment.objects.create(
            chore=self.dishes, member=self.alice, week_start=date(2026, 8, 10),
            status=Assignment.Status.SKIPPED,
        )
        Assignment.objects.create(
            chore=self.dishes, member=self.alice, week_start=date(2026, 8, 17),
            status=Assignment.Status.COMPLETED,
        )
        self.assertEqual(services.member_streak(self.alice), 1)

    def test_week_only_counts_if_all_that_weeks_assignments_completed(self):
        Assignment.objects.create(
            chore=self.dishes, member=self.alice, week_start=date(2026, 8, 17),
            status=Assignment.Status.COMPLETED,
        )
        Assignment.objects.create(
            chore=self.laundry, member=self.alice, week_start=date(2026, 8, 17),
            status=Assignment.Status.SKIPPED,
        )
        self.assertEqual(services.member_streak(self.alice), 0)


class DashboardViewTests(TestCase):
    def test_get_dashboard_returns_200(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_visiting_dashboard_creates_current_assignment(self):
        alice = Member.objects.create(name='Alice')
        dishes = Chore.objects.create(name='Dishes', difficulty='light')
        make_rotation(dishes, alice)

        self.assertEqual(Assignment.objects.count(), 0)
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Assignment.objects.count(), 1)
        self.assertContains(response, 'Alice')

    def test_complete_action_updates_status_and_redirects(self):
        alice = Member.objects.create(name='Alice')
        dishes = Chore.objects.create(name='Dishes', difficulty='light')
        make_rotation(dishes, alice)
        assignment = services.get_or_create_current_assignment(dishes)

        response = self.client.post(f'/assignments/{assignment.pk}/complete/')
        assignment.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(assignment.status, Assignment.Status.COMPLETED)


class SkipViewTests(TestCase):
    def setUp(self):
        self.alice = Member.objects.create(name='Alice')
        self.dishes = Chore.objects.create(name='Dishes', difficulty='light')
        make_rotation(self.dishes, self.alice)
        self.assignment = services.get_or_create_current_assignment(self.dishes)
        self.url = f'/assignments/{self.assignment.pk}/skip/'

    def test_empty_note_is_rejected(self):
        response = self.client.post(self.url, {'note': ''}, follow=True)
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.status, Assignment.Status.ASSIGNED)
        self.assertEqual(self.assignment.note, '')
        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertTrue(any('note is required' in m for m in messages))

    def test_whitespace_only_note_is_rejected(self):
        response = self.client.post(self.url, {'note': '   '}, follow=True)
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.status, Assignment.Status.ASSIGNED)
        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertTrue(any('note is required' in m for m in messages))

    def test_missing_note_key_is_rejected_not_a_server_error(self):
        response = self.client.post(self.url, {}, follow=True)
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.status, Assignment.Status.ASSIGNED)
        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertTrue(any('note is required' in m for m in messages))

    def test_valid_note_is_accepted(self):
        response = self.client.post(self.url, {'note': 'forgot the bin'})
        self.assignment.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.assignment.status, Assignment.Status.SKIPPED)
        self.assertEqual(self.assignment.note, 'forgot the bin')

    def test_get_is_not_allowed(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)

    def test_nonexistent_assignment_returns_404(self):
        response = self.client.post('/assignments/999999/skip/', {'note': 'x'})
        self.assertEqual(response.status_code, 404)


class ReassignViewTests(TestCase):
    def setUp(self):
        self.alice = Member.objects.create(name='Alice')
        self.bob = Member.objects.create(name='Bob')
        self.dishes = Chore.objects.create(name='Dishes', difficulty='light')
        make_rotation(self.dishes, self.alice, self.bob)
        self.assignment = services.get_or_create_current_assignment(self.dishes)
        self.url = f'/assignments/{self.assignment.pk}/reassign/'

    def test_valid_reassign_updates_member_status_and_note(self):
        response = self.client.post(self.url, {'member': self.bob.pk, 'note': 'Alice is sick'})
        self.assignment.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.assignment.member, self.bob)
        self.assertEqual(self.assignment.status, Assignment.Status.REASSIGNED)
        self.assertEqual(self.assignment.note, 'Alice is sick')

    def test_empty_note_is_rejected(self):
        response = self.client.post(self.url, {'member': self.bob.pk, 'note': ''}, follow=True)
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.member, self.alice)
        self.assertEqual(self.assignment.status, Assignment.Status.ASSIGNED)
        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertTrue(any('note is required' in m for m in messages))

    def test_missing_member_is_rejected(self):
        response = self.client.post(self.url, {'member': '', 'note': 'Alice is sick'}, follow=True)
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.member, self.alice)
        self.assertEqual(self.assignment.status, Assignment.Status.ASSIGNED)
        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertTrue(any('Select a member' in m for m in messages))

    def test_non_numeric_member_is_rejected_not_a_server_error(self):
        response = self.client.post(self.url, {'member': 'not-an-id', 'note': 'Alice is sick'}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.member, self.alice)
        self.assertEqual(self.assignment.status, Assignment.Status.ASSIGNED)


class HistoryViewTests(TestCase):
    def setUp(self):
        alice = Member.objects.create(name='Alice')
        self.dishes = Chore.objects.create(name='Dishes', difficulty='light')
        make_rotation(self.dishes, alice)
        self.pending = Assignment.objects.create(
            chore=self.dishes, member=alice, week_start=date(2026, 8, 24),
            status=Assignment.Status.ASSIGNED,
        )
        self.older = Assignment.objects.create(
            chore=self.dishes, member=alice, week_start=date(2026, 8, 10),
            status=Assignment.Status.COMPLETED,
        )
        self.newer = Assignment.objects.create(
            chore=self.dishes, member=alice, week_start=date(2026, 8, 17),
            status=Assignment.Status.SKIPPED, note='forgot',
        )

    def test_excludes_pending_assignments(self):
        response = self.client.get('/history/')
        entries = list(response.context['entries'])
        self.assertNotIn(self.pending, entries)
        self.assertIn(self.older, entries)
        self.assertIn(self.newer, entries)

    def test_orders_newest_first(self):
        response = self.client.get('/history/')
        entries = list(response.context['entries'])
        self.assertEqual(entries, [self.newer, self.older])


class OneOffTaskServiceTests(TestCase):
    def test_add_task_requires_title(self):
        with self.assertRaises(ValueError):
            services.add_one_off_task('')

    def test_add_task_creates_pending_task(self):
        task = services.add_one_off_task('Fix the fence')
        self.assertEqual(task.status, OneOffTask.Status.PENDING)

    def test_complete_one_off_task(self):
        task = services.add_one_off_task('Fix the fence')
        services.complete_one_off_task(task)
        task.refresh_from_db()
        self.assertEqual(task.status, OneOffTask.Status.COMPLETED)

    def test_skip_one_off_task_requires_note(self):
        task = services.add_one_off_task('Fix the fence')
        with self.assertRaises(ValueError):
            services.skip_one_off_task(task, '')

    def test_skip_one_off_task_updates_status_and_note(self):
        task = services.add_one_off_task('Fix the fence')
        services.skip_one_off_task(task, 'no materials')
        task.refresh_from_db()
        self.assertEqual(task.status, OneOffTask.Status.SKIPPED)
        self.assertEqual(task.note, 'no materials')


class BacklogViewTests(TestCase):
    def test_get_backlog_returns_200(self):
        response = self.client.get('/backlog/')
        self.assertEqual(response.status_code, 200)

    def test_post_with_title_creates_task(self):
        response = self.client.post('/backlog/', {'title': 'Fix the fence'})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(OneOffTask.objects.filter(title='Fix the fence').exists())

    def test_post_with_blank_title_does_not_create_task(self):
        response = self.client.post('/backlog/', {'title': '   '}, follow=True)
        self.assertEqual(OneOffTask.objects.count(), 0)
        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertTrue(any('title is required' in m for m in messages))

    def test_complete_task_updates_status(self):
        task = OneOffTask.objects.create(title='Fix the fence')
        response = self.client.post(f'/tasks/{task.pk}/complete/')
        task.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(task.status, OneOffTask.Status.COMPLETED)

    def test_skip_task_without_note_is_rejected(self):
        task = OneOffTask.objects.create(title='Fix the fence')
        response = self.client.post(f'/tasks/{task.pk}/skip/', {'note': ''}, follow=True)
        task.refresh_from_db()
        self.assertEqual(task.status, OneOffTask.Status.PENDING)
        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertTrue(any('note is required' in m for m in messages))

    def test_skip_task_with_note_updates_status_and_note(self):
        task = OneOffTask.objects.create(title='Fix the fence')
        response = self.client.post(f'/tasks/{task.pk}/skip/', {'note': 'no materials'})
        task.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(task.status, OneOffTask.Status.SKIPPED)
        self.assertEqual(task.note, 'no materials')


class ModelConstraintTests(TestCase):
    def test_assignment_unique_per_chore_and_week(self):
        alice = Member.objects.create(name='Alice')
        bob = Member.objects.create(name='Bob')
        dishes = Chore.objects.create(name='Dishes', difficulty='light')
        Assignment.objects.create(chore=dishes, member=alice, week_start=date(2026, 8, 17))
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Assignment.objects.create(chore=dishes, member=bob, week_start=date(2026, 8, 17))

    def test_rotation_slot_unique_order_per_chore(self):
        alice = Member.objects.create(name='Alice')
        bob = Member.objects.create(name='Bob')
        dishes = Chore.objects.create(name='Dishes', difficulty='light')
        RotationSlot.objects.create(chore=dishes, member=alice, order=1)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                RotationSlot.objects.create(chore=dishes, member=bob, order=1)

    def test_rotation_slot_unique_member_per_chore(self):
        alice = Member.objects.create(name='Alice')
        dishes = Chore.objects.create(name='Dishes', difficulty='light')
        RotationSlot.objects.create(chore=dishes, member=alice, order=1)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                RotationSlot.objects.create(chore=dishes, member=alice, order=2)
