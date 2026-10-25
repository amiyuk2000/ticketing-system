from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from .models import Ticket
from .forms import TicketForm

@login_required
def ticket_list(request):
    tickets = Ticket.objects.all()

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
            return redirect('ticket_detail', pk=ticket.pk)
    else:
        form = TicketForm()
    return render(request, 'tickets/ticket_form.html', {'form': form})

@login_required
def ticket_detail(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    return render(request, 'tickets/ticket_detail.html', {'ticket': ticket})

@login_required
def assigned_tickets(request):
    tickets = Ticket.objects.filter(assigned_to=request.user)
    context = {
        'tickets': tickets,
    }
    return render(request, 'tickets/assigned_tickets.html', context)

@login_required
def ticket_counts_by_category(request):
    ticket_counts = Ticket.objects.values('category').annotate(count=Count('category'))
    context = {
        'ticket_counts': ticket_counts,
    }
    return render(request, 'tickets/ticket_counts_by_category.html', context)
