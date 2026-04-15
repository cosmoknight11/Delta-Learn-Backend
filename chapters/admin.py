from django.contrib import admin
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html

from .models import Subject, Chapter, Question, Takeaway, Highlight, Note, StagedRequest, Subscription


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
    list_display = ('chapter_number', 'title', 'subject', 'part', 'question_count', 'preview_link')
    list_filter = ('subject', 'part')
    search_fields = ('title', 'subtitle')
    list_select_related = ('subject',)
    inlines = [QuestionInline, TakeawayInline]
    change_form_template = 'admin/chapters/chapter_change_form.html'

    @admin.display(description='Questions')
    def question_count(self, obj):
        return obj.questions.count()

    @admin.display(description='Preview')
    def preview_link(self, obj):
        url = reverse('admin:chapters_chapter_preview', args=[obj.pk])
        return format_html(
            '<a href="{}" target="_blank" style="white-space:nowrap">'
            '&#9654; Preview</a>',
            url,
        )

    def get_urls(self):
        custom = [
            path(
                '<int:pk>/preview/',
                self.admin_site.admin_view(self.preview_view),
                name='chapters_chapter_preview',
            ),
        ]
        return custom + super().get_urls()

    def preview_view(self, request, pk):
        chapter = get_object_or_404(
            Chapter.objects.select_related('subject'),
            pk=pk,
        )
        questions = chapter.questions.all()
        takeaways = chapter.takeaways.all()
        context = {
            **self.admin_site.each_context(request),
            'chapter': chapter,
            'questions': questions,
            'takeaways': takeaways,
        }
        return TemplateResponse(
            request,
            'admin/chapters/chapter_preview.html',
            context,
        )


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


@admin.register(StagedRequest)
class StagedRequestAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'operation', 'target_model', 'target_id',
        'status_badge', 'requested_by', 'created_at', 'reviewed_at',
    )
    list_filter = ('status', 'operation', 'target_model')
    list_select_related = ('requested_by', 'reviewed_by')
    readonly_fields = (
        'operation', 'target_model', 'target_id', 'payload_pretty',
        'requested_by', 'created_at', 'reviewed_by', 'reviewed_at', 'review_note',
    )
    actions = ['approve_selected', 'reject_selected']

    @admin.display(description='Status')
    def status_badge(self, obj):
        colors = {'pending': '#ff9f0a', 'approved': '#30d158', 'rejected': '#ff453a'}
        color = colors.get(obj.status, '#888')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 10px;'
            'border-radius:8px;font-size:0.8rem;font-weight:600">{}</span>',
            color, obj.status.upper(),
        )

    @admin.display(description='Payload')
    def payload_pretty(self, obj):
        import json
        return format_html(
            '<pre style="max-height:400px;overflow:auto;background:#1c1c1e;'
            'color:#f5f5f7;padding:12px;border-radius:8px;font-size:0.82rem">{}</pre>',
            json.dumps(obj.payload, indent=2),
        )

    @admin.action(description='Approve selected requests')
    def approve_selected(self, request, queryset):
        count = 0
        for sr in queryset.filter(status='pending'):
            try:
                sr.apply(reviewer=request.user)
                count += 1
            except Exception as e:
                self.message_user(request, f'Failed to apply #{sr.pk}: {e}', level='error')
        self.message_user(request, f'{count} request(s) approved and applied.')

    @admin.action(description='Reject selected requests')
    def reject_selected(self, request, queryset):
        count = 0
        for sr in queryset.filter(status='pending'):
            sr.reject(reviewer=request.user, note='Bulk rejected via admin')
            count += 1
        self.message_user(request, f'{count} request(s) rejected.')


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'email', 'subject', 'difficulty', 'is_active',
        'last_sent_at', 'created_at',
    )
    list_filter = ('is_active', 'difficulty', 'subject')
    search_fields = ('email',)
    readonly_fields = ('last_sent_at', 'last_chapter_sent', 'created_at')
    actions = ['send_test_deltamail']

    @admin.action(description='Send test DeltaMail to selected subscribers')
    def send_test_deltamail(self, request, queryset):
        from django.core.management import call_command
        from io import StringIO

        active = queryset.filter(is_active=True)
        if not active.exists():
            self.message_user(request, 'No active subscriptions selected.', level='warning')
            return

        emails = list(active.values_list('email', flat=True).distinct())
        out = StringIO()
        try:
            call_command('send_deltamails', '--emails', *emails, stdout=out)
            self.message_user(request, f'DeltaMail sent to: {", ".join(emails)}')
        except Exception as e:
            self.message_user(request, f'Failed: {e}', level='error')
