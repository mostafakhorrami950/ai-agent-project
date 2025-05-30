# users_ai/urls.py

from django.urls import path
# from rest_framework_simplejwt.views import ( # اگر از TokenObtainPairView, TokenRefreshView مستقیما استفاده نمی‌کنید، لازم نیست
#     TokenObtainPairView,
#     TokenRefreshView,
# )
from .views import (
    RegisterUserView, LoginUserView,
    UserProfileDetail, HealthRecordDetail, PsychologicalProfileDetail,
    CareerEducationDetail, FinancialInfoDetail, SocialRelationshipDetail,
    PreferenceInterestDetail, EnvironmentalContextDetail, RealTimeDataDetail,
    FeedbackLearningDetail,  # این ویو در فایل views.py شما UserSpecificOneToOneViewSet است.
    GoalListCreate, GoalDetail, HabitListCreate, HabitDetail,
    AIAgentChatView, AiChatSessionListCreate, AiChatSessionDetail, TestTimeView, PsychTestHistoryView,
    PsychTestHistoryDetail,  # این ویو را در فایل views.py قبلی داشتید، اضافه می‌کنم
    # Tool Views
    ToolUpdateUserProfileDetailsView, ToolUpdateHealthRecordView, ToolUpdatePsychologicalProfileView,
    ToolUpdateCareerEducationView, ToolUpdateFinancialInfoView, ToolUpdateSocialRelationshipView,
    ToolUpdatePreferenceInterestView, ToolUpdateEnvironmentalContextView, ToolUpdateRealTimeDataView,
    ToolUpdateFeedbackLearningView,  # این ویو در فایل views.py شما اکنون فقط متد POST دارد
    ToolCreateGoalView, ToolUpdateGoalView, ToolDeleteGoalView,
    ToolCreateHabitView, ToolUpdateHabitView, ToolDeleteHabitView,
    ToolCreatePsychTestRecordView, ToolUpdatePsychTestRecordView, ToolDeletePsychTestRecordView
)

urlpatterns = [
    path('register/', RegisterUserView.as_view(), name='register'),
    path('login/', LoginUserView.as_view(), name='login'),

    # User-facing API endpoints (Authenticated)
    path('profile/', UserProfileDetail.as_view(), name='user-profile-detail'),  # نامگذاری بهتر
    path('health/', HealthRecordDetail.as_view(), name='health-record-detail'),
    path('psych/', PsychologicalProfileDetail.as_view(), name='psychological-profile-detail'),
    path('career/', CareerEducationDetail.as_view(), name='career-education-detail'),
    path('finance/', FinancialInfoDetail.as_view(), name='financial-info-detail'),
    path('social/', SocialRelationshipDetail.as_view(), name='social-relationship-detail'),
    path('preferences/', PreferenceInterestDetail.as_view(), name='preference-interest-detail'),
    path('environment/', EnvironmentalContextDetail.as_view(), name='environmental-context-detail'),
    path('realtime/', RealTimeDataDetail.as_view(), name='realtime-data-detail'),
    path('feedback/', FeedbackLearningDetail.as_view(), name='feedback-learning-detail'),  # اگر این OneToOne است

    path('goals/', GoalListCreate.as_view(), name='goal-list-create'),
    path('goals/<int:pk>/', GoalDetail.as_view(), name='goal-detail'),

    path('habits/', HabitListCreate.as_view(), name='habit-list-create'),
    path('habits/<int:pk>/', HabitDetail.as_view(), name='habit-detail'),
    # این URL به ویویی اشاره دارد که pk را از URL می‌گیرد

    path('psych-test-history/', PsychTestHistoryView.as_view(), name='psych-test-history-list-create'),
    path('psych-test-history/<int:pk>/', PsychTestHistoryDetail.as_view(), name='psych-test-history-detail'),

    path('ai-agent/chat/', AIAgentChatView.as_view(), name='ai-agent-chat'),
    path('ai-sessions/', AiChatSessionListCreate.as_view(), name='ai-session-list'),  # Create از طریق chat انجام می‌شود
    path('ai-sessions/<uuid:pk>/', AiChatSessionDetail.as_view(), name='ai-session-detail'),
    # اگر ai_session_id شما UUID است، pk را به uuid تغییر دهید
    # یا اگر از id عددی پیش‌فرض برای AiResponse استفاده می‌کنید:
    # path('ai-sessions/<int:pk>/', AiChatSessionDetail.as_view(), name='ai-session-detail'),

    path('test-tool-status-minimal/', TestTimeView.as_view(), name='test-tool-status-minimal'),

    # ----------------------------------------------------
    # Metis AI Tool Callback Endpoints
    # ----------------------------------------------------
    path('tools/profile/update/', ToolUpdateUserProfileDetailsView.as_view(), name='tool-update-profile'),
    path('tools/health/update/', ToolUpdateHealthRecordView.as_view(), name='tool-update-health'),
    path('tools/psych/update/', ToolUpdatePsychologicalProfileView.as_view(), name='tool-update-psych'),
    path('tools/career/update/', ToolUpdateCareerEducationView.as_view(), name='tool-update-career'),
    path('tools/finance/update/', ToolUpdateFinancialInfoView.as_view(), name='tool-update-finance'),
    path('tools/social/update/', ToolUpdateSocialRelationshipView.as_view(), name='tool-update-social'),
    path('tools/preferences/update/', ToolUpdatePreferenceInterestView.as_view(), name='tool-update-preferences'),
    path('tools/environment/update/', ToolUpdateEnvironmentalContextView.as_view(), name='tool-update-environment'),
    path('tools/realtime/update/', ToolUpdateRealTimeDataView.as_view(), name='tool-update-realtime'),

    # ToolUpdateFeedbackLearningView اکنون فقط POST را می‌پذیرد، نام مسیر شاید نیاز به تغییر داشته باشد
    # اگر فقط برای ایجاد است، بهتر است /create/ باشد، اما برای سازگاری با نام ویو فعلی نگه داشته شده
    path('tools/feedback/update/', ToolUpdateFeedbackLearningView.as_view(), name='tool-create-feedback'),

    path('tools/goals/create/', ToolCreateGoalView.as_view(), name='tool-create-goal'),
    path('tools/goals/update/', ToolUpdateGoalView.as_view(), name='tool-update-goal'),
    path('tools/goals/delete/', ToolDeleteGoalView.as_view(), name='tool-delete-goal'),

    path('tools/habits/create/', ToolCreateHabitView.as_view(), name='tool-create-habit'),
    # ToolUpdateHabitView و ToolDeleteHabitView در ویو pk را از URL می‌گیرند
    path('tools/habits/update/<int:pk>/', ToolUpdateHabitView.as_view(), name='tool-update-habit'),
    path('tools/habits/delete/<int:pk>/', ToolDeleteHabitView.as_view(), name='tool-delete-habit'),

    path('tools/psych-test-history/create/', ToolCreatePsychTestRecordView.as_view(), name='tool-create-psych-test'),
    path('tools/psych-test-history/update/', ToolUpdatePsychTestRecordView.as_view(), name='tool-update-psych-test'),
    path('tools/psych-test-history/delete/', ToolDeletePsychTestRecordView.as_view(), name='tool-delete-psych-test'),
]