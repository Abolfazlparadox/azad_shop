# Generated by Django 5.1.7 on 2025-05-09 17:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0006_alter_siteoption_logo'),
        ('product', '0025_remove_productattribute_quantity_and_more'),
        ('university', '0002_university_city_university_province_and_more'),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name='product',
            name='product_pro_price_e0e858_idx',
        ),
        migrations.RemoveIndex(
            model_name='product',
            name='product_pro_stock_11f466_idx',
        ),
        migrations.RemoveField(
            model_name='product',
            name='old_price',
        ),
        migrations.RemoveField(
            model_name='product',
            name='price',
        ),
        migrations.RemoveField(
            model_name='product',
            name='stock',
        ),
        migrations.AlterField(
            model_name='productvariant',
            name='price_override',
            field=models.IntegerField(blank=True, null=True, verbose_name='قیمت مخصوص این تنوع'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['is_active'], name='product_pro_is_acti_9d034c_idx'),
        ),
    ]
