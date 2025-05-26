# aiagent/urls.py

from django.contrib import admin
from django.urls import path, include # 'include' را اضافه کنید

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('users_ai.urls')), # تمام مسیرهای users_ai را زیر پیشوند /api/ قرار می‌دهیم
]