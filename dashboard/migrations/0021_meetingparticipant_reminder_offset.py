# Generated by Django 5.2 on 2025-04-23 12:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0020_meeting_meetingparticipant_meeting_participants'),
    ]

    operations = [
        migrations.AddField(
            model_name='meetingparticipant',
            name='reminder_offset',
            field=models.PositiveIntegerField(blank=True, help_text='Minutes before meeting start to remind you', null=True),
        ),
    ]
