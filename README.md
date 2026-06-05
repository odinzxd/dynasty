# Dynasty

## Railway persistent database

The app uses SQLite. On Railway, SQLite must live on a persistent Volume or the
database file will be lost when the container is recreated.

Create a Railway Volume for the service and mount it at:

```text
/data
```

The Docker image sets:

```text
DATABASE_PATH=/data/database.sqlite
```

After redeploy, visit `/api/` and confirm:

```json
"persistent_storage": true
```

## First local admin login

Google login is disabled. The app uses local username/password accounts.

Set this Railway environment variable before deploying:

```text
INITIAL_ADMIN_PASSWORD=<choose-a-strong-password>
```

On startup, the app creates this admin account if needed. If the account exists
but has no local password yet, the password is initialized from the environment
variable.

```text
username: odin
email: odinzyt@gmail.com
```

After logging in, admins can create users and reset passwords from the
`Ansatte` page.
