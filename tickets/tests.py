from datetime import timedelta

from django.contrib.auth.models import Group, User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import Comment, Floor, Property, Space, SubType, Ticket
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

        self.building_a = Property.objects.create(name='Building A')
        self.a_ground = Floor.objects.create(property=self.building_a, name='Ground Floor')
        self.a_kitchen = Space.objects.create(floor=self.a_ground, name='Kitchen')
        self.a_room1 = Space.objects.create(floor=self.a_ground, name='Room 1')
        self.building_b = Property.objects.create(name='Building B')
        self.b_first = Floor.objects.create(property=self.building_b, name='1st Floor')
        self.b_office = Space.objects.create(floor=self.b_first, name='Office')

        # Sub types are created by a data migration
        self.no_cooling = SubType.objects.get(category='hvac', name='No cooling')
        self.leak = SubType.objects.get(category='plumbing', name='Leak')

        self.hvac = self.make_ticket(
            title='AC broken', description='Too hot', space=self.a_room1,
            category='hvac', sub_type=self.no_cooling, priority=4,
            assigned_to=self.tech, created_by=self.staff,
        )
        self.plumbing = self.make_ticket(
            title='Leaking tap', description='Drip', space=self.b_office,
            category='plumbing', sub_type=self.leak, priority=1,
            assigned_to=self.other_tech, created_by=self.manager,
        )

    def make_ticket(self, space=None, **fields):
        space = space or self.a_kitchen
        fields.setdefault('description', 'x')
        return Ticket.objects.create(property=space.floor.property, floor=space.floor, space=space, **fields)

    def ticket_data(self, **overrides):
        data = {
            'title': 'AC broken', 'description': 'Too hot',
            'property': self.building_a.pk, 'floor': self.a_ground.pk, 'space': self.a_room1.pk,
            'category': 'hvac', 'sub_type': self.no_cooling.pk, 'priority': 4, 'status': 'open',
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

    def test_list_filters_by_property(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse('ticket_list'), {'property': self.building_b.pk})
        self.assertContains(response, 'Leaking tap')
        self.assertNotContains(response, 'AC broken')

    def test_create_ticket_records_creator(self):
        self.client.force_login(self.staff)
        response = self.client.post(reverse('ticket_create'), self.ticket_data(title='New light'))
        ticket = Ticket.objects.get(title='New light')
        self.assertRedirects(response, reverse('ticket_detail', args=[ticket.pk]))
        self.assertEqual(ticket.created_by, self.staff)
        self.assertEqual(ticket.space, self.a_room1)

    def test_create_ticket_invalid_shows_form(self):
        self.client.force_login(self.staff)
        response = self.client.post(reverse('ticket_create'), {'title': ''})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Ticket.objects.filter(title='').exists())

    def test_property_is_required(self):
        self.client.force_login(self.staff)
        response = self.client.post(reverse('ticket_create'), self.ticket_data(title='Nowhere', property='', floor='', space=''))
        self.assertTrue(response.context['form'].errors['property'])
        self.assertFalse(Ticket.objects.filter(title='Nowhere').exists())

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


class LocationAndSubTypeTests(TicketTestCase):
    def post_new(self, **overrides):
        self.client.force_login(self.manager)
        return self.client.post(reverse('ticket_create'), self.ticket_data(title='Check', **overrides))

    def test_floor_must_belong_to_property(self):
        response = self.post_new(floor=self.b_first.pk, space='')
        self.assertIn('floor', response.context['form'].errors)

    def test_space_must_be_on_floor(self):
        response = self.post_new(space=self.b_office.pk)
        self.assertIn('space', response.context['form'].errors)

    def test_space_needs_a_floor(self):
        response = self.post_new(floor='')
        self.assertIn('space', response.context['form'].errors)

    def test_sub_type_must_match_category(self):
        response = self.post_new(category='hvac', sub_type=self.leak.pk)
        self.assertIn('sub_type', response.context['form'].errors)

    def test_floor_and_space_are_optional(self):
        self.post_new(floor='', space='')
        self.assertEqual(Ticket.objects.get(title='Check').location_display, 'Building A')

    def test_options_are_tagged_for_chained_dropdowns(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse('ticket_create'))
        self.assertContains(response, f'value="{self.a_ground.pk}" data-parent="{self.building_a.pk}"')
        self.assertContains(response, f'value="{self.no_cooling.pk}" data-parent="hvac"')

    def test_location_display(self):
        self.assertEqual(self.hvac.location_display, 'Building A / Ground Floor / Room 1')


class SlaTests(TicketTestCase):
    def test_deadline_set_from_priority(self):
        ticket = self.make_ticket(title='Urgent', priority=4)
        self.assertAlmostEqual(ticket.complete_by, ticket.created_at + timedelta(hours=4), delta=timedelta(minutes=1))
        low = self.make_ticket(title='Low', priority=1)
        self.assertAlmostEqual(low.complete_by, low.created_at + timedelta(days=7), delta=timedelta(minutes=1))

    def test_priority_change_moves_deadline(self):
        self.client.force_login(self.manager)
        self.client.post(reverse('ticket_edit', args=[self.plumbing.pk]), self.ticket_data(
            title='Leaking tap', property=self.building_b.pk, floor=self.b_first.pk, space=self.b_office.pk,
            category='plumbing', sub_type=self.leak.pk, priority=4,
        ))
        self.plumbing.refresh_from_db()
        self.assertAlmostEqual(self.plumbing.complete_by, self.plumbing.created_at + timedelta(hours=4), delta=timedelta(minutes=1))

    def test_manager_can_override_deadline(self):
        due = (timezone.now() + timedelta(days=30)).replace(second=0, microsecond=0)
        self.client.force_login(self.manager)
        self.client.post(reverse('ticket_edit', args=[self.hvac.pk]), self.ticket_data(
            priority=1, complete_by=due.strftime('%Y-%m-%dT%H:%M'),
        ))
        self.hvac.refresh_from_db()
        self.assertEqual(self.hvac.complete_by, due)

    def test_untouched_deadline_is_kept_on_save(self):
        original = self.hvac.complete_by
        self.client.force_login(self.manager)
        form_page = self.client.get(reverse('ticket_edit', args=[self.hvac.pk]))
        rendered = form_page.context['form']['complete_by'].value()
        self.client.post(reverse('ticket_edit', args=[self.hvac.pk]), self.ticket_data(
            description='Updated', complete_by=rendered.strftime('%Y-%m-%dT%H:%M'),
        ))
        self.hvac.refresh_from_db()
        self.assertEqual(self.hvac.description, 'Updated')
        self.assertEqual(self.hvac.complete_by, original)

    def test_overdue(self):
        Ticket.objects.filter(pk=self.hvac.pk).update(complete_by=timezone.now() - timedelta(hours=1))
        self.hvac.refresh_from_db()
        self.assertTrue(self.hvac.is_overdue)
        self.hvac.status = 'resolved'
        self.assertFalse(self.hvac.is_overdue)  # finished tickets are never overdue

    def test_overdue_filter(self):
        Ticket.objects.filter(pk=self.hvac.pk).update(complete_by=timezone.now() - timedelta(hours=1))
        self.client.force_login(self.manager)
        response = self.client.get(reverse('ticket_list'), {'overdue': '1'})
        self.assertContains(response, 'AC broken')
        self.assertNotContains(response, 'Leaking tap')

    def test_response_time_recorded_once(self):
        self.assertIsNone(self.hvac.responded_at)
        self.hvac.status = 'in_progress'
        self.hvac.save()
        first_response = self.hvac.responded_at
        self.assertIsNotNone(first_response)
        self.hvac.status = 'resolved'
        self.hvac.save()
        self.assertEqual(self.hvac.responded_at, first_response)

    def test_staff_cannot_set_deadline_or_cost(self):
        self.client.force_login(self.staff)
        self.client.post(reverse('ticket_create'), self.ticket_data(
            title='Sneaky', complete_by='2099-01-01T00:00', cost_limit='99999',
        ))
        ticket = Ticket.objects.get(title='Sneaky')
        self.assertIsNone(ticket.cost_limit)
        self.assertLess(ticket.complete_by, timezone.now() + timedelta(days=1))


class CommentTests(TicketTestCase):
    def test_visible_user_can_comment(self):
        self.client.force_login(self.tech)
        response = self.client.post(reverse('ticket_comment', args=[self.hvac.pk]), {'body': 'On my way'})
        self.assertRedirects(response, reverse('ticket_detail', args=[self.hvac.pk]))
        comment = Comment.objects.get(ticket=self.hvac)
        self.assertEqual((comment.author, comment.body), (self.tech, 'On my way'))

    def test_comments_shown_on_ticket(self):
        Comment.objects.create(ticket=self.hvac, author=self.tech, body='Parts ordered')
        self.client.force_login(self.staff)
        self.assertContains(self.client.get(reverse('ticket_detail', args=[self.hvac.pk])), 'Parts ordered')

    def test_cannot_comment_on_hidden_ticket(self):
        self.client.force_login(self.staff)
        response = self.client.post(reverse('ticket_comment', args=[self.plumbing.pk]), {'body': 'Hi'})
        self.assertEqual(response.status_code, 404)
        self.assertFalse(Comment.objects.exists())

    def test_empty_comment_rejected(self):
        self.client.force_login(self.staff)
        self.client.post(reverse('ticket_comment', args=[self.hvac.pk]), {'body': '   '})
        self.assertFalse(Comment.objects.exists())

    def test_comment_requires_post(self):
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(reverse('ticket_comment', args=[self.hvac.pk])).status_code, 405)


class VisibilityTests(TicketTestCase):
    def listed_titles(self, user):
        self.client.force_login(user)
        return {t.title for t in self.client.get(reverse('ticket_list')).context['page_obj']}

    def test_manager_sees_all_tickets(self):
        self.assertEqual(self.listed_titles(self.manager), {'AC broken', 'Leaking tap'})

    def test_staff_sees_only_tickets_they_reported(self):
        self.assertEqual(self.listed_titles(self.staff), {'AC broken'})

    def test_technician_sees_assigned_and_reported_tickets(self):
        self.make_ticket(title='Tech report', created_by=self.tech)
        self.make_ticket(title='Unrelated', created_by=self.manager)
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
            self.ticket_data(status='resolved', assigned_to=self.other_tech.pk, cost_limit='350'),
        )
        self.assertRedirects(response, reverse('ticket_detail', args=[self.hvac.pk]))
        self.hvac.refresh_from_db()
        self.assertEqual(self.hvac.status, 'resolved')
        self.assertEqual(self.hvac.assigned_to, self.other_tech)
        self.assertEqual(str(self.hvac.cost_limit), '350.00')

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
        ticket = self.make_ticket(
            title='Tech report', status='in_progress', created_by=self.tech, assigned_to=self.other_tech,
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
            Ticket(title=f'Bulk {i}', description='x', property=self.building_a, category='other')
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
        # session + user + groups (once, cached) + count + tickets joined with
        # assignee/location/sub type + properties for the filter dropdown
        with self.assertNumQueries(6):
            self.client.get(reverse('ticket_list'))
