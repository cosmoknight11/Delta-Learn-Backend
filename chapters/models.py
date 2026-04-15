from django.conf import settings
from django.db import models, transaction


class Subject(models.Model):
    slug = models.SlugField(max_length=100, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    accent_color = models.CharField(max_length=20, default='#0a84ff')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.name

    @property
    def chapter_count(self):
        return self.chapters.count()

    @property
    def written_count(self):
        return self.chapters.filter(questions__isnull=False).distinct().count()


class Chapter(models.Model):
    subject = models.ForeignKey(
        Subject, on_delete=models.CASCADE, related_name='chapters'
    )
    chapter_number = models.PositiveIntegerField()
    part = models.CharField(max_length=200, blank=True, default='')
    title = models.CharField(max_length=300)
    subtitle = models.TextField(blank=True, default='')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'chapter_number']
        unique_together = ['subject', 'chapter_number']

    def __str__(self):
        return f'{self.subject.slug} Ch.{self.chapter_number}: {self.title}'


class Question(models.Model):
    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
    ]

    chapter = models.ForeignKey(
        Chapter, on_delete=models.CASCADE, related_name='questions'
    )
    order = models.PositiveIntegerField(default=0)
    question = models.TextField()
    difficulty = models.CharField(
        max_length=10, choices=DIFFICULTY_CHOICES, blank=True, default=''
    )
    tldr = models.TextField(blank=True, default='')
    answer = models.TextField(blank=True, default='')
    points = models.JSONField(blank=True, default=list)
    diagram = models.TextField(blank=True, default='')
    diagram_caption = models.CharField(max_length=300, blank=True, default='')
    diagram2 = models.TextField(blank=True, default='')
    diagram2_caption = models.CharField(max_length=300, blank=True, default='')
    table_data = models.JSONField(blank=True, null=True)
    followup = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'Q{self.order}: {self.question[:80]}'


class Takeaway(models.Model):
    chapter = models.ForeignKey(
        Chapter, on_delete=models.CASCADE, related_name='takeaways'
    )
    order = models.PositiveIntegerField(default=0)
    content = models.TextField()

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'Takeaway {self.order}: {self.content[:60]}'


class Highlight(models.Model):
    COLOR_CHOICES = [
        ('yellow', 'Yellow'),
        ('green', 'Green'),
        ('blue', 'Blue'),
        ('pink', 'Pink'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='highlights'
    )
    chapter = models.ForeignKey(
        Chapter, on_delete=models.CASCADE, related_name='highlights'
    )
    question_index = models.PositiveIntegerField()
    text = models.TextField()
    color = models.CharField(max_length=10, choices=COLOR_CHOICES, default='yellow')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username}: {self.text[:50]}'


class StagedRequest(models.Model):
    OPERATION_CHOICES = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
    ]
    TARGET_MODEL_CHOICES = [
        ('subject', 'Subject'),
        ('chapter', 'Chapter'),
        ('question', 'Question'),
        ('takeaway', 'Takeaway'),
        ('chapter_populate', 'Chapter Populate'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    operation = models.CharField(max_length=10, choices=OPERATION_CHOICES)
    target_model = models.CharField(max_length=20, choices=TARGET_MODEL_CHOICES)
    target_id = models.PositiveIntegerField(null=True, blank=True)
    payload = models.JSONField(default=dict)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='staged_requests',
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='reviewed_requests',
    )
    review_note = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        target = f'{self.target_model}#{self.target_id}' if self.target_id else self.target_model
        return f'[{self.status}] {self.operation} {target} by {self.requested_by}'

    def apply(self, reviewer):
        """Execute the staged operation against the real models."""
        from django.utils import timezone

        if self.target_model == 'chapter_populate':
            self._apply_chapter_populate()
        else:
            model_map = {
                'subject': Subject,
                'chapter': Chapter,
                'question': Question,
                'takeaway': Takeaway,
            }
            model_cls = model_map[self.target_model]
            payload = dict(self.payload)

            if self.operation == 'create':
                obj = model_cls.objects.create(**payload)
                self.target_id = obj.pk
            elif self.operation == 'update':
                model_cls.objects.filter(pk=self.target_id).update(**payload)
            elif self.operation == 'delete':
                model_cls.objects.filter(pk=self.target_id).delete()

        self.status = 'approved'
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.save()

    @transaction.atomic
    def _apply_chapter_populate(self):
        chapter = Chapter.objects.get(pk=self.target_id)
        payload = self.payload

        chapter.questions.all().delete()
        chapter.takeaways.all().delete()

        for idx, q in enumerate(payload.get('questions', []), start=1):
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

        for idx, t in enumerate(payload.get('takeaways', []), start=1):
            Takeaway.objects.create(
                chapter=chapter,
                order=t.get('order', idx),
                content=t['content'],
            )

    def reject(self, reviewer, note=''):
        from django.utils import timezone
        self.status = 'rejected'
        self.reviewed_by = reviewer
        self.review_note = note
        self.reviewed_at = timezone.now()
        self.save()


class Note(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notes'
    )
    subject = models.ForeignKey(
        Subject, on_delete=models.CASCADE, related_name='notes',
        null=True, blank=True,
    )
    chapter = models.ForeignKey(
        Chapter, on_delete=models.CASCADE, related_name='notes',
        null=True, blank=True,
    )
    content = models.TextField()
    ai_summary = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        scope = self.chapter or self.subject or 'General'
        return f'{self.user.username} — {scope}: {self.content[:50]}'


class EmailTopic(models.Model):
    SOURCE_CHOICES = [
        ('chapter', 'From Chapter'),
        ('web', 'Web Search'),
        ('manual', 'Manual'),
    ]

    subject = models.ForeignKey(
        Subject, on_delete=models.CASCADE, related_name='email_topics',
    )
    title = models.CharField(max_length=300)
    keywords = models.JSONField(default=list)
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default='manual')
    chapter = models.ForeignKey(
        Chapter, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='email_topics',
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['subject', 'title']

    def __str__(self):
        return f'[{self.subject.slug}] {self.title}'


class Subscription(models.Model):
    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
        ('mixed', 'Mixed'),
    ]

    email = models.EmailField()
    subject = models.ForeignKey(
        Subject, on_delete=models.CASCADE, related_name='subscriptions',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        null=True, blank=True, related_name='subscriptions',
    )
    difficulty = models.CharField(
        max_length=10, choices=DIFFICULTY_CHOICES, default='mixed',
    )
    custom_prompt = models.TextField(
        blank=True, default='',
        help_text='Optional: "explain like I am 5", "focus on trade-offs", etc.',
    )
    is_active = models.BooleanField(default=True)
    last_sent_at = models.DateTimeField(null=True, blank=True)
    last_chapter_sent = models.ForeignKey(
        Chapter, on_delete=models.SET_NULL, null=True, blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['email', 'subject']
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.email} → {self.subject.slug} ({self.difficulty})'


class SentHistory(models.Model):
    subscription = models.ForeignKey(
        Subscription, on_delete=models.CASCADE, related_name='sent_history',
    )
    topic = models.ForeignKey(
        EmailTopic, on_delete=models.CASCADE, related_name='sent_history',
    )
    sent_at = models.DateTimeField(auto_now_add=True)
    questions_json = models.JSONField(default=dict)

    class Meta:
        ordering = ['-sent_at']
        unique_together = ['subscription', 'topic']

    def __str__(self):
        return f'{self.subscription.email} — {self.topic.title} ({self.sent_at:%Y-%m-%d})'
