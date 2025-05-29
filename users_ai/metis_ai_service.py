# users_ai/metis_ai_service.py
import requests
from django.conf import settings
import logging
import json

logger = logging.getLogger(__name__)


class MetisAIService:
    def __init__(self):
        self.base_url = "https://api.metisai.ir/api/v1"
        self.api_key = settings.METIS_API_KEY
        self.bot_id = settings.METIS_BOT_ID
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        if not self.api_key or not self.bot_id:
            logger.error("METIS_API_KEY or METIS_BOT_ID not configured in settings.")
            raise ValueError("Metis AI credentials are not set up.")
        logger.debug("MetisAIService initialized for Bot/Session API.")

    def _make_request(self, method, endpoint, json_data=None, params=None):
        url = f"{self.base_url}/{endpoint}"
        try:
            logger.debug(f"[_make_request] Attempting request to {method} {url}")
            # logger.debug(f"[_make_request] Request Headers: {self.headers}") # Do not log sensitive headers in production
            if json_data:
                logger.debug(
                    f"[_make_request] Request JSON Data: {json.dumps(json_data, indent=2, ensure_ascii=False)}")
            response = requests.request(method, url, headers=self.headers, json=json_data, params=params, timeout=60)
            response.raise_for_status()
            logger.debug(f"[_make_request] Response Status: {response.status_code}")
            logger.debug(f"[_make_request] Response Body: {response.text}")
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            logger.error(
                f"HTTP error occurred: {http_err} - Response: {http_err.response.text if http_err.response else 'No response'}",
                exc_info=True)
            raise
        except requests.exceptions.ConnectionError as conn_err:
            logger.error(f"Connection error occurred: {conn_err}", exc_info=True)
            raise
        except requests.exceptions.Timeout as timeout_err:
            logger.error(f"Timeout error occurred: {timeout_err}", exc_info=True)
            raise
        except requests.exceptions.RequestException as req_err:
            logger.error(f"An unexpected error occurred: {req_err}", exc_info=True)
            raise

    def send_message(self, metis_session_id, message_content, chat_history, user_profile_summary=None):
        """
        Sends a message to an existing Metis AI chat session, including full chat history and user summary.
        """
        endpoint = f"bot/{self.bot_id}/session/{metis_session_id}/message"

        # Prepare the messages list for Metis AI
        messages = []

        # Add user profile summary as a system message if available
        if user_profile_summary:
            messages.append({"role": "system", "content": f"User information summary: {user_profile_summary}"})

        # Add previous chat history
        for msg in chat_history:
            # Metis AI expects 'user' or 'assistant' roles, not 'user'/'bot' potentially
            role = msg['role']
            content = msg['content']
            if role == 'bot':  # اگر در تاریخچه شما 'bot' ذخیره می‌شود
                role = 'assistant'
            messages.append({"role": role, "content": content})

        # Add the current user message
        messages.append({"role": "user", "content": message_content})

        # Prepare the payload for Metis AI
        payload = {
            "messages": messages,  # ارسال کل تاریخچه به Metis AI
            "streaming": False  # اگر نمی‌خواهید پاسخ استریم شود
        }

        try:
            response_data = self._make_request("POST", endpoint, json_data=payload)
            return response_data
        except Exception as e:
            logger.error(f"Error sending message to Metis AI: {e}", exc_info=True)
            raise

    def start_new_chat_session(self, initial_message, user_profile_summary=None):
        """
        Starts a new chat session with Metis AI, optionally including user profile summary.
        """
        endpoint = f"bot/{self.bot_id}/session"

        messages = []
        if user_profile_summary:
            messages.append({"role": "system", "content": f"User information summary: {user_profile_summary}"})

        messages.append({"role": "user", "content": initial_message})

        payload = {
            "messages": messages,
            "streaming": False
        }
        try:
            response_data = self._make_request("POST", endpoint, json_data=payload)
            return response_data
        except Exception as e:
            logger.error(f"Error starting new chat session with Metis AI: {e}", exc_info=True)
            raise

    def delete_chat_session(self, metis_session_id):
        """
        Deletes a Metis AI chat session.
        """
        endpoint = f"bot/{self.bot_id}/session/{metis_session_id}"
        try:
            response_data = self._make_request("DELETE", endpoint)
            logger.info(f"Metis session {metis_session_id} deleted successfully.")
            return response_data
        except Exception as e:
            logger.error(f"Error deleting Metis AI session {metis_session_id}: {e}", exc_info=True)
            raise

    # متد create_arg برای خوانایی بهتر در متد get_bot_tools
    def create_arg(self, name, description, type, required, enum=None):
        arg = {"name": name, "description": description, "type": type, "required": required}
        if enum:
            arg["enum"] = enum
        return arg

    def get_bot_tools(self, django_api_base_url):
        """
        Generates the list of tools for Metis AI to use.
        Includes a placeholder for user_id to be provided by Metis AI when calling tools.
        """
        tools = []

        # Tools for UserProfile
        tools.append({
            "name": "get_user_profile_details",
            "description": "جزئیات پایه و هویتی کاربر را بازیابی می کند.",
            "url": f"{django_api_base_url}/profile/",
            "method": "GET",
            "args": []
            # user_id should be implicit from the session for Metis to send it, or explicitly added by Metis AI
        })
        tools.append({
            "name": "update_user_profile_details",
            "description": "جزئیات اضافی پروفایل کاربر را بروزرسانی یا ثبت می کند.",
            "url": f"{django_api_base_url}/profile/",
            "method": "PATCH",
            "args": [
                self.create_arg("first_name", "نام کوچک کاربر.", "STRING", False),
                self.create_arg("last_name", "نام خانوادگی کاربر.", "STRING", False),
                self.create_arg("age", "سن کاربر.", "INTEGER", False),
                self.create_arg("gender", "جنسیت کاربر.", "STRING", False, ["مرد", "زن", "سایر"]),
                self.create_arg("nationality", "ملیت کاربر.", "STRING", False),
                self.create_arg("location", "محل زندگی کاربر (شهر یا کشور).", "STRING", False),
                self.create_arg("languages", "زبان‌های مورد استفاده کاربر.", "STRING", False),
                self.create_arg("cultural_background", "اطلاعات فرهنگی و ارزش‌های کاربر.", "STRING", False),
                self.create_arg("marital_status", "وضعیت تأهل کاربر.", "STRING", False,
                                ["مجرد", "متأهل", "مطلقه", "جدا شده", "بیوه"]),
                self.create_arg("ai_psychological_test", "نتیجه تست روانشناسی کاربر.", "STRING", False),
                self.create_arg("user_information_summary",
                                "خلاصه‌ای از تمام اطلاعات کاربر که با استفاده از هوش مصنوعی خلاصه شده است.", "STRING",
                                False),
            ]
        })

        # Tools for HealthRecord
        tools.append({
            "name": "get_health_record_details",
            "description": "جزئیات سوابق سلامتی کاربر را بازیابی می کند.",
            "url": f"{django_api_base_url}/health/",
            "method": "GET",
            "args": []
        })
        tools.append({
            "name": "update_health_record",
            "description": "سوابق سلامتی جسمانی و روانی کاربر را بروزرسانی یا ثبت می کند.",
            "url": f"{django_api_base_url}/health/",
            "method": "PATCH",
            "args": [
                self.create_arg("medical_history", "تاریخچه پزشکی کاربر (بیماری‌های گذشته یا جراحی‌ها).", "STRING",
                                False),
                self.create_arg("chronic_conditions", "بیماری‌های مزمن کاربر (مثل دیابت، فشار خون).", "STRING", False),
                self.create_arg("allergies", "آلرژی‌های کاربر (مثل حساسیت به دارو یا غذا).", "STRING", False),
                self.create_arg("diet_type", "نوع رژیم غذایی کاربر (مثل گیاه‌خواری، بدون گلوتن).", "STRING", False),
                self.create_arg("daily_calorie_intake", "میانگین کالری مصرفی روزانه کاربر.", "INTEGER", False),
                self.create_arg("physical_activity_level", "سطح فعالیت بدنی کاربر (کم، متوسط، زیاد).", "STRING", False),
                self.create_arg("height", "قد کاربر به سانتی‌متر.", "NUMBER", False),
                self.create_arg("weight", "وزن کاربر به کیلوگرم.", "NUMBER", False),
                self.create_arg("bmi", "شاخص توده بدنی کاربر.", "NUMBER", False),
                self.create_arg("mental_health_status", "وضعیت سلامت روان کاربر (مثل اضطراب، افسردگی).", "STRING",
                                False),
                self.create_arg("sleep_hours", "میانگین ساعات خواب روزانه کاربر.", "NUMBER", False),
                self.create_arg("medications", "داروهای در حال مصرف و دوز آن‌ها.", "STRING", False),
                self.create_arg("last_checkup_date", "تاریخ آخرین معاینه پزشکی کاربر (YYYY-MM-DD).", "STRING", False),
            ]
        })

        # Tools for PsychologicalProfile
        tools.append({
            "name": "get_psychological_profile_details",
            "description": "جزئیات پروفایل روانشناختی کاربر را بازیابی می کند.",
            "url": f"{django_api_base_url}/psych/",
            "method": "GET",
            "args": []
        })
        tools.append({
            "name": "update_psychological_profile",
            "description": "ویژگی‌های روانشناختی و شخصیتی کاربر را بروزرسانی یا ثبت می کند.",
            "url": f"{django_api_base_url}/psych/",
            "method": "PATCH",
            "args": [
                self.create_arg("personality_type", "تیپ شخصیتی کاربر (مثل MBTI: INFP، یا Big Five).", "STRING", False),
                self.create_arg("core_values", "ارزش‌های اصلی کاربر (مثل خانواده، موفقیت، آزادی).", "STRING", False),
                self.create_arg("motivations", "انگیزه‌های کاربر (مثل رشد شخصی، ثبات مالی).", "STRING", False),
                self.create_arg("decision_making_style", "سبک تصمیم‌گیری کاربر (منطقی، احساسی، ترکیبی).", "STRING",
                                False),
                self.create_arg("stress_response", "واکنش کاربر به استرس (مثل اجتناب، مقابله فعال).", "STRING", False),
                self.create_arg("emotional_triggers", "محرک‌های احساسی کاربر (مثل انتقاد یا فشار کاری).", "STRING",
                                False),
                self.create_arg("preferred_communication", "سبک ارتباطی کاربر (مستقیم، غیرمستقیم).", "STRING", False),
                self.create_arg("resilience_level", "سطح تاب‌آوری روانی کاربر (کم، متوسط، زیاد).", "STRING", False),
            ]
        })

        # Tools for CareerEducation
        tools.append({
            "name": "get_career_education_details",
            "description": "اطلاعات مربوط به مسیر تحصیلی و حرفه‌ای کاربر را بازیابی می کند.",
            "url": f"{django_api_base_url}/career/",
            "method": "GET",
            "args": []
        })
        tools.append({
            "name": "update_career_education",
            "description": "اطلاعات مربوط به مسیر تحصیلی و حرفه‌ای کاربر را بروزرسانی یا ثبت می کند.",
            "url": f"{django_api_base_url}/career/",
            "method": "PATCH",
            "args": [
                self.create_arg("education_level", "سطح تحصیلات کاربر (مثل کارشناسی، دکتری).", "STRING", False),
                self.create_arg("field_of_study", "رشته تحصیلی کاربر.", "STRING", False),
                self.create_arg("skills", "مهارت‌های حرفه‌ای کاربر (مثل برنامه‌نویسی، مدیریت پروژه).", "STRING", False),
                self.create_arg("job_title", "عنوان شغلی فعلی کاربر.", "STRING", False),
                self.create_arg("industry", "صنعت کاری کاربر (مثل فناوری، آموزش).", "STRING", False),
                self.create_arg("job_satisfaction", "سطح رضایت شغلی کاربر (از 1 تا 10).", "INTEGER", False),
                self.create_arg("career_goals", "اهداف حرفه‌ای کاربر (مثل ارتقا، تغییر شغل).", "STRING", False),
                self.create_arg("work_hours", "میانگین ساعات کاری هفتگی کاربر.", "NUMBER", False),
                self.create_arg("learning_style", "سبک یادگیری کاربر (بصری، شنیداری، عملی).", "STRING", False),
                self.create_arg("certifications", "گواهینامه‌های حرفه‌ای کاربر.", "STRING", False),
            ]
        })

        # Tools for FinancialInfo
        tools.append({
            "name": "get_financial_info_details",
            "description": "داده‌های مالی کاربر را بازیابی می کند.",
            "url": f"{django_api_base_url}/finance/",
            "method": "GET",
            "args": []
        })
        tools.append({
            "name": "update_financial_info",
            "description": "داده‌های مالی کاربر را بروزرسانی یا ثبت می کند.",
            "url": f"{django_api_base_url}/finance/",
            "method": "PATCH",
            "args": [
                self.create_arg("monthly_income", "درآمد ماهانه کاربر.", "NUMBER", False),
                self.create_arg("monthly_expenses", "هزینه‌های ماهانه کاربر.", "NUMBER", False),
                self.create_arg("savings", "مقدار پس‌انداز کاربر.", "NUMBER", False),
                self.create_arg("debts", "مقدار بدهی‌های کاربر.", "NUMBER", False),
                self.create_arg("investment_types", "انواع سرمایه‌گذاری کاربر (مثل سهام، املاک).", "STRING", False),
                self.create_arg("financial_goals", "اهداف مالی کاربر (مثل خرید خانه، بازنشستگی).", "STRING", False),
                self.create_arg("risk_tolerance", "سطح تحمل ریسک کاربر (کم، متوسط، زیاد).", "STRING", False),
                self.create_arg("budgeting_habits", "عادات بودجه‌بندی کاربر.", "STRING", False),
            ]
        })

        # Tools for SocialRelationship
        tools.append({
            "name": "get_social_relationship_details",
            "description": "اطلاعات شبکه اجتماعی و تعاملات کاربر را بازیابی می کند.",
            "url": f"{django_api_base_url}/social/",
            "method": "GET",
            "args": []
        })
        tools.append({
            "name": "update_social_relationship",
            "description": "اطلاعات شبکه اجتماعی و تعاملات کاربر را بروزرسانی یا ثبت می کند.",
            "url": f"{django_api_base_url}/social/",
            "method": "PATCH",
            "args": [
                self.create_arg("key_relationships", "افراد کلیدی در زندگی کاربر (مثل خانواده، دوستان).", "STRING",
                                False),
                self.create_arg("relationship_status", "وضعیت روابط عاطفی کاربر (مثل در رابطه، مجرد).", "STRING",
                                False),
                self.create_arg("communication_style", "سبک ارتباطی کاربر (مثل برون‌گرا، درون‌گرا).", "STRING", False),
                self.create_arg("emotional_needs", "نیازهای عاطفی کاربر (مثل حمایت، تأیید).", "STRING", False),
                self.create_arg("social_frequency", "میزان تعاملات اجتماعی کاربر (روزانه، هفتگی).", "STRING", False),
                self.create_arg("conflict_resolution", "روش‌های حل تعارض در روابط.", "STRING", False),
            ]
        })

        # Tools for PreferenceInterest
        tools.append({
            "name": "get_preference_interest_details",
            "description": "ترجیحات و علایق کاربر را بازیابی می کند.",
            "url": f"{django_api_base_url}/preferences/",
            "method": "GET",
            "args": []
        })
        tools.append({
            "name": "update_preference_interest",
            "description": "ترجیحات و علایق کاربر را بروزرسانی یا ثبت می کند.",
            "url": f"{django_api_base_url}/preferences/",
            "method": "PATCH",
            "args": [
                self.create_arg("hobbies", "سرگرمی‌های کاربر (مثل ورزش، نقاشی).", "STRING", False),
                self.create_arg("favorite_music_genres", "ژانرهای موسیقی مورد علاقه کاربر.", "STRING", False),
                self.create_arg("favorite_movies", "فیلم‌ها یا ژانرهای سینمایی مورد علاقه کاربر.", "STRING", False),
                self.create_arg("reading_preferences", "نوع کتاب‌های مورد علاقه کاربر (مثل علمی، رمان).", "STRING",
                                False),
                self.create_arg("travel_preferences", "ترجیحات سفر کاربر (مثل ماجراجویی، فرهنگی).", "STRING", False),
                self.create_arg("food_preferences", "ترجیحات غذایی کاربر (مثل غذاهای تند، سنتی).", "STRING", False),
                self.create_arg("lifestyle_choices", "سبک زندگی کاربر (مثل مینیمال، لوکس).", "STRING", False),
                self.create_arg("movie_fav_choices", "فیلم‌های مورد علاقه کاربر.", "STRING", False),
            ]
        })

        # Tools for EnvironmentalContext
        tools.append({
            "name": "get_environmental_context_details",
            "description": "اطلاعات محیطی و زمینه‌ای کاربر را بازیابی می کند.",
            "url": f"{django_api_base_url}/environment/",
            "method": "GET",
            "args": []
        })
        tools.append({
            "name": "update_environmental_context",
            "description": "اطلاعات محیطی و زمینه‌ای کاربر را بروزرسانی یا ثبت می کند.",
            "url": f"{django_api_base_url}/environment/",
            "method": "PATCH",
            "args": [
                self.create_arg("current_city", "شهر محل زندگی فعلی کاربر.", "STRING", False),
                self.create_arg("climate", "وضعیت آب‌وهوایی محل زندگی کاربر (مثل معتدل، گرم).", "STRING", False),
                self.create_arg("housing_type", "نوع محل سکونت کاربر (آپارتمان، خانه ویلایی).", "STRING", False),
                self.create_arg("tech_access", "دسترسی کاربر به فناوری (مثل گوشی هوشمند، اینترنت پرسرعت).", "STRING",
                                False),
                self.create_arg("life_events", "رویدادهای مهم زندگی کاربر (مثل ازدواج، نقل‌مکان).", "STRING", False),
                self.create_arg("transportation", "وسایل حمل‌ونقل مورد استفاده کاربر (مثل ماشین شخصی، مترو).", "STRING",
                                False),
            ]
        })

        # Tools for RealTimeData
        tools.append({
            "name": "get_real_time_data_details",
            "description": "داده‌های لحظه‌ای کاربر را بازیابی می کند.",
            "url": f"{django_api_base_url}/realtime/",
            "method": "GET",
            "args": []
        })
        tools.append({
            "name": "update_real_time_data",
            "description": "داده‌های لحظه‌ای کاربر را بروزرسانی یا ثبت می کند.",
            "url": f"{django_api_base_url}/realtime/",
            "method": "PATCH",
            "args": [
                self.create_arg("current_location", "مکان فعلی کاربر.", "STRING", False),
                self.create_arg("current_mood", "حال و هوای لحظه‌ای کاربر.", "STRING", False),
                self.create_arg("current_activity", "فعالیت فعلی کاربر.", "STRING", False),
                self.create_arg("daily_schedule", "برنامه روزانه کاربر.", "STRING", False),
                self.create_arg("heart_rate", "ضربان قلب کاربر.", "INTEGER", False),
            ]
        })

        # Tools for FeedbackLearning
        tools.append({
            "name": "update_feedback_learning",
            "description": "بازخوردهای کاربر و داده‌های یادگیری AI را بروزرسانی یا ثبت می کند.",
            "url": f"{django_api_base_url}/feedback/",
            "method": "PATCH",
            "args": [
                self.create_arg("feedback_text", "نظرات کاربر درباره عملکرد AI.", "STRING", False),
                self.create_arg("interaction_type", "نوع تعامل (مثل سوال، توصیه، دستور).", "STRING", False),
                self.create_arg("interaction_rating", "امتیاز کاربر به تعامل (از 1 تا 5).", "INTEGER", False),
                self.create_arg("interaction_frequency", "تعداد تعاملات در بازه زمانی.", "INTEGER", False),
            ]
        })

        # Tools for Goal
        tools.append({
            "name": "get_goals",
            "description": "لیست اهداف کاربر را بازیابی می کند.",
            "url": f"{django_api_base_url}/goals/",
            "method": "GET",
            "args": []
        })
        tools.append({
            "name": "create_goal",
            "description": "یک هدف جدید برای کاربر ایجاد می کند.",
            "url": f"{django_api_base_url}/goals/",
            "method": "POST",
            "args": [
                self.create_arg("goal_type", "نوع هدف (شخصی، حرفه‌ای، مالی).", "STRING", True),
                self.create_arg("description", "توضیح هدف.", "STRING", True),
                self.create_arg("priority", "اولویت هدف (از 1 تا 5).", "INTEGER", False),
                self.create_arg("deadline", "مهلت دستیابی به هدف (YYYY-MM-DD).", "STRING", False),
                self.create_arg("progress", "درصد پیشرفت (مثلاً 50).", "NUMBER", False),
            ]
        })
        tools.append({
            "name": "update_goal",
            "description": "یک هدف موجود کاربر را بروزرسانی می کند.",
            "url": f"{django_api_base_url}/goals/<int:pk>/",  # Note: Metis AI needs to pass the PK
            "method": "PATCH",
            "args": [
                self.create_arg("pk", "شناسه یکتای هدف.", "INTEGER", True),  # Primary key for the specific goal
                self.create_arg("goal_type", "نوع هدف (شخصی، حرفه‌ای، مالی).", "STRING", False),
                self.create_arg("description", "توضیح هدف.", "STRING", False),
                self.create_arg("priority", "اولویت هدف (از 1 تا 5).", "INTEGER", False),
                self.create_arg("deadline", "مهلت دستیابی به هدف (YYYY-MM-DD).", "STRING", False),
                self.create_arg("progress", "درصد پیشرفت (مثلاً 50).", "NUMBER", False),
            ]
        })
        tools.append({
            "name": "delete_goal",
            "description": "یک هدف موجود کاربر را حذف می کند.",
            "url": f"{django_api_base_url}/goals/<int:pk>/",
            "method": "DELETE",
            "args": [
                self.create_arg("pk", "شناسه یکتای هدف.", "INTEGER", True),
            ]
        })

        # Tools for Habit
        tools.append({
            "name": "get_habits",
            "description": "لیست عادات کاربر را بازیابی می کند.",
            "url": f"{django_api_base_url}/habits/",
            "method": "GET",
            "args": []
        })
        tools.append({
            "name": "create_habit",
            "description": "یک عادت جدید برای کاربر ایجاد می کند.",
            "url": f"{django_api_base_url}/habits/",
            "method": "POST",
            "args": [
                self.create_arg("habit_name", "نام عادت (مثل ورزش صبحگاهی).", "STRING", True),
                self.create_arg("frequency", "دفعات انجام (روزانه، هفتگی).", "STRING", False),
                self.create_arg("duration", "مدت زمان انجام عادت (به دقیقه).", "INTEGER", False),
                self.create_arg("start_date", "تاریخ شروع عادت (YYYY-MM-DD).", "STRING", False),
                self.create_arg("success_rate", "درصد موفقیت در انجام عادت.", "NUMBER", False),
            ]
        })
        tools.append({
            "name": "update_habit",
            "description": "یک عادت موجود کاربر را بروزرسانی می کند.",
            "url": f"{django_api_base_url}/habits/<int:pk>/",
            "method": "PATCH",
            "args": [
                self.create_arg("pk", "شناسه یکتای عادت.", "INTEGER", True),
                self.create_arg("habit_name", "نام عادت (مثل ورزش صبحگاهی).", "STRING", False),
                self.create_arg("frequency", "دفعات انجام (روزانه، هفتگی).", "STRING", False),
                self.create_arg("duration", "مدت زمان انجام عادت (به دقیقه).", "INTEGER", False),
                self.create_arg("start_date", "تاریخ شروع عادت (YYYY-MM-DD).", "STRING", False),
                self.create_arg("success_rate", "درصد موفقیت در انجام عادت.", "NUMBER", False),
            ]
        })
        tools.append({
            "name": "delete_habit",
            "description": "یک عادت موجود کاربر را حذف می کند.",
            "url": f"{django_api_base_url}/habits/<int:pk>/",
            "method": "DELETE",
            "args": [
                self.create_arg("pk", "شناسه یکتای عادت.", "INTEGER", True),
            ]
        })

        # Tools for AiResponse (Sessions) - Listing and Deleting
        tools.append({
            "name": "get_ai_sessions",
            "description": "لیست سشن‌های چت هوش مصنوعی کاربر را بازیابی می کند.",
            "url": f"{django_api_base_url}/ai-sessions/",
            "method": "GET",
            "args": []
        })
        tools.append({
            "name": "delete_ai_session",
            "description": "یک سشن چت هوش مصنوعی کاربر را حذف می کند.",
            "url": f"{django_api_base_url}/ai-sessions/<int:pk>/",
            "method": "DELETE",
            "args": [
                self.create_arg("pk", "شناسه یکتای سشن چت.", "INTEGER", True),
            ]
        })

        # Tools for PsychTestHistory
        tools.append({
            "name": "get_psych_test_history",
            "description": "تاریخچه تست‌های روانشناسی کاربر را بازیابی می‌کند.",
            "url": f"{django_api_base_url}/psych-test-history/",
            "method": "GET",
            "args": []
        })
        tools.append({
            "name": "create_psych_test_record",
            "description": "یک رکورد جدید برای تست روانشناسی کاربر ایجاد می‌کند.",
            "url": f"{django_api_base_url}/psych-test-history/",
            "method": "POST",
            "args": [
                self.create_arg("test_name", "نام تست (مثلاً Big Five).", "STRING", True),
                self.create_arg("test_result_summary", "خلاصه نتایج تست.", "STRING", True),
                self.create_arg("full_test_data", "داده‌های کامل تست به فرمت JSON.", "JSON", False),
                self.create_arg("ai_analysis", "تحلیل AI از نتایج تست.", "STRING", False),
            ]
        })
        tools.append({
            "name": "update_psych_test_record",
            "description": "یک رکورد تست روانشناسی موجود کاربر را به‌روزرسانی می‌کند.",
            "url": f"{django_api_base_url}/psych-test-history/<int:pk>/",
            "method": "PATCH",
            "args": [
                self.create_arg("pk", "شناسه یکتای رکورد تست روانشناسی.", "INTEGER", True),
                self.create_arg("test_name", "نام تست.", "STRING", False),
                self.create_arg("test_result_summary", "خلاصه نتایج تست.", "STRING", False),
                self.create_arg("full_test_data", "داده‌های کامل تست به فرمت JSON.", "JSON", False),
                self.create_arg("ai_analysis", "تحلیل AI از نتایج تست.", "STRING", False),
            ]
        })
        tools.append({
            "name": "delete_psych_test_record",
            "description": "یک رکورد تست روانشناسی موجود کاربر را حذف می‌کند.",
            "url": f"{django_api_base_url}/psych-test-history/<int:pk>/",
            "method": "DELETE",
            "args": [
                self.create_arg("pk", "شناسه یکتای رکورد تست روانشناسی.", "INTEGER", True),
            ]
        })

        return tools