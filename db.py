import json
import sqlite3
from typing import Mapping, Union, Dict

import settings

Ticker = str
PriceMap = Mapping[Ticker, Mapping[str, Union[float, int]]]
# share.ticker: {'price': float(price), 'lotsize': share.lot}
WeightMap = Mapping[Ticker, float]


def sqlite_get_db_name():
    return getattr(settings, "SQLITE_DB_NAME", "moex.sqlite")


def get_sqlite_connection():
    conn = sqlite3.connect(sqlite_get_db_name())
    return conn


def init_sqlite(cursor):
    cursor.execute("CREATE TABLE IF NOT EXISTS prices("
                   "dt PRIMARY KEY, source TEXT NOT NULL, price_map TEXT NOT NULL)")

    cursor.execute("CREATE TABLE IF NOT EXISTS users("
                   "email TEXT PRIMARY KEY, "
                   "is_active INT DEFAULT 1, is_available INT DEFAULT 0, "
                   "secret TEXT NOT NULL DEFAULT '', "
                   "shares BLOB NOT NULL DEFAULT '{}', "
                   "favorites TEXT NOT NULL DEFAULT '', ignored TEXT NOT NULL DEFAULT '', "
                   "capital NUMERIC NOT NULL DEFAULT 1000000)")

    cursor.execute("CREATE TABLE IF NOT EXISTS shares("
                   "ticker TEXT PRIMARY KEY, "
                   "short_name TEXT NOT NULL)")

    cursor.execute("CREATE TABLE IF NOT EXISTS weights("
                   "name TEXT PRIMARY KEY, "
                   "weights_json BLOB NOT NULL DEFAULT '{}')")


def fetch_names(cursor) -> Dict[str, str]:
    result = cursor.execute("SELECT ticker, short_name FROM shares").fetchall()
    return {ticker: short_name for ticker, short_name in result}


def fetch_last_prices(cursor) -> PriceMap:
    result = cursor.execute("SELECT price_map FROM prices ORDER BY dt DESC LIMIT 1").fetchone()
    return json.loads(result[0]) if result else None


def fetch_weights(cursor, name) -> WeightMap:
    result = cursor.execute("SELECT weights_json FROM weights WHERE name = ?", (name,)).fetchone()
    return json.loads(result[0]) if result else None


def fetch_weights_names(cursor):
    result = cursor.execute("SELECT name FROM weights").fetchall()
    return [row[0] for row in result] if result else None


def add_new_tickers(cursor, tickers):
    db_tickers = set(fetch_names(cursor).keys())
    new_tickers = tickers - db_tickers
    data = []
    for ticker in new_tickers:
        data.append((ticker, ticker))
    if data:
        print('created tickers', new_tickers)
        cursor.executemany("INSERT INTO shares VALUES(?, ?)", data)
