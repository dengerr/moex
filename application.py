import sqlite3
import typing as t
from decimal import Decimal

import pyotp
from flask import Flask, render_template, render_template_string
from flask import g
from flask import redirect, make_response
from flask import request
from flask import session
from flask_qrcode import QRcode

import settings
import tink
from main import UserBriefcase, WeightManager, fetch_names, fetch_last_prices, fetch_weights
from users import User

app = Flask(__name__)
app.secret_key = settings.SECRET_KEY
QRcode(app)

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


def app_shares() -> t.Mapping:
    result = getattr(g, '_shares', None)
    if result is None:
        result = g._shares = fetch_names(get_db().cursor())
    return result


def last_prices() -> t.Mapping:
    result = getattr(g, '_last_prices', None)
    if result is None:
        result = g._last_prices = fetch_last_prices(get_db().cursor())
    return result


def init_briefcase(user_data):
    weights_map = fetch_weights(get_db().cursor(), 'MOEX 2022')
    weight_manager = WeightManager(app_shares(), last_prices(), weights_map)
    ub = UserBriefcase(weight_manager)

    ignored = user_data.get('ignored', [])
    ub.set_ignored(ignored if isinstance(ignored, list) else ignored.split())
    favorites = user_data.get('favorites', [])
    ub.set_favorites(favorites if isinstance(favorites, list) else favorites.split())
    ub.set_capital(Decimal(user_data['capital']))
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
            if k == 'capital':
                user_briefcase['capital'] = int(v)
                user.save(capital=user_briefcase['capital'])
            elif k == 'toggle_fav':
                favs = user_briefcase['favorites'].split()
                if v in favs:
                    favs.remove(v)
                else:
                    favs.append(v)
                user_briefcase['favorites'] = ' '.join(favs)
                user.save(favorites=user_briefcase['favorites'])
            elif k == 'toggle_ign':
                ignored = user_briefcase['ignored'].split()
                if v in ignored:
                    ignored.remove(v)
                elif not user_briefcase['shares'].get(v):
                    ignored.append(v)
                user_briefcase['ignored'] = ' '.join(ignored)
                user.save(ignored=user_briefcase['ignored'])
            else:
                user_briefcase['shares'][k] = int(v)
                user.save(shares=user_briefcase['shares'])

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
    tickers = list(app_shares().keys())
    with tink.Client(tink.TOKEN) as client:
        shares = tink.get_shares(client, tickers)
        shares_with_prices = tink.get_prices(client, shares)

    price_map = {
        share.ticker: {'price': float(price), 'lotsize': share.lot}
        for share, price in shares_with_prices}

    g._last_prices = price_map
    WeightManager.save_to_sqlite(get_db(), 'tinkoff', price_map)

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
