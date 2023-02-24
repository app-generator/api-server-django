
# [Django API Server](https://github.com/app-generator/api-server-django)

Simple starter built with Python / Django Rest / Sqlite3 and JWT Auth. The authentication flow is built with [json web tokens](https://jwt.io).

<br />

## 🚀 `PROMO` [Spring Boost Campaign](https://appseed.us/discounts/) `50%OFF`

> The **discount is applicable to all products and licenses** (no stock limits) until `15.MAR`

[![Spring Boost Campaign](https://user-images.githubusercontent.com/51070104/221118889-171c5afc-4d01-402b-8681-61b37338e26c.png)](https://appseed.us/discounts/)

<br />

> Features:

- ✅ `Up-to-date dependencies` 
- ✅ [API Definition](https://docs.appseed.us/boilerplate-code/api-unified-definition) - the unified API structure implemented by this server
- ✅ Django / DRF / SQLite3 - a simple, easy to use backend
- ✅ `JWT Authentication` (login, logout, register)
- 🆕 `OAuth` for **Github**
  - Full-stack ready with [React Soft Dashboard](https://github.com/app-generator/react-soft-ui-dashboard)
- ✅ Docker, Unitary tests
- 🚀 `Instant Deploy` on RENDER using [Python Deployer](https://github.com/app-generator/deploy-automation-render)
  - `python.exe deployer.py django <THIS_REPO>`
  
<br />

> Can be used with other [React Starters](https://appseed.us/apps/react) for a complete **Full-Stack** experience:

| [React Node JS Berry](https://appseed.us/product/berry-dashboard/api-server-nodejs/react/) | [React Node Soft Dashboard](https://appseed.us/product/soft-ui-dashboard/api-server-nodejs/react/) | [React Node Horizon](https://appseed.us/product/horizon-ui/api-server-nodejs/) |
| --- | --- | --- |
| [![React Node JS Berry](https://user-images.githubusercontent.com/51070104/176936514-f1bccb21-bafe-4b43-9e4c-b6fe0ec9511d.png)](https://appseed.us/product/berry-dashboard/api-server-nodejs/react/) | [![React Node Soft Dashboard](https://user-images.githubusercontent.com/51070104/176936814-74386559-4e05-43d5-b9a4-8f70ce96a610.png)](https://appseed.us/product/soft-ui-dashboard/api-server-nodejs/react/) | [![React Node Horizon](https://user-images.githubusercontent.com/51070104/174428337-181e6dea-0ad9-4fe1-a35f-25e5fa656a9d.png)](https://appseed.us/product/horizon-ui/api-server-nodejs/)

<br />

![Nodejs API Server - Open-source Nodejs Starter provided by AppSeed.](https://user-images.githubusercontent.com/51070104/124414813-142aa180-dd5c-11eb-9279-6b082dadc51a.png)

<br />

## ✨ Quick Start in `Docker`

> 👉 Get the code

```bash
$ git clone https://github.com/app-generator/api-server-django.git
$ cd api-server-django
```

> 👉 Start the app in Docker

```bash
$ docker-compose up --build  
```

The API server will start using the PORT `5000`.

<br />

## ✨ How to use the code

> 👉 **Step #1** -  Clone the sources

```bash
$ git clone https://github.com/app-generator/api-server-django.git
$ cd api-server-django
```
<br />

> 👉 **Step #2** - Create a virtual environment

```bash
$ # Virtualenv modules installation (Unix based systems)
$ virtualenv env
$ source env/bin/activate
$
$ # Virtualenv modules installation (Windows based systems)
$ # virtualenv env
$ # .\env\Scripts\activate
```

<br />

> 👉 **Step #3** - Install dependencies using PIP

```bash
$ pip install -r requirements.txt
```

<br />

> 👉 **Step #4** - Create a new `.env` file using sample `env.sample`

The meaning of each variable can be found below: 

- `DEBUG`: if `True` the app runs in develoment mode
  - For production value `False` should be used
- `SECRET_KEY`: used in assets management
- `GITHUB_CLIENT_ID`: For GitHub social login
- `GITHUB_SECRET_KEY`: For GitHub social login

<br />

> 👉 **Step #5** - Start the API server

```bash
$ python manage.py migrate
$ python manage.py runserver
```

The API server will start using the default port `8000`.

<br />

## ✨ Tests

```bash 
$ python manage.py test
```

<br />

## ✨ API

For a fast set up, use this POSTMAN file: [api_sample](https://github.com/app-generator/api-server-Django/blob/master/media/api.postman_collection.json)

> **Register** - `api/users/signup`

```
POST api/users/signup
Content-Type: application/json

{
    "username":"test",
    "password":"pass", 
    "email":"test@appseed.us"
}
```

<br />

> **Login** - `api/users/login`

```
POST /api/users/login
Content-Type: application/json

{
    "password":"pass", 
    "email":"test@appseed.us"
}
```

<br />

> **Logout** - `api/users/logout`

```
POST api/users/logout
Content-Type: application/json
authorization: JWT_TOKEN (returned by Login request)

{
    "token":"JWT_TOKEN"
}
```

<br />

---
**[Django API Server](https://github.com/app-generator/api-server-django)** - provided by [AppSeed](https://appseed.us)
