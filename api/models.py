from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import EmailValidator
from django.forms import ValidationError
from django.utils import timezone
import uuid
import os
from django.dispatch import receiver
from django.db.models.signals import post_delete
import bcrypt

def user_profile_picture_path(instance, filename):
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('profile_pictures', str(instance.id), filename)

class User(AbstractUser):
    email = models.EmailField(unique=True, validators=[EmailValidator()])
    full_name = models.CharField(max_length=255)
    profile_picture = models.ImageField(upload_to=user_profile_picture_path, null=True, blank=True)
    email_verified = models.BooleanField(default=False)
    verification_code = models.CharField(max_length=6, null=True, blank=True)
    verification_code_created_at = models.DateTimeField(null=True, blank=True)
    
    def set_password(self, raw_password):
        # Hash password using bcrypt
        salt = bcrypt.gensalt()
        self.password = bcrypt.hashpw(raw_password.encode('utf-8'), salt).decode('utf-8')
    
    def check_password(self, raw_password):
        return bcrypt.checkpw(raw_password.encode('utf-8'), self.password.encode('utf-8'))

class Task(models.Model):
    URGENCY_CHOICES = [
        ('high', 'High'),
        ('normal', 'Normal'),
    ]
    
    TASK_TYPE_CHOICES = [
        ('assignment', 'Assignment'),
        ('exam', 'Exam'),
        ('project', 'Project'),
        ('revision', 'Revision'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=255)
    subject = models.CharField(max_length=255)
    urgency = models.CharField(max_length=10, choices=URGENCY_CHOICES)
    task_type = models.CharField(max_length=20, choices=TASK_TYPE_CHOICES)
    deadline = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed = models.BooleanField(default=False)
    missed = models.BooleanField(default=False)
    
    def save(self, *args, **kwargs):
        # Check if task is missed
        if not self.completed and self.deadline < timezone.now():
            self.missed = True
        super().save(*args, **kwargs)

class SubTask(models.Model):
    task = models.ForeignKey('Task', on_delete=models.CASCADE, related_name='subtasks')
    title = models.CharField(max_length=255)
    deadline = models.DateTimeField()
    completed = models.BooleanField(default=False)

    def clean(self):
        """Validate deadline is before parent task's deadline"""
        if hasattr(self, 'task') and self.deadline > self.task.deadline:
            raise ValidationError("SubTask deadline cannot be after parent Task's deadline")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    related_task = models.ForeignKey(Task, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)

@receiver(post_delete, sender=User)
def delete_user_files(sender, instance, **kwargs):
    if instance.profile_picture:
        if os.path.isfile(instance.profile_picture.path):
            os.remove(instance.profile_picture.path)
            folder = os.path.dirname(instance.profile_picture.path)
            if not os.listdir(folder):
                os.rmdir(folder)