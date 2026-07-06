from django.core.management.base import BaseCommand
from Account.models import OTP
from django.utils import timezone
from datetime import timedelta


class Command(BaseCommand):
    help = "Delete expired OTP records from the database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--minutes",
            type=int,
            default=10,
            help="Maximum OTP age in minutes (default: 10)",
        )

    def handle(self, *args, **options):
        threshold = timezone.now() - timedelta(minutes=options["minutes"])
        count, _ = OTP.objects.filter(created_at__lte=threshold).delete()
        self.stdout.write(
            self.style.SUCCESS(f"✓ {count} expired OTP record(s) deleted.")
        )