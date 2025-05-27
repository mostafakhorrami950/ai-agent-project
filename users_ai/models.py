# models.py
# users_ai/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils import timezone
from django.conf import settings # این خط رو اضافه کن

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
        extra_fields.setdefault('is_active', True) # سوپر یوزر باید فعال باشه

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self.create_user(phone_number, password, **extra_fields)

# مدل کاربر سفارشی
class CustomUser(AbstractUser):
    username = None # ما از شماره موبایل به عنوان نام کاربری استفاده می‌کنیم
    phone_number = models.CharField(max_length=15, unique=True, verbose_name='شماره موبایل')
    # میتونی فیلدهای دیگه مثل ایمیل (اختیاری) هم اینجا اضافه کنی
    email = models.EmailField(verbose_name='ایمیل', unique=True, null=True, blank=True)
    # is_active به طور پیش‌فرض در AbstractUser هست و True است.
    # date_joined (created_at) و last_login (updated_at) هم در AbstractUser هستند.

    USERNAME_FIELD = 'phone_number' # فیلد مورد استفاده برای لاگین
    REQUIRED_FIELDS = [] # فیلدهایی که موقع createsuperuser پرسیده میشه (به جز پسورد و USERNAME_FIELD)

    objects = CustomUserManager()

    def __str__(self):
        return self.phone_number

    class Meta:
        verbose_name = 'کاربر'
        verbose_name_plural = 'کاربران'

# حالا باید تمام مدل‌هایی که به User پیش‌فرض لینک بودن رو آپدیت کنیم
# تا به CustomUser ما (settings.AUTH_USER_MODEL) اشاره کنن.

class UserRole(models.Model):
    # ... (بدون تغییر) ...
    name = models.CharField(max_length=50, unique=True) # مثال: VIP, Pro, Admin, Free
    max_active_sessions = models.IntegerField(default=1) # حداکثر تعداد گفتگوهای همزمان
    session_duration_hours = models.IntegerField(default=24) # مدت زمان فعال بودن هر گفتگو (ساعت)
    daily_message_limit = models.IntegerField(default=50) # محدودیت پیام روزانه (اگر لازم باشد)

    def __str__(self):
        return self.name

class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile') # تغییر کرد
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    # ... (بقیه فیلدهای UserProfile بدون تغییر در تعریف، فقط user آپدیت شد) ...
    age = models.IntegerField(blank=True, null=True)
    gender = models.CharField(max_length=50, blank=True, null=True)
    nationality = models.CharField(max_length=100, blank=True, null=True)
    location = models.CharField(max_length=200, blank=True, null=True)
    languages = models.TextField(blank=True, null=True)
    cultural_background = models.TextField(blank=True, null=True)
    marital_status = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    ai_psychological_test = models.TextField(blank=True, null=True)
    user_information_summary = models.TextField(blank=True, null=True)
    role = models.ForeignKey(UserRole, on_delete=models.SET_NULL, null=True, blank=True, default=None)
    messages_sent_today = models.IntegerField(default=0)
    last_message_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"Profile of {self.user.phone_number}" # یا هر فیلد دیگری از CustomUser

class HealthRecord(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='health_record') # تغییر کرد
    # ... (بقیه فیلدها بدون تغییر) ...
    medical_history = models.TextField(blank=True, null=True)
    chronic_conditions = models.TextField(blank=True, null=True)
    allergies = models.TextField(blank=True, null=True)
    diet_type = models.CharField(max_length=100, blank=True, null=True)
    daily_calorie_intake = models.IntegerField(blank=True, null=True)
    physical_activity_level = models.CharField(max_length=50, blank=True, null=True)
    height = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True) # e.g., 180.50
    weight = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True) # e.g., 75.25
    bmi = models.DecimalField(max_digits=4, decimal_places=2, blank=True, null=True)
    mental_health_status = models.TextField(blank=True, null=True)
    sleep_hours = models.DecimalField(max_digits=4, decimal_places=2, blank=True, null=True)
    medications = models.TextField(blank=True, null=True)
    last_checkup_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"Health Record for {self.user.phone_number}"

class PsychologicalProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='psych_profile') # تغییر کرد
    # ... (بقیه فیلدها بدون تغییر) ...
    personality_type = models.CharField(max_length=100, blank=True, null=True)
    core_values = models.TextField(blank=True, null=True)
    motivations = models.TextField(blank=True, null=True)
    decision_making_style = models.CharField(max_length=100, blank=True, null=True)
    stress_response = models.TextField(blank=True, null=True)
    emotional_triggers = models.TextField(blank=True, null=True)
    preferred_communication = models.CharField(max_length=100, blank=True, null=True)
    resilience_level = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"Psychological Profile for {self.user.phone_number}"


class CareerEducation(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='career_education') # تغییر کرد
    # ... (بقیه فیلدها بدون تغییر) ...
    education_level = models.CharField(max_length=100, blank=True, null=True)
    field_of_study = models.CharField(max_length=200, blank=True, null=True)
    skills = models.TextField(blank=True, null=True)
    job_title = models.CharField(max_length=200, blank=True, null=True)
    industry = models.CharField(max_length=100, blank=True, null=True)
    job_satisfaction = models.IntegerField(blank=True, null=True) # 1 to 10
    career_goals = models.TextField(blank=True, null=True)
    work_hours = models.DecimalField(max_digits=4, decimal_places=2, blank=True, null=True)
    learning_style = models.CharField(max_length=100, blank=True, null=True)
    certifications = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Career & Education for {self.user.phone_number}"

class FinancialInfo(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='financial_info') # تغییر کرد
    # ... (بقیه فیلدها بدون تغییر) ...
    monthly_income = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    monthly_expenses = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    savings = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    debts = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    investment_types = models.TextField(blank=True, null=True)
    financial_goals = models.TextField(blank=True, null=True)
    risk_tolerance = models.CharField(max_length=50, blank=True, null=True)
    budgeting_habits = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Financial Info for {self.user.phone_number}"

class SocialRelationship(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='social_relationship') # تغییر کرد
    # ... (بقیه فیلدها بدون تغییر) ...
    key_relationships = models.TextField(blank=True, null=True)
    relationship_status = models.CharField(max_length=50, blank=True, null=True)
    communication_style = models.CharField(max_length=100, blank=True, null=True)
    emotional_needs = models.TextField(blank=True, null=True)
    social_frequency = models.CharField(max_length=50, blank=True, null=True)
    conflict_resolution = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Social Relationships for {self.user.phone_number}"

class PreferenceInterest(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='preferences_interests') # تغییر کرد
    # ... (بقیه فیلدها بدون تغییر) ...
    hobbies = models.TextField(blank=True, null=True)
    favorite_music_genres = models.TextField(blank=True, null=True)
    favorite_movies = models.TextField(blank=True, null=True)
    reading_preferences = models.TextField(blank=True, null=True)
    travel_preferences = models.TextField(blank=True, null=True)
    food_preferences = models.TextField(blank=True, null=True)
    lifestyle_choices = models.TextField(blank=True, null=True)
    movie_fav_choices = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Preferences & Interests for {self.user.phone_number}"

class EnvironmentalContext(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='environmental_context') # تغییر کرد
    # ... (بقیه فیلدها بدون تغییر) ...
    current_city = models.CharField(max_length=200, blank=True, null=True)
    climate = models.CharField(max_length=100, blank=True, null=True)
    housing_type = models.CharField(max_length=100, blank=True, null=True)
    tech_access = models.TextField(blank=True, null=True)
    life_events = models.TextField(blank=True, null=True)
    transportation = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Environmental Context for {self.user.phone_number}"

class RealTimeData(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='realtime_data') # تغییر کرد
    # ... (بقیه فیلدها بدون تغییر) ...
    current_location = models.CharField(max_length=255, blank=True, null=True)
    current_mood = models.CharField(max_length=100, blank=True, null=True)
    current_activity = models.CharField(max_length=100, blank=True, null=True)
    daily_schedule = models.TextField(blank=True, null=True)
    heart_rate = models.IntegerField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Real-Time Data for {self.user.phone_number} at {self.timestamp}"

class FeedbackLearning(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='feedback_learning') # تغییر کرد
    # ... (بقیه فیلدها بدون تغییر) ...
    feedback_text = models.TextField(blank=True, null=True)
    interaction_type = models.CharField(max_length=100, blank=True, null=True)
    interaction_rating = models.IntegerField(blank=True, null=True) # 1 to 5
    interaction_frequency = models.IntegerField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback for {self.user.phone_number} on {self.timestamp}"

class Goal(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='goals') # تغییر کرد
    # ... (بقیه فیلدها بدون تغییر) ...
    goal_type = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    priority = models.IntegerField(blank=True, null=True) # 1 to 5
    deadline = models.DateField(blank=True, null=True)
    progress = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)

    def __str__(self):
        return f"Goal for {self.user.phone_number}: {self.description[:50]}..."

class Habit(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='habits') # تغییر کرد
    # ... (بقیه فیلدها بدون تغییر) ...
    habit_name = models.CharField(max_length=200)
    frequency = models.CharField(max_length=100, blank=True, null=True)
    duration = models.IntegerField(blank=True, null=True) # in minutes
    start_date = models.DateField(blank=True, null=True)
    success_rate = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)

    def __str__(self):
        return f"Habit for {self.user.phone_number}: {self.habit_name}"

class AiResponse(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ai_responses') # تغییر کرد
    # ... (بقیه فیلدها بدون تغییر) ...
    ai_session_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    metis_session_id = models.CharField(max_length=255, null=True, blank=True)
    ai_response_name = models.CharField(max_length=255, default="New AI Chat Session")
    chat_history = models.TextField(blank=True, null=True) # Store as JSON string
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)


    def save(self, *args, **kwargs):
        if not self.expires_at and self.user and hasattr(self.user, 'profile') and self.user.profile and self.user.profile.role: # اضافه کردن بررسی hasattr
            duration = self.user.profile.role.session_duration_hours
            self.expires_at = timezone.now() + timezone.timedelta(hours=duration)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"AI Chat for {self.user.phone_number} - {self.ai_response_name} (Metis Session ID: {self.metis_session_id})"

    class Meta:
        ordering = ['-created_at']