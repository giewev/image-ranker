import sqlite3
import psycopg2
from psycopg2 import sql

# SQLite connection
sqlite_conn = sqlite3.connect('mtg_card_art.db')
sqlite_cur = sqlite_conn.cursor()

# PostgreSQL connection
postgres_conn = psycopg2.connect(dbname='postgres_db_name', user='postgres_user', password='postgres_password', host='postgres_host', port='postgres_port')
postgres_cur = postgres_conn.cursor()

# Get all tables in SQLite database
sqlite_cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = sqlite_cur.fetchall()

for table in tables:
    table = table[0]
    sqlite_cur.execute(f"PRAGMA table_info({table})")
    columns = [column[1] for column in sqlite_cur.fetchall()]
    sqlite_cur.execute(f"SELECT * FROM {table}")
    rows = sqlite_cur.fetchall()

    # Create table in PostgreSQL
    postgres_cur.execute(
        sql.SQL("CREATE TABLE IF NOT EXISTS {} ({});").format(
            sql.Identifier(table),
            sql.SQL(', ').join(sql.Identifier(column) for column in columns)
        )
    )
    postgres_conn.commit()

    # Insert data into PostgreSQL table
    for row in rows:
        postgres_cur.execute(
            sql.SQL("INSERT INTO {} VALUES ({});").format(
                sql.Identifier(table),
                sql.SQL(', ').join(sql.Placeholder() for column in columns)
            ),
            row
        )
    postgres_conn.commit()

# Close connections
sqlite_conn.close()
postgres_conn.close()
