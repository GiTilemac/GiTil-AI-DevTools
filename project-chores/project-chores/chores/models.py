from django.db import models


class Member(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Chore(models.Model):
    class Difficulty(models.TextChoices):
        LIGHT = 'light', 'Light'
        MEDIUM = 'medium', 'Medium'
        HEAVY = 'heavy', 'Heavy'

    name = models.CharField(max_length=100, unique=True)
    difficulty = models.CharField(max_length=10, choices=Difficulty.choices, default=Difficulty.MEDIUM)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class RotationSlot(models.Model):
    """One member's fixed position in a chore's weekly rotation order."""
    chore = models.ForeignKey(Chore, on_delete=models.CASCADE, related_name='rotation_slots')
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='rotation_slots')
    order = models.PositiveIntegerField()

    class Meta:
        ordering = ['chore', 'order']
        unique_together = [('chore', 'order'), ('chore', 'member')]

    def __str__(self):
        return f'{self.chore} #{self.order}: {self.member}'


class Assignment(models.Model):
    """A chore assigned to a member for one calendar week (Monday start)."""
    class Status(models.TextChoices):
        ASSIGNED = 'assigned', 'Assigned'
        COMPLETED = 'completed', 'Completed'
        SKIPPED = 'skipped', 'Skipped'
        REASSIGNED = 'reassigned', 'Reassigned'

    chore = models.ForeignKey(Chore, on_delete=models.CASCADE, related_name='assignments')
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='assignments')
    week_start = models.DateField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ASSIGNED)
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-week_start']
        unique_together = [('chore', 'week_start')]

    def __str__(self):
        return f'{self.chore} — {self.week_start} — {self.member}'


class OneOffTask(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        COMPLETED = 'completed', 'Completed'
        SKIPPED = 'skipped', 'Skipped'

    title = models.CharField(max_length=255)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title
