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
        'status_badge', 'requested_by', 'created_at',
    )
    list_filter = ('status', 'operation', 'target_model')
    list_select_related = ('requested_by', 'reviewed_by')
    readonly_fields = (
        'operation', 'target_model', 'target_id',
        'content_preview', 'payload_raw',
        'requested_by', 'created_at', 'reviewed_by', 'reviewed_at', 'review_note',
    )
    fieldsets = (
        ('Request Info', {
            'fields': ('operation', 'target_model', 'target_id', 'status',
                       'requested_by', 'created_at'),
        }),
        ('Content Preview', {
            'fields': ('content_preview',),
        }),
        ('Raw Payload', {
            'fields': ('payload_raw',),
            'classes': ('collapse',),
        }),
        ('Review', {
            'fields': ('reviewed_by', 'reviewed_at', 'review_note'),
        }),
    )
    actions = ['approve_selected', 'reject_selected']

    def get_default_filters(self, request):
        return {'status': 'pending'}

    def changelist_view(self, request, extra_context=None):
        if not request.GET and not request.POST:
            from django.http import HttpResponseRedirect
            return HttpResponseRedirect(f'{request.path}?status=pending')
        return super().changelist_view(request, extra_context=extra_context)

    @admin.display(description='Status')
    def status_badge(self, obj):
        colors = {'pending': '#ff9f0a', 'approved': '#30d158', 'rejected': '#ff453a'}
        color = colors.get(obj.status, '#888')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 10px;'
            'border-radius:8px;font-size:0.8rem;font-weight:600">{}</span>',
            color, obj.status.upper(),
        )

    @admin.display(description='Content Preview')
    def content_preview(self, obj):
        import json
        p = obj.payload
        model = obj.target_model

        css = (
            'background:#111;color:#f5f5f7;padding:20px 24px;border-radius:12px;'
            'font-family:-apple-system,BlinkMacSystemFont,sans-serif;'
            'line-height:1.6;max-width:800px;'
        )
        mark_css = 'background:rgba(255,159,10,0.25);color:#ff9f0a;padding:1px 4px;border-radius:3px;'
        strong_css = 'color:#fff;font-weight:600;'
        h3_css = 'color:#fff;font-size:1.2rem;margin:0 0 8px;font-weight:600;'
        meta_css = 'color:#86868b;font-size:0.8rem;margin-bottom:12px;'
        point_css = (
            'margin:6px 0;padding:8px 12px;background:rgba(255,255,255,0.04);'
            'border-radius:6px;border-left:3px solid #0a84ff;'
        )
        table_css = (
            'width:100%;border-collapse:collapse;margin:12px 0;font-size:0.85rem;'
        )
        th_css = (
            'text-align:left;padding:8px 10px;background:rgba(255,255,255,0.06);'
            'color:#86868b;border-bottom:1px solid rgba(255,255,255,0.1);'
        )
        td_css = (
            'padding:8px 10px;border-bottom:1px solid rgba(255,255,255,0.04);color:#ccc;'
        )

        if model == 'question':
            html = f'<div style="{css}">'

            diff = p.get('difficulty', '')
            diff_colors = {'easy': '#30d158', 'medium': '#ff9f0a', 'hard': '#ff453a'}
            dc = diff_colors.get(diff, '#888')
            html += f'<span style="background:{dc};color:#fff;padding:2px 8px;border-radius:6px;font-size:0.75rem;font-weight:600;text-transform:uppercase;">{diff}</span>'

            html += f'<h3 style="{h3_css} margin-top:10px;">{p.get("question", "")}</h3>'

            tldr = p.get('tldr', '')
            if tldr:
                html += f'<div style="{meta_css}"><em>TL;DR: {tldr}</em></div>'

            answer = p.get('answer', '')
            if answer:
                answer = answer.replace('<mark>', f'<mark style="{mark_css}">').replace('<strong>', f'<strong style="{strong_css}">')
                html += f'<div style="margin:12px 0;color:#ddd;">{answer}</div>'

            points = p.get('points', [])
            if points:
                html += '<div style="margin:12px 0;">'
                for pt in points:
                    pt_html = pt.replace('<mark>', f'<mark style="{mark_css}">').replace('<strong>', f'<strong style="{strong_css}">')
                    html += f'<div style="{point_css}">{pt_html}</div>'
                html += '</div>'

            table = p.get('table_data')
            if table and isinstance(table, dict):
                headers = table.get('headers', [])
                rows = table.get('rows', [])
                html += f'<table style="{table_css}"><thead><tr>'
                for h in headers:
                    html += f'<th style="{th_css}">{h}</th>'
                html += '</tr></thead><tbody>'
                for row in rows:
                    html += '<tr>'
                    for cell in row:
                        html += f'<td style="{td_css}">{cell}</td>'
                    html += '</tr>'
                html += '</tbody></table>'

            diagram = p.get('diagram', '')
            if diagram:
                html += (
                    f'<div style="margin:12px 0;padding:10px;background:rgba(10,132,255,0.08);'
                    f'border-radius:8px;border:1px solid rgba(10,132,255,0.2);">'
                    f'<div style="color:#0a84ff;font-size:0.75rem;font-weight:600;margin-bottom:6px;">MERMAID DIAGRAM</div>'
                    f'<pre style="color:#aaa;font-size:0.8rem;white-space:pre-wrap;margin:0;">{diagram}</pre>'
                )
                cap = p.get('diagram_caption', '')
                if cap:
                    html += f'<div style="color:#86868b;font-size:0.78rem;margin-top:6px;font-style:italic;">{cap}</div>'
                html += '</div>'

            followup = p.get('followup', '')
            if followup:
                followup = followup.replace('<mark>', f'<mark style="{mark_css}">').replace('<strong>', f'<strong style="{strong_css}">')
                html += (
                    f'<div style="margin:14px 0 0;padding:12px;background:rgba(191,90,242,0.08);'
                    f'border-radius:8px;border-left:3px solid #bf5af2;">'
                    f'<div style="color:#bf5af2;font-size:0.75rem;font-weight:600;margin-bottom:4px;">FOLLOW-UP</div>'
                    f'{followup}</div>'
                )

            html += '</div>'
            return format_html(html)

        elif model == 'takeaway':
            content = p.get('content', '')
            content = content.replace('<mark>', f'<mark style="{mark_css}">').replace('<strong>', f'<strong style="{strong_css}">')
            order = p.get('order', '?')
            html = (
                f'<div style="{css}">'
                f'<div style="color:#30d158;font-size:0.75rem;font-weight:600;margin-bottom:6px;">TAKEAWAY #{order}</div>'
                f'<div style="font-size:1rem;">{content}</div>'
                f'</div>'
            )
            return format_html(html)

        elif model == 'chapter':
            html = f'<div style="{css}">'
            html += f'<div style="{meta_css}">{p.get("part", "")}</div>'
            html += f'<h3 style="{h3_css}">{p.get("title", "")}</h3>'
            sub = p.get('subtitle', '')
            if sub:
                html += f'<div style="color:#aaa;font-style:italic;">{sub}</div>'
            html += '</div>'
            return format_html(html)

        elif model == 'subject':
            html = f'<div style="{css}">'
            html += f'<h3 style="{h3_css}">{p.get("name", "")}</h3>'
            html += f'<div style="color:#aaa;">{p.get("description", "")}</div>'
            color = p.get('accent_color', '#888')
            html += f'<div style="margin-top:8px;"><span style="display:inline-block;width:20px;height:20px;background:{color};border-radius:4px;vertical-align:middle;"></span> <span style="color:#86868b;">{color}</span></div>'
            html += '</div>'
            return format_html(html)

        return format_html(
            '<pre style="background:#1c1c1e;color:#f5f5f7;padding:12px;border-radius:8px;">{}</pre>',
            json.dumps(p, indent=2),
        )

    @admin.display(description='Raw JSON')
    def payload_raw(self, obj):
        import json
        return format_html(
            '<pre style="max-height:300px;overflow:auto;background:#1c1c1e;'
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
