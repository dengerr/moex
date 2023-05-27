import pyotp

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
