import hmac
import logging
import threading

from django.conf import settings
from django.core.management import call_command
from django.http import JsonResponse
from django.utils import timezone
from django.views import View

logger = logging.getLogger(__name__)

ALLOWED_TASKS = {
    'send-deltamails': 'send_deltamails',
    'refresh-topics': 'refresh_topics',
}


def _run_command(command):
    """Execute a management command in a background thread."""
    started = timezone.now()
    try:
        call_command(command)
        elapsed = (timezone.now() - started).total_seconds()
        logger.info('Cron task %s completed in %.1fs', command, elapsed)
    except Exception:
        elapsed = (timezone.now() - started).total_seconds()
        logger.exception('Cron task %s failed after %.1fs', command, elapsed)


class CronTriggerView(View):
    """Secret-protected webhook that external cron services can call.

    Validates the token, kicks off the management command in a background
    thread, and returns 202 Accepted immediately so the HTTP caller
    (cron-job.org) never times out.

    Usage:
        GET /cron/send-deltamails/?token=<CRON_SECRET>
        GET /cron/refresh-topics/?token=<CRON_SECRET>
    """

    http_method_names = ['get']

    def get(self, request, task_name):
        secret = settings.CRON_SECRET
        if not secret:
            return JsonResponse({'status': 'disabled'}, status=403)

        token = request.GET.get('token', '')
        if not hmac.compare_digest(token, secret):
            return JsonResponse({'status': 'forbidden'}, status=403)

        command = ALLOWED_TASKS.get(task_name)
        if not command:
            return JsonResponse(
                {'status': 'error', 'detail': f'Unknown task: {task_name}'},
                status=404,
            )

        thread = threading.Thread(target=_run_command, args=(command,), daemon=True)
        thread.start()
        logger.info('Cron task %s dispatched in background thread', command)

        return JsonResponse({
            'status': 'accepted',
            'task': command,
            'detail': 'Running in background',
        }, status=202)
