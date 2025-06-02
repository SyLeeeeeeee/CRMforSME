from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from django.urls import reverse
from django.utils.http import urlencode
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from django.http import HttpResponseRedirect
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponseForbidden, HttpResponseNotAllowed
import json
from django.views.decorators.http import require_POST
from django.db.models import Max
from django.db.models import Exists, OuterRef
from django.db.models import Prefetch
from django.contrib.auth.decorators import user_passes_test
import datetime
from datetime import timedelta, timezone as dt_timezone
from urllib.parse import quote
import pytz
from django.db.models import Count, Avg, Sum, F, ExpressionWrapper, DurationField
from django.db.models.functions import TruncDate
from .forms import ReportForm

from .models import (
    Ticket,
    Customer,
    TicketComment,
    ExternalEmailLog,
    PotentialCustomer,
    Notification,
    TicketCaller,
    TicketChange,
    Pipeline,
    PipelineStage,
    LeadPipelineEntry,
    Meeting,
    MeetingParticipant,
)
from .forms import PotentialCustomerForm, PotentialCustomerStatusForm, MeetingForm

from django.contrib.auth.models import User, Group

# Dashboard home
@login_required
def dashboard_view(request):
    return render(request, 'accounts/dashboard.html')

@login_required
def ticket_list(request):
    # Get all GET parameters
    query = request.GET.get('q', '')
    search_by = request.GET.get('search_by', 'ticket_id')
    status = request.GET.get('status', '')
    priority = request.GET.get('priority', '')
    assignee = request.GET.get('assignee', '')
    sort_created = request.GET.get('created_sort', '')
    sort_updated = request.GET.get('sort_updated', '')

    # Start with all tickets
    tickets = Ticket.objects.all()

    # Search by selected field
    if query:
        if search_by == 'ticket_id':
            if query.isdigit():
                tickets = tickets.filter(id=int(query))
        elif search_by == 'customer_name':
            tickets = tickets.filter(customer__customer_name__istartswith=query)
        elif search_by == 'customer_email':
            tickets = tickets.filter(customer__customer_email__istartswith=query)
        elif search_by == 'customer_phone':
            tickets = tickets.filter(customer__customer_phone__istartswith=query)
        elif search_by == 'customer_id':
            if query.isdigit():
                tickets = tickets.filter(customer__id=int(query))

    # Filter by status
    if status:
        tickets = tickets.filter(status=status)

    # Filter by priority
    if priority:
        tickets = tickets.filter(priority=priority)

    # Filter by assignee (including "Unassigned" logic)
    if assignee:
        if assignee == "Unassigned":
            tickets = tickets.filter(assignee__isnull=True)
        else:
            user = User.objects.filter(username=assignee).first()
            if user:
                tickets = tickets.filter(assignee=user)

    # Sort by created date
    if sort_created == 'newest':
        tickets = tickets.order_by('-created_date')
    elif sort_created == 'oldest':
        tickets = tickets.order_by('created_date')

    # Sort by last updated date
    if sort_updated == 'newest':
        tickets = tickets.order_by('-updated_date')
    elif sort_updated == 'oldest':
        tickets = tickets.order_by('updated_date')

    # Paginate results
    paginator = Paginator(tickets, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get unique assignee usernames
    assignees = (
        User.objects.filter(id__in=Ticket.objects.exclude(assignee__isnull=True)
        .values_list('assignee', flat=True))
        .order_by('username')
        .values_list('username', flat=True)
    )

    # Render template with context
    return render(request, 'accounts/ticket_list.html', {
        'page_obj': page_obj,
        'query': query,
        'search_by': search_by,
        'selected_status': status,
        'selected_priority': priority,
        'selected_assignee': assignee,
        'selected_sort_created': sort_created,
        'selected_sort_updated': sort_updated,
        'assignees': assignees,
    })

@login_required
@require_GET
def get_customer_info(request, customer_id):
    try:
        customer = Customer.objects.get(id=customer_id)
        return JsonResponse({
            'email': customer.customer_email,
            'phone': customer.customer_phone,
            'name': f"{customer.customer_name} {customer.customer_surname}"
        })
    except Customer.DoesNotExist:
        return JsonResponse({'error': 'Customer not found'}, status=404)

# Tickets - General View
@login_required
def tickets_view(request):
    tickets = Ticket.objects.all()
    return render(request, 'accounts/tickets.html', {'tickets': tickets})

@login_required
def customer_list(request):
    query = request.GET.get('q', '').strip()
    search_by = request.GET.get('search_by', 'name')
    
    customers = Customer.objects.all()

    if query:
        if search_by == 'customer_id':
            if query.isdigit():
                customers = customers.filter(id=int(query))
        elif search_by == 'name':
            customers = customers.filter(customer_name__istartswith=query)
        elif search_by == 'email':
            customers = customers.filter(customer_email__istartswith=query)
        elif search_by == 'phone':
            customers = customers.filter(customer_phone__istartswith=query)
        elif search_by == 'company':
            customers = customers.filter(customer_company__istartswith=query)

    # Default sort by customer ID
    customers = customers.order_by('id')

    # Pagination - 15 per page
    paginator = Paginator(customers, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'accounts/customers.html', {
        'customers': page_obj,
        'query': query,
        'search_by': search_by,
        'page_obj': page_obj
    })

# Customers - Add
@login_required
def customer_add(request):
    if request.method == 'POST':
        try:
            Customer.objects.create(
                customer_name=request.POST['customer_name'],
                customer_surname=request.POST['customer_surname'],
                customer_email=request.POST['customer_email'],
                customer_phone=request.POST['customer_phone'],
                customer_company=request.POST['customer_company'],
                customer_address=request.POST['customer_address'],
                customer_status=request.POST['customer_status'],
                customer_joined_at=timezone.now()
            )
            return redirect('customer_list')
        except Exception as e:
            print("Error:", e)
            return render(request, 'accounts/customer_form.html', {
                'action': 'Add',
                'error': str(e)
            })
    return render(request, 'accounts/customer_form.html', {'action': 'Add'})


# Customers - Edit
@login_required
def customer_edit(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == 'POST':
        customer.customer_name = request.POST.get('customer_name')
        customer.customer_surname = request.POST.get('customer_surname')
        customer.customer_email = request.POST.get('customer_email')
        customer.customer_phone = request.POST.get('customer_phone')
        customer.customer_company = request.POST.get('customer_company')
        customer.customer_address = request.POST.get('customer_address')
        customer.customer_status = request.POST.get('customer_status')
        customer.save()
        return redirect('customer_list')

    return render(request, 'accounts/customer_form.html', {'action': 'Edit', 'customer': customer})


# Customers - Delete
@login_required
def customer_delete(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    customer.delete()
    return redirect('customer_list')

@login_required
def add_potential_customer(request):
    if request.method == 'POST':
        PotentialCustomer.objects.create(
            potential_customer_name=request.POST['name'],
            potential_customer_email=request.POST['email'],
            potential_customer_phone=request.POST['phone'],
            potential_customer_source=request.POST['source'],
            potential_customer_submitted_at=timezone.now(),
            potential_customer_converted=False
        )
        return redirect('potential_customer_list')  # you’ll create this view next
    return render(request, 'accounts/potential_customer_form.html')

@login_required
def add_potential_customer(request):
    if request.method == 'POST':
        form = PotentialCustomerForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('potential_customer_list')  # We'll create this next
    else:
        form = PotentialCustomerForm()
    
    return render(request, 'accounts/potential_customer_form.html', {
        'form': form,
        'action': 'Add'
    })

@login_required
def potential_customer_list(request):
    query = request.GET.get('q')
    assigned_filter = request.GET.get('assigned_filter', '')

    # Base queryset
    if request.user.groups.filter(name='Sales').exists():
        leads = PotentialCustomer.objects.filter(
            assigned_agent=request.user, potential_customer_is_dead=False
        )
    else:
        leads = PotentialCustomer.objects.filter(potential_customer_is_dead=False)

    # Search filtering
    if query:
        leads = leads.filter(
            Q(potential_customer_name__icontains=query) |
            Q(potential_customer_email__icontains=query) |
            Q(potential_customer_source__icontains=query)
        )

    # Dropdown assigned/unassigned filtering (only for non-sales)
    if not request.user.groups.filter(name='Sales').exists():
        if assigned_filter == 'true':
            leads = leads.exclude(assigned_agent=None)
        elif assigned_filter == 'false':
            leads = leads.filter(assigned_agent=None)

    # Limit agent list to Sales group
    try:
        sales_group = Group.objects.get(name="Sales")
        users = User.objects.filter(groups=sales_group)
    except Group.DoesNotExist:
        users = User.objects.none()

    # Get pipelines created by this user
    pipelines = Pipeline.objects.filter(created_by=request.user)

    unread_count = request.user.notifications.filter(is_read=False).count()

    return render(request, 'accounts/potential_customers.html', {
        'leads': leads,
        'users': users,
        'unread_count': unread_count,
        'assigned_filter': assigned_filter,
        'pipelines': pipelines,
    })

@login_required
def create_ticket(request):
    if request.method == 'POST':
        subject             = request.POST.get('subject')
        problem_description = request.POST.get('problem_description')
        case_summary        = request.POST.get('case_summary')
        action_plan         = request.POST.get('action_plan')
        customer_id         = request.POST.get('customer_id')
        priority            = request.POST.get('priority')
        status              = request.POST.get('status')
        source_type         = request.POST.get('source_type')
        resolution_reason   = request.POST.get('resolution_reason')
        initial_comment     = request.POST.get('initial_comment')

        # Validate and get customer
        customer = Customer.objects.filter(id=customer_id).first()
        if not customer:
            return render(request, 'accounts/create_ticket.html', {
                'error': 'Customer ID not found.',
                'customers': Customer.objects.all().values(
                    'id', 'customer_email', 'customer_name', 'customer_surname', 'customer_phone'
                ).order_by('id'),
                'agents': User.objects.all().values_list('username', flat=True),
                'groups': Group.objects.all(),
                'created_date': timezone.now(),
                'updated_date': timezone.now(),
                'internal_comments': [],
                'external_emails': [],
                'next_ticket_id': Ticket.objects.latest('id').id + 1 if Ticket.objects.exists() else 1,
                'selected_assignee': request.POST.get('assignee', ''),
                'selected_group_id': request.POST.get('group_filter', '')
            })

        # Assignee (optional)
        assignee_username = request.POST.get('assignee')
        assignee = User.objects.filter(username=assignee_username).first() if assignee_username else None

        # Department selection
        group_id = request.POST.get('group_filter')
        current_department = Group.objects.filter(id=group_id).first() if group_id else None

        # Originating department = based on logged in user
        user_groups = request.user.groups.all()
        originating_department = user_groups.first() if user_groups.exists() else None

        # Create the ticket
        ticket = Ticket.objects.create(
            subject               = subject,
            problem_description   = problem_description,
            case_summary          = case_summary,
            action_plan           = action_plan,
            priority              = priority,
            status                = status,
            source_type           = source_type,
            resolution_reason     = resolution_reason,
            customer              = customer,
            assignee              = assignee,
            created_by            = request.user,
            originating_department= originating_department,
            current_department    = current_department,
        )

        # Build a link to the ticket
        ticket_url     = reverse('ticket_detail', args=[ticket.id])
        link_to_ticket = f"<a href='{ticket_url}'>Ticket #{ticket.id}</a>"

        # Notify the assignee in-app
        if assignee:
            Notification.objects.create(
                user    = assignee,
                message = f"{link_to_ticket}: You’ve been assigned"
            )

        # Send email notification to the customer
        if customer.customer_email:
            email_subject = f"[Support] We’ve received your ticket #{ticket.id}"
            email_body = (
                f"Hello {customer.customer_name},\n\n"
                f"Your support ticket has been created:\n"
                f"Ticket ID: {ticket.id}\n"
                f"Subject:   {ticket.subject}\n"
                f"Status:    {ticket.status}\n\n"
                "We will keep you updated as we work on it.\n\n"
                "Thank you,\nThe Support Team"
            )
            send_mail(
                email_subject,
                email_body,
                settings.DEFAULT_FROM_EMAIL,
                [customer.customer_email],
                fail_silently=False,
            )

        # Save caller list
        names     = request.POST.getlist('caller_name[]')
        emails    = request.POST.getlist('caller_email[]')
        phones    = request.POST.getlist('caller_phone[]')
        types     = request.POST.getlist('caller_phone_type[]')
        positions = request.POST.getlist('caller_position[]')

        for i in range(len(names)):
            if names[i].strip():
                TicketCaller.objects.create(
                    ticket     = ticket,
                    name       = names[i],
                    email      = emails[i] or None,
                    phone      = phones[i],
                    phone_type = types[i],
                    position   = positions[i] or None
                )

        # Save internal comment
        if initial_comment:
            TicketComment.objects.create(
                ticket  = ticket,
                user    = request.user,
                message = initial_comment
            )

        return redirect('ticket_detail', id=ticket.id)

    # GET request
    customers      = Customer.objects.all().values(
                         'id', 'customer_email',
                         'customer_name', 'customer_surname',
                         'customer_phone'
                      ).order_by('id')
    groups         = Group.objects.all()
    agents         = User.objects.all().values_list('username', flat=True)
    next_ticket_id = Ticket.objects.latest('id').id + 1 if Ticket.objects.exists() else 1

    return render(request, 'accounts/create_ticket.html', {
        'customers':         customers,
        'groups':            groups,
        'agents':            agents,
        'created_date':      timezone.now(),
        'updated_date':      timezone.now(),
        'internal_comments': [],
        'external_emails':   [],
        'next_ticket_id':    next_ticket_id,
        'selected_assignee': '',
        'selected_group_id': '',
    })

@login_required
def edit_lead_status(request, pk):
    lead = get_object_or_404(PotentialCustomer, pk=pk)

    if request.method == 'POST':
        lead.potential_customer_status = request.POST.get(
            'potential_customer_status',
            lead.potential_customer_status
        )

        new_agent_id = request.POST.get('assigned_agent')
        previous_agent = lead.assigned_agent

        if new_agent_id:
            if str(lead.assigned_agent_id) != new_agent_id:
                lead.assigned_agent_id = new_agent_id
                new_agent = User.objects.get(id=new_agent_id)
                Notification.objects.create(
                    user=new_agent,
                    message=f"You’ve been assigned a new lead: {lead.potential_customer_name}"
                )
        else:
            lead.assigned_agent = None

        lead.save()

    # Preserve assigned_filter in redirect (if present)
    redirect_url = reverse('potential_customer_list')
    assigned_filter = request.GET.get('assigned_filter')
    if assigned_filter:
        redirect_url += '?' + urlencode({'assigned_filter': assigned_filter})

    return redirect(redirect_url)


@login_required
def edit_lead_status(request, pk):
    lead = get_object_or_404(PotentialCustomer, pk=pk)

    if request.method == 'POST':
        form_type = request.POST.get('form_type')

        if form_type == 'status':
            new_status = request.POST.get('potential_customer_status')
            if new_status:
                lead.potential_customer_status = new_status

        elif form_type == 'agent':
            new_agent_id = request.POST.get('assigned_agent')
            if new_agent_id:
                if str(lead.assigned_agent_id) != new_agent_id:
                    lead.assigned_agent_id = new_agent_id
                    # Send notification
                    new_agent = User.objects.get(id=new_agent_id)
                    Notification.objects.create(
                        user=new_agent,
                        message=f"You’ve been assigned a new lead: {lead.potential_customer_name}"
                    )
            else:
                lead.assigned_agent = None

        lead.save()

    return redirect('potential_customer_list')

@csrf_exempt
def submit_lead_view(request):
    if request.method == 'POST':
        PotentialCustomer.objects.create(
            potential_customer_name=request.POST.get('name'),
            potential_customer_email=request.POST.get('email'),
            potential_customer_phone=request.POST.get('phone'),
            potential_customer_source=request.POST.get('source'),
            potential_customer_submitted_at=timezone.now(),
            potential_customer_converted=False
        )
        return redirect('thank_you')

    return render(request, 'accounts/submit_lead.html')

@login_required
def mark_lead_as_dead(request, pk):
    lead = get_object_or_404(PotentialCustomer, pk=pk)
    lead.potential_customer_is_dead = True
    lead.save()
    return redirect('potential_customer_list')

@login_required
def convert_lead_to_customer(request, pk):
    lead = get_object_or_404(PotentialCustomer, pk=pk)

    # Create a new customer with correct fields
    Customer.objects.create(
        customer_name=lead.potential_customer_name,
        customer_surname="",
        customer_email=lead.potential_customer_email,
        customer_phone=lead.potential_customer_phone,
        customer_company="",
        customer_address="",
        customer_status="Active",
        customer_joined_at=timezone.now()
    )

    # Delete the lead after converting
    lead.delete()

    return redirect('potential_customer_list')

@login_required
def mark_notification_read(request, id):
    try:
        note = Notification.objects.get(id=id, user=request.user)
        note.is_read = True
        note.save()
        return JsonResponse({"success": True})
    except Notification.DoesNotExist:
        return JsonResponse({"success": False}, status=404)

@login_required
def clear_all_notifications(request):
    request.user.notifications.all().delete()
    return JsonResponse({'status': 'ok'})

@login_required
def get_agents_by_group(request):
    group_id = request.GET.get('group_id')
    if group_id:
        try:
            group = Group.objects.get(id=group_id)
            agents = list(User.objects.filter(groups=group).values_list('username', flat=True))
            return JsonResponse({'agents': agents})
        except Group.DoesNotExist:
            return JsonResponse({'agents': []})
    return JsonResponse({'agents': []})

@login_required
def ticket_detail(request, id):
    ticket = get_object_or_404(Ticket, id=id)

    # Keep the old assignee for assignment‐change notifications
    old_assignee = ticket.assignee

    # Snapshot of “before” for change logging
    old_data = {
        "Subject":             ticket.subject,
        "Problem Description": ticket.problem_description or "",
        "Case Summary":        ticket.case_summary or "",
        "Action Plan":         ticket.action_plan or "",
        "Priority":            ticket.priority,
        "Status":              ticket.status,
        "Source Type":         ticket.source_type,
        "Resolution Reason":   ticket.resolution_reason or "",
        "Department":          ticket.current_department.name if ticket.current_department else "",
        "Assignee":            ticket.assignee.username if ticket.assignee else "",
    }

    # Form defaults
    selected_group_id = str(ticket.current_department.id) if ticket.current_department else ""
    selected_assignee = ticket.assignee.username if ticket.assignee else ""

    # Build link for notifications
    ticket_url     = reverse('ticket_detail', args=[ticket.id])
    link_to_ticket = f"<a href='{ticket_url}'>Ticket #{ticket.id}</a>"

    if request.method == 'POST':
        # Pull out free‐form fields
        content   = request.POST.get('new_internal_comment', '').strip()
        parent_id = request.POST.get('parent_comment_id')
        to_addr   = request.POST.get('email_to', '').strip()
        subj      = request.POST.get('email_subject', '').strip()
        body      = request.POST.get('email_message', '').strip()

        # Update main ticket fields
        ticket.subject             = request.POST.get('subject')
        ticket.problem_description = request.POST.get('problem_description')
        ticket.case_summary        = request.POST.get('case_summary')
        ticket.action_plan         = request.POST.get('action_plan')
        ticket.priority            = request.POST.get('priority')

        # handle status & resolved_date stamping + resolution email
        new_status = request.POST.get('status')
        # detect the moment we move into “Resolved”
        just_resolved = (
            new_status and
            new_status.lower() == 'resolved' and
            ticket.resolved_date is None
        )
        ticket.status = new_status
        if just_resolved:
            ticket.resolved_date = timezone.now()

        ticket.source_type       = request.POST.get('source_type')
        ticket.resolution_reason = request.POST.get('resolution_reason')
        ticket.updated_date      = timezone.now()

        # Department switch
        group_id = request.POST.get('group_filter')
        ticket.current_department = (
            Group.objects.filter(id=group_id).first()
            if group_id else ticket.current_department
        )
        selected_group_id = group_id or selected_group_id

        # Assignee change
        au = request.POST.get('assignee','').strip()
        ticket.assignee = User.objects.filter(username=au).first() if au else None
        selected_assignee = ticket.assignee.username if ticket.assignee else ""

        # Save ticket (with stamps)
        ticket.save()

        # Send resolution email if we just resolved it
        if just_resolved and ticket.customer and ticket.customer.customer_email:
            subject = f"[YourApp] Ticket #{ticket.id} Resolved"
            resolution = ticket.resolution_reason or "(no resolution details provided)"
            body = (
                f"Hello {ticket.customer.customer_name},\n\n"
                f"Your ticket #{ticket.id} (“{ticket.subject}”) has been marked as *Resolved*.\n\n"
                f"Resolution Details:\n{resolution}\n\n"
                "Thank you,\nThe Support Team"
            )
            send_mail(
                subject,
                body,
                settings.DEFAULT_FROM_EMAIL,
                [ticket.customer.customer_email],
                fail_silently=False,
            )

        # 4) Record field‐by‐field changes for the change log
        new_data = {
            "Subject":             ticket.subject,
            "Problem Description": ticket.problem_description or "",
            "Case Summary":        ticket.case_summary or "",
            "Action Plan":         ticket.action_plan or "",
            "Priority":            ticket.priority,
            "Status":              ticket.status,
            "Source Type":         ticket.source_type,
            "Resolution Reason":   ticket.resolution_reason or "",
            "Department":          ticket.current_department.name if ticket.current_department else "",
            "Assignee":            ticket.assignee.username if ticket.assignee else "",
        }
        for field_label, old_val in old_data.items():
            new_val = new_data[field_label]
            if str(old_val) != str(new_val):
                TicketChange.objects.create(
                    ticket    = ticket,
                    user      = request.user,
                    field     = field_label,
                    old_value = old_val,
                    new_value = new_val
                )

        # 5) Assignment notifications
        new_assignee = ticket.assignee
        if new_assignee and new_assignee != old_assignee:
            Notification.objects.create(
                user    = new_assignee,
                message = f"{link_to_ticket}: You’ve been assigned"
            )

        # If it was just a field‐only update (no comment/email),
        # ping the current assignee about “Changes were made”
        if not content and not (to_addr and subj and body):
            if ticket.assignee:
                Notification.objects.create(
                    user    = ticket.assignee,
                    message = f"{link_to_ticket}: Changes were made"
                )

        # 7) Replace callers
        TicketCaller.objects.filter(ticket=ticket).delete()
        names     = request.POST.getlist('caller_name[]')
        emails    = request.POST.getlist('caller_email[]')
        phones    = request.POST.getlist('caller_phone[]')
        types     = request.POST.getlist('caller_phone_type[]')
        positions = request.POST.getlist('caller_position[]')
        for i in range(len(names)):
            if names[i].strip():
                TicketCaller.objects.create(
                    ticket     = ticket,
                    name       = names[i],
                    email      = emails[i] or None,
                    phone      = phones[i],
                    phone_type = types[i],
                    position   = positions[i] or None
                )

        # 8) Internal comment flow
        if content:
            TicketComment.objects.create(
                ticket  = ticket,
                user    = request.user,
                message = content,
                parent  = TicketComment.objects.filter(id=parent_id).first()
                          if parent_id else None
            )
            if ticket.assignee and ticket.assignee != request.user:
                Notification.objects.create(
                    user    = ticket.assignee,
                    message = f"{link_to_ticket}: New comment posted"
                )
            return redirect(f"{ticket_url}#internal-comments-anchor")

        # 9) External email flow
        if to_addr and subj and body:
            send_mail(
                subject       = subj,
                message       = body,
                from_email    = settings.EMAIL_HOST_USER,
                recipient_list=[to_addr],
                fail_silently = False
            )
            ExternalEmailLog.objects.create(
                ticket  = ticket,
                to      = to_addr,
                cc      = request.POST.get('email_cc'),
                subject = subj,
                message = body,
                sender  = request.user,
                sent_at = timezone.now()
            )
            return redirect(f"{ticket_url}#external-email-anchor")

    # GET: prepare context for rendering
    agents           = []
    if selected_group_id:
        agents = User.objects.filter(groups__id=selected_group_id)\
                             .values_list('username', flat=True)

    groups            = Group.objects.all()
    customer          = ticket.customer
    internal_comments = TicketComment.objects.filter(ticket=ticket, parent=None)\
                                             .prefetch_related('parent')\
                                             .order_by('created_at')
    external_emails   = ExternalEmailLog.objects.filter(ticket=ticket)\
                                                .order_by('sent_at')
    changes           = ticket.changes.all()

    return render(request, 'accounts/ticket_detail.html', {
        'ticket':            ticket,
        'customer':          customer,
        'internal_comments': internal_comments,
        'external_emails':   external_emails,
        'agents':            agents,
        'groups':            groups,
        'selected_group_id': selected_group_id,
        'selected_assignee': selected_assignee,
        'changes':           changes,
    })

@login_required
def pipeline_list(request):
    def get_annotated_stages(pipeline):
        if not pipeline:
            return []

        done_subquery = LeadPipelineEntry.objects.filter(
            done_stages=OuterRef('pk')
        )

        return (pipeline.stages
                .annotate(has_done_leads=Exists(done_subquery))
                .order_by("order"))

    # Superuser
    if request.user.is_superuser:
        try:
            sales_group = Group.objects.get(name="Sales")
            all_agents = User.objects.filter(groups=sales_group)
        except Group.DoesNotExist:
            all_agents = User.objects.none()

        selected_agent_id = request.GET.get("agent_id")
        selected_pipeline_id = request.GET.get("selected_pipeline_id")

        selected_user = User.objects.filter(id=selected_agent_id).first() if selected_agent_id else None
        pipelines = Pipeline.objects.filter(created_by=selected_user) if selected_user else Pipeline.objects.none()

        selected_pipeline = None
        if selected_pipeline_id:
            selected_pipeline = pipelines.filter(id=selected_pipeline_id).first()
        elif pipelines.exists():
            selected_pipeline = pipelines.first()

        stages = get_annotated_stages(selected_pipeline)

        return render(request, 'accounts/pipeline_list.html', {
            'pipelines': pipelines,
            'selected_pipeline': selected_pipeline,
            'selected_pipeline_id': selected_pipeline.id if selected_pipeline else None,
            'all_agents': all_agents,
            'selected_agent_id': selected_agent_id,
            'stages': stages,
        })

    # Normal user
    pipelines = Pipeline.objects.filter(created_by=request.user)
    selected_pipeline_id = request.GET.get("selected_pipeline_id")
    selected_pipeline = pipelines.filter(id=selected_pipeline_id).first() if selected_pipeline_id else pipelines.first()

    stages = get_annotated_stages(selected_pipeline)

    return render(request, 'accounts/pipeline_list.html', {
        'pipelines': pipelines,
        'selected_pipeline': selected_pipeline,
        'selected_pipeline_id': selected_pipeline.id if selected_pipeline else None,
        'stages': stages,
    })

@login_required
def add_to_pipeline(request, pk):
    lead = get_object_or_404(PotentialCustomer, pk=pk)

    if not (request.user.is_superuser or lead.assigned_agent == request.user):
        messages.error(request, "You are not allowed to add this lead to a pipeline.")
        return redirect('potential_customer_list')

    # Get first matching pipeline or create if none exist
    pipeline = Pipeline.objects.filter(created_by=request.user).first()
    if not pipeline:
        pipeline = Pipeline.objects.create(name=f"{request.user.username}'s Pipeline", created_by=request.user)

    # If pipeline was just created or empty, create default stages
    if pipeline.stages.count() == 0:
        default_stage_names = ["New", "Contacted", "Demo", "Negotiation", "Won"]
        for i, name in enumerate(default_stage_names, start=1):
            PipelineStage.objects.create(pipeline=pipeline, name=name, order=i)

    # Get first stage
    first_stage = pipeline.stages.order_by('order').first()
    if not first_stage:
        messages.error(request, "No stages found for your pipeline.")
        return redirect('potential_customer_list')

    # Prevent duplicates
    if LeadPipelineEntry.objects.filter(potential_customer=lead, pipeline=pipeline).exists():
        messages.warning(request, "This lead is already in your pipeline.")
        return redirect('potential_customer_list')

    # Create entry
    LeadPipelineEntry.objects.create(
        potential_customer=lead,
        pipeline=pipeline,
        stage=first_stage,
        assigned_agent=request.user
    )

    messages.success(request, f"Lead '{lead.potential_customer_name}' added to your pipeline!")
    return redirect('potential_customer_list')

@login_required
def pipeline_lead_detail(request, entry_id):
    entry = get_object_or_404(LeadPipelineEntry, id=entry_id)

    if not (entry.assigned_agent == request.user or request.user.is_superuser):
        return HttpResponseForbidden("Not allowed.")

    data = {
        'lead_name': str(entry.potential_customer),
        'note': entry.note or '',
        'stage': entry.stage.name,
    }
    return JsonResponse(data)

@login_required
def mark_lead_status(request, entry_id):
    entry = get_object_or_404(LeadPipelineEntry, id=entry_id)

    if not (entry.assigned_agent == request.user or request.user.is_superuser):
        return HttpResponseForbidden("Not allowed.")

    if request.method == "POST":
        status = request.POST.get("status")
        if status == "won":
            entry.is_won = True
            entry.is_lost = False
        elif status == "lost":
            entry.is_lost = True
            entry.is_won = False
        entry.save()
        messages.success(request, "Lead marked as " + status.upper())

    return redirect('pipeline_list')

@csrf_exempt
@login_required
def update_pipeline_stage(request):
    if request.method == "POST":
        data = json.loads(request.body)
        entry_id = data.get("entry_id")
        stage_id = data.get("stage_id")

        entry = get_object_or_404(LeadPipelineEntry, id=entry_id)

        if entry.assigned_agent != request.user and not request.user.is_superuser:
            return JsonResponse({"error": "Forbidden"}, status=403)

        entry.stage_id = stage_id
        entry.entered_stage_at = timezone.now()
        entry.save()
        return JsonResponse({"message": "Updated"})
    return JsonResponse({"error": "Invalid method"}, status=405)

@login_required
@require_POST
def update_lead_note(request, entry_id):
    entry = get_object_or_404(LeadPipelineEntry, id=entry_id)

    # Only allow assigned agent or superuser to update note
    if entry.assigned_agent != request.user and not request.user.is_superuser:
        return JsonResponse({'error': 'Forbidden'}, status=403)

    note = request.POST.get('note', '')
    entry.note = note
    entry.save()

    return JsonResponse({'status': 'success'})

@login_required
def create_pipeline(request):
    if request.method == 'POST':
        name = request.POST.get('pipeline_name')
        stage_count = int(request.POST.get('stage_count', 0))

        if name and stage_count > 0:
            pipeline = Pipeline.objects.create(name=name, created_by=request.user)

            for i in range(1, stage_count + 1):
                stage_name = request.POST.get(f'stage_name_{i}')
                if stage_name:
                    PipelineStage.objects.create(pipeline=pipeline, name=stage_name, order=i)

            messages.success(request, f"Pipeline '{name}' created with {stage_count} stages!")

    return redirect('pipeline_list')

@login_required
def delete_pipeline(request, pipeline_id):
    pipeline = get_object_or_404(Pipeline, id=pipeline_id)

    # Superuser can delete any, others only their own
    if not request.user.is_superuser and pipeline.created_by != request.user:
        messages.error(request, "Permission denied.")
        return redirect('pipeline_list')

    pipeline.delete()
    messages.success(request, "Pipeline deleted.")

    # Handle redirection safely
    if request.user.is_superuser:
        agent_id = request.GET.get('agent_id')
        if agent_id:
            remaining_pipelines = Pipeline.objects.filter(created_by__id=agent_id)
            if remaining_pipelines.exists():
                return redirect(f"{reverse('pipeline_list')}?agent_id={agent_id}&selected_pipeline_id={remaining_pipelines.first().id}")
            else:
                return redirect(f"{reverse('pipeline_list')}?agent_id={agent_id}")
        else:
            return redirect('pipeline_list')
    else:
        remaining_pipelines = Pipeline.objects.filter(created_by=request.user)
        if remaining_pipelines.exists():
            return redirect(f"{reverse('pipeline_list')}?selected_pipeline_id={remaining_pipelines.first().id}")
        else:
            return redirect('pipeline_list')

@login_required
@require_POST
def edit_stage(request):
    stage_id = request.POST.get("stage_id")
    name = request.POST.get("stage_name")

    stage = get_object_or_404(PipelineStage, id=stage_id)

    if stage.pipeline.created_by != request.user and not request.user.is_superuser:
        return HttpResponseForbidden("You don’t have permission to edit this stage.")

    stage.name = name
    stage.save()
    return redirect('pipeline_list')

@csrf_exempt
def update_stage_order(request):
    if request.method == "POST":
        data = json.loads(request.body)
        for item in data.get("order", []):
            try:
                stage = PipelineStage.objects.get(id=item["stage_id"])
                stage.order = item["order"]
                stage.save()
            except:
                continue
        return JsonResponse({"status": "success"})
    return JsonResponse({"status": "error"}, status=400)

@require_POST
@login_required
def remove_pipeline_entry(request, entry_id):
    entry = get_object_or_404(LeadPipelineEntry, id=entry_id)
    if entry.assigned_agent == request.user or request.user.is_superuser:
        entry.delete()
        return JsonResponse({"status": "success"})
    return JsonResponse({"status": "forbidden"}, status=403)

@login_required
def delete_stage(request, stage_id):
    stage = get_object_or_404(PipelineStage, id=stage_id)
    if request.user == stage.pipeline.created_by or request.user.is_superuser:
        stage.delete()
    return redirect('pipeline_list')

@login_required
def add_stage(request):
    if request.method == 'POST':
        name = request.POST.get('stage_name')
        pipeline_id = request.POST.get('pipeline_id')
        pipeline = get_object_or_404(Pipeline, id=pipeline_id)

        # Check superuser permission or ownership
        if not request.user.is_superuser and pipeline.created_by != request.user:
            messages.error(request, "Permission denied.")
            return redirect('pipeline_list')

        if name:
            max_order = pipeline.stages.aggregate(Max('order'))['order__max'] or 0
            PipelineStage.objects.create(pipeline=pipeline, name=name, order=max_order + 1)
            messages.success(request, "Stage added.")

        # Redirect back to the correct pipeline (and agent if superuser)
        redirect_url = reverse('pipeline_list')
        query_params = f"?selected_pipeline_id={pipeline_id}"
        if request.user.is_superuser:
            query_params += f"&agent_id={pipeline.created_by.id}"
        return redirect(f"{redirect_url}{query_params}")

    return redirect('pipeline_list')

@login_required
def add_lead_to_selected_pipeline(request):
    if request.method == "POST":
        lead_id = request.POST.get("lead_id")
        pipeline_id = request.POST.get("pipeline_id")

        lead = get_object_or_404(PotentialCustomer, id=lead_id)
        pipeline = get_object_or_404(Pipeline, id=pipeline_id)

        if not (request.user.is_superuser or lead.assigned_agent == request.user):
            messages.error(request, "Permission denied.")
            return redirect("potential_customer_list")

        # Create default stages if missing
        if pipeline.stages.count() == 0:
            default_stage_names = ["New", "Contacted", "Demo", "Negotiation", "Won"]
            for i, name in enumerate(default_stage_names, start=1):
                PipelineStage.objects.create(pipeline=pipeline, name=name, order=i)

        # Check if already added
        if LeadPipelineEntry.objects.filter(potential_customer=lead, pipeline=pipeline).exists():
            messages.warning(request, "Lead already in pipeline.")
            return redirect("potential_customer_list")

        first_stage = pipeline.stages.order_by("order").first()
        LeadPipelineEntry.objects.create(
            potential_customer=lead,
            pipeline=pipeline,
            stage=first_stage,
            assigned_agent=request.user,
        )

        messages.success(request, f"Lead '{lead.potential_customer_name}' added to pipeline '{pipeline.name}'.")
        return redirect("potential_customer_list")

    return redirect("potential_customer_list")

@require_POST
@login_required
def mark_pipeline_entry_done(request, entry_id):
    entry = get_object_or_404(LeadPipelineEntry, id=entry_id)
    if not (entry.assigned_agent == request.user or request.user.is_superuser):
        return JsonResponse({"error": "Not allowed"}, status=403)

    current_stage = entry.stage
    pipeline = current_stage.pipeline
    all_stages = list(pipeline.stages.order_by("order"))

    try:
        idx = all_stages.index(current_stage)
    except ValueError:
        return JsonResponse({"error": "Stage not found in pipeline"}, status=404)

    # record this stage as completed
    entry.done_stages.add(current_stage)

    # move on
    if idx < len(all_stages) - 1:
        entry.stage = all_stages[idx + 1]
        entry.is_done = True
        entry.entered_stage_at = timezone.now()
        entry.save()
        return JsonResponse({"status": "moved_to_next"})
    else:
        entry.is_done = True
        entry.is_won  = True
        entry.entered_stage_at = timezone.now()
        entry.save()
        return JsonResponse({"status": "final_stage"})

@require_POST
@login_required
def mark_pipeline_entry_undone(request, entry_id):
    entry = get_object_or_404(LeadPipelineEntry, id=entry_id)
    payload = json.loads(request.body)
    stage_id = int(payload.get("stage_id"))

    # Get that stage object (404 if it doesn’t exist)
    stage = get_object_or_404(PipelineStage, id=stage_id)

    # Remove it from the M2M set
    entry.done_stages.remove(stage)

    # Clear the “first done” marker:
    if entry.done_in_stage and entry.done_in_stage.id == stage_id:
        entry.done_in_stage = None

    # Optionally clear the overall flag
    entry.is_done = False
    entry.save()

    return JsonResponse({"status": "success"})

def is_admin(user):
    return user.is_superuser

@login_required
def meeting_list(request):
    now = timezone.now()

    if request.user.is_superuser:
        # Superuser only sees the meetings they themselves created
        upcoming = Meeting.objects.filter(
            created_by=request.user,
            start_datetime__gte=now
        )
        past = Meeting.objects.filter(
            created_by=request.user,
            end_datetime__lt=now
        )
        return render(request, "accounts/meeting_list.html", {
            "is_super": True,
            "upcoming": upcoming,
            "past":     past,
        })

    # Non-superuser
    # “My” meetings (creator)
    my_upcoming = Meeting.objects.filter(
        created_by=request.user,
        start_datetime__gte=now
    )
    my_past = Meeting.objects.filter(
        created_by=request.user,
        end_datetime__lt=now
    )

    # “Internal” meetings (invited by someone else) — only if published
    internal_upcoming = Meeting.objects.filter(
        participants=request.user,
        published=True,
        start_datetime__gte=now
    ).exclude(created_by=request.user)

    internal_past = Meeting.objects.filter(
        participants=request.user,
        published=True,
        end_datetime__lt=now
    ).exclude(created_by=request.user)

    return render(request, "accounts/meeting_list.html", {
        "is_super":          False,
        "my_upcoming":       my_upcoming,
        "my_past":           my_past,
        "internal_upcoming": internal_upcoming,
        "internal_past":     internal_past,
    })

@login_required
def meeting_detail(request, pk):
    meeting = get_object_or_404(Meeting, pk=pk)

    # Permissions
    is_participant = meeting.participants.filter(pk=request.user.pk).exists()
    if not (
        request.user.is_superuser
        or meeting.created_by == request.user
        or (is_participant and meeting.published)
    ):
        return HttpResponseForbidden()

    # RSVP map & summary
    participants_qs = meeting.meetingparticipant_set.select_related("user")
    rsvp_map = { mp.user_id: mp for mp in participants_qs }

    if request.user.is_superuser:
        rsvp_summary = {
            key: participants_qs.filter(rsvp_status=key).count()
            for key, _ in MeetingParticipant.RSVP_CHOICES
        }
    else:
        rsvp_summary = {}

    # Google Calendar link
    dtstart_utc = meeting.start_datetime.astimezone(pytz.UTC)
    dtend_base  = meeting.end_datetime or (meeting.start_datetime + timedelta(hours=1))
    dtend_utc   = dtend_base.astimezone(pytz.UTC)

    google_start = dtstart_utc.strftime("%Y%m%dT%H%M%SZ")
    google_end   = dtend_utc.strftime("%Y%m%dT%H%M%SZ")
    google_url = (
        "https://calendar.google.com/calendar/render?"
        f"action=TEMPLATE&text={quote(meeting.title)}"
        f"&dates={google_start}%2F{google_end}"
        f"&location={quote(meeting.location)}"
    )

    return render(request, "accounts/meeting_detail.html", {
        "meeting":      meeting,
        "rsvp_map":     rsvp_map,
        "rsvp_summary": rsvp_summary,
        "google_url":   google_url,
    })

@login_required
def meeting_create(request):
    """
    - Superusers: multi-invite form + notification
    - Everyone else: 1-on-1 form (customer OR lead) + auto-RSVP + email
    """
    if request.method == "POST":
        form = MeetingForm(request.POST, user=request.user)
        if form.is_valid():
            meeting = form.save(commit=False)
            meeting.created_by = request.user
            meeting.save()
            form.save_m2m()

            if request.user.is_superuser:
                # old multi-invite
                for u in form.cleaned_data.get("participants", []):
                    MeetingParticipant.objects.get_or_create(
                        meeting=meeting, user=u
                    )
                if meeting.published:
                    for u in meeting.participants.all():
                        Notification.objects.create(
                            user=u,
                            message=(
                                f"New meeting: “{meeting.title}” at "
                                f"{meeting.start_datetime:%Y-%m-%d %H:%M}"
                            )
                        )
                messages.success(request, "Meeting created.")
            else:
                # 1-on-1 agent flow
                MeetingParticipant.objects.create(
                    meeting=meeting,
                    user=request.user,
                    rsvp_status="yes",
                )
                cust   = form.cleaned_data.get("customer")
                lead   = form.cleaned_data.get("lead")
                to_addr = (
                    cust.customer_email
                    if cust
                    else (lead.potential_customer_email if lead else None)
                )
                if to_addr:
                    subject = f"Invitation: {meeting.title}"
                    body = (
                        f"You’re invited to a meeting:\n\n"
                        f"Title:   {meeting.title}\n"
                        f"When:    {meeting.start_datetime:%Y-%m-%d %H:%M}\n"
                        f"Where:   {meeting.location}\n\n"
                        f"{meeting.agenda}"
                    )
                    send_mail(
                        subject,
                        body,
                        settings.DEFAULT_FROM_EMAIL,
                        [to_addr],
                        fail_silently=False,
                    )
                    messages.success(
                        request,
                        "Meeting scheduled and invitation emailed."
                    )
                else:
                    messages.warning(
                        request,
                        "Meeting scheduled but no customer/lead selected so no email sent."
                    )

            return redirect("meeting_list")

    else:
        form = MeetingForm(user=request.user)

    return render(request, "accounts/meeting_form.html", {"form": form})


@login_required
def meeting_edit(request, pk):
    meeting = get_object_or_404(Meeting, pk=pk)

    # only superusers or original creator may edit
    if not (request.user.is_superuser or meeting.created_by == request.user):
        return HttpResponseForbidden()

    old_published    = meeting.published
    old_participants = set(meeting.participants.all())

    # handle Cancel action
    if request.method == "POST" and "cancel" in request.POST:
        # notify all current participants
        for mp in meeting.meetingparticipant_set.select_related("user"):
            Notification.objects.create(
                user=mp.user,
                message=(
                    f"Meeting “{meeting.title}” on "
                    f"{meeting.start_datetime:%Y-%m-d %H:%M} was canceled."
                )
            )
        meeting.delete()
        messages.success(request, "Meeting canceled and participants notified.")
        return redirect("meeting_list")

    # handle Save action
    if request.method == "POST":
        form = MeetingForm(request.POST, instance=meeting, user=request.user)
        if form.is_valid():
            meeting = form.save(commit=False)
            meeting.save()
            form.save_m2m()

            if request.user.is_superuser:
                # multi-invite syncing + notifications
                current = set(form.cleaned_data.get("participants", []))
                for u in current:
                    MeetingParticipant.objects.get_or_create(meeting=meeting, user=u)
                if not old_published and meeting.published:
                    # just published: notify all
                    for u in current:
                        Notification.objects.create(
                            user=u,
                            message=(
                                f"You’ve been invited to meeting “{meeting.title}” "
                                f"at {meeting.start_datetime:%Y-%m-d %H:%M}"
                            )
                        )
                elif meeting.published:
                    # already published: notify new invitees only
                    new_inv = current - old_participants
                    for u in new_inv:
                        Notification.objects.create(
                            user=u,
                            message=(
                                f"You’ve been invited to meeting “{meeting.title}” "
                                f"at {meeting.start_datetime:%Y-%m-d %H:%M}"
                            )
                        )
                messages.success(request, "Meeting updated.")
            else:
                # agent reschedule flow
                messages.success(request, "Meeting updated.")

            return redirect("meeting_detail", pk=meeting.pk)
    else:
        form = MeetingForm(instance=meeting, user=request.user)

    return render(request, "accounts/meeting_form.html", {
        "form":    form,
        "meeting": meeting,
    })

@login_required
@user_passes_test(is_admin)
def ajax_users_by_groups(request):
    group_ids = request.GET.get("group_ids", "")
    try:
        ids = [int(pk) for pk in group_ids.split(",") if pk.strip()]
    except ValueError:
        return JsonResponse([], safe=False)

    qs = User.objects.filter(groups__id__in=ids).distinct()
    data = [
        {
            "id": u.id,
            "username": u.username,
            "full_name": u.get_full_name() or u.username
        }
        for u in qs
    ]
    return JsonResponse(data, safe=False)

@login_required
def submit_rsvp(request, pk):
    meeting = get_object_or_404(Meeting, pk=pk)
    try:
        mp = MeetingParticipant.objects.get(meeting=meeting, user=request.user)
    except MeetingParticipant.DoesNotExist:
        return JsonResponse({'error': 'You are not invited to this meeting.'}, status=403)

    if request.method == 'POST':
        rsvp = request.POST.get("rsvp")
        valid_options = [choice[0] for choice in MeetingParticipant.RSVP_CHOICES]
        if rsvp in valid_options:
            mp.rsvp_status = rsvp
            mp.responded_at = timezone.now()
            mp.save()
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'error': 'Invalid RSVP option'}, status=400)

    return JsonResponse({'error': 'Invalid request method'}, status=405)

@login_required
def meeting_delete(request, pk):
    meeting = get_object_or_404(Meeting, pk=pk)
    # only superusers or creator may delete
    if not (request.user.is_superuser or meeting.created_by == request.user):
        return HttpResponseForbidden()

    if request.method == 'POST':
        # grab the requested tab (default to “mine” for non-super)
        tab = request.POST.get('tab', 'all' if request.user.is_superuser else 'mine')
        meeting.delete()
        messages.success(request, "Meeting deleted.")

        # redirect back to the list, preserving the tab query param
        url = reverse('meeting_list')
        return redirect(f"{url}?tab={tab}")

    return HttpResponseNotAllowed(['POST'])

@login_required
def remove_participation(request, pk):
    """Allow a normal user to remove themselves from a *past* meeting."""
    meeting = get_object_or_404(Meeting, pk=pk, participants=request.user)
    now = timezone.now()
        # only past meetings may be removed
    if not meeting.end_datetime or meeting.end_datetime >= now:
        return HttpResponseForbidden("Can only remove past meetings.")

    if request.method == 'POST':
        MeetingParticipant.objects.filter(
            meeting=meeting,
            user=request.user
        ).delete()
        messages.success(request, "Removed this meeting from your history.")
        return redirect('meeting_list')
    return HttpResponseNotAllowed(['POST'])

@login_required
def meeting_ics(request, pk):
    m = get_object_or_404(Meeting, pk=pk)

    # permission check
    if (not m.published
        and not request.user.is_superuser
        and request.user not in m.participants.all()):
        return HttpResponseForbidden("You may not download this meeting.")

    # helper to format a datetime as a UTC ICS timestamp
    def fmt(dt):
        return dt.astimezone(dt_timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    dtstart = m.start_datetime
    dtend   = m.end_datetime or (dtstart + timedelta(hours=1))
    dtstamp = timezone.now()
    uid     = f"meeting-{m.pk}@{request.get_host()}"

    ics_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//YourApp//Meetings//EN",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{fmt(dtstamp)}",
        f"DTSTART:{fmt(dtstart)}",
        f"DTEND:{fmt(dtend)}",
        f"SUMMARY:{m.title}",
        # fall back to empty string if agenda is blank
        f"DESCRIPTION:{m.agenda or ''}",
        f"LOCATION:{m.location}",
        # 1-hour reminder
        "BEGIN:VALARM",
        "TRIGGER:-PT60M",
        "ACTION:DISPLAY",
        f"DESCRIPTION:Reminder — 1 hour until {m.title}",
        "END:VALARM",
        # 30-minute reminder
        "BEGIN:VALARM",
        "TRIGGER:-PT30M",
        "ACTION:DISPLAY",
        f"DESCRIPTION:Reminder — 30 minutes until {m.title}",
        "END:VALARM",
        "END:VEVENT",
        "END:VCALENDAR",
    ]

    return HttpResponse("\r\n".join(ics_lines), content_type="text/calendar")

@login_required
@user_passes_test(is_admin)
def meeting_cancel(request, pk):
    meeting = get_object_or_404(Meeting, pk=pk)
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    if not meeting.published:
        messages.warning(request, "That meeting is already unpublished.")
        return redirect('meeting_detail', pk=pk)

    # gather participants before unpublishing
    participants = list(meeting.participants.all())

    # unpublish (i.e. “cancel”) the meeting
    meeting.published = False
    meeting.save()

    # notify everyone who was invited
    when = meeting.start_datetime.strftime("%Y-%m-%d %H:%M")
    for user in participants:
        Notification.objects.create(
            user=user,
            message=(
                f"Meeting “{meeting.title}” scheduled on {when} "
                "has been canceled."
            )
        )

    messages.success(request, "Meeting canceled and notifications sent.")
    return redirect('meeting_list')

REPORT_DESCRIPTIONS = {
    'tickets_volume':      "Number of tickets opened per day in the selected range.",
    'avg_resolution':      "Average time between ticket creation and resolution.",
    'pipeline_value':      "Count of leads added to any pipeline.",
    'pipeline_conversion': "Share of pipeline leads marked “Won” vs all added.",
    'meetings_scheduled':  "Number of meetings scheduled per day.",
    'meetings_attendance': "Average meeting attendance rate (global or per-agent).",
    'customers_new':       "How many customers joined in that period.",
}

@login_required
def reports(request):
    form        = ReportForm(request.GET or None)
    data        = None
    description = ""

    if form.is_valid():
        sd    = form.cleaned_data['start_date']
        ed    = form.cleaned_data['end_date']
        grp   = form.cleaned_data['group']
        agent = form.cleaned_data['agent']
        rpt   = form.cleaned_data['report_type']

        # Ticket/Customer filters
        base_filters = {}
        if agent:
            base_filters['created_by'] = agent
        elif grp:
            base_filters['created_by__groups'] = grp

        # Pipeline‐entry filters
        entry_filters = {}
        if agent:
            entry_filters['assigned_agent'] = agent
        elif grp:
            entry_filters['assigned_agent__groups'] = grp
        # Tickets Volume Over Time
        if rpt == 'tickets_volume':
            qs = (
                Ticket.objects
                      .filter(created_date__date__gte=sd,
                              created_date__date__lte=ed,
                              **base_filters)
                      .annotate(day=TruncDate('created_date'))
                      .values('day')
                      .order_by('day')
                      .annotate(count=Count('id'))
            )
            data = list(qs)
        # Average Ticket Resolution Time
        elif rpt == 'avg_resolution':
            agg = (
                Ticket.objects
                      .filter(resolved_date__date__gte=sd,
                              resolved_date__date__lte=ed,
                              resolved_date__isnull=False,
                              **base_filters)
                      .annotate(
                          resolution=ExpressionWrapper(
                              F('resolved_date') - F('created_date'),
                              output_field=DurationField()
                          )
                      )
                      .aggregate(avg_res=Avg('resolution'))
            )
            avg = agg['avg_res']
            if avg:
                secs = avg.total_seconds()
                hrs  = int(secs // 3600)
                mins = int((secs % 3600) // 60)
                data = f"{hrs}h {mins}m"
            else:
                # force the template to render the “no tickets” message
                data = ""
        # Pipeline Total Entries Added
        elif rpt == 'pipeline_value':
            data = LeadPipelineEntry.objects.filter(
                added_at__date__gte=sd,
                added_at__date__lte=ed,
                **entry_filters
            ).count()
        # Pipeline Conversion Rates
        elif rpt == 'pipeline_conversion':
            qs    = LeadPipelineEntry.objects.filter(
                        added_at__date__gte=sd,
                        added_at__date__lte=ed,
                        **entry_filters
                    )
            total = qs.count()
            won   = qs.filter(is_won=True).count()
            data  = {
                'won':     won,
                'total':   total,
                'percent': (won / total * 100) if total else 0
            }
        # Meetings Scheduled per Day
        elif rpt == 'meetings_scheduled':
            qs = (
                Meeting.objects
                       .filter(start_datetime__date__gte=sd,
                               start_datetime__date__lte=ed,
                               **base_filters)
                       .annotate(day=TruncDate('start_datetime'))
                       .values('day')
                       .order_by('day')
                       .annotate(count=Count('id'))
            )
            data = list(qs)
        # Meeting Attendance Rate
        elif rpt == 'meetings_attendance':
            if agent:
                # Per-agent breakdown
                mp_qs   = MeetingParticipant.objects.filter(
                              user=agent,
                              meeting__start_datetime__date__gte=sd,
                              meeting__start_datetime__date__lte=ed
                          )
                total   = mp_qs.count()
                yes     = mp_qs.filter(rsvp_status='yes').count()
                no      = mp_qs.filter(rsvp_status='no').count()
                maybe   = mp_qs.filter(rsvp_status='maybe').count()
                percent = (yes / total * 100) if total else 0
                data = {
                    'yes':     yes,
                    'no':      no,
                    'maybe':   maybe,
                    'total':   total,
                    'percent': percent
                }
            else:
                # Global: average per-meeting attendance
                meetings = Meeting.objects.filter(
                    start_datetime__date__gte=sd,
                    start_datetime__date__lte=ed,
                    **base_filters
                )
                m_list = list(meetings)
                count  = len(m_list)
                if count:
                    sum_pct = 0.0
                    for m in m_list:
                        tot_p = m.meetingparticipant_set.count()
                        if tot_p:
                            yes_p = m.meetingparticipant_set.filter(
                                        rsvp_status='yes'
                                    ).count()
                            sum_pct += (yes_p / tot_p)
                    avg_pct = (sum_pct / count) * 100
                else:
                    avg_pct = 0.0

                data = {
                    'num_meetings': count,
                    'avg_percent':  avg_pct
                }
        # New Customers Joined
        elif rpt == 'customers_new':
            # Count customers whose joined date falls in [sd, ed].
            data = Customer.objects.filter(
                customer_joined_at__gte=sd,
                customer_joined_at__lte=ed
            ).count()

        # pull in the friendly description
        description = REPORT_DESCRIPTIONS.get(rpt, "")

    return render(request, 'accounts/reports.html', {
        'form':        form,
        'data':        data,
        'description': description,
    })