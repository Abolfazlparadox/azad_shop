# Generated by Django 5.1.7 on 2025-05-06 08:25

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0011_alter_productcategory_parent'),
    ]

    operations = [
        migrations.AlterField(
            model_name='productcategory',
            name='parent',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='children', to='product.productcategory', verbose_name='دسته\u200cبندی والد'),
        ),
    ]
