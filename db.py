import sqlite3

import settings


def sqlite_get_db_name():
    return getattr(settings, "sqlite_db_name", "moex.db")


def get_sqlite_connection():
    conn = sqlite3.connect(sqlite_get_db_name())
    return conn


def init_sqlite(cursor):
    cursor.execute("CREATE TABLE prices(dt, source, price_map)")
