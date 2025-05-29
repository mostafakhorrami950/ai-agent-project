# users_ai/models.py
import json  # اضافه کردن
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils import timezone
from django.conf import settings


# کلاس مدیریت کاربر سفارشی
class CustomUserManager(BaseUserManager):
    def create_user(self, phone_number, password=None, **extra_fields):
        if not phone_number:
            raise ValueError('The Phone number must be set')
        user = self.model(phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)  # سوپر یوزر باید فعال باشه

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self.create_user(phone_number, password, **extra_fields)


# مدل کاربر سفارشی
class CustomUser(AbstractUser):
    username = None  # ما از شماره موبایل به عنوان نام کاربری استفاده می‌کنیم
    phone_number = models.CharField(max_length=15, unique=True)
    email = models.EmailField(blank=True, null=True)

    # افزودن فیلدهای مربوط به نام و نام خانوادگی به مدل کاربر
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=150, blank=True)

    USERNAME_FIELD = 'phone_number'  # شماره موبایل به عنوان فیلد نام کاربری
    REQUIRED_FIELDS = ['email']  # ایمیل (یا هر فیلد دیگری) که در زمان ساخت کاربر باید وارد شود

    objects = CustomUserManager()

    def __str__(self):
        return self.phone_number


# مدل نقش کاربر
class UserRole(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    max_active_sessions = models.IntegerField(default=1)  # حداکثر تعداد سشن‌های فعال همزمان
    session_duration_hours = models.IntegerField(default=24)  # مدت زمان اعتبار هر سشن چت به ساعت
    daily_message_limit = models.IntegerField(default=50)  # محدودیت پیام در روز
    psych_test_message_limit = models.IntegerField(default=5)  # محدودیت پیام برای تست روانشناسی
    psych_test_duration_hours = models.IntegerField(default=1)  # مدت زمان مجاز برای پاسخ به تست روانشناسی

    def __str__(self):
        return self.name


# 1. جدول Users (اطلاعات پایه کاربر)
class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    first_name = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    age = models.IntegerField(blank=True, null=True)
    gender = models.CharField(max_length=50, blank=True, null=True)
    nationality = models.CharField(max_length=100, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    languages = models.TextField(blank=True, null=True)
    cultural_background = models.TextField(blank=True, null=True)
    marital_status = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    ai_psychological_test = models.TextField(blank=True, null=True)
    user_information_summary = models.TextField(blank=True, null=True)  # خلاصه اطلاعات کاربر

    role = models.ForeignKey(UserRole, on_delete=models.SET_NULL, null=True, blank=True)  # نقش کاربر
    messages_sent_today = models.IntegerField(default=0)  # تعداد پیام‌های ارسالی امروز
    last_message_date = models.DateField(blank=True, null=True)  # آخرین تاریخ ارسال پیام

    def __str__(self):
        return f"Profile of {self.user.phone_number}"


# 2. جدول HealthRecords (سوابق سلامتی)
class HealthRecord(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='health_record')
    medical_history = models.TextField(blank=True, null=True)
    chronic_conditions = models.TextField(blank=True, null=True)
    allergies = models.TextField(blank=True, null=True)
    diet_type = models.CharField(max_length=100, blank=True, null=True)
    daily_calorie_intake = models.IntegerField(blank=True, null=True)
    physical_activity_level = models.CharField(max_length=50, blank=True, null=True)
    height = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    weight = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    bmi = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    mental_health_status = models.TextField(blank=True, null=True)
    sleep_hours = models.DecimalField(max_digits=4, decimal_places=2, blank=True, null=True)
    medications = models.TextField(blank=True, null=True)
    last_checkup_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"Health Record of {self.user.phone_number}"


# 3. جدول PsychologicalProfile (پروفایل روانشناختی)
class PsychologicalProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name='psychological_profile')
    personality_type = models.CharField(max_length=100, blank=True, null=True)
    core_values = models.TextField(blank=True, null=True)
    motivations = models.TextField(blank=True, null=True)
    decision_making_style = models.CharField(max_length=100, blank=True, null=True)
    stress_response = models.TextField(blank=True, null=True)
    emotional_triggers = models.TextField(blank=True, null=True)
    preferred_communication = models.CharField(max_length=100, blank=True, null=True)
    resilience_level = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"Psychological Profile of {self.user.phone_number}"


# 4. جدول CareerEducation (حرفه و تحصیلات)
class CareerEducation(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='career_education')
    education_level = models.CharField(max_length=100, blank=True, null=True)
    field_of_study = models.CharField(max_length=255, blank=True, null=True)
    skills = models.TextField(blank=True, null=True)
    job_title = models.CharField(max_length=255, blank=True, null=True)
    industry = models.CharField(max_length=255, blank=True, null=True)
    job_satisfaction = models.IntegerField(blank=True, null=True)
    career_goals = models.TextField(blank=True, null=True)
    work_hours = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    learning_style = models.CharField(max_length=100, blank=True, null=True)
    certifications = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Career & Education of {self.user.phone_number}"


# 5. جدول FinancialInfo (اطلاعات مالی)
class FinancialInfo(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='financial_info')
    monthly_income = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    monthly_expenses = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    savings = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    debts = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    investment_types = models.TextField(blank=True, null=True)
    financial_goals = models.TextField(blank=True, null=True)
    risk_tolerance = models.CharField(max_length=50, blank=True, null=True)
    budgeting_habits = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Financial Info of {self.user.phone_number}"


# 6. جدول SocialRelationships (روابط اجتماعی)
class SocialRelationship(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='social_relationship')
    key_relationships = models.TextField(blank=True, null=True)
    relationship_status = models.CharField(max_length=100, blank=True, null=True)
    communication_style = models.CharField(max_length=100, blank=True, null=True)
    emotional_needs = models.TextField(blank=True, null=True)
    social_frequency = models.CharField(max_length=50, blank=True, null=True)
    conflict_resolution = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Social Relationships of {self.user.phone_number}"


# 7. جدول PreferencesInterests (ترجیحات و علایق)
class PreferenceInterest(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='preference_interest')
    hobbies = models.TextField(blank=True, null=True)
    favorite_music_genres = models.TextField(blank=True, null=True)
    favorite_movies = models.TextField(blank=True, null=True)
    reading_preferences = models.TextField(blank=True, null=True)
    travel_preferences = models.TextField(blank=True, null=True)
    food_preferences = models.TextField(blank=True, null=True)
    lifestyle_choices = models.TextField(blank=True, null=True)
    movie_fav_choices = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Preferences & Interests of {self.user.phone_number}"


# 8. جدول EnvironmentalContext (زمینه محیطی)
class EnvironmentalContext(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name='environmental_context')
    current_city = models.CharField(max_length=255, blank=True, null=True)
    climate = models.CharField(max_length=100, blank=True, null=True)
    housing_type = models.CharField(max_length=100, blank=True, null=True)
    tech_access = models.TextField(blank=True, null=True)
    life_events = models.TextField(blank=True, null=True)
    transportation = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Environmental Context of {self.user.phone_number}"


# 9. جدول RealTimeData (داده‌های بلادرنگ)
class RealTimeData(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='real_time_data')
    current_location = models.CharField(max_length=255, blank=True, null=True)
    current_mood = models.CharField(max_length=100, blank=True, null=True)
    current_activity = models.CharField(max_length=100, blank=True, null=True)
    daily_schedule = models.TextField(blank=True, null=True)
    heart_rate = models.IntegerField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Real-Time Data of {self.user.phone_number}"


# 10. جدول FeedbackLearning (بازخورد و یادگیری)
class FeedbackLearning(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='feedback_learnings')
    feedback_text = models.TextField(blank=True, null=True)
    interaction_type = models.CharField(max_length=100, blank=True, null=True)
    interaction_rating = models.IntegerField(blank=True, null=True)
    interaction_frequency = models.IntegerField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback from {self.user.phone_number} on {self.timestamp.strftime('%Y-%m-%d %H:%M')}"


# 11. جدول Goals (اهداف)
class Goal(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='goals')
    goal_type = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    priority = models.IntegerField(blank=True, null=True)
    deadline = models.DateField(blank=True, null=True)
    progress = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)

    def __str__(self):
        return f"Goal for {self.user.phone_number}: {self.description}"


# 12. جدول Habits (عادات)
class Habit(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='habits')
    habit_name = models.CharField(max_length=255, blank=True, null=True)
    frequency = models.CharField(max_length=100, blank=True, null=True)
    duration = models.IntegerField(blank=True, null=True)
    start_date = models.DateField(blank=True, null=True)
    success_rate = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)

    def __str__(self):
        return f"Habit for {self.user.phone_number}: {self.habit_name}"


class AiResponse(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='ai_responses')  # تغییر کرد
    ai_session_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    metis_session_id = models.CharField(max_length=255, null=True, blank=True)
    ai_response_name = models.CharField(max_length=255, default="New AI Chat Session")
    chat_history = models.TextField(blank=True, null=True)  # Store as JSON string
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def get_chat_history(self):
        if self.chat_history:
            try:
                return json.loads(self.chat_history)
            except json.JSONDecodeError:
                return []
        return []

    def add_to_chat_history(self, role, content):
        history = self.get_chat_history()
        history.append({
            "role": role,
            "content": content,
            "timestamp": timezone.now().isoformat()
        })
        self.chat_history = json.dumps(history, ensure_ascii=False)  # مطمئن شوید که یونیکدها ذخیره می‌شوند
        self.save()  # این save باعث میشه که تاریخچه بلافاصله در دیتابیس ذخیره بشه. در view باید save نهایی را انجام دهید یا این را بردارید

    def save(self, *args, **kwargs):
        if not self.expires_at and self.user and hasattr(self.user,
                                                         'profile') and self.user.profile and self.user.profile.role:  # اضافه کردن بررسی hasattr
            duration = self.user.profile.role.session_duration_hours
            if duration:
                self.expires_at = timezone.now() + timezone.timedelta(hours=duration)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"AI Chat Session {self.pk} for {self.user.phone_number}"


# 13. جدول Ai_response پاسخ های هوش مصنوعی به هر کاربر
class PsychTestHistory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='psych_test_history')
    test_name = models.CharField(max_length=255)
    test_date = models.DateTimeField(auto_now_add=True)
    test_result_summary = models.TextField()  # خلاصه نتایج تست
    full_test_data = models.JSONField(blank=True, null=True)  # داده‌های کامل تست (مثلاً سوالات و پاسخ‌ها)
    ai_analysis = models.TextField(blank=True, null=True)  # تحلیل AI از نتایج تست

    def __str__(self):
        return f"Psych Test for {self.user.phone_number} on {self.test_date.strftime('%Y-%m-%d')}"