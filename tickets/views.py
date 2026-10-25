from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count
from .models import Ticket
from .forms import TicketForm
from .permissions import creatable_fields, editable_fields, is_manager, manager_required, visible_tickets

TICKETS_PER_PAGE = 10


def paginate(request, queryset):
    return Paginator(queryset, TICKETS_PER_PAGE).get_page(request.GET.get('page'))


@login_required
def ticket_list(request):
    # select_related loads each ticket's assignee in the same query,
    # instead of one extra query per row in the table
    tickets = visible_tickets(request.user).select_related('assigned_to')

    # Filter tickets based on facilities criteria
    location = request.GET.get('location')
    category = request.GET.get('category')
    priority = request.GET.get('priority')
    status = request.GET.get('status')

    if location:
        tickets = tickets.filter(location__icontains=location)
    if category:
        tickets = tickets.filter(category=category)
    if priority:
        tickets = tickets.filter(priority=priority)
    if status:
        tickets = tickets.filter(status=status)

    sees_all = is_manager(request.user)
    context = {
        'page_obj': paginate(request, tickets),
        'heading': 'All Tickets' if sees_all else 'My Tickets',
        'empty_message': 'No tickets found.' if sees_all else "No tickets found. Tickets you report will appear here.",
        'category_choices': Ticket.CATEGORY_CHOICES,
        'priority_choices': Ticket.PRIORITY_CHOICES,
        'status_choices': Ticket.STATUS_CHOICES,
    }
    return render(request, 'tickets/ticket_list.html', context)

@login_required
def ticket_create(request):
    allowed = creatable_fields(request.user)
    if request.method == 'POST':
        form = TicketForm(request.POST, allowed_fields=allowed)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.created_by = request.user
            ticket.save()
            messages.success(request, f'Ticket "{ticket.title}" created.')
            return redirect('ticket_detail', pk=ticket.pk)
    else:
        form = TicketForm(allowed_fields=allowed)
    return render(request, 'tickets/ticket_form.html', {'form': form})

@login_required
def ticket_edit(request, pk):
    ticket = get_object_or_404(visible_tickets(request.user), pk=pk)
    allowed = editable_fields(request.user, ticket)
    if not allowed:
        raise PermissionDenied
    if request.method == 'POST':
        form = TicketForm(request.POST, instance=ticket, allowed_fields=allowed)
        if form.is_valid():
            form.save()
            messages.success(request, f'Ticket "{ticket.title}" updated.')
            return redirect('ticket_detail', pk=ticket.pk)
    else:
        form = TicketForm(instance=ticket, allowed_fields=allowed)
    return render(request, 'tickets/ticket_form.html', {'form': form, 'ticket': ticket})

@login_required
def ticket_detail(request, pk):
    # 404 (not 403) for tickets the user can't see, so it doesn't reveal that they exist
    ticket = get_object_or_404(visible_tickets(request.user).select_related('assigned_to', 'created_by'), pk=pk)
    context = {
        'ticket': ticket,
        'can_edit': bool(editable_fields(request.user, ticket)),
    }
    return render(request, 'tickets/ticket_detail.html', context)

@login_required
def assigned_tickets(request):
    tickets = Ticket.objects.filter(assigned_to=request.user).select_related('assigned_to')
    context = {
        'page_obj': paginate(request, tickets),
    }
    return render(request, 'tickets/assigned_tickets.html', context)

@login_required
@manager_required
def ticket_counts_by_category(request):
    ticket_counts = list(Ticket.objects.values('category').annotate(count=Count('category')).order_by('-count'))
    labels = dict(Ticket.CATEGORY_CHOICES)
    total = sum(row['count'] for row in ticket_counts)
    for row in ticket_counts:
        row['label'] = labels.get(row['category'], row['category'])
        row['percent'] = round(row['count'] * 100 / total) if total else 0
    context = {
        'ticket_counts': ticket_counts,
        'total': total,
    }
    return render(request, 'tickets/ticket_counts_by_category.html', context)
