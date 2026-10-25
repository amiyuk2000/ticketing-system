from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django.utils import timezone

from tickets.models import Comment, Floor, Property, Space, SubType, Ticket
from tickets.permissions import MANAGERS, TECHNICIANS

DEMO_PASSWORD = 'demo1234'

# username -> group (None = regular staff)
DEMO_USERS = {
    'manager': MANAGERS,
    'technician': TECHNICIANS,
    'staff': None,
}

# property -> floor -> spaces
LOCATIONS = {
    'Building A': {
        'Ground Floor': ['Lobby', 'Reception', 'Kitchen'],
        '2nd Floor': ['Room 2.04', 'Open Office'],
        '3rd Floor': ['Open Office', 'Room 3.10'],
        '4th Floor': ['Kitchenette', 'Room 4.01'],
        'Stairwells': ['Stairwell 2'],
    },
    'Building B': {
        'Basement': ['Server Room'],
        'Ground Floor': ['Toilets', 'Back Entrance'],
        '1st Floor': ['Room 1.12', 'Open Office'],
        '3rd Floor': ['Room 3.01'],
    },
    'Car Park': {
        'Level 0': ['Entrance Gate', 'Exit Gate'],
    },
}

# Each sample ticket. "age" is how many hours ago it was reported; "responded" is
# how many hours after reporting someone first picked it up (None = not yet).
SAMPLE_TICKETS = [
    dict(title='Flickering lights in meeting room', description='Lights in Room 2.04 flicker constantly during meetings.',
         where=('Building A', '2nd Floor', 'Room 2.04'), category='electrical', sub_type='Burnt bulb',
         priority=2, status='open', assignee='technician', creator='staff', age=20),
    dict(title='Leaking tap in kitchen', description='Cold water tap drips even when fully closed.',
         where=('Building A', 'Ground Floor', 'Kitchen'), category='plumbing', sub_type='Leak',
         priority=1, status='in_progress', assignee='technician', creator='staff', age=50, responded=3,
         comments=[('technician', 'Washer is worn. Replacement part ordered, fitting on Thursday.')]),
    dict(title='Air conditioning not working', description='Server room temperature above 28°C, AC unit not responding.',
         where=('Building B', 'Basement', 'Server Room'), category='hvac', sub_type='No cooling',
         priority=4, status='open', assignee='technician', creator='manager', age=6, cost_limit='1500',
         comments=[('manager', 'Servers at risk. Please treat as top priority and get a contractor quote if needed.')]),
    dict(title='Spill in main lobby', description='Coffee spilled near the entrance, slip hazard.',
         where=('Building A', 'Ground Floor', 'Lobby'), category='cleaning', sub_type='Spill',
         priority=3, status='resolved', assignee=None, creator='staff', age=30, responded=1),
    dict(title='Power socket sparking', description='Socket next to desk 14 sparks when plugging in.',
         where=('Building B', '1st Floor', 'Open Office'), category='electrical', sub_type='Faulty socket',
         priority=4, status='in_progress', assignee='technician', creator='staff', age=2, responded=0.5,
         comments=[('technician', 'Socket isolated and taped off. Replacing this afternoon.'),
                   ('staff', 'Thanks, I have moved to desk 16 for now.')]),
    dict(title='Blocked toilet', description="Ground floor men's toilet is blocked.",
         where=('Building B', 'Ground Floor', 'Toilets'), category='plumbing', sub_type='Blockage',
         priority=3, status='closed', assignee='technician', creator='manager', age=100, responded=2),
    dict(title='Heating too high on 3rd floor', description='Thermostat seems stuck at 26°C.',
         where=('Building A', '3rd Floor', 'Open Office'), category='hvac', sub_type='Thermostat fault',
         priority=2, status='open', assignee=None, creator='staff', age=10),
    dict(title='Broken chair in reception', description='Chair leg is cracked and wobbly.',
         where=('Building A', 'Ground Floor', 'Reception'), category='other', sub_type='Furniture',
         priority=1, status='open', assignee=None, creator='staff', age=4),
    dict(title='Car park barrier stuck', description='Exit barrier stays down; staff are queueing to leave.',
         where=('Car Park', 'Level 0', 'Exit Gate'), category='electrical', sub_type='Power outage',
         priority=3, status='in_progress', assignee='technician', creator='manager', age=30, responded=4, cost_limit='800'),
    dict(title='Windows not cleaned', description='Second-floor windows have not been cleaned in months.',
         where=('Building A', '2nd Floor', 'Open Office'), category='cleaning', sub_type='Windows',
         priority=1, status='open', assignee=None, creator='staff', age=1),
    dict(title='Radiator cold in Room 1.12', description='Radiator stays cold even with valve fully open.',
         where=('Building B', '1st Floor', 'Room 1.12'), category='hvac', sub_type='No heating',
         priority=2, status='in_progress', assignee='technician', creator='staff', age=40, responded=6),
    dict(title='Water pressure low', description='Very low pressure from all taps on 4th floor.',
         where=('Building A', '4th Floor', 'Kitchenette'), category='plumbing', sub_type='Low water pressure',
         priority=2, status='open', assignee=None, creator='manager', age=80),
    dict(title='Bins overflowing', description='Recycling bins at the back entrance are overflowing.',
         where=('Building B', 'Ground Floor', 'Back Entrance'), category='cleaning', sub_type='Waste and bins',
         priority=2, status='resolved', assignee=None, creator='staff', age=26, responded=5),
    dict(title='Emergency light faulty', description='Emergency exit sign above stairwell 2 is not lit.',
         where=('Building A', 'Stairwells', 'Stairwell 2'), category='electrical', sub_type='Emergency lighting',
         priority=4, status='open', assignee=None, creator='manager', age=1),
    dict(title='Door handle loose', description='Handle on the meeting room door is coming off.',
         where=('Building B', '3rd Floor', 'Room 3.01'), category='other', sub_type='Doors and locks',
         priority=1, status='closed', assignee='technician', creator='staff', age=200, responded=24),
]


class Command(BaseCommand):
    help = 'Create demo users (one per role), locations and sample tickets for showcasing the app.'

    def handle(self, *args, **options):
        users = self.create_users()
        spaces = self.create_locations()
        now = timezone.now()

        added = 0
        for data in SAMPLE_TICKETS:
            space = spaces[data['where']]
            ticket, was_created = Ticket.objects.update_or_create(
                title=data['title'],
                defaults={
                    'description': data['description'],
                    'property': space.floor.property,
                    'floor': space.floor,
                    'space': space,
                    'category': data['category'],
                    'sub_type': SubType.objects.get(category=data['category'], name=data['sub_type']),
                    'priority': data['priority'],
                    'status': data['status'],
                    'assigned_to': users.get(data['assignee']),
                    'created_by': users[data['creator']],
                    'cost_limit': Decimal(data['cost_limit']) if data.get('cost_limit') else None,
                },
            )
            added += was_created

            # Backdate the ticket so the SLA deadlines, overdue badges and response times look realistic.
            # .update() skips save(), and auto_now_add can only be overridden this way.
            created_at = now - timedelta(hours=data['age'])
            responded = data.get('responded')
            ticket.created_at = created_at
            Ticket.objects.filter(pk=ticket.pk).update(
                created_at=created_at,
                complete_by=ticket.sla_deadline(),
                responded_at=created_at + timedelta(hours=responded) if responded is not None else None,
            )

            ticket.comments.all().delete()
            for i, (author, body) in enumerate(data.get('comments', [])):
                comment = Comment.objects.create(ticket=ticket, author=users[author], body=body)
                Comment.objects.filter(pk=comment.pk).update(created_at=created_at + timedelta(minutes=30 * (i + 1)))

        self.stdout.write(self.style.SUCCESS(
            f'Added {added} sample tickets, reset {len(SAMPLE_TICKETS) - added}. Password for all demo users: {DEMO_PASSWORD}'
        ))

    def create_users(self):
        users = {}
        for username, group_name in DEMO_USERS.items():
            user, created = User.objects.get_or_create(username=username)
            user.set_password(DEMO_PASSWORD)
            user.save()
            if group_name:
                user.groups.add(Group.objects.get_or_create(name=group_name)[0])
            users[username] = user
            self.stdout.write(f"{'Created' if created else 'Updated'} user '{username}' ({group_name or 'Staff'})")
        return users

    def create_locations(self):
        """Create the demo properties, floors and spaces; return {(property, floor, space): Space}."""
        spaces = {}
        for prop_name, floors in LOCATIONS.items():
            prop, _ = Property.objects.get_or_create(name=prop_name)
            for floor_name, space_names in floors.items():
                floor, _ = Floor.objects.get_or_create(property=prop, name=floor_name)
                for space_name in space_names:
                    space, _ = Space.objects.get_or_create(floor=floor, name=space_name)
                    spaces[(prop_name, floor_name, space_name)] = space
        return spaces
