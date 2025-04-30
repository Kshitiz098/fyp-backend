from django.test import TestCase
from .models import Notification, User, Task
from django.utils import timezone
from datetime import timedelta

class NotificationModelTest(TestCase):

    def test_create_notification(self):
        # Create a user instance
        user = User.objects.create_user(
            username='janedoe',
            email='jane@example.com',
            full_name='Jane Doe',
            password='Test@1234'
        )
        
        # Create a task instance
        deadline = timezone.now() + timedelta(days=1)
        task = Task.objects.create(
            user=user,
            title='Complete Assignment',
            subject='Mathematics',
            urgency='high',
            task_type='assignment',
            deadline=deadline
        )
        
        # Create a notification instance for the task
        notification = Notification.objects.create(
            user=user,
            message='You have a new task due soon.',
            related_task=task
        )
        
        # Ensure the notification is created correctly
        self.assertEqual(notification.message, 'You have a new task due soon.')
        self.assertEqual(notification.related_task, task)
        self.assertFalse(notification.read)
        self.assertEqual(notification.user, user)
