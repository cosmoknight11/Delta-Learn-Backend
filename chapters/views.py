from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from .models import Subject, Chapter, Highlight, Note
from .serializers import (
    SubjectListSerializer,
    SubjectDetailSerializer,
    ChapterDetailSerializer,
    HighlightSerializer,
    NoteSerializer,
)


# ── Public (read-only) views ──

class SubjectListView(generics.ListAPIView):
    queryset = Subject.objects.all()
    serializer_class = SubjectListSerializer


class SubjectDetailView(generics.RetrieveAPIView):
    queryset = Subject.objects.prefetch_related('chapters')
    serializer_class = SubjectDetailSerializer
    lookup_field = 'slug'


class ChapterDetailView(generics.GenericAPIView):
    def get(self, request, slug, chapter_number):
        subject = get_object_or_404(Subject, slug=slug)
        chapter = get_object_or_404(
            Chapter.objects.prefetch_related('questions', 'takeaways'),
            subject=subject,
            chapter_number=chapter_number,
        )
        serializer = ChapterDetailSerializer(chapter)
        return Response(serializer.data)


# ── Authenticated views ──

class HighlightListCreateView(generics.ListCreateAPIView):
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


class HighlightDestroyView(generics.DestroyAPIView):
    serializer_class = HighlightSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Highlight.objects.filter(user=self.request.user)


class NoteListCreateView(generics.ListCreateAPIView):
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


class NoteDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = NoteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Note.objects.filter(user=self.request.user)


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
