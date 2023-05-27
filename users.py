import shelve
from secrets import token_urlsafe
from typing import Optional

import pyotp

SESSION_FILENAME = 'sessions.shelve'
USERS_FILENAME = 'users.shelve'


class User:
    def __init__(self, store, email):
        if email not in store:
            store[email] = {
                'email': email,
                'is_available': False,
                'is_active': True,
            }
        self.user = store[email]
        self.store = store

    def is_available(self) -> bool:
        return self.user.get('is_available', False)

    def get_secret(self):
        return self.user['secret']

    def save(self):
        self.store[self.user['email']] = self.user

    def login(self):
        if not self.is_available():
            self.user['is_available'] = True
            self.save()

    def new_secret(self):
        user_secret = pyotp.random_base32()
        if not self.is_available():
            self.user['secret'] = user_secret
            self.save()
        return user_secret

    def check(self, code) -> bool:
        user_secret = self.get_secret()
        totp = pyotp.TOTP(user_secret)
        good = totp.now() == code
        if good:
            self.login()
        return good

    @property
    def briefcase(self):
        if not 'briefcase' in self.user:
            self.user['briefcase'] = dict(
                kapital=1000*1000,
                ignored="",
                favorites="",
                briefcase={},
            )
        return self.user['briefcase']


class Session:
    @classmethod
    def create(cls, email: str):
        token = token_urlsafe(16)
        with shelve.open(SESSION_FILENAME) as store:
            store[token] = dict(
                email=email,
                user=email,
            )
        return token

    @classmethod
    def get(cls, token: str) -> Optional[dict]:
        with shelve.open(SESSION_FILENAME) as store:
            if token in store:
                session = store[token]
                if not session:
                    return
                with shelve.open(USERS_FILENAME) as users:
                    user = users.get(session.get('user'))
                return user
