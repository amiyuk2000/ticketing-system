from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Ticket


class TicketViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='pass12345')
        self.other = User.objects.create_user(username='bob', password='pass12345')
        self.hvac = Ticket.objects.create(
            title='AC broken', description='Too hot', location='Room 1',
            category='hvac', priority=4, assigned_to=self.user,
        )
        self.plumbing = Ticket.objects.create(
            title='Leaking tap', description='Drip', location='Kitchen',
            category='plumbing', priority=1, assigned_to=self.other,
        )

    def test_pages_require_login(self):
        response = self.client.get(reverse('ticket_list'))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('ticket_list')}")

    def test_list_filters_by_category(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('ticket_list'), {'category': 'hvac'})
        self.assertContains(response, 'AC broken')
        self.assertNotContains(response, 'Leaking tap')

    def test_list_filters_by_location(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('ticket_list'), {'location': 'kitch'})
        self.assertContains(response, 'Leaking tap')
        self.assertNotContains(response, 'AC broken')

    def test_create_ticket(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('ticket_create'), {
            'title': 'New light', 'description': 'Bulb out', 'location': 'Hall',
            'category': 'electrical', 'priority': 2, 'status': 'open',
        })
        ticket = Ticket.objects.get(title='New light')
        self.assertRedirects(response, reverse('ticket_detail', args=[ticket.pk]))

    def test_create_ticket_invalid_shows_form(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('ticket_create'), {'title': ''})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Ticket.objects.filter(title='').exists())

    def test_detail_404_for_missing_ticket(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('ticket_detail', args=[9999]))
        self.assertEqual(response.status_code, 404)

    def test_assigned_tickets_only_shows_own(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('assigned_tickets'))
        self.assertContains(response, 'AC broken')
        self.assertNotContains(response, 'Leaking tap')

    def test_counts_by_category(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('ticket_counts_by_category'))
        counts = {row['category']: row['count'] for row in response.context['ticket_counts']}
        self.assertEqual(counts, {'hvac': 1, 'plumbing': 1})
