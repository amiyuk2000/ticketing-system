from django import template

register = template.Library()

# Bootstrap badge colours for each priority and status value
PRIORITY_CLASSES = {
    1: 'text-bg-secondary',
    2: 'text-bg-info',
    3: 'text-bg-warning',
    4: 'text-bg-danger',
}

STATUS_CLASSES = {
    'open': 'text-bg-primary',
    'in_progress': 'text-bg-warning',
    'resolved': 'text-bg-success',
    'closed': 'text-bg-secondary',
}


@register.filter
def priority_class(value):
    return PRIORITY_CLASSES.get(value, 'text-bg-light')


@register.filter
def status_class(value):
    return STATUS_CLASSES.get(value, 'text-bg-light')


@register.filter
def duration(value):
    """Format a timedelta compactly, e.g. "2d 3h", "4h 15m" or "12m"."""
    if value is None:
        return '—'
    minutes = int(value.total_seconds() // 60)
    days, minutes = divmod(minutes, 60 * 24)
    hours, minutes = divmod(minutes, 60)
    if days:
        return f'{days}d {hours}h'
    if hours:
        return f'{hours}h {minutes}m'
    return f'{minutes}m'
