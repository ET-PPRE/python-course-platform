import csv

from allauth.account.models import EmailAddress
from django.core.management.base import BaseCommand

from users.models import UserProfile as User


class Command(BaseCommand):
    help = "Import or update users from a CSV file (no emails sent)."

    def add_arguments(self, parser):
        parser.add_argument("csv_file", type=str, help="Path to the CSV file")

    def handle(self, *args, **options):
        csv_file = options["csv_file"]

        with open(csv_file, newline="", encoding="latin1") as f:
            reader = csv.DictReader(f)
            for row in reader:
                email = row.get("email")
                first_name = row.get("first_name", "")
                last_name = row.get("last_name", "")
                password = row.get("password", None)
                username = row.get("username") or (email.split("@")[0] if email else None)
                
                # --- Get or create user ---
                user, created = User.objects.get_or_create(
                    username=username,
                    email=email,
                    defaults={
                        "first_name": first_name,
                        "last_name": last_name,
                    },
                )

                if created:
                    # Set password for new user
                    if password:
                        user.set_password(password)
                    else:
                        user.set_unusable_password()
                    user.save()
                    self.stdout.write(self.style.SUCCESS(f"✅ Created user: {email}"))
                else:
                    # Update existing user info
                    user.first_name = first_name
                    user.last_name = last_name
                    if password:
                        user.set_password(password)
                    user.save()
                    self.stdout.write(self.style.WARNING(f"📝 Updated user: {email}"))

                # --- Create or update email entry ---
                email_entry, email_created = EmailAddress.objects.get_or_create(
                    user=user,
                    email=email,
                    defaults={"primary": True, "verified": True},
                )
                if not email_entry.primary or not email_entry.verified:
                    email_entry.primary = True
                    email_entry.verified = True
                    email_entry.save()

        self.stdout.write(self.style.SUCCESS("🎉 Import/update completed successfully!"))
