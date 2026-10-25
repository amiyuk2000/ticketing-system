import builtins
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

CATEGORY_CHOICES = [
    ('electrical', 'Electrical'),
    ('plumbing', 'Plumbing'),
    ('hvac', 'HVAC'),
    ('cleaning', 'Cleaning'),
    ('other', 'Other'),
]


class Property(models.Model):
    """A building or site, e.g. "Building A"."""
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'properties'

    def __str__(self):
        return self.name


class Floor(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='floors')
    name = models.CharField(max_length=50)

    class Meta:
        ordering = ['property__name', 'name']
        constraints = [models.UniqueConstraint(fields=['property', 'name'], name='unique_floor_per_property')]

    def __str__(self):
        return self.name


class Space(models.Model):
    """A room or area on a floor, e.g. "Room 2.04" or "Kitchen"."""
    floor = models.ForeignKey(Floor, on_delete=models.CASCADE, related_name='spaces')
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ['floor__property__name', 'floor__name', 'name']
        constraints = [models.UniqueConstraint(fields=['floor', 'name'], name='unique_space_per_floor')]

    def __str__(self):
        return self.name


class SubType(models.Model):
    """A more specific kind of issue within a category, e.g. Electrical → Burnt bulb."""
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ['category', 'name']
        constraints = [models.UniqueConstraint(fields=['category', 'name'], name='unique_subtype_per_category')]

    def __str__(self):
        return self.name


class Ticket(models.Model):
    CATEGORY_CHOICES = CATEGORY_CHOICES

    PRIORITY_CHOICES = [
        (1, 'Low'),
        (2, 'Medium'),
        (3, 'High'),
        (4, 'Urgent'),
    ]

    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]

    ACTIVE_STATUSES = ['open', 'in_progress']

    # Service level agreement: hours allowed to complete a ticket, by priority
    SLA_HOURS = {4: 4, 3: 24, 2: 72, 1: 168}

    title = models.CharField(max_length=200)
    description = models.TextField()
    property = models.ForeignKey(Property, on_delete=models.PROTECT, null=True, related_name='tickets')
    floor = models.ForeignKey(Floor, on_delete=models.PROTECT, null=True, blank=True, related_name='tickets')
    space = models.ForeignKey(Space, on_delete=models.PROTECT, null=True, blank=True, related_name='tickets')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')
    sub_type = models.ForeignKey(SubType, on_delete=models.PROTECT, null=True, blank=True, related_name='tickets')
    priority = models.IntegerField(choices=PRIORITY_CHOICES, default=2)
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_tickets', editable=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    complete_by = models.DateTimeField(null=True, blank=True, help_text='Defaults to the SLA for the priority.')
    responded_at = models.DateTimeField(null=True, blank=True, editable=False)
    cost_limit = models.DecimalField('Do not exceed amount', max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    # The `property` field above shadows Python's built-in inside this class,
    # so computed properties below use @builtins.property

    def clean(self):
        errors = {}
        if self.floor and self.property and self.floor.property_id != self.property_id:
            errors['floor'] = 'This floor is not in the selected property.'
        if self.space and not self.floor:
            errors['space'] = 'Choose a floor before choosing a space.'
        elif self.space and self.space.floor_id != self.floor_id:
            errors['space'] = 'This space is not on the selected floor.'
        if self.sub_type and self.sub_type.category != self.category:
            errors['sub_type'] = 'This sub type does not belong to the selected category.'
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.complete_by is None:
            self.complete_by = self.sla_deadline()
        # The first time a ticket leaves "open" counts as the first response
        if self.status != 'open' and self.responded_at is None:
            self.responded_at = timezone.now()
        super().save(*args, **kwargs)

    def sla_deadline(self):
        start = self.created_at or timezone.now()
        deadline = start + timedelta(hours=self.SLA_HOURS.get(self.priority, 72))
        return deadline.replace(second=0, microsecond=0)

    @builtins.property
    def is_overdue(self):
        return (
            self.status in self.ACTIVE_STATUSES
            and self.complete_by is not None
            and self.complete_by < timezone.now()
        )

    @builtins.property
    def response_time(self):
        if self.responded_at:
            return self.responded_at - self.created_at
        return None

    @builtins.property
    def location_display(self):
        return ' / '.join(str(part) for part in (self.property, self.floor, self.space) if part)


class Comment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    body = models.TextField('Comment')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'Comment by {self.author} on {self.ticket}'
