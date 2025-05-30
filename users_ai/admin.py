# users_ai/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from .models import (
    CustomUser, UserProfile, HealthRecord, PsychologicalProfile, CareerEducation,
    FinancialInfo, SocialRelationship, PreferenceInterest, EnvironmentalContext,
    RealTimeData, FeedbackLearning, Goal, Habit, AiResponse, UserRole, PsychTestHistory  # PsychTestHistory اضافه شد
)


# 1. تعریف فرم‌های سفارشی
class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = CustomUser
        # فیلدها را می‌توان بر اساس نیاز تنظیم کرد
        fields = (
        'phone_number', 'email', 'first_name', 'last_name', 'password', 'is_active', 'is_staff', 'is_superuser',
        'groups', 'user_permissions', 'last_login', 'date_joined')


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = (
        'phone_number', 'email', 'first_name', 'last_name')  # اضافه کردن first_name و last_name به فرم ساخت کاربر


# 2. تعریف کلاس‌های ادمین سفارشی
class CustomUserAdmin(BaseUserAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm
    list_display = ('phone_number', 'email', 'first_name', 'last_name', 'is_staff', 'is_active',
                    'date_joined')  # استفاده مستقیم از فیلدهای first_name و last_name مدل CustomUser
    search_fields = ('phone_number', 'email', 'first_name', 'last_name')  # جستجو بر اساس فیلدهای مستقیم مدل
    ordering = ('-date_joined',)
    fieldsets = (
        (None, {'fields': ('phone_number', 'password')}),
        ('اطلاعات شخصی', {'fields': ('first_name', 'last_name', 'email')}),  # first_name و last_name اضافه شد
        ('دسترسی‌ها', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('تاریخ‌های مهم', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone_number', 'email', 'first_name', 'last_name', 'password', 'password2'),
            # first_name و last_name اضافه شد
        }),
    )
    # توابع first_name_admin و last_name_admin دیگر لازم نیستند چون فیلدها مستقیم به CustomUser اضافه شدند


class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user_phone_number', 'get_user_first_name', 'get_user_last_name', 'role', 'is_in_profile_setup',
                    'last_form_submission_time', 'updated_at')
    search_fields = (
    'user__phone_number', 'user__first_name', 'user__last_name', 'role__name')  # جستجو بر اساس فیلدهای CustomUser
    list_filter = ('role', 'gender', 'marital_status', 'is_in_profile_setup')
    raw_id_fields = ('user',)
    readonly_fields = (
    'created_at', 'updated_at', 'last_form_submission_time')  # last_form_submission_time معمولا توسط سیستم پر می‌شود

    fieldsets = (
        (None, {'fields': ('user', 'role')}),
        # فیلدهای first_name و last_name از اینجا حذف شدند چون در CustomUser مدیریت می‌شوند و اینجا افزونگی است.
        # اگر می‌خواهید در UserProfile هم کپی داشته باشید، می‌توانید نگه دارید.
        # برای سادگی، فرض می‌کنیم نام و نام خانوادگی اصلی در CustomUser است.
        ('اطلاعات شخصی تکمیلی', {'fields': (
        'age', 'gender', 'nationality', 'location', 'languages', 'cultural_background', 'marital_status')}),
        ('وضعیت تنظیم پروفایل', {'fields': ('is_in_profile_setup', 'last_form_submission_time')}),
        ('اطلاعات سیستمی و AI', {'fields': ('ai_psychological_test', 'user_information_summary')}),
        ('محدودیت‌های پیام', {'fields': ('messages_sent_today', 'last_message_date')}),
        ('تاریخ‌ها', {'fields': ('created_at', 'updated_at')}),
    )

    def user_phone_number(self, obj):
        return obj.user.phone_number

    user_phone_number.short_description = 'شماره موبایل کاربر'

    def get_user_first_name(self, obj):
        return obj.user.first_name

    get_user_first_name.short_description = 'نام کاربر'
    get_user_first_name.admin_order_field = 'user__first_name'

    def get_user_last_name(self, obj):
        return obj.user.last_name

    get_user_last_name.short_description = 'نام خانوادگی کاربر'
    get_user_last_name.admin_order_field = 'user__last_name'


class UserRoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'max_active_sessions', 'session_duration_hours', 'daily_message_limit',
                    'form_submission_interval_hours', 'psych_test_message_limit', 'psych_test_duration_hours')
    search_fields = ('name',)
    # افزودن form_submission_interval_hours به fieldsets اگر می‌خواهید در فرم ویرایش مستقیم قابل تنظیم باشد
    fieldsets = (
        (None, {'fields': ('name', 'description')}),
        ('محدودیت‌های جلسه و پیام',
         {'fields': ('max_active_sessions', 'session_duration_hours', 'daily_message_limit')}),
        ('محدودیت‌های تست و فرم',
         {'fields': ('form_submission_interval_hours', 'psych_test_message_limit', 'psych_test_duration_hours')}),
    )


class AiResponseAdmin(admin.ModelAdmin):
    list_display = (
    'user', 'ai_session_id', 'metis_session_id', 'ai_response_name', 'is_active', 'created_at', 'expires_at')
    search_fields = ('user__phone_number', 'ai_session_id', 'metis_session_id', 'ai_response_name')
    list_filter = ('is_active', 'created_at', 'expires_at')
    readonly_fields = ('created_at', 'updated_at', 'expires_at', 'chat_history_display')
    raw_id_fields = ('user',)

    fieldsets = (
        (None, {'fields': ('user', 'ai_response_name', 'is_active')}),
        ('شناسه‌های جلسه', {'fields': ('ai_session_id', 'metis_session_id')}),
        ('تاریخ‌ها', {'fields': ('created_at', 'updated_at', 'expires_at')}),
        ('تاریخچه چت', {'fields': ('chat_history_display',)}),
    )

    def chat_history_display(self, obj):
        # نمایش بخشی از تاریخچه برای خوانایی بهتر در ادمین
        history = obj.get_chat_history()
        if history:
            return json.dumps(history[-3:], indent=2, ensure_ascii=False)  # نمایش ۳ پیام آخر
        return "تاریخچه خالی است."

    chat_history_display.short_description = 'بخشی از تاریخچه چت'


class PsychTestHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'test_name', 'test_date', 'short_summary')
    search_fields = ('user__phone_number', 'test_name')
    list_filter = ('test_date', 'test_name')
    raw_id_fields = ('user',)
    readonly_fields = ('test_date',)

    def short_summary(self, obj):
        if obj.test_result_summary and len(obj.test_result_summary) > 100:
            return obj.test_result_summary[:100] + "..."
        return obj.test_result_summary

    short_summary.short_description = 'خلاصه نتایج (کوتاه)'


# 3. ثبت مدل‌ها
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(UserRole, UserRoleAdmin)  # استفاده از UserRoleAdmin تعریف شده
admin.site.register(HealthRecord)
admin.site.register(PsychologicalProfile)
admin.site.register(CareerEducation)
admin.site.register(FinancialInfo)
admin.site.register(SocialRelationship)
admin.site.register(PreferenceInterest)
admin.site.register(EnvironmentalContext)
admin.site.register(RealTimeData)
admin.site.register(FeedbackLearning)  # می‌توانید برای این هم کلاس ادمین تعریف کنید
admin.site.register(Goal)  # می‌توانید برای این هم کلاس ادمین تعریف کنید
admin.site.register(Habit)  # می‌توانید برای این هم کلاس ادمین تعریف کنید
admin.site.register(AiResponse, AiResponseAdmin)
admin.site.register(PsychTestHistory, PsychTestHistoryAdmin)