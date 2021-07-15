from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status


class FilmViewsTest(APITestCase):
    base_url = reverse("api:register-list")

    data = {
        "username": "coucou",
        "password": "12345678",
        "email": "teast@admin.com"
    }

    def setUp(self) -> None:
        pass

    def test_list(self):
        response = self.client.post(f"{self.base_url}", data=self.data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
