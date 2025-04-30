from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import User, Task, SubTask, Notification
from rest_framework.permissions import AllowAny
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, UserProfileSerializer,
    TaskSerializer, SubTaskSerializer, NotificationSerializer,
    VerificationCodeSerializer, EmailUpdateSerializer, PasswordCheckSerializer
)
from django.core.mail import send_mail
from django.conf import settings
import random
from datetime import datetime, timedelta
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import get_object_or_404
import os
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.http import JsonResponse

def generate_verification_code():
    return str(random.randint(1000, 9999))

import logging
logger = logging.getLogger(__name__)

class UserRegistrationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        logger.info(f"Registration attempt with data: {request.data}")
        
        try:
            serializer = UserRegistrationSerializer(data=request.data)
            if not serializer.is_valid():
                logger.error(f"Validation errors: {serializer.errors}")
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            user = serializer.save()
            logger.info(f"User created: {user.username}")

            # Generate and save verification code
            verification_code = generate_verification_code()
            user.verification_code = verification_code
            user.verification_code_created_at = timezone.now()
            user.save()

            # Email sending with error handling
            try:
                send_mail(
                    'Verify Your Email',
                    f'Your verification code is: {verification_code}',
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False,
                )
                logger.info(f"Verification email sent to {user.email}")
            except Exception as e:
                logger.error(f"Failed to send email: {str(e)}")
                raise Exception("Registration complete but failed to send email")

            return Response({
                'status': 'success',
                'message': 'Verification code sent to your email',
                'email': user.email
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Registration failed: {str(e)}", exc_info=True)
            return Response({
                'status': 'error',
                'message': 'Registration failed',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class VerifyEmailView(APIView):
    permission_classes = [AllowAny]  # Add this line
    
    def post(self, request):
        serializer = VerificationCodeSerializer(data=request.data)
        if serializer.is_valid():
            email = request.data.get('email')
            code = serializer.validated_data['code']
            
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
            
            if user.verification_code != code:
                return Response({'error': 'Invalid verification code'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if code is expired (10 minutes)
            if (timezone.now() - user.verification_code_created_at) > timedelta(minutes=10):
                return Response({'error': 'Verification code expired'}, status=status.HTTP_400_BAD_REQUEST)
            
            user.email_verified = True
            user.verification_code = None
            user.verification_code_created_at = None
            user.save()
            
            return Response({
                'message': f'{user.username} successfully created',
                'username': user.username
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ResendVerificationCodeView(APIView):
    permission_classes = [AllowAny]  # Add this line

    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Generate new verification code
        verification_code = generate_verification_code()
        user.verification_code = verification_code
        user.verification_code_created_at = timezone.now()
        user.save()
        
        # Send verification email
        send_mail(
            'Verify Your Email',
            f'Your new verification code is: {verification_code}',
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        
        return Response({
            'message': 'New verification code sent to your email'
        }, status=status.HTTP_200_OK)

class UserLoginView(APIView):
    permission_classes = [AllowAny]  # Add this line

    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'message': 'Login successful',
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': UserProfileSerializer(user).data
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)

class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        # Handle profile picture upload
        if 'profile_picture' in request.FILES:
            if instance.profile_picture:
                # Delete old profile picture
                if os.path.isfile(instance.profile_picture.path):
                    os.remove(instance.profile_picture.path)
            
            # Save new profile picture
            profile_picture = request.FILES['profile_picture']
            path = default_storage.save(f'profile_pictures/{instance.id}/{profile_picture.name}', ContentFile(profile_picture.read()))
            instance.profile_picture = path
            instance.save()
        
        return Response(serializer.data)

class DeleteProfilePictureView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def delete(self, request):
        user = request.user
        if user.profile_picture:
            if os.path.isfile(user.profile_picture.path):
                os.remove(user.profile_picture.path)
            user.profile_picture = None
            user.save()
            return Response({'message': 'Profile picture deleted successfully'}, status=status.HTTP_200_OK)
        return Response({'error': 'No profile picture to delete'}, status=status.HTTP_400_BAD_REQUEST)

class UpdateEmailView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = EmailUpdateSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            new_email = serializer.validated_data['email']
            
            # Generate verification code
            verification_code = generate_verification_code()
            user.new_email = new_email
            user.verification_code = verification_code
            user.verification_code_created_at = timezone.now()
            user.save()
            
            # Send verification email
            send_mail(
                'Verify Your New Email',
                f'Your verification code is: {verification_code}',
                settings.DEFAULT_FROM_EMAIL,
                [new_email],
                fail_silently=False,
            )
            
            return Response({
                'message': 'Verification code sent to your new email',
                'email': new_email
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class VerifyEmailUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = VerificationCodeSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            code = serializer.validated_data['code']
            
            if not user.new_email:
                return Response({'error': 'No email update pending'}, status=status.HTTP_400_BAD_REQUEST)
            
            if user.verification_code != code:
                return Response({'error': 'Invalid verification code'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if code is expired (10 minutes)
            if (timezone.now() - user.verification_code_created_at) > timedelta(minutes=10):
                return Response({'error': 'Verification code expired'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Update email
            user.email = user.new_email
            user.new_email = None
            user.verification_code = None
            user.verification_code_created_at = None
            user.save()
            
            return Response({
                'message': 'Email updated successfully',
                'email': user.email
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class TaskListView(generics.ListCreateAPIView):
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Task.objects.filter(user=self.request.user, completed=False).order_by('deadline')
    
    def perform_create(self, serializer):
        task = serializer.save(user=self.request.user)
        
        # Create notification if deadline is within 2 days
        if task.deadline - timezone.now() <= timedelta(days=2):
            Notification.objects.create(
                user=self.request.user,
                message=f"Task '{task.title}' is due in less than 2 days",
                related_task=task
            )

class TaskDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Task.objects.filter(user=self.request.user)
    
    def perform_update(self, serializer):
        task = serializer.save()
        
        # Check if task is completed
        if 'completed' in self.request.data and self.request.data['completed']:
            Notification.objects.create(
                user=self.request.user,
                message=f"Task '{task.title}' completed!",
                related_task=task
            )
        
        # Check if deadline changed and is within 2 days
        if 'deadline' in self.request.data:
            new_deadline = serializer.validated_data.get('deadline')
            if new_deadline and new_deadline - timezone.now() <= timedelta(days=2):
                Notification.objects.create(
                    user=self.request.user,
                    message=f"Task '{task.title}' is due in less than 2 days",
                    related_task=task
                )

class SubTaskView(generics.ListCreateAPIView):
    serializer_class = SubTaskSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        task_id = self.kwargs['task_id']
        return SubTask.objects.filter(task__id=task_id, task__user=self.request.user)
    
    def perform_create(self, serializer):
        task = get_object_or_404(Task, id=self.kwargs['task_id'], user=self.request.user)
        serializer.save(task=task)

class SubTaskDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = SubTaskSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return SubTask.objects.filter(task__user=self.request.user)

class TaskHistoryView(generics.ListAPIView):
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Task.objects.filter(
            user=self.request.user
        ).exclude(completed=False, missed=False).order_by('-deadline')

class MonthlyReportView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        month = request.query_params.get('month', None)
        year = request.query_params.get('year', None)
        
        if not month or not year:
            return Response({'error': 'Month and year parameters are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            month = int(month)
            year = int(year)
            start_date = timezone.datetime(year=year, month=month, day=1)
            if month == 12:
                end_date = timezone.datetime(year=year+1, month=1, day=1)
            else:
                end_date = timezone.datetime(year=year, month=month+1, day=1)
        except (ValueError, TypeError):
            return Response({'error': 'Invalid month or year'}, status=status.HTTP_400_BAD_REQUEST)
        
        tasks = Task.objects.filter(
            user=request.user,
            deadline__gte=start_date,
            deadline__lt=end_date
        )
        
        total_tasks = tasks.count()
        completed_tasks = tasks.filter(completed=True).count()
        missed_tasks = tasks.filter(missed=True).count()
        
        completion_percentage = 0
        if total_tasks > 0:
            completion_percentage = (completed_tasks / total_tasks) * 100
        
        return Response({
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'missed_tasks': missed_tasks,
            'completion_percentage': round(completion_percentage, 2)
        })

class HighUrgencyTasksView(generics.ListAPIView):
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Task.objects.filter(
            user=self.request.user,
            urgency='high',
            completed=False,
            deadline__gte=timezone.now()
        ).order_by('deadline')

class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')

class MarkNotificationAsReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, pk):
        notification = get_object_or_404(Notification, id=pk, user=request.user)
        notification.read = True
        notification.save()
        return Response({'message': 'Notification marked as read'})

class DeleteAccountView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = PasswordCheckSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            if user.check_password(serializer.validated_data['password']):
                # Delete user and all related data
                user.delete()
                return Response({'message': 'Account deleted successfully'}, status=status.HTTP_200_OK)
            return Response({'error': 'Incorrect password'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)