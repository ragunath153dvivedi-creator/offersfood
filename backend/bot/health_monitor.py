"""
Bot Health Monitor
Runs as a background process, checks bot health every 2 minutes,
and promotes standby bots if the active one goes down.
"""

import os
import sys
import time
import logging
import hashlib
import requests
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Add parent dir to path for Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from django.utils import timezone
from core.models import BotConfig

logging.basicConfig(level=logging.INFO, format="%(asctime)s [HEALTH] %(message)s")
logger = logging.getLogger(__name__)

CHECK_INTERVAL = int(os.getenv("HEALTH_CHECK_INTERVAL", "120"))  # seconds
WEBHOOK_BASE = os.getenv("TELEGRAM_WEBHOOK_BASE_URL", "")


def check_bot(bot: BotConfig) -> bool:
    """Check if a bot is responsive via getMe."""
    try:
        resp = requests.get(
            f"https://api.telegram.org/bot{bot.token}/getMe",
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json().get("result", {})
            bot.bot_username = data.get("username", bot.bot_username)
            bot.last_error = ""
            return True
        elif resp.status_code in (401, 403):
            bot.last_error = f"Bot banned or token revoked (HTTP {resp.status_code})"
            return False
        else:
            bot.last_error = f"HTTP {resp.status_code}"
            return False
    except requests.Timeout:
        bot.last_error = "Timeout"
        return False
    except Exception as e:
        bot.last_error = str(e)[:200]
        return False


def set_webhook(bot: BotConfig) -> bool:
    """Set webhook for a bot."""
    if not WEBHOOK_BASE:
        logger.info("No WEBHOOK_BASE set, skipping webhook setup")
        return True

    token_hash = hashlib.sha256(bot.token.encode()).hexdigest()[:16]
    webhook_url = f"{WEBHOOK_BASE}/api/webhook/{token_hash}/"

    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{bot.token}/setWebhook",
            json={"url": webhook_url},
            timeout=10,
        )
        if resp.status_code == 200 and resp.json().get("ok"):
            logger.info(f"Webhook set for {bot.name}: {webhook_url}")
            bot.is_webhook_set = True
            return True
        else:
            logger.error(f"Failed to set webhook for {bot.name}: {resp.text}")
            return False
    except Exception as e:
        logger.error(f"Webhook error for {bot.name}: {e}")
        return False


def remove_webhook(bot: BotConfig):
    """Remove webhook from a bot."""
    try:
        requests.post(
            f"https://api.telegram.org/bot{bot.token}/deleteWebhook",
            timeout=10,
        )
        bot.is_webhook_set = False
    except Exception:
        pass


def run_health_check():
    """Run a single health check cycle."""
    bots = list(BotConfig.objects.all().order_by("priority"))
    if not bots:
        logger.warning("No bots configured")
        return

    active_bot = None
    needs_promotion = False

    for bot in bots:
        healthy = check_bot(bot)
        bot.last_health_check = timezone.now()

        if bot.status == BotConfig.Status.ACTIVE:
            if healthy:
                active_bot = bot
                logger.info(f"✅ Active bot '{bot.name}' is healthy")
            else:
                logger.warning(f"❌ Active bot '{bot.name}' is DOWN! Error: {bot.last_error}")
                bot.status = BotConfig.Status.BANNED if "banned" in bot.last_error.lower() else BotConfig.Status.ERROR
                remove_webhook(bot)
                needs_promotion = True
        elif bot.status in (BotConfig.Status.STANDBY,):
            if healthy:
                logger.info(f"🟡 Standby bot '{bot.name}' is healthy")
            else:
                logger.warning(f"🔴 Standby bot '{bot.name}' is unhealthy: {bot.last_error}")
                bot.status = BotConfig.Status.ERROR
        elif bot.status in (BotConfig.Status.BANNED, BotConfig.Status.ERROR):
            if healthy:
                logger.info(f"🔄 Previously failed bot '{bot.name}' is now healthy, moving to standby")
                bot.status = BotConfig.Status.STANDBY

        bot.save()

    # Promote a standby bot if needed
    if needs_promotion:
        standby = BotConfig.objects.filter(status=BotConfig.Status.STANDBY).order_by("priority").first()
        if standby:
            standby.status = BotConfig.Status.ACTIVE
            set_webhook(standby)
            standby.save()
            logger.info(f"🚀 PROMOTED '{standby.name}' to active!")
        else:
            logger.error("🚨 NO HEALTHY STANDBY BOTS AVAILABLE! All bots are down.")


def main():
    """Run the health monitor loop."""
    logger.info(f"Bot health monitor started (checking every {CHECK_INTERVAL}s)")

    # Initial check
    run_health_check()

    while True:
        time.sleep(CHECK_INTERVAL)
        try:
            run_health_check()
        except Exception as e:
            logger.error(f"Health check cycle failed: {e}")


if __name__ == "__main__":
    main()
