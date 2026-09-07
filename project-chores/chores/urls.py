from django.urls import path

from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('assignments/<int:pk>/complete/', views.complete_assignment, name='complete_assignment'),
    path('assignments/<int:pk>/skip/', views.skip_assignment, name='skip_assignment'),
]
