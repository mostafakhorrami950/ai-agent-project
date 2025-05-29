# users_ai/metis_ai_service.py
import requests
from django.conf import settings
import logging
import json

logger = logging.getLogger(__name__)


class MetisAIService:
    def __init__(self):
        # تغییر مهم: Base URL برای عملیات چت
        self.base_url = "https://api.metisai.ir/api/v1/chat"
        self.api_key = settings.METIS_API_KEY
        self.bot_id = settings.METIS_BOT_ID # همچنان bot_id را نگه می‌داریم، چون در create_chat_session استفاده می‌شود
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        if not self.api_key or not self.bot_id:
            logger.error("METIS_API_KEY or METIS_BOT_ID not configured in settings.")
            raise ValueError("Metis AI credentials are not set up.")
        logger.debug("MetisAIService initialized for Chat API.")

    def _make_request(self, method, endpoint, json_data=None, params=None):
        # URL کامل از Base URL + endpoint ساخته می‌شود
        url = f"{self.base_url}/{endpoint}"
        try:
            logger.debug(f"[_make_request] Attempting request to {method} {url}")
            logger.debug(f"[_make_request] Request Headers: {self.headers}")
            if json_data:
                logger.debug(
                    f"[_make_request] Request JSON Data: {json.dumps(json_data, indent=2, ensure_ascii=False)}")
            if params:
                logger.debug(f"[_make_request] Request Params: {params}")

            response = requests.request(method, url, headers=self.headers, json=json_data, params=params, timeout=60)
            response.raise_for_status()
            logger.debug(f"[_make_request] Response Status: {response.status_code}")
            try:
                response_json = response.json()
                logger.debug(
                    f"[_make_request] Response JSON Body: {json.dumps(response_json, indent=2, ensure_ascii=False)}")
                return response_json
            except json.JSONDecodeError as e:
                logger.error(
                    f"[_make_request] JSON Decode Error: {e}, Response content: {response.text if 'response' in locals() else 'N/A'}")
                raise ValueError(f"Invalid JSON response from Metis AI: {e}")

        except requests.exceptions.HTTPError as e:
            logger.error(
                f"[_make_request] HTTP Error: {e.response.status_code} for url: {e.request.url}, Response: {getattr(e.response, 'text', 'No response text')}")
            raise ConnectionError(
                f"Metis AI API Error ({e.response.status_code}): {getattr(e.response, 'text', 'No response text')}")
        except requests.exceptions.RequestException as e:
            logger.error(
                f"[_make_request] Network/Request Error: {e} for url: {e.request.url if e.request else 'N/A'}")
            raise ConnectionError(f"Failed to connect to Metis AI: {e}")
        except Exception as e:
            logger.error(f"[_make_request] An unexpected error occurred: {e}", exc_info=True)
            raise

    # متدهای create_bot, update_bot, get_bot_info, get_bots_list, delete_bot
    # این متدها برای مدیریت بات‌ها هستند و base_url اصلی ("https://api.metisai.ir/api/v1") را می‌خواهند.
    # پس باید یک متد جداگانه برای آن‌ها ایجاد کنیم یا base_url را داینامیک مدیریت کنیم.
    # فعلاً آن‌ها را از اینجا حذف می‌کنیم تا بر عملیات چت تمرکز کنیم، مگر اینکه بعداً نیاز باشد.
    # اگر از این متدها در جای دیگری استفاده می‌شود، باید یک Base URL دیگر (مثلاً self.bot_api_base_url) برای آن‌ها تعریف شود.

    # تابع جدید برای شروع سشن چت - مطابق با chatbot (3).py
    def create_chat_session(self, bot_id, user_data=None, initial_messages=None):
        endpoint = "session" # URL نسبی: /chat/session
        data = {
            "botId": bot_id, # bot_id به عنوان فیلد در payload
            "user": user_data,
            "initialMessages": initial_messages or []
        }
        logger.debug(f"[create_chat_session] Data: {json.dumps(data, indent=2, ensure_ascii=False)}")
        return self._make_request("POST", endpoint, json_data=data)

    # تابع جدید برای ارسال پیام - مطابق با chatbot (3).py
    def send_message(self, session_id, message_content, message_type="USER", chat_history=None, user_profile_summary=None):
        endpoint = f"session/{session_id}/message" # URL نسبی: /chat/session/{session_id}/message

        # Metis AI expects 'messages' list for context, not individual message types for _this_ endpoint
        # The structure is `{"message": {"type": "USER", "content": "..."}}` for single messages,
        # but for full history, it should be different.
        # Let's adjust this to match the `views.py` expectation of passing `chat_history` and `user_profile_summary`.
        # Reviewing `chatbot (3).py`'s `send_message`, it's simplified.
        # We need to send the full history as `initialMessages` might imply only for starting sessions.
        # It's better to stick to the previous `views.py`'s logic for `send_message` in terms of content,
        # but apply the correct endpoint from `chatbot (3).py`.

        # Re-adapting the message structure to include full history, based on common LLM API patterns.
        # If Metis AI's `send_message` endpoint specifically only takes `{"message": {"type": "...", "content": "..."}}`
        # and manages history internally, then this part might need further adjustment.
        # Based on common LLM API patterns, the `messages` array in `initialMessages` is often used for context.
        # Assuming `send_message` can also take `messages` list for continuous context.

        # Let's align with the `initial_messages` structure used in `create_chat_session`.
        # The `send_message` in `chatbot (3).py` only sends a single message:
        # data = { "message": { "content": content, "type": message_type } }
        # This implies history is managed by Metis internally, or needs to be resent via a different mechanism.

        # Given the previous error and the simplified `send_message` in `chatbot (3).py`,
        # it seems Metis expects `send_message` to be purely for the current turn.
        # If full history is needed for continuity, it might be that Metis manages it per session,
        # or it should be passed via `user_data` or a `system` message within `initial_messages` for new sessions,
        # or via a specific "context" field in `send_message` if available.

        # For now, let's revert `send_message` to its basic form as seen in chatbot(3).py for the current message,
        # as it's the one actually working there. The responsibility of sending full history to Metis (if required)
        # would then shift to `create_chat_session` for initial context, and Metis internal logic for subsequent turns.
        # If Metis needs history in `send_message`, its documentation should specify a `messages` or `context` field.

        data = {
            "message": {
                "content": message_content,
                "type": message_type # "USER"
            }
        }
        logger.debug(f"[send_message] Data to send to Metis: {json.dumps(data, indent=2, ensure_ascii=False)}")
        return self._make_request("POST", endpoint, json_data=data)

    def delete_chat_session(self, session_id):
        endpoint = f"session/{session_id}" # URL نسبی: /chat/session/{session_id}
        logger.debug(f"[delete_chat_session] Deleting session: {session_id}")
        return self._make_request("DELETE", endpoint)

    def get_chat_session_info(self, session_id):
        endpoint = f"session/{session_id}" # URL نسبی: /chat/session/{session_id}
        return self._make_request("GET", endpoint)

    def get_chat_sessions_for_user(self, user_id, page=0, size=10):
        endpoint = "session" # URL نسبی: /chat/session
        params = {"userId": user_id, "page": page, "size": size}
        return self._make_request("GET", endpoint, params=params)

    def get_chat_sessions_for_bot(self, bot_id, page=0, size=10):
        endpoint = "session" # URL نسبی: /chat/session
        params = {"botId": bot_id, "page": page, "size": size}
        return self._make_request("GET", endpoint, params=params)

    @staticmethod
    def get_tool_schemas_for_metis_bot():
        django_api_base_url = getattr(settings, 'DJANGO_API_BASE_URL', "https://api.mobixtube.ir/api")
        if django_api_base_url == "https://api.mobixtube.ir/api":
            logger.warning(
                "Using default DJANGO_API_BASE_URL. Ensure this is configured in settings.py for production.")

        def create_arg(name, description, arg_type, required, enum_values=None):
            arg = {"name": name, "description": description, "type": arg_type, "required": required}
            if enum_values:
                arg["enumValues"] = enum_values
            return arg

        # Note: The `tools` defined here are for informing Metis AI about your callable endpoints.
        # The URLs must be full and accessible by Metis AI.
        # This part assumes Metis AI will pass `user_id` to your tools or the tools operate on authenticated user.
        # The `django_api_base_url` must be the public facing URL of your Django API.

        tools = []
        tools.append({
            "name": "create_goal",
            "description": "اهداف کاربر را ثبت یا ویرایش می کند. برای ثبت یک هدف جدید یا بروزرسانی هدف موجود استفاده می شود.",
            "url": f"{django_api_base_url}/goals/",
            "method": "POST",
            "args": [
                create_arg("goal_type", "نوع هدف (مثلاً شخصی، حرفه‌ای، مالی، سلامتی).", "STRING", True),
                create_arg("description", "توضیح کامل هدف کاربر (مثلاً یادگیری زبان جدید).", "STRING", True),
                create_arg("priority", "اولویت هدف (از 1 تا 5، 5 بالاترین اولویت).", "INTEGER", False),
                create_arg("deadline", "تاریخ مهلت دستیابی به هدف در قالب YYYY-MM-DD.", "STRING", False),
                create_arg("progress", "درصد پیشرفت فعلی هدف (از 0.0 تا 100.0).", "NUMBER", False),
            ],
        })
        tools.append({
            "name": "update_health_record",
            "description": "سوابق سلامتی جسمانی و روانی کاربر را بروزرسانی یا ثبت می کند.",
            "url": f"{django_api_base_url}/health/", # Note: Changed from health-record/ to health/ as per your urls.py
            "method": "PATCH",
            "args": [
                create_arg("medical_history", "تاریخچه پزشکی کاربر (بیماری‌های گذشته، جراحی‌ها).", "STRING", False),
                create_arg("chronic_conditions", "بیماری‌های مزمن کاربر (مثل دیابت، فشار خون).", "STRING", False),
                create_arg("allergies", "آلرژی‌های کاربر (مثل حساسیت به دارو یا غذا).", "STRING", False),
                create_arg("diet_type", "نوع رژیم غذایی (مثلاً گیاه‌خواری، بدون گلوتن).", "STRING", False,
                           ["گیاه‌خواری", "وگان", "بدون گلوتن", "عادی"]),
                create_arg("daily_calorie_intake", "میانگین کالری مصرفی روزانه.", "INTEGER", False),
                create_arg("physical_activity_level", "سطح فعالیت بدنی (کم، متوسط، زیاد).", "STRING", False,
                           ["کم", "متوسط", "زیاد"]),
                create_arg("height", "قد کاربر به سانتی‌متر (مثلاً 175.5).", "NUMBER", False),
                create_arg("weight", "وزن کاربر به کیلوگرم (مثلاً 70.2).", "NUMBER", False),
                create_arg("bmi", "شاخص توده بدنی (BMI).", "NUMBER", False),
                create_arg("mental_health_status", "وضعیت سلامت روان (مثل اضطراب، افسردگی، حال عمومی).", "STRING",
                           False),
                create_arg("sleep_hours", "میانگین ساعات خواب روزانه (مثلاً 7.5).", "NUMBER", False),
                create_arg("medications", "داروهای در حال مصرف و دوز آن‌ها.", "STRING", False),
                create_arg("last_checkup_date", "تاریخ آخرین معاینه پزشکی در قالب YYYY-MM-DD.", "STRING", False),
            ]
        })
        tools.append({
            "name": "update_psychological_profile",
            "description": "پروفایل روانشناختی و ویژگی‌های شخصیتی کاربر را بروزرسانی یا ثبت می کند.",
            "url": f"{django_api_base_url}/psych/", # Note: Changed from psychological-profile/ to psych/ as per your urls.py
            "method": "PATCH",
            "args": [
                create_arg("personality_type", "تیپ شخصیتی (مثلاً MBTI: INFP، یا Big Five).", "STRING", False),
                create_arg("core_values", "ارزش‌های اصلی کاربر (مثل خانواده، موفقیت، آزادی).", "STRING", False),
                create_arg("motivations", "انگیزه‌های کاربر (مثل رشد شخصی، ثبات مالی).", "STRING", False),
                create_arg("decision_making_style", "سبک تصمیم‌گیری (منطقی، احساسی، ترکیبی).", "STRING", False,
                           ["منطقی", "احساسی", "ترکیبی"]),
                create_arg("stress_response", "واکنش به استرس (مثلاً اجتناب، مقابله فعال).", "STRING", False),
                create_arg("emotional_triggers", "محرک‌های احساسی (مثل انتقاد یا فشار کاری).", "STRING", False),
                create_arg("preferred_communication", "سبک ارتباطی (مستقیم، غیرمستقیم).", "STRING", False,
                           ["مستقیم", "غیرمستقیم"]),
                create_arg("resilience_level", "سطح تاب‌آوری روانی (کم، متوسط، زیاد).", "STRING", False,
                           ["کم", "متوسط", "زیاد"]),
            ]
        })
        tools.append({
            "name": "update_career_education",
            "description": "اطلاعات مسیر تحصیلی و حرفه‌ای کاربر را بروزرسانی یا ثبت می کند.",
            "url": f"{django_api_base_url}/career/", # Note: Changed from career-education/ to career/ as per your urls.py
            "method": "PATCH",
            "args": [
                create_arg("education_level", "سطح تحصیلات (مثلاً کارشناسی، دکتری).", "STRING", False),
                create_arg("field_of_study", "رشته تحصیلی (مثلاً مهندسی، پزشکی).", "STRING", False),
                create_arg("skills", "مهارت‌های حرفه‌ای (مثلاً برنامه‌نویسی، مدیریت پروژه).", "STRING", False),
                create_arg("job_title", "عنوان شغلی فعلی.", "STRING", False),
                create_arg("industry", "صنعت کاری (مثلاً فناوری، آموزش).", "STRING", False),
                create_arg("job_satisfaction", "سطح رضایت شغلی (از 1 تا 10).", "INTEGER", False),
                create_arg("career_goals", "اهداف حرفه‌ای (مثلاً ارتقا، تغییر شغل).", "STRING", False),
                create_arg("work_hours", "میانگین ساعات کاری هفتگی (مثلاً 40.5).", "NUMBER", False),
                create_arg("learning_style", "سبک یادگیری (بصری، شنیداری، عملی).", "STRING", False,
                           ["بصری", "شنیداری", "عملی"]),
                create_arg("certifications", "گواهینامه‌های حرفه‌ای.", "STRING", False),
            ]
        })
        tools.append({
            "name": "update_financial_info",
            "description": "داده‌های مالی کاربر را بروزرسانی یا ثبت می کند.",
            "url": f"{django_api_base_url}/finance/", # Note: Changed from financial-info/ to finance/ as per your urls.py
            "method": "PATCH",
            "args": [
                create_arg("monthly_income", "درآمد ماهانه.", "NUMBER", False),
                create_arg("monthly_expenses", "هزینه‌های ماهانه.", "NUMBER", False),
                create_arg("savings", "مقدار پس‌انداز.", "NUMBER", False),
                create_arg("debts", "مقدار بدهی‌ها.", "NUMBER", False),
                create_arg("investment_types", "انواع سرمایه‌گذاری (مثل سهام، املاک).", "STRING", False),
                create_arg("financial_goals", "اهداف مالی (مثل خرید خانه، بازنشستگی).", "STRING", False),
                create_arg("risk_tolerance", "سطح تحمل ریسک (کم، متوسط، زیاد).", "STRING", False,
                           ["کم", "متوسط", "زیاد"]),
                create_arg("budgeting_habits", "عادات بودجه‌بندی (مثلاً پس‌انداز ماهانه).", "STRING", False),
            ]
        })
        tools.append({
            "name": "update_social_relationship",
            "description": "اطلاعات شبکه اجتماعی و تعاملات کاربر را بروزرسانی یا ثبت می کند.",
            "url": f"{django_api_base_url}/social/", # Note: Changed from social-relationship/ to social/ as per your urls.py
            "method": "PATCH",
            "args": [
                create_arg("key_relationships", "افراد کلیدی در زندگی (مثل خانواده، دوستان).", "STRING", False),
                create_arg("relationship_status", "وضعیت روابط عاطفی (مثل در رابطه، مجرد، متأهل).", "STRING", False,
                           ["در رابطه", "مجرد", "متأهل", "مطلقه"]),
                create_arg("communication_style", "سبک ارتباطی (مثل برون‌گرا، درون‌گرا).", "STRING", False),
                create_arg("emotional_needs", "نیازهای عاطفی (مثل حمایت، تأیید).", "STRING", False),
                create_arg("social_frequency", "میزان تعاملات اجتماعی (روزانه، هفتگی، ماهانه).", "STRING", False,
                           ["روزانه", "هفتگی", "ماهانه", "کم", "زیاد"]),
                create_arg("conflict_resolution", "روش‌های حل تعارض در روابط.", "STRING", False),
            ]
        })
        tools.append({
            "name": "update_preference_interest",
            "description": "ترجیحات و علایق کاربر را بروزرسانی یا ثبت می کند.",
            "url": f"{django_api_base_url}/preferences/", # Note: Changed from preferences-interests/ to preferences/ as per your urls.py
            "method": "PATCH",
            "args": [
                create_arg("hobbies", "سرگرمی‌ها (مثل ورزش، نقاشی).", "STRING", False),
                create_arg("favorite_music_genres", "ژانرهای موسیقی مورد علاقه.", "STRING", False),
                create_arg("favorite_movies", "فیلم‌ها یا ژانرهای سینمایی مورد علاقه.", "STRING", False),
                create_arg("reading_preferences", "نوع کتاب‌های مورد علاقه.", "STRING", False),
                create_arg("travel_preferences", "ترجیحات سفر (مثلاً ماجراجویی، فرهنگی).", "STRING", False),
                create_arg("food_preferences", "ترجیحات غذایی (مثلاً غذاهای تند، سنتی).", "STRING", False),
                create_arg("lifestyle_choices", "سبک زندگی (مثلاً مینیمال، لوکس).", "STRING", False),
                create_arg("movie_fav_choices", "فیلم‌های مورد علاقه کاربر.", "STRING", False),
            ]
        })
        tools.append({
            "name": "update_environmental_context",
            "description": "اطلاعات محیطی و زمینه‌ای کاربر را بروزرسانی یا ثبت می کند.",
            "url": f"{django_api_base_url}/environment/", # Note: Changed from environmental-context/ to environment/ as per your urls.py
            "method": "PATCH",
            "args": [
                create_arg("current_city", "شهر محل زندگی فعلی.", "STRING", False),
                create_arg("climate", "وضعیت آب‌وهوایی محل زندگی (مثل معتدل، گرم، سرد).", "STRING", False,
                           ["معتدل", "گرم", "سرد", "خشک", "مرطوم"]),
                create_arg("housing_type", "نوع محل سکونت (آپارتمان، خانه ویلایی).", "STRING", False,
                           ["آپارتمان", "خانه ویلایی", "پنت هاوس", "استودیو"]),
                create_arg("tech_access", "دسترسی به فناوری (مثل گوشی هوشمند، اینترنت پرسرعت).", "STRING", False),
                create_arg("life_events", "رویدادهای مهم زندگی (مثل ازدواج، نقل‌مکان، تولد فرزند).", "STRING", False),
                create_arg("transportation", "وسایل حمل‌ونقل مورد استفاده (مثل ماشین شخصی، مترو، اتوبوس).", "STRING",
                           False),
            ]
        })
        tools.append({
            "name": "update_real_time_data",
            "description": "داده‌های لحظه‌ای کاربر را بروزرسانی یا ثبت می کند.",
            "url": f"{django_api_base_url}/realtime/", # Note: Changed from real-time-data/ to realtime/ as per your urls.py
            "method": "PATCH",
            "args": [
                create_arg("current_location", "مکان فعلی کاربر (مثلاً مختصات GPS یا نام مکان).", "STRING", False),
                create_arg("current_mood", "حال و هوای لحظه‌ای (مثلاً خوشحال، مضطرب، خنثی).", "STRING", False,
                           ["خوشحال", "غمگین", "مضطرب", "عصبی", "آرام", "هیجان زده", "خسته", "خنثی"]),
                create_arg("current_activity", "فعالیت فعلی (مثلاً کار، استراحت، ورزش).", "STRING", False),
                create_arg("daily_schedule", "برنامه روزانه (مثل جلسات، وظایف).", "STRING", False),
                create_arg("heart_rate", "ضربان قلب کاربر.", "INTEGER", False),
            ]
        })
        tools.append({
            "name": "update_feedback_learning",
            "description": "بازخوردهای کاربر و داده‌های یادگیری AI را بروزرسانی یا ثبت می کند.",
            "url": f"{django_api_base_url}/feedback/", # Note: Changed from feedback-learning/ to feedback/ as per your urls.py
            "method": "PATCH",
            "args": [
                create_arg("feedback_text", "نظرات کاربر درباره عملکرد AI.", "STRING", False),
                create_arg("interaction_type", "نوع تعامل (مثل سوال، توصیه، دستور).", "STRING", False),
                create_arg("interaction_rating", "امتیاز کاربر به تعامل (از 1 تا 5).", "INTEGER", False),
                create_arg("interaction_frequency", "تعداد تعاملات در بازه زمانی.", "INTEGER", False),
            ]
        })
        tools.append({
            "name": "update_user_profile_details",
            "description": "جزئیات اضافی پروفایل کاربر را بروزرسانی یا ثبت می کند.",
            "url": f"{django_api_base_url}/profile/",
            "method": "PATCH",
            "args": [
                create_arg("ai_psychological_test", "نتیجه تست روانشناسی کاربر.", "STRING", False),
                create_arg("user_information_summary",
                           "خلاصه‌ای از تمام اطلاعات کاربر که با استفاده از هوش مصنوعی خلاصه شده است.", "STRING",
                           False),
            ]
        })
        logger.debug(f"Defined {len(tools)} tools for Metis Bot API.")
        return tools