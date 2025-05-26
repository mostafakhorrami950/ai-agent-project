# users_ai/views.py
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
# from django.contrib.auth.models import User # این خط رو حذف یا کامنت کنید
from django.contrib.auth import get_user_model # این خط رو اضافه کنید
from django.shortcuts import get_object_or_404
from django.utils import timezone
import uuid
import json
import logging
# import datetime # این ایمپورت در فایل شما بود، اگر لازم نیست می‌توانید حذف کنید
# import requests # این ایمپورت در فایل شما بود، اگر لازم نیست می‌توانید حذف کنید

# Import your models
from .models import (
    UserProfile, HealthRecord, PsychologicalProfile, CareerEducation,
    FinancialInfo, SocialRelationship, PreferenceInterest, EnvironmentalContext,
    RealTimeData, FeedbackLearning, Goal, Habit, AiResponse, UserRole
)
# Import your serializers
from .serializers import (
    UserSerializer, UserProfileSerializer, HealthRecordSerializer, PsychologicalProfileSerializer,
    CareerEducationSerializer, FinancialInfoSerializer, SocialRelationshipSerializer,
    PreferenceInterestSerializer, EnvironmentalContextSerializer, RealTimeDataSerializer,
    FeedbackLearningSerializer, GoalSerializer, HabitSerializer, AiResponseSerializer
)
# Import your Metis AI service
from .metis_ai_service import MetisAIService

logger = logging.getLogger(__name__)
User = get_user_model() # مدل کاربر فعال رو می‌گیریم

# --- Authentication Views ---
class RegisterUserView(generics.CreateAPIView):
    queryset = User.objects.all() # حالا به CustomUser اشاره داره
    serializer_class = UserSerializer # UserSerializer ما آپدیت شده
    permission_classes = [permissions.AllowAny]
    # در UserSerializer متد create برای ساخت UserProfile و اختصاص نقش هم آپدیت شد.

class LoginUserView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        logger.debug(f"Received POST request to LoginUserView: {request.data}")
        # کاربر با شماره موبایل لاگین می‌کنه
        phone_number = request.data.get('phone_number') # تغییر از 'username' به 'phone_number'
        password = request.data.get('password')

        if not phone_number or not password:
            return Response({'detail': 'شماره موبایل و رمز عبور الزامی است.'}, status=status.HTTP_400_BAD_REQUEST)

        # پیدا کردن کاربر بر اساس شماره موبایل
        # get_user_model().USERNAME_FIELD به ما میگه فیلد لاگین چی هست (که ما phone_number تنظیم کردیم)
        # اما برای صراحت بیشتر، مستقیم از phone_number استفاده می‌کنیم.
        user = User.objects.filter(phone_number=phone_number).first()

        if user is None or not user.check_password(password):
            logger.warning(f"Invalid login attempt for phone_number: {phone_number}")
            return Response({'detail': 'شماره موبایل یا رمز عبور نامعتبر است.'}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.is_active:
            logger.warning(f"Login attempt for inactive user: {phone_number}")
            return Response({'detail': 'حساب کاربری شما غیرفعال است.'}, status=status.HTTP_401_UNAUTHORIZED)

        refresh = RefreshToken.for_user(user)
        logger.info(f"User {phone_number} logged in successfully.")
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user_id': user.id, # ارسال user_id هم میتونه مفید باشه
            'phone_number': user.phone_number
        }, status=status.HTTP_200_OK)


# --- Base ViewSets for CRUD operations on user-specific models ---
# این کلاس‌ها نیازی به تغییر ندارند چون از self.request.user استفاده می‌کنند
# و self.request.user حالا یک نمونه از CustomUser خواهد بود.
class UserSpecificOneToOneViewSet(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    # queryset و serializer_class در کلاس‌های فرزند تعریف میشن

    def get_object(self):
        # مطمئن میشیم که queryset در کلاس فرزند تعریف شده باشه
        if not hasattr(self, 'queryset'):
            raise AttributeError("queryset attribute must be set on the child class.")
        return get_object_or_404(self.queryset, user=self.request.user)

    def perform_create(self, serializer): # این متد در RetrieveUpdateDestroyAPIView معمولا استفاده نمیشه مگر اینکه PUT رو به Create تغییر بدیم
        serializer.save(user=self.request.user)

class UserSpecificForeignKeyViewSet(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    # queryset و serializer_class در کلاس‌های فرزند تعریف میشن

    def get_queryset(self):
        if not hasattr(self, 'queryset'):
            raise AttributeError("queryset attribute must be set on the child class.")
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class UserSpecificForeignKeyDetailViewSet(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    # queryset و serializer_class در کلاس‌های فرزند تعریف میشن

    def get_queryset(self):
        if not hasattr(self, 'queryset'):
            raise AttributeError("queryset attribute must be set on the child class.")
        return self.queryset.filter(user=self.request.user)


# --- Model-specific Views ---
# این ویوها هم نیازی به تغییر ندارند، چون از کلاس‌های پایه بالا ارث‌بری می‌کنند.
class UserProfileDetail(UserSpecificOneToOneViewSet):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer

class HealthRecordDetail(UserSpecificOneToOneViewSet):
    queryset = HealthRecord.objects.all()
    serializer_class = HealthRecordSerializer
    # اضافه کردن متد perform_create اگر بخواهیم با POST هم رکورد ساخته بشه
    # def post(self, request, *args, **kwargs):
    #     return self.create(request, *args, **kwargs)


# (به همین ترتیب برای PsychologicalProfileDetail, CareerEducationDetail, FinancialInfoDetail,
# SocialRelationshipDetail, PreferenceInterestDetail, EnvironmentalContextDetail,
# RealTimeDataDetail, FeedbackLearningDetail)
# ... تمام کلاس‌های UserSpecificOneToOneViewSet دیگر ...
class PsychologicalProfileDetail(UserSpecificOneToOneViewSet):
    queryset = PsychologicalProfile.objects.all()
    serializer_class = PsychologicalProfileSerializer

class CareerEducationDetail(UserSpecificOneToOneViewSet):
    queryset = CareerEducation.objects.all()
    serializer_class = CareerEducationSerializer

class FinancialInfoDetail(UserSpecificOneToOneViewSet):
    queryset = FinancialInfo.objects.all()
    serializer_class = FinancialInfoSerializer

class SocialRelationshipDetail(UserSpecificOneToOneViewSet):
    queryset = SocialRelationship.objects.all()
    serializer_class = SocialRelationshipSerializer

class PreferenceInterestDetail(UserSpecificOneToOneViewSet):
    queryset = PreferenceInterest.objects.all()
    serializer_class = PreferenceInterestSerializer

class EnvironmentalContextDetail(UserSpecificOneToOneViewSet):
    queryset = EnvironmentalContext.objects.all()
    serializer_class = EnvironmentalContextSerializer

class RealTimeDataDetail(UserSpecificOneToOneViewSet):
    queryset = RealTimeData.objects.all()
    serializer_class = RealTimeDataSerializer

class FeedbackLearningDetail(UserSpecificOneToOneViewSet):
    queryset = FeedbackLearning.objects.all()
    serializer_class = FeedbackLearningSerializer


# ... GoalListCreate, GoalDetail, HabitListCreate, HabitDetail ...
class GoalListCreate(UserSpecificForeignKeyViewSet):
    queryset = Goal.objects.all()
    serializer_class = GoalSerializer

class GoalDetail(UserSpecificForeignKeyDetailViewSet):
    queryset = Goal.objects.all()
    serializer_class = GoalSerializer

class HabitListCreate(UserSpecificForeignKeyViewSet):
    queryset = Habit.objects.all()
    serializer_class = HabitSerializer

class HabitDetail(UserSpecificForeignKeyDetailViewSet):
    queryset = Habit.objects.all()
    serializer_class = HabitSerializer


# --- AI Agent Chat View with Function Calling ---
class AIAgentChatView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['post'] # فقط متد POST مجاز است

    # ... (متدهای dispatch, _get_active_sessions_for_user, _check_message_limit, _increment_message_count بدون تغییر باقی می‌مانند) ...
    def dispatch(self, request, *args, **kwargs):
        logger.debug(f"Dispatching request to AIAgentChatView: {request.method}, {request.path}")
        return super().dispatch(request, *args, **kwargs)

    def _get_active_sessions_for_user(self, user):
        AiResponse.objects.filter(
            user=user,
            expires_at__lte=timezone.now(),
            is_active=True
        ).update(is_active=False)
        return AiResponse.objects.filter(user=user, is_active=True)

    def _check_message_limit(self, user_profile):
        if not user_profile.role: # اگر کاربر نقشی نداشته باشد، محدودیت اعمال نشود یا یک پیش‌فرض در نظر بگیرید
            logger.warning(f"User {user_profile.user.phone_number} has no role assigned. Skipping pyt limit check.")
            return True # یا False اگر می‌خواهید در این حالت اجازه ارسال پیام ندهید

        now = timezone.localdate()
        if user_profile.last_message_date != now:
            user_profile.messages_sent_today = 0
            user_profile.last_message_date = now
            # user_profile.save() # ذخیره در اینجا می‌تواند باعث write اضافی به دیتابیس در هر اولین پیام روز شود.
                              # بهتر است این ذخیره همراه با increment_message_count انجام شود.

        if user_profile.messages_sent_today >= user_profile.role.daily_message_limit:
            logger.warning(f"User {user_profile.user.phone_number} reached daily message limit ({user_profile.role.daily_message_limit}).")
            return False
        return True

    def _increment_message_count(self, user_profile):
        now = timezone.localdate() # برای اطمینان از اینکه last_message_date هم آپدیت می‌شود
        if user_profile.last_message_date != now:
            user_profile.messages_sent_today = 0
            user_profile.last_message_date = now
        user_profile.messages_sent_today += 1
        user_profile.save(update_fields=['messages_sent_today', 'last_message_date'])


    def _get_user_info_for_metis_api(self, user_profile):
        """Constructs the user dictionary for Metis AI's 'user' field."""
        user_info = {
            "id": str(user_profile.user.id),
            # تغییر user_profile.user.username به user_profile.user.phone_number
            "name": user_profile.user.phone_number, # یا user_profile.first_name اگر ترجیح می‌دهید
        }
        if user_profile.first_name: user_info["first_name"] = user_profile.first_name
        if user_profile.last_name: user_info["last_name"] = user_profile.last_name
        # ... (بقیه فیلدهای این متد بدون تغییر، چون از user_profile یا مدل‌های مرتبط می‌خوانند) ...
        if user_profile.age is not None: user_info["age"] = user_profile.age
        if user_profile.gender: user_info["gender"] = user_profile.gender
        if user_profile.nationality: user_info["nationality"] = user_profile.nationality
        if user_profile.location: user_info["location"] = user_profile.location
        if user_profile.marital_status: user_info["marital_status"] = user_profile.marital_status
        if user_profile.languages: user_info["languages"] = user_profile.languages
        if user_profile.cultural_background: user_info["cultural_background"] = user_profile.cultural_background
        if user_profile.user_information_summary: user_info["summary"] = user_profile.user_information_summary

        try:
            health_record = user_profile.user.health_record
            health_data = {}
            if health_record.chronic_conditions: health_data["chronic_conditions"] = health_record.chronic_conditions
            if health_record.allergies: health_data["allergies"] = health_record.allergies
            if health_record.diet_type: health_data["diet_type"] = health_record.diet_type
            if health_record.medications: health_data["medications"] = health_record.medications
            if health_data: user_info["health_info"] = health_data
        except HealthRecord.DoesNotExist:
            pass
        # ... (بقیه try-except ها برای سایر مدل‌ها) ...
        return user_info

    # متد _get_user_context_for_ai نیازی به تغییر ندارد چون از user_profile و مدل‌های مرتبط می‌خواند.

    def _get_user_context_for_ai(self, user_profile):
        # ... (این متد طولانی است و در فایل شما وجود دارد، بدون تغییر باقی می‌ماند) ...
        # فقط برای اطمینان، هر جا به user.username اشاره شده بود، باید بررسی شود.
        # در کد شما، به نظر نمی‌رسد مستقیما به user.username در اینجا اشاره شده باشد.
        context_parts = []
        user_id = user_profile.user.id # صحیح است

        context_parts.append("### اطلاعات هویتی و پایه‌ای کاربر:")
        # ... (بقیه کد این متد)
        return "این اطلاعات جامع درباره کاربر است..." # و الی آخر


    # --- پیاده سازی توابع ابزار (Tool Functions) ---
    # این بخش بسیار مهم است و باید برای هر ابزاری که در get_tool_schemas_for_metis_bot تعریف کرده‌اید،
    # یک متد مشابه در اینجا پیاده‌سازی کنید.
    # این متدها مسئول ذخیره یا به‌روزرسانی اطلاعات در دیتابیس شما خواهند بود.

    def _call_tool_function(self, user, tool_name, tool_args):
        """یک تابع کمکی برای فراخوانی توابع ابزار بر اساس نام."""
        logger.info(f"User {user.phone_number} calling tool: {tool_name} with args: {tool_args}")
        try:
            # برای هر ابزار باید یک متد جداگانه برای تمیزی بیشتر کد ایجاد شود
            if tool_name == "create_goal":
                return self._tool_create_goal(user, **tool_args)
            elif tool_name == "update_health_record":
                return self._tool_update_health_record(user, **tool_args)
            elif tool_name == "update_psychological_profile":
                return self._tool_update_psychological_profile(user, **tool_args)
            elif tool_name == "update_career_education":
                return self._tool_update_career_education(user, **tool_args)
            elif tool_name == "update_financial_info":
                return self._tool_update_financial_info(user, **tool_args)
            elif tool_name == "update_social_relationship":
                return self._tool_update_social_relationship(user, **tool_args)
            elif tool_name == "update_preference_interest":
                return self._tool_update_preference_interest(user, **tool_args)
            elif tool_name == "update_environmental_context":
                return self._tool_update_environmental_context(user, **tool_args)
            elif tool_name == "update_real_time_data":
                return self._tool_update_real_time_data(user, **tool_args)
            elif tool_name == "update_feedback_learning":
                return self._tool_update_feedback_learning(user, **tool_args)
            elif tool_name == "update_user_profile_details": # ابزار مربوط به UserProfile
                return self._tool_update_user_profile_details(user, **tool_args)
            else:
                logger.error(f"Unknown tool function requested: {tool_name}")
                return f"Error: تابع ابزار '{tool_name}' تعریف نشده است."
        except Exception as e:
            logger.exception(f"Error executing tool {tool_name} for user {user.phone_number}: {e}")
            return f"خطا در اجرای تابع ابزار {tool_name}: {str(e)}"

    # نمونه پیاده‌سازی برای یک تابع ابزار (بقیه باید مشابه این تکمیل شوند)
    def _tool_create_goal(self, user, **kwargs):
        serializer = GoalSerializer(data=kwargs, context={'request': self.request}) # پاس دادن request به context
        if serializer.is_valid():
            serializer.save(user=user) # کاربر رو به صورت دستی پاس میدیم
            return f"هدف با موفقیت برای کاربر {user.phone_number} ذخیره شد: {serializer.data}"
        else:
            logger.error(f"Error creating goal for user {user.phone_number}: {serializer.errors}")
            return f"خطا در ذخیره هدف: {json.dumps(serializer.errors)}"

    def _tool_update_user_profile_details(self, user, **kwargs):
        # این ابزار برای فیلدهایی از UserProfile است که در get_tool_schemas_for_metis_bot تعریف شده
        # مثل ai_psychological_test و user_information_summary
        profile = get_object_or_404(UserProfile, user=user)
        serializer = UserProfileSerializer(profile, data=kwargs, partial=True, context={'request': self.request})
        if serializer.is_valid():
            serializer.save()
            return f"جزئیات پروفایل کاربر {user.phone_number} با موفقیت به‌روز شد: {serializer.data}"
        else:
            logger.error(f"Error updating user profile details for {user.phone_number}: {serializer.errors}")
            return f"خطا در به‌روزرسانی جزئیات پروفایل: {json.dumps(serializer.errors)}"


    # شما باید متدهای مشابه _tool_create_goal و _tool_update_user_profile_details
    # را برای سایر ابزارهای تعریف شده در metis_ai_service.py (مانند update_health_record و ...)
    # در اینجا پیاده‌سازی کنید. این متدها از سریالایزرهای مربوطه برای اعتبارسنجی و ذخیره داده‌ها استفاده می‌کنند.
    # برای مدل‌های OneToOne، ابتدا آبجکت رو get_or_create کنید و سپس آپدیت کنید.

    def _tool_update_health_record(self, user, **kwargs):
        record, created = HealthRecord.objects.get_or_create(user=user)
        serializer = HealthRecordSerializer(record, data=kwargs, partial=True, context={'request': self.request})
        if serializer.is_valid():
            serializer.save()
            return f"اطلاعات سلامتی کاربر {user.phone_number} {'ایجاد' if created else 'به‌روز'} شد."
        return f"خطا در اطلاعات سلامتی: {json.dumps(serializer.errors)}"

    # ... (پیاده‌سازی مشابه برای سایر _tool_update_... methods) ...
    def _tool_update_psychological_profile(self, user, **kwargs):
        record, created = PsychologicalProfile.objects.get_or_create(user=user)
        serializer = PsychologicalProfileSerializer(record, data=kwargs, partial=True, context={'request': self.request})
        if serializer.is_valid(): serializer.save(); return f"پروفایل روانشناختی {'ایجاد' if created else 'به‌روز'} شد."
        return f"خطا در پروفایل روانشناختی: {json.dumps(serializer.errors)}"

    def _tool_update_career_education(self, user, **kwargs):
        record, created = CareerEducation.objects.get_or_create(user=user)
        serializer = CareerEducationSerializer(record, data=kwargs, partial=True, context={'request': self.request})
        if serializer.is_valid(): serializer.save(); return f"اطلاعات شغلی/تحصیلی {'ایجاد' if created else 'به‌روز'} شد."
        return f"خطا در اطلاعات شغلی/تحصیلی: {json.dumps(serializer.errors)}"

    def _tool_update_financial_info(self, user, **kwargs):
        record, created = FinancialInfo.objects.get_or_create(user=user)
        serializer = FinancialInfoSerializer(record, data=kwargs, partial=True, context={'request': self.request})
        if serializer.is_valid(): serializer.save(); return f"اطلاعات مالی {'ایجاد' if created else 'به‌روز'} شد."
        return f"خطا در اطلاعات مالی: {json.dumps(serializer.errors)}"

    def _tool_update_social_relationship(self, user, **kwargs):
        record, created = SocialRelationship.objects.get_or_create(user=user)
        serializer = SocialRelationshipSerializer(record, data=kwargs, partial=True, context={'request': self.request})
        if serializer.is_valid(): serializer.save(); return f"اطلاعات روابط اجتماعی {'ایجاد' if created else 'به‌روز'} شد."
        return f"خطا در اطلاعات روابط اجتماعی: {json.dumps(serializer.errors)}"

    def _tool_update_preference_interest(self, user, **kwargs):
        record, created = PreferenceInterest.objects.get_or_create(user=user)
        serializer = PreferenceInterestSerializer(record, data=kwargs, partial=True, context={'request': self.request})
        if serializer.is_valid(): serializer.save(); return f"ترجیحات و علایق {'ایجاد' if created else 'به‌روز'} شد."
        return f"خطا در ترجیحات و علایق: {json.dumps(serializer.errors)}"

    def _tool_update_environmental_context(self, user, **kwargs):
        record, created = EnvironmentalContext.objects.get_or_create(user=user)
        serializer = EnvironmentalContextSerializer(record, data=kwargs, partial=True, context={'request': self.request})
        if serializer.is_valid(): serializer.save(); return f"زمینه محیطی {'ایجاد' if created else 'به‌روز'} شد."
        return f"خطا در زمینه محیطی: {json.dumps(serializer.errors)}"

    def _tool_update_real_time_data(self, user, **kwargs): # این معمولا باید یک آبجکت جدید بسازد یا آخرین را آپدیت کند
        # اگر RealTimeData باید OneToOne باشد، پس get_or_create مناسب است
        record, created = RealTimeData.objects.get_or_create(user=user)
        # اگر timestamp نباید توسط کاربر ارسال شود، از دیتای kwargs حذف شود
        kwargs.pop('timestamp', None) # timestamp خودکار توسط مدل پر می‌شود
        serializer = RealTimeDataSerializer(record, data=kwargs, partial=True, context={'request': self.request})
        if serializer.is_valid():
            serializer.save()
            return f"داده‌های بلادرنگ {'ایجاد' if created else 'به‌روز'} شد."
        return f"خطا در داده‌های بلادرنگ: {json.dumps(serializer.errors)}"

    def _tool_update_feedback_learning(self, user, **kwargs):
        # مشابه RealTimeData، اگر OneToOne است، get_or_create
        record, created = FeedbackLearning.objects.get_or_create(user=user)
        kwargs.pop('timestamp', None)
        serializer = FeedbackLearningSerializer(record, data=kwargs, partial=True, context={'request': self.request})
        if serializer.is_valid():
            serializer.save()
            return f"بازخورد و یادگیری {'ایجاد' if created else 'به‌روز'} شد."
        return f"خطا در بازخورد و یادگیری: {json.dumps(serializer.errors)}"


    def post(self, request):
        logger.debug(f"AIAgentChatView received POST request. Request data: {request.data}")
        user = request.user # حالا یک نمونه از CustomUser است
        user_profile = get_object_or_404(UserProfile, user=user)
        user_message = request.data.get('message')
        session_id_from_request = request.data.get('session_id')

        if not user_message:
            logger.warning("Message content is missing in request.")
            return Response({'detail': 'محتوای پیام الزامی است.'}, status=status.HTTP_400_BAD_REQUEST)

        if not self._check_message_limit(user_profile): # بررسی محدودیت پیام
            return Response({'detail': 'محدودیت پیام روزانه شما به پایان رسیده است.'},
                            status=status.HTTP_429_TOO_MANY_REQUESTS)

        metis_service = MetisAIService()
        active_sessions = self._get_active_sessions_for_user(user)
        current_session = None

        if session_id_from_request:
            # ... (بقیه منطق پیدا کردن یا ساخت سشن بدون تغییر زیاد) ...
            current_session = active_sessions.filter(ai_session_id=session_id_from_request).first()
            if not current_session:
                logger.warning(f"Provided session ID {session_id_from_request} not found or inactive for user {user.phone_number}.")
                return Response({'detail': 'شناسه جلسه ارائه شده نامعتبر یا غیرفعال است.'},
                                status=status.HTTP_404_NOT_FOUND)
            logger.info(
                f"User {user.phone_number} continuing existing internal session {session_id_from_request} with Metis session {current_session.metis_session_id}.")
        else:
            # ... (منطق بررسی حداکثر سشن‌های فعال) ...
            if user_profile.role and active_sessions.count() >= user_profile.role.max_active_sessions:
                logger.warning(
                    f"User {user.phone_number} reached max active chat sessions ({user_profile.role.max_active_sessions}).")
                return Response({
                    'detail': 'به حداکثر تعداد جلسات گفتگوی فعال رسیده‌اید. لطفاً یک جلسه موجود را ببندید یا طرح خود را ارتقا دهید.'},
                    status=status.HTTP_400_BAD_REQUEST)
            # ... (منطق ساخت سشن جدید با Metis AI) ...
            try:
                internal_session_id = str(uuid.uuid4())
                user_info_for_metis = self._get_user_info_for_metis_api(user_profile)
                initial_messages_for_metis = []
                user_context_prompt = self._get_user_context_for_ai(user_profile)
                if user_context_prompt:
                    initial_messages_for_metis.append({"type": "SYSTEM", "content": user_context_prompt}) # بهتر است به عنوان SYSTEM باشد

                logger.info(
                    f"Attempting to create Metis AI session for bot_id: {metis_service.bot_id} for user {user.phone_number}.")
                metis_ai_session_response = metis_service.create_chat_session(
                    bot_id=metis_service.bot_id,
                    user_data=user_info_for_metis,
                    initial_messages=initial_messages_for_metis
                )
                metis_session_id = metis_ai_session_response.get("id")

                if not metis_session_id:
                    logger.error(f"Metis AI returned no session ID: {metis_ai_session_response} for user {user.phone_number}")
                    raise Exception("Failed to create Metis AI session. No ID returned.")

                current_session = AiResponse.objects.create(
                    user=user,
                    ai_session_id=internal_session_id,
                    metis_session_id=metis_session_id,
                    ai_response_name=f"Chat Session {timezone.now().strftime('%Y-%m-%d %H:%M')}",
                    chat_history=json.dumps([]) # تاریخچه اولیه خالی
                )
                logger.info(
                    f"New internal session {internal_session_id} created for user {user.phone_number} with Metis session {metis_session_id}.")

            except ConnectionError as e:
                # ... (مدیریت خطا) ...
                logger.exception(f"Connection error during Metis AI session creation for user {user.phone_number}: {e}")
                return Response({'detail': f'خطا در اتصال به سرویس AI هنگام ایجاد جلسه: {e}'},
                                status=status.HTTP_503_SERVICE_UNAVAILABLE)

            except Exception as e:
                # ... (مدیریت خطا) ...
                logger.exception(f"Unexpected error during Metis AI session creation for user {user.phone_number}: {e}")
                return Response({'detail': f'خطای پیش‌بینی نشده هنگام ایجاد جلسه AI: {e}'},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)


        try:
            chat_history_list = json.loads(current_session.chat_history) if current_session.chat_history else []

            # اضافه کردن پیام کاربر به تاریخچه (قبل از ارسال به AI)
            # این کار به جلوگیری از ذخیره دوباره پیام کاربر کمک می‌کند اگر قبلاً در طول tool calling ذخیره شده باشد.
            # chat_history_list.append({"role": "user", "content": user_message, "timestamp": str(timezone.now())}) # این خط ممکن است باعث تکرار پیام کاربر در تاریخچه شود اگر tool calling اتفاق بیفتد

            logger.debug(f"Sending user message to Metis AI session {current_session.metis_session_id} for user {user.phone_number}: {user_message}")
            # شامل کردن تاریخچه قبلی در صورت نیاز Metis (بستگی به API Metis دارد)
            # اگر Metis تاریخچه را از پیام‌های قبلی در همان سشن نگه می‌دارد، نیازی به ارسال کل تاریخچه نیست.
            # در کد فعلی، فقط پیام جدید کاربر ارسال می‌شود.
            metis_message_response = metis_service.send_message(
                session_id=current_session.metis_session_id,
                message_content=user_message,
                message_type="USER"
            )
            logger.debug(f"Metis AI raw message response (first call) for user {user.phone_number}: {metis_message_response}")

            ai_content = None
            tool_calls_from_metis = []

            if metis_message_response and 'actions' in metis_message_response and metis_message_response['actions']:
                for action in metis_message_response['actions']:
                    if action.get('type') == 'FUNCTION_CALL':
                        tool_calls_from_metis.append(action['function_call'])

                if tool_calls_from_metis:
                    logger.info(f"Metis AI requested tool calls for user {user.phone_number}: {tool_calls_from_metis}")
                    # اضافه کردن پیام کاربر به تاریخچه (فقط اگر هنوز اضافه نشده)
                    if not chat_history_list or chat_history_list[-1].get("content") != user_message or chat_history_list[-1].get("role") != "user":
                        chat_history_list.append({"role": "user", "content": user_message, "timestamp": str(timezone.now())})

                    chat_history_list.append({"role": "assistant", "content": None, "tool_calls": tool_calls_from_metis, "timestamp": str(timezone.now())})


                    tool_outputs_for_metis = []
                    for tool_call in tool_calls_from_metis:
                        function_name = tool_call.get('name')
                        function_args_str = tool_call.get('args', '{}') # آرگومان‌ها ممکن است رشته JSON باشند
                        try:
                            function_args = json.loads(function_args_str) if isinstance(function_args_str, str) else function_args_str
                        except json.JSONDecodeError:
                            logger.error(f"Failed to parse tool arguments for {function_name}: {function_args_str}")
                            function_args = {}


                        # فراخوانی تابع ابزار داخلی
                        tool_result_content = self._call_tool_function(user, function_name, function_args)

                        tool_outputs_for_metis.append({
                            "tool_call_id": tool_call.get("id"), # Metis ممکن است ID برای هر tool_call برگرداند
                            "tool_name": function_name,
                            "output": tool_result_content
                        })
                        chat_history_list.append({"role": "tool", "tool_call_id": tool_call.get("id"), "name": function_name, "content": tool_result_content, "timestamp": str(timezone.now())})


                    logger.debug(f"Sending tool outputs back to Metis AI for user {user.phone_number}: {tool_outputs_for_metis}")
                    final_metis_response = metis_service.send_message(
                        session_id=current_session.metis_session_id,
                        message_content=json.dumps(tool_outputs_for_metis), # Metis انتظار دارد این یک رشته JSON باشد
                        message_type="TOOL"
                    )
                    ai_content = final_metis_response.get('content', 'پاسخی از AI پس از اجرای ابزار دریافت نشد.')
                else: # اگر actions وجود داشت اما FUNCTION_CALL نبود
                    ai_content = metis_message_response.get('content', 'پاسخ مستقیمی از AI دریافت نشد، اما ابزاری هم فراخوانی نشد.')
            else: # پاسخ عادی بدون tool calling
                ai_content = metis_message_response.get('content', 'پاسخی از AI دریافت نشد.')

            if not ai_content:
                ai_content = "محتوای معتبری از AI دریافت نشد."

            # ذخیره پیام کاربر (اگر قبلا نشده) و پاسخ نهایی AI در تاریخچه داخلی
            if not any(entry.get("content") == user_message and entry.get("role") == "user" for entry in chat_history_list):
                 chat_history_list.append({"role": "user", "content": user_message, "timestamp": str(timezone.now())})
            chat_history_list.append({"role": "assistant", "content": ai_content, "timestamp": str(timezone.now())})

            current_session.chat_history = json.dumps(chat_history_list, ensure_ascii=False) # ensure_ascii=False برای پشتیبانی از فارسی
            current_session.updated_at = timezone.now()
            current_session.save(update_fields=['chat_history', 'updated_at'])

            self._increment_message_count(user_profile) # افزایش شمارنده پیام‌ها

            return Response({
                'ai_response': ai_content,
                'session_id': current_session.ai_session_id,
                'chat_history': chat_history_list # ارسال تاریخچه کامل به کلاینت
            }, status=status.HTTP_200_OK)

        except ConnectionError as e:
            logger.exception(f"Connection error during Metis AI interaction for user {user.phone_number}: {e}")
            return Response({'detail': f'خطا در ارتباط با سرویس AI: {e}'},
                            status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception as e:
            logger.exception(f"An unexpected error occurred during AI interaction for user {user.phone_number}: {e}")
            return Response({'detail': f'خطای پیش‌بینی نشده در طول تعامل با AI: {e}'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# --- کلاس‌های View برای مدیریت سشن‌های چت (AiResponse) ---
class AiChatSessionListCreate(generics.ListCreateAPIView):
    # ... (بدون تغییر)
    queryset = AiResponse.objects.all()
    serializer_class = AiResponseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user, is_active=True).order_by('-created_at')

    def perform_create(self, serializer):
        # ایجاد سشن از طریق AIAgentChatView انجام می‌شود، این متد شاید لازم نباشد مگر اینکه بخواهید دستی سشن بسازید.
        # اگر قرار است از اینجا هم سشن ساخته شود، باید منطق مشابه AIAgentChatView برای اتصال به Metis پیاده‌سازی شود.
        # فعلا آن را غیرفعال می‌کنیم تا از تداخل جلوگیری شود.
        # serializer.save(user=self.request.user)
        logger.warning("Direct creation of AiChatSession via API is generally handled by AIAgentChatView.")
        pass


class AiChatSessionDetail(generics.RetrieveUpdateDestroyAPIView):
    # ... (بدون تغییر)
    queryset = AiResponse.objects.all()
    serializer_class = AiResponseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def perform_destroy(self, instance):
        metis_service = MetisAIService()
        try:
            if instance.metis_session_id:
                logger.info(f"Attempting to delete Metis session {instance.metis_session_id} for user {self.request.user.phone_number}.")
                metis_service.delete_chat_session(instance.metis_session_id)
                logger.info(f"Metis session {instance.metis_session_id} deleted successfully for user {self.request.user.phone_number}.")
        except Exception as e:
            logger.error(f"Failed to delete Metis session {instance.metis_session_id} for user {self.request.user.phone_number}: {e}", exc_info=True)
            # ادامه می‌دهیم تا سشن داخلی حذف شود حتی اگر سشن Metis حذف نشد
        instance.delete()
        logger.info(f"Local AiResponse session {instance.ai_session_id} deleted for user {self.request.user.phone_number}.")

from django.http import JsonResponse
import datetime

class TestTimeView(APIView):
    permission_classes = [permissions.AllowAny] # برای تست راحت‌تر، فعلا بدون احراز هویت
    def get(self, request, *args, **kwargs):
        now = datetime.datetime.now().isoformat()
        logger.info(f"TestTimeView called. Returning current time: {now}")
        return Response({"currentTime": now, "status": "ok"})