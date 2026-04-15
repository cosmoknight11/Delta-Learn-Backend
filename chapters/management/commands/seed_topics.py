import re

from django.core.management.base import BaseCommand

from chapters.models import Chapter, EmailTopic


class Command(BaseCommand):
    help = 'Seed EmailTopic pool from existing Chapter objects.'

    def handle(self, *args, **options):
        created = 0
        skipped = 0

        for ch in Chapter.objects.select_related('subject').all():
            if EmailTopic.objects.filter(subject=ch.subject, chapter=ch).exists():
                skipped += 1
                continue

            keywords = self._extract_keywords(ch)

            EmailTopic.objects.create(
                subject=ch.subject,
                title=ch.title,
                keywords=keywords,
                source='chapter',
                chapter=ch,
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(
            f'Done. Created {created} topics, skipped {skipped} (already exist).'
        ))

    @staticmethod
    def _extract_keywords(chapter):
        """Pull keyword list from chapter subtitle, part, and title."""
        raw = f'{chapter.subtitle or ""} {chapter.part or ""} {chapter.title}'
        raw = raw.lower()
        raw = re.sub(r'[^a-z0-9\s/\-]', ' ', raw)
        tokens = raw.split()

        stop = {
            'the', 'and', 'for', 'with', 'that', 'this', 'from', 'are',
            'was', 'were', 'been', 'have', 'has', 'had', 'will', 'would',
            'could', 'should', 'may', 'might', 'can', 'how', 'what',
            'when', 'where', 'why', 'who', 'which', 'about', 'into',
            'like', 'more', 'also', 'use', 'using', 'used', 'part',
            'chapter', 'deep', 'dive', 'introduction', 'overview',
            'advanced', 'basics', 'beyond',
        }
        seen = set()
        keywords = []
        for t in tokens:
            t = t.strip('-/')
            if len(t) >= 3 and t not in stop and t not in seen:
                seen.add(t)
                keywords.append(t)

        return keywords[:15]
