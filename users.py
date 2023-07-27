import json
from collections import namedtuple
from typing import Mapping

import pyotp

FIELDS = "email is_active is_available secret shares favorites ignored capital weight_name"
UserData = namedtuple('UserData', FIELDS)


class User:
    def __init__(self, conn, email):
        self.conn = conn
        self.cursor = conn.cursor()
        self.email = email
        self.user = self._get_user() or self._create_user()

    def is_available(self) -> bool:
        return self.user.is_available

    def save(self, **data):

        if not data:
            data = {k: getattr(self.user, k)
                    for k in FIELDS.split() if k != 'email'}

        keys = ', '.join(f"{k} = ?" for k in data.keys())
        values = [(json.dumps(val) if isinstance(val, Mapping) else val) for val in data.values()]
        values.append(self.user.email)

        self.cursor.execute(f'UPDATE users SET {keys} WHERE email=?', values)
        self.conn.commit()

    def new_secret(self):
        user_secret = pyotp.random_base32()
        if not self.is_available():
            self.save(secret=user_secret)
        return user_secret

    def check(self, code) -> bool:
        user_secret = self._get_secret()
        totp = pyotp.TOTP(user_secret)
        good = totp.now() == code
        if good:
            self.save(is_available=True)
        return good

    @property
    def briefcase(self):
        fields = 'shares favorites ignored capital weight_name'.split()
        row = self.cursor.execute(
            'SELECT %s FROM users WHERE email=? LIMIT 1' % ', '.join(fields),
            (self.email,)
        ).fetchone()
        return {field: (json.loads(val) if field == 'shares' else val)
                for field, val in zip(fields, row)}

    def _get_user(self):
        row = self.cursor.execute(
            'SELECT %s FROM users WHERE email=? LIMIT 1' % ', '.join(FIELDS.split()),
            (self.email,)
        ).fetchone()
        return UserData(*row) if row else None

    def _create_user(self):
        self.cursor.execute('INSERT INTO users (email) VALUES(?)', (self.email,))
        self.conn.commit()
        return self._get_user()

    def _get_secret(self):
        return self.user.secret
