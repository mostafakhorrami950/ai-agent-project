# users_ai/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from .models import (
    CustomUser, UserProfile, HealthRecord, PsychologicalProfile, CareerEducation,
    FinancialInfo, SocialRelationship, PreferenceInterest, EnvironmentalContext,
    RealTimeData, FeedbackLearning, Goal, Habit, AiResponse, UserRole
)

# 1. تعریف فرم‌های سفارشی (اگر دارید، مثل CustomUserChangeForm, CustomUserCreationForm)
class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = CustomUser
        fields = ('phone_number', 'email', 'password', 'is_active', 'is_staff', 'is_superuser',
                  'groups', 'user_permissions', 'last_login', 'date_joined')

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('phone_number', 'email')


# 2. تعریف کلاس‌های ادمین سفارشی (مثل CustomUserAdmin و UserProfileAdmin)
class CustomUserAdmin(BaseUserAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm
    list_display = ('phone_number', 'email', 'first_name_admin', 'last_name_admin', 'is_staff', 'is_active', 'date_joined')
    search_fields = ('phone_number', 'email', 'profile__first_name', 'profile__last_name')
    ordering = ('-date_joined',)
    fieldsets = (
        (None, {'fields': ('phone_number', 'password')}),
        ('اطلاعات شخصی', {'fields': ('email',)}),
        ('دسترسی‌ها', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('تاریخ‌های مهم', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone_number', 'email', 'password', 'password2'),
        }),
    )
    def first_name_admin(self, obj):
        try: return obj.profile.first_name
        except UserProfile.DoesNotExist: return None
    first_name_admin.short_description = 'نام'

    def last_name_admin(self, obj):
        try: return obj.profile.last_name
        except UserProfile.DoesNotExist: return None
    last_name_admin.short_description = 'نام خانوادگی'


class UserProfileAdmin(admin.ModelAdmin): # <--- تعریف کلاس UserProfileAdmin باید اینجا باشه
    list_display = ('user_phone_number', 'first_name', 'last_name', 'role', 'updated_at')
    search_fields = ('user__phone_number', 'first_name', 'last_name', 'role__name')
    list_filter = ('role', 'gender', 'marital_status')
    raw_id_fields = ('user',)
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {'fields': ('user', 'role')}),
        ('اطلاعات شخصی', {'fields': ('first_name', 'last_name', 'age', 'gender', 'nationality', 'location', 'languages', 'cultural_background', 'marital_status')}),
        ('اطلاعات سیستمی و AI', {'fields': ('ai_psychological_test', 'user_information_summary')}),
        ('محدودیت‌های پیام', {'fields': ('messages_sent_today', 'last_message_date')}),
        ('تاریخ‌ها', {'fields': ('created_at', 'updated_at')}),
    )
    def user_phone_number(self, obj):
        return obj.user.phone_number
    user_phone_number.short_description = 'شماره موبایل کاربر'

# ... سایر کلاس‌های ادمین سفارشی اگر دارید ...


# 3. ثبت مدل‌ها با استفاده از کلاس‌های ادمین تعریف شده در بالا
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(UserProfile, UserProfileAdmin) # حالا UserProfileAdmin تعریف شده است
admin.site.register(UserRole) # می‌توانید برای UserRole هم یک کلاس ادمین ساده بسازید
admin.site.register(HealthRecord)
# ... و بقیه مدل‌ها ...
admin.site.register(PsychologicalProfile)
admin.site.register(CareerEducation)
admin.site.register(FinancialInfo)
admin.site.register(SocialRelationship)
admin.site.register(PreferenceInterest)
admin.site.register(EnvironmentalContext)
admin.site.register(RealTimeData)
admin.site.register(FeedbackLearning)
admin.site.register(Goal)
admin.site.register(Habit)
admin.site.register(AiResponse)