import requests
import json
import logging

# --- Global Configuration ---
METIS_API_KEY = 'tpsg-rzXGQBUB57hQLyyP0p9AxtU96rTboG6'  # کلید API شما
METIS_BOT_ID = 'be1823aa-ad0d-4827-9c27-68a388fb7551'  # شناسه ربات شما
BASE_URL = "https://api.metisai.ir/api/v1"

# !!!!!!!!!! مهم: این آدرس باید URL عمومی و معتبر شما از CPanel باشد !!!!!!!!!!
# مثال: DJANGO_CALLBACK_BASE_URL = "https://api.mobixtube.ir/api"
DJANGO_CALLBACK_BASE_URL = "https://api.mobixtube.ir/api"  # ## مطمئن شوید این آدرس صحیح و فعال است ##

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.StreamHandler()  # برای نمایش لاگ‌ها در کنسول
        # logging.FileHandler("update_bot.log", mode='w') # برای ذخیره لاگ‌ها در فایل (اختیاری)
    ]
)
logger = logging.getLogger(__name__)


class MetisBotUpdater:
    def __init__(self, api_key: str, bot_id: str, base_metis_url: str):
        self.api_key = api_key
        self.bot_id = bot_id
        self.base_metis_url = base_metis_url
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"  # اضافه کردن هدر Accept
        }
        if not self.api_key or not self.bot_id:
            logger.critical("API Key or Bot ID is missing!")
            raise ValueError("API Key or Bot ID must be provided.")
        logger.info(f"MetisBotUpdater initialized for Bot ID: {self.bot_id}")

    def _send_request(self, method: str, endpoint: str, payload: dict = None):
        url = f"{self.base_metis_url}/{endpoint}"
        logger.debug(f"Attempting {method} request to URL: {url}")
        logger.debug(f"Request Headers: {json.dumps(self.headers, indent=2)}")
        if payload:
            # لاگ کردن دقیق payload قبل از ارسال
            # برای جلوگیری از نمایش اطلاعات حساس در لاگ‌های عمومی، این بخش را در صورت نیاز محدود کنید
            logger.debug(f"Request Payload (JSON): {json.dumps(payload, indent=2, ensure_ascii=False)}")

        try:
            response = requests.request(method, url, headers=self.headers, json=payload, timeout=30)
            logger.debug(f"Response Status Code: {response.status_code}")
            logger.debug(f"Response Headers: {json.dumps(dict(response.headers), indent=2)}")
            logger.debug(f"Response Raw Text: {response.text}")

            response.raise_for_status()  # در صورت بروز خطای HTTP (4xx or 5xx)، یک استثنا ایجاد می‌کند

            # بررسی اینکه آیا پاسخ محتوایی دارد قبل از تلاش برای پارس کردن JSON
            if response.text and response.headers.get("Content-Type", "").startswith("application/json"):
                return response.json()
            elif response.text:  # اگر محتوا دارد ولی JSON نیست
                return {"status_code": response.status_code, "message": "Response was not JSON",
                        "content": response.text}
            else:  # اگر محتوایی ندارد (مثلاً برای پاسخ‌های 204 No Content)
                return {"status_code": response.status_code, "message": "No content in response"}

        except requests.exceptions.HTTPError as http_err:
            logger.error(f"HTTP error occurred: {http_err} - Status: {http_err.response.status_code}")
            logger.error(f"Response Content: {http_err.response.text}")
            raise  # استثنا را دوباره ایجاد می‌کنیم تا در بلوک اصلی مدیریت شود
        except requests.exceptions.Timeout:
            logger.error(f"Request timed out after 30 seconds for URL: {url}")
            raise
        except requests.exceptions.RequestException as req_err:
            logger.error(f"Error during request to {url}: {req_err}")
            raise
        except json.JSONDecodeError as json_err:
            logger.error(
                f"Failed to decode JSON response from {url}. Error: {json_err}. Response Text: {response.text}")
            raise ValueError(f"Invalid JSON response from Metis AI: {response.text}") from json_err
        except Exception as e:
            logger.exception(f"An unexpected error occurred in _send_request for URL {url}: {e}")
            raise

    def get_current_bot_config(self):
        logger.info(f"Fetching current configuration for bot: {self.bot_id}")
        return self._send_request("GET", f"bots/{self.bot_id}")

    def _get_minimal_test_function_schema(self, callback_base_url: str):
        logger.debug(f"Generating minimal test function schema with callback_base_url: {callback_base_url}")
        return [
            {
                "name": "get_simple_status",  # نام ساده انگلیسی
                "description": "یک تست ساده برای بررسی عملکرد فراخوانی تابع.",  # توضیحات ساده
                "url": f"{callback_base_url}/test-tool-status-minimal/",  # اندپوینت تستی شما
                "method": "GET",
                "args": []  # بدون آرگومان برای حداکثر سادگی
            }
        ]

    def update_bot_with_minimal_functions(self, current_config: dict, callback_base_url: str):
        logger.info("Preparing to update bot with a minimal set of functions.")

        # فقط فیلدهای ضروری که از مستندات Bot API برای PUT مشخص است یا منطقی به نظر می‌رسد
        # name, enabled, providerConfig معمولاً برای شناسایی و عملکرد اصلی ربات لازم هستند
        if not all(k in current_config for k in ["name", "enabled", "providerConfig"]):
            logger.error(
                f"Current bot config is missing essential fields (name, enabled, providerConfig): {current_config}")
            raise ValueError("Essential fields missing from current bot configuration.")

        payload = {
            "name": current_config["name"],
            "enabled": current_config["enabled"],
            "providerConfig": current_config["providerConfig"],
            "functions": self._get_minimal_test_function_schema(callback_base_url)
            # سایر فیلدهای اختیاری مانند instructions, description, avatar, corpusIds را فعلاً ارسال نمی‌کنیم
            # تا payload تا حد ممکن ساده باشد.
        }

        # اگر مستندات Metis یا تست‌ها نشان دهد که فیلدهای اختیاری حتی اگر null یا خالی هستند باید ارسال شوند،
        # می‌توانید آنها را اینجا از current_config اضافه کنید:
        # if 'instructions' in current_config: payload['instructions'] = current_config['instructions']
        # if 'description' in current_config: payload['description'] = current_config['description']
        # if 'corpusIds' in current_config: payload['corpusIds'] = current_config['corpusIds']
        # if 'avatar' in current_config: payload['avatar'] = current_config['avatar']

        logger.info(f"Attempting to update bot {self.bot_id} with minimal payload.")
        return self._send_request("PUT", f"bots/{self.bot_id}", payload=payload)


if __name__ == "__main__":
    logger.info("--- Metis Bot Function Updater Script Started (Minimal Approach) ---")

    if "YOUR_PUBLIC_TUNNEL_URL" in DJANGO_CALLBACK_BASE_URL or \
            DJANGO_CALLBACK_BASE_URL == "http://127.0.0.1:8000/api" or \
            DJANGO_CALLBACK_BASE_URL == "https://api.mobixtube.ir/api" and not DJANGO_CALLBACK_BASE_URL.startswith(
        "https://"):  # یک بررسی ساده
        logger.warning("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        logger.warning(f"CRITICAL: DJANGO_CALLBACK_BASE_URL is '{DJANGO_CALLBACK_BASE_URL}'.")
        logger.warning(
            "This needs to be your publicly accessible URL (e.g., your CPanel subdomain or ngrok/localtunnel URL).")
        logger.warning("Metis AI server will not be able to call back to a localhost or unconfigured URL.")
        logger.warning("Please verify and set it correctly at the top of the script.")
        logger.warning("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        # برای جلوگیری از اجرای با URL اشتباه، می‌توانید اینجا اسکریپت را متوقف کنید:
        # exit("Exiting due to potentially incorrect DJANGO_CALLBACK_BASE_URL.")

    bot_updater = MetisBotUpdater(api_key=METIS_API_KEY, bot_id=METIS_BOT_ID, base_metis_url=BASE_URL)

    try:
        # 1. دریافت پیکربندی فعلی ربات
        current_config = bot_updater.get_current_bot_config()
        logger.info(f"Successfully fetched current bot config. Name: {current_config.get('name')}")

        # 2. به‌روزرسانی ربات با استفاده از حداقل داده‌ها و یک تابع ساده
        update_response = bot_updater.update_bot_with_minimal_functions(current_config, DJANGO_CALLBACK_BASE_URL)
        logger.info("Bot update attempt finished.")
        logger.info(f"Update Response: {json.dumps(update_response, indent=2, ensure_ascii=False)}")

        if update_response.get("id") == METIS_BOT_ID:  # یا هر فیلدی که نشان‌دهنده موفقیت است
            logger.info("--- Bot update with minimal functions seems SUCCESSFUL! ---")
            logger.info(
                "Next steps: Try adding your original functions one by one to this script to find the problematic one.")
        else:
            logger.warning(
                "--- Bot update with minimal functions may have FAILED or returned unexpected response. Check logs carefully. ---")


    except ValueError as ve:
        logger.error(f"A value or JSON decoding error occurred: {ve}")
    except ConnectionError as ce:
        logger.error(f"A connection error occurred: {ce}")
    except Exception as e:
        logger.exception("An unexpected critical error occurred:")
    finally:
        logger.info("--- Metis Bot Function Updater Script Finished ---")