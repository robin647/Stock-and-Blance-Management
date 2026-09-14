#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from apps.showrooms.serializers import ShowroomSerializer

# Test with a different username
data = {
    'name': 'Mahadi Zone-2',
    'address': 'Mirpur-2',
    'username': 'zone2_user',  # Changed from 'robin' to 'zone2_user'
    'password': '12345678'
}

serializer = ShowroomSerializer(data=data)

if serializer.is_valid():
    print("✓ Validation passed!")
    showroom = serializer.save()
    print(f"✓ Showroom created successfully!")
    print(f"  - ID: {showroom.id}")
    print(f"  - Name: {showroom.name}")
    print(f"  - Address: {showroom.address}")
    print(f"  - Login Username: {showroom.login_user.username}")
    print(f"\nShowroom staff can now log in with:")
    print(f"  Username: zone2_user")
    print(f"  Password: 12345678")
else:
    print("✗ Validation failed!")
    print("Errors:")
    for field, errors in serializer.errors.items():
        for error in errors:
            print(f"  - {field}: {error}")
