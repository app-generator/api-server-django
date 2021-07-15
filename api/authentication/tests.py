from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from api.fixtures import run_fixtures


class AuthenticationTest(APITestCase):
    base_url_register = reverse("api:register-list")
    base_url_login = reverse("api:login-list")

    data_register = {
        "username": "test",
        "password": "pass",
        "email": "test@appseed.us"
    }

    data_login = {
        "password": "12345678",
        "email": "teast@admin.com"
    }

    def test_register(self):
        response = self.client.post(f"{self.base_url_register}", data=self.data_register)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response_data = response.json()
        self.assertEqual(response_data['success'], True)

    def test_login(self):
        # Running fixtures #
        run_fixtures()

        response = self.client.post(f"{self.base_url_login}", data=self.data_login)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(response_data['success'], True)

    def test_logout(self):
        pass

    def test_check_session(self):
        pass
