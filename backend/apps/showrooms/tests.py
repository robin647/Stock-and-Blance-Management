from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User


class ShowroomManagementTests(TestCase):
    def test_admin_can_create_a_showroom_with_its_login_and_list_all_showrooms(self):
        admin = User.objects.create_user(username="admin", password="password", role="admin")
        client = APIClient()
        client.force_authenticate(user=admin)

        response = client.post("/api/showrooms/", {
            "name": "Zone-1", "address": "Dhaka", "phone": "01700000000",
            "username": "zone-1-login", "password": "password",
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(response.data["has_login"])
        self.assertEqual(response.data["login_username"], "zone-1-login")

        listing = client.get("/api/showrooms/")
        self.assertEqual(listing.status_code, 200)
        self.assertIsInstance(listing.data, list)
        self.assertEqual(len(listing.data), 1)
