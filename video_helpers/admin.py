from django.contrib import admin

from video_helpers import models


@admin.register(models.VideoFile)
class VideoFileAdmin(admin.ModelAdmin):
    list_display = ['id', 'duration', 'width', 'height', 'last_used_at']
    fields = ['id', ('duration', 'width', 'height'), 'file']
    sortable_by = ['id', 'duration', 'last_used_at']
    readonly_fields = ['last_used_at']
    view_on_site = False
