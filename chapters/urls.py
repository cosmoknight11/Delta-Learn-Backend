from django.urls import path
from . import views

urlpatterns = [
    # ── Public (read-only) ──
    path('subjects/', views.SubjectListView.as_view(), name='subject-list'),
    path('subjects/<slug:slug>/', views.SubjectDetailView.as_view(), name='subject-detail'),
    path(
        'subjects/<slug:slug>/chapters/<int:chapter_number>/',
        views.ChapterDetailView.as_view(),
        name='chapter-detail',
    ),

    # ── Admin CRUD (staff-only) ──
    path('manage/subjects/', views.AdminSubjectListCreateView.as_view(), name='admin-subject-list'),
    path('manage/subjects/<slug:slug>/', views.AdminSubjectDetailView.as_view(), name='admin-subject-detail'),
    path('manage/chapters/', views.AdminChapterListCreateView.as_view(), name='admin-chapter-list'),
    path('manage/chapters/<int:pk>/', views.AdminChapterDetailView.as_view(), name='admin-chapter-detail'),
    path('manage/questions/', views.AdminQuestionListCreateView.as_view(), name='admin-question-list'),
    path('manage/questions/<int:pk>/', views.AdminQuestionDetailView.as_view(), name='admin-question-detail'),
    path('manage/takeaways/', views.AdminTakeawayListCreateView.as_view(), name='admin-takeaway-list'),
    path('manage/takeaways/<int:pk>/', views.AdminTakeawayDetailView.as_view(), name='admin-takeaway-detail'),

    # ── Authenticated (user-scoped) ──
    path('highlights/', views.HighlightListCreateView.as_view(), name='highlight-list'),
    path('highlights/<int:pk>/', views.HighlightDestroyView.as_view(), name='highlight-delete'),
    path('notes/', views.NoteListCreateView.as_view(), name='note-list'),
    path('notes/<int:pk>/', views.NoteDetailView.as_view(), name='note-detail'),
    path('notes/<int:pk>/analyze/', views.NoteAIAnalyzeView.as_view(), name='note-analyze'),
]
