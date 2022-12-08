import requests
import jwt
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from api.authentication.serializers.login import _generate_jwt_token
from api.user.models import User
from api.authentication.models import ActiveSession

from rest_framework.views import APIView

class GithubSocialLogin(APIView):
    permission_classes = (AllowAny,)

    def get(self, request):    
        code = self.request.GET.get('code')
        client_id = getattr(settings, 'GITHUB_CLIENT_ID')
        client_secret = getattr(settings, 'GITHUB_SECRET_KEY')
        root_url = 'https://github.com/login/oauth/access_token'

        params = { 'client_id': client_id, 'client_secret': client_secret, 'code': code }

        data = requests.post(root_url, params=params, headers={
          'Content-Type': 'application/x-www-form-urlencoded',
        })

        response = data._content.decode('utf-8')
        access_token = response.split('&')[0].split('=')[1]

        user_data = requests.get('https://api.github.com/user', headers={
            "Authorization": "Bearer " + access_token
        }).json()
        
        if User.objects.filter(username=user_data['login']).exists():
            user = User.objects.get(username=user_data['login'])
        else:
            try:
                user = User.objects.create(username=user_data['login'], email=user_data['email'])
            except:
                user = User.objects.create(username=user_data['login'])
        
        try:
            session = ActiveSession.objects.get(user=user)
            if not session.token:
                raise ValueError

            jwt.decode(session.token, settings.SECRET_KEY, algorithms=["HS256"])

        except (ObjectDoesNotExist, ValueError, jwt.ExpiredSignatureError):
            session = ActiveSession.objects.create(
                user=user, token=_generate_jwt_token(user)
            )
             
        return Response({
            "success": True,
            "user": {"_id": user.pk, "username": user.username, "email": user.email, "token": session.token},
        })