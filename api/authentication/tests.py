from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status


class AuthenticationTest(APITestCase):
    base_url = reverse("api:register-list")

    data = {
        "username": "test",
        "password": "pass",
        "email": "test@appseed.us"
    }

    def test_register(self):
        response = self.client.post(f"{self.base_url}", data=self.data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_login(self):
        pass

    def test_logout(self):
        pass

    def test_check_session(self):
        pass