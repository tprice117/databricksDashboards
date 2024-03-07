# Generated by Django 4.1 on 2024-03-07 13:29

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("payment_methods", "0002_paymentmethoduseraddress_paymentmethoduser"),
    ]

    operations = [
        migrations.AlterField(
            model_name="paymentmethoduser",
            name="payment_method",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="payment_method_users",
                to="payment_methods.paymentmethod",
            ),
        ),
        migrations.AlterField(
            model_name="paymentmethoduseraddress",
            name="payment_method",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="payment_method_user_addresses",
                to="payment_methods.paymentmethod",
            ),
        ),
    ]
