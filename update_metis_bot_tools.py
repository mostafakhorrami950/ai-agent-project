import requests
import json
import logging
import datetime

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

METIS_API_KEY = 'tpsg-rzXGQBUB57hQLyyP0p9AxtU96rTboG6'
METIS_BOT_ID = 'be1823aa-ad0d-4827-9c27-68a388fb7551'

BASE_URL = "https://api.metisai.ir/api/v1"


class MetisBotAPIUpdater:
    def __init__(self, api_key: str, bot_id: str):
        self.api_key = api_key
        self.bot_id = bot_id
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        if not self.api_key or not self.bot_id:
            logger.error("API Key or Bot ID not provided. Please check METIS_API_KEY and METIS_BOT_ID.")
            raise ValueError("API Key or Bot ID not provided.")
        logger.debug("MetisBotAPIUpdater initialized.")

    def _make_request(self, method: str, endpoint: str, json_data: dict = None, params: dict = None):
        url = f"{BASE_URL}/{endpoint}"
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
            logger.debug(f"[_make_request] Response Body: {response.text}")
            return response.json()
        except requests.exceptions.HTTPError as e:
            logger.error(
                f"[_make_request] HTTP Status Error: {e.response.status_code} {e.response.reason} for url: {e.request.url}, Response: {getattr(e.response, 'text', 'No response text')}")
            raise ConnectionError(f"Failed to connect to Metis AI: {e}")
        except requests.exceptions.RequestException as e:
            logger.error(f"[_make_request] Network/Timeout Error: {e} for url: {e.request.url if e.request else 'N/A'}")
            raise ConnectionError(
                f"Failed to connect to Metis AI (Network/Timeout): {e} for url: {e.request.url if e.request else 'N/A'}")
        except json.JSONDecodeError as e:
            logger.error(
                f"[_make_request] JSON Decode Error: {e}, Response content: {response.text if 'response' in locals() else 'N/A'}")
            raise ValueError(f"Invalid JSON response from Metis AI: {e}")
        except Exception as e:
            logger.error(f"[_make_request] An unexpected error occurred: {e}", exc_info=True)
            raise

    def get_bot_info(self, bot_id: str):
        endpoint = f"bots/{bot_id}"
        return self._make_request("GET", endpoint)

    def update_bot(self, bot_id: str, name: str, enabled: bool, provider_config: dict, instructions: str = None,
                   functions: list = None, corpus_ids: list = None, description: str = None, avatar: str = None):
        """
        Updates an existing bot with new configuration including functions.
        (Based on POSTMAN collection and ربات _ متیس.html)
        """
        endpoint = f"bots/{bot_id}"
        data = {
            "name": name,
            "enabled": enabled,
            "providerConfig": provider_config,
            "instructions": instructions,
            "functions": functions if functions is not None else [],
            "corpusIds": corpus_ids if corpus_ids is not None else []
        }
        if description is not None:
            data["description"] = description
        if avatar is not None:
            data["avatar"] = avatar

        logger.debug(f"[update_bot] Data to send: {json.dumps(data, indent=2, ensure_ascii=False)}")
        return self._make_request("PUT", endpoint, json_data=data)

    @staticmethod
    def get_tool_schemas_for_metis_bot():
        """
        Returns a list of tool definitions in Metis AI's 'Function' format for sending to Bot API.
        This schema is used when creating/updating a Bot in Metis AI.
        """
        django_api_base_url = "https://small-ducks-know.loca.lt/api"  # This should be your public Django API URL in production!

        def create_arg(name, description, arg_type, required, enum_values=None):
            arg = {"name": name, "description": description, "type": arg_type, "required": required}
            if enum_values is not None:  # Changed to check for None, not just empty list
                arg["enumValues"] = enum_values
            return arg

        tools = []

        # Tool for Goal model (users_ai_goal)
        tools.append({
            "name": "create_goal",
            "description": "اهداف کاربر را ثبت یا ویرایش می کند.",
            "url": f"{django_api_base_url}/goals/",
            "method": "POST",
            "args": [
                create_arg("goal_type", "نوع هدف (مثلاً شخصی، حرفه‌ای، مالی، سلامتی).", "STRING", True),
                create_arg("description", "توضیح کامل هدف کاربر (مثلاً یادگیری زبان جدید).", "STRING", True),
                create_arg("priority", "اولویت هدف (از 1 تا 5، 5 بالاترین اولویت).", "INTEGER", False),
                create_arg("deadline", "تاریخ مهلت دستیابی به هدف در قالبولندا-MM-DD.", "STRING", False),
                create_arg("progress", "درصد پیشرفت فعلی هدف (از 0.0 تا 100.0).", "NUMBER", False),
            ],
        })

        # Tool for HealthRecord (users_ai_healthrecord)
        tools.append({
            "name": "update_health_record",
            "description": "سوابق سلامتی جسمانی و روانی کاربر را بروزرسانی یا ثبت می کند. برای اضافه کردن یا تغییر اطلاعات پزشکی کاربر استفاده می شود.",
            "url": f"{django_api_base_url}/health-record/",
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
                create_arg("last_checkup_date", "تاریخ آخرین معاینه پزشکی در قالبولندا-MM-DD.", "STRING", False),
            ]
        })

        tools.append({
            "name": "update_psychological_profile",
            "description": "پروفایل روانشناختی و ویژگی‌های شخصیتی کاربر را بروزرسانی یا ثبت می کند.",
            "url": f"{django_api_base_url}/psychological-profile/",
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
            "url": f"{django_api_base_url}/career-education/",
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
            "url": f"{django_api_base_url}/financial-info/",
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
            "url": f"{django_api_base_url}/social-relationship/",
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
            "url": f"{django_api_base_url}/preferences-interests/",
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
            "url": f"{django_api_base_url}/environmental-context/",
            "method": "PATCH",
            "args": [
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
            "url": f"{django_api_base_url}/real-time-data/",
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
            "url": f"{django_api_base_url}/feedback-learning/",
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


# --- Main execution block for the independent script ---
if __name__ == "__main__":
    logger.info("Starting Metis Bot Tools Update Script.")
    updater = MetisBotAPIUpdater(METIS_API_KEY, METIS_BOT_ID)

    try:
        # 1. اطلاعات فعلی ربات را دریافت کنید
        logger.info(f"Fetching current bot info for bot ID: {updater.bot_id}")
        current_bot_info = updater.get_bot_info(updater.bot_id)

        if not current_bot_info:
            logger.error(
                f"Failed to retrieve bot info for ID: {updater.bot_id}. Please ensure the bot ID is correct and the bot exists in your Metis AI console.")
            logger.info("Script finished with errors.")
            exit(1)

        logger.info(f"Current bot name: {current_bot_info.get('name')}, Enabled: {current_bot_info.get('enabled')}")

        # 2. Tool Schemas را دریافت کنید
        new_tools = MetisBotAPIUpdater.get_tool_schemas_for_metis_bot()

        # 3. اطلاعات ربات را با Tool Schemas جدید بروزرسانی کنید
        logger.info(f"Updating bot {updater.bot_id} with {len(new_tools)} new tools...")
        updated_bot_response = updater.update_bot(
            bot_id=updater.bot_id,
            name=current_bot_info.get('name', 'My AI Assistant Bot'),
            enabled=current_bot_info.get('enabled', True),
            instructions=current_bot_info.get('instructions'),
            provider_config=current_bot_info.get('providerConfig'),
            functions=new_tools,
            corpus_ids=current_bot_info.get('corpusIds'),
            description=current_bot_info.get('description'),
            avatar=current_bot_info.get('avatar')
        )
        logger.info(f"Bot {updater.bot_id} updated successfully. Response: {updated_bot_response}")
        logger.info("Script finished successfully.")

    except ConnectionError as e:
        logger.error(f"Connection error during bot update: {e}")
        logger.info("Script finished with errors.")
        exit(1)
    except Exception as e:
        logger.exception(f"An unexpected error occurred during bot update: {e}")
        logger.info("Script finished with errors.")
        exit(1)