import sqlite3

import settings


def sqlite_get_db_name():
    return getattr(settings, "SQLITE_DB_NAME", "moex.sqlite")


def get_sqlite_connection():
    conn = sqlite3.connect(sqlite_get_db_name())
    return conn


def init_sqlite(cursor):
    cursor.execute("CREATE TABLE IF NOT EXISTS prices("
                   "dt PRIMARY KEY, source TEXT NOT NULL, price_map TEXT NOT NULL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS users("
                   "email PRIMARY KEY,"
                   "is_active INT DEFAULT 1, is_available INT DEFAULT 0,"
                   "secret TEXT NOT NULL DEFAULT '', "
                   "shares TEXT NOT NULL DEFAULT '{}',"
                   "favorites TEXT NOT NULL DEFAULT '', ignored TEXT NOT NULL DEFAULT '',"
                   "kapital NUMERIC NOT NULL DEFAULT 1000000)")
