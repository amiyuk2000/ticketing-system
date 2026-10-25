from django.contrib.auth.models import Group, User
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Ticket
from .permissions import MANAGERS, TECHNICIANS


# A fast (insecure) hasher keeps user creation quick in tests
@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class TicketTestCase(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user(username='mia', password='pass12345')
        self.manager.groups.add(Group.objects.get(name=MANAGERS))
        self.tech = User.objects.create_user(username='tom', password='pass12345')
        self.tech.groups.add(Group.objects.get(name=TECHNICIANS))
        self.other_tech = User.objects.create_user(username='tina', password='pass12345')
        self.other_tech.groups.add(Group.objects.get(name=TECHNICIANS))
        self.staff = User.objects.create_user(username='sam', password='pass12345')

        self.hvac = Ticket.objects.create(
            title='AC broken', description='Too hot', location='Room 1',
            category='hvac', priority=4, assigned_to=self.tech, created_by=self.staff,
        )
        self.plumbing = Ticket.objects.create(
            title='Leaking tap', description='Drip', location='Kitchen',
            category='plumbing', priority=1, assigned_to=self.other_tech, created_by=self.manager,
        )

    def ticket_data(self, **overrides):
        data = {
            'title': 'AC broken', 'description': 'Too hot', 'location': 'Room 1',
            'category': 'hvac', 'priority': 4, 'status': 'open',
        }
        data.update(overrides)
        return data


class TicketViewTests(TicketTestCase):
    def test_pages_require_login(self):
        response = self.client.get(reverse('ticket_list'))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('ticket_list')}")

    def test_list_filters_by_category(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse('ticket_list'), {'category': 'hvac'})
        self.assertContains(response, 'AC broken')
        self.assertNotContains(response, 'Leaking tap')

    def test_list_filters_by_location(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse('ticket_list'), {'location': 'kitch'})
        self.assertContains(response, 'Leaking tap')
        self.assertNotContains(response, 'AC broken')

    def test_create_ticket_records_creator(self):
        self.client.force_login(self.staff)
        response = self.client.post(reverse('ticket_create'), self.ticket_data(title='New light'))
        ticket = Ticket.objects.get(title='New light')
        self.assertRedirects(response, reverse('ticket_detail', args=[ticket.pk]))
        self.assertEqual(ticket.created_by, self.staff)

    def test_create_ticket_invalid_shows_form(self):
        self.client.force_login(self.staff)
        response = self.client.post(reverse('ticket_create'), {'title': ''})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Ticket.objects.filter(title='').exists())

    def test_detail_404_for_missing_ticket(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse('ticket_detail', args=[9999]))
        self.assertEqual(response.status_code, 404)

    def test_assigned_tickets_only_shows_own(self):
        self.client.force_login(self.tech)
        response = self.client.get(reverse('assigned_tickets'))
        self.assertContains(response, 'AC broken')
        self.assertNotContains(response, 'Leaking tap')

    def test_counts_by_category(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse('ticket_counts_by_category'))
        counts = {row['category']: row['count'] for row in response.context['ticket_counts']}
        self.assertEqual(counts, {'hvac': 1, 'plumbing': 1})


class VisibilityTests(TicketTestCase):
    def listed_titles(self, user):
        self.client.force_login(user)
        return {t.title for t in self.client.get(reverse('ticket_list')).context['page_obj']}

    def test_manager_sees_all_tickets(self):
        self.assertEqual(self.listed_titles(self.manager), {'AC broken', 'Leaking tap'})

    def test_staff_sees_only_tickets_they_reported(self):
        self.assertEqual(self.listed_titles(self.staff), {'AC broken'})

    def test_technician_sees_assigned_and_reported_tickets(self):
        Ticket.objects.create(title='Tech report', description='x', location='Hall', created_by=self.tech)
        Ticket.objects.create(title='Unrelated', description='x', location='Hall', created_by=self.manager)
        self.assertEqual(self.listed_titles(self.tech), {'AC broken', 'Tech report'})

    def test_hidden_ticket_detail_returns_404(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse('ticket_detail', args=[self.plumbing.pk]))
        self.assertEqual(response.status_code, 404)

    def test_hidden_ticket_edit_returns_404(self):
        self.client.force_login(self.tech)
        response = self.client.get(reverse('ticket_edit', args=[self.plumbing.pk]))
        self.assertEqual(response.status_code, 404)

    def test_heading_reflects_scope(self):
        self.client.force_login(self.staff)
        self.assertContains(self.client.get(reverse('ticket_list')), 'My Tickets')
        self.client.force_login(self.manager)
        self.assertContains(self.client.get(reverse('ticket_list')), 'All Tickets')


class PermissionTests(TicketTestCase):
    def test_manager_can_edit_and_assign_any_ticket(self):
        self.client.force_login(self.manager)
        response = self.client.post(
            reverse('ticket_edit', args=[self.hvac.pk]),
            self.ticket_data(status='resolved', assigned_to=self.other_tech.pk),
        )
        self.assertRedirects(response, reverse('ticket_detail', args=[self.hvac.pk]))
        self.hvac.refresh_from_db()
        self.assertEqual(self.hvac.status, 'resolved')
        self.assertEqual(self.hvac.assigned_to, self.other_tech)

    def test_technician_can_only_change_status_of_assigned_ticket(self):
        self.client.force_login(self.tech)
        self.client.post(
            reverse('ticket_edit', args=[self.hvac.pk]),
            self.ticket_data(title='Hacked title', priority=1, status='in_progress'),
        )
        self.hvac.refresh_from_db()
        self.assertEqual(self.hvac.status, 'in_progress')
        self.assertEqual(self.hvac.title, 'AC broken')  # other fields ignored
        self.assertEqual(self.hvac.priority, 4)

    def test_technician_cannot_edit_ticket_they_reported_once_assigned_elsewhere(self):
        # Visible to them (they reported it) but not editable: in progress, and not theirs to work on
        ticket = Ticket.objects.create(
            title='Tech report', description='x', location='Hall', status='in_progress',
            created_by=self.tech, assigned_to=self.other_tech,
        )
        self.client.force_login(self.tech)
        response = self.client.get(reverse('ticket_edit', args=[ticket.pk]))
        self.assertEqual(response.status_code, 403)

    def test_staff_can_edit_own_open_ticket_but_not_status(self):
        self.client.force_login(self.staff)
        self.client.post(
            reverse('ticket_edit', args=[self.hvac.pk]),
            self.ticket_data(description='Even hotter now', status='closed'),
        )
        self.hvac.refresh_from_db()
        self.assertEqual(self.hvac.description, 'Even hotter now')
        self.assertEqual(self.hvac.status, 'open')

    def test_staff_cannot_edit_own_ticket_once_in_progress(self):
        self.hvac.status = 'in_progress'
        self.hvac.save()
        self.client.force_login(self.staff)
        response = self.client.get(reverse('ticket_edit', args=[self.hvac.pk]))
        self.assertEqual(response.status_code, 403)

    def test_staff_cannot_edit_others_ticket(self):
        self.client.force_login(self.staff)
        response = self.client.post(reverse('ticket_edit', args=[self.plumbing.pk]), self.ticket_data())
        self.assertEqual(response.status_code, 404)
        self.plumbing.refresh_from_db()
        self.assertEqual(self.plumbing.title, 'Leaking tap')

    def test_staff_cannot_assign_or_set_status_on_create(self):
        self.client.force_login(self.staff)
        self.client.post(
            reverse('ticket_create'),
            self.ticket_data(title='Sneaky', status='closed', assigned_to=self.tech.pk),
        )
        ticket = Ticket.objects.get(title='Sneaky')
        self.assertEqual(ticket.status, 'open')
        self.assertIsNone(ticket.assigned_to)

    def test_reports_are_manager_only(self):
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(reverse('ticket_counts_by_category')).status_code, 403)
        self.client.force_login(self.tech)
        self.assertEqual(self.client.get(reverse('ticket_counts_by_category')).status_code, 403)

    def test_edit_button_hidden_without_permission(self):
        self.hvac.status = 'in_progress'
        self.hvac.save()
        self.client.force_login(self.staff)
        response = self.client.get(reverse('ticket_detail', args=[self.hvac.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, reverse('ticket_edit', args=[self.hvac.pk]))

    def test_assignee_choices_limited_to_technicians(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse('ticket_create'))
        assignees = set(response.context['form'].fields['assigned_to'].queryset)
        self.assertEqual(assignees, {self.tech, self.other_tech})


class PaginationTests(TicketTestCase):
    def setUp(self):
        super().setUp()
        Ticket.objects.bulk_create([
            Ticket(title=f'Bulk {i}', description='x', location='Hall', category='other')
            for i in range(23)
        ])  # 25 tickets in total

    def test_list_is_paginated(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse('ticket_list'))
        self.assertEqual(len(response.context['page_obj']), 10)
        self.assertEqual(response.context['page_obj'].paginator.num_pages, 3)

    def test_last_page_and_out_of_range(self):
        self.client.force_login(self.manager)
        self.assertEqual(len(self.client.get(reverse('ticket_list'), {'page': 3}).context['page_obj']), 5)
        # An invalid page number falls back to the last page instead of erroring
        self.assertEqual(self.client.get(reverse('ticket_list'), {'page': 99}).context['page_obj'].number, 3)

    def test_page_links_keep_filters(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse('ticket_list'), {'category': 'other'})
        self.assertContains(response, '?category=other&amp;page=2')

    def test_list_query_count_does_not_grow_with_rows(self):
        self.client.force_login(self.manager)
        # session + user + groups (once, cached) + count + tickets with assignees in one join
        with self.assertNumQueries(5):
            self.client.get(reverse('ticket_list'))
