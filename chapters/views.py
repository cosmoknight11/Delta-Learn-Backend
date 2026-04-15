from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter

from django.db import transaction

from .models import Subject, Chapter, Question, Takeaway, Highlight, Note, StagedRequest, Subscription
from .serializers import (
    SubjectListSerializer,
    SubjectDetailSerializer,
    ChapterDetailSerializer,
    SubjectWriteSerializer,
    ChapterWriteSerializer,
    QuestionWriteSerializer,
    TakeawayWriteSerializer,
    HighlightSerializer,
    NoteSerializer,
    StagedRequestSerializer,
    StagedRequestReviewSerializer,
    SubscriptionSerializer,
    SubscriptionCreateSerializer,
    SubscriptionPreferencesSerializer,
    SubscriptionUnsubscribeSerializer,
)


# ────────────────────────────────────────────────────
#  Public (read-only) views
# ────────────────────────────────────────────────────

@extend_schema(tags=['Subjects'])
class SubjectListView(generics.ListAPIView):
    """List all subjects with chapter counts."""
    queryset = Subject.objects.all()
    serializer_class = SubjectListSerializer


@extend_schema(tags=['Subjects'])
class SubjectDetailView(generics.RetrieveAPIView):
    """Get a subject's details and its ordered chapter list."""
    queryset = Subject.objects.prefetch_related('chapters')
    serializer_class = SubjectDetailSerializer
    lookup_field = 'slug'


@extend_schema(tags=['Chapters'])
class ChapterDetailView(generics.GenericAPIView):
    """Get the full content of a single chapter (questions, diagrams, takeaways)."""
    serializer_class = ChapterDetailSerializer

    def get(self, request, slug, chapter_number):
        subject = get_object_or_404(Subject, slug=slug)
        chapter = get_object_or_404(
            Chapter.objects.prefetch_related('questions', 'takeaways'),
            subject=subject,
            chapter_number=chapter_number,
        )
        serializer = ChapterDetailSerializer(chapter)
        return Response(serializer.data)


# ────────────────────────────────────────────────────
#  Admin CRUD views  (staff-only)
# ────────────────────────────────────────────────────

@extend_schema_view(
    list=extend_schema(tags=['Admin — Subjects']),
    create=extend_schema(tags=['Admin — Subjects']),
)
class AdminSubjectListCreateView(generics.ListCreateAPIView):
    """List all subjects or create a new one."""
    queryset = Subject.objects.all()
    serializer_class = SubjectWriteSerializer
    permission_classes = [permissions.IsAdminUser]


@extend_schema_view(
    retrieve=extend_schema(tags=['Admin — Subjects']),
    update=extend_schema(tags=['Admin — Subjects']),
    partial_update=extend_schema(tags=['Admin — Subjects']),
    destroy=extend_schema(tags=['Admin — Subjects']),
)
class AdminSubjectDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a subject."""
    queryset = Subject.objects.all()
    serializer_class = SubjectWriteSerializer
    permission_classes = [permissions.IsAdminUser]
    lookup_field = 'slug'


@extend_schema_view(
    list=extend_schema(
        tags=['Admin — Chapters'],
        parameters=[
            OpenApiParameter('subject', str, description='Filter by subject slug'),
        ],
    ),
    create=extend_schema(tags=['Admin — Chapters']),
)
class AdminChapterListCreateView(generics.ListCreateAPIView):
    """List chapters (optionally filtered by subject) or create a new one."""
    serializer_class = ChapterWriteSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        qs = Chapter.objects.select_related('subject').prefetch_related(
            'questions', 'takeaways'
        )
        slug = self.request.query_params.get('subject')
        if slug:
            qs = qs.filter(subject__slug=slug)
        return qs


@extend_schema_view(
    retrieve=extend_schema(tags=['Admin — Chapters']),
    update=extend_schema(tags=['Admin — Chapters']),
    partial_update=extend_schema(tags=['Admin — Chapters']),
    destroy=extend_schema(tags=['Admin — Chapters']),
)
class AdminChapterDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a chapter."""
    queryset = Chapter.objects.select_related('subject').prefetch_related(
        'questions', 'takeaways'
    )
    serializer_class = ChapterWriteSerializer
    permission_classes = [permissions.IsAdminUser]


@extend_schema_view(
    list=extend_schema(
        tags=['Admin — Questions'],
        parameters=[
            OpenApiParameter('chapter', int, description='Filter by chapter ID'),
            OpenApiParameter('subject', str, description='Filter by subject slug'),
        ],
    ),
    create=extend_schema(tags=['Admin — Questions']),
)
class AdminQuestionListCreateView(generics.ListCreateAPIView):
    """List questions (optionally filtered by chapter/subject) or create a new one."""
    serializer_class = QuestionWriteSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        qs = Question.objects.select_related('chapter', 'chapter__subject')
        chapter_id = self.request.query_params.get('chapter')
        if chapter_id:
            qs = qs.filter(chapter_id=chapter_id)
        slug = self.request.query_params.get('subject')
        if slug:
            qs = qs.filter(chapter__subject__slug=slug)
        return qs


@extend_schema_view(
    retrieve=extend_schema(tags=['Admin — Questions']),
    update=extend_schema(tags=['Admin — Questions']),
    partial_update=extend_schema(tags=['Admin — Questions']),
    destroy=extend_schema(tags=['Admin — Questions']),
)
class AdminQuestionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a question."""
    queryset = Question.objects.select_related('chapter', 'chapter__subject')
    serializer_class = QuestionWriteSerializer
    permission_classes = [permissions.IsAdminUser]


@extend_schema_view(
    list=extend_schema(
        tags=['Admin — Takeaways'],
        parameters=[
            OpenApiParameter('chapter', int, description='Filter by chapter ID'),
        ],
    ),
    create=extend_schema(tags=['Admin — Takeaways']),
)
class AdminTakeawayListCreateView(generics.ListCreateAPIView):
    """List takeaways (optionally filtered by chapter) or create a new one."""
    serializer_class = TakeawayWriteSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        qs = Takeaway.objects.select_related('chapter')
        chapter_id = self.request.query_params.get('chapter')
        if chapter_id:
            qs = qs.filter(chapter_id=chapter_id)
        return qs


@extend_schema_view(
    retrieve=extend_schema(tags=['Admin — Takeaways']),
    update=extend_schema(tags=['Admin — Takeaways']),
    partial_update=extend_schema(tags=['Admin — Takeaways']),
    destroy=extend_schema(tags=['Admin — Takeaways']),
)
class AdminTakeawayDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a takeaway."""
    queryset = Takeaway.objects.select_related('chapter')
    serializer_class = TakeawayWriteSerializer
    permission_classes = [permissions.IsAdminUser]


@extend_schema(tags=['Admin — Chapters'])
class AdminChapterPopulateView(APIView):
    """Bulk-populate a chapter with questions and takeaways in one request.

    Replaces all existing questions/takeaways. Admin only, no staging.
    """
    permission_classes = [permissions.IsAdminUser]

    @transaction.atomic
    def post(self, request, pk):
        chapter = get_object_or_404(
            Chapter.objects.select_related('subject'), pk=pk
        )
        questions_data = request.data.get('questions', [])
        takeaways_data = request.data.get('takeaways', [])

        if not questions_data:
            return Response(
                {'detail': 'At least one question is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        chapter.questions.all().delete()
        chapter.takeaways.all().delete()

        for idx, q in enumerate(questions_data, start=1):
            Question.objects.create(
                chapter=chapter,
                order=q.get('order', idx),
                question=q['question'],
                difficulty=q.get('difficulty', 'medium'),
                tldr=q.get('tldr', ''),
                answer=q.get('answer', ''),
                points=q.get('points', []),
                diagram=q.get('diagram', ''),
                diagram_caption=q.get('diagram_caption', ''),
                diagram2=q.get('diagram2', ''),
                diagram2_caption=q.get('diagram2_caption', ''),
                table_data=q.get('table_data'),
                followup=q.get('followup', ''),
            )

        for idx, t in enumerate(takeaways_data, start=1):
            Takeaway.objects.create(
                chapter=chapter,
                order=t.get('order', idx),
                content=t['content'],
            )

        chapter.refresh_from_db()
        serializer = ChapterDetailSerializer(
            Chapter.objects.prefetch_related('questions', 'takeaways').get(pk=pk)
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)


# ────────────────────────────────────────────────────
#  Authenticated views  (user-scoped)
# ────────────────────────────────────────────────────

@extend_schema_view(
    list=extend_schema(
        tags=['Highlights'],
        parameters=[
            OpenApiParameter('subject', str, description='Filter by subject slug'),
            OpenApiParameter('chapter', int, description='Filter by chapter number'),
        ],
    ),
    create=extend_schema(tags=['Highlights']),
)
class HighlightListCreateView(generics.ListCreateAPIView):
    """List or create user highlights."""
    serializer_class = HighlightSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Highlight.objects.filter(
            user=self.request.user
        ).select_related('chapter', 'chapter__subject')

        slug = self.request.query_params.get('subject')
        if slug:
            qs = qs.filter(chapter__subject__slug=slug)

        chapter_num = self.request.query_params.get('chapter')
        if chapter_num:
            qs = qs.filter(chapter__chapter_number=chapter_num)

        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


@extend_schema(tags=['Highlights'])
class HighlightDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Update (PATCH) or delete a highlight."""
    serializer_class = HighlightSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['patch', 'delete']

    def get_queryset(self):
        return Highlight.objects.filter(user=self.request.user)


@extend_schema_view(
    list=extend_schema(
        tags=['Notes'],
        parameters=[
            OpenApiParameter('subject', str, description='Filter by subject slug'),
            OpenApiParameter('chapter', int, description='Filter by chapter number'),
        ],
    ),
    create=extend_schema(tags=['Notes']),
)
class NoteListCreateView(generics.ListCreateAPIView):
    """List or create user notes."""
    serializer_class = NoteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Note.objects.filter(
            user=self.request.user
        ).select_related('subject', 'chapter')

        slug = self.request.query_params.get('subject')
        if slug:
            qs = qs.filter(subject__slug=slug)

        chapter_num = self.request.query_params.get('chapter')
        if chapter_num:
            qs = qs.filter(chapter__chapter_number=chapter_num)

        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


@extend_schema_view(
    retrieve=extend_schema(tags=['Notes']),
    update=extend_schema(tags=['Notes']),
    partial_update=extend_schema(tags=['Notes']),
    destroy=extend_schema(tags=['Notes']),
)
class NoteDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a note."""
    serializer_class = NoteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Note.objects.filter(user=self.request.user)


@extend_schema(tags=['Notes'])
class NoteAIAnalyzeView(APIView):
    """Placeholder for AI-powered note analysis. Returns a mock summary."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        note = get_object_or_404(Note, pk=pk, user=request.user)
        note.ai_summary = (
            'AI analysis will be available soon. '
            'This feature will summarize your notes, identify knowledge gaps, '
            'and suggest areas to review.'
        )
        note.save(update_fields=['ai_summary'])
        return Response(NoteSerializer(note).data)


# ────────────────────────────────────────────────────
#  Staged request views
# ────────────────────────────────────────────────────

@extend_schema_view(
    list=extend_schema(
        tags=['Staged Requests'],
        parameters=[
            OpenApiParameter('status', str, description='Filter by status: pending, approved, rejected'),
            OpenApiParameter('target_model', str, description='Filter by target model'),
        ],
    ),
    create=extend_schema(tags=['Staged Requests']),
)
class StagedRequestListCreateView(generics.ListCreateAPIView):
    """List staged requests (own for users, all for admin) or create a new one."""
    serializer_class = StagedRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = StagedRequest.objects.select_related('requested_by', 'reviewed_by')
        if not self.request.user.is_staff:
            qs = qs.filter(requested_by=self.request.user)

        req_status = self.request.query_params.get('status')
        if req_status:
            qs = qs.filter(status=req_status)

        target = self.request.query_params.get('target_model')
        if target:
            qs = qs.filter(target_model=target)

        return qs

    def perform_create(self, serializer):
        serializer.save(requested_by=self.request.user)


@extend_schema(tags=['Staged Requests'])
class StagedRequestDetailView(generics.RetrieveAPIView):
    """Retrieve a staged request's details."""
    serializer_class = StagedRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = StagedRequest.objects.select_related('requested_by', 'reviewed_by')
        if not self.request.user.is_staff:
            qs = qs.filter(requested_by=self.request.user)
        return qs


@extend_schema(tags=['Staged Requests'], request=StagedRequestReviewSerializer)
class StagedRequestApproveView(APIView):
    """Approve a staged request and apply the change. Admin only."""
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, pk):
        staged = get_object_or_404(StagedRequest, pk=pk)
        if staged.status != 'pending':
            return Response(
                {'detail': f'Request is already {staged.status}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            staged.apply(reviewer=request.user)
        except Exception as e:
            return Response(
                {'detail': f'Failed to apply: {e}'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(StagedRequestSerializer(staged).data)


@extend_schema(tags=['Staged Requests'], request=StagedRequestReviewSerializer)
class StagedRequestRejectView(APIView):
    """Reject a staged request with an optional note. Admin only."""
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, pk):
        staged = get_object_or_404(StagedRequest, pk=pk)
        if staged.status != 'pending':
            return Response(
                {'detail': f'Request is already {staged.status}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ser = StagedRequestReviewSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        staged.reject(reviewer=request.user, note=ser.validated_data.get('note', ''))
        return Response(StagedRequestSerializer(staged).data)


# ────────────────────────────────────────────────────
#  DeltaMails subscription views
# ────────────────────────────────────────────────────

@extend_schema(tags=['DeltaMails'])
class SubscriptionListView(APIView):
    """List subscriptions for the authenticated user, or by email query param."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        if request.user.is_authenticated:
            qs = Subscription.objects.filter(user=request.user, is_active=True)
        else:
            email = request.query_params.get('email')
            if not email:
                return Response(
                    {'detail': 'Provide ?email= or authenticate.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            qs = Subscription.objects.filter(email=email, is_active=True)
        return Response(SubscriptionSerializer(qs, many=True).data)


@extend_schema(tags=['DeltaMails'], request=SubscriptionCreateSerializer)
class SubscriptionCreateView(APIView):
    """Subscribe to DeltaMails for one or more subjects."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        ser = SubscriptionCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        subjects = Subject.objects.filter(slug__in=data['subjects'])
        if not subjects.exists():
            return Response(
                {'detail': 'No valid subjects found.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        created = []
        for sub in subjects:
            obj, was_created = Subscription.objects.update_or_create(
                email=data['email'],
                subject=sub,
                defaults={
                    'difficulty': data['difficulty'],
                    'custom_prompt': data.get('custom_prompt', ''),
                    'is_active': True,
                    'user': request.user if request.user.is_authenticated else None,
                },
            )
            created.append(obj)

        return Response(
            SubscriptionSerializer(created, many=True).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=['DeltaMails'], request=SubscriptionPreferencesSerializer)
class SubscriptionUpdatePreferencesView(APIView):
    """Update difficulty / custom_prompt for a subscription."""
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        sub = get_object_or_404(Subscription, pk=pk, user=request.user)
        ser = SubscriptionPreferencesSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)

        if 'difficulty' in ser.validated_data:
            sub.difficulty = ser.validated_data['difficulty']
        if 'custom_prompt' in ser.validated_data:
            sub.custom_prompt = ser.validated_data['custom_prompt']
        sub.save()

        return Response(SubscriptionSerializer(sub).data)


@extend_schema(tags=['DeltaMails'], request=SubscriptionUnsubscribeSerializer)
class SubscriptionUnsubscribeView(APIView):
    """Deactivate a subscription by email + subject slug."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        ser = SubscriptionUnsubscribeSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        updated = Subscription.objects.filter(
            email=ser.validated_data['email'],
            subject__slug=ser.validated_data['subject'],
            is_active=True,
        ).update(is_active=False)

        if not updated:
            return Response(
                {'detail': 'No active subscription found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response({'detail': 'Unsubscribed successfully.'})
