import json
import shelve
from datetime import datetime

import db

USERS_FILENAME = 'users.shelve'
PRICES_FILENAME = 'prices.json'
WEIGHTS_FILENAME = 'weights.txt'


def migrate():
    conn = db.get_sqlite_connection()
    cursor = conn.cursor()
    db.init_sqlite(cursor)

    result = cursor.execute('select count(*) from users').fetchone()
    if not result or not result[0]:
        migrate_users(cursor)
        conn.commit()

    result = cursor.execute('select count(*) from prices').fetchone()
    if not result or not result[0]:
        migrate_prices(cursor)
        conn.commit()

    result = cursor.execute('select count(*) from shares').fetchone()
    if not result or not result[0]:
        migrate_weights(cursor)
        conn.commit()

    conn.close()


def migrate_users(cursor):
    users = []
    with shelve.open(USERS_FILENAME) as store:
        for email, user in store.items():
            if 'briefcase' not in user:
                continue
            users.append((
                email,
                user['is_active'],
                user['is_available'],
                user['secret'],
                json.dumps(user['briefcase']['briefcase']),
                user['briefcase']['favorites'],
                user['briefcase']['ignored'],
                user['briefcase']['kapital'],
            ))
    print(users)
    cursor.executemany("INSERT INTO users VALUES(?, ?, ?, ?, ?, ?, ?, ?)", users)


def migrate_prices(cursor):
    with open(PRICES_FILENAME, 'r') as fp:
        price_map = json.load(fp)
    print(price_map)
    data = (datetime.utcnow(), 'tinkoff', json.dumps(price_map))
    cursor.execute("INSERT INTO prices VALUES(?, ?, ?)", data)


def migrate_weights(cursor):
    with open(WEIGHTS_FILENAME, 'r') as fp:
        data = fp.readlines()
    rows = [row.strip().split('\t') for row in data]
    print(rows)

    shares = []
    weights = {}
    for ticker, weight, short_name in rows:
        shares.append((ticker, short_name))
        weights[ticker] = float(weight)

    cursor.executemany(
        "INSERT INTO shares VALUES(?, ?)",
        shares)

    cursor.execute("INSERT INTO weights VALUES(?, ?)",
                   ('MOEX 2022', json.dumps(weights)))


if __name__ == '__main__':
    migrate()