from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from .models import Ticket
from .forms import TicketForm

@login_required
def ticket_list(request):
    tickets = Ticket.objects.all().order_by('-created_at')

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

    context = {
        'tickets': tickets,
        'category_choices': Ticket.CATEGORY_CHOICES,
        'priority_choices': Ticket.PRIORITY_CHOICES,
        'status_choices': Ticket.STATUS_CHOICES,
    }
    return render(request, 'tickets/ticket_list.html', context)

@login_required
def ticket_create(request):
    if request.method == 'POST':
        form = TicketForm(request.POST)
        if form.is_valid():
            ticket = form.save()
            messages.success(request, f'Ticket "{ticket.title}" created.')
            return redirect('ticket_detail', pk=ticket.pk)
    else:
        form = TicketForm()
    return render(request, 'tickets/ticket_form.html', {'form': form})

@login_required
def ticket_edit(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    if request.method == 'POST':
        form = TicketForm(request.POST, instance=ticket)
        if form.is_valid():
            form.save()
            messages.success(request, f'Ticket "{ticket.title}" updated.')
            return redirect('ticket_detail', pk=ticket.pk)
    else:
        form = TicketForm(instance=ticket)
    return render(request, 'tickets/ticket_form.html', {'form': form, 'ticket': ticket})

@login_required
def ticket_detail(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    return render(request, 'tickets/ticket_detail.html', {'ticket': ticket})

@login_required
def assigned_tickets(request):
    tickets = Ticket.objects.filter(assigned_to=request.user).order_by('-created_at')
    context = {
        'tickets': tickets,
    }
    return render(request, 'tickets/assigned_tickets.html', context)

@login_required
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
