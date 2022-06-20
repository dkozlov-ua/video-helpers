from django.db import models


class VideoFile(models.Model):
    id = models.SlugField(primary_key=True)
    duration = models.IntegerField()
    width = models.IntegerField()
    height = models.IntegerField()
    file = models.FileField()
    last_used_at = models.DateTimeField(auto_now=True)
