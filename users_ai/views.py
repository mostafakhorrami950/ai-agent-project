# views.py
# users_ai/views.py
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.utils import timezone
import uuid
import json
import logging
import datetime  # این ایمپورت در فایل شما بود، اگر لازم نیست می‌توانید حذف کنید
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
User = get_user_model()


class RegisterUserView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]


class LoginUserView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        logger.debug(f"Received POST request to LoginUserView: {request.data}")
        phone_number = request.data.get('phone_number')
        password = request.data.get('password')

        if not phone_number or not password:
            return Response({'detail': 'شماره موبایل و رمز عبور الزامی است.'}, status=status.HTTP_400_BAD_REQUEST)

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
            'user_id': user.id,
            'phone_number': user.phone_number
        }, status=status.HTTP_200_OK)


class UserSpecificOneToOneViewSet(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        if not hasattr(self, 'queryset'):
            raise AttributeError("queryset attribute must be set on the child class.")
        # For OneToOne fields, we can try to get_or_create the object if we want PUT to also create.
        # However, DRF's RetrieveUpdateDestroyAPIView expects the object to exist for GET/PUT/PATCH/DELETE.
        # If we want PUT/PATCH to create if not exists, we might need to override respective methods.
        # For now, assuming standard behavior: it must exist.
        # The _tool_... methods in AIAgentChatView handle get_or_create.
        return get_object_or_404(self.queryset, user=self.request.user)

    # perform_create is not typically used in RetrieveUpdateDestroyAPIView
    # def perform_create(self, serializer):
    #     serializer.save(user=self.request.user)


class UserSpecificForeignKeyViewSet(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if not hasattr(self, 'queryset'):
            raise AttributeError("queryset attribute must be set on the child class.")
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class UserSpecificForeignKeyDetailViewSet(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if not hasattr(self, 'queryset'):
            raise AttributeError("queryset attribute must be set on the child class.")
        return self.queryset.filter(user=self.request.user)


class UserProfileDetail(UserSpecificOneToOneViewSet):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer


class HealthRecordDetail(UserSpecificOneToOneViewSet):
    queryset = HealthRecord.objects.all()
    serializer_class = HealthRecordSerializer


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


class AIAgentChatView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['post']

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
        if not user_profile.role:
            logger.warning(f"User {user_profile.user.phone_number} has no role assigned. Skipping message limit check.")
            return True

        now = timezone.localdate()
        if user_profile.last_message_date != now:
            user_profile.messages_sent_today = 0
            user_profile.last_message_date = now
            # Save handled by _increment_message_count

        if user_profile.messages_sent_today >= user_profile.role.daily_message_limit:
            logger.warning(
                f"User {user_profile.user.phone_number} reached daily message limit ({user_profile.role.daily_message_limit}).")
            return False
        return True

    def _increment_message_count(self, user_profile):
        now = timezone.localdate()
        if user_profile.last_message_date != now:  # Ensure date is current before incrementing
            user_profile.messages_sent_today = 0
            user_profile.last_message_date = now
        user_profile.messages_sent_today += 1
        user_profile.save(update_fields=['messages_sent_today', 'last_message_date'])

    def _get_user_info_for_metis_api(self, user_profile):
        user_info = {
            "id": str(user_profile.user.id),
            "name": user_profile.user.phone_number,
        }
        if user_profile.first_name: user_info["first_name"] = user_profile.first_name
        if user_profile.last_name: user_info["last_name"] = user_profile.last_name
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
        # Add similar try-except blocks for other related models if needed for user_info
        return user_info

    def _get_user_context_for_ai(self, user_profile):
        # This method aggregates various pieces of user information into a system prompt.
        # You can customize this extensively.
        context_parts = ["اطلاعات کاربر به شرح زیر است:"]
        context_parts.append(f"- شناسه کاربر: {user_profile.user.id}, شماره موبایل: {user_profile.user.phone_number}")
        if user_profile.first_name: context_parts.append(f"- نام: {user_profile.first_name}")
        if user_profile.last_name: context_parts.append(f"- نام خانوادگی: {user_profile.last_name}")
        # ... (add more fields from UserProfile)

        # Example for HealthRecord
        try:
            hr = user_profile.user.health_record
            context_parts.append("\nسوابق سلامتی:")
            if hr.medical_history: context_parts.append(f"- تاریخچه پزشکی: {hr.medical_history}")
            # ... (add more fields from HealthRecord)
        except HealthRecord.DoesNotExist:
            context_parts.append("- سوابق سلامتی ثبت نشده است.")

        # Add other models similarly (PsychologicalProfile, CareerEducation, etc.)

        if user_profile.user_information_summary:
            context_parts.append(f"\nخلاصه جامع کاربر:\n{user_profile.user_information_summary}")

        full_context = "\n".join(context_parts)
        logger.debug(
            f"Generated AI context for user {user_profile.user.phone_number}: {full_context[:500]}...")  # Log snippet
        return full_context

    def _call_tool_function(self, user, tool_name, tool_args):
        logger.info(f"User {user.phone_number} calling tool: {tool_name} with args: {tool_args}")
        try:
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
            elif tool_name == "update_user_profile_details":
                return self._tool_update_user_profile_details(user, **tool_args)
            else:
                logger.error(f"Unknown tool function requested: {tool_name}")
                return {"status": "error", "message": f"تابع ابزار '{tool_name}' تعریف نشده است."}
        except Exception as e:
            logger.exception(f"Error executing tool {tool_name} for user {user.phone_number}: {e}")
            return {"status": "error", "message": f"خطا در اجرای تابع ابزار {tool_name}: {str(e)}"}

    def _tool_create_goal(self, user, **kwargs):
        serializer = GoalSerializer(data=kwargs, context={'request': self.request})
        if serializer.is_valid():
            goal = serializer.save(user=user)
            logger.info(f"Goal created for user {user.phone_number}: {goal.id}")
            return {"status": "success",
                    "message": f"هدف با موفقیت برای کاربر {user.phone_number} ذخیره شد.",
                    "data": serializer.data}
        else:
            logger.error(f"Error creating goal for user {user.phone_number}: {serializer.errors}")
            return {"status": "error", "message": "خطا در ذخیره هدف.", "errors": serializer.errors}

    def _tool_update_user_profile_details(self, user, **kwargs):
        profile = get_object_or_404(UserProfile, user=user)
        serializer = UserProfileSerializer(profile, data=kwargs, partial=True, context={'request': self.request})
        if serializer.is_valid():
            serializer.save()
            logger.info(f"UserProfile details updated for user {user.phone_number}.")
            return {"status": "success",
                    "message": f"جزئیات پروفایل کاربر {user.phone_number} با موفقیت به‌روز شد.",
                    "data": serializer.data}
        else:
            logger.error(f"Error updating user profile details for {user.phone_number}: {serializer.errors}")
            return {"status": "error", "message": "خطا در به‌روزرسانی جزئیات پروفایل.", "errors": serializer.errors}

    def _tool_update_health_record(self, user, **kwargs):
        record, created = HealthRecord.objects.get_or_create(user=user)
        serializer = HealthRecordSerializer(record, data=kwargs, partial=True, context={'request': self.request})
        if serializer.is_valid():
            serializer.save()
            logger.info(f"HealthRecord {'created' if created else 'updated'} for user {user.phone_number}.")
            return {"status": "success",
                    "message": f"اطلاعات سلامتی کاربر {user.phone_number} {'ایجاد' if created else 'به‌روز'} شد.",
                    "data": serializer.data}
        logger.error(f"Error updating HealthRecord for user {user.phone_number}: {serializer.errors}")
        return {"status": "error", "message": "خطا در اطلاعات سلامتی.", "errors": serializer.errors}

    def _tool_update_psychological_profile(self, user, **kwargs):
        record, created = PsychologicalProfile.objects.get_or_create(user=user)
        serializer = PsychologicalProfileSerializer(record, data=kwargs, partial=True,
                                                    context={'request': self.request})
        if serializer.is_valid():
            serializer.save()
            logger.info(f"PsychologicalProfile {'created' if created else 'updated'} for user {user.phone_number}.")
            return {"status": "success",
                    "message": f"پروفایل روانشناختی کاربر {user.phone_number} {'ایجاد' if created else 'به‌روز'} شد.",
                    "data": serializer.data}
        logger.error(f"Error updating PsychologicalProfile for user {user.phone_number}: {serializer.errors}")
        return {"status": "error", "message": "خطا در پروفایل روانشناختی.", "errors": serializer.errors}

    def _tool_update_career_education(self, user, **kwargs):
        record, created = CareerEducation.objects.get_or_create(user=user)
        serializer = CareerEducationSerializer(record, data=kwargs, partial=True, context={'request': self.request})
        if serializer.is_valid():
            serializer.save()
            logger.info(f"CareerEducation {'created' if created else 'updated'} for user {user.phone_number}.")
            return {"status": "success",
                    "message": f"اطلاعات شغلی/تحصیلی کاربر {user.phone_number} {'ایجاد' if created else 'به‌روز'} شد.",
                    "data": serializer.data}
        logger.error(f"Error updating CareerEducation for user {user.phone_number}: {serializer.errors}")
        return {"status": "error", "message": "خطا در اطلاعات شغلی/تحصیلی.", "errors": serializer.errors}

    def _tool_update_financial_info(self, user, **kwargs):
        record, created = FinancialInfo.objects.get_or_create(user=user)
        serializer = FinancialInfoSerializer(record, data=kwargs, partial=True, context={'request': self.request})
        if serializer.is_valid():
            serializer.save()
            logger.info(f"FinancialInfo {'created' if created else 'updated'} for user {user.phone_number}.")
            return {"status": "success",
                    "message": f"اطلاعات مالی کاربر {user.phone_number} {'ایجاد' if created else 'به‌روز'} شد.",
                    "data": serializer.data}
        logger.error(f"Error updating FinancialInfo for user {user.phone_number}: {serializer.errors}")
        return {"status": "error", "message": "خطا در اطلاعات مالی.", "errors": serializer.errors}

    def _tool_update_social_relationship(self, user, **kwargs):
        record, created = SocialRelationship.objects.get_or_create(user=user)
        serializer = SocialRelationshipSerializer(record, data=kwargs, partial=True, context={'request': self.request})
        if serializer.is_valid():
            serializer.save()
            logger.info(f"SocialRelationship {'created' if created else 'updated'} for user {user.phone_number}.")
            return {"status": "success",
                    "message": f"اطلاعات روابط اجتماعی کاربر {user.phone_number} {'ایجاد' if created else 'به‌روز'} شد.",
                    "data": serializer.data}
        logger.error(f"Error updating SocialRelationship for user {user.phone_number}: {serializer.errors}")
        return {"status": "error", "message": "خطا در اطلاعات روابط اجتماعی.", "errors": serializer.errors}

    def _tool_update_preference_interest(self, user, **kwargs):
        record, created = PreferenceInterest.objects.get_or_create(user=user)
        serializer = PreferenceInterestSerializer(record, data=kwargs, partial=True, context={'request': self.request})
        if serializer.is_valid():
            serializer.save()
            logger.info(f"PreferenceInterest {'created' if created else 'updated'} for user {user.phone_number}.")
            return {"status": "success",
                    "message": f"ترجیحات و علایق کاربر {user.phone_number} {'ایجاد' if created else 'به‌روز'} شد.",
                    "data": serializer.data}
        logger.error(f"Error updating PreferenceInterest for user {user.phone_number}: {serializer.errors}")
        return {"status": "error", "message": "خطا در ترجیحات و علایق.", "errors": serializer.errors}

    def _tool_update_environmental_context(self, user, **kwargs):
        record, created = EnvironmentalContext.objects.get_or_create(user=user)
        serializer = EnvironmentalContextSerializer(record, data=kwargs, partial=True,
                                                    context={'request': self.request})
        if serializer.is_valid():
            serializer.save()
            logger.info(f"EnvironmentalContext {'created' if created else 'updated'} for user {user.phone_number}.")
            return {"status": "success",
                    "message": f"زمینه محیطی کاربر {user.phone_number} {'ایجاد' if created else 'به‌روز'} شد.",
                    "data": serializer.data}
        logger.error(f"Error updating EnvironmentalContext for user {user.phone_number}: {serializer.errors}")
        return {"status": "error", "message": "خطا در زمینه محیطی.", "errors": serializer.errors}

    def _tool_update_real_time_data(self, user, **kwargs):
        record, created = RealTimeData.objects.get_or_create(user=user)
        kwargs.pop('timestamp', None)  # timestamp is auto_now_add or managed by model
        serializer = RealTimeDataSerializer(record, data=kwargs, partial=True, context={'request': self.request})
        if serializer.is_valid():
            serializer.save()  # timestamp will be updated if auto_now=True, or use auto_now_add for creation
            logger.info(f"RealTimeData {'created' if created else 'updated'} for user {user.phone_number}.")
            return {"status": "success",
                    "message": f"داده‌های بلادرنگ کاربر {user.phone_number} {'ایجاد' if created else 'به‌روز'} شد.",
                    "data": serializer.data}
        logger.error(f"Error updating RealTimeData for user {user.phone_number}: {serializer.errors}")
        return {"status": "error", "message": "خطا در داده‌های بلادرنگ.", "errors": serializer.errors}

    def _tool_update_feedback_learning(self, user, **kwargs):
        record, created = FeedbackLearning.objects.get_or_create(user=user)
        kwargs.pop('timestamp', None)
        serializer = FeedbackLearningSerializer(record, data=kwargs, partial=True, context={'request': self.request})
        if serializer.is_valid():
            serializer.save()
            logger.info(f"FeedbackLearning {'created' if created else 'updated'} for user {user.phone_number}.")
            return {"status": "success",
                    "message": f"بازخورد و یادگیری کاربر {user.phone_number} {'ایجاد' if created else 'به‌روز'} شد.",
                    "data": serializer.data}
        logger.error(f"Error updating FeedbackLearning for user {user.phone_number}: {serializer.errors}")
        return {"status": "error", "message": "خطا در بازخورد و یادگیری.", "errors": serializer.errors}

    # users_ai/views.py
    def post(self, request):
        user = request.user
        user_profile = get_object_or_404(UserProfile, user=user)
        user_message_content = request.data.get('message')
        session_id_from_request = request.data.get('session_id')
        is_psych_test = request.data.get('is_psych_test', False)

        if not user_message_content:
            return Response({'detail': 'محتوای پیام الزامی است.'}, status=status.HTTP_400_BAD_REQUEST)

        if not self._check_message_limit(user_profile):
            return Response({'detail': 'محدودیت پیام روزانه.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        metis_service = MetisAIService()
        active_sessions = self._get_active_sessions_for_user(user)
        current_session_instance = None

        if is_psych_test:
            message_limit = user_profile.role.psych_test_message_limit
            duration_hours = user_profile.role.psych_test_duration_hours
            session_name = "Psychological Test"
            psych_sessions = active_sessions.filter(ai_response_name=session_name)

            if psych_sessions.exists():
                current_session_instance = psych_sessions.first()
                chat_history = json.loads(
                    current_session_instance.chat_history) if current_session_instance.chat_history else []
                if len([m for m in chat_history if m['role'] == 'user']) >= message_limit:
                    return Response({'detail': 'محدودیت پیام تست روان‌شناسی.'},
                                    status=status.HTTP_429_TOO_MANY_REQUESTS)
            else:
                internal_session_id = str(uuid.uuid4())
                prompt = "تست MBTI: سوالات پویا برای تعیین تیپ شخصیتی (E/I, S/N, T/F, J/P) بپرس و تیپ نهایی را تحلیل کن."
                metis_response = metis_service.create_chat_session(
                    bot_id=metis_service.bot_id,
                    user_data=self._get_user_info_for_metis_api(user_profile),
                    initial_messages=[{"type": "SYSTEM", "content": prompt}]
                )
                current_session_instance = AiResponse.objects.create(
                    user=user,
                    ai_session_id=internal_session_id,
                    metis_session_id=metis_response.get("id"),
                    ai_response_name=session_name,
                    chat_history="[]",
                    expires_at=timezone.now() + timezone.timedelta(hours=duration_hours)
                )
        else:
            # منطق فعلی برای چت معمولی (بدون تغییر)
            if session_id_from_request:
                current_session_instance = active_sessions.filter(ai_session_id=session_id_from_request).first()
                if not current_session_instance:
                    return Response({'detail': 'جلسه نامعتبر.'}, status=status.HTTP_404_NOT_FOUND)
            else:
                if user_profile.role and active_sessions.count() >= user_profile.role.max_active_sessions:
                    return Response({'detail': 'حداکثر جلسات فعال.'}, status=status.HTTP_400_BAD_REQUEST)
                internal_session_id = str(uuid.uuid4())
                metis_response = metis_service.create_chat_session(
                    bot_id=metis_service.bot_id,
                    user_data=self._get_user_info_for_metis_api(user_profile),
                    initial_messages=[{"type": "SYSTEM", "content": self._get_user_context_for_ai(user_profile)}]
                )
                current_session_instance = AiResponse.objects.create(
                    user=user,
                    ai_session_id=internal_session_id,
                    metis_session_id=metis_response.get("id"),
                    ai_response_name=f"Chat Session {timezone.now().strftime('%Y-%m-%d %H:%M')}",
                    chat_history="[]"
                )

        chat_history_list = json.loads(
            current_session_instance.chat_history) if current_session_instance.chat_history else []
        chat_history_list.append({"role": "user", "content": user_message_content, "timestamp": str(timezone.now())})

        metis_response = metis_service.send_message(
            session_id=current_session_instance.metis_session_id,
            message_content=user_message_content,
            message_type="USER"
        )

        ai_response = metis_response.get('content', 'پاسخ نامعتبر از AI.')
        personality_type = None

        if is_psych_test and 'personality_type' in metis_response:
            personality_type = metis_response['personality_type']
            user_profile.ai_psychological_test = json.dumps({
                "responses": chat_history_list,
                "personality_type": personality_type
            }, ensure_ascii=False)
            user_profile.save(update_fields=['ai_psychological_test'])
            current_session_instance.is_active = False
            current_session_instance.save()

        chat_history_list.append({"role": "assistant", "content": ai_response, "timestamp": str(timezone.now())})
        current_session_instance.chat_history = json.dumps(chat_history_list, ensure_ascii=False)
        current_session_instance.save(update_fields=['chat_history', 'updated_at'])

        self._increment_message_count(user_profile)

        return Response({
            'ai_response': ai_response,
            'session_id': current_session_instance.ai_session_id,
            'chat_history': chat_history_list,
            'personality_type': personality_type
        }, status=status.HTTP_200_OK)

from rest_framework.permissions import BasePermission

class IsOwnerOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (request.user.is_superuser or view.get_queryset().filter(user=request.user).exists())

class PsychTestHistoryView(generics.ListAPIView):
    serializer_class = AiResponseSerializer
    permission_classes = [IsOwnerOrAdmin]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return AiResponse.objects.filter(ai_response_name="Psychological Test").select_related('user__profile')
        return AiResponse.objects.filter(user=user, ai_response_name="Psychological Test").select_related('user__profile')

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        response_data = []
        for session in serializer.data:
            user_profile = UserProfile.objects.get(user__id=session['user'])
            psych_test = json.loads(user_profile.ai_psychological_test) if user_profile.ai_psychological_test else {}
            response_data.append({
                'session': session,
                'personality_type': psych_test.get('personality_type', None)
            })
        return Response(response_data)
from rest_framework.exceptions import PermissionDenied
class AiChatSessionListCreate(generics.ListCreateAPIView):
    queryset = AiResponse.objects.all()
    serializer_class = AiResponseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user, is_active=True).order_by('-created_at')

    def perform_create(self, serializer):
        # Creation is handled by AIAgentChatView to ensure Metis session is also created.
        # This endpoint is primarily for listing.
        logger.warning(
            "Direct creation of AiChatSession via API is handled by AIAgentChatView. This endpoint is for listing.")
        # To prevent creation here unless specifically designed for it:
        raise PermissionDenied("Sessions are created via the AI chat endpoint.")


class AiChatSessionDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = AiResponse.objects.all()
    serializer_class = AiResponseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def perform_destroy(self, instance):
        metis_service = MetisAIService()
        try:
            if instance.metis_session_id:
                logger.info(
                    f"Attempting to delete Metis session {instance.metis_session_id} for user {self.request.user.phone_number}.")
                metis_service.delete_chat_session(instance.metis_session_id)
                logger.info(
                    f"Metis session {instance.metis_session_id} deleted successfully for user {self.request.user.phone_number}.")
        except Exception as e:
            logger.error(
                f"Failed to delete Metis session {instance.metis_session_id} for user {self.request.user.phone_number}: {e}",
                exc_info=True)
        instance.delete()  # Delete local session regardless
        logger.info(
            f"Local AiResponse session {instance.ai_session_id} deleted for user {self.request.user.phone_number}.")


class TestTimeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        now = datetime.datetime.now().isoformat()
        logger.info(f"TestTimeView (test-tool-status-minimal) called. Returning current time: {now}")
        return Response({"currentTime": now, "status": "ok", "message": "Test endpoint for Metis tool is working!"})