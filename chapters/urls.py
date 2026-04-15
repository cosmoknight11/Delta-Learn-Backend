from django.urls import path
from . import views

urlpatterns = [
    # Public
    path('subjects/', views.SubjectListView.as_view(), name='subject-list'),
    path('subjects/<slug:slug>/', views.SubjectDetailView.as_view(), name='subject-detail'),
    path(
        'subjects/<slug:slug>/chapters/<int:chapter_number>/',
        views.ChapterDetailView.as_view(),
        name='chapter-detail',
    ),

    # Authenticated — highlights
    path('highlights/', views.HighlightListCreateView.as_view(), name='highlight-list'),
    path('highlights/<int:pk>/', views.HighlightDestroyView.as_view(), name='highlight-delete'),

    # Authenticated — notes
    path('notes/', views.NoteListCreateView.as_view(), name='note-list'),
    path('notes/<int:pk>/', views.NoteDetailView.as_view(), name='note-detail'),
    path('notes/<int:pk>/analyze/', views.NoteAIAnalyzeView.as_view(), name='note-analyze'),
]
