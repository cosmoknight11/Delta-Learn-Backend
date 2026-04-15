from rest_framework import serializers
from .models import Subject, Chapter, Question, Takeaway


class QuestionSerializer(serializers.ModelSerializer):
    table = serializers.JSONField(source='table_data', default=None)
    diagramCaption = serializers.CharField(source='diagram_caption')
    diagram2Caption = serializers.CharField(source='diagram2_caption')

    class Meta:
        model = Question
        fields = [
            'question', 'difficulty', 'tldr', 'answer', 'points',
            'diagram', 'diagramCaption', 'diagram2', 'diagram2Caption',
            'table', 'followup',
        ]


class TakeawaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Takeaway
        fields = ['content']


class ChapterListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for sidebar / chapter lists."""
    id = serializers.IntegerField(source='chapter_number')
    question_count = serializers.SerializerMethodField()

    class Meta:
        model = Chapter
        fields = ['id', 'part', 'title', 'subtitle', 'question_count']

    def get_question_count(self, obj):
        return obj.questions.count()


class ChapterDetailSerializer(serializers.ModelSerializer):
    """Full serializer with nested questions and takeaways."""
    id = serializers.IntegerField(source='chapter_number')
    questions = QuestionSerializer(many=True, read_only=True)
    takeaways = serializers.SerializerMethodField()

    class Meta:
        model = Chapter
        fields = ['id', 'part', 'title', 'subtitle', 'questions', 'takeaways']

    def get_takeaways(self, obj):
        return [t.content for t in obj.takeaways.all()]


class SubjectListSerializer(serializers.ModelSerializer):
    chapter_count = serializers.SerializerMethodField()
    written_count = serializers.SerializerMethodField()
    accentColor = serializers.CharField(source='accent_color')

    class Meta:
        model = Subject
        fields = [
            'slug', 'name', 'description', 'accentColor',
            'chapter_count', 'written_count',
        ]

    def get_chapter_count(self, obj):
        return obj.chapters.count()

    def get_written_count(self, obj):
        return obj.chapters.filter(questions__isnull=False).distinct().count()


class SubjectDetailSerializer(serializers.ModelSerializer):
    accentColor = serializers.CharField(source='accent_color')
    chapters = ChapterListSerializer(many=True, read_only=True)

    class Meta:
        model = Subject
        fields = ['slug', 'name', 'description', 'accentColor', 'chapters']
