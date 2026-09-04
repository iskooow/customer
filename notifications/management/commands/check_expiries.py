"""
Management command to check expiries and create notifications.

Evaluates every customer's document expiry dates against day windows
(expired, 7-day, 30-day, 60-day) and creates an in-app Notification for
the relevant recipients. Notifications that were previously live (UNREAD
or READ) for a document but no longer fall within any warning window are
automatically dismissed so the Expiry Alerts tab reflects the current
state (e.g. a renewed document clears its old alert).

The actual scan logic lives in :mod:`notifications.services` and is also
used by the on-demand "Refresh alerts" action in the web UI, so both
entry points produce identical, preference-aware alerts.

Usage:
    manage.py check_expiries
"""

from django.core.management.base import BaseCommand

from notifications.services import run_expiry_scan


class Command(BaseCommand):
    help = 'Check document expiries and create notifications'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without creating notifications'
        )
        parser.add_argument(
            '--send-email',
            action='store_true',
            help='Send email notifications (if configured)'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        send_email = options['send_email']

        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No notifications will be created')
            )

        result = run_expiry_scan(
            user_scope=None,
            send_email=send_email,
            dry_run=dry_run,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f'Completed: {result["created_count"]} notifications created, '
                f'{result["skipped_count"]} skipped, '
                f'{result["dismissed_count"]} stale alerts dismissed.'
            )
        )
