# pylint: disable=wrong-import-position
import logging

import click
import django

django.setup()

from django.conf import settings

from telegram.bot import bot


@click.command()
@click.option('--loglevel', help='Level for logging', default='INFO',
              type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], case_sensitive=False))
def main(loglevel: str) -> None:
    logger_level = getattr(logging, loglevel.upper())
    logger = logging.getLogger(__name__)
    logger.setLevel(logger_level)

    if settings.TELEGRAM_BOT_ENABLED:
        logger.info(f"Starting bot {settings.TELEGRAM_BOT_TOKEN.split(':')[0]}")
        bot.infinity_polling(logger_level=logger_level)
    else:
        logger.warning('Telegram bot is disabled. Exiting')


# pylint: disable=no-value-for-parameter
main()
