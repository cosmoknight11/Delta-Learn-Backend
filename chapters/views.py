from rest_framework import generics
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Subject, Chapter
from .serializers import (
    SubjectListSerializer,
    SubjectDetailSerializer,
    ChapterDetailSerializer,
)


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
