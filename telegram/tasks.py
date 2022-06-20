from datetime import datetime
from typing import Literal, Optional

import telebot
from celery import shared_task
from django.conf import settings
from django.db import transaction

from moviemaker.models import VideoFile
from telegram.models import Chat, TaskMessage

bot = telebot.TeleBot(
    token=settings.TELEGRAM_BOT_TOKEN,
    parse_mode='Markdown',
    threaded=False,
)


@shared_task(ack_late=True, ignore_result=True)
def reply_with_video(video: VideoFile, chat: Chat, message_id: int) -> None:
    with video.file.open(mode='rb') as file:
        bot.send_video(
            chat_id=chat.id,
            reply_to_message_id=message_id,
            video=file,
            supports_streaming=True,
            duration=video.duration,
            width=video.width,
            height=video.height,
        )


@shared_task(ack_late=True, ignore_result=True)
def reply_with_error_msg(request, exc, traceback, chat: Chat, message_id: int) -> None:
    _ = request
    _ = traceback
    bot.send_message(
        chat_id=chat.id,
        reply_to_message_id=message_id,
        text=f"❗ {type(exc).__name__}: {str(exc)}"
    )


@shared_task(ack_late=True, ignore_result=True)
def update_task_progress(
        chat: Chat,
        message_id: int,
        event: Optional[Literal['download', 'transform', 'concatenate', 'finished']],
) -> None:
    with transaction.atomic():
        task_message: TaskMessage = (
            TaskMessage.objects
            .select_for_update()
            .filter(chat=chat, message_id=message_id)
            .select_related()
            [0]
        )

        if event == 'finished':
            elapsed_time_total_s = int((datetime.utcnow() - task_message.created_at).total_seconds())
            elapsed_time_m = elapsed_time_total_s // 60
            elapsed_time_s = elapsed_time_total_s - elapsed_time_m * 60
            if elapsed_time_m:
                elapsed_time_verb = f"{elapsed_time_m}m{elapsed_time_s}s"
            else:
                elapsed_time_verb = f"{elapsed_time_s}s"
            msg_text = '\n'.join((
                f"*Finished* in {elapsed_time_verb}",
                "",
                f"Downloaded: {task_message.download_tasks_done}/{task_message.download_tasks_total}",
                f"Transformed: {task_message.transform_tasks_done}/{task_message.transform_tasks_total}",
                f"Concatenated: {task_message.concatenate_tasks_done}/{task_message.concatenate_tasks_total}",
            ))
        else:
            if event == 'download':
                task_message.download_tasks_done += 1
                task_message.save(update_fields=('download_tasks_done',))
            elif event == 'transform':
                task_message.transform_tasks_done += 1
                task_message.save(update_fields=('transform_tasks_done',))
            elif event == 'concatenate':
                task_message.concatenate_tasks_done += 1
                task_message.save(update_fields=('concatenate_tasks_done',))
            msg_text = '\n'.join((
                "*Processing videos*",
                "",
                f"Downloaded: {task_message.download_tasks_done}/{task_message.download_tasks_total}",
                f"Transformed: {task_message.transform_tasks_done}/{task_message.transform_tasks_total}",
                f"Concatenated: {task_message.concatenate_tasks_done}/{task_message.concatenate_tasks_total}",
            ))

        if task_message.reply_message_id is None:
            message = bot.send_message(
                chat_id=task_message.chat.id,
                reply_to_message_id=task_message.message_id,
                text=msg_text,
            )
            task_message.reply_message_id = message.message_id
            task_message.save(update_fields=('reply_message_id',))
        else:
            bot.edit_message_text(
                chat_id=task_message.chat.id,
                message_id=task_message.reply_message_id,
                text=msg_text
            )
