# Generated by Django 5.1.7 on 2025-05-20 10:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cart', '0007_order_orderitem'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cart',
            name='is_paid',
            field=models.BooleanField(blank=True, default=False, null=True, verbose_name='نهایی شده / نشده'),
        ),
    ]
