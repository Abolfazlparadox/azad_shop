# Generated by Django 5.1.7 on 2025-04-28 06:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0003_tag'),
    ]

    operations = [
        migrations.CreateModel(
            name='SiteOption',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True, verbose_name='گزینه سایت')),
                ('slug', models.SlugField(allow_unicode=True, max_length=100, unique=True, verbose_name='شناسه URL')),
            ],
            options={
                'verbose_name': 'گزینه سایت',
                'verbose_name_plural': 'گزینه\u200cهای سایت',
                'ordering': ['name'],
            },
        ),
        migrations.AlterModelOptions(
            name='sitesetting',
            options={'verbose_name': 'تنظیمات سایت', 'verbose_name_plural': 'تنظیمات سایت'},
        ),
        migrations.AddField(
            model_name='sitesetting',
            name='secondary_logo',
            field=models.ImageField(blank=True, help_text='لوگوی کوچک\u200cشده یا موبایل', null=True, upload_to='images/site.setting/', verbose_name='لوگو دوم سایت'),
        ),
        migrations.AddField(
            model_name='sitesetting',
            name='slogan',
            field=models.CharField(blank=True, help_text='متن شعار نمایش داده\u200cشده در هدر یا فوتر', max_length=255, verbose_name='شعار سایت'),
        ),
        migrations.AlterField(
            model_name='sitesetting',
            name='address',
            field=models.CharField(max_length=200, verbose_name='آدرس '),
        ),
        migrations.AlterField(
            model_name='sitesetting',
            name='copy_right',
            field=models.TextField(verbose_name='متن کپی رایت  سایت'),
        ),
        migrations.AlterField(
            model_name='sitesetting',
            name='email',
            field=models.CharField(blank=True, max_length=200, null=True, verbose_name='ایمیل '),
        ),
        migrations.AlterField(
            model_name='sitesetting',
            name='fax',
            field=models.CharField(blank=True, max_length=200, null=True, verbose_name='فکس '),
        ),
        migrations.AlterField(
            model_name='sitesetting',
            name='phone',
            field=models.CharField(blank=True, max_length=200, null=True, verbose_name='تلفن '),
        ),
        migrations.AlterField(
            model_name='sitesetting',
            name='site_logo',
            field=models.ImageField(upload_to='images/site.setting/', verbose_name='لوگو اصلی سایت'),
        ),
        migrations.AddField(
            model_name='sitesetting',
            name='options',
            field=models.ManyToManyField(blank=True, help_text='گزینه\u200cها/ویژگی\u200cهای فعال\u200cشده در سایت', to='home.siteoption', verbose_name='گزینه\u200cهای سایت'),
        ),
    ]
