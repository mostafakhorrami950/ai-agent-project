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
    AIAgentChatView, AiChatSessionListCreate, AiChatSessionDetail,TestTimeView
)

urlpatterns = [
    path('register/', RegisterUserView.as_view(), name='register'),
    path('login/', LoginUserView.as_view(), name='login'),
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
    path('ai-agent/chat/', AIAgentChatView.as_view(), name='ai-agent-chat'),  # مسیر چت AI
    path('ai-sessions/', AiChatSessionListCreate.as_view(), name='ai-sessions'),
    path('ai-sessions/<int:pk>/', AiChatSessionDetail.as_view(), name='ai-session-detail'),
path('test-tool-status-minimal/', TestTimeView.as_view(), name='test-tool-status-minimal'),
]