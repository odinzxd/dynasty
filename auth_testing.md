# Dynasty 8 - Auth Testing Playbook

The app uses local username/password auth. Admins create users from the
`Ansatte` page, and sessions are stored in `user_sessions`.

## First admin

Set this Railway environment variable before deploy:

```text
INITIAL_ADMIN_PASSWORD=<strong password>
```

The app creates or updates:

```text
username: odin
email: odinzyt@gmail.com
role: admin
```

## API login

```bash
API=https://dynasty-production-c083.up.railway.app/api

curl -i -s -X POST "$API/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"odin","password":"<INITIAL_ADMIN_PASSWORD>"}'
```

Copy the returned `session_token` cookie or let the browser keep it.

## Create a user

```bash
curl -s -X POST "$API/users" \
  -H "Content-Type: application/json" \
  -H "Cookie: session_token=<token>" \
  -d '{
    "username":"sara",
    "password":"ByttMeg123!",
    "email":"sara@dynasty8.no",
    "name":"Sara Hansen",
    "role":"ansatt",
    "employee_number":"E101"
  }'
```

## Check current user

```bash
curl -s "$API/auth/me" -H "Cookie: session_token=<token>"
```
