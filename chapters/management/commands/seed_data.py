import json
from pathlib import Path

from django.core.management.base import BaseCommand
from chapters.models import Subject, Chapter, Question, Takeaway

FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent.parent / 'fixtures'

FIXTURE_FILES = ['system-design.json', 'dsa.json', 'ai.json']


class Command(BaseCommand):
    help = 'Seed database from JSON fixtures exported from the React app'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Delete all existing data before seeding',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing data...')
            Takeaway.objects.all().delete()
            Question.objects.all().delete()
            Chapter.objects.all().delete()
            Subject.objects.all().delete()

        for filename in FIXTURE_FILES:
            filepath = FIXTURES_DIR / filename
            if not filepath.exists():
                self.stderr.write(f'Fixture not found: {filepath}')
                continue

            with open(filepath, 'r') as f:
                data = json.load(f)

            subj_data = data['subject']
            subject, created = Subject.objects.update_or_create(
                slug=subj_data['slug'],
                defaults={
                    'name': subj_data['name'],
                    'description': subj_data.get('description', ''),
                    'accent_color': subj_data.get('accentColor', '#0a84ff'),
                    'order': subj_data.get('order', 0),
                },
            )
            action = 'Created' if created else 'Updated'
            self.stdout.write(f'{action} subject: {subject.name}')

            for ch_data in data['chapters']:
                chapter, _ = Chapter.objects.update_or_create(
                    subject=subject,
                    chapter_number=ch_data['id'],
                    defaults={
                        'part': ch_data.get('part', ''),
                        'title': ch_data['title'],
                        'subtitle': ch_data.get('subtitle', ''),
                        'order': ch_data['id'],
                    },
                )

                chapter.questions.all().delete()
                for qi, q_data in enumerate(ch_data.get('questions', [])):
                    Question.objects.create(
                        chapter=chapter,
                        order=qi,
                        question=q_data.get('question', ''),
                        difficulty=q_data.get('difficulty', ''),
                        tldr=q_data.get('tldr', ''),
                        answer=q_data.get('answer', ''),
                        points=q_data.get('points', []),
                        diagram=q_data.get('diagram', ''),
                        diagram_caption=q_data.get('diagramCaption', ''),
                        diagram2=q_data.get('diagram2', ''),
                        diagram2_caption=q_data.get('diagram2Caption', ''),
                        table_data=q_data.get('table', None),
                        followup=q_data.get('followup', ''),
                    )

                chapter.takeaways.all().delete()
                for ti, t_content in enumerate(ch_data.get('takeaways', [])):
                    Takeaway.objects.create(
                        chapter=chapter,
                        order=ti,
                        content=t_content,
                    )

            total_q = sum(
                len(c.get('questions', [])) for c in data['chapters']
            )
            self.stdout.write(
                f'  {len(data["chapters"])} chapters, {total_q} questions'
            )

        self.stdout.write(self.style.SUCCESS('Seeding complete.'))
