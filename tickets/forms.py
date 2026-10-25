from django import forms
from django.contrib.auth.models import User
from .models import Comment, Ticket
from .permissions import ALL_FIELDS, TECHNICIANS


class ChainedSelect(forms.Select):
    """A select whose options are tagged with their parent's value (data-parent),
    so the page script can show only the options that match the parent field.
    e.g. the Floor list only shows floors of the chosen Property."""

    def __init__(self, parent_field, parent_attr, attrs=None):
        self.parent_attr = parent_attr
        attrs = {'data-chained-to': parent_field, **(attrs or {})}
        super().__init__(attrs)

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        instance = getattr(value, 'instance', None)
        if instance is not None:
            option['attrs']['data-parent'] = str(getattr(instance, self.parent_attr))
        return option


# Form layout: sections in order, with each field's Bootstrap column width (out of 12)
FORM_SECTIONS = [
    ('Issue', {'title': 12, 'description': 12}),
    ('Location', {'property': 4, 'floor': 4, 'space': 4}),
    ('Classification', {'category': 4, 'sub_type': 4, 'priority': 4}),
    ('Work order', {'assigned_to': 6, 'status': 6, 'complete_by': 6, 'cost_limit': 6}),
]


class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ALL_FIELDS
        labels = {
            'category': 'Type',
            'sub_type': 'Sub type',
            'complete_by': 'Complete by',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'floor': ChainedSelect('property', 'property_id'),
            'space': ChainedSelect('floor', 'floor_id'),
            'sub_type': ChainedSelect('category', 'category'),
            'complete_by': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'cost_limit': forms.NumberInput(attrs={'min': 0, 'step': '0.01', 'placeholder': 'No limit'}),
        }

    def __init__(self, *args, allowed_fields=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show the fields this user's role is allowed to change
        if allowed_fields is not None:
            for name in list(self.fields):
                if name not in allowed_fields:
                    del self.fields[name]

        if 'property' in self.fields:
            self.fields['property'].required = True
        if 'assigned_to' in self.fields:
            self.fields['assigned_to'].queryset = User.objects.filter(groups__name=TECHNICIANS).order_by('username')
        if 'complete_by' in self.fields:
            self.fields['complete_by'].help_text = 'Leave blank to use the SLA for the priority.'
            # The input works in whole minutes; drop seconds so an untouched value doesn't count as changed
            if self.instance.complete_by:
                self.initial['complete_by'] = self.instance.complete_by.replace(second=0, microsecond=0)

        # Apply Bootstrap styling to every field
        for field in self.fields.values():
            css_class = 'form-select' if isinstance(field.widget, forms.Select) else 'form-control'
            field.widget.attrs['class'] = css_class

        # Layout: column width per field, and a heading above the first field shown in each section
        for section, widths in FORM_SECTIONS:
            present = [name for name in widths if name in self.fields]
            for name in present:
                self.fields[name].col = widths[name]
                self.fields[name].section = section if name == present[0] else None

    def save(self, commit=True):
        ticket = super().save(commit=False)
        # A priority change moves the deadline, unless the manager set one by hand
        if self.instance.pk and 'priority' in self.changed_data and 'complete_by' not in self.changed_data:
            ticket.complete_by = ticket.sla_deadline()
        if commit:
            ticket.save()
        return ticket


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['body']
        labels = {'body': ''}
        widgets = {
            'body': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Add a comment…'}),
        }
