# users_ai/views.py
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.conf import settings
import uuid
import json
import logging
import datetime

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
# Import custom permission
from .permissions import IsMetisToolCallback

logger = logging.getLogger(__name__)
User = get_user_model()


# --- Authentication Views ---
class RegisterUserView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]


class LoginUserView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        logger.debug(f"LoginUserView received: {request.data}")
        phone_number = request.data.get('phone_number')
        password = request.data.get('password')
        if not phone_number or not password:
            return Response({'detail': 'شماره موبایل و رمز عبور الزامی است.'}, status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.filter(phone_number=phone_number).first()
        if user is None or not user.check_password(password):
            return Response({'detail': 'شماره موبایل یا رمز عبور نامعتبر است.'}, status=status.HTTP_401_UNAUTHORIZED)
        if not user.is_active:
            return Response({'detail': 'حساب کاربری شما غیرفعال است.'}, status=status.HTTP_401_UNAUTHORIZED)
        refresh = RefreshToken.for_user(user)
        logger.info(f"User {phone_number} logged in successfully.")
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user_id': user.id,
            'phone_number': user.phone_number
        }, status=status.HTTP_200_OK)


# --- User-facing Views (Protected by standard JWT IsAuthenticated) ---
class UserProfileDetailView(generics.RetrieveUpdateAPIView):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return get_object_or_404(UserProfile, user=self.request.user)


# --- Base View for Metis Tool Callbacks ---
class BaseMetisToolView(generics.GenericAPIView):
    permission_classes = [IsMetisToolCallback]  # Custom permission to check secret token in URL

    def get_user_from_identifier(self, request_data):
        # Expects Metis AI to send a 'user_phone_identifier' (or similar) in the tool arguments
        user_identifier = request_data.get('user_phone_identifier')  # Ensure this arg is defined in Metis tool
        if not user_identifier:
            logger.warning("Metis tool call missing 'user_phone_identifier' in request data.")
            return None
        try:
            # Assuming phone_number is the identifier sent by Metis
            user = User.objects.get(phone_number=user_identifier)
            logger.info(f"User {user.phone_number} identified for Metis tool call.")
            return user
        except User.DoesNotExist:
            logger.error(f"User with phone_number '{user_identifier}' not found for Metis tool call.")
            return None
        except Exception as e:
            logger.error(f"Error identifying user from identifier '{user_identifier}': {e}")
            return None


# --- Tool Callback Views (Called by Metis AI, secured by IsMetisToolCallback) ---
class GoalToolView(BaseMetisToolView, generics.CreateAPIView):
    serializer_class = GoalSerializer

    def post(self, request, *args, **kwargs):  # Renamed from perform_create for clarity with CreateAPIView
        logger.info(f"GoalToolView POST received data: {request.data}")
        user = self.get_user_from_identifier(request.data)
        if not user:
            return Response({"error": "User not identified or not found."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            try:
                serializer.save(user=user)
                logger.info(f"Goal created for user {user.phone_number} via Metis tool.")
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except Exception as e:
                logger.error(f"Error saving goal for user {user.phone_number}: {e}")
                return Response({"error": f"Failed to save goal: {str(e)}"},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        logger.error(
            f"GoalToolView validation error for user {user.phone_number if user else 'Unknown'}: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class HealthRecordToolView(BaseMetisToolView, generics.UpdateAPIView):  # RetrieveAPIView might not be needed for PATCH
    queryset = HealthRecord.objects.all()  # queryset needed for UpdateAPIView
    serializer_class = HealthRecordSerializer

    def patch(self, request, *args, **kwargs):
        logger.info(f"HealthRecordToolView PATCH received data: {request.data}")
        user = self.get_user_from_identifier(request.data)
        if not user:
            return Response({"error": "User not identified or not found."}, status=status.HTTP_400_BAD_REQUEST)
        instance, created = HealthRecord.objects.get_or_create(user=user)
        if created:
            logger.info(f"HealthRecord created for user {user.phone_number} as it did not exist.")
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            logger.info(f"HealthRecord for user {user.phone_number} updated by Metis tool.")
            return Response(serializer.data, status=status.HTTP_200_OK)
        logger.error(f"HealthRecordToolView validation error for user {user.phone_number}: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ... Define similar ToolViews for other models:
# PsychologicalProfileToolView, CareerEducationToolView, FinancialInfoToolView,
# SocialRelationshipToolView, PreferenceInterestToolView, EnvironmentalContextToolView,
# RealTimeDataToolView, FeedbackLearningToolView, UserProfileToolView (for specific fields like ai_psychological_test)

# Example for UserProfile specific fields (like ai_psychological_test)
class UserProfileToolView(BaseMetisToolView, generics.UpdateAPIView):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer  # This serializer should allow partial updates to specific fields

    def patch(self, request, *args, **kwargs):
        logger.info(f"UserProfileToolView PATCH received data: {request.data}")
        user = self.get_user_from_identifier(request.data)
        if not user:
            return Response({"error": "User not identified or not found."}, status=status.HTTP_400_BAD_REQUEST)
        instance = get_object_or_404(UserProfile, user=user)
        # Ensure only allowed fields are updated by the tool
        allowed_tool_fields = ['ai_psychological_test', 'user_information_summary']
        update_data = {k: v for k, v in request.data.items() if k in allowed_tool_fields}

        if not update_data:
            logger.warning(
                f"No valid fields to update in UserProfileToolView for user {user.phone_number}. Data: {request.data}")
            return Response({"error": "No valid fields provided for update."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(instance, data=update_data, partial=True)
        if serializer.is_valid():
            serializer.save()
            logger.info(f"UserProfile specific details for user {user.phone_number} updated by Metis tool.")
            return Response(serializer.data, status=status.HTTP_200_OK)
        logger.error(f"UserProfileToolView validation error for user {user.phone_number}: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# --- Test View (remains AllowAny) ---
class TestTimeView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        now = datetime.datetime.now().isoformat()
        logger.info(f"TestTimeView called. Returning current time: {now}")
        return Response({"currentTime": now, "status": "ok", "message": "Test endpoint is working!"})


# --- AI Agent Chat View ---
class AIAgentChatView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['post']

    def _get_active_sessions_for_user(self, user):
        AiResponse.objects.filter(user=user, expires_at__lte=timezone.now(), is_active=True).update(is_active=False)
        return AiResponse.objects.filter(user=user, is_active=True)

    def _check_message_limit(self, user_profile):
        if not user_profile.role:
            logger.warning(f"User {user_profile.user.phone_number} has no role assigned. Skipping message limit check.")
            return True
        now = timezone.localdate()
        if user_profile.last_message_date != now:
            user_profile.messages_sent_today = 0
            user_profile.last_message_date = now
        if user_profile.messages_sent_today >= user_profile.role.daily_message_limit:
            return False
        return True

    def _increment_message_count(self, user_profile):
        now = timezone.localdate()
        if user_profile.last_message_date != now:
            user_profile.messages_sent_today = 0
            user_profile.last_message_date = now
        user_profile.messages_sent_today += 1
        user_profile.save(update_fields=['messages_sent_today', 'last_message_date'])

    def _get_user_info_for_metis_api(self, user_profile):
        user = user_profile.user
        user_info = {"id": str(user.id), "name": user.phone_number}
        if user_profile.first_name: user_info["first_name"] = user_profile.first_name
        if user_profile.last_name: user_info["last_name"] = user_profile.last_name
        # ... (add other relevant UserProfile fields and related models as needed)
        return user_info

    def _get_user_context_for_ai(self, user_profile):
        context_parts = []
        user = user_profile.user
        context_parts.append("### اطلاعات هویتی و پایه‌ای کاربر:")
        context_parts.append(f"شناسه کاربر (شماره موبایل): {user.phone_number}")
        # ... (کد کامل جمع آوری اطلاعات کاربر که قبلا داشتید) ...
        return "این اطلاعات جامع درباره کاربر است:\n" + "\n".join(context_parts) if context_parts else ""

    def post(self, request):
        logger.info(f"AIAgentChatView POST. User: {request.user.phone_number}, Data: {request.data}")
        user = request.user
        user_profile = get_object_or_404(UserProfile, user=user)
        user_message = request.data.get('message')
        session_id_from_request = request.data.get('session_id')

        if not user_message:
            return Response({'detail': 'محتوای پیام الزامی است.'}, status=status.HTTP_400_BAD_REQUEST)
        if not self._check_message_limit(user_profile):
            return Response({'detail': 'محدودیت پیام روزانه شما به پایان رسیده است.'},
                            status=status.HTTP_429_TOO_MANY_REQUESTS)

        metis_service = MetisAIService()
        active_sessions = self._get_active_sessions_for_user(user)
        current_session = None

        if session_id_from_request:
            current_session = active_sessions.filter(ai_session_id=session_id_from_request).first()
            if not current_session:
                return Response({'detail': 'شناسه جلسه نامعتبر است.'}, status=status.HTTP_404_NOT_FOUND)
        else:
            if user_profile.role and active_sessions.count() >= user_profile.role.max_active_sessions:
                return Response({'detail': 'به حداکثر تعداد جلسات فعال رسیده‌اید.'}, status=status.HTTP_400_BAD_REQUEST)
            try:
                internal_session_id = str(uuid.uuid4())
                user_info = self._get_user_info_for_metis_api(user_profile)
                initial_context = self._get_user_context_for_ai(user_profile)
                initial_messages = [{"type": "SYSTEM", "content": initial_context}] if initial_context else []

                logger.info(f"Attempting to create Metis session for user {user.phone_number}")
                metis_response = metis_service.create_chat_session(
                    bot_id=metis_service.bot_id, user_data=user_info, initial_messages=initial_messages
                )
                metis_session_id = metis_response.get("id")
                if not metis_session_id: raise Exception("No session ID from Metis.")

                current_session = AiResponse.objects.create(
                    user=user, ai_session_id=internal_session_id, metis_session_id=metis_session_id,
                    chat_history=json.dumps([])
                )
                logger.info(
                    f"New session {internal_session_id} (Metis: {metis_session_id}) created for {user.phone_number}")
            except Exception as e:
                logger.exception(f"Error creating Metis session for {user.phone_number}: {e}")
                return Response({'detail': f'خطا در ایجاد جلسه با سرویس AI: {e}'},
                                status=status.HTTP_503_SERVICE_UNAVAILABLE)

        chat_history_list = json.loads(current_session.chat_history) if current_session.chat_history else []
        chat_history_list.append({"role": "user", "content": user_message, "timestamp": str(timezone.now())})

        try:
            logger.debug(f"Sending to Metis (session: {current_session.metis_session_id}): '{user_message}'")

            # در اینجا دیگر توابع را به send_message ارسال نمی‌کنیم.
            # فرض بر این است که توابع به صورت دستی در پنل متیس برای ربات تعریف شده‌اند.
            # متیس خودش تشخیص می‌دهد که آیا باید تابعی را فراخوانی کند یا خیر.
            metis_response = metis_service.send_message(
                session_id=current_session.metis_session_id,
                message_content=user_message,
                message_type="USER"
            )
            logger.info(f"Metis raw response: {json.dumps(metis_response, ensure_ascii=False, indent=2)}")

            ai_final_content = "متأسفم، مشکلی در پردازش درخواست شما پیش آمد."  # Default error response

            # بررسی پاسخ Metis AI برای فراخوانی تابع یا محتوای عادی
            if metis_response:
                if 'actions' in metis_response and metis_response['actions']:
                    tool_call_action = next((a for a in metis_response['actions'] if a.get('type') == 'FUNCTION_CALL'),
                                            None)
                    if tool_call_action:
                        # Metis یک تابع را پیشنهاد داده است.
                        # در این سناریو، Metis خودش تابع را فراخوانی خواهد کرد (چون URL عمومی است).
                        # ما فقط منتظر پاسخ بعدی Metis می‌مانیم که باید شامل نتیجه اجرای تابع باشد
                        # یا پاسخی بر اساس آن نتیجه.
                        # بنابراین، پیام فعلی AI ممکن است یک پیام میانی باشد.
                        function_call_data = tool_call_action['function_call']
                        tool_name_called = function_call_data.get('name')
                        ai_final_content = metis_response.get('content')  # ممکن است محتوای اولیه قبل از نتیجه تابع باشد
                        if not ai_final_content:  # اگر محتوای اولیه وجود ندارد
                            ai_final_content = f"در حال پردازش درخواست شما با استفاده از ابزار '{tool_name_called}'..."
                        logger.info(
                            f"Metis indicated a tool call to '{tool_name_called}'. Waiting for Metis to call the tool and provide final response.")
                        # نیازی به ارسال مجدد پیام از نوع TOOL از اینجا نیست، چون Metis خودش تابع را صدا می‌زند.
                        # ما باید منتظر پیام بعدی باشیم که نتیجه اجرای تابع را از طرف سرور جنگو دریافت کرده و پردازش کرده.
                        # پاسخ موفقیت‌آمیز قبلی شما ("هدف شما با موفقیت ایجاد شد...") نشان می‌دهد که Metis پس از فراخوانی تابع، خودش پاسخ نهایی را می‌سازد.
                    else:  # actions وجود داشت اما FUNCTION_CALL نبود
                        ai_final_content = metis_response.get('content',
                                                              "پاسخ دریافتی از AI ساختار مورد انتظار برای actions را نداشت.")
                elif metis_response.get('content'):  # پاسخ عادی بدون tool calling
                    ai_final_content = metis_response.get('content')
                else:
                    logger.warning(f"Unexpected Metis response structure: {metis_response}")

            chat_history_list.append(
                {"role": "assistant", "content": ai_final_content, "timestamp": str(timezone.now())})
            current_session.chat_history = json.dumps(chat_history_list, ensure_ascii=False)
            current_session.save(update_fields=['chat_history', 'updated_at'])
            self._increment_message_count(user_profile)

            return Response({
                'ai_response': ai_final_content,
                'session_id': current_session.ai_session_id,
                'chat_history': chat_history_list
            }, status=status.HTTP_200_OK)

        except ConnectionError as e:
            logger.exception(f"Connection error during Metis AI interaction for user {user.phone_number}: {e}")
            # ... (مدیریت خطا و ذخیره در تاریخچه)
            return Response({'detail': f'خطا در ارتباط با سرویس AI: {e}'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception as e:
            logger.exception(f"Unexpected error during AI interaction for user {user.phone_number}: {e}")
            # ... (مدیریت خطا و ذخیره در تاریخچه)
            return Response({'detail': f'خطای پیش‌بینی نشده: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# --- ویوهای مربوط به سشن‌ها (بدون تغییر) ---
class AiChatSessionListCreate(generics.ListCreateAPIView):
    queryset = AiResponse.objects.all()
    serializer_class = AiResponseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self): return self.queryset.filter(user=self.request.user, is_active=True).order_by('-created_at')

    def perform_create(self, serializer): pass


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
        except Exception as e:
            logger.error(f"Failed to delete Metis session {instance.metis_session_id}: {e}", exc_info=True)
        instance.delete()
        logger.info(
            f"Local AiResponse session {instance.ai_session_id} deleted for user {self.request.user.phone_number}.")