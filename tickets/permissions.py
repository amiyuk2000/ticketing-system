"""Role-based rules for who can do what with tickets.

Roles are Django groups (created in migration 0005):
- Managers: full access, including assigning tickets and viewing reports
- Technicians: update the status of tickets assigned to them
- Everyone else (staff): report tickets and edit their own while still open
"""
from functools import wraps

from django.core.exceptions import PermissionDenied

MANAGERS = 'Managers'
TECHNICIANS = 'Technicians'

ALL_FIELDS = ['title', 'description', 'location', 'category', 'priority', 'assigned_to', 'status']
REPORTER_FIELDS = ['title', 'description', 'location', 'category', 'priority']
TECHNICIAN_FIELDS = ['status']


def is_manager(user):
    return user.is_superuser or user.groups.filter(name=MANAGERS).exists()


def is_technician(user):
    return user.groups.filter(name=TECHNICIANS).exists()


def role_name(user):
    if is_manager(user):
        return 'Manager'
    if is_technician(user):
        return 'Technician'
    return 'Staff'


def creatable_fields(user):
    """Fields a user may fill in when reporting a new ticket."""
    return ALL_FIELDS if is_manager(user) else REPORTER_FIELDS


def editable_fields(user, ticket):
    """Fields a user may change on an existing ticket (empty list = no access)."""
    if is_manager(user):
        return ALL_FIELDS
    if is_technician(user) and ticket.assigned_to_id == user.id:
        return TECHNICIAN_FIELDS
    if ticket.created_by_id == user.id and ticket.status == 'open':
        return REPORTER_FIELDS
    return []


def manager_required(view_func):
    """Return 403 Forbidden unless the user is a manager. Use after @login_required."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not is_manager(request.user):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapper
