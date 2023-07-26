import shelve
import sqlite3
from decimal import Decimal

import pyotp
from flask import Flask, render_template, render_template_string
from flask import g
from flask import redirect, make_response
from flask import request
from flask import session
from flask_qrcode import QRcode

import db
import settings
import tink
from main import UserBriefcase, WeightManager
from users import User

app = Flask(__name__)
app.secret_key = settings.SECRET_KEY
QRcode(app)

weight_manager = WeightManager()

DATABASE = 'moex.sqlite'


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def init_briefcase(user_data):
    ub = UserBriefcase(weight_manager)
    ignored = user_data.get('ignored', [])
    ub.set_ignored(ignored if isinstance(ignored, list) else ignored.split())
    favorites = user_data.get('favorites', [])
    ub.set_favorites(favorites if isinstance(favorites, list) else favorites.split())
    ub.set_kapital(Decimal(user_data['kapital']))
    ub.set_briefcase(user_data['shares'])
    return ub


def htmx_response(template, **data):
    is_htmx = request.headers.get('Hx-Request') == 'true'

    if is_htmx:
        return render_template(template, **data)
    else:
        return render_template('base.html', template=template, **data)


@app.route("/", methods=['GET', 'PATCH'])
def index():
    if 'email' not in session:
        return redirect('/login')

    user = User(get_db(), session['email'])
    user_briefcase = user.briefcase

    if request.method == 'PATCH':
        for k, v in request.form.items():
            if k == 'kapital':
                user_briefcase['kapital'] = int(v)
            elif k == 'toggle_fav':
                favs = user_briefcase['favorites'].split()
                if v in favs:
                    favs.remove(v)
                else:
                    favs.append(v)
                user_briefcase['favorites'] = ' '.join(favs)
            elif k == 'toggle_ign':
                ignored = user_briefcase['ignored'].split()
                if v in ignored:
                    ignored.remove(v)
                elif not user_briefcase['briefcase'].get(v):
                    ignored.append(v)
                user_briefcase['ignored'] = ' '.join(ignored)
            else:
                user_briefcase['briefcase'][k] = int(v)
        user.save(briefcase=user_briefcase)

    ub = init_briefcase(user_briefcase)

    templates = {
        'desktop': 'table.html',
        'mobile': 'table-mobile.html',
    }
    layout = request.cookies.get('layout', '')
    template = templates.get(layout, templates['mobile'])

    return htmx_response(template, ub=ub, session=session)


@app.route("/settings")
def settings_view():
    layout = request.args.get('layout', '')
    response = make_response(redirect('/'))
    if layout in ('desktop', 'mobile'):
        response.set_cookie('layout', layout)
    return response


@app.route("/update_prices", methods=['GET', 'POST'])
def update_prices_view():
    tickers = [weight.code for weight in weight_manager.values()]
    with tink.Client(tink.TOKEN) as client:
        shares = tink.get_shares(client, tickers)
        shares_with_prices = tink.get_prices(client, shares)

    price_map = {
        share.ticker: {'price': float(price), 'lotsize': share.lot}
        for share, price in shares_with_prices}

    weight_manager.set_prices(price_map)

    conn = db.get_sqlite_connection()
    weight_manager.save_to_sqlite(conn, 'tinkoff')
    conn.close()

    return redirect('/')


@app.route("/qr")
def qr():
    return render_template_string('<img src="{{ qrcode("Do you speak QR?") }}">')


@app.route("/login", methods=['GET', 'POST'])
def login():
    qr = None
    email = request.form.get('email', '')
    if request.method == 'POST' and email:
        user = User(get_db(), email)
        code = request.form.get('code')
        if code:
            if user.check(code):
                session['email'] = email
                return 'Login success, go to <a href="/">MOEX table</a>'
            else:
                print('check code failed')

        elif not user.is_available():
            user_secret = user.new_secret()
            qr = pyotp.totp.TOTP(user_secret).provisioning_uri(
                name=email, issuer_name='MOEX table')
        return render_template('totp_form.html', qr=qr)
    return render_template('login.html')


@app.route("/logout", methods=['GET', 'POST'])
def logout():
    if 'email' in session:
        del session['email']
    return redirect('/')
