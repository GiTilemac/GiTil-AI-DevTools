from django.urls import path

from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('assignments/<int:pk>/complete/', views.complete_assignment, name='complete_assignment'),
    path('assignments/<int:pk>/skip/', views.skip_assignment, name='skip_assignment'),
    path('history/', views.history, name='history'),
    path('backlog/', views.backlog, name='backlog'),
    path('tasks/<int:pk>/complete/', views.complete_task, name='complete_task'),
    path('tasks/<int:pk>/skip/', views.skip_task, name='skip_task'),
]
