from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User, Group
from django.conf import settings

class Ticket(models.Model):
    subject = models.CharField(max_length=255)
    source_type = models.CharField(max_length=100)
    priority = models.CharField(max_length=20)
    status = models.CharField(max_length=20)
    resolution_reason = models.CharField(max_length=255, blank=True, null=True)

    assignee = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_tickets")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_tickets")
    customer = models.ForeignKey("dashboard.Customer", on_delete=models.CASCADE)
    
    originating_department = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True, blank=True, related_name="originated_tickets")
    current_department = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True, blank=True, related_name="active_tickets")

    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    resolved_date = models.DateTimeField(blank=True, null=True)

    problem_description = models.TextField(blank=True, null=True)
    case_summary = models.TextField(blank=True, null=True)
    action_plan = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'dashboard_ticket'

    def __str__(self):
        return f"Ticket #{self.id} - {self.subject}"

class TicketChange(models.Model):
    ticket      = models.ForeignKey(
                      Ticket,
                      on_delete=models.CASCADE,
                      related_name='changes'
                   )
    field       = models.CharField(max_length=64)
    old_value   = models.TextField(blank=True, null=True)
    new_value   = models.TextField(blank=True, null=True)
    user        = models.ForeignKey(
                      settings.AUTH_USER_MODEL,
                      on_delete=models.CASCADE
                   )
    changed_at  = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['changed_at']

    def __str__(self):
        return f"{self.ticket} – {self.field} @ {self.changed_at:%Y‑%m‑%d %H:%M}"

class Customer(models.Model):
    customer_name = models.CharField(max_length=100)
    customer_surname = models.CharField(max_length=100)
    customer_email = models.CharField(max_length=100)
    customer_phone = models.CharField(max_length=20)
    customer_company = models.CharField(max_length=100)
    customer_address = models.CharField(max_length=255)
    customer_joined_at = models.DateField(auto_now_add=True)
    customer_status = models.CharField(max_length=20)

    class Meta:
        db_table = 'dashboard_customer'

    def __str__(self):
        return f"{self.customer_name} {self.customer_surname}"


class PotentialCustomer(models.Model):
    STATUS_CHOICES = [
    ('not_contacted', 'Not Contacted'),
    ('emailed', 'Emailed'),
    ('contacted', 'Contacted'),
    ('in_progress', 'In Progress'),  # 👈 new one
]

    potential_customer_name = models.CharField(max_length=100)
    potential_customer_email = models.CharField(max_length=100)
    potential_customer_phone = models.CharField(max_length=20)
    potential_customer_source = models.CharField(max_length=100)
    potential_customer_submitted_at = models.DateField(auto_now_add=True)
    potential_customer_converted = models.BooleanField(default=False)
    potential_customer_converted_at = models.DateField(null=True, blank=True)
    converted_customer_id = models.IntegerField(null=True, blank=True)
    
    potential_customer_status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='not_contacted'
    )
    assigned_agent = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    potential_customer_is_dead = models.BooleanField(default=False)

    class Meta:
        db_table = 'dashboard_potential_customer'

    def __str__(self):
        return self.potential_customer_name


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f'Notification for {self.user.username}: {self.message}'

class TicketComment(models.Model):
    ticket = models.ForeignKey('Ticket', on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    parent = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies'
    )

    class Meta:
        db_table = 'dashboard_ticket_comment'
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.user.username} on Ticket {self.ticket.ticket_id}"

class ExternalEmailLog(models.Model):
    ticket = models.ForeignKey('Ticket', on_delete=models.CASCADE, related_name='emails')
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    to = models.CharField(max_length=255)
    cc = models.CharField(max_length=255, blank=True)
    subject = models.CharField(max_length=255)
    message = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'dashboard_external_email_log'
        ordering = ['-sent_at']

    def __str__(self):
        return f"Email to {self.to} from {self.sender.username} on Ticket {self.ticket.ticket_id}"

class TicketCaller(models.Model):
    ticket = models.ForeignKey('Ticket', on_delete=models.CASCADE, related_name='callers')
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=50)
    phone_type = models.CharField(max_length=50, choices=[
        ('Business', 'Business'),
        ('Home', 'Home'),
        ('Other', 'Other'),
    ])
    position = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.phone})"
    
class Pipeline(models.Model):
    name = models.CharField(max_length=100)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class PipelineStage(models.Model):
    pipeline = models.ForeignKey(Pipeline, on_delete=models.CASCADE, related_name='stages')
    name = models.CharField(max_length=100)
    order = models.PositiveIntegerField()

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.pipeline.name} - {self.name}"

class LeadPipelineEntry(models.Model):
    potential_customer = models.ForeignKey('dashboard.PotentialCustomer', on_delete=models.CASCADE)
    pipeline = models.ForeignKey(Pipeline, on_delete=models.CASCADE)
    stage = models.ForeignKey(PipelineStage, on_delete=models.SET_NULL, null=True)
    assigned_agent = models.ForeignKey(User, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)
    is_done = models.BooleanField(default=False)
    is_won = models.BooleanField(default=False)
    is_lost = models.BooleanField(default=False)
    note = models.TextField(blank=True, null=True)
    entered_stage_at = models.DateTimeField(default=timezone.now)
    done_stages = models.ManyToManyField(
        PipelineStage,
        blank=True,
        related_name='completed_entries'
    )

    def __str__(self):
        return f"{self.potential_customer} in {self.pipeline.name} - {self.stage.name}"

class Meeting(models.Model):
    title           = models.CharField(max_length=200)
    location        = models.CharField(max_length=200)
    start_datetime  = models.DateTimeField()
    end_datetime    = models.DateTimeField(
        null=True, blank=True,
        help_text="When the meeting ends"
    )
    agenda          = models.TextField(
        blank=True, help_text="Pre-meeting notes or agenda"
    )
    summary         = models.TextField(
        blank=True, help_text="Post-meeting summary (fill after)"
    )
    customer = models.ForeignKey(
        Customer, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='meetings'
    )
    lead     = models.ForeignKey(
        PotentialCustomer, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='meetings_as_lead'
    )

    created_by      = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='meetings_created'
    )
    groups          = models.ManyToManyField(
        Group,
        related_name='meetings',
        help_text="Departments whose users you can invite"
    )
    participants    = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='MeetingParticipant',
        related_name='meetings',
        blank=True,
    )
    published       = models.BooleanField(default=False)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['start_datetime']

    def __str__(self):
        return f"{self.title} @ {self.start_datetime:%Y-%m-d %H:%M}"


class MeetingParticipant(models.Model):
    RSVP_CHOICES = [
        ('yes',   'Yes'),
        ('no',    'No'),
        ('maybe', "Don't know"),
    ]

    meeting         = models.ForeignKey(
                          Meeting,
                          on_delete=models.CASCADE
                      )
    user            = models.ForeignKey(
                          settings.AUTH_USER_MODEL,
                          on_delete=models.CASCADE
                      )
    rsvp_status     = models.CharField(
                          max_length=5,
                          choices=RSVP_CHOICES,
                          default='maybe'
                      )
    responded_at    = models.DateTimeField(
                          null=True,
                          blank=True,
                          help_text="When they last updated their RSVP"
                      )
    reminder_offset = models.PositiveIntegerField(
                          null=True,
                          blank=True,
                          help_text="Minutes before meeting start to remind you"
                      )

    class Meta:
        unique_together = ('meeting', 'user')
        ordering        = ['user__username']

    def __str__(self):
        return f"{self.user.username}: {self.get_rsvp_status_display()}"
