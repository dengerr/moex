import shelve
from decimal import Decimal

from flask import request
from flask import Flask, render_template, render_template_string
from flask import make_response, redirect
from flask_qrcode import QRcode
import pyotp

from main import UserBriefcase
from users import User, Session, USERS_FILENAME

app = Flask(__name__)
QRcode(app)


def init_briefcase(user_data):
    ub = UserBriefcase()
    ignored = user_data.get('ignored', [])
    ub.set_ignored(ignored if isinstance(ignored, list) else ignored.split())
    favorites = user_data.get('favorites', [])
    ub.set_favorites(favorites if isinstance(favorites, list) else favorites.split())
    ub.set_kapital(Decimal(user_data['kapital']))
    ub.set_briefcase(user_data['briefcase'])
    return ub


@app.route("/", methods=['GET', 'PATCH'])
def index():
    user_dict = Session.get(request.cookies.get('token', ''))
    if not user_dict:
        return redirect('/login')

    with shelve.open(USERS_FILENAME) as store:
        user = User(store, user_dict['email'])

        if request.method == 'PATCH':
            for k, v in request.form.items():
                if k == 'kapital':
                    user.user['briefcase']['kapital'] = int(v)
                else:
                    user.user['briefcase']['briefcase'][k] = int(v)
            user.save()

        ub = init_briefcase(user.briefcase)

    return render_template('table.html', ub=ub, user=user_dict)


@app.route("/qr")
def qr():
    return render_template_string('<img src="{{ qrcode("Do you speak QR?") }}">')


@app.route("/login", methods=['GET', 'POST'])
def login():
    qr = None
    email = request.form.get('email', '')
    if request.method == 'POST' and email:
        with shelve.open(USERS_FILENAME) as store:
            user = User(store, email)
            if code := request.form.get('code'):
                if user.check(code):
                    resp = make_response(render_template_string(
                        'Login success, go to <a href="/">MOEX table</a>'))
                    token = Session.create(email)
                    resp.set_cookie('token', token)
                    return resp

            elif not user.is_available():
                user_secret = user.new_secret()
                qr = pyotp.totp.TOTP(user_secret).provisioning_uri(
                        name=email, issuer_name='MOEX table')
            return render_template('totp_form.html', qr=qr)
    return render_template('login.html')

@app.route("/logout", methods=['GET', 'POST'])
def logout():
    resp = make_response(redirect('/'))
    resp.set_cookie('token', '')
    return resp
