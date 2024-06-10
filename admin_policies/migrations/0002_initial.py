# Generated by Django 4.1 on 2024-04-27 21:34

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("admin_policies", "0001_initial"),
        ("api", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="usergrouppolicypurchaseapproval",
            name="user_group",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="policy_purchase_approvals",
                to="api.usergroup",
            ),
        ),
        migrations.AddField(
            model_name="usergrouppolicymonthlylimit",
            name="user_group",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="policy_monthly_limit",
                to="api.usergroup",
            ),
        ),
        migrations.AddField(
            model_name="usergrouppolicyinvitationapproval",
            name="user_group",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="policy_invitation_approvals",
                to="api.usergroup",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="usergrouppolicypurchaseapproval",
            unique_together={("user_group", "user_type")},
        ),
        migrations.AlterUniqueTogether(
            name="usergrouppolicyinvitationapproval",
            unique_together={("user_group", "user_type")},
        ),
    ]
