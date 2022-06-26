from __future__ import annotations

from django.db import models
from telebot.types import Message


class Chat(models.Model):
    id = models.BigIntegerField(primary_key=True)
    username = models.TextField(null=True)
    first_name = models.TextField(null=True)
    last_name = models.TextField(null=True)
    last_seen_date = models.DateTimeField(auto_now=True)

    @classmethod
    def update_from_message(cls, message: Message) -> Chat:
        chat, _ = cls.objects.get_or_create(id=message.chat.id)
        chat.username = message.chat.username or None
        chat.first_name = message.chat.first_name or None
        chat.last_name = message.chat.last_name or None
        chat.save()
        return chat

    def __str__(self) -> str:
        return f"@{self.username} ({self.first_name} {self.last_name})"


class TaskMessage(models.Model):
    id = models.UUIDField(primary_key=True)
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE)
    message_id = models.BigIntegerField()
    status_message_id = models.BigIntegerField()
    result_message_id = models.BigIntegerField(null=True)

    download_tasks_total = models.IntegerField(default=0)
    download_tasks_done = models.IntegerField(default=0)
    transform_tasks_total = models.IntegerField(default=0)
    transform_tasks_done = models.IntegerField(default=0)
    concatenate_tasks_total = models.IntegerField(default=0)
    concatenate_tasks_done = models.IntegerField(default=0)
    encode_tasks_total = models.IntegerField(default=0)
    encode_tasks_done = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
