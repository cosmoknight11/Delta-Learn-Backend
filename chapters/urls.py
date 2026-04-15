from django.urls import path
from . import views

urlpatterns = [
    path('subjects/', views.SubjectListView.as_view(), name='subject-list'),
    path('subjects/<slug:slug>/', views.SubjectDetailView.as_view(), name='subject-detail'),
    path(
        'subjects/<slug:slug>/chapters/<int:chapter_number>/',
        views.ChapterDetailView.as_view(),
        name='chapter-detail',
    ),
]
