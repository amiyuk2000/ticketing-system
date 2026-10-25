"""Role-based rules for who can do what with tickets.

Roles are Django groups (created in migration 0005):
- Managers: see and change all tickets, assign them and view reports
- Technicians: see tickets assigned to them (and ones they reported),
  and update the status of tickets assigned to them
- Everyone else (staff): see only the tickets they reported, and edit
  them while still open
"""
from functools import wraps

from django.core.exceptions import PermissionDenied
from django.db.models import Q

from .models import Ticket

MANAGERS = 'Managers'
TECHNICIANS = 'Technicians'

REPORTER_FIELDS = ['title', 'description', 'property', 'floor', 'space', 'category', 'sub_type', 'priority']
ALL_FIELDS = REPORTER_FIELDS + ['assigned_to', 'status', 'complete_by', 'cost_limit']
TECHNICIAN_FIELDS = ['status']


def _group_names(user):
    # Role checks happen several times per request (views, templates), so load
    # the user's groups once and cache them on the user object
    if not hasattr(user, '_group_names_cache'):
        user._group_names_cache = set(user.groups.values_list('name', flat=True))
    return user._group_names_cache


def is_manager(user):
    return user.is_superuser or MANAGERS in _group_names(user)


def is_technician(user):
    return TECHNICIANS in _group_names(user)


def role_name(user):
    if is_manager(user):
        return 'Manager'
    if is_technician(user):
        return 'Technician'
    return 'Staff'


def visible_tickets(user):
    """The tickets a user is allowed to see. Every ticket query in the views starts here."""
    if is_manager(user):
        return Ticket.objects.all()
    if is_technician(user):
        return Ticket.objects.filter(Q(assigned_to=user) | Q(created_by=user))
    return Ticket.objects.filter(created_by=user)


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
