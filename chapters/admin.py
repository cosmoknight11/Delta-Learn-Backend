from django.contrib import admin
from .models import Subject, Chapter, Question, Takeaway, Highlight, Note


class ChapterInline(admin.TabularInline):
    model = Chapter
    extra = 0
    fields = ('chapter_number', 'part', 'title', 'order')
    show_change_link = True


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'accent_color', 'chapter_count', 'order')
    list_editable = ('order',)
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ChapterInline]

    @admin.display(description='Chapters')
    def chapter_count(self, obj):
        return obj.chapters.count()


class QuestionInline(admin.StackedInline):
    model = Question
    extra = 0
    fieldsets = (
        (None, {
            'fields': ('order', 'question', 'difficulty', 'tldr'),
        }),
        ('Answer Content', {
            'fields': ('answer', 'points', 'followup'),
            'classes': ('collapse',),
        }),
        ('Diagrams', {
            'fields': (
                'diagram', 'diagram_caption',
                'diagram2', 'diagram2_caption',
            ),
            'classes': ('collapse',),
        }),
        ('Table Data', {
            'fields': ('table_data',),
            'classes': ('collapse',),
        }),
    )


class TakeawayInline(admin.TabularInline):
    model = Takeaway
    extra = 0


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ('chapter_number', 'title', 'subject', 'part', 'question_count')
    list_filter = ('subject', 'part')
    search_fields = ('title', 'subtitle')
    list_select_related = ('subject',)
    inlines = [QuestionInline, TakeawayInline]

    @admin.display(description='Questions')
    def question_count(self, obj):
        return obj.questions.count()


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('question_short', 'chapter', 'difficulty', 'order')
    list_filter = ('difficulty', 'chapter__subject')
    search_fields = ('question',)
    list_select_related = ('chapter',)

    @admin.display(description='Question')
    def question_short(self, obj):
        return obj.question[:100]


@admin.register(Takeaway)
class TakeawayAdmin(admin.ModelAdmin):
    list_display = ('content_short', 'chapter', 'order')
    list_filter = ('chapter__subject',)
    list_select_related = ('chapter',)

    @admin.display(description='Content')
    def content_short(self, obj):
        return obj.content[:100]


@admin.register(Highlight)
class HighlightAdmin(admin.ModelAdmin):
    list_display = ('user', 'chapter', 'question_index', 'color', 'text_short', 'created_at')
    list_filter = ('color', 'chapter__subject')
    list_select_related = ('user', 'chapter', 'chapter__subject')

    @admin.display(description='Text')
    def text_short(self, obj):
        return obj.text[:80]


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ('user', 'subject', 'chapter', 'content_short', 'updated_at')
    list_filter = ('subject',)
    list_select_related = ('user', 'subject', 'chapter')

    @admin.display(description='Content')
    def content_short(self, obj):
        return obj.content[:80]
