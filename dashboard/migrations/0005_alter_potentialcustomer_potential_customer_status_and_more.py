# Generated by Django 5.2 on 2025-04-17 12:30

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0004_potentialcustomer_potential_customer_is_dead'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='potentialcustomer',
            name='potential_customer_status',
            field=models.CharField(choices=[('not_contacted', 'Not Contacted'), ('emailed', 'Emailed'), ('contacted', 'Contacted'), ('in_progress', 'In Progress')], default='not_contacted', max_length=20),
        ),
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('message', models.CharField(max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('is_read', models.BooleanField(default=False)),
                ('recipient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'dashboard_notification',
            },
        ),
    ]
