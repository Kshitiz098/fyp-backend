from rest_framework import serializers
from .models import User, Task, SubTask, Notification
from django.core.validators import EmailValidator
from django.core.exceptions import ValidationError
import bcrypt

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['username', 'full_name', 'email', 'password', 'confirm_password']
    
    def validate_email(self, value):
        validator = EmailValidator()
        try:
            validator(value)
        except ValidationError:
            raise serializers.ValidationError("Invalid email format")
        return value
    
    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords don't match")
        
        if User.objects.filter(username=data['username']).exists():
            raise serializers.ValidationError("Username already exists")
        
        return data
    
    def create(self, validated_data):
        user = User(
            username=validated_data['username'],
            email=validated_data['email'],
            full_name=validated_data['full_name']
        )
        user.set_password(validated_data['password'])
        user.save()
        return user

class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()
    
    def validate(self, data):
        try:
            user = User.objects.get(email=data['email'])
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid email or password")
        
        if not user.check_password(data['password']):
            raise serializers.ValidationError("Invalid email or password")
        
        if not user.email_verified:
            raise serializers.ValidationError("Email not verified. Please verify your email first.")
        
        return {'user': user}

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'full_name', 'email', 'profile_picture']
        read_only_fields = ['id', 'email']

class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = '__all__'
        read_only_fields = ['user', 'created_at', 'updated_at', 'missed']

class SubTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubTask
        fields = '__all__'
        read_only_fields = ['task']
        def validate(self, data):

            if data['deadline'] > data['task'].deadline:
                    raise serializers.ValidationError(
                        "SubTask deadline cannot be after parent Task's deadline"
                    )
            return data

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'
        read_only_fields = ['user', 'created_at', 'read']

class VerificationCodeSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=6)

class EmailUpdateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    
    def validate_email(self, value):
        validator = EmailValidator()
        try:
            validator(value)
        except ValidationError:
            raise serializers.ValidationError("Invalid email format")
        
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already in use")
        
        return value

class PasswordCheckSerializer(serializers.Serializer):
    password = serializers.CharField()