import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from django.core.management import call_command

logger = logging.getLogger(__name__)

_started = False


def _run(command):
    try:
        logger.info('Scheduler: starting %s', command)
        call_command(command)
        logger.info('Scheduler: %s completed', command)
    except Exception:
        logger.exception('Scheduler: %s failed', command)


def start_scheduler():
    global _started
    if _started:
        return
    _started = True

    scheduler = BackgroundScheduler(daemon=True)

    scheduler.add_job(
        _run,
        trigger=CronTrigger(hour=1, minute=30),
        args=('send_deltamails',),
        id='send_deltamails',
        replace_existing=True,
        misfire_grace_time=3600,
    )

    scheduler.add_job(
        _run,
        trigger=CronTrigger(day_of_week='sun', hour=21, minute=30),
        args=('refresh_topics',),
        id='refresh_topics',
        replace_existing=True,
        misfire_grace_time=3600,
    )

    scheduler.start()
    logger.info('APScheduler started with %d jobs', len(scheduler.get_jobs()))
