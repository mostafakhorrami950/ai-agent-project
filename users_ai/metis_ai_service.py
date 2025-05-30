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
                # لاگ کردن بخشی از داده‌ها برای جلوگیری از لاگ‌های بسیار طولانی
                log_data = json_data.copy()
                if "initialMessages" in log_data and log_data["initialMessages"] and isinstance(
                        log_data["initialMessages"], list) and len(log_data["initialMessages"]) > 0 and "content" in \
                        log_data["initialMessages"][0]:
                    if len(log_data["initialMessages"][0]["content"]) > 300:
                        log_data["initialMessages"][0]["content"] = log_data["initialMessages"][0]["content"][
                                                                    :300] + "..."

                # لاگ کردن کلیدهای اصلی JSON ارسالی
                logger.info(f"[_make_request] !!! JSON ارسالی (keys): {list(json_data.keys())}")
                # برای دیباگ دقیق‌تر، می‌توانید بخشی از JSON یا کل آن را (با احتیاط در مورد حجم) لاگ کنید:
                # logger.info(f"[_make_request] !!! Full JSON ارسالی: {json.dumps(json_data, indent=2, ensure_ascii=False)}")

            if params:
                logger.debug(f"[_make_request] Request Params: {params}")

            response = requests.request(method, url, headers=self.headers, json=json_data, params=params, timeout=60)

            response.raise_for_status()

            if response.status_code == 204:
                logger.debug(f"[_make_request] Response Status: 204 No Content")
                return None

            response_json = response.json()
            logger.debug(f"[_make_request] Response Status: {response.status_code}")
            # logger.debug(f"[_make_request] Response JSON Body: {json.dumps(response_json, indent=2, ensure_ascii=False)}") # ممکن است پاسخ خیلی طولانی باشد
            return response_json

        except requests.exceptions.HTTPError as e:
            response_text = getattr(e.response, 'text', 'No response text')
            logger.error(
                f"[_make_request] HTTP Error: {e.response.status_code} for url: {e.request.url}, Response: {response_text}")
            try:
                error_details = json.loads(response_text)
                raise ConnectionError(
                    f"Metis AI API Error ({e.response.status_code}): {json.dumps(error_details, ensure_ascii=False)}")
            except json.JSONDecodeError:
                raise ConnectionError(f"Metis AI API Error ({e.response.status_code}): {response_text}")
        except json.JSONDecodeError as e_json:
            logger.error(
                f"[_make_request] JSON Decode Error after successful status: {e_json}, Response content: {response.text if 'response' in locals() else 'N/A'}")
            raise ValueError(f"Invalid JSON response from Metis AI despite 2xx status: {e_json}")
        except requests.exceptions.RequestException as e_req:
            logger.error(
                f"[_make_request] Network/Request Error: {e_req} for url: {e_req.request.url if e_req.request else 'N/A'}")
            raise ConnectionError(f"Failed to connect to Metis AI: {e_req}")
        except Exception as e_gen:
            logger.error(f"[_make_request] An unexpected error occurred: {e_gen}", exc_info=True)
            raise

    # Bot Management Methods - Use bot_management_base_url
    def create_bot(self, name, enabled, provider_config, instructions=None, functions=None, corpus_ids=None):
        endpoint = "bots"
        data = {
            "name": name,
            "enabled": enabled,
            "providerConfig": provider_config,
            "instructions": instructions,
        }
        if functions:  # فقط اگر functions مقدار دارد اضافه شود
            data["functions"] = functions
        if corpus_ids:  # فقط اگر corpus_ids مقدار دارد اضافه شود
            data["corpusIds"] = corpus_ids

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

        # فقط اگر functions مقدار دارد (حتی لیست خالی)، به data اضافه شود
        # اگر مقدار None است، یعنی نمی‌خواهیم این فیلد را در آپدیت ارسال کنیم
        if functions is not None:
            data["functions"] = functions

        if corpus_ids is not None: data["corpusIds"] = corpus_ids
        if description is not None: data["description"] = description
        if avatar is not None: data["avatar"] = avatar

        # logger.debug(f"[update_bot] Data to send: {json.dumps(data, indent=2, ensure_ascii=False)}")
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
    def create_chat_session(self, bot_id, user_data=None, initial_messages=None):  # پارامتر functions حذف شد
        endpoint = "session"
        data = {
            "botId": bot_id,
            "user": user_data if user_data is not None else {},
            "initialMessages": initial_messages if initial_messages is not None else []
        }
        # کلید "functions" دیگر به صورت پیش‌فرض یا در صورت None بودن functions اضافه نمی‌شود

        # logger.info(f"[create_chat_session] Sending data to Metis (log in _make_request)")
        return self._make_request("POST", "chat", endpoint, json_data=data)

    def send_message(self, session_id, content, message_type="USER"):
        endpoint = f"session/{session_id}/message"
        data = {
            "message": {
                "content": content,
                "type": message_type
            }
        }
        # logger.debug(f"[send_message] Data to send to Metis: {json.dumps(data, indent=2, ensure_ascii=False)}")
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
        if django_api_base_url == "https://api.mobixtube.ir/api" and not settings.DEBUG:
            logger.warning(
                "Using default DJANGO_API_BASE_URL in production. Ensure this is configured in settings.py for production.")

        def create_arg(name, arg_type, required, description=None):
            arg = {"name": name, "type": arg_type, "required": required}
            if description:
                arg["description"] = description
            return arg

        tools = []
        # با توجه به رویکرد "تست پویا"، ممکن است فعلاً به این ابزارها برای جمع‌آوری اولیه اطلاعات نیازی نباشد.
        # اما برای به‌روزرسانی‌های موردی پس از تکمیل پروفایل توسط AI، یا برای وظایف خاص دیگر می‌توانند مفید باشند.
        # اطمینان حاصل کنید که توضیحات (description) برای هر ابزار و آرگومان بسیار واضح و دقیق است.

        tools.append({
            "name": "update_user_profile_details",
            "description": "جزئیات پروفایل پایه کاربر مانند نام، سن، مکان و غیره را بر اساس اطلاعات جدید به‌روزرسانی می‌کند. فقط فیلدهایی که نیاز به تغییر دارند باید ارسال شوند.",
            "url": f"{django_api_base_url}/tools/profile/update/",
            "method": "PATCH",
            "args": [
                create_arg("user_id", "STRING", True, "شناسه عددی یکتای کاربر در سیستم."),
                create_arg("first_name", "STRING", False, "نام کوچک جدید کاربر."),
                create_arg("last_name", "STRING", False, "نام خانوادگی جدید کاربر."),
                create_arg("age", "INTEGER", False, "سن جدید کاربر (عدد صحیح)."),
                create_arg("gender", "STRING", False, "جنسیت جدید کاربر."),
                create_arg("nationality", "STRING", False, "ملیت جدید کاربر."),
                create_arg("location", "STRING", False, "مکان (شهر/کشور) جدید کاربر."),
                create_arg("languages", "STRING", False, "زبان یا زبان‌های جدیدی که کاربر صحبت می‌کند."),
                create_arg("cultural_background", "STRING", False, "پیشینه فرهنگی جدید کاربر."),
                create_arg("marital_status", "STRING", False, "وضعیت تأهل جدید کاربر."),
                # ai_psychological_test و user_information_summary معمولاً توسط سیستم پر می‌شوند، نه مستقیم توسط این ابزار.
            ]
        })

        tools.append({
            "name": "update_health_record",
            "description": "سوابق سلامتی کاربر (جسمانی و روانی) را بر اساس اطلاعات جدید به‌روزرسانی می‌کند. فقط فیلدهایی که نیاز به تغییر دارند باید ارسال شوند.",
            "url": f"{django_api_base_url}/tools/health/update/",
            "method": "PATCH",
            "args": [
                create_arg("user_id", "STRING", True, "شناسه عددی یکتای کاربر."),
                create_arg("medical_history", "STRING", False, "تاریخچه پزشکی جدید یا اصلاح شده."),
                create_arg("chronic_conditions", "STRING", False, "بیماری‌های مزمن جدید یا اصلاح شده."),
                create_arg("allergies", "STRING", False, "آلرژی‌های جدید یا اصلاح شده."),
                create_arg("diet_type", "STRING", False, "نوع رژیم غذایی جدید یا اصلاح شده."),
                create_arg("daily_calorie_intake", "INTEGER", False, "میانگین کالری مصرفی روزانه جدید (عدد صحیح)."),
                create_arg("physical_activity_level", "STRING", False, "سطح فعالیت بدنی جدید (مثلا کم، متوسط، زیاد)."),
                create_arg("height", "FLOAT", False, "قد جدید کاربر (عدد اعشاری، به سانتی‌متر)."),
                create_arg("weight", "FLOAT", False, "وزن جدید کاربر (عدد اعشاری، به کیلوگرم)."),
                create_arg("bmi", "FLOAT", False, "شاخص توده بدنی جدید (عدد اعشاری)."),
                create_arg("mental_health_status", "STRING", False, "وضعیت سلامت روان جدید یا اصلاح شده."),
                create_arg("sleep_hours", "FLOAT", False, "میانگین ساعات خواب جدید (عدد اعشاری)."),
                create_arg("medications", "STRING", False, "داروهای مصرفی جدید یا اصلاح شده."),
                create_arg("last_checkup_date", "STRING", False, "تاریخ آخرین معاینه پزشکی (فرمت YYYY-MM-DD)."),
            ]
        })

        # ... (تعریف سایر ابزارها مانند PsychologicalProfile, CareerEducation و غیره با توضیحات دقیق مشابه بالا)
        # ToolUpdatePsychologicalProfileView, ToolUpdateCareerEducationView, ... ToolCreateGoalView, ToolUpdateGoalView, ...

        # ابزار برای ایجاد یک هدف جدید برای کاربر
        tools.append({
            "name": "create_new_goal_for_user",  # نامی متفاوت از ابزارهای دیگر اگر لازم است
            "description": "یک هدف جدید (شخصی، حرفه‌ای، مالی و غیره) برای کاربر ایجاد می‌کند.",
            "url": f"{django_api_base_url}/tools/goals/create/",
            "method": "POST",
            "args": [
                create_arg("user_id", "STRING", True, "شناسه عددی یکتای کاربر."),
                create_arg("goal_type", "STRING", True, "نوع هدف (مثلاً: شخصی، حرفه‌ای، مالی)."),
                create_arg("description", "STRING", True, "شرح کامل هدف."),
                create_arg("priority", "INTEGER", False, "اولویت هدف (مثلاً 1 تا 5)."),
                create_arg("deadline", "STRING", False, "مهلت دستیابی به هدف (فرمت YYYY-MM-DD)."),
                create_arg("progress", "FLOAT", False, "درصد پیشرفت اولیه (معمولاً 0.0)."),
            ],
        })

        # ابزار برای ثبت بازخورد جدید کاربر
        tools.append({
            "name": "record_user_feedback",
            "description": "بازخورد متنی کاربر در مورد یک تعامل یا پاسخ خاص را ثبت می‌کند.",
            "url": f"{django_api_base_url}/tools/feedback/update/",
            # URL فعلی شما از /update/ استفاده می‌کند اما ویو POST است
            "method": "POST",  # ویو ToolUpdateFeedbackLearningView متد POST را می‌پذیرد
            "args": [
                create_arg("user_id", "STRING", True, "شناسه عددی یکتای کاربر."),
                create_arg("feedback_text", "STRING", True, "متن کامل بازخورد کاربر."),
                create_arg("interaction_type", "STRING", False,
                           "نوع تعاملی که بازخورد به آن مربوط است (مثلاً 'پاسخ_هوش_مصنوعی')."),
                create_arg("interaction_rating", "INTEGER", False, "امتیاز کاربر به تعامل (مثلاً 1 تا 5)."),
            ]
        })

        # ابزار نمونه برای تست زمان سرور (بدون نیاز به user_id در args، اما از طریق توکن احراز هویت می‌شود)
        tools.append({
            "name": "get_current_server_time",
            "description": "زمان و تاریخ فعلی سرور را برمی‌گرداند. برای اطلاع از ساعت فعلی استفاده می‌شود.",
            "url": f"{django_api_base_url}/test-tool-status-minimal/",
            "method": "GET",
            "args": []
        })

        logger.debug(f"Defined {len(tools)} tools for Metis Bot API based on current simplified list.")
        return tools