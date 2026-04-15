#!/bin/bash
set -e

echo "── Delta Learn Backend starting ──"

# Run migrations
echo "→ Running migrations…"
python manage.py migrate --noinput

# Collect static files
echo "→ Collecting static files…"
python manage.py collectstatic --noinput 2>/dev/null || true

# Create superuser if it doesn't exist
echo "→ Ensuring superuser exists…"
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
import os
su = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'cosmoknight11')
email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@deltalearn.com')
pw = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'helloDelta123')
if not User.objects.filter(username=su).exists():
    User.objects.create_superuser(su, email, pw)
    print(f'  Created superuser: {su}')
else:
    print(f'  Superuser {su} already exists')
"

# Seed content data if Subject table is empty
echo "→ Checking content data…"
python manage.py shell -c "
from chapters.models import Subject
if Subject.objects.count() == 0:
    print('  No subjects found — running seed_data…')
    from django.core.management import call_command
    call_command('seed_data')
else:
    print(f'  {Subject.objects.count()} subjects, {Subject.objects.count()} loaded')
"

# Seed topics from chapters if EmailTopic table is empty
echo "→ Checking topic pool…"
python manage.py shell -c "
from chapters.models import EmailTopic
if EmailTopic.objects.count() == 0:
    print('  Topic pool empty — running seed_topics…')
    from django.core.management import call_command
    call_command('seed_topics')
else:
    print(f'  Topic pool has {EmailTopic.objects.count()} topics')
"

# Install cron jobs
echo "→ Installing cron jobs…"
python manage.py crontab add 2>/dev/null || echo "  (crontab setup skipped)"

# Start cron daemon in background
echo "→ Starting cron daemon…"
cron

echo "── Ready. Starting server… ──"
exec "$@"
