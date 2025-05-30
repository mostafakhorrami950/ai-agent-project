# users_ai/models.py
import json
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils import timezone
from django.conf import settings
from datetime import timedelta  # Import timedelta
import uuid  # <--- این خط را اضافه کنید
import logging # <--- این خط را اضافه کنید

from update_metis_functions import logger
logger = logging.getLogger(__name__)

# کلاس مدیریت کاربر سفارشی
class CustomUserManager(BaseUserManager):
    def create_user(self, phone_number, password=None, **extra_fields):
        if not phone_number:
            raise ValueError('The Phone number must be set')
        # Ensure email is handled if provided, but allow it to be None if not part of extra_fields
        email = extra_fields.pop('email', None)
        if email:  # Normalize email only if it's provided
            email = self.normalize_email(email)
            extra_fields['email'] = email  # Add it back if it was popped and normalized

        user = self.model(phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        # Ensure email is provided for superuser if it's in REQUIRED_FIELDS
        if 'email' in self.model.REQUIRED_FIELDS and not extra_fields.get('email'):
            raise ValueError('Superuser must have an email address.')

        return self.create_user(phone_number, password, **extra_fields)


# مدل کاربر سفارشی
class CustomUser(AbstractUser):
    username = None
    phone_number = models.CharField(max_length=15, unique=True, verbose_name='شماره موبایل')
    email = models.EmailField(verbose_name='ایمیل', blank=True, null=True, unique=True)  # unique=True is important

    # first_name and last_name are inherited from AbstractUser
    # We can override them here if we need different max_length or other attributes, but usually not necessary
    # first_name = models.CharField(_('first name'), max_length=150, blank=True)
    # last_name = models.CharField(_('last name'), max_length=150, blank=True)

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['email']  # For createsuperuser command

    objects = CustomUserManager()

    def __str__(self):
        return self.phone_number

    class Meta:
        verbose_name = 'کاربر'
        verbose_name_plural = 'کاربران'


# مدل نقش کاربر
class UserRole(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name='نام نقش')
    description = models.TextField(blank=True, null=True, verbose_name='توضیحات')
    max_active_sessions = models.IntegerField(default=1, verbose_name='حداکثر جلسات فعال')
    session_duration_hours = models.IntegerField(default=24, verbose_name='مدت زمان اعتبار جلسه (ساعت)')
    daily_message_limit = models.IntegerField(default=50, verbose_name='محدودیت پیام روزانه')
    # These psych_test fields might be less relevant with the new dynamic test approach
    psych_test_message_limit = models.IntegerField(default=5, verbose_name='محدودیت پیام تست روانشناسی')
    psych_test_duration_hours = models.IntegerField(default=1, verbose_name='مدت زمان تست روانشناسی (ساعت)')
    # New field for form submission rate limiting
    form_submission_interval_hours = models.IntegerField(default=24,
                                                         help_text="ساعت فاصله زمانی مجاز برای پر کردن مجدد فرم اطلاعات جامع توسط کاربر",
                                                         verbose_name='فاصله ارسال فرم (ساعت)')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'نقش کاربر'
        verbose_name_plural = 'نقش‌های کاربران'


# 1. جدول پروفایل کاربر (اطلاعات پایه کاربر)
class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile',
                                verbose_name='کاربر')
    # first_name and last_name can be fetched from user model directly if you keep them there.
    # If you want to store copies or different versions here, you can keep these fields.
    # For simplicity, let's assume first_name/last_name on CustomUser is primary.
    # first_name = models.CharField(max_length=255, blank=True, null=True, verbose_name='نام')
    # last_name = models.CharField(max_length=255, blank=True, null=True, verbose_name='نام خانوادگی')
    age = models.IntegerField(blank=True, null=True, verbose_name='سن')
    gender = models.CharField(max_length=50, blank=True, null=True, verbose_name='جنسیت')
    nationality = models.CharField(max_length=100, blank=True, null=True, verbose_name='ملیت')
    location = models.CharField(max_length=255, blank=True, null=True, verbose_name='مکان')
    languages = models.TextField(blank=True, null=True,
                                 verbose_name='زبان‌ها')  # Storing as comma-separated string or JSON string
    cultural_background = models.TextField(blank=True, null=True, verbose_name='پیشینه فرهنگی')
    marital_status = models.CharField(max_length=50, blank=True, null=True, verbose_name='وضعیت تأهل')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='زمان ایجاد')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='زمان بروزرسانی')

    ai_psychological_test = models.TextField(blank=True, null=True,
                                             verbose_name='نتیجه تست روانشناسی AI')  # For specific psych tests if any
    user_information_summary = models.TextField(blank=True, null=True, verbose_name='خلاصه اطلاعات کاربر توسط AI')

    role = models.ForeignKey(UserRole, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='نقش کاربر')
    messages_sent_today = models.IntegerField(default=0, verbose_name='پیام‌های ارسالی امروز')
    last_message_date = models.DateField(blank=True, null=True, verbose_name='تاریخ آخرین پیام')

    # Fields for new dynamic test/profile setup flow
    last_form_submission_time = models.DateTimeField(null=True, blank=True,
                                                     help_text="آخرین زمان ارسال فرم اطلاعات جامع",
                                                     verbose_name='آخرین زمان ارسال فرم')
    is_in_profile_setup = models.BooleanField(default=False,
                                              help_text="مشخص می‌کند آیا کاربر در حال حاضر در مرحله تنظیم پروفایل (تست پویا) است یا خیر",
                                              verbose_name='در حال تنظیم پروفایل؟')

    def __str__(self):
        return f"Profile of {self.user.phone_number}"

    class Meta:
        verbose_name = 'پروفایل کاربر'
        verbose_name_plural = 'پروفایل‌های کاربران'


# 2. جدول HealthRecords (سوابق سلامتی)
class HealthRecord(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='health_record',
                                verbose_name='کاربر')
    medical_history = models.TextField(blank=True, null=True, verbose_name='تاریخچه پزشکی')
    chronic_conditions = models.TextField(blank=True, null=True, verbose_name='بیماری‌های مزمن')
    allergies = models.TextField(blank=True, null=True, verbose_name='آلرژی‌ها')
    diet_type = models.CharField(max_length=100, blank=True, null=True, verbose_name='نوع رژیم غذایی')
    daily_calorie_intake = models.IntegerField(blank=True, null=True, verbose_name='کالری دریافتی روزانه')
    physical_activity_level = models.CharField(max_length=50, blank=True, null=True, verbose_name='سطح فعالیت بدنی')
    height = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, verbose_name='قد (سانتی‌متر)')
    weight = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, verbose_name='وزن (کیلوگرم)')
    bmi = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True,
                              verbose_name='شاخص توده بدنی (BMI)')
    mental_health_status = models.TextField(blank=True, null=True, verbose_name='وضعیت سلامت روان')
    sleep_hours = models.DecimalField(max_digits=4, decimal_places=2, blank=True, null=True, verbose_name='ساعات خواب')
    medications = models.TextField(blank=True, null=True, verbose_name='داروهای مصرفی')
    last_checkup_date = models.DateField(blank=True, null=True, verbose_name='تاریخ آخرین چکاپ')

    def __str__(self):
        return f"Health Record of {self.user.phone_number}"

    class Meta:
        verbose_name = 'سابقه سلامت'
        verbose_name_plural = 'سوابق سلامت'


# 3. جدول PsychologicalProfile (پروفایل روانشناختی)
class PsychologicalProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name='psychological_profile', verbose_name='کاربر')
    personality_type = models.CharField(max_length=100, blank=True, null=True, verbose_name='تیپ شخصیتی')
    core_values = models.TextField(blank=True, null=True, verbose_name='ارزش‌های اصلی')
    motivations = models.TextField(blank=True, null=True, verbose_name='انگیزه‌ها')
    decision_making_style = models.CharField(max_length=100, blank=True, null=True, verbose_name='سبک تصمیم‌گیری')
    stress_response = models.TextField(blank=True, null=True, verbose_name='واکنش به استرس')
    emotional_triggers = models.TextField(blank=True, null=True, verbose_name='محرک‌های احساسی')
    preferred_communication = models.CharField(max_length=100, blank=True, null=True, verbose_name='سبک ارتباطی ترجیحی')
    resilience_level = models.CharField(max_length=50, blank=True, null=True, verbose_name='سطح تاب‌آوری')

    def __str__(self):
        return f"Psychological Profile of {self.user.phone_number}"

    class Meta:
        verbose_name = 'پروفایل روانشناختی'
        verbose_name_plural = 'پروفایل‌های روانشناختی'


# 4. جدول CareerEducation (حرفه و تحصیلات)
class CareerEducation(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='career_education',
                                verbose_name='کاربر')
    education_level = models.CharField(max_length=100, blank=True, null=True, verbose_name='سطح تحصیلات')
    field_of_study = models.CharField(max_length=255, blank=True, null=True, verbose_name='رشته تحصیلی')
    skills = models.TextField(blank=True, null=True, verbose_name='مهارت‌ها')
    job_title = models.CharField(max_length=255, blank=True, null=True, verbose_name='عنوان شغلی')
    industry = models.CharField(max_length=255, blank=True, null=True, verbose_name='صنعت')
    job_satisfaction = models.IntegerField(blank=True, null=True, verbose_name='رضایت شغلی (1-10)')
    career_goals = models.TextField(blank=True, null=True, verbose_name='اهداف شغلی')
    work_hours = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True,
                                     verbose_name='ساعات کاری هفتگی')
    learning_style = models.CharField(max_length=100, blank=True, null=True, verbose_name='سبک یادگیری')
    certifications = models.TextField(blank=True, null=True, verbose_name='گواهینامه‌ها')

    def __str__(self):
        return f"Career & Education of {self.user.phone_number}"

    class Meta:
        verbose_name = 'اطلاعات شغلی و تحصیلی'
        verbose_name_plural = 'اطلاعات شغلی و تحصیلی'


# 5. جدول FinancialInfo (اطلاعات مالی)
class FinancialInfo(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='financial_info',
                                verbose_name='کاربر')
    monthly_income = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True,
                                         verbose_name='درآمد ماهانه')
    monthly_expenses = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True,
                                           verbose_name='هزینه‌های ماهانه')
    savings = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, verbose_name='پس‌انداز')
    debts = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, verbose_name='بدهی‌ها')
    investment_types = models.TextField(blank=True, null=True, verbose_name='انواع سرمایه‌گذاری')
    financial_goals = models.TextField(blank=True, null=True, verbose_name='اهداف مالی')
    risk_tolerance = models.CharField(max_length=50, blank=True, null=True, verbose_name='تحمل ریسک')
    budgeting_habits = models.TextField(blank=True, null=True, verbose_name='عادات بودجه‌بندی')

    def __str__(self):
        return f"Financial Info of {self.user.phone_number}"

    class Meta:
        verbose_name = 'اطلاعات مالی'
        verbose_name_plural = 'اطلاعات مالی'


# 6. جدول SocialRelationships (روابط اجتماعی)
class SocialRelationship(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='social_relationship',
                                verbose_name='کاربر')
    key_relationships = models.TextField(blank=True, null=True, verbose_name='روابط کلیدی')
    relationship_status = models.CharField(max_length=100, blank=True, null=True, verbose_name='وضعیت رابطه عاطفی')
    communication_style = models.CharField(max_length=100, blank=True, null=True, verbose_name='سبک ارتباطی')
    emotional_needs = models.TextField(blank=True, null=True, verbose_name='نیازهای عاطفی')
    social_frequency = models.CharField(max_length=50, blank=True, null=True, verbose_name='میزان تعاملات اجتماعی')
    conflict_resolution = models.TextField(blank=True, null=True, verbose_name='روش حل تعارض')

    def __str__(self):
        return f"Social Relationships of {self.user.phone_number}"

    class Meta:
        verbose_name = 'روابط اجتماعی'
        verbose_name_plural = 'روابط اجتماعی'


# 7. جدول PreferencesInterests (ترجیحات و علایق)
class PreferenceInterest(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='preference_interest',
                                verbose_name='کاربر')
    hobbies = models.TextField(blank=True, null=True, verbose_name='سرگرمی‌ها')
    favorite_music_genres = models.TextField(blank=True, null=True, verbose_name='ژانرهای موسیقی موردعلاقه')
    favorite_movies = models.TextField(blank=True, null=True, verbose_name='فیلم‌های موردعلاقه')  # یا ژانرها
    reading_preferences = models.TextField(blank=True, null=True, verbose_name='ترجیحات مطالعه')
    travel_preferences = models.TextField(blank=True, null=True, verbose_name='ترجیحات سفر')
    food_preferences = models.TextField(blank=True, null=True, verbose_name='ترجیحات غذایی')
    lifestyle_choices = models.TextField(blank=True, null=True, verbose_name='انتخاب‌های سبک زندگی')
    movie_fav_choices = models.TextField(blank=True, null=True, verbose_name='فیلم‌های سینمایی مورد علاقه (لیست)')

    def __str__(self):
        return f"Preferences & Interests of {self.user.phone_number}"

    class Meta:
        verbose_name = 'ترجیحات و علایق'
        verbose_name_plural = 'ترجیحات و علایق'


# 8. جدول EnvironmentalContext (زمینه محیطی)
class EnvironmentalContext(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name='environmental_context', verbose_name='کاربر')
    current_city = models.CharField(max_length=255, blank=True, null=True, verbose_name='شهر فعلی')
    climate = models.CharField(max_length=100, blank=True, null=True, verbose_name='آب و هوا')
    housing_type = models.CharField(max_length=100, blank=True, null=True, verbose_name='نوع مسکن')
    tech_access = models.TextField(blank=True, null=True, verbose_name='دسترسی به تکنولوژی')
    life_events = models.TextField(blank=True, null=True, verbose_name='رویدادهای مهم زندگی')
    transportation = models.TextField(blank=True, null=True, verbose_name='روش‌های حمل و نقل')

    def __str__(self):
        return f"Environmental Context of {self.user.phone_number}"

    class Meta:
        verbose_name = 'زمینه محیطی'
        verbose_name_plural = 'زمینه‌های محیطی'


# 9. جدول RealTimeData (داده‌های بلادرنگ)
class RealTimeData(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='real_time_data',
                                verbose_name='کاربر')
    current_location = models.CharField(max_length=255, blank=True, null=True, verbose_name='مکان فعلی')
    current_mood = models.CharField(max_length=100, blank=True, null=True, verbose_name='حال فعلی')
    current_activity = models.CharField(max_length=100, blank=True, null=True, verbose_name='فعالیت فعلی')
    daily_schedule = models.TextField(blank=True, null=True, verbose_name='برنامه روزانه')
    heart_rate = models.IntegerField(blank=True, null=True, verbose_name='ضربان قلب')
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='زمان ثبت')

    def __str__(self):
        return f"Real-Time Data of {self.user.phone_number} at {self.timestamp}"

    class Meta:
        verbose_name = 'داده بلادرنگ'
        verbose_name_plural = 'داده‌های بلادرنگ'


# 10. جدول FeedbackLearning (بازخورد و یادگیری)
class FeedbackLearning(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='feedback_learnings',
                             verbose_name='کاربر')
    feedback_text = models.TextField(blank=True, null=True, verbose_name='متن بازخورد')
    interaction_type = models.CharField(max_length=100, blank=True, null=True, verbose_name='نوع تعامل')
    interaction_rating = models.IntegerField(blank=True, null=True, verbose_name='امتیاز به تعامل')
    # interaction_frequency = models.IntegerField(blank=True, null=True, verbose_name='فرکانس تعامل') # Removed as per earlier diffs
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='زمان ثبت بازخورد')

    def __str__(self):
        return f"Feedback from {self.user.phone_number} on {self.timestamp.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        verbose_name = 'بازخورد و یادگیری'
        verbose_name_plural = 'بازخوردها و یادگیری‌ها'


# 11. جدول Goals (اهداف)
class Goal(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='goals',
                             verbose_name='کاربر')
    goal_type = models.CharField(max_length=100, blank=True, null=True, verbose_name='نوع هدف')
    description = models.TextField(blank=True, null=True, verbose_name='شرح هدف')
    priority = models.IntegerField(blank=True, null=True, verbose_name='اولویت')
    deadline = models.DateField(blank=True, null=True, verbose_name='مهلت')
    progress = models.DecimalField(max_digits=5, decimal_places=2, default=0.0, blank=True, null=True,
                                   verbose_name='درصد پیشرفت')

    def __str__(self):
        return f"Goal for {self.user.phone_number}: {self.description[:50]}"

    class Meta:
        verbose_name = 'هدف'
        verbose_name_plural = 'اهداف'


# 12. جدول Habits (عادات)
class Habit(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='habits',
                             verbose_name='کاربر')
    habit_name = models.CharField(max_length=255, verbose_name='نام عادت')  # Made non-blank
    frequency = models.CharField(max_length=100, blank=True, null=True, verbose_name='فرکانس')
    duration = models.IntegerField(blank=True, null=True, help_text="به دقیقه", verbose_name='مدت زمان (دقیقه)')
    start_date = models.DateField(blank=True, null=True, verbose_name='تاریخ شروع')
    success_rate = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True,
                                       verbose_name='درصد موفقیت')

    def __str__(self):
        return f"Habit for {self.user.phone_number}: {self.habit_name}"

    class Meta:
        verbose_name = 'عادت'
        verbose_name_plural = 'عادات'


class AiResponse(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ai_responses',
                             verbose_name='کاربر')
    ai_session_id = models.CharField(max_length=255, unique=True, null=True, blank=True,
                                     verbose_name='شناسه جلسه داخلی AI')
    metis_session_id = models.CharField(max_length=255, null=True, blank=True, verbose_name='شناسه جلسه متیس')
    ai_response_name = models.CharField(max_length=255, default="New AI Chat Session", verbose_name='نام جلسه AI')
    chat_history = models.TextField(blank=True, null=True, verbose_name='تاریخچه چت (JSON)')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='زمان ایجاد')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='زمان بروزرسانی')
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name='زمان انقضا')
    is_active = models.BooleanField(default=True, verbose_name='فعال است؟')

    def get_chat_history(self):
        if self.chat_history:
            try:
                return json.loads(self.chat_history)
            except json.JSONDecodeError:
                logger.error(f"Failed to decode chat_history for AiResponse ID {self.pk}")
                return []
        return []

    def add_to_chat_history(self, role, content):
        history = self.get_chat_history()
        history.append({
            "role": role,
            "content": content,
            "timestamp": timezone.now().isoformat()
        })
        self.chat_history = json.dumps(history, ensure_ascii=False)
        # self.save() # Defer save to the view to avoid multiple saves per request

    def save(self, *args, **kwargs):
        if not self.ai_session_id:  # Generate an internal session ID if not provided
            self.ai_session_id = str(uuid.uuid4())

        if not self.expires_at and self.user and hasattr(self.user,
                                                         'profile') and self.user.profile and self.user.profile.role:
            duration_hours = self.user.profile.role.session_duration_hours
            if duration_hours:
                self.expires_at = timezone.now() + timedelta(hours=duration_hours)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"AI Chat Session {self.ai_session_id or self.pk} for {self.user.phone_number}"

    class Meta:
        verbose_name = 'جلسه چت AI'
        verbose_name_plural = 'جلسات چت AI'
        ordering = ['-created_at']


class PsychTestHistory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='psych_test_history',
                             verbose_name='کاربر')
    test_name = models.CharField(max_length=255, verbose_name='نام تست')
    test_date = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ انجام تست')
    test_result_summary = models.TextField(blank=True, null=True, verbose_name='خلاصه نتایج تست')
    full_test_data = models.JSONField(blank=True, null=True, verbose_name='داده‌های کامل تست (JSON)')
    ai_analysis = models.TextField(blank=True, null=True, verbose_name='تحلیل AI از نتایج')

    def __str__(self):
        return f"Psych Test '{self.test_name}' for {self.user.phone_number} on {self.test_date.strftime('%Y-%m-%d')}"

    class Meta:
        verbose_name = 'تاریخچه تست روانشناسی'
        verbose_name_plural = 'تاریخچه‌های تست روانشناسی'
        ordering = ['-test_date']