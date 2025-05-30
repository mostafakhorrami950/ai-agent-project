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
        response = None  # Initialize response
        try:
            logger.debug(f"[_make_request] Attempting request to {method} {url}")
            # logger.debug(f"[_make_request] Request Headers: {self.headers}") # Can be verbose
            if json_data:
                log_data_keys = list(json_data.keys())
                logger.info(f"[_make_request] JSON Sent (keys): {log_data_keys}")
                # To log full JSON for debugging (be careful with large payloads):
                # if settings.DEBUG or logger.isEnabledFor(logging.DEBUG): # Only log full payload in debug
                #    logger.debug(f"[_make_request] Full JSON Sent: {json.dumps(json_data, indent=2, ensure_ascii=False)}")
            if params:
                logger.debug(f"[_make_request] Request Params: {params}")

            response = requests.request(method, url, headers=self.headers, json=json_data, params=params, timeout=60)

            logger.info(f"[_make_request] Response Status Code from Metis: {response.status_code} for URL: {url}")
            # Log a snippet of the response text for quick diagnostics
            # logger.debug(f"[_make_request] Response Text from Metis (snippet): {response.text[:500] if response.text else 'No text'}")

            response.raise_for_status()

            if response.status_code == 204:
                logger.info(f"[_make_request] Response Status: 204 No Content. Returning None for URL: {url}")
                return None

            if response.text:  # Check if there's content to parse
                response_json = response.json()
                # logger.debug(f"[_make_request] Full Response JSON Body: {json.dumps(response_json, indent=2, ensure_ascii=False)}")
                return response_json
            else:
                logger.warning(
                    f"[_make_request] Response was successful (status {response.status_code}) but had no content to decode as JSON for URL: {url}.")
                return {}  # Return empty dict or None, depending on expected behavior for empty successful responses

        except requests.exceptions.HTTPError as e:
            response_text = getattr(e.response, 'text', 'No response text available in HTTPError')
            status_code_val = e.response.status_code if e.response is not None else 'N/A'
            logger.error(
                f"[_make_request] HTTP Error: {status_code_val} for url: {url}. Response: {response_text[:1000]}...")  # Log more of the error
            try:
                if response_text and e.response is not None and 'application/json' in e.response.headers.get(
                        'Content-Type', ''):
                    error_details = json.loads(response_text)
                    raise ConnectionError(
                        f"Metis AI API Error ({status_code_val}): {json.dumps(error_details, ensure_ascii=False)}")
                else:
                    raise ConnectionError(f"Metis AI API Error ({status_code_val}): {response_text}")
            except json.JSONDecodeError:
                raise ConnectionError(f"Metis AI API Error ({status_code_val}) (non-JSON response): {response_text}")
            except AttributeError:
                raise ConnectionError(f"Metis AI API Error (AttributeError accessing response): {response_text}")

        except json.JSONDecodeError as e_json:
            resp_status = response.status_code if response else 'N/A'
            resp_text = response.text if response else 'N/A'
            logger.error(
                f"[_make_request] JSON Decode Error: {e_json}. Response status: {resp_status}, Response content: {resp_text[:500]}...")
            raise ValueError(f"Invalid JSON response from Metis AI: {e_json}. Content: {resp_text[:500]}...")
        except requests.exceptions.RequestException as e_req:
            logger.error(
                f"[_make_request] Network/Request Error: {e_req} for url: {url}")
            raise ConnectionError(f"Failed to connect to Metis AI: {e_req}")
        except Exception as e_gen:
            logger.error(f"[_make_request] An unexpected error occurred for url {url}: {e_gen}", exc_info=True)
            raise

    # Bot Management Methods
    def create_bot(self, name, enabled, provider_config, instructions=None, functions=None, corpus_ids=None):
        endpoint = "bots"
        data = {
            "name": name,
            "enabled": enabled,
            "providerConfig": provider_config,
        }
        if instructions is not None: data["instructions"] = instructions
        if functions is not None: data["functions"] = functions  # Will be sent if provided
        if corpus_ids is not None: data["corpusIds"] = corpus_ids

        return self._make_request("POST", "bot_management", endpoint, json_data=data)

    def update_bot(self, bot_id, name=None, enabled=None, provider_config=None, instructions=None, functions=None,
                   corpus_ids=None, description=None, avatar=None):
        endpoint = f"bots/{bot_id}"
        data = {}
        if name is not None: data["name"] = name
        if enabled is not None: data["enabled"] = enabled
        if provider_config is not None: data["providerConfig"] = provider_config
        if instructions is not None: data["instructions"] = instructions
        if functions is not None: data["functions"] = functions
        if corpus_ids is not None: data["corpusIds"] = corpus_ids
        if description is not None: data["description"] = description
        if avatar is not None: data["avatar"] = avatar
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

    # Chat Session Methods
    def create_chat_session(self, bot_id, user_data=None, initial_messages=None):
        endpoint = "session"
        data = {
            "botId": bot_id,
            "user": user_data if user_data is not None else {},
            "initialMessages": initial_messages if initial_messages is not None else []
        }
        # Key "functions" is intentionally omitted here as per new strategy
        return self._make_request("POST", "chat", endpoint, json_data=data)

    def send_message(self, session_id, content, message_type="USER"):
        endpoint = f"session/{session_id}/message"
        data = {
            "message": {
                "content": content,
                "type": message_type
            }
        }
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

        # Removed redundant warning about DJANGO_API_BASE_URL as it's better handled once.

        def create_arg(name, arg_type, required, description=None):
            arg = {"name": name, "type": arg_type, "required": required}
            if description:
                arg["description"] = description
            return arg

        tools = []
        # Since the primary data gathering is now via "dynamic test",
        # the tools listed here are for potential ad-hoc updates or specific actions by the AI *after* initial profile setup.
        # Ensure descriptions are very clear for the LLM to avoid "hallucinated tool calls".

        tools.append({
            "name": "update_user_profile_details",
            "description": "جزئیات پروفایل پایه کاربر مانند سن، مکان و غیره را بر اساس اطلاعات جدید به‌روزرسانی می‌کند. نام و نام خانوادگی از این طریق قابل تغییر نیستند. فقط فیلدهایی که نیاز به تغییر دارند باید ارسال شوند.",
            "url": f"{django_api_base_url}/tools/profile/update/",
            "method": "PATCH",
            "args": [
                create_arg("user_id", "STRING", True, "شناسه عددی یکتای کاربر در سیستم ما."),
                create_arg("age", "INTEGER", False, "سن جدید کاربر (عدد صحیح)."),
                create_arg("gender", "STRING", False, "جنسیت جدید کاربر (مثال: مرد، زن، دیگر)."),
                create_arg("nationality", "STRING", False, "ملیت جدید کاربر."),
                create_arg("location", "STRING", False, "مکان (شهر/کشور) جدید کاربر."),
                create_arg("languages", "STRING", False,
                           "زبان یا زبان‌های جدیدی که کاربر صحبت می‌کند (مثلا: فارسی، انگلیسی)."),
                create_arg("cultural_background", "STRING", False, "توضیح مختصری از پیشینه فرهنگی جدید کاربر."),
                create_arg("marital_status", "STRING", False, "وضعیت تأهل جدید کاربر (مثال: مجرد، متاهل)."),
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
                # BMI is usually calculated, not set directly by AI unless specifically told.
                # create_arg("bmi", "FLOAT", False, "شاخص توده بدنی جدید (عدد اعشاری)."),
                create_arg("mental_health_status", "STRING", False, "وضعیت سلامت روان جدید یا اصلاح شده."),
                create_arg("sleep_hours", "FLOAT", False, "میانگین ساعات خواب جدید (عدد اعشاری)."),
                create_arg("medications", "STRING", False, "داروهای مصرفی جدید یا اصلاح شده."),
                create_arg("last_checkup_date", "STRING", False, "تاریخ آخرین معاینه پزشکی (فرمت YYYY-MM-DD)."),
            ]
        })

        tools.append({
            "name": "create_new_goal_for_user",
            "description": "یک هدف جدید (شخصی، حرفه‌ای، مالی و غیره) برای کاربر ایجاد می‌کند.",
            "url": f"{django_api_base_url}/tools/goals/create/",
            "method": "POST",
            "args": [
                create_arg("user_id", "STRING", True, "شناسه عددی یکتای کاربر."),
                create_arg("goal_type", "STRING", True, "نوع هدف (مثلاً: شخصی، حرفه‌ای، مالی، سلامتی)."),
                create_arg("description", "STRING", True, "شرح کامل و واضح هدف."),
                create_arg("priority", "INTEGER", False, "اولویت عددی هدف (مثلاً 1 برای کمترین، 5 برای بیشترین)."),
                create_arg("deadline", "STRING", False, "تاریخ مهلت دستیابی به هدف (فرمت YYYY-MM-DD)."),
            ],
        })

        tools.append({
            "name": "record_user_feedback",
            "description": "بازخورد متنی کاربر در مورد یک تعامل یا پاسخ خاص را ثبت می‌کند.",
            "url": f"{django_api_base_url}/tools/feedback/update/",  # مسیر فعلی شما برای این ویو
            "method": "POST",
            "args": [
                create_arg("user_id", "STRING", True, "شناسه عددی یکتای کاربر."),
                create_arg("feedback_text", "STRING", True, "متن کامل بازخورد کاربر."),
                create_arg("interaction_type", "STRING", False,
                           "نوع تعاملی که بازخورد به آن مربوط است (مثلاً 'پاسخ_AI', 'پیشنهاد_AI')."),
                create_arg("interaction_rating", "INTEGER", False, "امتیاز کاربر به تعامل (مثلاً از 1 تا 5)."),
            ]
        })

        tools.append({
            "name": "get_current_server_time",
            "description": "زمان و تاریخ فعلی سرور را برمی‌گرداند. برای اطلاع از ساعت فعلی استفاده می‌شود.",
            "url": f"{django_api_base_url}/test-tool-status-minimal/",
            "method": "GET",
            "args": []
        })

        logger.debug(f"Defined {len(tools)} tools for Metis Bot API.")
        return tools