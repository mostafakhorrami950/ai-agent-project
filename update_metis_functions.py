# update_metis_functions.py
import os
import sys
import django
import json
import logging

# تنظیمات جنگو را بارگذاری کنید
# این خطوط تضمین می‌کنند که Django settings برای اسکریپت قابل دسترسی هستند
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aiagent.settings')
django.setup()

# حالا می‌توانید ماژول‌های جنگو را ایمپورت کنید
from django.conf import settings
from users_ai.metis_ai_service import MetisAIService

logger = logging.getLogger(__name__)

def update_metis_bot_functions():
    """
    Fetches the latest tool schemas from MetisAIService and updates the Metis AI bot.
    """
    try:
        metis_service = MetisAIService()

        # Get current bot info to ensure it exists and to get its current configuration
        # You might want to get bot_id from settings.METIS_BOT_ID
        bot_id = settings.METIS_BOT_ID
        if not bot_id:
            logger.error("METIS_BOT_ID is not set in Django settings.")
            print("Error: METIS_BOT_ID is not set in Django settings.")
            return

        print(f"Fetching current bot info for bot ID: {bot_id}...")
        try:
            current_bot_info = metis_service.get_bot_info(bot_id)
            print(f"Current bot name: {current_bot_info.get('name')}")
        except Exception as e:
            logger.error(f"Failed to fetch current bot info for {bot_id}: {e}")
            print(f"Error: Could not retrieve current bot info. Ensure the bot ID is correct and API key has permissions. Details: {e}")
            return

        # Get the latest tool schemas from your Django application
        print("Generating latest tool schemas from Django app...")
        latest_tools = MetisAIService.get_tool_schemas_for_metis_bot()
        print(f"Generated {len(latest_tools)} tool schemas.")

        # Update the bot with the new functions
        print(f"Updating bot {bot_id} with new function schemas...")
        updated_bot = metis_service.update_bot(
            bot_id=bot_id,
            functions=latest_tools,
            # You might want to pass other fields like name, enabled, instructions if you manage them here
            # For simplicity, we are only updating functions.
            # If you update bot properties here, make sure they are not None unless you intend to clear them.
            # Example: name=current_bot_info.get('name'), enabled=current_bot_info.get('enabled')
        )
        print("Bot update successful!")
        print(f"Updated Bot ID: {updated_bot.get('id')}")
        print(f"Updated Bot Name: {updated_bot.get('name')}")
        print(f"Updated Bot Functions (first 3): {updated_bot.get('functions', [])[:3]}...")

    except ValueError as ve:
        print(f"Configuration Error: {ve}")
        logger.error(f"Configuration Error: {ve}")
    except ConnectionError as ce:
        print(f"Metis AI API Connection Error: {ce}")
        logger.error(f"Metis AI API Connection Error: {ce}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        logger.exception("An unexpected error occurred during bot function update.")

if __name__ == "__main__":
    update_metis_bot_functions()