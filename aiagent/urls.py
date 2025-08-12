# aiagent/urls.py

from django.contrib import admin
from django.urls import path, include # 'include' را اضافه کنید
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('users_ai.urls')), # تمام مسیرهای users_ai را زیر پیشوند /api/ قرار می‌دهیم
    path('chat/', TemplateView.as_view(template_name='chat.html'), name='chat-ui'),
]