
# Django API Server

Simple starter built with Python / Django Rest / Sqlite3 and JWT Auth. The authentication flow is built with [json web tokens](https://jwt.io).

<br />

> Features:

- [API Definition](https://docs.appseed.us/boilerplate-code/api-unified-definition) - the unified API structure implemented by this server
- Simple, intuitive codebase - can be extended with ease 
- Django / DRF / SQLite3 - a simple, easy to use backend
- Authentication with JWT (login, logout, register)
- Docker, Unitary tests

<br />

> **[PRO Version](https://github.com/app-generator/api-server-django-pro)** available: MongoDB persistance, Docker, Unitary Tests, 24/7 LIVE Support via [Discord](https://discord.gg/fZC6hup)

> Can be used with other [React Starters](https://appseed.us/apps/react) for a complete **Full-Stack** experience:

| [React Node JS Berry](https://appseed.us/product/react-node-js-berry-dashboard) | [Full-Stack Material PRO](https://appseed.us/full-stack/react-material-dashboard) | [React Node Datta Able](https://github.com/app-generator/react-datta-able) |
| --- | --- | --- |
| [![React Node JS Berry](https://user-images.githubusercontent.com/51070104/124934742-aa392300-e00d-11eb-83bf-28d8b8704ec8.png)](https://appseed.us/product/react-node-js-berry-dashboard) | [![Full-Stack Material PRO](https://user-images.githubusercontent.com/51070104/128878037-50da7a12-787d-455d-933a-30b2957e2896.png)](https://appseed.us/full-stack/react-material-dashboard) | [![React Node Datta Able](https://user-images.githubusercontent.com/51070104/125737710-834a9e6f-c39b-4f3b-a42a-9583ce2ce1da.png)](https://github.com/app-generator/react-datta-able)

<br />

![Django API Server - Open-source Django Starter provided by AppSeed.](https://user-images.githubusercontent.com/51070104/126252341-6961a681-767b-4aca-a95f-140da5af5f81.png) 

<br />

## Requirements

- Django==3.2.5
- djangorestframework==3.12.4
- PyJWT==2.1.0
- django-cors-headers==3.7.0 

<br />

## How to use the code

**Step #1** -  Clone the sources

```bash
$ git clone https://github.com/app-generator/api-server-django.git
$ cd api-server-django
```

**Step #2** - Create a virtual environment

```bash
$ # Virtualenv modules installation (Unix based systems)
$ virtualenv env
$ source env/bin/activate
$
$ # Virtualenv modules installation (Windows based systems)
$ # virtualenv env
$ # .\env\Scripts\activate
```

**Step #3** - Install dependencies using PIP

```bash
$ pip install -r requirements.txt
```

**Step #4** - Start the API server

```bash
$ python manage.py migrate
$ python manage.py runserver
```

The API server will start using the default port `8000`.

<br />

### [Docker](https://www.docker.com/) execution
---

> Get the code

```bash
$ git clone https://github.com/app-generator/api-server-django.git
$ cd api-server-django
```

> Start the app in Docker

```bash
$ docker-compose up --build -d
```

Visit `http://localhost:5000` in your browser. The API server will be running.

<br />

## Tests

```bash 
$ python manage.py test
```

<br />

## API

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
**Django API Server** - provided by AppSeed [App Generator](https://appseed.us)
