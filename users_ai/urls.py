# users_ai/urls.py

from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import (
    RegisterUserView, LoginUserView,
    UserProfileDetail, HealthRecordDetail, PsychologicalProfileDetail,
    CareerEducationDetail, FinancialInfoDetail, SocialRelationshipDetail,
    PreferenceInterestDetail, EnvironmentalContextDetail, RealTimeDataDetail,
    FeedbackLearningDetail,
    GoalListCreate, GoalDetail, HabitListCreate, HabitDetail,
    AIAgentChatView, AiChatSessionListCreate, AiChatSessionDetail, TestTimeView, PsychTestHistoryView,
    # New Tool Views
    ToolUpdateUserProfileDetailsView, ToolUpdateHealthRecordView, ToolUpdatePsychologicalProfileView,
    ToolUpdateCareerEducationView, ToolUpdateFinancialInfoView, ToolUpdateSocialRelationshipView,
    ToolUpdatePreferenceInterestView, ToolUpdateEnvironmentalContextView, ToolUpdateRealTimeDataView,
    ToolUpdateFeedbackLearningView,
    ToolCreateGoalView, ToolUpdateGoalView, ToolDeleteGoalView,  # Goal tools
    ToolCreateHabitView, ToolUpdateHabitView, ToolDeleteHabitView,  # Habit tools
    ToolCreatePsychTestRecordView, ToolUpdatePsychTestRecordView, ToolDeletePsychTestRecordView  # PsychTest tools
)

urlpatterns = [
    path('register/', RegisterUserView.as_view(), name='register'),
    path('login/', LoginUserView.as_view(), name='login'),

    # User-facing API endpoints (Authenticated)
    path('profile/', UserProfileDetail.as_view(), name='profile'),
    path('health/', HealthRecordDetail.as_view(), name='health'),
    path('psych/', PsychologicalProfileDetail.as_view(), name='psych'),
    path('career/', CareerEducationDetail.as_view(), name='career'),
    path('finance/', FinancialInfoDetail.as_view(), name='finance'),
    path('social/', SocialRelationshipDetail.as_view(), name='social'),
    path('preferences/', PreferenceInterestDetail.as_view(), name='preferences'),
    path('environment/', EnvironmentalContextDetail.as_view(), name='environment'),
    path('realtime/', RealTimeDataDetail.as_view(), name='realtime'),
    path('feedback/', FeedbackLearningDetail.as_view(), name='feedback'),
    path('goals/', GoalListCreate.as_view(), name='goals-list'),
    path('goals/<int:pk>/', GoalDetail.as_view(), name='goal-detail'),
    path('habits/', HabitListCreate.as_view(), name='habits-list'),
    path('habits/<int:pk>/', HabitDetail.as_view(), name='habit-detail'),
    path('psych-test/history/', PsychTestHistoryView.as_view(), name='psych-test-history'),
    path('ai-agent/chat/', AIAgentChatView.as_view(), name='ai-agent-chat'),
    path('ai-sessions/', AiChatSessionListCreate.as_view(), name='ai-sessions'),
    path('ai-sessions/<int:pk>/', AiChatSessionDetail.as_view(), name='ai-session-detail'),
    path('test-tool-status-minimal/', TestTimeView.as_view(), name='test-tool-status-minimal'),

    # ----------------------------------------------------
    # Metis AI Tool Callback Endpoints (Protected by IsMetisToolCallback)
    # Metis AI will call these URLs directly.
    # The URL paths should match what you defined in metis_ai_service.py in get_tool_schemas_for_metis_bot().
    # Metis AI will add `?metis_secret_token=YOUR_TOKEN` to these URLs.
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
    path('tools/feedback/update/', ToolUpdateFeedbackLearningView.as_view(), name='tool-update-feedback'),

    path('tools/goals/create/', ToolCreateGoalView.as_view(), name='tool-create-goal'),
    path('tools/goals/update/', ToolUpdateGoalView.as_view(), name='tool-update-goal'),  # <int:pk>/ حذف شد
    path('tools/goals/delete/', ToolDeleteGoalView.as_view(), name='tool-delete-goal'),  # <int:pk>/ حذف شد

    path('tools/habits/create/', ToolCreateHabitView.as_view(), name='tool-create-habit'),
    path('tools/habits/update/', ToolUpdateHabitView.as_view(), name='tool-update-habit'),  # <int:pk>/ حذف شد
    path('tools/habits/delete/', ToolDeleteHabitView.as_view(), name='tool-delete-habit'),

    path('tools/psych-test-history/create/', ToolCreatePsychTestRecordView.as_view(), name='tool-create-psych-test'),
    path('tools/psych-test-history/update/', ToolUpdatePsychTestRecordView.as_view(), name='tool-update-psych-test'),
    # <int:pk>/ حذف شد
    path('tools/psych-test-history/delete/', ToolDeletePsychTestRecordView.as_view(), name='tool-delete-psych-test'),
    # <int:pk>/ حذف شد
]