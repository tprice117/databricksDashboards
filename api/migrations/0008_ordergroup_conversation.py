# Generated by Django 4.1 on 2024-06-10 23:02

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("chat", "0001_initial"),
        ("api", "0007_alter_order_status_ordergroupsellerdecline"),
    ]

    operations = [
        migrations.AddField(
            model_name="ordergroup",
            name="conversation",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="chat.conversation",
            ),
        ),
    ]
