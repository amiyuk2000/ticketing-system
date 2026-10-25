from datetime import timedelta

from django.db import migrations

SUB_TYPES = {
    'electrical': ['Burnt bulb', 'Faulty socket', 'Power outage', 'Emergency lighting'],
    'plumbing': ['Leak', 'Blockage', 'Low water pressure'],
    'hvac': ['No cooling', 'No heating', 'Thermostat fault'],
    'cleaning': ['Spill', 'Waste and bins', 'Windows'],
    'other': ['Furniture', 'Doors and locks', 'General'],
}

# Copied from Ticket.SLA_HOURS at the time of writing; migrations must not import live model code
SLA_HOURS = {4: 4, 3: 24, 2: 72, 1: 168}


def forwards(apps, schema_editor):
    SubType = apps.get_model('tickets', 'SubType')
    Property = apps.get_model('tickets', 'Property')
    Ticket = apps.get_model('tickets', 'Ticket')

    for category, names in SUB_TYPES.items():
        for name in names:
            SubType.objects.get_or_create(category=category, name=name)

    # Old tickets had free-text locations like "Building A, Room 2.04".
    # Use the part before the comma as the property, and keep the full text
    # in the description so no detail is lost.
    for ticket in Ticket.objects.all():
        location = (ticket.location or '').strip()
        building, _, rest = location.partition(',')
        building = building.strip()
        if not building or building.lower() == 'other':
            building = 'Unknown'
        ticket.property, _ = Property.objects.get_or_create(name=building)
        if rest.strip():
            ticket.description = f'{ticket.description}\n\nOriginal location: {location}'
        if ticket.complete_by is None:
            hours = SLA_HOURS.get(ticket.priority, 72)
            ticket.complete_by = (ticket.created_at + timedelta(hours=hours)).replace(second=0, microsecond=0)
        ticket.save(update_fields=['property', 'description', 'complete_by'])


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0006_locations_subtypes_sla_comments'),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
