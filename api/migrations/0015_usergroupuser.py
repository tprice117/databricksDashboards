# Generated by Django 4.1.1 on 2023-04-24 13:52

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0014_usergroup_user_user_group'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserGroupUser',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('updated_on', models.DateTimeField(auto_now=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.user')),
                ('user_group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.usergroup')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
