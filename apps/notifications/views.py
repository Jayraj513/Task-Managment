from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from apps.notifications.models import Notification


@login_required
def notification_list_view(request):
    notifications = Notification.objects.filter(
        recipient=request.user
    ).select_related('actor', 'task', 'project').order_by('-created_at')

    unread_notifications = [n for n in notifications if not n.read_at]
    read_notifications = [n for n in notifications if n.read_at]

    return render(request, 'notifications/list.html', {
        'unread_notifications': unread_notifications,
        'read_notifications': read_notifications,
        'total_count': len(notifications),
    })


@login_required
@require_POST
def mark_notification_read(request, notification_id):
    notif = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    if not notif.read_at:
        notif.read_at = timezone.now()
        notif.save()

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
        return JsonResponse({'success': True})

    next_url = request.POST.get('next') or notif.link_url or 'notification_list'
    return redirect(next_url)


@login_required
@require_POST
def mark_all_notifications_read(request):
    Notification.objects.filter(
        recipient=request.user,
        read_at__isnull=True
    ).update(read_at=timezone.now())

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True})

    return redirect('notification_list')
