# Generated by Django 5.1.7 on 2025-05-09 12:32

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0020_rename_productattribute_productattributetype'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='productattributetype',
            name='attributes',
        ),
        migrations.AlterModelOptions(
            name='productattributetype',
            options={'ordering': ['name'], 'verbose_name': 'نوع ویژگی', 'verbose_name_plural': 'انواع ویژگی\u200cها'},
        ),
        migrations.AlterField(
            model_name='productattributetype',
            name='name',
            field=models.CharField(max_length=100, verbose_name='نوع ویژگی'),
        ),
        migrations.CreateModel(
            name='ProductAttribute',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.CharField(max_length=100, verbose_name='مقدار ویژگی')),
                ('type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='product.productattributetype', verbose_name='نوع ویژگی')),
            ],
            options={
                'verbose_name': 'مقدار ویژگی',
                'verbose_name_plural': 'مقادیر ویژگی\u200cها',
                'ordering': ['type', 'value'],
            },
        ),
        migrations.DeleteModel(
            name='ProductType',
        ),
    ]
