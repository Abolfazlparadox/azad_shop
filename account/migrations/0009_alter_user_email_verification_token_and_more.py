# Generated by Django 5.1.7 on 2025-04-30 08:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0008_alter_membership_role_alter_membership_university'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='email_verification_token',
            field=models.CharField(blank=True, editable=False, max_length=64, verbose_name='توکن تأیید ایمیل'),
        ),
        migrations.AlterField(
            model_name='user',
            name='email_verified',
            field=models.BooleanField(default=False, verbose_name='ایمیل تأیید شده'),
        ),
    ]
