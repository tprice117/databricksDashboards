# Generated by Django 4.2.3 on 2023-07-26 14:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0049_alter_subscription_order_group'),
    ]

    operations = [
        migrations.AddField(
            model_name='subscription',
            name='length',
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
    ]
