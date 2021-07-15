from django.urls import reverse
from rest_framework.test import APITestCase


class UserViewSetTest(APITestCase):
    base_url = reverse("api:edit-list")

    def test_edit(self):
        pass
