import os

from django.apps import AppConfig


class ChaptersConfig(AppConfig):
    name = 'chapters'

    def ready(self):
        is_dev_reload = os.environ.get('RUN_MAIN') == 'true'
        is_wsgi = not os.environ.get('RUN_MAIN')

        if is_wsgi or is_dev_reload:
            from delta_learn.scheduler import start_scheduler
            start_scheduler()
