import jwt

from rest_framework import authentication, exceptions
from django.conf import settings

from api.user.models import User
from api.authentication.models import ActiveSession


class ActiveSessionAuthentication(authentication.BaseAuthentication):
    authentication_header_prefix = "Bearer"

    auth_error_message = {
        "success": False,
        "msg": "User is not logged on."
    }

    def authenticate(self, request):

        request.user = None

        auth_header = authentication.get_authorization_header(request).split()
        auth_header_prefix = self.authentication_header_prefix.lower()

        if not auth_header:
            return None

        if len(auth_header) == 1:
            return None

        elif len(auth_header) > 2:
            return None

        prefix = auth_header[0].decode('utf-8')
        token = auth_header[1].decode('utf-8')

        if prefix.lower() != auth_header_prefix:
            return None

        return self._authenticate_credentials(token)

    def _authenticate_credentials(self, token):

        try:
            jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        except:
            raise exceptions.AuthenticationFailed(self.auth_error_message)

        try:
            active_session = ActiveSession.objects.get(token=token)
        except:
            raise exceptions.AuthenticationFailed(self.auth_error_message)

        try:
            user = active_session.user
        except User.DoesNotExist:
            msg = 'No user matching this token was found.'
            raise exceptions.AuthenticationFailed(msg)

        if not user.is_active:
            msg = 'This user has been deactivated.'
            raise exceptions.AuthenticationFailed(msg)

        return (user, token)
