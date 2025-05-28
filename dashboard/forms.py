from django import forms
from .models import Customer
from .models import PotentialCustomer
from django.contrib.auth.models import User, Group
from .models import Meeting
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = '__all__'

class PotentialCustomerForm(forms.ModelForm):
    class Meta:
        model = PotentialCustomer
        exclude = [
            'potential_customer_status',
            'assigned_agent',
            'potential_customer_is_dead',
            'potential_customer_converted',
            'potential_customer_converted_at',
            'converted_customer_id'
        ]

class PotentialCustomerStatusForm(forms.ModelForm):
    class Meta:
        model = PotentialCustomer
        fields = ['potential_customer_status', 'assigned_agent']


User = get_user_model()

class MeetingForm(forms.ModelForm):
    # only shown to non-superusers
    customer = forms.ModelChoiceField(
        queryset=Customer.objects.all(),
        required=False,
        label="Existing Customer"
    )
    lead = forms.ModelChoiceField(
        queryset=PotentialCustomer.objects.all(),
        required=False,
        label="Existing Lead"
    )
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        required=True,
        label="Departments",
        help_text="(superuser only)"
    )

    class Meta:
        model = Meeting
        fields = [
            "title",
            "location",
            "start_datetime",
            "end_datetime",
            "agenda",
            "summary",
            "customer",  # for agents
            "lead",      # for agents
            "groups",    # for superusers
            "participants",
            "published",
        ]
        widgets = {
            "start_datetime": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "end_datetime":   forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

        # Superusers never see the 1:1 fields
        if user and user.is_superuser:
            for f in ("customer", "lead"):
                self.fields.pop(f, None)

        # Non-superusers only get 1:1 fields
        if user and not user.is_superuser:
            keep = {"title", "location", "start_datetime", "end_datetime", "agenda", "summary", "customer", "lead"}
            for name in list(self.fields):
                if name not in keep:
                    self.fields.pop(name)

        # Participants dropdown is only for superusers
        if "participants" in self.fields:
            self.fields["participants"].queryset = User.objects.none()
            if self.data:
                ids = self.data.getlist("participants")
                if ids:
                    self.fields["participants"].queryset = User.objects.filter(id__in=ids)
            elif self.instance.pk:
                self.initial["groups"] = self.instance.groups.all()
                self.fields["participants"].queryset = self.instance.participants.all()

class ReportForm(forms.Form):
    REPORT_CHOICES = [
        ('tickets_volume',      'Tickets Volume Over Time'),
        ('avg_resolution',      'Average Ticket Resolution Time'),
        ('pipeline_value',      'Pipeline Total Value'),
        ('pipeline_conversion', 'Pipeline Conversion Rates'),
        ('meetings_scheduled',  'Meetings Scheduled'),
        ('meetings_attendance', 'Meeting Attendance Rate'),
        ('customers_new',       'New Customers'),
    ]

    start_date  = forms.DateField(
        widget=forms.DateInput(attrs={'type':'date'}),
        label="Start Date",
        initial=timezone.now().date().replace(day=1)
    )
    end_date    = forms.DateField(
        widget=forms.DateInput(attrs={'type':'date'}),
        label="End Date",
        initial=timezone.now().date()
    )
    group       = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        required=False,
        label="Department",
        empty_label="All Departments"
    )
    agent       = forms.ModelChoiceField(
        queryset=User.objects.none(),
        required=False,
        label="Agent",
        empty_label="All Agents"
    )
    report_type = forms.ChoiceField(choices=REPORT_CHOICES, label="Report")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If a group is selected in the GET data, filter agents to that group
        gid = self.data.get('group')
        if gid:
            try:
                self.fields['agent'].queryset = User.objects.filter(groups__id=int(gid))
            except (ValueError, TypeError):
                self.fields['agent'].queryset = User.objects.none()
        else:
            # no group filter → show all agents
            self.fields['agent'].queryset = User.objects.all()