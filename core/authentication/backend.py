import jwt

from django.conf import settings

from django.core.exceptions import ObjectDoesNotExist

from rest_framework import authentication, exceptions

from core.user.models import User


class JWTAuthentication(authentication.BaseAuthentication):
    authentication_header_prefix = 'Bearer'

    def authenticate(self, request):

        pass

    def _authenticate_credentials(self, request, token):

        pass
