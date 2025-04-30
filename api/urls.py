from django.urls import path
from .views import (
    UserRegistrationView, VerifyEmailView, ResendVerificationCodeView, UserLoginView,
    UserProfileView, DeleteProfilePictureView, UpdateEmailView, VerifyEmailUpdateView,
    TaskListView, TaskDetailView, SubTaskView, SubTaskDetailView, TaskHistoryView,
    MonthlyReportView, HighUrgencyTasksView, NotificationListView, MarkNotificationAsReadView,
    DeleteAccountView
)

urlpatterns = [
    # Authentication
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('verify-email/', VerifyEmailView.as_view(), name='verify-email'),
    path('resend-verification-code/', ResendVerificationCodeView.as_view(), name='resend-verification-code'),
    path('login/', UserLoginView.as_view(), name='login'),
    
    # User Profile
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('profile/delete-picture/', DeleteProfilePictureView.as_view(), name='delete-profile-picture'),
    path('profile/update-email/', UpdateEmailView.as_view(), name='update-email'),
    path('profile/verify-email-update/', VerifyEmailUpdateView.as_view(), name='verify-email-update'),
    path('profile/delete-account/', DeleteAccountView.as_view(), name='delete-account'),
    
    # Tasks
    path('tasks/', TaskListView.as_view(), name='task-list'),
    path('tasks/<int:pk>/', TaskDetailView.as_view(), name='task-detail'),
    path('tasks/<int:task_id>/subtasks/', SubTaskView.as_view(), name='subtask-list'),
    path('subtasks/<int:pk>/', SubTaskDetailView.as_view(), name='subtask-detail'),
    path('tasks/history/', TaskHistoryView.as_view(), name='task-history'),
    
    # Reports
    path('reports/monthly/', MonthlyReportView.as_view(), name='monthly-report'),
    path('tasks/high-urgency/', HighUrgencyTasksView.as_view(), name='high-urgency-tasks'),
    
    # Notifications
    path('notifications/', NotificationListView.as_view(), name='notification-list'),
    path('notifications/<int:pk>/read/', MarkNotificationAsReadView.as_view(), name='mark-notification-read'),
]