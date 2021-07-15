from api.user.models import User

user_data = {
    "username": "test",
    "password": "pass",
    "email": "test@appseed.us"
}

User.objects.create_user(**user_data)
