from django.contrib import admin

from .models import Assignment, Chore, Member, OneOffTask, RotationSlot


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ['name']


@admin.register(Chore)
class ChoreAdmin(admin.ModelAdmin):
    list_display = ['name', 'difficulty']
    list_filter = ['difficulty']


@admin.register(RotationSlot)
class RotationSlotAdmin(admin.ModelAdmin):
    list_display = ['chore', 'order', 'member']
    list_filter = ['chore']
    ordering = ['chore', 'order']


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ['chore', 'week_start', 'member', 'status']
    list_filter = ['status', 'chore']
    date_hierarchy = 'week_start'


@admin.register(OneOffTask)
class OneOffTaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'status', 'created_at']
    list_filter = ['status']
