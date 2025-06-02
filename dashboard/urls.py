from django.urls import path
from . import views
from django.shortcuts import render
from .views import add_to_pipeline

urlpatterns = [
    # Dashboard
    path('', views.dashboard_view, name='dashboard'),

    # Tickets
    path('tickets/', views.ticket_list, name='tickets'),
    path('tickets/create/', views.create_ticket, name='add_ticket'),
    path('tickets/<int:id>/', views.ticket_detail, name='ticket_detail'),

    # AJAX
    path('get-agents-by-group/', views.get_agents_by_group, name='get_agents_by_group'),
    path('ajax/get-customer-info/<int:customer_id>/', views.get_customer_info, name='get_customer_info'),

    # Customers
    path('customers/', views.customer_list, name='customer_list'),
    path('customers/add/', views.customer_add, name='customer_add'),
    path('customers/<int:pk>/edit/', views.customer_edit, name='customer_edit'),
    path('customers/<int:pk>/delete/', views.customer_delete, name='customer_delete'),

    # Potential Customers / Leads
    path('leads/', views.potential_customer_list, name='potential_customer_list'),
    path('leads/add/', views.add_potential_customer, name='add_potential_customer'),
    path('leads/<int:pk>/mark-dead/', views.mark_lead_as_dead, name='mark_lead_as_dead'),
    path('leads/<int:pk>/convert/', views.convert_lead_to_customer, name='convert_lead'),
    path('leads/<int:pk>/edit/', views.edit_lead_status, name='edit_lead_status'),

    # Notifications
    path('notifications/mark-read/<int:id>/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/clear-all/', views.clear_all_notifications, name='clear_all_notifications'),

    # External submission
    path('submit-lead/', views.submit_lead_view, name='submit_lead'),
    path('thank-you/', lambda request: render(request, 'accounts/thank_you.html'), name='thank_you'),

    # Pipelines
    path('pipeline/', views.pipeline_list, name='pipeline_list'),
    path('leads/<int:pk>/add-to-pipeline/', add_to_pipeline, name='add_to_pipeline_by_id'),
    path('pipeline/stage/edit/', views.edit_stage, name='edit_stage'),
    path('pipeline/lead-detail/<int:entry_id>/', views.pipeline_lead_detail, name='pipeline_lead_detail'),
    path('pipeline/mark-status/<int:entry_id>/', views.mark_lead_status, name='mark_lead_status'),
    path('pipeline/update-stage/', views.update_pipeline_stage, name='update_pipeline_stage'),
    path('pipeline/update-note/<int:entry_id>/', views.update_lead_note, name='update_lead_note'),
    path('pipeline/create/', views.create_pipeline, name='create_pipeline'),
    path('pipeline/update-stage-order/', views.update_stage_order, name='update_stage_order'),
    path('pipeline/remove-entry/<int:entry_id>/', views.remove_pipeline_entry, name='remove_pipeline_entry'),
    path('pipeline/delete/<int:pipeline_id>/', views.delete_pipeline, name='delete_pipeline'),
    path('pipeline/delete-stage/<int:stage_id>/', views.delete_stage, name='delete_stage'),
    path('pipeline/add-stage/', views.add_stage, name='add_stage'),
    path('leads/add-to-pipeline/', views.add_to_pipeline, name='add_to_pipeline'),
    path('leads/add-to-selected-pipeline/', views.add_lead_to_selected_pipeline, name='add_lead_to_selected_pipeline'),
    path('pipeline/mark-done/<int:entry_id>/', views.mark_pipeline_entry_done, name='mark_pipeline_entry_done'),
    path('pipeline/mark-undone/<int:entry_id>/',views.mark_pipeline_entry_undone,name='mark_pipeline_entry_undone'),

    # Meetings
    path('meetings/',        views.meeting_list,   name='meeting_list'),
    path('meetings/create/', views.meeting_create, name='meeting_create'),
    path('meetings/<int:pk>/',    views.meeting_detail, name='meeting_detail'),
    path('meetings/<int:pk>/edit/', views.meeting_edit, name='meeting_edit'),
    path('ajax/users-by-groups/', views.ajax_users_by_groups, name='ajax_users_by_groups'),
    path('meetings/<int:pk>/rsvp/', views.submit_rsvp, name='submit_rsvp'),
    path('meetings/<int:pk>/delete/', views.meeting_delete, name='meeting_delete'),
    path('meetings/<int:pk>/remove/', views.remove_participation, name='remove_participation'),
    path('meetings/<int:pk>/ics/', views.meeting_ics, name='meeting_ics'),
    path('meetings/<int:pk>/cancel/', views.meeting_cancel, name='meeting_cancel'),

    # Reports
    path('reports/', views.reports, name='reports'),

]
