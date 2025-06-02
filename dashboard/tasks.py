from celery import shared_task
from django.utils import timezone
from .models import MeetingParticipant, Notification

@shared_task
def send_meeting_reminder(mp_id):
    try:
        mp = (
            MeetingParticipant.objects
            .select_related("meeting", "user")
            .get(pk=mp_id)
        )
    except MeetingParticipant.DoesNotExist:
        return

    m = mp.meeting
    if m.published and mp.user in m.participants.all():
        Notification.objects.create(
            user=mp.user,
            message=(
                f"Reminder: “{m.title}” starts at "
                f"{m.start_datetime:%Y-%m-%d %H:%M}"
            )
        )
