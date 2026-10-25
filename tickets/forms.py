from django import forms
from django.contrib.auth.models import User
from .models import Ticket
from .permissions import ALL_FIELDS, TECHNICIANS


class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ALL_FIELDS
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, allowed_fields=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show the fields this user's role is allowed to change
        if allowed_fields is not None:
            for name in list(self.fields):
                if name not in allowed_fields:
                    del self.fields[name]

        if 'assigned_to' in self.fields:
            self.fields['assigned_to'].queryset = User.objects.filter(groups__name=TECHNICIANS).order_by('username')

        # Apply Bootstrap styling to every field
        for field in self.fields.values():
            css_class = 'form-select' if isinstance(field.widget, forms.Select) else 'form-control'
            field.widget.attrs['class'] = css_class
