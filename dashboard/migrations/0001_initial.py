# Generated by Django 5.2 on 2025-04-17 09:51

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Customer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('customer_name', models.CharField(max_length=100)),
                ('customer_surname', models.CharField(max_length=100)),
                ('customer_email', models.CharField(max_length=100)),
                ('customer_phone', models.CharField(max_length=20)),
                ('customer_company', models.CharField(max_length=100)),
                ('customer_address', models.CharField(max_length=255)),
                ('customer_joined_at', models.DateField(auto_now_add=True)),
                ('customer_status', models.CharField(max_length=20)),
            ],
            options={
                'db_table': 'dashboard_customer',
            },
        ),
        migrations.CreateModel(
            name='PotentialCustomer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('potential_customer_name', models.CharField(max_length=100)),
                ('potential_customer_email', models.CharField(max_length=100)),
                ('potential_customer_phone', models.CharField(max_length=20)),
                ('potential_customer_source', models.CharField(max_length=100)),
                ('potential_customer_submitted_at', models.DateField(auto_now_add=True)),
                ('potential_customer_converted', models.BooleanField(default=False)),
                ('potential_customer_converted_at', models.DateField(blank=True, null=True)),
                ('converted_customer_id', models.IntegerField(blank=True, null=True)),
            ],
            options={
                'db_table': 'dashboard_potential_customer',
            },
        ),
        migrations.CreateModel(
            name='Ticket',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ticket_id', models.CharField(max_length=20, unique=True)),
                ('subject', models.CharField(max_length=255)),
                ('source_type', models.CharField(max_length=100)),
                ('priority', models.CharField(max_length=20)),
                ('status', models.CharField(max_length=20)),
                ('resolution_reason', models.CharField(blank=True, max_length=255, null=True)),
                ('assignee', models.CharField(blank=True, max_length=100, null=True)),
                ('customer_name', models.CharField(max_length=255)),
                ('customer_id', models.CharField(max_length=20)),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('updated_date', models.DateTimeField(auto_now=True)),
                ('resolved_date', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'db_table': 'dashboard_ticket',
            },
        ),
    ]
