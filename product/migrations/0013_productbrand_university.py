# Generated by Django 5.1.7 on 2025-05-06 09:19

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0012_alter_productcategory_parent'),
        ('university', '0002_university_city_university_province_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='productbrand',
            name='university',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='university.university'),
        ),
    ]
