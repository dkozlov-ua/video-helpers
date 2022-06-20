import logging
import re
from typing import List, Optional

import pytimeparse
import telebot
from celery.canvas import Signature, group
from django.conf import settings
from telebot.types import Message

from moviemaker.tasks import download_youtube_video, transform_video, concatenate_videos
from moviemaker.utils import video_id_from_url
from telegram.models import Chat, TaskMessage
from telegram.tasks import reply_with_video, reply_with_error_msg, update_task_progress

bot = telebot.TeleBot(
    token=settings.TELEGRAM_BOT_TOKEN,
    parse_mode='MarkdownV2',
    threaded=True,
)
logger = logging.getLogger(__name__)


@bot.message_handler()
def _cmd_default(message: Message) -> None:
    chat = Chat.update_from_message(message)
    message_id = message.message_id

    msg_text = message.text.strip()
    msg_text = re.sub(r" +", ' ', msg_text)

    prepare_video_tasks: List[Signature] = []
    for video_n, line in enumerate(msg_text.splitlines(), start=1):
        line = line.strip()
        video_url, *params_raw = line.split(maxsplit=1)
        params: List[str] = [el.casefold() for el in params_raw]

        try:
            video_id = video_id_from_url(video_url)

            cut_from_ms: Optional[int]
            if 'from' in params:
                try:
                    cut_from_time = pytimeparse.parse(params.index('from')+1)
                except IndexError:
                    cut_from_time = None
                if cut_from_time is None:
                    raise ValueError('Cannot parse value for the "from" parameter')
                cut_from_ms = int(cut_from_time * 1000)
            else:
                cut_from_ms = None

            cut_to_ms: Optional[int]
            if 'to' in params:
                try:
                    cut_to_time = pytimeparse.parse(params.index('to')+1)
                except IndexError:
                    cut_to_time = None
                if cut_to_time is None:
                    raise ValueError('Cannot parse value for the "to" parameter')
                cut_to_ms = int(cut_to_time * 1000)
            else:
                cut_to_ms = None

        except ValueError as exc:
            bot.reply_to(message, f"❗ Video #{video_n}: {str(exc)}")
            return

        download_video_sig = download_youtube_video.signature(
            args=(video_id,),
            link=update_task_progress.si(chat, message_id, 'download'),
        )
        transform_video_sig = transform_video.signature(
            args=(cut_from_ms, cut_to_ms,),
            link=update_task_progress.si(chat, message_id, 'transform'),
        )
        prepare_video_tasks.append(download_video_sig | transform_video_sig)

    task_message = TaskMessage(
        chat=chat,
        message_id=message_id,
        download_tasks_total=len(prepare_video_tasks),
        transform_tasks_total=len(prepare_video_tasks),
        concatenate_tasks_total=1,
    )
    task_message.save()
    update_task_progress(chat, message_id, None)

    concatenate_videos_sig = concatenate_videos.signature(
        args=(),
        link=update_task_progress.si(chat, message_id, 'concatenate'),
    )
    reply_with_video_sig = reply_with_video.signature(
        args=(chat, message_id,),
        link=update_task_progress.si(chat, message_id, 'finished'),
    )
    complete_task: Signature = (
            group(*prepare_video_tasks)
            | concatenate_videos_sig
            | reply_with_video_sig
    )
    complete_task.link_error(reply_with_error_msg.s(chat, message.message_id))
    complete_task.apply_async()
