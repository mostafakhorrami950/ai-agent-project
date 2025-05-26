# users_ai/serializers.py
from rest_framework import serializers
from .models import (
    UserProfile, HealthRecord, PsychologicalProfile, CareerEducation,
    FinancialInfo, SocialRelationship, PreferenceInterest, EnvironmentalContext,
    RealTimeData, FeedbackLearning, Goal, Habit, AiResponse, UserRole,
    # CustomUser # اگر CustomUser رو مستقیم ایمپورت می‌کنید
)
# from django.contrib.auth.models import User # این خط رو حذف یا کامنت کنید
from django.contrib.auth import get_user_model # این خط رو اضافه کنید
from django.db import transaction # برای اطمینان از ساخت پروفایل و نقش

User = get_user_model() # مدل کاربر فعال رو می‌گیریم (که الان CustomUser ماست)


# Serializer برای مدل UserRole (بدون تغییر)
class UserRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserRole
        fields = '__all__'



# Serializer برای مدل CustomUser (به‌روز شده)
class UserSerializer(serializers.ModelSerializer):
    # اگر می‌خواهید ایمیل در زمان ثبت‌نام اختیاری نباشد، required=True رو اضافه کنید
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    class Meta:
        model = User
        # فیلدهایی که از کاربر برای ثبت‌نام دریافت و نمایش داده میشه
        fields = ['id', 'phone_number', 'password', 'email', 'first_name', 'last_name']
        extra_kwargs = {
            'password': {'write_only': True, 'style': {'input_type': 'password'}}, # پسورد فقط برای نوشتن و به صورت مخفی
            'phone_number': {'required': True},
            # first_name و last_name رو هم می‌تونیم موقع ثبت‌نام بگیریم
            'first_name': {'required': False},
            'last_name': {'required': False},

        }

    @transaction.atomic # برای اینکه یا همه عملیات انجام بشه یا هیچکدوم
    def create(self, validated_data):
        # جدا کردن اطلاعات پروفایل از اطلاعات کاربر
        profile_data = {
            'first_name': validated_data.pop('first_name', None),
            'last_name': validated_data.pop('last_name', None)
        }
        # ساخت کاربر با استفاده از متد create_user در CustomUserManager
        user = User.objects.create_user(
            phone_number=validated_data['phone_number'],
            password=validated_data['password'],
            email=validated_data.get('email')
            # بقیه فیلدهای CustomUser که در validated_data هستن (اگر اضافه کرده باشیم)
            # **validated_data # اگر فیلد دیگری در CustomUser برای create_user ارسال نمی‌کنیم، این لازم نیست
        )

        # پیدا کردن یا ساخت نقش پیش‌فرض (مثلاً 'Free')
        # مطمئن شوید که این نقش در دیتابیس وجود داره یا توسط یک سیگنال/مایگریشن اولیه ساخته میشه
        default_role_name = 'Free' # یا هر اسم دیگه‌ای که برای نقش پیش‌فرض در نظر گرفتید
        default_role, created = UserRole.objects.get_or_create(
            name=default_role_name,
            defaults={ # مقادیر پیش‌فرض اگر نقش برای اولین بار ساخته می‌شود
                'max_active_sessions': 1,
                'session_duration_hours': 24,
                'daily_message_limit': 20 # یا هر مقداری که مناسب است
            }
        )

        # ساخت UserProfile برای کاربر جدید و اختصاص نقش
        # فیلدهای first_name و last_name از validated_data به profile_data منتقل شدن
        UserProfile.objects.create(user=user, role=default_role, **profile_data)
        return user

# Serializer برای UserProfile
# Serializer برای UserProfile (بدون تغییر قابل توجه، فقط مطمئن شویم user درست نمایش داده میشه)
class UserProfileSerializer(serializers.ModelSerializer):
    role = UserRoleSerializer(read_only=True) # نمایش جزئیات نقش کاربر
    # اگر اطلاعات کاربر (مثل شماره موبایل) رو هم می‌خواید اینجا نشون بدید:
    # phone_number = serializers.CharField(source='user.phone_number', read_only=True)
    # email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = UserProfile
        fields = '__all__' # یا لیست فیلدهای مورد نظرتون
        read_only_fields = ['user', 'created_at', 'updated_at', 'messages_sent_today', 'last_message_date']
        # 'role' از read_only_fields حذف شد چون در بالا به صورت read_only تعریف شده



# Serializer برای HealthRecord
class HealthRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthRecord
        fields = '__all__'
        read_only_fields = ['user']

# Serializer برای PsychologicalProfile
class PsychologicalProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = PsychologicalProfile
        fields = '__all__'
        read_only_fields = ['user']

# Serializer برای CareerEducation
class CareerEducationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CareerEducation
        fields = '__all__'
        read_only_fields = ['user']

# Serializer برای FinancialInfo
class FinancialInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialInfo
        fields = '__all__'
        read_only_fields = ['user']

# Serializer برای SocialRelationship
class SocialRelationshipSerializer(serializers.ModelSerializer):
    class Meta:
        model = SocialRelationship
        fields = '__all__'
        read_only_fields = ['user']

# Serializer برای PreferenceInterest
class PreferenceInterestSerializer(serializers.ModelSerializer):
    class Meta:
        model = PreferenceInterest
        fields = '__all__'
        read_only_fields = ['user']

# Serializer برای EnvironmentalContext
class EnvironmentalContextSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnvironmentalContext
        fields = '__all__'
        read_only_fields = ['user']

# Serializer برای RealTimeData
class RealTimeDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = RealTimeData
        fields = '__all__'
        read_only_fields = ['user', 'timestamp']

# Serializer برای FeedbackLearning
class FeedbackLearningSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeedbackLearning
        fields = '__all__'
        read_only_fields = ['user', 'timestamp']

# Serializer برای Goal
class GoalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Goal
        fields = '__all__'
        read_only_fields = ['user']

# Serializer برای Habit
class HabitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Habit
        fields = '__all__'
        read_only_fields = ['user']

# Serializer برای AiResponse
class AiResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = AiResponse
        fields = '__all__'
        read_only_fields = ['user', 'created_at', 'updated_at', 'expires_at', 'is_active', 'ai_session_id']
        # ai_session_id فقط خواندنی است چون توسط سیستم مدیریت می‌شود