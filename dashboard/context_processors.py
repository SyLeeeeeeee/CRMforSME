from .models import Notification

def unread_notifications_count(request):
    if request.user.is_authenticated:
        return {
            'has_unread_notifications': Notification.objects.filter(user=request.user, is_read=False).exists()
        }
    return {'has_unread_notifications': False}
