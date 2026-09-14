from django.db import migrations


def migrate_credentials_forward(apps, schema_editor):
    """
    For every existing Showroom that has a username/password set (from the
    old, broken direct-login design), create the equivalent User account
    (role=showroom_user) so nobody's login stops working. Django's password
    hash format is identical between the two models (both use
    django.contrib.auth.hashers), so the hash is copied across as-is —
    no plaintext passwords are ever read or re-hashed here.
    """
    Showroom = apps.get_model("showrooms", "Showroom")
    User = apps.get_model("accounts", "User")

    for showroom in Showroom.objects.exclude(username=""):
        if User.objects.filter(username=showroom.username).exists():
            # Username collision with an existing account — skip rather than
            # silently overwrite; admin can set up the login manually.
            continue
        User.objects.create(
            username=showroom.username,
            password=showroom.password,
            role="showroom_user",
            showroom=showroom,
            is_active=showroom.is_active,
        )


def migrate_credentials_backward(apps, schema_editor):
    # Nothing to reverse into — the fields are being removed anyway.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("showrooms", "0002_showroom_password_showroom_username"),
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(migrate_credentials_forward, migrate_credentials_backward),
    ]
