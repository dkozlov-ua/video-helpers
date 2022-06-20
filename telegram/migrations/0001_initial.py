# Generated by Django 4.0.5 on 2022-06-20 15:52

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Chat',
            fields=[
                ('id', models.BigIntegerField(primary_key=True, serialize=False)),
                ('username', models.TextField(null=True)),
                ('first_name', models.TextField(null=True)),
                ('last_name', models.TextField(null=True)),
                ('last_seen_date', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='TaskMessage',
            fields=[
                ('id', models.UUIDField(primary_key=True, serialize=False)),
                ('message_id', models.BigIntegerField()),
                ('status_message_id', models.BigIntegerField()),
                ('result_message_id', models.BigIntegerField(null=True)),
                ('download_tasks_total', models.IntegerField(default=0)),
                ('download_tasks_done', models.IntegerField(default=0)),
                ('transform_tasks_total', models.IntegerField(default=0)),
                ('transform_tasks_done', models.IntegerField(default=0)),
                ('concatenate_tasks_total', models.IntegerField(default=0)),
                ('concatenate_tasks_done', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('chat', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='telegram.chat')),
            ],
        ),
    ]
