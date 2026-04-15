from django.db import models


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
