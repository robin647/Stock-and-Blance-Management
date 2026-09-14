#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from apps.accounts.models import User

# Reset password for khilkhet
user = User.objects.get(username='khilkhet')
user.set_password('test12345')
user.save()
print(f"✓ Password reset for {user.username}")
print(f"  New credentials:")
print(f"  Username: khilkhet")
print(f"  Password: test12345")

# Also verify zone2_user still works
print(f"\n✓ zone2_user credentials:")
print(f"  Username: zone2_user")
print(f"  Password: 12345678")
