import psycopg

conn = psycopg.connect(
    host="nova-guard-db.cf6wuwqkw62p.us-east-2.rds.amazonaws.com",
    port=5432,
    user="nova_user",
    password="NovaGuard2024Secure",
    dbname="postgres",
)
conn.autocommit = True
cur = conn.cursor()
try:
    cur.execute("CREATE DATABASE nova_guard")
    print("Database created")
except psycopg.errors.DuplicateDatabase:
    print("Database already exists")
finally:
    conn.close()
