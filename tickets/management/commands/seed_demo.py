from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from tickets.models import Ticket

DEMO_USERNAME = 'demo'
DEMO_PASSWORD = 'demo1234'

SAMPLE_TICKETS = [
    ('Flickering lights in meeting room', 'Lights in Room 2.04 flicker constantly during meetings.', 'Building A, Room 2.04', 'electrical', 2, 'open', True),
    ('Leaking tap in kitchen', 'Cold water tap drips even when fully closed.', 'Building A, Kitchen', 'plumbing', 1, 'in_progress', True),
    ('Air conditioning not working', 'Server room temperature above 28°C, AC unit not responding.', 'Building B, Server Room', 'hvac', 4, 'open', True),
    ('Spill in main lobby', 'Coffee spilled near the entrance, slip hazard.', 'Building A, Lobby', 'cleaning', 3, 'resolved', False),
    ('Power socket sparking', 'Socket next to desk 14 sparks when plugging in.', 'Building B, Open Office', 'electrical', 4, 'in_progress', False),
    ('Blocked toilet', 'Ground floor men\'s toilet is blocked.', 'Building B, Ground Floor', 'plumbing', 3, 'closed', False),
    ('Heating too high on 3rd floor', 'Thermostat seems stuck at 26°C.', 'Building A, 3rd Floor', 'hvac', 2, 'open', False),
    ('Broken chair in reception', 'Chair leg is cracked and wobbly.', 'Building A, Reception', 'other', 1, 'open', False),
]


class Command(BaseCommand):
    help = 'Create a demo user and sample tickets for showcasing the app.'

    def handle(self, *args, **options):
        user, created = User.objects.get_or_create(username=DEMO_USERNAME)
        user.set_password(DEMO_PASSWORD)
        user.save()
        self.stdout.write(f"{'Created' if created else 'Updated'} user '{DEMO_USERNAME}' (password: {DEMO_PASSWORD})")

        added = 0
        for title, description, location, category, priority, status, assign_to_demo in SAMPLE_TICKETS:
            _, was_created = Ticket.objects.get_or_create(
                title=title,
                defaults={
                    'description': description,
                    'location': location,
                    'category': category,
                    'priority': priority,
                    'status': status,
                    'assigned_to': user if assign_to_demo else None,
                },
            )
            added += was_created
        self.stdout.write(self.style.SUCCESS(f'Added {added} sample tickets.'))
