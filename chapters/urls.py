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
    path('manage/chapters/<int:pk>/populate/', views.AdminChapterPopulateView.as_view(), name='admin-chapter-populate'),
    path('manage/chapters/<int:pk>/stage-populate/', views.AdminChapterStagePopulateView.as_view(), name='admin-chapter-stage-populate'),

    # ── Staged requests (authenticated, admin approves) ──
    path('staged/', views.StagedRequestListCreateView.as_view(), name='staged-list'),
    path('staged/<int:pk>/', views.StagedRequestDetailView.as_view(), name='staged-detail'),
    path('staged/<int:pk>/approve/', views.StagedRequestApproveView.as_view(), name='staged-approve'),
    path('staged/<int:pk>/reject/', views.StagedRequestRejectView.as_view(), name='staged-reject'),

    # ── Authenticated (user-scoped) ──
    path('highlights/', views.HighlightListCreateView.as_view(), name='highlight-list'),
    path('highlights/<int:pk>/', views.HighlightDetailView.as_view(), name='highlight-detail'),
    path('notes/', views.NoteListCreateView.as_view(), name='note-list'),
    path('notes/<int:pk>/', views.NoteDetailView.as_view(), name='note-detail'),
    path('notes/<int:pk>/analyze/', views.NoteAIAnalyzeView.as_view(), name='note-analyze'),

    # ── DeltaMails subscriptions ──
    path('deltamails/', views.SubscriptionListView.as_view(), name='deltamails-list'),
    path('deltamails/subscribe/', views.SubscriptionCreateView.as_view(), name='deltamails-subscribe'),
    path('deltamails/<int:pk>/preferences/', views.SubscriptionUpdatePreferencesView.as_view(), name='deltamails-preferences'),
    path('deltamails/unsubscribe/', views.SubscriptionUnsubscribeView.as_view(), name='deltamails-unsubscribe'),
]
