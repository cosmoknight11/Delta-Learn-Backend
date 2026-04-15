from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter

from .models import Subject, Chapter, Question, Takeaway, Highlight, Note
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
class HighlightDestroyView(generics.DestroyAPIView):
    """Delete a highlight."""
    serializer_class = HighlightSerializer
    permission_classes = [permissions.IsAuthenticated]

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
