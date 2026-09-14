#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from django.contrib.auth import authenticate
from apps.accounts.models import User

# Test authentication
user = authenticate(username='zone2_user', password='12345678')
print(f'Authenticate result: {user}')

# Check if user exists and password check works
u = User.objects.get(username='zone2_user')
print(f'User found: {u.username}, role: {u.role}, active: {u.is_active}')
print(f'Password check (12345678): {u.check_password("12345678")}')
print(f'Password check (wrong): {u.check_password("wrongpass")}')

# Also check other users
print('\n=== All Users Password Status ===')
for user in User.objects.filter(role='showroom_user'):
    print(f'{user.username}: password set = {bool(user.password)}, is_active = {user.is_active}')
