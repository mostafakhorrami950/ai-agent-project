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
                logger.info(f"[_make_request] !!! JSON ارسالی: {json.dumps(json_data, indent=2, ensure_ascii=False)}")
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

    # Bot Management Methods - Use bot_management_base_url
    def create_bot(self, name, enabled, provider_config, instructions=None, functions=None, corpus_ids=None):
        endpoint = "bots"
        data = {
            "name": name,
            "enabled": enabled,
            "providerConfig": provider_config,
            "instructions": instructions,
            "functions": functions if functions is not None else [],
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
            data["functions"] = functions
        else:
            data["functions"] = []
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
            "user": user_data if user_data is not None else {},
            "initialMessages": initial_messages if initial_messages is not None else []
        }
        if functions is not None:
            data["functions"] = functions
        else:
            data["functions"] = []

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
        """
        Generates the list of tool schemas for Metis AI to consume.
        These schemas define the functions Metis AI can call on your Django API.
        The `url` field in each tool schema is the actual API endpoint that Metis AI will call.
        """
        django_api_base_url = getattr(settings, 'DJANGO_API_BASE_URL', "https://api.mobixtube.ir/api")
        if django_api_base_url == "https://api.mobixtube.ir/api":
            logger.warning(
                "Using default DJANGO_API_BASE_URL. Ensure this is configured in settings.py for production.")

        # تغییر: description برای آرگومان‌ها حذف شد تا با محدودیت احتمالی Metis AI سازگار شود.
        def create_arg(name, arg_type, required):  # description از اینجا حذف شد
            arg = {"name": name, "type": arg_type, "required": required}
            # arg["description"] = description # این خط دیگر لازم نیست
            return arg

        tools = []

        tools.append({
            "name": "create_goal",
            "description": "اهداف کاربر را ثبت یا ویرایش می کند. برای ثبت یک هدف جدید یا بروزرسانی هدف موجود استفاده می شود.",
            "url": f"{django_api_base_url}/tools/goals/create/",
            "method": "POST",
            "args": [
                create_arg("user_id", "STRING", True),  # description حذف شد
                create_arg("goal_type", "STRING", True),  # description حذف شد
                create_arg("description", "STRING", True),  # description حذف شد
                create_arg("priority", "INTEGER", False),  # NUMBER به INTEGER تغییر یافت
                create_arg("deadline", "STRING", False),  # description حذف شد
                create_arg("progress", "FLOAT", False),  # NUMBER به FLOAT تغییر یافت
            ],
        })
        tools.append({
            "name": "update_health_record",
            "description": "سوابق سلامتی جسمانی و روانی کاربر را بروزرسانی یا ثبت می کند.",
            "url": f"{django_api_base_url}/tools/health/update/",
            "method": "PATCH",
            "args": [
                create_arg("user_id", "STRING", True),
                create_arg("medical_history", "STRING", False),
                create_arg("chronic_conditions", "STRING", False),
                create_arg("allergies", "STRING", False),
                create_arg("diet_type", "STRING", False),
                create_arg("daily_calorie_intake", "INTEGER", False),  # NUMBER به INTEGER تغییر یافت
                create_arg("physical_activity_level", "STRING", False),
                create_arg("height", "FLOAT", False),  # NUMBER به FLOAT تغییر یافت
                create_arg("weight", "FLOAT", False),  # NUMBER به FLOAT تغییر یافت
                create_arg("bmi", "FLOAT", False),  # NUMBER به FLOAT تغییر یافت
                create_arg("mental_health_status", "STRING", False),
                create_arg("sleep_hours", "FLOAT", False),  # NUMBER به FLOAT تغییر یافت
                create_arg("medications", "STRING", False),
                create_arg("last_checkup_date", "STRING", False),
            ]
        })
        tools.append({
            "name": "update_psychological_profile",
            "description": "پروفایل روانشناختی و ویژگی‌های شخصیتی کاربر را بروزرسانی یا ثبت می کند.",
            "url": f"{django_api_base_url}/tools/psych/update/",
            "method": "PATCH",
            "args": [
                create_arg("user_id", "STRING", True),
                create_arg("personality_type", "STRING", False),
                create_arg("core_values", "STRING", False),
                create_arg("motivations", "STRING", False),
                create_arg("decision_making_style", "STRING", False),
                create_arg("stress_response", "STRING", False),
                create_arg("emotional_triggers", "STRING", False),
                create_arg("preferred_communication", "STRING", False),
                create_arg("resilience_level", "STRING", False),
            ]
        })
        tools.append({
            "name": "update_career_education",
            "description": "اطلاعات مسیر تحصیلی و حرفه‌ای کاربر را بروزرسانی یا ثبت می کند.",
            "url": f"{django_api_base_url}/tools/career/update/",
            "method": "PATCH",
            "args": [
                create_arg("user_id", "STRING", True),
                create_arg("education_level", "STRING", False),
                create_arg("field_of_study", "STRING", False),
                create_arg("skills", "STRING", False),
                create_arg("job_title", "STRING", False),
                create_arg("industry", "STRING", False),
                create_arg("job_satisfaction", "INTEGER", False),  # NUMBER به INTEGER تغییر یافت
                create_arg("career_goals", "STRING", False),
                create_arg("work_hours", "FLOAT", False),  # NUMBER به FLOAT تغییر یافت
                create_arg("learning_style", "STRING", False),
                create_arg("certifications", "STRING", False),
            ]
        })
        tools.append({
            "name": "update_financial_info",
            "description": "داده‌های مالی کاربر را بروزرسانی یا ثبت می کند.",
            "url": f"{django_api_base_url}/tools/finance/update/",
            "method": "PATCH",
            "args": [
                create_arg("user_id", "STRING", True),
                create_arg("monthly_income", "FLOAT", False),  # NUMBER به FLOAT تغییر یافت
                create_arg("monthly_expenses", "FLOAT", False),  # NUMBER به FLOAT تغییر یافت
                create_arg("savings", "FLOAT", False),  # NUMBER به FLOAT تغییر یافت
                create_arg("debts", "FLOAT", False),  # NUMBER به FLOAT تغییر یافت
                create_arg("investment_types", "STRING", False),
                create_arg("financial_goals", "STRING", False),
                create_arg("risk_tolerance", "STRING", False),
                create_arg("budgeting_habits", "STRING", False),
            ]
        })
        tools.append({
            "name": "update_social_relationship",
            "description": "اطلاعات شبکه اجتماعی و تعاملات کاربر را بروزرسانی یا ثبت می کند.",
            "url": f"{django_api_base_url}/tools/social/update/",
            "method": "PATCH",
            "args": [
                create_arg("user_id", "STRING", True),
                create_arg("key_relationships", "STRING", False),
                create_arg("relationship_status", "STRING", False),
                create_arg("communication_style", "STRING", False),
                create_arg("emotional_needs", "STRING", False),
                create_arg("social_frequency", "STRING", False),
                create_arg("conflict_resolution", "STRING", False),
            ]
        })
        tools.append({
            "name": "update_preference_interest",
            "description": "ترجیحات و علایق کاربر را بروزرسانی یا ثبت می کند.",
            "url": f"{django_api_base_url}/tools/preferences/update/",
            "method": "PATCH",
            "args": [
                create_arg("user_id", "STRING", True),
                create_arg("hobbies", "STRING", False),
                create_arg("favorite_music_genres", "STRING", False),
                create_arg("favorite_movies", "STRING", False),
                create_arg("reading_preferences", "STRING", False),
                create_arg("travel_preferences", "STRING", False),
                create_arg("food_preferences", "STRING", False),
                create_arg("lifestyle_choices", "STRING", False),
                create_arg("movie_fav_choices", "STRING", False),
            ]
        })
        tools.append({
            "name": "update_environmental_context",
            "description": "اطلاعات محیطی و زمینه‌ای کاربر را بروزرسانی یا ثبت می کند.",
            "url": f"{django_api_base_url}/tools/environment/update/",
            "method": "PATCH",
            "args": [
                create_arg("user_id", "STRING", True),
                create_arg("current_city", "STRING", False),
                create_arg("climate", "STRING", False),
                create_arg("housing_type", "STRING", False),
                create_arg("tech_access", "STRING", False),
                create_arg("life_events", "STRING", False),
                create_arg("transportation", "STRING", False),
            ]
        })
        tools.append({
            "name": "update_real_time_data",
            "description": "داده‌های لحظه‌ای کاربر را بروزرسانی یا ثبت می کند.",
            "url": f"{django_api_base_url}/tools/realtime/update/",
            "method": "PATCH",
            "args": [
                create_arg("user_id", "STRING", True),
                create_arg("current_location", "STRING", False),
                create_arg("current_mood", "STRING", False),
                create_arg("current_activity", "STRING", False),
                create_arg("daily_schedule", "STRING", False),
                create_arg("heart_rate", "INTEGER", False),  # NUMBER به INTEGER تغییر یافت
            ]
        })
        tools.append({
            "name": "update_feedback_learning",
            "description": "بازخوردهای کاربر و داده‌های یادگیری AI را بروزرسانی یا ثبت می کند.",
            "url": f"{django_api_base_url}/tools/feedback/update/",
            "method": "PATCH",
            "args": [
                create_arg("user_id", "STRING", True),
                create_arg("feedback_text", "STRING", False),
                create_arg("interaction_type", "STRING", False),
                create_arg("interaction_rating", "INTEGER", False),  # NUMBER به INTEGER تغییر یافت
                create_arg("interaction_frequency", "INTEGER", False),  # NUMBER به INTEGER تغییر یافت
            ]
        })
        tools.append({
            "name": "update_user_profile_details",
            "description": "جزئیات اضافی پروفایل کاربر را بروزرسانی یا ثبت می کند.",
            "url": f"{django_api_base_url}/tools/profile/update/",
            "method": "PATCH",
            "args": [
                create_arg("user_id", "STRING", True),
                create_arg("first_name", "STRING", False),
                create_arg("last_name", "STRING", False),
                create_arg("age", "INTEGER", False),  # NUMBER به INTEGER تغییر یافت
                create_arg("gender", "STRING", False),
                create_arg("nationality", "STRING", False),
                create_arg("location", "STRING", False),
                create_arg("languages", "STRING", False),
                create_arg("cultural_background", "STRING", False),
                create_arg("marital_status", "STRING", False),
                create_arg("ai_psychological_test", "STRING", False),
                create_arg("user_information_summary", "STRING", False),
            ]
        })
        tools.append({
            "name": "create_psych_test_record",
            "description": "یک رکورد جدید برای تست روانشناسی کاربر ایجاد می‌کند.",
            "url": f"{django_api_base_url}/tools/psych-test-history/create/",
            "method": "POST",
            "args": [
                create_arg("user_id", "STRING", True),
                create_arg("test_name", "STRING", True),
                create_arg("test_result_summary", "STRING", True),
                create_arg("full_test_data", "STRING", False),
                create_arg("ai_analysis", "STRING", False),
            ]
        })
        tools.append({
            "name": "update_psych_test_record",
            "description": "یک رکورد تست روانشناسی موجود کاربر را به‌روزرسانی می‌کند. باید pk رکورد را ارائه دهید.",
            "url": f"{django_api_base_url}/tools/psych-test-history/update/",
            "method": "PATCH",
            "args": [
                create_arg("user_id", "STRING", True),
                create_arg("pk", "INTEGER", True),  # NUMBER به INTEGER تغییر یافت
                create_arg("test_name", "STRING", False),
                create_arg("test_result_summary", "STRING", False),
                create_arg("full_test_data", "STRING", False),
                create_arg("ai_analysis", "STRING", False),
            ]
        })
        tools.append({
            "name": "delete_psych_test_record",
            "description": "یک رکورد تست روانشناسی موجود کاربر را حذف می‌کند. باید pk رکورد را ارائه دهید.",
            "url": f"{django_api_base_url}/tools/psych-test-history/delete/",
            "method": "DELETE",
            "args": [
                create_arg("user_id", "STRING", True),
                create_arg("pk", "INTEGER", True),  # NUMBER به INTEGER تغییر یافت
            ]
        })

        logger.debug(f"Defined {len(tools)} tools for Metis Bot API.")
        return tools