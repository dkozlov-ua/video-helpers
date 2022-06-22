from enum import Enum
from typing import Optional, NewType
from uuid import UUID

import telebot
from celery import shared_task
from django.conf import settings
from django.db.models import F
from telebot.apihelper import ApiTelegramException

from moviemaker.models import VideoFile
from telegram.models import TaskMessage

bot = telebot.TeleBot(
    token=settings.TELEGRAM_BOT_TOKEN,
    parse_mode='Markdown',
    threaded=False,
)


VideoId = NewType('VideoId', str)


@shared_task(acks_late=True, ignore_result=True)
def reply_with_video(video_id: VideoId, task_message_pk: UUID) -> None:
    task_message: TaskMessage = TaskMessage.objects.select_related().get(pk=task_message_pk)
    video: VideoFile = VideoFile.objects.get(id=video_id)
    with video.file.open(mode='rb') as file:
        result_message = bot.send_video(
            chat_id=task_message.chat.id,
            reply_to_message_id=task_message.message_id,
            video=file,
            supports_streaming=True,
            duration=video.duration,
            width=video.width,
            height=video.height,
        )
    task_message.result_message_id = result_message.message_id
    task_message.save(update_fields=('result_message_id',))
    try:
        bot.delete_message(chat_id=task_message.chat.id, message_id=task_message.status_message_id)
    except ApiTelegramException as exc:
        if exc.error_code != 400:
            raise


@shared_task(acks_late=True, ignore_result=True)
def reply_with_error_msg(request, exc, traceback, task_message_pk: UUID) -> None:
    _ = request
    _ = traceback
    task_message: TaskMessage = TaskMessage.objects.select_related().get(pk=task_message_pk)
    result_message = bot.send_message(
        chat_id=task_message.chat.id,
        reply_to_message_id=task_message.message_id,
        text=f"❗ `{type(exc).__name__}: {str(exc)}`"
    )
    task_message.result_message_id = result_message.message_id
    task_message.save(update_fields=('result_message_id',))
    try:
        bot.delete_message(chat_id=task_message.chat.id, message_id=task_message.status_message_id)
    except ApiTelegramException as error:
        if error.error_code != 400:
            raise


class TaskProgressEvent(Enum):
    DOWNLOAD_TASK_FINISHED = 1
    TRANSFORM_TASK_FINISHED = 2
    CONCATENATE_TASK_FINISHED = 3


@shared_task(acks_late=True, ignore_result=True)
def update_task_progress(event: Optional[TaskProgressEvent], task_message_pk: UUID) -> None:
    task_message: TaskMessage = TaskMessage.objects.select_related().get(pk=task_message_pk)
    if event is TaskProgressEvent.DOWNLOAD_TASK_FINISHED:
        TaskMessage.objects.filter(pk=task_message.pk).update(download_tasks_done=F('download_tasks_done') + 1)
    elif event is TaskProgressEvent.TRANSFORM_TASK_FINISHED:
        TaskMessage.objects.filter(pk=task_message.pk).update(transform_tasks_done=F('transform_tasks_done') + 1)
    elif event is TaskProgressEvent.CONCATENATE_TASK_FINISHED:
        TaskMessage.objects.filter(pk=task_message.pk).update(concatenate_tasks_done=F('concatenate_tasks_done') + 1)
    elif event is None:
        pass
    else:
        raise ValueError(f"Unknown event: TaskProgressEvent = {event}")

    task_message.refresh_from_db()
    msg_text = '\n'.join((
        "*Processing videos*",
        "",
        f"Downloaded: {task_message.download_tasks_done}/{task_message.download_tasks_total}",
        f"Transformed: {task_message.transform_tasks_done}/{task_message.transform_tasks_total}",
        f"Concatenated: {task_message.concatenate_tasks_done}/{task_message.concatenate_tasks_total}",
    ))
    try:
        bot.edit_message_text(
            chat_id=task_message.chat.id,
            message_id=task_message.status_message_id,
            text=msg_text
        )
    except ApiTelegramException as exc:
        if exc.error_code != 400:
            raise
