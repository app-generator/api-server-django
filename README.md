# Django API Server

Open-Source API server powered by [Django](https://app-generator.dev/docs/technologies/django/index.html), a progressive Node.js framework for building efficient, reliable, and scalable server-side applications.

> Status: **Work in progress**

- 👉 [Django API Server](#) - **Complete Documentation**
- 👉 [Get Support](https://app-generator.dev/ticket/create/) via Email and Discord

<br />

## Features  

- **Best Practices**: Follows industry-standard best practices for building robust APIs.
- **Backend**: Built with Django, a powerful and scalable Node.js framework.
- **UI**: 
  - React Mantis (optional frontend integration).

<br />

## Backend API

- **Simple, modular & intuitive structure**: Easy to understand and extend.
- **Toolchain**:
  - Usable with the latest Node.js LTS versions:
    - v22.x
    - v21.x
    - v20.x
  - Package Managers: 
    - PNPM, 
    - Yarn, 
    - Npm  
- **Authentication**: Auth0 for GitHub integration.
  - GitHub email pulled during OAuth SignIN.
  - Optional: Email validation.
- **Roles**: Admin, Users.
- **ORM**: Prisma for database management.
- **User Profiles**:
  - ROLE: Default user.
  - Fields: Name, surname, bio, country, address, job.
- **API Features**:
  - Search, Pagination.
  - Public Access: GET by ID, get all.
  - Private access (requires token):
    - Create, Update, Delete.
- **Admin**:
  - Can search or mutate any user.
- **Users**:
  - Can view and mutate only their own information.

## Start with Docker

@Todo

## Start Django Backend

> Edit Environment

Add a `.env` file to your project root directory and populate as follows:

```env
AUTH0_DOMAIN=YOUR_AUTH0_DOMAIN
AUTH0_CLIENT_ID=YOUR_AUTH0_CLIENT_ID
AUTH0_CLIENT_SECRET=YOUR_AUTH0_CLIENT_SECRET

JWT_SECRET=YOUR_JWT_SECRET

DATABASE_URL=YOUR_DATABASE_URL
```

Here's how to get the required Auth0 details. You need to register a client (application) in your Auth0 dashboard.

Follow these steps to register a client with Auth0:

1. Open the [Auth0 Applications](https://manage.auth0.com/?_gl=1*1a4zekg*_ga*Mjg3MzE5NzcyLjE3MzcwMjU4MzA.*_ga_QKMSDV5369*MTczNzIwMTkzNy45LjEuMTczNzIwMTk1Ni40MS4wLjA.#/applications) section of the Auth0 Dashboard.
2. Click on the **Create Application** button.
3. Provide a **Name**, such as "GitHub Auth".
4. Choose `Single Page Web Applications` as the application type.
5. Click on the **Create** button.
6. Finally, note down your `Domain`, `Client ID`, and `Client Secret` and add them to your `.env` file. Click the settings tab if you do not see them.

Choose a random string of letters and numbers for your `JWT_SECRET` and populate the `DATABASE_URL` with your database connection string.

> Install Dependencies

Run the following to install dependencies:

```bash
npm install
```

OR

```bash
yarn
```

> Set Up Prisma

1. Run the following command to generate the Prisma client and apply migrations:

```bash
npx prisma generate
npx prisma migrate dev --name init
```

2. If you need to seed your database, you can add a `seed` script in the `prisma/seed.ts` file and run:

```bash
npx prisma db seed
```

> Run Your Server

Start the Django server with:

```bash
npm run start:dev
```

OR

```bash
yarn start:dev
```

## Compile [React UI](https://github.com/codedthemes/mantis-free-react-admin-template)

> Edit Environment

Add your server base URL to your environment variables as follows:

```env
VITE_APP_PUBLIC_URL=<YOUR_SERVER_URL>
```

> Install Dependencies

```bash
npm install
```

OR

```bash
yarn
```

> Start the React UI

```bash
npm run dev
```

OR

```bash
yarn dev
```

---
Django API Starter provided by [App Generator](https://app-generator.dev/) - Open-source service for developers and companies.
