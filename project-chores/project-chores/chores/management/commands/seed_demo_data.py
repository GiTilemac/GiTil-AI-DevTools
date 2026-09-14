from django.core.management.base import BaseCommand

from chores.models import Chore, Member, OneOffTask, RotationSlot

MEMBERS = ['Alice', 'Bob', 'Carol']

CHORES = [
    ('Dishes', Chore.Difficulty.LIGHT, ['Alice', 'Bob', 'Carol']),
    ('Trash', Chore.Difficulty.LIGHT, ['Bob', 'Carol', 'Alice']),
    ('Laundry', Chore.Difficulty.MEDIUM, ['Carol', 'Alice', 'Bob']),
    ('Deep Clean Kitchen', Chore.Difficulty.HEAVY, ['Alice', 'Bob', 'Carol']),
]

ONE_OFF_TASKS = ['Fix the leaky faucet', 'Clean out the garage']


class Command(BaseCommand):
    help = 'Create a small demo household (members, chores, rotations, one-off tasks) for trying out the app.'

    def handle(self, *args, **options):
        members = {}
        for name in MEMBERS:
            member, created = Member.objects.get_or_create(name=name)
            members[name] = member
            self.stdout.write(f"{'Created' if created else 'Already exists'}: member '{name}'")

        for chore_name, difficulty, rotation_order in CHORES:
            chore, created = Chore.objects.get_or_create(name=chore_name, defaults={'difficulty': difficulty})
            self.stdout.write(f"{'Created' if created else 'Already exists'}: chore '{chore_name}'")
            for order, member_name in enumerate(rotation_order, start=1):
                _, slot_created = RotationSlot.objects.get_or_create(
                    chore=chore, member=members[member_name], defaults={'order': order},
                )
                if slot_created:
                    self.stdout.write(f"  Added '{member_name}' to '{chore_name}' rotation (position {order})")

        for title in ONE_OFF_TASKS:
            _, created = OneOffTask.objects.get_or_create(title=title)
            self.stdout.write(f"{'Created' if created else 'Already exists'}: one-off task '{title}'")

        self.stdout.write(self.style.SUCCESS('Demo data ready.'))
