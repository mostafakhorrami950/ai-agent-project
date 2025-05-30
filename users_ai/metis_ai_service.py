# users_ai/metis_ai_service.py
import requests
from django.conf import settings
import logging
import json

logger = logging.getLogger(__name__)


class MetisAIService:
    def __init__(self):
        self.chat_base_url = "https://api.metisai.ir/api/v1/chat"
        self.bot_management_base_url = "https://api.metisai.ir/api/v1"
        self.api_key = settings.METIS_API_KEY
        self.bot_id = settings.METIS_BOT_ID
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        if not self.api_key or not self.bot_id:
            logger.error("METIS_API_KEY or METIS_BOT_ID not configured in settings.")
            raise ValueError("Metis AI credentials are not set up.")
        logger.debug("MetisAIService initialized.")

    def _make_request(self, method, base_url_type, endpoint, json_data=None, params=None):
        base_url = ""
        if base_url_type == "chat":
            base_url = self.chat_base_url
        elif base_url_type == "bot_management":
            base_url = self.bot_management_base_url
        else:
            raise ValueError("Invalid base_url_type provided to _make_request")

        url = f"{base_url}/{endpoint}"
        try:
            logger.debug(f"[_make_request] Attempting request to {method} {url}")
            logger.debug(f"[_make_request] Request Headers: {self.headers}")
            if json_data:
                # لاگ کردن JSON ارسالی
                logger.debug(
                    f"[_make_request] Request JSON Data: {json.dumps(json_data, indent=2, ensure_ascii=False)}")
            if params:
                logger.debug(f"[_make_request] Request Params: {params}")

            response = requests.request(method, url, headers=self.headers, json=json_data, params=params, timeout=60)
            response.raise_for_status()
            logger.debug(f"[_make_request] Response Status: {response.status_code}")
            try:
                response_json = response.json()
                # لاگ کردن JSON دریافتی
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

    # Bot Management Methods - Use bot_management_base_url
    def create_bot(self, name, enabled, provider_config, instructions=None, functions=None, corpus_ids=None):
        endpoint = "bots"
        data = {
            "name": name,
            "enabled": enabled,
            "providerConfig": provider_config,
            "instructions": instructions,
            "functions": functions if functions is not None else [],  # اطمینان از ارسال لیست خالی به جای None
            "corpusIds": corpus_ids if corpus_ids is not None else []
        }
        return self._make_request("POST", "bot_management", endpoint, json_data=data)

    def update_bot(self, bot_id, name=None, enabled=None, provider_config=None, instructions=None, functions=None,
                   corpus_ids=None,
                   description=None, avatar=None):
        endpoint = f"bots/{bot_id}"
        data = {}
        if name is not None: data["name"] = name
        if enabled is not None: data["enabled"] = enabled
        if provider_config is not None: data["providerConfig"] = provider_config
        if instructions is not None: data["instructions"] = instructions
        if functions is not None:
            data["functions"] = functions  # ارسال لیست توابع
        else:
            data["functions"] = []  # ارسال لیست خالی به جای None برای توابع
        if corpus_ids is not None: data["corpusIds"] = corpus_ids
        if description is not None: data["description"] = description
        if avatar is not None: data["avatar"] = avatar

        logger.debug(f"[update_bot] Data to send: {json.dumps(data, indent=2, ensure_ascii=False)}")
        return self._make_request("PUT", "bot_management", endpoint, json_data=data)

    def get_bot_info(self, bot_id):
        endpoint = f"bots/{bot_id}"
        return self._make_request("GET", "bot_management", endpoint)

    def get_bots_list(self):
        endpoint = "bots/all"
        return self._make_request("GET", "bot_management", endpoint)

    def delete_bot(self, bot_id):
        endpoint = f"bots/{bot_id}"
        return self._make_request("DELETE", "bot_management", endpoint)

    # Chat Session Methods - Use chat_base_url
    def create_chat_session(self, bot_id, user_data=None, initial_messages=None, functions=None):
        endpoint = "session"
        data = {
            "botId": bot_id,
            "user": user_data if user_data is not None else {},  # اطمینان از ارسال دیکشنری خالی به جای None
            "initialMessages": initial_messages if initial_messages is not None else []
            # اطمینان از ارسال لیست خالی به جای None
        }
        if functions is not None:
            data["functions"] = functions
        else:
            data["functions"] = []  # اطمینان از ارسال لیست خالی به جای None برای توابع

        logger.debug(f"[create_chat_session] Data: {json.dumps(data, indent=2, ensure_ascii=False)}")
        return self._make_request("POST", "chat", endpoint, json_data=data)

    def send_message(self, session_id, content, message_type="USER"):
        endpoint = f"session/{session_id}/message"
        data = {
            "message": {
                "content": content,
                "type": message_type
            }
        }
        logger.debug(f"[send_message] Data to send to Metis: {json.dumps(data, indent=2, ensure_ascii=False)}")
        return self._make_request("POST", "chat", endpoint, json_data=data)

    def delete_chat_session(self, session_id):
        endpoint = f"session/{session_id}"
        logger.debug(f"[delete_chat_session] Deleting session: {session_id}")
        return self._make_request("DELETE", "chat", endpoint)

    def get_chat_session_info(self, session_id):
        endpoint = f"session/{session_id}"
        return self._make_request("GET", "chat", endpoint)

    def get_chat_sessions_for_user(self, user_id, page=0, size=10):
        endpoint = "session"
        params = {"userId": user_id, "page": page, "size": size}
        return self._make_request("GET", "chat", endpoint, params=params)

    def get_chat_sessions_for_bot(self, bot_id, page=0, size=10):
        endpoint = "session"
        params = {"botId": bot_id, "page": page, "size": size}
        return self._make_request("GET", "chat", endpoint, params=params)

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

        tools = []
        tools.append({
            "name": "create_goal",
            "description": "اهداف کاربر را ثبت یا ویرایش می کند. برای ثبت یک هدف جدید یا بروزرسانی هدف موجود استفاده می شود.",
            "url": f"{django_api_base_url}/tools/goals/create/",
            "method": "POST",
            "args": [
                create_arg("user_id", "شناسه یکتای کاربر در سیستم شما.", "STRING", True),
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
            "url": f"{django_api_base_url}/tools/health/update/",
            "method": "PATCH",
            "args": [
                create_arg("user_id", "شناسه یکتای کاربر در سیستم شما.", "STRING", True),
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
            "url": f"{django_api_base_url}/tools/psych/update/",
            "method": "PATCH",
            "args": [
                create_arg("user_id", "شناسه یکتای کاربر در سیستم شما.", "STRING", True),
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
            "url": f"{django_api_base_url}/tools/career/update/",
            "method": "PATCH",
            "args": [
                create_arg("user_id", "شناسه یکتای کاربر در سیستم شما.", "STRING", True),
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
            "url": f"{django_api_base_url}/tools/finance/update/",
            "method": "PATCH",
            "args": [
                create_arg("user_id", "شناسه یکتای کاربر در سیستم شما.", "STRING", True),
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
            "url": f"{django_api_base_url}/tools/social/update/",
            "method": "PATCH",
            "args": [
                create_arg("user_id", "شناسه یکتای کاربر در سیستم شما.", "STRING", True),
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
            "url": f"{django_api_base_url}/tools/preferences/update/",
            "method": "PATCH",
            "args": [
                create_arg("user_id", "شناسه یکتای کاربر در سیستم شما.", "STRING", True),
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
            "url": f"{django_api_base_url}/tools/environment/update/",
            "method": "PATCH",
            "args": [
                create_arg("user_id", "شناسه یکتای کاربر در سیستم شما.", "STRING", True),
                create_arg("current_city", "شهر محل زندگی فعلی.", "STRING", False),
                create_arg("climate", "وضعیت آب‌وهوایی محل زندگی (مثل معتدل، گرم، سرد).", "STRING", False,
                           ["معتدل", "گرم", "سرد", "خشک", "مرطوب"]),
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
            "url": f"{django_api_base_url}/tools/realtime/update/",
            "method": "PATCH",
            "args": [
                create_arg("user_id", "شناسه یکتای کاربر در سیستم شما.", "STRING", True),
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
            "url": f"{django_api_base_url}/tools/feedback/update/",
            "method": "PATCH",
            "args": [
                create_arg("user_id", "شناسه یکتای کاربر در سیستم شما.", "STRING", True),
                create_arg("feedback_text", "نظرات کاربر درباره عملکرد AI.", "STRING", False),
                create_arg("interaction_type", "نوع تعامل (مثل سوال، توصیه، دستور).", "STRING", False),
                create_arg("interaction_rating", "امتیاز کاربر به تعامل (از 1 تا 5).", "INTEGER", False),
                create_arg("interaction_frequency", "تعداد تعاملات در بازه زمانی.", "INTEGER", False),
            ]
        })
        tools.append({
            "name": "update_user_profile_details",
            "description": "جزئیات اضافی پروفایل کاربر را بروزرسانی یا ثبت می کند.",
            "url": f"{django_api_base_url}/tools/profile/update/",
            "method": "PATCH",
            "args": [
                create_arg("user_id", "شناسه یکتای کاربر در سیستم شما.", "STRING", True),
                create_arg("first_name", "نام کوچک کاربر.", "STRING", False),
                create_arg("last_name", "نام خانوادگی کاربر.", "STRING", False),
                create_arg("age", "سن کاربر.", "INTEGER", False),
                create_arg("gender", "جنسیت کاربر.", "STRING", False, ["مرد", "زن", "سایر"]),
                create_arg("nationality", "ملیت کاربر.", "STRING", False),
                create_arg("location", "محل زندگی کاربر (شهر یا کشور).", "STRING", False),
                create_arg("languages", "زبان‌های مورد استفاده کاربر.", "STRING", False),
                create_arg("cultural_background", "اطلاعات فرهنگی و ارزش‌های کاربر.", "STRING", False),
                create_arg("marital_status", "وضعیت تأهل (مجرد، متأهل، مطلقه).", "STRING", False,
                           ["مجرد", "متأهل", "مطلقه", "جدا شده", "بیوه"]),
                create_arg("ai_psychological_test", "نتیجه تست روانشناسی کاربر.", "STRING", False),
                create_arg("user_information_summary",
                           "خلاصه‌ای از تمام اطلاعات کاربر که با استفاده از هوش مصنوعی خلاصه شده است.", "STRING",
                           False),
            ]
        })
        tools.append({
            "name": "create_psych_test_record",
            "description": "یک رکورد جدید برای تست روانشناسی کاربر ایجاد می‌کند.",
            "url": f"{django_api_base_url}/tools/psych-test-history/create/",
            "method": "POST",
            "args": [
                create_arg("user_id", "شناسه یکتای کاربر در سیستم شما.", "STRING", True),
                create_arg("test_name", "نام تست (مثلاً MBTI Psychological Test).", "STRING", True),
                create_arg("test_result_summary", "خلاصه نتایج تست.", "STRING", True),
                create_arg("full_test_data", "داده‌های کامل تست به فرمت JSON (به صورت رشته JSON).", "STRING", False),
                create_arg("ai_analysis", "تحلیل AI از نتایج تست.", "STRING", False),
            ]
        })
        tools.append({
            "name": "update_psych_test_record",
            "description": "یک رکورد تست روانشناسی موجود کاربر را به‌روزرسانی می‌کند. باید pk رکورد را ارائه دهید.",
            "url": f"{django_api_base_url}/tools/psych-test-history/update/<int:pk>/",
            "method": "PATCH",
            "args": [
                create_arg("user_id", "شناسه یکتای کاربر در سیستم شما.", "STRING", True),
                create_arg("pk", "شناسه یکتای رکورد تست روانشناسی برای به‌روزرسانی.", "INTEGER", True),
                create_arg("test_name", "نام تست.", "STRING", False),
                create_arg("test_result_summary", "خلاصه نتایج تست.", "STRING", False),
                create_arg("full_test_data", "داده‌های کامل تست به فرمت JSON (به صورت رشته JSON).", "STRING", False),
                create_arg("ai_analysis", "تحلیل AI از نتایج تست.", "STRING", False),
            ]
        })
        tools.append({
            "name": "delete_psych_test_record",
            "description": "یک رکورد تست روانشناسی موجود کاربر را حذف می‌کند. باید pk رکورد را ارائه دهید.",
            "url": f"{django_api_base_url}/tools/psych-test-history/delete/<int:pk>/",
            "method": "DELETE",
            "args": [
                create_arg("user_id", "شناسه یکتای کاربر در سیستم شما.", "STRING", True),
                create_arg("pk", "شناسه یکتای رکورد تست روانشناسی برای حذف.", "INTEGER", True),
            ]
        })

        logger.debug(f"Defined {len(tools)} tools for Metis Bot API.")
        return tools