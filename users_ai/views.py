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
from .permissions import IsMetisToolCallback  # مطمئن شوید این ایمپورت وجود دارد
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
        # ایجاد UserProfile برای کاربر جدید
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
# These views will be called by Metis AI directly when it decides to use a tool.
# They will use the IsMetisToolCallback permission.
# Each tool needs to receive the `user_id` as part of its payload from Metis AI.
# ----------------------------------------------------

class ToolUpdateUserProfileDetailsView(APIView):
    permission_classes = [IsMetisToolCallback]
    http_method_names = ['patch']

    def patch(self, request, *args, **kwargs):
        user_id = request.data.get('user_id')
        if not user_id:
            logger.error("Tool call for update_user_profile_details received without user_id.")
            return Response({"error": "User ID is required for tool calls."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            logger.error(f"User with ID {user_id} not found for tool call.")
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        profile = get_object_or_404(UserProfile, user=user)
        serializer = UserProfileSerializer(profile, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            logger.info(f"Tool: UserProfile details updated for user {user.phone_number}.")
            return Response(
                {"status": "success", "message": f"جزئیات پروفایل کاربر {user.phone_number} با موفقیت به‌روز شد.",
                 "data": serializer.data}, status=status.HTTP_200_OK)
        else:
            logger.error(f"Tool: Error updating user profile details for {user.phone_number}: {serializer.errors}")
            return Response(
                {"status": "error", "message": "خطا در به‌روزرسانی جزئیات پروفایل.", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST)


class ToolUpdateHealthRecordView(APIView):
    permission_classes = [IsMetisToolCallback]
    http_method_names = ['patch']

    def patch(self, request, *args, **kwargs):
        user_id = request.data.get('user_id')
        if not user_id:
            logger.error("Tool call for update_health_record received without user_id.")
            return Response({"error": "User ID is required for tool calls."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            logger.error(f"User with ID {user_id} not found for tool call.")
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        record, created = HealthRecord.objects.get_or_create(user=user)
        serializer = HealthRecordSerializer(record, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            logger.info(f"Tool: HealthRecord {'created' if created else 'updated'} for user {user.phone_number}.")
            return Response({"status": "success",
                             "message": f"اطلاعات سلامتی کاربر {user.phone_number} {'ایجاد' if created else 'به‌روز'} شد.",
                             "data": serializer.data}, status=status.HTTP_200_OK)
        else:
            logger.error(f"Tool: Error updating HealthRecord for user {user.phone_number}: {serializer.errors}")
            return Response({"status": "error", "message": "خطا در اطلاعات سلامتی.", "errors": serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)


class ToolUpdatePsychologicalProfileView(APIView):
    permission_classes = [IsMetisToolCallback]
    http_method_names = ['patch']

    def patch(self, request, *args, **kwargs):
        user_id = request.data.get('user_id')
        if not user_id:
            logger.error("Tool call for update_psychological_profile received without user_id.")
            return Response({"error": "User ID is required for tool calls."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            logger.error(f"User with ID {user_id} not found for tool call.")
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        record, created = PsychologicalProfile.objects.get_or_create(user=user)
        serializer = PsychologicalProfileSerializer(record, data=request.data, partial=True,
                                                    context={'request': request})
        if serializer.is_valid():
            serializer.save()
            logger.info(
                f"Tool: PsychologicalProfile {'created' if created else 'updated'} for user {user.phone_number}.")
            return Response({"status": "success",
                             "message": f"پروفایل روانشناختی کاربر {user.phone_number} {'ایجاد' if created else 'به‌روز'} شد.",
                             "data": serializer.data}, status=status.HTTP_200_OK)
        else:
            logger.error(f"Tool: Error updating PsychologicalProfile for user {user.phone_number}: {serializer.errors}")
            return Response({"status": "error", "message": "خطا در پروفایل روانشناختی.", "errors": serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)


class ToolUpdateCareerEducationView(APIView):
    permission_classes = [IsMetisToolCallback]
    http_method_names = ['patch']

    def patch(self, request, *args, **kwargs):
        user_id = request.data.get('user_id')
        if not user_id:
            logger.error("Tool call for update_career_education received without user_id.")
            return Response({"error": "User ID is required for tool calls."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            logger.error(f"User with ID {user_id} not found for tool call.")
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        record, created = CareerEducation.objects.get_or_create(user=user)
        serializer = CareerEducationSerializer(record, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            logger.info(f"Tool: CareerEducation {'created' if created else 'updated'} for user {user.phone_number}.")
            return Response({"status": "success",
                             "message": f"اطلاعات شغلی/تحصیلی کاربر {user.phone_number} {'ایجاد' if created else 'به‌روز'} شد.",
                             "data": serializer.data}, status=status.HTTP_200_OK)
        else:
            logger.error(f"Tool: Error updating CareerEducation for user {user.phone_number}: {serializer.errors}")
            return Response({"status": "error", "message": "خطا در اطلاعات شغلی/تحصیلی.", "errors": serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)


class ToolUpdateFinancialInfoView(APIView):
    permission_classes = [IsMetisToolCallback]
    http_method_names = ['patch']

    def patch(self, request, *args, **kwargs):
        user_id = request.data.get('user_id')
        if not user_id:
            logger.error("Tool call for update_financial_info received without user_id.")
            return Response({"error": "User ID is required for tool calls."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            logger.error(f"User with ID {user_id} not found for tool call.")
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        record, created = FinancialInfo.objects.get_or_create(user=user)
        serializer = FinancialInfoSerializer(record, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            logger.info(f"Tool: FinancialInfo {'created' if created else 'updated'} for user {user.phone_number}.")
            return Response({"status": "success",
                             "message": f"اطلاعات مالی کاربر {user.phone_number} {'ایجاد' if created else 'به‌روز'} شد.",
                             "data": serializer.data}, status=status.HTTP_200_OK)
        else:
            logger.error(f"Tool: Error updating FinancialInfo for user {user.phone_number}: {serializer.errors}")
            return Response({"status": "error", "message": "خطا در اطلاعات مالی.", "errors": serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)


class ToolUpdateSocialRelationshipView(APIView):
    permission_classes = [IsMetisToolCallback]
    http_method_names = ['patch']

    def patch(self, request, *args, **kwargs):
        user_id = request.data.get('user_id')
        if not user_id:
            logger.error("Tool call for update_social_relationship received without user_id.")
            return Response({"error": "User ID is required for tool calls."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            logger.error(f"User with ID {user_id} not found for tool call.")
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        record, created = SocialRelationship.objects.get_or_create(user=user)
        serializer = SocialRelationshipSerializer(record, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            logger.info(f"Tool: SocialRelationship {'created' if created else 'updated'} for user {user.phone_number}.")
            return Response({"status": "success",
                             "message": f"اطلاعات روابط اجتماعی کاربر {user.phone_number} {'ایجاد' if created else 'به‌روز'} شد.",
                             "data": serializer.data}, status=status.HTTP_200_OK)
        else:
            logger.error(f"Tool: Error updating SocialRelationship for user {user.phone_number}: {serializer.errors}")
            return Response(
                {"status": "error", "message": "خطا در اطلاعات روابط اجتماعی.", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST)


class ToolUpdatePreferenceInterestView(APIView):
    permission_classes = [IsMetisToolCallback]
    http_method_names = ['patch']

    def patch(self, request, *args, **kwargs):
        user_id = request.data.get('user_id')
        if not user_id:
            logger.error("Tool call for update_preference_interest received without user_id.")
            return Response({"error": "User ID is required for tool calls."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            logger.error(f"User with ID {user_id} not found for tool call.")
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        record, created = PreferenceInterest.objects.get_or_create(user=user)
        serializer = PreferenceInterestSerializer(record, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            logger.info(f"Tool: PreferenceInterest {'created' if created else 'updated'} for user {user.phone_number}.")
            return Response({"status": "success",
                             "message": f"ترجیحات و علایق کاربر {user.phone_number} {'ایجاد' if created else 'به‌روز'} شد.",
                             "data": serializer.data}, status=status.HTTP_200_OK)
        else:
            logger.error(f"Tool: Error updating PreferenceInterest for user {user.phone_number}: {serializer.errors}")
            return Response({"status": "error", "message": "خطا در ترجیحات و علایق.", "errors": serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)


class ToolUpdateEnvironmentalContextView(APIView):
    permission_classes = [IsMetisToolCallback]
    http_method_names = ['patch']

    def patch(self, request, *args, **kwargs):
        user_id = request.data.get('user_id')
        if not user_id:
            logger.error("Tool call for update_environmental_context received without user_id.")
            return Response({"error": "User ID is required for tool calls."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            logger.error(f"User with ID {user_id} not found for tool call.")
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        record, created = EnvironmentalContext.objects.get_or_create(user=user)
        serializer = EnvironmentalContextSerializer(record, data=request.data, partial=True,
                                                    context={'request': request})
        if serializer.is_valid():
            serializer.save()
            logger.info(
                f"Tool: EnvironmentalContext {'created' if created else 'updated'} for user {user.phone_number}.")
            return Response({"status": "success",
                             "message": f"زمینه محیطی کاربر {user.phone_number} {'ایجاد' if created else 'به‌روز'} شد.",
                             "data": serializer.data}, status=status.HTTP_200_OK)
        else:
            logger.error(f"Tool: Error updating EnvironmentalContext for user {user.phone_number}: {serializer.errors}")
            return Response({"status": "error", "message": "خطا در زمینه محیطی.", "errors": serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)


class ToolUpdateRealTimeDataView(APIView):
    permission_classes = [IsMetisToolCallback]
    http_method_names = ['patch']

    def patch(self, request, *args, **kwargs):
        user_id = request.data.get('user_id')
        if not user_id:
            logger.error("Tool call for update_real_time_data received without user_id.")
            return Response({"error": "User ID is required for tool calls."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            logger.error(f"User with ID {user_id} not found for tool call.")
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        record, created = RealTimeData.objects.get_or_create(user=user)
        request_data = request.data.copy()
        request_data.pop('timestamp', None)  # timestamp is auto_now_add or managed by model
        serializer = RealTimeDataSerializer(record, data=request_data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            logger.info(f"Tool: RealTimeData {'created' if created else 'updated'} for user {user.phone_number}.")
            return Response({"status": "success",
                             "message": f"داده‌های بلادرنگ کاربر {user.phone_number} {'ایجاد' if created else 'به‌روز'} شد.",
                             "data": serializer.data}, status=status.HTTP_200_OK)
        else:
            logger.error(f"Tool: Error updating RealTimeData for user {user.phone_number}: {serializer.errors}")
            return Response({"status": "error", "message": "خطا در داده‌های بلادرنگ.", "errors": serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)


class ToolUpdateFeedbackLearningView(APIView):
    permission_classes = [IsMetisToolCallback]
    http_method_names = ['patch']

    def patch(self, request, *args, **kwargs):
        user_id = request.data.get('user_id')
        if not user_id:
            logger.error("Tool call for update_feedback_learning received without user_id.")
            return Response({"error": "User ID is required for tool calls."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            logger.error(f"User with ID {user_id} not found for tool call.")
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        record, created = FeedbackLearning.objects.get_or_create(user=user)
        request_data = request.data.copy()
        request_data.pop('timestamp', None)
        serializer = FeedbackLearningSerializer(record, data=request_data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            logger.info(f"Tool: FeedbackLearning {'created' if created else 'updated'} for user {user.phone_number}.")
            return Response({"status": "success",
                             "message": f"بازخورد و یادگیری کاربر {user.phone_number} {'ایجاد' if created else 'به‌روز'} شد.",
                             "data": serializer.data}, status=status.HTTP_200_OK)
        else:
            logger.error(f"Tool: Error updating FeedbackLearning for user {user.phone_number}: {serializer.errors}")
            return Response({"status": "error", "message": "خطا در بازخورد و یادگیری.", "errors": serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)


class ToolCreateGoalView(APIView):
    permission_classes = [IsMetisToolCallback]
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        user_id = request.data.get('user_id')
        if not user_id:
            logger.error("Tool call for create_goal received without user_id.")
            return Response({"error": "User ID is required for tool calls."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            logger.error(f"User with ID {user_id} not found for tool call.")
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = GoalSerializer(data=request.data, context={'request': request})
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

    def patch(self, request, *args, **kwargs):  # pk را از URL حذف کردیم
        user_id = request.data.get('user_id')
        pk = request.data.get('pk')  # pk را از body درخواست می‌گیریم
        if not user_id or not pk:
            logger.error("Tool call for update_goal received without user_id or pk.")
            return Response({"error": "User ID and PK are required for tool calls."},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            logger.error(f"User with ID {user_id} not found for tool call.")
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        goal = get_object_or_404(Goal, pk=pk, user=user)  # Ensure user owns the goal
        serializer = GoalSerializer(goal, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            logger.info(f"Tool: Goal {pk} updated for user {user.phone_number}.")
            return Response({"status": "success", "message": f"هدف {pk} کاربر {user.phone_number} با موفقیت به‌روز شد.",
                             "data": serializer.data}, status=status.HTTP_200_OK)
        else:
            logger.error(f"Tool: Error updating goal {pk} for {user.phone_number}: {serializer.errors}")
            return Response({"status": "error", "message": "خطا در به‌روزرسانی هدف.", "errors": serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)


class ToolDeleteGoalView(APIView):
    permission_classes = [IsMetisToolCallback]
    http_method_names = ['delete']

    def delete(self, request, *args, **kwargs): # pk را از URL حذف کردیم
        user_id = request.data.get('user_id')
        pk = request.data.get('pk') # pk را از body درخواست می‌گیریم
        if not user_id or not pk:
            logger.error("Tool call for delete_goal received without user_id or pk.")
            return Response({"error": "User ID and PK are required for tool calls."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            logger.error(f"User with ID {user_id} not found for tool call.")
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        goal = get_object_or_404(Goal, pk=pk, user=user)
        goal.delete()
        logger.info(f"Tool: Goal {pk} deleted for user {user.phone_number}.")
        return Response({"status": "success", "message": f"هدف {pk} کاربر {user.phone_number} با موفقیت حذف شد."}, status=status.HTTP_204_NO_CONTENT)


class ToolCreateHabitView(APIView):
    permission_classes = [IsMetisToolCallback]
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        user_id = request.data.get('user_id')
        if not user_id:
            logger.error("Tool call for create_habit received without user_id.")
            return Response({"error": "User ID is required for tool calls."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            logger.error(f"User with ID {user_id} not found for tool call.")
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = HabitSerializer(data=request.data, context={'request': request})
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
        user_id = request.data.get('user_id')
        if not user_id:
            logger.error("Tool call for update_habit received without user_id.")
            return Response({"error": "User ID is required for tool calls."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            logger.error(f"User with ID {user_id} not found for tool call.")
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        habit = get_object_or_404(Habit, pk=pk, user=user)
        serializer = HabitSerializer(habit, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            logger.info(f"Tool: Habit {pk} updated for user {user.phone_number}.")
            return Response(
                {"status": "success", "message": f"عادت {pk} کاربر {user.phone_number} با موفقیت به‌روز شد.",
                 "data": serializer.data}, status=status.HTTP_200_OK)
        else:
            logger.error(f"Tool: Error updating habit {pk} for {user.phone_number}: {serializer.errors}")
            return Response({"status": "error", "message": "خطا در به‌روزرسانی عادت.", "errors": serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)


class ToolDeleteHabitView(APIView):
    permission_classes = [IsMetisToolCallback]
    http_method_names = ['delete']

    def delete(self, request, pk, *args, **kwargs):
        user_id = request.data.get('user_id')
        if not user_id:
            logger.error("Tool call for delete_habit received without user_id.")
            return Response({"error": "User ID is required for tool calls."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            logger.error(f"User with ID {user_id} not found for tool call.")
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        habit = get_object_or_404(Habit, pk=pk, user=user)
        habit.delete()
        logger.info(f"Tool: Habit {pk} deleted for user {user.phone_number}.")
        return Response({"status": "success", "message": f"عادت {pk} کاربر {user.phone_number} با موفقیت حذف شد."},
                        status=status.HTTP_204_NO_CONTENT)


class ToolCreatePsychTestRecordView(APIView):
    permission_classes = [IsMetisToolCallback]
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        user_id = request.data.get('user_id')
        if not user_id:
            logger.error("Tool call for create_psych_test_record received without user_id.")
            return Response({"error": "User ID is required for tool calls."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            logger.error(f"User with ID {user_id} not found for tool call.")
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = PsychTestHistorySerializer(data=request.data, context={'request': request})
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

    def patch(self, request, *args, **kwargs): # pk را از URL حذف کردیم
        user_id = request.data.get('user_id')
        pk = request.data.get('pk') # pk را از body درخواست می‌گیریم
        if not user_id or not pk:
            logger.error("Tool call for update_psych_test_record received without user_id or pk.")
            return Response({"error": "User ID and PK are required for tool calls."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            logger.error(f"User with ID {user_id} not found for tool call.")
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        psych_test_record = get_object_or_404(PsychTestHistory, pk=pk, user=user)
        serializer = PsychTestHistorySerializer(psych_test_record, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            logger.info(f"Tool: PsychTestHistory record {pk} updated for user {user.phone_number}.")
            return Response({"status": "success", "message": f"رکورد تست روانشناسی {pk} کاربر {user.phone_number} با موفقیت به‌روز شد.", "data": serializer.data}, status=status.HTTP_200_OK)
        else:
            logger.error(f"Tool: Error updating PsychTestHistory record {pk} for {user.phone_number}: {serializer.errors}")
            return Response({"status": "error", "message": "خطا در به‌روزرسانی رکورد تست روانشناسی.", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class ToolDeletePsychTestRecordView(APIView):
    permission_classes = [IsMetisToolCallback]
    http_method_names = ['delete']

    def delete(self, request, *args, **kwargs): # pk را از URL حذف کردیم
        user_id = request.data.get('user_id')
        pk = request.data.get('pk') # pk را از body درخواست می‌گیریم
        if not user_id or not pk:
            logger.error("Tool call for delete_psych_test_record received without user_id or pk.")
            return Response({"error": "User ID and PK are required for tool calls."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            logger.error(f"User with ID {user_id} not found for tool call.")
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        psych_test_record = get_object_or_404(PsychTestHistory, pk=pk, user=user)
        psych_test_record.delete()
        logger.info(f"Tool: PsychTestHistory record {pk} deleted for user {user.phone_number}.")
        return Response({"status": "success", "message": f"رکورد تست روانشناسی {pk} کاربر {user.phone_number} با موفقیت حذف شد."}, status=status.HTTP_204_NO_CONTENT)


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
        # Mark expired sessions as inactive
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
            # Save will be handled by _increment_message_count or later saves of user_profile

        if user_profile.messages_sent_today >= user_profile.role.daily_message_limit:
            logger.warning(
                f"User {user_profile.user.phone_number} reached daily message limit ({user_profile.role.daily_message_limit}).")
            return False
        return True

    def _increment_message_count(self, user_profile):
        now = timezone.localdate()
        if user_profile.last_message_date != now:  # Reset if it's a new day
            user_profile.messages_sent_today = 0
            user_profile.last_message_date = now
        user_profile.messages_sent_today += 1
        user_profile.save(update_fields=['messages_sent_today', 'last_message_date'])

    def _get_user_info_for_metis_api(self, user_profile: UserProfile):
        """
        Generates a simplified user object suitable for Metis AI's 'user' field during session creation.
        Metis AI expects a simple user object, typically with 'id' and 'name'.
        """
        user_obj = {
            "id": str(user_profile.user.id)
        }

        user_name_parts = []
        if user_profile.first_name:
            user_name_parts.append(user_profile.first_name)
        if user_profile.last_name:
            user_name_parts.append(user_profile.last_name)

        if user_name_parts:
            user_obj["name"] = " ".join(user_name_parts)
        elif user_profile.user.phone_number:
            user_obj["name"] = user_profile.user.phone_number

        logger.debug(
            f"Simplified user_info for Metis API (session creation): {json.dumps(user_obj, ensure_ascii=False)}")
        return user_obj

    def _get_user_context_for_ai(self, user_profile: UserProfile):
        """
        Aggregates various pieces of user information into a detailed system prompt.
        This prompt acts as a detailed initial context for the AI, complementing structured user_data.
        """
        context_parts = []
        profile_info = [
            # f"شناسه کاربر: {user_profile.user.id}", # Already in user_obj for Metis
            f"شماره موبایل کاربر فعلی: {user_profile.user.phone_number}"
        ]
        if user_profile.first_name: profile_info.append(f"نام: {user_profile.first_name}")
        if user_profile.last_name: profile_info.append(f"نام خانوادگی: {user_profile.last_name}")
        if user_profile.age is not None: profile_info.append(f"سن: {user_profile.age}")
        if user_profile.gender: profile_info.append(f"جنسیت: {user_profile.gender}")
        if user_profile.nationality: profile_info.append(f"ملیت: {user_profile.nationality}")
        if user_profile.location: profile_info.append(f"مکان: {user_profile.location}")
        if user_profile.marital_status: profile_info.append(f"وضعیت تأهل: {user_profile.marital_status}")

        # These are better as distinct context parts if they are long
        if user_profile.languages: context_parts.append(f"زبان‌ها: {user_profile.languages}")
        if user_profile.cultural_background: context_parts.append(f"پیشینه فرهنگی: {user_profile.cultural_background}")

        if profile_info:
            context_parts.append("اطلاعات پایه و هویتی کاربر:\n" + "\n".join([f"- {item}" for item in profile_info]))

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
            if health_details:
                context_parts.append("سوابق سلامتی:\n" + "\n".join([f"- {item}" for item in health_details]))
        except HealthRecord.DoesNotExist:
            context_parts.append("سوابق سلامتی ثبت نشده است.")

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
            if psych_details:
                context_parts.append("پروفایل روانشناختی:\n" + "\n".join([f"- {item}" for item in psych_details]))
        except PsychologicalProfile.DoesNotExist:
            context_parts.append("پروفایل روانشناختی ثبت نشده است.")

        if user_profile.user_information_summary:
            context_parts.append(
                f"خلاصه جامع کاربر (تولید شده توسط AI یا خلاصه‌نویسی شده):\n{user_profile.user_information_summary}")

        full_context = "\n\n".join(filter(None, context_parts))  # Filter out empty strings if any part was empty
        logger.debug(f"Generated AI context for user {user_profile.user.phone_number}: {full_context[:500]}...")
        return full_context

    def post(self, request, *args, **kwargs):
        user = request.user
        user_profile = get_object_or_404(UserProfile, user=user)
        user_message_content = request.data.get('message')
        session_id_from_request = request.data.get('session_id')
        is_psych_test = request.data.get('is_psych_test', False)
        personality_type = None  # Initialize

        if not user_message_content:
            return Response({'detail': 'محتوای پیام الزامی است.'}, status=status.HTTP_400_BAD_REQUEST)

        if not self._check_message_limit(user_profile):
            return Response({'detail': 'محدودیت پیام روزانه شما به پایان رسیده است.'},
                            status=status.HTTP_429_TOO_MANY_REQUESTS)

        metis_service = MetisAIService()
        active_sessions = self._get_active_sessions_for_user(user)
        current_session_instance = None
        metis_ai_response_content = None

        try:
            with transaction.atomic():
                # 1. Try to find an existing, active session
                if session_id_from_request:
                    current_session_instance = active_sessions.filter(ai_session_id=session_id_from_request).first()
                    if current_session_instance:
                        if current_session_instance.expires_at and current_session_instance.expires_at < timezone.now():
                            current_session_instance.is_active = False
                            current_session_instance.save(update_fields=['is_active'])
                            logger.warning(
                                f"Session {session_id_from_request} for user {user.phone_number} has expired.")
                            # Allow creating a new session by falling through, or return error:
                            # return Response({'detail': 'جلسه منقضی شده است. لطفا یک جلسه جدید شروع کنید.'}, status=status.HTTP_400_BAD_REQUEST)
                            current_session_instance = None  # Treat as if no session was found to create a new one
                        else:
                            # Existing, valid session found. Send message to it.
                            logger.info(
                                f"Continuing existing Metis AI session {current_session_instance.metis_session_id} for user {user.phone_number}")
                            metis_response_data = metis_service.send_message(
                                session_id=current_session_instance.metis_session_id,
                                content=user_message_content,
                                message_type="USER"
                            )
                            metis_ai_response_content = metis_response_data.get('content',
                                                                                'پاسخی از طرف دستیار دریافت نشد.')
                            current_session_instance.add_to_chat_history("user", user_message_content)
                            current_session_instance.add_to_chat_history("assistant", metis_ai_response_content)
                    else:  # session_id provided but not found or invalid by ai_session_id
                        return Response({'detail': 'جلسه نامعتبر است یا پیدا نشد.'}, status=status.HTTP_404_NOT_FOUND)

                # 2. If no valid existing session instance is identified, create a new one
                if not current_session_instance:
                    if not is_psych_test and user_profile.role and active_sessions.count() >= user_profile.role.max_active_sessions:
                        return Response({
                            'detail': f'شما به حداکثر تعداد جلسات فعال ({user_profile.role.max_active_sessions}) رسیده‌اید. لطفاً یک جلسه قبلی را حذف کنید.'
                        }, status=status.HTTP_400_BAD_REQUEST)

                    initial_metis_messages = []
                    user_context_for_ai = self._get_user_context_for_ai(user_profile)
                    if user_context_for_ai:  # Only add context if it's not empty
                        initial_metis_messages.append({"type": "USER", "content": user_context_for_ai})
                    initial_metis_messages.append({"type": "USER", "content": user_message_content})

                    logger.info(f"Starting new Metis AI session for user {user.phone_number}")

                    user_data_for_metis = self._get_user_info_for_metis_api(user_profile)
                    metis_response = metis_service.create_chat_session(
                        bot_id=metis_service.bot_id,
                        user_data=user_data_for_metis,
                        initial_messages=initial_metis_messages
                    )

                    metis_session_id = metis_response.get('id')
                    metis_ai_response_content = metis_response.get('content', 'پاسخی از طرف دستیار دریافت نشد.')

                    session_name = "Psychological Test" if is_psych_test else f"Chat Session {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"

                    # Determine duration based on UserRole; ensure role exists
                    duration_hours = 24  # Default duration
                    if user_profile.role:
                        duration_hours = user_profile.role.psych_test_duration_hours if is_psych_test else user_profile.role.session_duration_hours
                    else:
                        logger.warning(
                            f"User {user_profile.user.phone_number} has no role, using default session duration.")

                    current_session_instance = AiResponse.objects.create(
                        user=user,
                        ai_session_id=str(uuid.uuid4()),  # Ensure ai_session_id is a string
                        metis_session_id=metis_session_id,
                        ai_response_name=session_name,
                        expires_at=timezone.now() + timezone.timedelta(hours=duration_hours)
                    )
                    # Add initial exchange to chat history for new session
                    if user_context_for_ai:
                        current_session_instance.add_to_chat_history("system",
                                                                     f"Initial context: {user_context_for_ai}")  # Or as USER type
                    current_session_instance.add_to_chat_history("user", user_message_content)
                    current_session_instance.add_to_chat_history("assistant", metis_ai_response_content)

                    if is_psych_test:
                        PsychTestHistory.objects.create(
                            user=user,
                            test_name="MBTI Psychological Test",  # Or make dynamic
                            test_result_summary="تست در حال انجام است.",
                            full_test_data=None,  # Will be filled later
                            ai_analysis="تحلیل تست پس از تکمیل انجام خواهد شد."
                        )

                # 3. Common post-processing for both new and continued sessions
                # Check for personality_type in Metis AI response (especially if psych test)
                # This check should apply to metis_ai_response_content whether from new session or continued
                if is_psych_test and metis_ai_response_content:  # Ensure content is not None
                    try:
                        # Metis might return a string that needs parsing, or structured data
                        # Assuming metis_ai_response_content might be JSON string containing personality_type
                        if isinstance(metis_ai_response_content, str):
                            try:
                                parsed_content = json.loads(metis_ai_response_content)
                                if isinstance(parsed_content, dict) and 'personality_type' in parsed_content:
                                    personality_type = parsed_content['personality_type']
                            except json.JSONDecodeError:
                                # If not JSON, perhaps it's a plain text and AI is expected to mention it in a specific format
                                # This part may need refinement based on actual Metis responses for psych tests
                                logger.debug(f"Psych test AI response is not direct JSON: {metis_ai_response_content}")
                                pass
                        elif isinstance(metis_ai_response_content,
                                        dict) and 'personality_type' in metis_ai_response_content:
                            personality_type = metis_ai_response_content['personality_type']


                    except Exception as e_parse:  # Catch any error during parsing
                        logger.error(f"Error parsing personality_type from AI response: {e_parse}")

                    if personality_type:
                        user_profile.ai_psychological_test = json.dumps({
                            "responses": current_session_instance.get_chat_history(),  # Full history up to this point
                            "personality_type": personality_type
                        }, ensure_ascii=False)
                        user_profile.save(update_fields=['ai_psychological_test'])

                        # Optionally deactivate session after psych test completion
                        current_session_instance.is_active = False

                        # Update PsychTestHistory record
                        psych_test_record = PsychTestHistory.objects.filter(user=user,
                                                                            test_name="MBTI Psychological Test").order_by(
                            '-test_date').first()
                        if psych_test_record and psych_test_record.test_result_summary == "تست در حال انجام است.":
                            psych_test_record.test_result_summary = f"تیپ شخصیتی: {personality_type}"
                            psych_test_record.full_test_data = current_session_instance.get_chat_history()
                            psych_test_record.ai_analysis = metis_ai_response_content  # Store the raw AI response
                            psych_test_record.save()

                current_session_instance.save()  # Save any changes to AiResponse (like chat history, is_active)
                self._increment_message_count(user_profile)

                return Response({
                    'ai_response': metis_ai_response_content,
                    'session_id': str(current_session_instance.ai_session_id),
                    'chat_history': current_session_instance.get_chat_history(),
                    'personality_type': personality_type  # Will be None if not found/applicable
                }, status=status.HTTP_200_OK)

        except ConnectionError as e_conn:  # More specific error handling for Metis
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

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user, is_active=True).order_by('-created_at')

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
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
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
        if user.is_superuser:
            return PsychTestHistory.objects.all().select_related('user')
        return PsychTestHistory.objects.filter(user=user).select_related('user')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class PsychTestHistoryDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = PsychTestHistory.objects.all()
    serializer_class = PsychTestHistorySerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'pk'

    def get_queryset(self):
        return PsychTestHistory.objects.filter(user=self.request.user)