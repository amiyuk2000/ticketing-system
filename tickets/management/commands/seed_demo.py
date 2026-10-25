from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand

from tickets.models import Ticket
from tickets.permissions import MANAGERS, TECHNICIANS

DEMO_PASSWORD = 'demo1234'

# username -> group (None = regular staff)
DEMO_USERS = {
    'manager': MANAGERS,
    'technician': TECHNICIANS,
    'staff': None,
}

# (title, description, location, category, priority, status, assigned_to, created_by)
SAMPLE_TICKETS = [
    ('Flickering lights in meeting room', 'Lights in Room 2.04 flicker constantly during meetings.', 'Building A, Room 2.04', 'electrical', 2, 'open', 'technician', 'staff'),
    ('Leaking tap in kitchen', 'Cold water tap drips even when fully closed.', 'Building A, Kitchen', 'plumbing', 1, 'in_progress', 'technician', 'staff'),
    ('Air conditioning not working', 'Server room temperature above 28°C, AC unit not responding.', 'Building B, Server Room', 'hvac', 4, 'open', 'technician', 'manager'),
    ('Spill in main lobby', 'Coffee spilled near the entrance, slip hazard.', 'Building A, Lobby', 'cleaning', 3, 'resolved', None, 'staff'),
    ('Power socket sparking', 'Socket next to desk 14 sparks when plugging in.', 'Building B, Open Office', 'electrical', 4, 'in_progress', 'technician', 'staff'),
    ('Blocked toilet', "Ground floor men's toilet is blocked.", 'Building B, Ground Floor', 'plumbing', 3, 'closed', 'technician', 'manager'),
    ('Heating too high on 3rd floor', 'Thermostat seems stuck at 26°C.', 'Building A, 3rd Floor', 'hvac', 2, 'open', None, 'staff'),
    ('Broken chair in reception', 'Chair leg is cracked and wobbly.', 'Building A, Reception', 'other', 1, 'open', None, 'staff'),
    ('Car park barrier stuck', 'Exit barrier stays down; staff are queueing to leave.', 'Car Park, Exit Gate', 'electrical', 3, 'open', 'technician', 'manager'),
    ('Windows not cleaned', 'Second-floor windows have not been cleaned in months.', 'Building A, 2nd Floor', 'cleaning', 1, 'open', None, 'staff'),
    ('Radiator cold in Room 1.12', 'Radiator stays cold even with valve fully open.', 'Building B, Room 1.12', 'hvac', 2, 'in_progress', 'technician', 'staff'),
    ('Water pressure low', 'Very low pressure from all taps on 4th floor.', 'Building A, 4th Floor', 'plumbing', 2, 'open', None, 'manager'),
    ('Bins overflowing', 'Recycling bins at the back entrance are overflowing.', 'Building B, Back Entrance', 'cleaning', 2, 'resolved', None, 'staff'),
    ('Emergency light faulty', 'Emergency exit sign above stairwell 2 is not lit.', 'Building A, Stairwell 2', 'electrical', 4, 'open', None, 'manager'),
    ('Door handle loose', 'Handle on the meeting room door is coming off.', 'Building B, Room 3.01', 'other', 1, 'closed', 'technician', 'staff'),
]


class Command(BaseCommand):
    help = 'Create demo users (one per role) and sample tickets for showcasing the app.'

    def handle(self, *args, **options):
        users = {}
        for username, group_name in DEMO_USERS.items():
            user, created = User.objects.get_or_create(username=username)
            user.set_password(DEMO_PASSWORD)
            user.save()
            if group_name:
                user.groups.add(Group.objects.get_or_create(name=group_name)[0])
            users[username] = user
            self.stdout.write(f"{'Created' if created else 'Updated'} user '{username}' ({group_name or 'Staff'})")

        added = 0
        for title, description, location, category, priority, status, assignee, creator in SAMPLE_TICKETS:
            _, was_created = Ticket.objects.update_or_create(
                title=title,
                defaults={
                    'description': description,
                    'location': location,
                    'category': category,
                    'priority': priority,
                    'status': status,
                    'assigned_to': users.get(assignee),
                    'created_by': users[creator],
                },
            )
            added += was_created
        self.stdout.write(self.style.SUCCESS(
            f'Added {added} sample tickets, reset {len(SAMPLE_TICKETS) - added}. Password for all demo users: {DEMO_PASSWORD}'
        ))
