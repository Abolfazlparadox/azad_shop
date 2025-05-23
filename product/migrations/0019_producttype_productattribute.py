# Generated by Django 5.1.7 on 2025-05-09 12:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0018_alter_productvariant_unique_together_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProductType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='نوع ویژگی')),
            ],
        ),
        migrations.CreateModel(
            name='ProductAttribute',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='مقدار ویژگی')),
                ('attributes', models.ManyToManyField(to='product.producttype', verbose_name='ویژگی\u200cها ')),
            ],
        ),
    ]
