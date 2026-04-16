import hmac
import io
import logging
from contextlib import redirect_stdout, redirect_stderr

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


class CronTriggerView(View):
    """Secret-protected webhook that external cron services can call.

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

        started = timezone.now()
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()

        try:
            with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
                call_command(command)
            elapsed = (timezone.now() - started).total_seconds()
            logger.info('Cron task %s completed in %.1fs', command, elapsed)
            return JsonResponse({
                'status': 'ok',
                'task': command,
                'elapsed_seconds': round(elapsed, 1),
                'output': stdout_buf.getvalue()[-500:],
            })
        except Exception as exc:
            elapsed = (timezone.now() - started).total_seconds()
            logger.exception('Cron task %s failed after %.1fs', command, elapsed)
            return JsonResponse({
                'status': 'error',
                'task': command,
                'elapsed_seconds': round(elapsed, 1),
                'detail': str(exc)[:200],
            }, status=500)
