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

    def post(self, request):
        logger.debug(f"AIAgentChatView received POST request. Request data: {request.data}")
        user = request.user
        user_profile = get_object_or_404(UserProfile, user=user)
        user_message_content = request.data.get('message')
        session_id_from_request = request.data.get('session_id')
        is_psych_test = request.data.get('is_psych_test', False)
        if is_psych_test:
            message_limit = user_profile.role.psych_test_message_limit
            duration_hours = user_profile.role.psych_test_duration_hours
            session_name = "Psychological Test"
            psych_sessions = active_sessions.filter(ai_response_name=session_name)
            if psych_sessions.exists():
                session = psych_sessions.first()
                chat_history = json.loads(session.chat_history) if session.chat_history else []
                if len([m for m in chat_history if m['role'] == 'user']) >= message_limit:
                    return Response({'detail': 'محدودیت پیام تست روان‌شناسی.'}, status=429)
            else:
                internal_session_id = str(uuid.uuid4())
                prompt = "تست MBTI: سوالات پویا برای تعیین تیپ شخصیتی بپرس و تحلیل کن."
                metis_response = metis_service.create_chat_session(
                    bot_id=metis_service.bot_id,
                    user_data=self._get_user_info_for_metis_api(user_profile),
                    initial_messages=[{"type": "SYSTEM", "content": prompt}]
                )
                session = AiResponse.objects.create(
                    user=user,
                    ai_session_id=internal_session_id,
                    metis_session_id=metis_response.get("id"),
                    ai_response_name=session_name,
                    chat_history="[]",
                    expires_at=timezone.now() + timezone.timedelta(hours=duration_hours)
                )

        if is_psych_test and 'personality_type' in metis_message_response:
            user_profile.ai_psychological_test = json.dumps({
                "responses": chat_history_list,
                "personality_type": metis_message_response['personality_type']
            }, ensure_ascii=False)
            user_profile.save()
            session.is_active = False
            session.save()

        if not user_message_content:
            logger.warning("Message content is missing in request.")
            return Response({'detail': 'محتوای پیام الزامی است.'}, status=status.HTTP_400_BAD_REQUEST)

        if not self._check_message_limit(user_profile):
            return Response({'detail': 'محدودیت پیام روزانه شما به پایان رسیده است.'},
                            status=status.HTTP_429_TOO_MANY_REQUESTS)

        metis_service = MetisAIService()
        active_sessions = self._get_active_sessions_for_user(user)
        current_session_instance = None

        if session_id_from_request:
            current_session_instance = active_sessions.filter(ai_session_id=session_id_from_request).first()
            if not current_session_instance:
                logger.warning(
                    f"Provided session ID {session_id_from_request} not found or inactive for user {user.phone_number}.")
                return Response({'detail': 'شناسه جلسه ارائه شده نامعتبر یا غیرفعال است.'},
                                status=status.HTTP_404_NOT_FOUND)
            logger.info(
                f"User {user.phone_number} continuing internal session {session_id_from_request} with Metis session {current_session_instance.metis_session_id}.")
        else:
            if user_profile.role and active_sessions.count() >= user_profile.role.max_active_sessions:
                logger.warning(
                    f"User {user.phone_number} reached max active chat sessions ({user_profile.role.max_active_sessions}).")
                return Response({
                    'detail': 'به حداکثر تعداد جلسات گفتگوی فعال رسیده‌اید. لطفاً یک جلسه موجود را ببندید یا طرح خود را ارتقا دهید.'},
                    status=status.HTTP_400_BAD_REQUEST)
            try:
                internal_session_id = str(uuid.uuid4())
                user_info_for_metis = self._get_user_info_for_metis_api(user_profile)
                initial_messages_for_metis = []
                user_context_prompt = self._get_user_context_for_ai(user_profile)  # Get comprehensive context
                if user_context_prompt:
                    initial_messages_for_metis.append({"type": "SYSTEM", "content": user_context_prompt})

                logger.info(
                    f"Attempting to create Metis AI session for bot_id: {metis_service.bot_id} for user {user.phone_number}.")
                metis_ai_session_response = metis_service.create_chat_session(
                    bot_id=metis_service.bot_id,
                    user_data=user_info_for_metis,
                    initial_messages=initial_messages_for_metis
                )
                metis_session_id = metis_ai_session_response.get("id")

                if not metis_session_id:
                    logger.error(
                        f"Metis AI returned no session ID: {metis_ai_session_response} for user {user.phone_number}")
                    raise Exception("Failed to create Metis AI session. No ID returned.")

                current_session_instance = AiResponse.objects.create(
                    user=user,
                    ai_session_id=internal_session_id,
                    metis_session_id=metis_session_id,
                    ai_response_name=f"Chat Session {timezone.now().strftime('%Y-%m-%d %H:%M')}",
                    chat_history="[]"  # Initialize with empty JSON array string
                )
                logger.info(
                    f"New internal session {internal_session_id} created for user {user.phone_number} with Metis session {metis_session_id}.")

            except ConnectionError as e:
                logger.exception(f"Connection error during Metis AI session creation for user {user.phone_number}: {e}")
                return Response({'detail': f'خطا در اتصال به سرویس AI هنگام ایجاد جلسه: {e}'},
                                status=status.HTTP_503_SERVICE_UNAVAILABLE)
            except Exception as e:
                logger.exception(f"Unexpected error during Metis AI session creation for user {user.phone_number}: {e}")
                return Response({'detail': f'خطای پیش‌بینی نشده هنگام ایجاد جلسه AI: {e}'},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            chat_history_list = json.loads(
                current_session_instance.chat_history) if current_session_instance.chat_history else []

            # Add user message to history (before sending to AI, as it's a confirmed interaction part)
            chat_history_list.append(
                {"role": "user", "content": user_message_content, "timestamp": str(timezone.now())})

            logger.debug(
                f"Sending user message to Metis AI session {current_session_instance.metis_session_id} for user {user.phone_number}: {user_message_content}")

            metis_message_response = metis_service.send_message(
                session_id=current_session_instance.metis_session_id,
                message_content=user_message_content,  # Send only the current user message
                message_type="USER"
            )
            logger.debug(
                f"Metis AI raw message response (first call) for user {user.phone_number}: {json.dumps(metis_message_response, ensure_ascii=False, indent=2)}")

            ai_final_text_response = None
            tool_calls_from_metis = []  # From Metis 'actions' -> 'function_call'

            if metis_message_response and 'actions' in metis_message_response and metis_message_response['actions']:
                assistant_entry_for_history = {"role": "assistant", "content": None, "tool_calls": [],
                                               "timestamp": str(timezone.now())}

                for action in metis_message_response['actions']:
                    if action.get('type') == 'FUNCTION_CALL' and action.get('function_call'):
                        tool_calls_from_metis.append(action['function_call'])
                        # Record the AI's intention to call tools in history
                        assistant_entry_for_history["tool_calls"].append(action['function_call'])
                    elif action.get('type') == 'MESSAGE' and action.get('message') and action.get('message').get(
                            'content'):
                        # If there's also a direct message content from AI along with potential (or no) tool calls
                        ai_final_text_response = action['message']['content']
                        assistant_entry_for_history["content"] = ai_final_text_response

                if tool_calls_from_metis:
                    logger.info(f"Metis AI requested tool calls for user {user.phone_number}: {tool_calls_from_metis}")
                    chat_history_list.append(assistant_entry_for_history)  # Add AI's turn (tool call request)

                    tool_outputs_for_metis_api = []  # This will be sent to Metis API
                    for tool_call_details in tool_calls_from_metis:  # tool_call_details is what Metis sent
                        function_name = tool_call_details.get('name')
                        function_args_str = tool_call_details.get('args', '{}')
                        tool_call_id_from_metis = tool_call_details.get("id")  # Metis provides this

                        try:
                            function_args = json.loads(function_args_str) if isinstance(function_args_str,
                                                                                        str) else function_args_str
                        except json.JSONDecodeError:
                            logger.error(f"Failed to parse tool arguments for {function_name}: {function_args_str}")
                            function_args = {}

                        tool_execution_result_obj = self._call_tool_function(user, function_name, function_args)

                        # Add tool execution result to chat history
                        chat_history_list.append({
                            "role": "tool",
                            "tool_call_id": tool_call_id_from_metis,
                            "name": function_name,
                            "content": json.dumps(tool_execution_result_obj, ensure_ascii=False),
                            # Store full result object as JSON string
                            "timestamp": str(timezone.now())
                        })

                        # Prepare the output for Metis API
                        tool_outputs_for_metis_api.append({
                            "tool_call_id": tool_call_id_from_metis,
                            "tool_name": function_name,
                            "output": tool_execution_result_obj  # Send the rich Python object as output
                        })

                    logger.debug(
                        f"Sending tool outputs back to Metis AI for user {user.phone_number}: {json.dumps(tool_outputs_for_metis_api, ensure_ascii=False, indent=2)}")

                    # Send tool execution results back to Metis
                    final_metis_response_after_tools = metis_service.send_message(
                        session_id=current_session_instance.metis_session_id,
                        message_content=tool_outputs_for_metis_api,  # Send the list of dicts
                        message_type="TOOL"
                    )
                    logger.debug(
                        f"Metis AI raw message response (after tools) for user {user.phone_number}: {json.dumps(final_metis_response_after_tools, ensure_ascii=False, indent=2)}")

                    # Metis should now respond with the final text based on tool outputs
                    ai_final_text_response = final_metis_response_after_tools.get('content',
                                                                                  'پاسخی از AI پس از اجرای ابزار دریافت نشد.')

                elif not ai_final_text_response and assistant_entry_for_history["content"] is None and not \
                assistant_entry_for_history["tool_calls"]:
                    # If assistant_entry was prepared but had no content and no tool calls from the first AI response
                    ai_final_text_response = metis_message_response.get('content',
                                                                        'پاسخ مستقیمی از AI دریافت نشد و ابزاری هم فراخوانی نشد.')


            else:  # No 'actions' field, direct response from Metis
                ai_final_text_response = metis_message_response.get('content', 'پاسخی از AI دریافت نشد.')

            if not ai_final_text_response:  # Fallback if still no text response
                ai_final_text_response = "محتوای معتبری از AI دریافت نشد."

            # Add final AI text response to history
            chat_history_list.append(
                {"role": "assistant", "content": ai_final_text_response, "timestamp": str(timezone.now())})

            current_session_instance.chat_history = json.dumps(chat_history_list, ensure_ascii=False)
            current_session_instance.updated_at = timezone.now()
            current_session_instance.save(update_fields=['chat_history', 'updated_at'])

            self._increment_message_count(user_profile)

            return Response({
                'ai_response': ai_final_text_response,
                'session_id': current_session_instance.ai_session_id,
                'chat_history': chat_history_list
            }, status=status.HTTP_200_OK)

        except ConnectionError as e:
            logger.exception(f"Connection error during Metis AI interaction for user {user.phone_number}: {e}")
            return Response({'detail': f'خطا در ارتباط با سرویس AI: {e}'},
                            status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception as e:
            logger.exception(f"An unexpected error occurred during AI interaction for user {user.phone_number}: {e}")
            return Response({'detail': f'خطای پیش‌بینی نشده در طول تعامل با AI: {e}'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# users_ai/views.py
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
            return AiResponse.objects.filter(ai_response_name="Psychological Test")
        return AiResponse.objects.filter(user=user, ai_response_name="Psychological Test")

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
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        now = datetime.datetime.now().isoformat()
        logger.info(f"TestTimeView (test-tool-status-minimal) called. Returning current time: {now}")
        return Response({"currentTime": now, "status": "ok", "message": "Test endpoint for Metis tool is working!"})