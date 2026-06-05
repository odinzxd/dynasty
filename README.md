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
