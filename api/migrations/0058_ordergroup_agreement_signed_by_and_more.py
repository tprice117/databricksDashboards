# Generated by Django 4.1 on 2024-10-21 15:44

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0057_ordergroup_agreement"),
    ]

    operations = [
        migrations.AddField(
            model_name="ordergroup",
            name="agreement_signed_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="signed_agreements",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="ordergroup",
            name="agreement_signed_on",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
