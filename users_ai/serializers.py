# users_ai/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db import transaction
from .models import (
    UserProfile, HealthRecord, PsychologicalProfile, CareerEducation,
    FinancialInfo, SocialRelationship, PreferenceInterest, EnvironmentalContext,
    RealTimeData, FeedbackLearning, Goal, Habit, AiResponse, UserRole, PsychTestHistory
)

User = get_user_model()


class UserRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserRole
        fields = '__all__'


class UserSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True,
                                   # unique=True را از اینجا بردارید اگر در مدل unique=True است و نمی‌خواهید اینجا اعتبارسنجی شود
                                   # یا مطمئن شوید که مدل CustomUser هم email را unique=True دارد.
                                   )
    first_name = serializers.CharField(required=False, allow_blank=True,
                                       max_length=150)  # max_length مطابق مدل AbstractUser
    last_name = serializers.CharField(required=False, allow_blank=True,
                                      max_length=150)  # max_length مطابق مدل AbstractUser

    class Meta:
        model = User
        fields = ['id', 'phone_number', 'password', 'email', 'first_name', 'last_name']
        extra_kwargs = {
            'password': {'write_only': True, 'style': {'input_type': 'password'}},
            'phone_number': {'required': True},
            # first_name و last_name از CustomUser خوانده می‌شوند
        }

    @transaction.atomic
    def create(self, validated_data):
        # first_name و last_name مستقیما به create_user در CustomUserManager پاس داده می‌شوند
        # اگر در CustomUser تعریف شده باشند.
        user = User.objects.create_user(
            phone_number=validated_data['phone_number'],
            password=validated_data['password'],
            email=validated_data.get('email'),
            first_name=validated_data.get('first_name', ''),  # مقدار پیش‌فرض اگر ارسال نشود
            last_name=validated_data.get('last_name', '')  # مقدار پیش‌فرض اگر ارسال نشود
        )

        default_role_name = 'Free'
        default_role, created = UserRole.objects.get_or_create(
            name=default_role_name,
            defaults={
                'max_active_sessions': 1,
                'session_duration_hours': 24,
                'daily_message_limit': 20,
                'form_submission_interval_hours': 24  # مقدار پیش‌فرض برای فیلد جدید
            }
        )

        # UserProfile دیگر نیازی به first_name و last_name جداگانه ندارد اگر از CustomUser خوانده شوند
        # مگر اینکه بخواهید در UserProfile هم کپی از آنها داشته باشید.
        # با فرض اینکه UserProfile.first_name و UserProfile.last_name حذف شده‌اند یا استفاده نمی‌شوند:
        UserProfile.objects.create(user=user, role=default_role)
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    role = UserRoleSerializer(read_only=True)
    # برای نمایش first_name و last_name از مدل CustomUser
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    phone_number = serializers.CharField(source='user.phone_number', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = UserProfile
        # فیلدهای first_name و last_name که مربوط به UserProfile بودند را از fields حذف می‌کنیم
        # اگر دیگر در مدل UserProfile نیستند.
        # اگر هستند و می‌خواهید آنها را هم سریالایز کنید، نگه دارید.
        # با فرض اینکه نام اصلی در CustomUser است:
        fields = [
            'id', 'user', 'phone_number', 'email', 'first_name', 'last_name',  # از CustomUser
            'age', 'gender', 'nationality', 'location', 'languages',
            'cultural_background', 'marital_status', 'role',
            'messages_sent_today', 'last_message_date',
            'user_information_summary', 'ai_psychological_test',
            'is_in_profile_setup', 'last_form_submission_time',  # فیلدهای جدید
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'user', 'phone_number', 'email', 'first_name', 'last_name',
            'created_at', 'updated_at', 'messages_sent_today',
            'last_message_date', 'last_form_submission_time'  # این فیلد هم معمولا read_only است
        ]
        # اگر فیلدهای first_name و last_name هنوز در مدل UserProfile هستند و می‌خواهید آنها را هم سریالایز کنید:
        # fields = '__all__'
        # read_only_fields = ['user', 'created_at', 'updated_at', 'messages_sent_today', 'last_message_date', 'last_form_submission_time']


class HealthRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthRecord
        fields = '__all__'
        read_only_fields = ['user']


class PsychologicalProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = PsychologicalProfile
        fields = '__all__'
        read_only_fields = ['user']


class CareerEducationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CareerEducation
        fields = '__all__'
        read_only_fields = ['user']


class FinancialInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialInfo
        fields = '__all__'
        read_only_fields = ['user']


class SocialRelationshipSerializer(serializers.ModelSerializer):
    class Meta:
        model = SocialRelationship
        fields = '__all__'
        read_only_fields = ['user']


class PreferenceInterestSerializer(serializers.ModelSerializer):
    class Meta:
        model = PreferenceInterest
        fields = '__all__'
        read_only_fields = ['user']


class EnvironmentalContextSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnvironmentalContext
        fields = '__all__'
        read_only_fields = ['user']


class RealTimeDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = RealTimeData
        fields = '__all__'
        read_only_fields = ['user', 'timestamp']


class FeedbackLearningSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeedbackLearning
        fields = '__all__'
        read_only_fields = ['user', 'timestamp']


class GoalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Goal
        fields = '__all__'
        read_only_fields = ['user']


class HabitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Habit
        fields = '__all__'
        read_only_fields = ['user']


class AiResponseSerializer(serializers.ModelSerializer):
    # نمایش ساده‌تر کاربر (فقط شناسه یا شماره تلفن)
    user = serializers.PrimaryKeyRelatedField(read_only=True)

    # یا: user = serializers.CharField(source='user.phone_number', read_only=True)

    class Meta:
        model = AiResponse
        fields = '__all__'
        read_only_fields = ['user', 'created_at', 'updated_at', 'expires_at', 'is_active', 'ai_session_id',
                            'metis_session_id']


class PsychTestHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PsychTestHistory
        fields = '__all__'
        read_only_fields = ['user', 'test_date']