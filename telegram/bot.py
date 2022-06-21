import logging
import re
from typing import List, Optional
from uuid import uuid4

import pytimeparse
import telebot
from celery.canvas import Signature, chain, chord
from django.conf import settings
from telebot.types import Message

from moviemaker.tasks import download_youtube_video, transform_video, concatenate_videos
from moviemaker.utils import video_id_from_url
from telegram.models import Chat, TaskMessage
from telegram.tasks import reply_with_video, reply_with_error_msg, update_task_progress, TaskProgressEvent

bot = telebot.TeleBot(
    token=settings.TELEGRAM_BOT_TOKEN,
    parse_mode='Markdown',
    threaded=True,
)
logger = logging.getLogger(__name__)


@bot.message_handler()
def _cmd_default(message: Message) -> None:
    chat = Chat.update_from_message(message)
    message_id = message.message_id
    task_message_id = uuid4()

    msg_text = message.text.strip()
    msg_text = re.sub(r" +", ' ', msg_text)

    prepare_video_tasks: List[Signature] = []
    for video_n, line in enumerate(msg_text.splitlines(), start=1):
        line = line.strip()
        video_url, *params_raw = line.split()
        params: List[str] = [el.casefold() for el in params_raw]

        try:
            video_id = video_id_from_url(video_url)

            cut_from_ms: Optional[int]
            if 'from' in params:
                try:
                    cut_from_time = pytimeparse.parse(params[params.index('from')+1])
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
                    cut_to_time = pytimeparse.parse(params[params.index('to')+1])
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

        prepare_video_tasks.append(
            chain(
                download_youtube_video.signature(
                    args=(video_id,),
                    link=update_task_progress.si(TaskProgressEvent.DOWNLOAD_TASK_FINISHED, task_message_id),
                ),
                transform_video.signature(
                    args=(cut_from_ms, cut_to_ms,),
                    link=update_task_progress.si(TaskProgressEvent.TRANSFORM_TASK_FINISHED, task_message_id),
                ),
            ),
        )

    status_message = bot.reply_to(message, '*Starting...*')
    task_message = TaskMessage(
        id=task_message_id,
        chat=chat,
        message_id=message_id,
        status_message_id=status_message.message_id,
        result_message_id=None,
        download_tasks_total=len(prepare_video_tasks),
        transform_tasks_total=len(prepare_video_tasks),
        concatenate_tasks_total=1,
    )
    task_message.save()
    update_task_progress(None, task_message_id)

    complete_task = chord(
        header=prepare_video_tasks,
        body=chain(
            concatenate_videos.signature(
                args=(),
                link=update_task_progress.si(TaskProgressEvent.CONCATENATE_TASK_FINISHED, task_message_id),
            ),
            reply_with_video.signature(
                args=(task_message_id,),
                link=None,
            ),
        ),
    )
    complete_task.link_error(reply_with_error_msg.s(task_message_id))
    complete_task.apply_async()
