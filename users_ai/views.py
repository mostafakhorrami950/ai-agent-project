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


# ----------------------------------------------------
# New API Views for Metis AI Tool Callbacks
# ----------------------------------------------------

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

        # For OneToOne fields, get_or_create is suitable.
        # The 'defaults' will only be used if the object is being created.
        defaults_for_create = profile_data_for_serializer.copy()
        profile, created = UserProfile.objects.get_or_create(user=user, defaults=defaults_for_create)

        serializer = UserProfileSerializer(profile, data=profile_data_for_serializer, partial=True,
                                           context={'request': request})
        if serializer.is_valid():
            serializer.save()
            action_message = 'ایجاد' if created else 'به‌روز'
            response_status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
            logger.info(f"Tool: UserProfile details {action_message} for user {user.phone_number}.")
            return Response(
                {"status": "success",
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
            return Response({
                "status": "success",
                "message": f"اطلاعات سلامتی کاربر {user.phone_number} با موفقیت {action_message} شد.",
                "data": serializer.data
            }, status=response_status_code)
        else:
            logger.error(
                f"Tool: Error updating/creating HealthRecord for user {user.phone_number}: {serializer.errors}")
            return Response({
                "status": "error", "message": "خطا در اعتبارسنجی اطلاعات سلامتی.", "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)


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

        profile_data_for_serializer = request.data.copy()
        profile_data_for_serializer.pop('user_id', None)
        defaults_for_create = profile_data_for_serializer.copy()
        record, created = PsychologicalProfile.objects.get_or_create(user=user, defaults=defaults_for_create)
        serializer = PsychologicalProfileSerializer(record, data=profile_data_for_serializer, partial=True,
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

        career_data_for_serializer = request.data.copy()
        career_data_for_serializer.pop('user_id', None)
        defaults_for_create = career_data_for_serializer.copy()
        record, created = CareerEducation.objects.get_or_create(user=user, defaults=defaults_for_create)
        serializer = CareerEducationSerializer(record, data=career_data_for_serializer, partial=True,
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

        financial_data_for_serializer = request.data.copy()
        financial_data_for_serializer.pop('user_id', None)
        defaults_for_create = financial_data_for_serializer.copy()
        record, created = FinancialInfo.objects.get_or_create(user=user, defaults=defaults_for_create)
        serializer = FinancialInfoSerializer(record, data=financial_data_for_serializer, partial=True,
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

        social_data_for_serializer = request.data.copy()
        social_data_for_serializer.pop('user_id', None)
        defaults_for_create = social_data_for_serializer.copy()
        record, created = SocialRelationship.objects.get_or_create(user=user, defaults=defaults_for_create)
        serializer = SocialRelationshipSerializer(record, data=social_data_for_serializer, partial=True,
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

        preference_data_for_serializer = request.data.copy()
        preference_data_for_serializer.pop('user_id', None)
        defaults_for_create = preference_data_for_serializer.copy()
        record, created = PreferenceInterest.objects.get_or_create(user=user, defaults=defaults_for_create)
        serializer = PreferenceInterestSerializer(record, data=preference_data_for_serializer, partial=True,
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

        env_data_for_serializer = request.data.copy()
        env_data_for_serializer.pop('user_id', None)
        defaults_for_create = env_data_for_serializer.copy()
        record, created = EnvironmentalContext.objects.get_or_create(user=user, defaults=defaults_for_create)
        serializer = EnvironmentalContextSerializer(record, data=env_data_for_serializer, partial=True,
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

        realtime_data_for_serializer = request.data.copy()
        realtime_data_for_serializer.pop('user_id', None)
        realtime_data_for_serializer.pop('timestamp', None)
        defaults_for_create = realtime_data_for_serializer.copy()
        record, created = RealTimeData.objects.get_or_create(user=user, defaults=defaults_for_create)
        serializer = RealTimeDataSerializer(record, data=realtime_data_for_serializer, partial=True,
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
    http_method_names = ['post']  # Changed to POST for creating new feedback, as FeedbackLearning is ForeignKey

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
            return Response({"status": "success",
                             "message": f"بازخورد جدید برای کاربر {user.phone_number} با موفقیت ایجاد شد.",
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

    def patch(self, request, pk, *args, **kwargs):  # pk from URL
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

    def delete(self, request, pk, *args, **kwargs):  # pk from URL
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


# ----------------------------------------------------
# AIAgentChatView (Modified for Metis AI Function Calling flow)
# ----------------------------------------------------

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
        if user_profile.messages_sent_today >= user_profile.role.daily_message_limit:
            logger.warning(
                f"User {user_profile.user.phone_number} reached daily message limit ({user_profile.role.daily_message_limit}).")
            return False
        return True

    def _increment_message_count(self, user_profile):
        now = timezone.localdate()
        if user_profile.last_message_date != now:
            user_profile.messages_sent_today = 0
            user_profile.last_message_date = now
        user_profile.messages_sent_today += 1
        user_profile.save(update_fields=['messages_sent_today', 'last_message_date'])

    def _get_user_info_for_metis_api(self, user_profile: UserProfile):
        user_obj = {"id": str(user_profile.user.id)}
        user_name_parts = []
        if user_profile.first_name: user_name_parts.append(user_profile.first_name)
        if user_profile.last_name: user_name_parts.append(user_profile.last_name)
        if user_name_parts:
            user_obj["name"] = " ".join(user_name_parts)
        elif user_profile.user.phone_number:
            user_obj["name"] = user_profile.user.phone_number
        logger.debug(
            f"Simplified user_info for Metis API (session creation): {json.dumps(user_obj, ensure_ascii=False)}")
        return user_obj

    def _get_user_context_for_ai(self, user_profile: UserProfile):
        context_parts = []
        profile_info_items = [f"شماره موبایل کاربر فعلی: {user_profile.user.phone_number}"]
        if user_profile.first_name: profile_info_items.append(f"نام: {user_profile.first_name}")
        if user_profile.last_name: profile_info_items.append(f"نام خانوادگی: {user_profile.last_name}")
        if user_profile.age is not None: profile_info_items.append(f"سن: {user_profile.age}")
        if user_profile.gender: profile_info_items.append(f"جنسیت: {user_profile.gender}")
        if user_profile.nationality: profile_info_items.append(f"ملیت: {user_profile.nationality}")
        if user_profile.location: profile_info_items.append(f"مکان: {user_profile.location}")
        if user_profile.marital_status: profile_info_items.append(f"وضعیت تأهل: {user_profile.marital_status}")
        if profile_info_items: context_parts.append(
            "اطلاعات پایه و هویتی کاربر:\n" + "\n".join([f"- {item}" for item in profile_info_items]))
        if user_profile.languages: context_parts.append(f"زبان‌ها: {user_profile.languages}")
        if user_profile.cultural_background: context_parts.append(f"پیشینه فرهنگی: {user_profile.cultural_background}")
        try:
            hr = user_profile.user.health_record
            health_details = []
            if hr.medical_history: health_details.append(f"تاریخچه پزشکی: {hr.medical_history}")
            if hr.chronic_conditions: health_details.append(f"بیماری‌های مزمن: {hr.chronic_conditions}")
            if hr.allergies: health_details.append(f"آلرژی‌ها: {hr.allergies}")
            if hr.diet_type: health_details.append(f"رژیم غذایی: {hr.diet_type}")
            if hr.physical_activity_level: health_details.append(f"سطح فعالیت بدنی: {hr.physical_activity_level}")
            if hr.mental_health_status: health_details.append(f"وضعیت سلامت روان: {hr.mental_health_status}")
            if hr.medications: health_details.append(f"داروهای مصرفی: {hr.medications}")
            if health_details: context_parts.append(
                "سوابق سلامتی:\n" + "\n".join([f"- {item}" for item in health_details]))
        except HealthRecord.DoesNotExist:
            pass
        try:
            psych_profile = user_profile.user.psychological_profile
            psych_details = []
            if psych_profile.personality_type: psych_details.append(f"تیپ شخصیتی: {psych_profile.personality_type}")
            if psych_profile.core_values: psych_details.append(f"ارزش‌های اصلی: {psych_profile.core_values}")
            if psych_profile.motivations: psych_details.append(f"انگیزه‌ها: {psych_profile.motivations}")
            if psych_profile.decision_making_style: psych_details.append(
                f"سبک تصمیم‌گیری: {psych_profile.decision_making_style}")
            if psych_profile.stress_response: psych_details.append(f"واکنش به استرس: {psych_profile.stress_response}")
            if psych_profile.emotional_triggers: psych_details.append(
                f"محرک‌های احساسی: {psych_profile.emotional_triggers}")
            if psych_profile.preferred_communication: psych_details.append(
                f"سبک ارتباطی ترجیحی: {psych_profile.preferred_communication}")
            if psych_profile.resilience_level: psych_details.append(f"سطح تاب‌آوری: {psych_profile.resilience_level}")
            if psych_details: context_parts.append(
                "پروفایل روانشناختی:\n" + "\n".join([f"- {item}" for item in psych_details]))
        except PsychologicalProfile.DoesNotExist:
            pass
        if user_profile.user_information_summary: context_parts.append(
            f"خلاصه جامع کاربر (تولید شده توسط AI یا خلاصه‌نویسی شده):\n{user_profile.user_information_summary}")
        full_context = "\n\n".join(filter(None, context_parts))
        logger.debug(
            f"Generated AI context for user {user_profile.user.phone_number}: Context length: {len(full_context)}")
        if len(full_context) > 15000:  # Example limit, adjust as needed
            logger.warning(
                f"Generated AI context for user {user_profile.user.phone_number} is very long: {len(full_context)} chars. Truncating or summarizing might be needed if API limits are hit.")
        return full_context

    def post(self, request, *args, **kwargs):
        user = request.user
        user_profile = get_object_or_404(UserProfile, user=user)
        user_message_content = request.data.get('message')
        session_id_from_request = request.data.get('session_id')
        is_psych_test = request.data.get('is_psych_test', False)
        personality_type = None
        metis_ai_response_content = None
        current_session_instance = None

        if not user_message_content:
            return Response({'detail': 'محتوای پیام الزامی است.'}, status=status.HTTP_400_BAD_REQUEST)
        if not self._check_message_limit(user_profile):
            return Response({'detail': 'محدودیت پیام روزانه شما به پایان رسیده است.'},
                            status=status.HTTP_429_TOO_MANY_REQUESTS)

        metis_service = MetisAIService()
        active_sessions = self._get_active_sessions_for_user(user)

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
                            logger.info(
                                f"Continuing existing Metis AI session {current_session_instance.metis_session_id} for user {user.phone_number}")
                            metis_response_data = metis_service.send_message(
                                session_id=current_session_instance.metis_session_id,
                                content=user_message_content, message_type="USER")
                            metis_ai_response_content = metis_response_data.get('content',
                                                                                'پاسخی از طرف دستیار دریافت نشد.')
                            current_session_instance.add_to_chat_history("user", user_message_content)
                            current_session_instance.add_to_chat_history("assistant", metis_ai_response_content)
                    else:
                        logger.warning(
                            f"Session ID {session_id_from_request} provided but not found or inactive for user {user.phone_number}.")
                        # Decide: either create a new session or return error.
                        # For now, let's try to create a new one if not found.
                        current_session_instance = None  # Ensure new session creation if ID was invalid

                if not current_session_instance:
                    logger.info(
                        f"No valid active session found or provided. Attempting to create a new session for user {user.phone_number}.")
                    if not is_psych_test and user_profile.role and active_sessions.count() >= user_profile.role.max_active_sessions:
                        return Response({
                                            'detail': f'شما به حداکثر تعداد جلسات فعال ({user_profile.role.max_active_sessions}) رسیده‌اید.'},
                                        status=status.HTTP_400_BAD_REQUEST)

                    initial_metis_messages = []
                    user_context_for_ai = self._get_user_context_for_ai(user_profile)
                    if user_context_for_ai: initial_metis_messages.append(
                        {"type": "USER", "content": user_context_for_ai})
                    initial_metis_messages.append({"type": "USER", "content": user_message_content})

                    logger.info(
                        f"Starting new Metis AI session for user {user.phone_number} with {len(initial_metis_messages)} initial messages.")
                    user_data_for_metis = self._get_user_info_for_metis_api(user_profile)

                    # Removed 'functions' parameter from create_chat_session
                    metis_response = metis_service.create_chat_session(
                        bot_id=metis_service.bot_id,
                        user_data=user_data_for_metis,
                        initial_messages=initial_metis_messages
                    )
                    metis_session_id = metis_response.get('id')
                    metis_ai_response_content = metis_response.get('content',
                                                                   'پاسخی از طرف دستیار دریافت نشد (هنگام ایجاد جلسه).')

                    if not metis_session_id:
                        logger.error(
                            f"Failed to create Metis session for user {user.phone_number}. Response: {metis_response}")
                        return Response({"error": "خطا در ایجاد جلسه با سرویس دستیار هوشمند."},
                                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                    session_name = "Psychological Test" if is_psych_test else f"Chat Session {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
                    duration_hours = 24
                    if user_profile.role:
                        duration_hours = user_profile.role.psych_test_duration_hours if is_psych_test else user_profile.role.session_duration_hours
                    else:
                        logger.warning(
                            f"User {user_profile.user.phone_number} has no role, using default session duration.")

                    current_session_instance = AiResponse.objects.create(
                        user=user, ai_session_id=str(uuid.uuid4()), metis_session_id=metis_session_id,
                        ai_response_name=session_name,
                        expires_at=timezone.now() + timezone.timedelta(hours=duration_hours))

                    if user_context_for_ai: current_session_instance.add_to_chat_history("system",
                                                                                         f"Initial context: {user_context_for_ai}")
                    current_session_instance.add_to_chat_history("user", user_message_content)
                    current_session_instance.add_to_chat_history("assistant", metis_ai_response_content)

                    if is_psych_test:
                        PsychTestHistory.objects.create(user=user, test_name="MBTI Psychological Test",
                                                        test_result_summary="تست در حال انجام است.",
                                                        full_test_data=None,
                                                        ai_analysis="تحلیل تست پس از تکمیل انجام خواهد شد.")

                if is_psych_test and metis_ai_response_content:
                    try:
                        if isinstance(metis_ai_response_content, str):
                            try:
                                parsed_content = json.loads(metis_ai_response_content)
                                if isinstance(parsed_content,
                                              dict) and 'personality_type' in parsed_content: personality_type = \
                                parsed_content['personality_type']
                            except json.JSONDecodeError:
                                logger.debug(f"Psych test AI response is not direct JSON: {metis_ai_response_content}")
                        elif isinstance(metis_ai_response_content,
                                        dict) and 'personality_type' in metis_ai_response_content:
                            personality_type = metis_ai_response_content['personality_type']
                    except Exception as e_parse:
                        logger.error(f"Error parsing personality_type from AI response: {e_parse}")
                    if personality_type:
                        user_profile.ai_psychological_test = json.dumps(
                            {"responses": current_session_instance.get_chat_history(),
                             "personality_type": personality_type}, ensure_ascii=False)
                        user_profile.save(update_fields=['ai_psychological_test'])
                        current_session_instance.is_active = False
                        psych_test_record = PsychTestHistory.objects.filter(user=user,
                                                                            test_name="MBTI Psychological Test").order_by(
                            '-test_date').first()
                        if psych_test_record and psych_test_record.test_result_summary == "تست در حال انجام است.":
                            psych_test_record.test_result_summary = f"تیپ شخصیتی: {personality_type}"
                            psych_test_record.full_test_data = current_session_instance.get_chat_history()
                            psych_test_record.ai_analysis = metis_ai_response_content
                            psych_test_record.save()

                current_session_instance.save()
                self._increment_message_count(user_profile)
                return Response({
                    'ai_response': metis_ai_response_content,
                    'session_id': str(current_session_instance.ai_session_id),
                    'chat_history': current_session_instance.get_chat_history(),
                    'personality_type': personality_type
                }, status=status.HTTP_200_OK)
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
        instance.delete()
        logger.info(
            f"Local AiResponse session {instance.ai_session_id} deleted for user {self.request.user.phone_number}.")


class TestTimeView(APIView):
    permission_classes = [IsMetisToolCallback]  # بازگرداندن به حالت اولیه یا AllowAny برای تست بدون توکن

    def get(self, request, *args, **kwargs):
        logger.info(f"Tool {self.__class__.__name__} - Request Query Params: {request.query_params}")
        logger.info(f"Tool {self.__class__.__name__} - Request Data: {request.data}")
        now = datetime.datetime.now().isoformat()
        logger.info(f"TestTimeView (test-tool-status-minimal) called. Returning current time: {now}")
        return Response({"currentTime": now, "status": "ok", "message": "Test endpoint for Metis tool is working!"})


# ----------------------------------------------------
# Psych Test History Views
# ----------------------------------------------------
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