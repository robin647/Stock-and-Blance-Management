from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("showrooms", "0003_migrate_credentials_to_user"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="showroom",
            name="username",
        ),
        migrations.RemoveField(
            model_name="showroom",
            name="password",
        ),
    ]
