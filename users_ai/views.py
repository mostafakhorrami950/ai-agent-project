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
import datetime
from django.db import transaction
from .permissions import IsMetisToolCallback
from django.conf import settings
from datetime import timedelta
from django.http import Http404  # اضافه کردن این import

# Import your models
from .models import (
    UserProfile, HealthRecord, PsychologicalProfile, CareerEducation,
    FinancialInfo, SocialRelationship, PreferenceInterest, EnvironmentalContext,
    RealTimeData, FeedbackLearning, Goal, Habit, AiResponse, UserRole, PsychTestHistory
)
# Import your serializers
from .serializers import (
    UserSerializer, UserProfileSerializer, HealthRecordSerializer, PsychologicalProfileSerializer,
    CareerEducationSerializer, FinancialInfoSerializer, SocialRelationshipSerializer,
    PreferenceInterestSerializer, EnvironmentalContextSerializer, RealTimeDataSerializer,
    FeedbackLearningSerializer, GoalSerializer, HabitSerializer, AiResponseSerializer, PsychTestHistorySerializer
)
# Import your Metis AI service
from .metis_ai_service import MetisAIService

logger = logging.getLogger(__name__)
User = get_user_model()

# ثابت برای پیام سیستمی شروع تست پویا
PROFILE_SETUP_SYSTEM_PROMPT = """شما در حال کمک به کاربر برای ساخت پروفایل جامع هستید. هدف جمع‌آوری اطلاعات کلیدی در مورد کاربر است. لطفاً سوالات زیر را به صورت طبیعی و محاوره‌ای، یکی پس از دیگری از کاربر بپرسید. پس از هر پاسخ کاربر، به سراغ سوال بعدی بروید. منتظر پاسخ کامل کاربر برای هر سوال باشید.
سوالات کلیدی که باید پوشش داده شوند (می‌توانید ترتیب یا نحوه پرسش را برای طبیعی‌تر شدن مکالمه تغییر دهید):
1.  سابقه پزشکی: آیا بیماری خاص یا مزمنی (مانند دیابت، فشار خون، آسم، مشکلات قلبی) دارید یا داشته‌اید؟ جراحی مهمی انجام داده‌اید؟
2.  آلرژی: آیا به دارو، غذا یا ماده خاصی حساسیت دارید؟
3.  رژیم غذایی: رژیم غذایی خاصی را دنبال می‌کنید (مثلاً گیاه‌خواری، وگان، بدون گلوتن، روزه‌داری متناوب)؟ عادات غذایی کلی شما چگونه است؟
4.  فعالیت بدنی: سطح فعالیت بدنی شما معمولاً چگونه است (کم تحرک، فعالیت متوسط، فعال)؟ ورزش خاصی انجام می‌دهید؟
5.  سلامت روان: وضعیت کلی سلامت روان خود را چگونه ارزیابی می‌کنید؟ آیا در حال حاضر با چالش‌هایی مانند استرس، اضطراب یا افسردگی مواجه هستید یا سابقه آن را داشته‌اید؟
6.  خواب: معمولاً چند ساعت در شبانه‌روز می‌خوابید؟ کیفیت خواب شما چگونه است؟
7.  شغل و تحصیلات: شغل فعلی شما چیست و در چه صنعتی فعالیت می‌کنید؟ بالاترین مدرک تحصیلی و رشته شما چیست؟
8.  مهارت‌ها: مهم‌ترین مهارت‌های شغلی یا فردی خود را چه می‌دانید؟
9.  اهداف شغلی: اهداف کوتاه‌مدت و بلندمدت شغلی و حرفه‌ای شما چیست؟
10. شخصیت: خودتان را چگونه توصیف می‌کنید؟ اگر تست شخصیتی مانند MBTI داده‌اید، نتیجه آن چه بوده است؟ (اختیاری)
11. ارزش‌های اصلی: چه ارزش‌هایی در زندگی برای شما از همه مهم‌تر هستند؟ (مثال: خانواده، صداقت، پیشرفت، آرامش)
12. انگیزه‌ها: چه چیزهایی به شما انگیزه و انرژی می‌دهد؟
13. سرگرمی‌ها و علایق: سرگرمی‌ها و علایق اصلی شما در اوقات فراغت چیست؟ (مثال: کتاب، فیلم، موسیقی، ورزش، سفر)
پس از اینکه احساس کردید اطلاعات کافی در این زمینه‌ها جمع‌آوری شده است، یا اگر کاربر دیگر تمایلی به ادامه نداشت، به کاربر اطلاع دهید که می‌تواند با ارسال عبارت "اتمام تست" این مرحله را به پایان برساند تا خلاصه‌ای از اطلاعاتش تهیه شود، یا با ارسال "لغو تست" از ادامه انصراف دهد.
"""

PROFILE_SUMMARIZATION_PROMPT_PREFIX = """بر اساس مکالمه زیر که شامل پرسش و پاسخ برای تکمیل پروفایل کاربر است، لطفاً یک خلاصه جامع و دقیق از اطلاعات کاربر در قالب 'user_information_summary' تهیه کن. این خلاصه باید شامل نکات کلیدی از تمام جنبه‌های مطرح شده در پروفایل او (سلامتی، شغل، روانشناسی، علایق و غیره) باشد. در صورت امکان و بر اساس پاسخ‌ها، یک تحلیل اولیه از تیپ شخصیتی یا ویژگی‌های روانشناختی بارز کاربر نیز ارائه بده. لطفاً فقط و فقط خود خلاصه نهایی را به صورت یک پاراگراف یا چند پاراگراف منسجم و به زبان فارسی روان برگردان. از اضافه کردن هرگونه عبارت مقدماتی یا پایانی مانند 'بله، حتما' یا 'این هم خلاصه' خودداری کن. فقط متن خلاصه:
[شروع تاریخچه مکالمه برای خلاصه سازی]
"""
PROFILE_SUMMARIZATION_PROMPT_SUFFIX = "\n[پایان تاریخچه مکالمه برای خلاصه سازی]"

CMD_START_SETUP = "تکمیل پروفایل"
CMD_FINISH_SETUP = "اتمام تست"
CMD_CANCEL_SETUP = "لغو تست"


class RegisterUserView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        user = serializer.save()
        UserProfile.objects.create(user=user)
        logger.info(f"User {user.phone_number} registered successfully and UserProfile created.")


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
        return get_object_or_404(self.queryset, user=self.request.user)


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


class ToolUpdateUserProfileDetailsView(APIView):
    permission_classes = [IsMetisToolCallback]
    http_method_names = ['patch']

    def patch(self, request, *args, **kwargs):
        logger.info(f"Tool {self.__class__.__name__} - Request Query Params: {request.query_params}")
        logger.info(f"Tool {self.__class__.__name__} - Request Data: {request.data}")
        user_id = request.data.get('user_id')
        if not user_id:
            logger.error(f"Tool {self.__class__.__name__}: 'user_id' NOT FOUND in request data: {request.data}")
            return Response({"error": "User ID ('user_id') is required in the request data."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            user_id_int = int(user_id)
            user = User.objects.get(id=user_id_int)
        except ValueError:
            logger.error(f"Tool {self.__class__.__name__}: Invalid 'user_id' format: {user_id}.")
            return Response({"error": "Invalid User ID format."}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            logger.error(f"Tool {self.__class__.__name__}: User with ID {user_id} not found.")
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        profile_data_for_serializer = request.data.copy()
        profile_data_for_serializer.pop('user_id', None)
        defaults_for_create = profile_data_for_serializer.copy()
        profile, created = UserProfile.objects.get_or_create(user=user, defaults=defaults_for_create)
        serializer = UserProfileSerializer(profile, data=profile_data_for_serializer, partial=True,
                                           context={'request': request})
        if serializer.is_valid():
            serializer.save()
            action_message = 'ایجاد' if created else 'به‌روز'
            response_status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
            logger.info(f"Tool: UserProfile details {action_message} for user {user.phone_number}.")
            return Response({"status": "success",
                             "message": f"جزئیات پروفایل کاربر {user.phone_number} با موفقیت {action_message} شد.",
                             "data": serializer.data}, status=response_status_code)
        else:
            logger.error(
                f"Tool: Error updating/creating user profile details for {user.phone_number}: {serializer.errors}")
            return Response(
                {"status": "error", "message": "خطا در به‌روزرسانی جزئیات پروفایل.", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST)


class ToolUpdateHealthRecordView(APIView):
    permission_classes = [IsMetisToolCallback]
    http_method_names = ['patch']

    def patch(self, request, *args, **kwargs):
        logger.info(f"Tool {self.__class__.__name__} - Request Query Params: {request.query_params}")
        logger.info(f"Tool {self.__class__.__name__} - Request Data: {request.data}")
        user_id = request.data.get('user_id')
        if not user_id:
            logger.error(f"Tool {self.__class__.__name__}: 'user_id' NOT FOUND in request data: {request.data}")
            return Response({"error": "User ID ('user_id') is required in the request data for tool calls."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            user_id_int = int(user_id)
            user = User.objects.get(id=user_id_int)
        except ValueError:
            logger.error(f"Tool {self.__class__.__name__}: Invalid 'user_id' format: {user_id}.")
            return Response({"error": f"Invalid User ID format: '{user_id}'. Must be an integer."},
                            status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            logger.error(f"Tool {self.__class__.__name__}: User with ID {user_id} not found.")
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        health_data_for_serializer = request.data.copy()
        health_data_for_serializer.pop('user_id', None)
        defaults_for_create = health_data_for_serializer.copy()
        record, created = HealthRecord.objects.get_or_create(user=user, defaults=defaults_for_create)
        serializer = HealthRecordSerializer(instance=record, data=health_data_for_serializer, partial=True,
                                            context={'request': request})
        if serializer.is_valid():
            serializer.save()
            action_message = 'ایجاد' if created else 'به‌روز'
            response_status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
            logger.info(f"Tool: HealthRecord {action_message} for user {user.phone_number}.")
            return Response({"status": "success",
                             "message": f"اطلاعات سلامتی کاربر {user.phone_number} با موفقیت {action_message} شد.",
                             "data": serializer.data}, status=response_status_code)
        else:
            logger.error(
                f"Tool: Error updating/creating HealthRecord for user {user.phone_number}: {serializer.errors}")
            return Response(
                {"status": "error", "message": "خطا در اعتبارسنجی اطلاعات سلامتی.", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST)


class ToolUpdatePsychologicalProfileView(APIView):
    permission_classes = [IsMetisToolCallback]
    http_method_names = ['patch']

    def patch(self, request, *args, **kwargs):
        logger.info(f"Tool {self.__class__.__name__} - Request Query Params: {request.query_params}")
        logger.info(f"Tool {self.__class__.__name__} - Request Data: {request.data}")
        user_id = request.data.get('user_id')
        if not user_id:
            logger.error(f"Tool {self.__class__.__name__}: 'user_id' NOT FOUND in request data: {request.data}")
            return Response({"error": "User ID ('user_id') is required in the request data."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            user_id_int = int(user_id)
            user = User.objects.get(id=user_id_int)
        except ValueError:
            logger.error(f"Tool {self.__class__.__name__}: Invalid 'user_id' format: {user_id}.")
            return Response({"error": "Invalid User ID format."}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            logger.error(f"Tool {self.__class__.__name__}: User with ID {user_id} not found.")
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        data_for_serializer = request.data.copy()
        data_for_serializer.pop('user_id', None)
        defaults_for_create = data_for_serializer.copy()
        record, created = PsychologicalProfile.objects.get_or_create(user=user, defaults=defaults_for_create)
        serializer = PsychologicalProfileSerializer(record, data=data_for_serializer, partial=True,
                                                    context={'request': request})
        if serializer.is_valid():
            serializer.save()
            action_message = 'ایجاد' if created else 'به‌روز'
            response_status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
            logger.info(f"Tool: PsychologicalProfile {action_message} for user {user.phone_number}.")
            return Response({"status": "success",
                             "message": f"پروفایل روانشناختی کاربر {user.phone_number} با موفقیت {action_message} شد.",
                             "data": serializer.data}, status=response_status_code)
        else:
            logger.error(
                f"Tool: Error updating/creating PsychologicalProfile for user {user.phone_number}: {serializer.errors}")
            return Response({"status": "error", "message": "خطا در پروفایل روانشناختی.", "errors": serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)


class ToolUpdateCareerEducationView(APIView):
    permission_classes = [IsMetisToolCallback]
    http_method_names = ['patch']

    def patch(self, request, *args, **kwargs):
        logger.info(f"Tool {self.__class__.__name__} - Request Query Params: {request.query_params}")
        logger.info(f"Tool {self.__class__.__name__} - Request Data: {request.data}")
        user_id = request.data.get('user_id')
        if not user_id:
            logger.error(f"Tool {self.__class__.__name__}: 'user_id' NOT FOUND in request data: {request.data}")
            return Response({"error": "User ID ('user_id') is required in the request data."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            user_id_int = int(user_id)
            user = User.objects.get(id=user_id_int)
        except ValueError:
            logger.error(f"Tool {self.__class__.__name__}: Invalid 'user_id' format: {user_id}.")
            return Response({"error": "Invalid User ID format."}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            logger.error(f"Tool {self.__class__.__name__}: User with ID {user_id} not found.")
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        data_for_serializer = request.data.copy()
        data_for_serializer.pop('user_id', None)
        defaults_for_create = data_for_serializer.copy()
        record, created = CareerEducation.objects.get_or_create(user=user, defaults=defaults_for_create)
        serializer = CareerEducationSerializer(record, data=data_for_serializer, partial=True,
                                               context={'request': request})
        if serializer.is_valid():
            serializer.save()
            action_message = 'ایجاد' if created else 'به‌روز'
            response_status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
            logger.info(f"Tool: CareerEducation {action_message} for user {user.phone_number}.")
            return Response({"status": "success",
                             "message": f"اطلاعات شغلی/تحصیلی کاربر {user.phone_number} با موفقیت {action_message} شد.",
                             "data": serializer.data}, status=response_status_code)
        else:
            logger.error(
                f"Tool: Error updating/creating CareerEducation for user {user.phone_number}: {serializer.errors}")
            return Response({"status": "error", "message": "خطا در اطلاعات شغلی/تحصیلی.", "errors": serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)


class ToolUpdateFinancialInfoView(APIView):
    permission_classes = [IsMetisToolCallback]
    http_method_names = ['patch']

    def patch(self, request, *args, **kwargs):
        logger.info(f"Tool {self.__class__.__name__} - Request Query Params: {request.query_params}")
        logger.info(f"Tool {self.__class__.__name__} - Request Data: {request.data}")
        user_id = request.data.get('user_id')
        if not user_id:
            logger.error(f"Tool {self.__class__.__name__}: 'user_id' NOT FOUND in request data: {request.data}")
            return Response({"error": "User ID ('user_id') is required in the request data."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            user_id_int = int(user_id)
            user = User.objects.get(id=user_id_int)
        except ValueError:
            logger.error(f"Tool {self.__class__.__name__}: Invalid 'user_id' format: {user_id}.")
            return Response({"error": "Invalid User ID format."}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            logger.error(f"Tool {self.__class__.__name__}: User with ID {user_id} not found.")
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        data_for_serializer = request.data.copy()
        data_for_serializer.pop('user_id', None)
        defaults_for_create = data_for_serializer.copy()
        record, created = FinancialInfo.objects.get_or_create(user=user, defaults=defaults_for_create)
        serializer = FinancialInfoSerializer(record, data=data_for_serializer, partial=True,
                                             context={'request': request})
        if serializer.is_valid():
            serializer.save()
            action_message = 'ایجاد' if created else 'به‌روز'
            response_status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
            logger.info(f"Tool: FinancialInfo {action_message} for user {user.phone_number}.")
            return Response({"status": "success",
                             "message": f"اطلاعات مالی کاربر {user.phone_number} با موفقیت {action_message} شد.",
                             "data": serializer.data}, status=response_status_code)
        else:
            logger.error(
                f"Tool: Error updating/creating FinancialInfo for user {user.phone_number}: {serializer.errors}")
            return Response({"status": "error", "message": "خطا در اطلاعات مالی.", "errors": serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)


class ToolUpdateSocialRelationshipView(APIView):
    permission_classes = [IsMetisToolCallback]
    http_method_names = ['patch']

    def patch(self, request, *args, **kwargs):
        logger.info(f"Tool {self.__class__.__name__} - Request Query Params: {request.query_params}")
        logger.info(f"Tool {self.__class__.__name__} - Request Data: {request.data}")
        user_id = request.data.get('user_id')
        if not user_id:
            logger.error(f"Tool {self.__class__.__name__}: 'user_id' NOT FOUND in request data: {request.data}")
            return Response({"error": "User ID ('user_id') is required in the request data."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            user_id_int = int(user_id)
            user = User.objects.get(id=user_id_int)
        except ValueError:
            logger.error(f"Tool {self.__class__.__name__}: Invalid 'user_id' format: {user_id}.")
            return Response({"error": "Invalid User ID format."}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            logger.error(f"Tool {self.__class__.__name__}: User with ID {user_id} not found.")
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        data_for_serializer = request.data.copy()
        data_for_serializer.pop('user_id', None)
        defaults_for_create = data_for_serializer.copy()
        record, created = SocialRelationship.objects.get_or_create(user=user, defaults=defaults_for_create)
        serializer = SocialRelationshipSerializer(record, data=data_for_serializer, partial=True,
                                                  context={'request': request})
        if serializer.is_valid():
            serializer.save()
            action_message = 'ایجاد' if created else 'به‌روز'
            response_status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
            logger.info(f"Tool: SocialRelationship {action_message} for user {user.phone_number}.")
            return Response({"status": "success",
                             "message": f"اطلاعات روابط اجتماعی کاربر {user.phone_number} با موفقیت {action_message} شد.",
                             "data": serializer.data}, status=response_status_code)
        else:
            logger.error(
                f"Tool: Error updating/creating SocialRelationship for user {user.phone_number}: {serializer.errors}")
            return Response(
                {"status": "error", "message": "خطا در اطلاعات روابط اجتماعی.", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST)


class ToolUpdatePreferenceInterestView(APIView):
    permission_classes = [IsMetisToolCallback]
    http_method_names = ['patch']

    def patch(self, request, *args, **kwargs):
        logger.info(f"Tool {self.__class__.__name__} - Request Query Params: {request.query_params}")
        logger.info(f"Tool {self.__class__.__name__} - Request Data: {request.data}")
        user_id = request.data.get('user_id')
        if not user_id:
            logger.error(f"Tool {self.__class__.__name__}: 'user_id' NOT FOUND in request data: {request.data}")
            return Response({"error": "User ID ('user_id') is required in the request data."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            user_id_int = int(user_id)
            user = User.objects.get(id=user_id_int)
        except ValueError:
            logger.error(f"Tool {self.__class__.__name__}: Invalid 'user_id' format: {user_id}.")
            return Response({"error": "Invalid User ID format."}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            logger.error(f"Tool {self.__class__.__name__}: User with ID {user_id} not found.")
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        data_for_serializer = request.data.copy()
        data_for_serializer.pop('user_id', None)
        defaults_for_create = data_for_serializer.copy()
        record, created = PreferenceInterest.objects.get_or_create(user=user, defaults=defaults_for_create)
        serializer = PreferenceInterestSerializer(record, data=data_for_serializer, partial=True,
                                                  context={'request': request})
        if serializer.is_valid():
            serializer.save()
            action_message = 'ایجاد' if created else 'به‌روز'
            response_status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
            logger.info(f"Tool: PreferenceInterest {action_message} for user {user.phone_number}.")
            return Response({"status": "success",
                             "message": f"ترجیحات و علایق کاربر {user.phone_number} با موفقیت {action_message} شد.",
                             "data": serializer.data}, status=response_status_code)
        else:
            logger.error(
                f"Tool: Error updating/creating PreferenceInterest for user {user.phone_number}: {serializer.errors}")
            return Response({"status": "error", "message": "خطا در ترجیحات و علایق.", "errors": serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)


class ToolUpdateEnvironmentalContextView(APIView):
    permission_classes = [IsMetisToolCallback]
    http_method_names = ['patch']

    def patch(self, request, *args, **kwargs):
        logger.info(f"Tool {self.__class__.__name__} - Request Query Params: {request.query_params}")
        logger.info(f"Tool {self.__class__.__name__} - Request Data: {request.data}")
        user_id = request.data.get('user_id')
        if not user_id:
            logger.error(f"Tool {self.__class__.__name__}: 'user_id' NOT FOUND in request data: {request.data}")
            return Response({"error": "User ID ('user_id') is required in the request data."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            user_id_int = int(user_id)
            user = User.objects.get(id=user_id_int)
        except ValueError:
            logger.error(f"Tool {self.__class__.__name__}: Invalid 'user_id' format: {user_id}.")
            return Response({"error": "Invalid User ID format."}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            logger.error(f"Tool {self.__class__.__name__}: User with ID {user_id} not found.")
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        data_for_serializer = request.data.copy()
        data_for_serializer.pop('user_id', None)
        defaults_for_create = data_for_serializer.copy()
        record, created = EnvironmentalContext.objects.get_or_create(user=user, defaults=defaults_for_create)
        serializer = EnvironmentalContextSerializer(record, data=data_for_serializer, partial=True,
                                                    context={'request': request})
        if serializer.is_valid():
            serializer.save()
            action_message = 'ایجاد' if created else 'به‌روز'
            response_status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
            logger.info(f"Tool: EnvironmentalContext {action_message} for user {user.phone_number}.")
            return Response({"status": "success",
                             "message": f"زمینه محیطی کاربر {user.phone_number} با موفقیت {action_message} شد.",
                             "data": serializer.data}, status=response_status_code)
        else:
            logger.error(
                f"Tool: Error updating/creating EnvironmentalContext for user {user.phone_number}: {serializer.errors}")
            return Response({"status": "error", "message": "خطا در زمینه محیطی.", "errors": serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)


class ToolUpdateRealTimeDataView(APIView):
    permission_classes = [IsMetisToolCallback]
    http_method_names = ['patch']

    def patch(self, request, *args, **kwargs):
        logger.info(f"Tool {self.__class__.__name__} - Request Query Params: {request.query_params}")
        logger.info(f"Tool {self.__class__.__name__} - Request Data: {request.data}")
        user_id = request.data.get('user_id')
        if not user_id:
            logger.error(f"Tool {self.__class__.__name__}: 'user_id' NOT FOUND in request data: {request.data}")
            return Response({"error": "User ID ('user_id') is required in the request data."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            user_id_int = int(user_id)
            user = User.objects.get(id=user_id_int)
        except ValueError:
            logger.error(f"Tool {self.__class__.__name__}: Invalid 'user_id' format: {user_id}.")
            return Response({"error": "Invalid User ID format."}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            logger.error(f"Tool {self.__class__.__name__}: User with ID {user_id} not found.")
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        data_for_serializer = request.data.copy()
        data_for_serializer.pop('user_id', None)
        data_for_serializer.pop('timestamp', None)
        defaults_for_create = data_for_serializer.copy()
        record, created = RealTimeData.objects.get_or_create(user=user, defaults=defaults_for_create)
        serializer = RealTimeDataSerializer(record, data=data_for_serializer, partial=True,
                                            context={'request': request})
        if serializer.is_valid():
            serializer.save()
            action_message = 'ایجاد' if created else 'به‌روز'
            response_status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
            logger.info(f"Tool: RealTimeData {action_message} for user {user.phone_number}.")
            return Response({"status": "success",
                             "message": f"داده‌های بلادرنگ کاربر {user.phone_number} با موفقیت {action_message} شد.",
                             "data": serializer.data}, status=response_status_code)
        else:
            logger.error(
                f"Tool: Error updating/creating RealTimeData for user {user.phone_number}: {serializer.errors}")
            return Response({"status": "error", "message": "خطا در داده‌های بلادرنگ.", "errors": serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)


class ToolUpdateFeedbackLearningView(APIView):
    permission_classes = [IsMetisToolCallback]
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        logger.info(f"Tool {self.__class__.__name__} (POST) - Request Query Params: {request.query_params}")
        logger.info(f"Tool {self.__class__.__name__} (POST) - Request Data: {request.data}")
        user_id = request.data.get('user_id')
        if not user_id:
            logger.error(f"Tool {self.__class__.__name__}: 'user_id' NOT FOUND in request data: {request.data}")
            return Response({"error": "User ID ('user_id') is required in the request data."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            user_id_int = int(user_id)
            user = User.objects.get(id=user_id_int)
        except ValueError:
            logger.error(f"Tool {self.__class__.__name__}: Invalid 'user_id' format: {user_id}.")
            return Response({"error": "Invalid User ID format."}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            logger.error(f"Tool {self.__class__.__name__}: User with ID {user_id} not found.")
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        feedback_data_for_serializer = request.data.copy()
        feedback_data_for_serializer.pop('user_id', None)
        feedback_data_for_serializer.pop('timestamp', None)
        serializer = FeedbackLearningSerializer(data=feedback_data_for_serializer, context={'request': request})
        if serializer.is_valid():
            serializer.save(user=user)
            logger.info(f"Tool: New FeedbackLearning created for user {user.phone_number}.")
            return Response(
                {"status": "success", "message": f"بازخورد جدید برای کاربر {user.phone_number} با موفقیت ایجاد شد.",
                 "data": serializer.data}, status=status.HTTP_201_CREATED)
        else:
            logger.error(f"Tool: Error creating FeedbackLearning for user {user.phone_number}: {serializer.errors}")
            return Response(
                {"status": "error", "message": "خطا در ایجاد بازخورد و یادگیری.", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST)


class ToolCreateGoalView(APIView):
    permission_classes = [IsMetisToolCallback]
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        logger.info(f"Tool {self.__class__.__name__} - Request Query Params: {request.query_params}")
        logger.info(f"Tool {self.__class__.__name__} - Request Data: {request.data}")
        user_id = request.data.get('user_id')
        if not user_id:
            logger.error(f"Tool {self.__class__.__name__}: 'user_id' NOT FOUND in request data: {request.data}")
            return Response({"error": "User ID ('user_id') is required in the request data."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            user_id_int = int(user_id)
            user = User.objects.get(id=user_id_int)
        except ValueError:
            logger.error(f"Tool {self.__class__.__name__}: Invalid 'user_id' format: {user_id}.")
            return Response({"error": "Invalid User ID format."}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            logger.error(f"Tool {self.__class__.__name__}: User with ID {user_id} not found.")
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        goal_data_for_serializer = request.data.copy()
        goal_data_for_serializer.pop('user_id', None)
        serializer = GoalSerializer(data=goal_data_for_serializer, context={'request': request})
        if serializer.is_valid():
            goal = serializer.save(user=user)
            logger.info(f"Tool: Goal created for user {user.phone_number}: {goal.id}")
            return Response({"status": "success", "message": f"هدف با موفقیت برای کاربر {user.phone_number} ذخیره شد.",
                             "data": serializer.data}, status=status.HTTP_201_CREATED)
        else:
            logger.error(f"Tool: Error creating goal for user {user.phone_number}: {serializer.errors}")
            return Response({"status": "error", "message": "خطا در ذخیره هدف.", "errors": serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)


class ToolUpdateGoalView(APIView):
    permission_classes = [IsMetisToolCallback]
    http_method_names = ['patch']

    def patch(self, request, *args, **kwargs):
        logger.info(f"Tool {self.__class__.__name__} - Request Query Params: {request.query_params}")
        logger.info(f"Tool {self.__class__.__name__} - Request Data: {request.data}")
        user_id = request.data.get('user_id')
        pk = request.data.get('pk')
        if not user_id:
            logger.error(f"Tool {self.__class__.__name__}: 'user_id' NOT FOUND in request data: {request.data}")
            return Response({"error": "User ID ('user_id') is required in the request data."},
                            status=status.HTTP_400_BAD_REQUEST)
        if not pk:
            logger.error(f"Tool {self.__class__.__name__}: 'pk' NOT FOUND in request data: {request.data}")
            return Response({"error": "Goal PK ('pk') is required in the request data."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            user_id_int = int(user_id)
            pk_int = int(pk)
            user = User.objects.get(id=user_id_int)
        except ValueError:
            logger.error(f"Tool {self.__class__.__name__}: Invalid 'user_id' or 'pk' format.")
            return Response({"error": "Invalid User ID or PK format."}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            logger.error(f"Tool {self.__class__.__name__}: User with ID {user_id} not found.")
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        goal = get_object_or_404(Goal, pk=pk_int, user=user)
        goal_data_for_serializer = request.data.copy()
        goal_data_for_serializer.pop('user_id', None)
        goal_data_for_serializer.pop('pk', None)
        serializer = GoalSerializer(goal, data=goal_data_for_serializer, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            logger.info(f"Tool: Goal {pk_int} updated for user {user.phone_number}.")
            return Response(
                {"status": "success", "message": f"هدف {pk_int} کاربر {user.phone_number} با موفقیت به‌روز شد.",
                 "data": serializer.data}, status=status.HTTP_200_OK)
        else:
            logger.error(f"Tool: Error updating goal {pk_int} for {user.phone_number}: {serializer.errors}")
            return Response({"status": "error", "message": "خطا در به‌روزرسانی هدف.", "errors": serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)


class ToolDeleteGoalView(APIView):
    permission_classes = [IsMetisToolCallback]
    http_method_names = ['delete']

    def delete(self, request, *args, **kwargs):
        logger.info(f"Tool {self.__class__.__name__} - Request Query Params: {request.query_params}")
        logger.info(f"Tool {self.__class__.__name__} - Request Data: {request.data}")
        user_id = request.data.get('user_id')
        pk = request.data.get('pk')
        if not user_id:
            logger.error(f"Tool {self.__class__.__name__}: 'user_id' NOT FOUND in request data: {request.data}")
            return Response({"error": "User ID ('user_id') is required in the request data."},
                            status=status.HTTP_400_BAD_REQUEST)
        if not pk:
            logger.error(f"Tool {self.__class__.__name__}: 'pk' NOT FOUND in request data: {request.data}")
            return Response({"error": "Goal PK ('pk') is required in the request data."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            user_id_int = int(user_id)
            pk_int = int(pk)
            user = User.objects.get(id=user_id_int)
        except ValueError:
            logger.error(f"Tool {self.__class__.__name__}: Invalid 'user_id' or 'pk' format.")
            return Response({"error": "Invalid User ID or PK format."}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            logger.error(f"Tool {self.__class__.__name__}: User with ID {user_id} not found.")
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        goal = get_object_or_404(Goal, pk=pk_int, user=user)
        goal.delete()
        logger.info(f"Tool: Goal {pk_int} deleted for user {user.phone_number}.")
        return Response({"status": "success", "message": f"هدف {pk_int} کاربر {user.phone_number} با موفقیت حذف شد."},
                        status=status.HTTP_204_NO_CONTENT)


class ToolCreateHabitView(APIView):
    permission_classes = [IsMetisToolCallback]
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        logger.info(f"Tool {self.__class__.__name__} - Request Query Params: {request.query_params}")
        logger.info(f"Tool {self.__class__.__name__} - Request Data: {request.data}")
        user_id = request.data.get('user_id')
        if not user_id:
            logger.error(f"Tool {self.__class__.__name__}: 'user_id' NOT FOUND in request data: {request.data}")
            return Response({"error": "User ID ('user_id') is required in the request data."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            user_id_int = int(user_id)
            user = User.objects.get(id=user_id_int)
        except ValueError:
            logger.error(f"Tool {self.__class__.__name__}: Invalid 'user_id' format: {user_id}.")
            return Response({"error": "Invalid User ID format."}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            logger.error(f"Tool {self.__class__.__name__}: User with ID {user_id} not found.")
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        habit_data_for_serializer = request.data.copy()
        habit_data_for_serializer.pop('user_id', None)
        serializer = HabitSerializer(data=habit_data_for_serializer, context={'request': request})
        if serializer.is_valid():
            habit = serializer.save(user=user)
            logger.info(f"Tool: Habit created for user {user.phone_number}: {habit.id}")
            return Response({"status": "success", "message": f"عادت با موفقیت برای کاربر {user.phone_number} ذخیره شد.",
                             "data": serializer.data}, status=status.HTTP_201_CREATED)
        else:
            logger.error(f"Tool: Error creating habit for user {user.phone_number}: {serializer.errors}")
            return Response({"status": "error", "message": "خطا در ذخیره عادت.", "errors": serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)


class ToolUpdateHabitView(APIView):
    permission_classes = [IsMetisToolCallback]
    http_method_names = ['patch']

    def patch(self, request, pk, *args, **kwargs):
        logger.info(f"Tool {self.__class__.__name__} - Request Query Params: {request.query_params}")
        logger.info(f"Tool {self.__class__.__name__} - Request Data: {request.data}")
        logger.info(f"Tool {self.__class__.__name__} - PK from URL: {pk}")
        user_id = request.data.get('user_id')
        if not user_id:
            logger.error(f"Tool {self.__class__.__name__}: 'user_id' NOT FOUND in request data: {request.data}")
            return Response({"error": "User ID ('user_id') is required in the request data."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            user_id_int = int(user_id)
            pk_int = int(pk)
            user = User.objects.get(id=user_id_int)
        except ValueError:
            logger.error(f"Tool {self.__class__.__name__}: Invalid 'user_id' or 'pk' format.")
            return Response({"error": "Invalid User ID or PK format."}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            logger.error(f"Tool {self.__class__.__name__}: User with ID {user_id} not found.")
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        habit = get_object_or_404(Habit, pk=pk_int, user=user)
        habit_data_for_serializer = request.data.copy()
        habit_data_for_serializer.pop('user_id', None)
        serializer = HabitSerializer(habit, data=habit_data_for_serializer, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            logger.info(f"Tool: Habit {pk_int} updated for user {user.phone_number}.")
            return Response(
                {"status": "success", "message": f"عادت {pk_int} کاربر {user.phone_number} با موفقیت به‌روز شد.",
                 "data": serializer.data}, status=status.HTTP_200_OK)
        else:
            logger.error(f"Tool: Error updating habit {pk_int} for {user.phone_number}: {serializer.errors}")
            return Response({"status": "error", "message": "خطا در به‌روزرسانی عادت.", "errors": serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)


class ToolDeleteHabitView(APIView):
    permission_classes = [IsMetisToolCallback]
    http_method_names = ['delete']

    def delete(self, request, pk, *args, **kwargs):
        logger.info(f"Tool {self.__class__.__name__} - Request Query Params: {request.query_params}")
        logger.info(f"Tool {self.__class__.__name__} - Request Data: {request.data}")
        logger.info(f"Tool {self.__class__.__name__} - PK from URL: {pk}")
        user_id = request.data.get('user_id')
        if not user_id:
            logger.error(
                f"Tool {self.__class__.__name__}: 'user_id' must be provided in request data for DELETE with PK in URL.")
            return Response({"error": "User ID ('user_id') is required in the request data for this operation."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            user_id_int = int(user_id)
            pk_int = int(pk)
            user = User.objects.get(id=user_id_int)
        except ValueError:
            logger.error(f"Tool {self.__class__.__name__}: Invalid 'user_id' or 'pk' format.")
            return Response({"error": "Invalid User ID or PK format."}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            logger.error(f"Tool {self.__class__.__name__}: User with ID {user_id} not found.")
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        habit = get_object_or_404(Habit, pk=pk_int, user=user)
        habit_owner_phone = habit.user.phone_number
        habit.delete()
        logger.info(f"Tool: Habit {pk_int} deleted for user {habit_owner_phone}.")
        return Response({"status": "success", "message": f"عادت {pk_int} کاربر {habit_owner_phone} با موفقیت حذف شد."},
                        status=status.HTTP_204_NO_CONTENT)


class ToolCreatePsychTestRecordView(APIView):
    permission_classes = [IsMetisToolCallback]
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        logger.info(f"Tool {self.__class__.__name__} - Request Query Params: {request.query_params}")
        logger.info(f"Tool {self.__class__.__name__} - Request Data: {request.data}")
        user_id = request.data.get('user_id')
        if not user_id:
            logger.error(f"Tool {self.__class__.__name__}: 'user_id' NOT FOUND in request data: {request.data}")
            return Response({"error": "User ID ('user_id') is required in the request data."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            user_id_int = int(user_id)
            user = User.objects.get(id=user_id_int)
        except ValueError:
            logger.error(f"Tool {self.__class__.__name__}: Invalid 'user_id' format: {user_id}.")
            return Response({"error": "Invalid User ID format."}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            logger.error(f"Tool {self.__class__.__name__}: User with ID {user_id} not found.")
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        test_data_for_serializer = request.data.copy()
        test_data_for_serializer.pop('user_id', None)
        serializer = PsychTestHistorySerializer(data=test_data_for_serializer, context={'request': request})
        if serializer.is_valid():
            psych_test_record = serializer.save(user=user)
            logger.info(f"Tool: PsychTestHistory record created for user {user.phone_number}: {psych_test_record.id}")
            return Response({"status": "success",
                             "message": f"رکورد تست روانشناسی با موفقیت برای کاربر {user.phone_number} ذخیره شد.",
                             "data": serializer.data}, status=status.HTTP_201_CREATED)
        else:
            logger.error(
                f"Tool: Error creating PsychTestHistory record for user {user.phone_number}: {serializer.errors}")
            return Response(
                {"status": "error", "message": "خطا در ذخیره رکورد تست روانشناسی.", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST)


class ToolUpdatePsychTestRecordView(APIView):
    permission_classes = [IsMetisToolCallback]
    http_method_names = ['patch']

    def patch(self, request, *args, **kwargs):
        logger.info(f"Tool {self.__class__.__name__} - Request Query Params: {request.query_params}")
        logger.info(f"Tool {self.__class__.__name__} - Request Data: {request.data}")
        user_id = request.data.get('user_id')
        pk = request.data.get('pk')
        if not user_id:
            logger.error(f"Tool {self.__class__.__name__}: 'user_id' NOT FOUND in request data: {request.data}")
            return Response({"error": "User ID ('user_id') is required in the request data."},
                            status=status.HTTP_400_BAD_REQUEST)
        if not pk:
            logger.error(f"Tool {self.__class__.__name__}: 'pk' NOT FOUND in request data: {request.data}")
            return Response({"error": "PsychTestHistory PK ('pk') is required in the request data."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            user_id_int = int(user_id)
            pk_int = int(pk)
            user = User.objects.get(id=user_id_int)
        except ValueError:
            logger.error(f"Tool {self.__class__.__name__}: Invalid 'user_id' or 'pk' format.")
            return Response({"error": "Invalid User ID or PK format."}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            logger.error(f"Tool {self.__class__.__name__}: User with ID {user_id} not found.")
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        psych_test_record = get_object_or_404(PsychTestHistory, pk=pk_int, user=user)
        test_data_for_serializer = request.data.copy()
        test_data_for_serializer.pop('user_id', None)
        test_data_for_serializer.pop('pk', None)
        serializer = PsychTestHistorySerializer(psych_test_record, data=test_data_for_serializer, partial=True,
                                                context={'request': request})
        if serializer.is_valid():
            serializer.save()
            logger.info(f"Tool: PsychTestHistory record {pk_int} updated for user {user.phone_number}.")
            return Response({"status": "success",
                             "message": f"رکورد تست روانشناسی {pk_int} کاربر {user.phone_number} با موفقیت به‌روز شد.",
                             "data": serializer.data}, status=status.HTTP_200_OK)
        else:
            logger.error(
                f"Tool: Error updating PsychTestHistory record {pk_int} for {user.phone_number}: {serializer.errors}")
            return Response(
                {"status": "error", "message": "خطا در به‌روزرسانی رکورد تست روانشناسی.", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST)


class ToolDeletePsychTestRecordView(APIView):
    permission_classes = [IsMetisToolCallback]
    http_method_names = ['delete']

    def delete(self, request, *args, **kwargs):
        logger.info(f"Tool {self.__class__.__name__} - Request Query Params: {request.query_params}")
        logger.info(f"Tool {self.__class__.__name__} - Request Data: {request.data}")
        user_id = request.data.get('user_id')
        pk = request.data.get('pk')
        if not user_id:
            logger.error(f"Tool {self.__class__.__name__}: 'user_id' NOT FOUND in request data: {request.data}")
            return Response({"error": "User ID ('user_id') is required in the request data."},
                            status=status.HTTP_400_BAD_REQUEST)
        if not pk:
            logger.error(f"Tool {self.__class__.__name__}: 'pk' NOT FOUND in request data: {request.data}")
            return Response({"error": "PsychTestHistory PK ('pk') is required in the request data."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            user_id_int = int(user_id)
            pk_int = int(pk)
            user = User.objects.get(id=user_id_int)
        except ValueError:
            logger.error(f"Tool {self.__class__.__name__}: Invalid 'user_id' or 'pk' format.")
            return Response({"error": "Invalid User ID or PK format."}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            logger.error(f"Tool {self.__class__.__name__}: User with ID {user_id} not found.")
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        psych_test_record = get_object_or_404(PsychTestHistory, pk=pk_int, user=user)
        psych_test_record.delete()
        logger.info(f"Tool: PsychTestHistory record {pk_int} deleted for user {user.phone_number}.")
        return Response({"status": "success",
                         "message": f"رکورد تست روانشناسی {pk_int} کاربر {user.phone_number} با موفقیت حذف شد."},
                        status=status.HTTP_204_NO_CONTENT)


class AIAgentChatView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['post']

    def dispatch(self, request, *args, **kwargs):
        logger.debug(f"Dispatching request to AIAgentChatView: {request.method}, {request.path}")
        return super().dispatch(request, *args, **kwargs)

    def _get_active_sessions_for_user(self, user):
        AiResponse.objects.filter(user=user, expires_at__lte=timezone.now(), is_active=True).update(is_active=False)
        return AiResponse.objects.filter(user=user, is_active=True)

    def _check_message_limit(self, user_profile: UserProfile, is_profile_setup_flow: bool = False):
        if not user_profile.role:
            logger.warning(f"User {user_profile.user.phone_number} has no role assigned. Skipping message limit check.")
            return True
        # برای جریان تنظیم پروفایل، محدودیت پیام را نادیده می‌گیریم یا محدودیت دیگری اعمال می‌کنیم
        if is_profile_setup_flow:
            return True  # یا یک محدودیت جداگانه برای پیام‌های تست پویا

        now = timezone.localdate()
        if user_profile.last_message_date != now:
            user_profile.messages_sent_today = 0
            # user_profile.last_message_date = now # این در _increment_message_count انجام می‌شود

        if user_profile.messages_sent_today >= user_profile.role.daily_message_limit:
            logger.warning(
                f"User {user_profile.user.phone_number} reached daily message limit ({user_profile.role.daily_message_limit}).")
            return False
        return True

    def _increment_message_count(self, user_profile: UserProfile, is_profile_setup_flow: bool = False):
        if is_profile_setup_flow:  # برای پیام‌های حین تست پویا، شمارنده کلی را افزایش نمی‌دهیم
            return

        now = timezone.localdate()
        if user_profile.last_message_date != now:
            user_profile.messages_sent_today = 0
            user_profile.last_message_date = now
        user_profile.messages_sent_today += 1
        user_profile.save(update_fields=['messages_sent_today', 'last_message_date'])

    def _get_user_info_for_metis_api(self, user_profile: UserProfile):
        user_obj = {"id": str(user_profile.user.id)}
        user_name_parts = []
        # از فیلدهای first_name و last_name روی خود آبجکت user استفاده می‌کنیم
        if user_profile.user.first_name: user_name_parts.append(user_profile.user.first_name)
        if user_profile.user.last_name: user_name_parts.append(user_profile.user.last_name)
        if user_name_parts:
            user_obj["name"] = " ".join(user_name_parts)
        elif user_profile.user.phone_number:
            user_obj["name"] = user_profile.user.phone_number
        logger.debug(
            f"Simplified user_info for Metis API (session creation): {json.dumps(user_obj, ensure_ascii=False)}")
        return user_obj

    def _get_user_context_for_ai(self, user_profile: UserProfile, for_setup_prompt: bool = False):
        if for_setup_prompt:
            return PROFILE_SETUP_SYSTEM_PROMPT

        context_parts = []
        # استفاده از user_information_summary اگر موجود باشد
        if user_profile.user_information_summary:
            context_parts.append(
                f"خلاصه اطلاعات کاربر (برای استفاده در پاسخ‌ها):\n{user_profile.user_information_summary}")
        else:
            # اگر خلاصه موجود نیست، اطلاعات پایه را از CustomUser و UserProfile جمع‌آوری کن
            profile_info_items = [f"شماره موبایل کاربر فعلی: {user_profile.user.phone_number}"]

            # دسترسی به first_name و last_name از طریق user_profile.user
            if user_profile.user.first_name:
                profile_info_items.append(f"نام: {user_profile.user.first_name}")
            if user_profile.user.last_name:
                profile_info_items.append(f"نام خانوادگی: {user_profile.user.last_name}")

            if user_profile.age is not None:
                profile_info_items.append(f"سن: {user_profile.age}")

            # می‌توانید سایر فیلدهای UserProfile را نیز در اینجا اضافه کنید اگر لازم است
            # مثال:
            # if user_profile.gender: profile_info_items.append(f"جنسیت: {user_profile.gender}")
            # if user_profile.location: profile_info_items.append(f"مکان: {user_profile.location}")

            if len(profile_info_items) > 1:  # اگر اطلاعاتی به جز شماره موبایل وجود دارد
                context_parts.append(
                    "اطلاعات پایه و هویتی کاربر:\n" + "\n".join([f"- {item}" for item in profile_info_items]))
            else:  # اگر فقط شماره موبایل موجود است یا هیچکدام
                context_parts.append(f"کاربر فعلی با شماره موبایل: {user_profile.user.phone_number}")

            context_parts.append(
                "اطلاعات پروفایل کاربر هنوز تکمیل نشده است. می‌توانید از کاربر بخواهید با ارسال 'تکمیل پروفایل' اطلاعات خود را وارد کند.")

        full_context = "\n\n".join(filter(None, context_parts))
        logger.debug(
            f"Generated AI context (normal chat) for user {user_profile.user.phone_number}: {full_context[:300]}...")
        return full_context

    def post(self, request, *args, **kwargs):
        user = request.user
        user_profile = get_object_or_404(UserProfile, user=user)
        user_message_content = request.data.get('message', "").strip()
        session_id_from_request = request.data.get('session_id')

        metis_service = MetisAIService()
        active_sessions = self._get_active_sessions_for_user(user)
        current_session_instance = None

        # Default response values
        ai_final_response_content = "خطایی در پردازش رخ داد، لطفا مجددا تلاش کنید."
        final_session_id_to_return = session_id_from_request
        final_chat_history = []
        http_status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

        if not user_message_content:
            return Response({'detail': 'محتوای پیام الزامی است.'}, status=status.HTTP_400_BAD_REQUEST)




        try:
            with transaction.atomic():
                if session_id_from_request:
                    current_session_instance = active_sessions.filter(ai_session_id=session_id_from_request).first()
                    if current_session_instance:
                        if current_session_instance.expires_at and current_session_instance.expires_at < timezone.now():
                            current_session_instance.is_active = False
                            current_session_instance.save(update_fields=['is_active'])
                            logger.warning(
                                f"Session {session_id_from_request} for user {user.phone_number} has expired.")
                            current_session_instance = None
                    else:
                        logger.warning(
                            f"Session ID {session_id_from_request} provided but not found or inactive for user {user.phone_number}.")
                        return Response({
                                            'detail': 'جلسه نامعتبر است یا منقضی شده. لطفا بدون session_id برای ایجاد جلسه جدید تلاش کنید یا یک session_id معتبر ارسال کنید.'},
                                        status=status.HTTP_400_BAD_REQUEST)

                # ---- Profile Setup Flow ----
                if user_message_content.lower() == CMD_START_SETUP.lower() and not user_profile.is_in_profile_setup:
                    can_start_setup = True
                    if user_profile.role and user_profile.last_form_submission_time:
                        interval = timedelta(hours=user_profile.role.form_submission_interval_hours)
                        if timezone.now() < user_profile.last_form_submission_time + interval:
                            can_start_setup = False
                            time_remaining = (user_profile.last_form_submission_time + interval) - timezone.now()
                            hours_rem = int(time_remaining.total_seconds() / 3600)
                            minutes_rem = int((time_remaining.total_seconds() % 3600) / 60)
                            ai_final_response_content = f"شما فقط هر {user_profile.role.form_submission_interval_hours} ساعت یکبار می‌توانید اطلاعات پروفایل را تکمیل یا اصلاح کنید. لطفاً پس از حدود {hours_rem} ساعت و {minutes_rem} دقیقه دیگر تلاش کنید."
                            http_status_code = status.HTTP_429_TOO_MANY_REQUESTS
                            # Return current session info if exists, otherwise no session
                            final_session_id_to_return = str(
                                current_session_instance.ai_session_id) if current_session_instance else None
                            final_chat_history = current_session_instance.get_chat_history() if current_session_instance else []
                            return Response(
                                {'ai_response': ai_final_response_content, 'session_id': final_session_id_to_return,
                                 'chat_history': final_chat_history}, status=http_status_code)

                    if can_start_setup:
                        user_profile.is_in_profile_setup = True
                        user_profile.save(update_fields=['is_in_profile_setup'])
                        logger.info(f"User {user.phone_number} started profile setup.")
                        current_session_instance = None

                        initial_messages_for_setup = [
                            {"type": "SYSTEM",
                             "content": self._get_user_context_for_ai(user_profile, for_setup_prompt=True)},
                            {"type": "USER", "content": "سلام، لطفا برای تکمیل پروفایلم از من سوال بپرسید."}
                        ]
                        metis_response = metis_service.create_chat_session(
                            bot_id=metis_service.bot_id,
                            user_data=self._get_user_info_for_metis_api(user_profile),
                            initial_messages=initial_messages_for_setup
                        )
                        metis_session_id = metis_response.get('id')
                        ai_final_response_content = metis_response.get('content',
                                                                       'سلام! برای شروع، لطفاً در مورد سوابق پزشکی خود توضیح دهید.')

                        if not metis_session_id:
                            logger.error(
                                f"Failed to create Metis session for profile setup for user {user.phone_number}. Response: {metis_response}")
                            user_profile.is_in_profile_setup = False;
                            user_profile.save(update_fields=['is_in_profile_setup'])
                            return Response({"error": "خطا در ایجاد جلسه تنظیم پروفایل با سرویس دستیار."},
                                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                        current_session_instance = AiResponse.objects.create(
                            user=user, ai_session_id=str(uuid.uuid4()), metis_session_id=metis_session_id,
                            ai_response_name=f"Profile Setup - {user.phone_number}",
                            expires_at=timezone.now() + timedelta(
                                hours=user_profile.role.session_duration_hours if user_profile.role else 24)
                        )
                        current_session_instance.add_to_chat_history("system",
                                                                     self._get_user_context_for_ai(user_profile,
                                                                                                   for_setup_prompt=True))
                        current_session_instance.add_to_chat_history("user", CMD_START_SETUP)
                        current_session_instance.add_to_chat_history("assistant", ai_final_response_content)
                        # No _increment_message_count here, as it's a special flow trigger

                elif user_profile.is_in_profile_setup:  # User is already in setup mode
                    if not current_session_instance:
                        logger.error(f"User {user.phone_number} in profile setup but no active session.")
                        return Response(
                            {"detail": "جلسه تنظیم پروفایل شما یافت نشد. لطفاً با 'تکمیل پروفایل' دوباره شروع کنید."},
                            status=status.HTTP_400_BAD_REQUEST)

                    final_session_id_to_return = str(
                        current_session_instance.ai_session_id)  # Set session id for response

                    if user_message_content.lower() == CMD_FINISH_SETUP.lower():
                        logger.info(f"User {user.phone_number} requested to finish profile setup.")
                        current_session_instance.add_to_chat_history("user", user_message_content)

                        setup_chat_history = current_session_instance.get_chat_history()
                        history_text_for_prompt = "\n".join(
                            [f"{msg['role']}: {msg['content']}" for msg in setup_chat_history if
                             msg['role'] != 'system'])
                        full_prompt_for_summarization = PROFILE_SUMMARIZATION_PROMPT_PREFIX + history_text_for_prompt + PROFILE_SUMMARIZATION_PROMPT_SUFFIX

                        logger.info(
                            f"Sending compiled setup chat to Metis for summarization for user {user.phone_number}.")
                        summary_response = metis_service.send_message(
                            session_id=current_session_instance.metis_session_id,
                            content=full_prompt_for_summarization, message_type="USER"
                        )
                        summary_text = summary_response.get('content')
                        if summary_text:
                            user_profile.user_information_summary = summary_text
                            ai_final_response_content = f"اطلاعات پروفایل شما با موفقیت دریافت و خلاصه‌سازی شد."
                            current_session_instance.add_to_chat_history("assistant",
                                                                         ai_final_response_content + f"\nخلاصه: {summary_text}")
                            logger.info(f"Profile summary generated for user {user.phone_number}.")
                        else:
                            ai_final_response_content = "متاسفانه در حال حاضر امکان خلاصه‌سازی اطلاعات شما وجود ندارد. اما اطلاعات شما در طول چت ذخیره شده است."
                            current_session_instance.add_to_chat_history("assistant", ai_final_response_content)
                            logger.error(
                                f"Metis failed to generate summary for user {user.phone_number}. Response: {summary_response}")
                        user_profile.is_in_profile_setup = False
                        user_profile.last_form_submission_time = timezone.now()
                        user_profile.save(update_fields=['is_in_profile_setup', 'last_form_submission_time',
                                                         'user_information_summary'])
                        current_session_instance.is_active = False
                        http_status_code = status.HTTP_200_OK

                    elif user_message_content.lower() == CMD_CANCEL_SETUP.lower():
                        logger.info(f"User {user.phone_number} cancelled profile setup.")
                        user_profile.is_in_profile_setup = False
                        user_profile.save(update_fields=['is_in_profile_setup'])
                        ai_final_response_content = "تکمیل پروفایل لغو شد. شما می‌توانید هر زمان خواستید با ارسال 'تکمیل پروفایل' این فرآیند را مجددا شروع کنید."
                        current_session_instance.add_to_chat_history("user", user_message_content)
                        current_session_instance.add_to_chat_history("assistant", ai_final_response_content)
                        current_session_instance.is_active = False
                        http_status_code = status.HTTP_200_OK

                    else:  # ادامه مکالمه در مد تنظیم پروفایل (Metis سوالات را می‌پرسد)
                        if not self._check_message_limit(user_profile,
                                                         is_profile_setup_flow=True):  # Check specific limit if any
                            return Response({'detail': 'محدودیت پیام در طول تنظیم پروفایل به پایان رسیده است.'},
                                            status=status.HTTP_429_TOO_MANY_REQUESTS)
                        logger.info(
                            f"Continuing profile setup for user {user.phone_number}. Message: {user_message_content}")
                        metis_response_data = metis_service.send_message(
                            session_id=current_session_instance.metis_session_id,
                            content=user_message_content, message_type="USER")
                        ai_final_response_content = metis_response_data.get('content',
                                                                            'پاسخی از طرف دستیار دریافت نشد.')
                        current_session_instance.add_to_chat_history("user", user_message_content)
                        current_session_instance.add_to_chat_history("assistant", ai_final_response_content)
                        http_status_code = status.HTTP_200_OK
                        self._increment_message_count(user_profile,
                                                      is_profile_setup_flow=True)  # Count setup messages differently if needed

                # چت عادی (کاربر در مد تنظیم پروفایل نیست و دستور خاصی هم نداده)
                else:
                    if not self._check_message_limit(user_profile):
                        return Response({'detail': 'محدودیت پیام روزانه شما به پایان رسیده است.'},
                                        status=status.HTTP_429_TOO_MANY_REQUESTS)

                    # داخل AIAgentChatView.post، در بخشی که initial_metis_messages ساخته می‌شود:
                    # ...
                    if not current_session_instance:
                        # ...
                        initial_metis_messages = []
                        # user_context_for_ai = self._get_user_context_for_ai(user_profile) # موقتا غیرفعال شود
                        # if user_context_for_ai: initial_metis_messages.append({"type": "USER", "content": user_context_for_ai})
                        initial_metis_messages.append(
                            {"type": "USER", "content": user_message_content})  # فقط پیام کاربر ارسال شود

                        logger.info(
                            f"Starting new Metis AI session for user {user.phone_number} with SIMPLIFIED initial messages.")
                        user_data_for_metis = self._get_user_info_for_metis_api(user_profile)

                        metis_response = metis_service.create_chat_session(
                            bot_id=metis_service.bot_id,
                            user_data=user_data_for_metis,
                            initial_messages=initial_metis_messages
                        )
                        # ...
                        metis_session_id = metis_response.get('id')
                        ai_final_response_content = metis_response.get('content',
                                                                       'پاسخی از طرف دستیار دریافت نشد (هنگام ایجاد جلسه عادی).')
                        if not metis_session_id:
                            logger.error(
                                f"Failed to create Metis normal session for user {user.phone_number}. Response: {metis_response}")
                            return Response({"error": "خطا در ایجاد جلسه عادی با سرویس دستیار."},
                                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                        current_session_instance = AiResponse.objects.create(
                            user=user, ai_session_id=str(uuid.uuid4()), metis_session_id=metis_session_id,
                            ai_response_name=f"Chat - {user.phone_number} - {datetime.datetime.now().strftime('%H:%M')}",
                            expires_at=timezone.now() + timedelta(
                                hours=user_profile.role.session_duration_hours if user_profile.role else 24)
                        )
                        # Note: Storing potentially large system context in every chat history entry can be verbose.
                        # current_session_instance.add_to_chat_history("system", self._get_user_context_for_ai(user_profile, for_setup_prompt=False))
                        current_session_instance.add_to_chat_history("user", user_message_content)
                        current_session_instance.add_to_chat_history("assistant", ai_final_response_content)
                    # If current_session_instance already existed and was valid, it was handled at the top, and metis_ai_response_content is already set.
                    http_status_code = status.HTTP_200_OK

                # ذخیره نهایی و افزایش شمارنده پیام
                if current_session_instance:
                    current_session_instance.save()
                    # شمارنده پیام فقط برای پیام‌های عادی یا پیام‌های طی فرآیند تنظیم پروفایل (به جز دستورات خاص)
                    if not (user_profile.is_in_profile_setup and user_message_content.lower() in [
                        CMD_FINISH_SETUP.lower(), CMD_CANCEL_SETUP.lower()]) and \
                            not (
                                    user_message_content.lower() == CMD_START_SETUP.lower() and ai_final_response_content != f"شما فقط هر {user_profile.role.form_submission_interval_hours if user_profile.role else 24} ساعت یکبار می‌توانید اطلاعات پروفایل را تکمیل یا اصلاح کنید. لطفاً پس از حدود {int(((user_profile.last_form_submission_time + timedelta(hours=user_profile.role.form_submission_interval_hours if user_profile.role else 24)) - timezone.now()).total_seconds() / 3600)} ساعت و {int((((user_profile.last_form_submission_time + timedelta(hours=user_profile.role.form_submission_interval_hours if user_profile.role else 24)) - timezone.now()).total_seconds() % 3600) / 60)} دقیقه دیگر تلاش کنید."):
                        self._increment_message_count(user_profile)

                    final_session_id_to_return = str(current_session_instance.ai_session_id)
                    final_chat_history = current_session_instance.get_chat_history()
                else:  # Fallback if somehow no session instance was set (should be rare)
                    if not final_session_id_to_return and session_id_from_request:  # If original session_id was provided but became invalid
                        final_session_id_to_return = session_id_from_request  # Return original requested session_id
                    # If no session was ever found or created, final_session_id_to_return will be None
                    ai_final_response_content = "خطایی در مدیریت جلسه رخ داد."
                    http_status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

                return Response({
                    'ai_response': ai_final_response_content,
                    'session_id': final_session_id_to_return,
                    'chat_history': final_chat_history,
                }, status=http_status_code)

        except ConnectionError as e_conn:
            logger.error(f"Metis AI Connection Error in AIAgentChatView for user {user.phone_number}: {e_conn}",
                         exc_info=True)
            return Response({"error": "خطا در ارتباط با سرویس دستیار هوشمند. لطفاً کمی بعد دوباره تلاش کنید.",
                             "details": str(e_conn) if settings.DEBUG else "Service connection error"},
                            status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception as e:
            logger.error(f"Error in AIAgentChatView for user {user.phone_number}: {e}", exc_info=True)
            return Response({"error": "یک خطای داخلی رخ داده است. لطفاً بعداً تلاش کنید.",
                             "details": str(e) if settings.DEBUG else "Internal server error"},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ----------------------------------------------------
# General Views for AiChatSession and PsychTestHistory
# ----------------------------------------------------
from rest_framework.exceptions import PermissionDenied


class AiChatSessionListCreate(generics.ListCreateAPIView):
    queryset = AiResponse.objects.all()
    serializer_class = AiResponseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self): return self.queryset.filter(user=self.request.user, is_active=True).order_by('-created_at')

    def perform_create(self, serializer):
        logger.warning(
            "Direct creation of AiChatSession via API is handled by AIAgentChatView. This endpoint is for listing.")
        raise PermissionDenied("Sessions are created via the AI chat endpoint.")


class AiChatSessionDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = AiResponse.objects.all()
    serializer_class = AiResponseSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'pk'  # Assuming you want to lookup by AiResponse PK for direct access, or ai_session_id (UUID)

    def get_object(self):
        # Allow lookup by either PK or ai_session_id (UUID string)
        queryset = self.filter_queryset(self.get_queryset())
        pk = self.kwargs.get(self.lookup_field)

        if pk is not None:
            try:  # Try UUID first if your pk might be ai_session_id
                uuid_pk = uuid.UUID(str(pk))  # Ensure pk is string for UUID conversion
                return get_object_or_404(queryset, ai_session_id=str(uuid_pk))
            except ValueError:  # If not a valid UUID, assume it's an integer PK
                try:
                    int_pk = int(pk)
                    return get_object_or_404(queryset, pk=int_pk)
                except (ValueError, TypeError):
                    raise Http404("Session not found with the provided ID format.")
        raise Http404("Session ID not provided in URL.")

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
        instance.delete()
        logger.info(
            f"Local AiResponse session {instance.ai_session_id} deleted for user {self.request.user.phone_number}.")


class TestTimeView(APIView):
    permission_classes = [IsMetisToolCallback]

    def get(self, request, *args, **kwargs):
        logger.info(f"Tool {self.__class__.__name__} - Request Query Params: {request.query_params}")
        logger.info(f"Tool {self.__class__.__name__} - Request Data: {request.data}")
        now = datetime.datetime.now().isoformat()
        logger.info(f"TestTimeView (test-tool-status-minimal) called. Returning current time: {now}")
        return Response({"currentTime": now, "status": "ok", "message": "Test endpoint for Metis tool is working!"})


class PsychTestHistoryView(generics.ListCreateAPIView):
    queryset = PsychTestHistory.objects.all()
    serializer_class = PsychTestHistorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser: return PsychTestHistory.objects.all().select_related('user')
        return PsychTestHistory.objects.filter(user=user).select_related('user')

    def perform_create(self, serializer): serializer.save(user=self.request.user)


class PsychTestHistoryDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = PsychTestHistory.objects.all()
    serializer_class = PsychTestHistorySerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'pk'

    def get_queryset(self): return PsychTestHistory.objects.filter(user=self.request.user)