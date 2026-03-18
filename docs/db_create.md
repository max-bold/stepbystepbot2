# Database setup

First create a new database and user with the following command:

```bash
createdb -U postgres [db_name]
psql -U postgres -d [db_name] -c "CREATE USER [db_user] WITH PASSWORD '[db_password]'; ALTER DATABASE [db_name] OWNER TO [db_user];"
```

then add to .env file, repalcing the placeholders with your actual database credentials:

```env
DATABASE_URL = "postgresql+psycopg://[db_user]:[db_password]@[db_host]:[db_port]/[db_name]"
```