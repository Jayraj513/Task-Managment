"""
Notification and activity event logging service.
"""
from django.utils import timezone
from apps.notifications.models import ActivityEvent, Notification, ActivityEventType


def record_activity(workspace, actor, event_type, summary, project=None, task=None, metadata=None):
    """
    Persist an audit-trail activity event for workspace, project, or task.
    """
    if metadata is None:
        metadata = {}
    return ActivityEvent.objects.create(
        workspace=workspace,
        actor=actor,
        project=project,
        task=task,
        event_type=event_type,
        summary=summary,
        metadata=metadata
    )


def notify_user(recipient, title, message, actor=None, task=None, project=None, event_type='SYSTEM', link_url=''):
    """
    Create an in-app notification for a user.
    Avoid notifying the actor of their own actions.
    """
    if actor and recipient == actor:
        return None

    return Notification.objects.create(
        recipient=recipient,
        actor=actor,
        task=task,
        project=project,
        event_type=event_type,
        title=title,
        message=message,
        link_url=link_url
    )
