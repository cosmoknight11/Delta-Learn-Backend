import json
import os

from django.core.management.base import BaseCommand

from chapters.models import Subject, EmailTopic


class Command(BaseCommand):
    help = (
        'Use Gemma AI to discover new interview topics for each subject '
        'and add them to the EmailTopic pool.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--subject', type=str, default='',
            help='Limit to a single subject slug (default: all).',
        )
        parser.add_argument(
            '--count', type=int, default=20,
            help='Number of new topics to request per subject (default: 20).',
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Print topics without saving.',
        )

    def handle(self, *args, **options):
        api_key = os.environ.get('GEMINI_API_KEY', '')
        if not api_key:
            self.stderr.write(self.style.ERROR('GEMINI_API_KEY not set.'))
            return

        from google import genai
        client = genai.Client(api_key=api_key)

        subjects = Subject.objects.all()
        if options['subject']:
            subjects = subjects.filter(slug=options['subject'])

        total_created = 0

        for subj in subjects:
            existing = list(
                EmailTopic.objects.filter(subject=subj)
                .values_list('title', flat=True)
            )
            existing_lower = {t.lower() for t in existing}

            prompt = self._build_prompt(subj, existing, options['count'])
            self.stdout.write(f'Requesting topics for {subj.name}...')

            try:
                response = client.models.generate_content(
                    model='gemma-3-27b-it',
                    contents=prompt,
                )
                topics = self._parse_response(response.text)
            except Exception as exc:
                self.stderr.write(self.style.ERROR(f'  AI error: {exc}'))
                continue

            created = 0
            for t in topics:
                title = t.get('title', '').strip()
                if not title or title.lower() in existing_lower:
                    continue

                keywords = [
                    k.strip().lower()
                    for k in t.get('keywords', [])
                    if isinstance(k, str) and k.strip()
                ][:15]

                if options['dry_run']:
                    self.stdout.write(f'  [DRY] {title}  keywords={keywords}')
                else:
                    EmailTopic.objects.create(
                        subject=subj,
                        title=title,
                        keywords=keywords,
                        source='web',
                    )
                created += 1
                existing_lower.add(title.lower())

            total_created += created
            self.stdout.write(self.style.SUCCESS(
                f'  {subj.name}: +{created} new topics '
                f'({len(existing)} existed, {len(topics)} returned)'
            ))

        self.stdout.write(self.style.SUCCESS(
            f'\nDone. {total_created} new topic(s) added.'
        ))

    @staticmethod
    def _build_prompt(subject, existing_titles, count):
        existing_block = '\n'.join(f'- {t}' for t in existing_titles[:80])
        return f"""You are an expert technical interviewer at a FAANG company.

Subject area: {subject.name}
Description: {subject.description}

The following topics are ALREADY in our database — do NOT repeat them:
{existing_block}

Generate {count} NEW, distinct interview topics that top companies
(Google, Meta, Amazon, Netflix, Uber, Stripe, etc.) ask about in
{subject.name} interviews in 2026.

Requirements:
- Each topic should be specific enough to generate 3-4 interview questions.
- Cover breadth: include both classic staples and trending/modern topics.
- Include system design scenarios ("Design X"), concept deep-dives, and
  trade-off comparisons.
- Provide 3-8 keywords per topic for search/matching.

RESPOND WITH ONLY a JSON array. No markdown, no explanation.
Format:
[
  {{"title": "Design a Distributed Rate Limiter", "keywords": ["rate limiting", "sliding window", "redis", "token bucket", "distributed"]}},
  ...
]"""

    @staticmethod
    def _parse_response(text):
        text = text.strip()
        if text.startswith('```'):
            text = text.split('\n', 1)[-1]
            if text.endswith('```'):
                text = text[:-3]
        text = text.strip()

        start = text.find('[')
        end = text.rfind(']')
        if start == -1 or end == -1:
            return []

        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            return []
