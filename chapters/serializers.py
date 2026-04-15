from rest_framework import serializers
from .models import Subject, Chapter, Question, Takeaway, Highlight, Note


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
    _dbId = serializers.IntegerField(source='pk', read_only=True)
    questions = QuestionSerializer(many=True, read_only=True)
    takeaways = serializers.SerializerMethodField()

    class Meta:
        model = Chapter
        fields = ['id', '_dbId', 'part', 'title', 'subtitle', 'questions', 'takeaways']

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


class HighlightSerializer(serializers.ModelSerializer):
    chapter_slug = serializers.SerializerMethodField()
    chapter_title = serializers.SerializerMethodField()
    chapter_number = serializers.IntegerField(source='chapter.chapter_number', read_only=True)

    class Meta:
        model = Highlight
        fields = [
            'id', 'chapter', 'chapter_number', 'chapter_slug', 'chapter_title',
            'question_index', 'text', 'color', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def get_chapter_slug(self, obj):
        return obj.chapter.subject.slug

    def get_chapter_title(self, obj):
        return obj.chapter.title


class NoteSerializer(serializers.ModelSerializer):
    subject_slug = serializers.SlugRelatedField(
        source='subject', slug_field='slug',
        queryset=Subject.objects.all(), required=False, allow_null=True,
    )
    chapter_number = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = Note
        fields = [
            'id', 'subject_slug', 'chapter', 'chapter_number',
            'content', 'ai_summary', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'ai_summary', 'created_at', 'updated_at']

    def create(self, validated_data):
        chapter_number = validated_data.pop('chapter_number', None)
        subject = validated_data.get('subject')
        if chapter_number and subject:
            chapter = Chapter.objects.filter(
                subject=subject, chapter_number=chapter_number
            ).first()
            validated_data['chapter'] = chapter
        return super().create(validated_data)
