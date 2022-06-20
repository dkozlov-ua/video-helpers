from django.contrib import admin

from telegram import models


@admin.register(models.Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = ['id', 'username', 'first_name', 'last_name', 'last_seen_date']
    fields = ['id', 'username', ('first_name', 'last_name'), 'last_seen_date']
    sortable_by = ['id', 'username', 'last_seen_date']
    readonly_fields = ['last_seen_date']
    view_on_site = False
