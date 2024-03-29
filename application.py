import json
import sqlite3
import typing as t
from decimal import Decimal

import pyotp
from flask import Flask
from flask import g
from flask import make_response, redirect, render_template, render_template_string
from flask import request, session
from flask_qrcode import QRcode

import db
import settings
import tink
from main import UserBriefcase, WeightManager
from users import User

app = Flask(__name__)
app.secret_key = settings.SECRET_KEY
DATABASE = getattr(settings, "SQLITE_DB_NAME", "moex.sqlite")
QRcode(app)


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
        result = g._shares = db.fetch_names(get_db().cursor())
    return result


def last_prices() -> t.Mapping:
    result = getattr(g, '_last_prices', None)
    if result is None:
        result = g._last_prices = db.fetch_last_prices(get_db().cursor())
    return result


def init_briefcase(user_data):
    weight_name = user_data.get('weight_name', 'MOEX 2022')
    weights_map = db.fetch_weights(get_db().cursor(), weight_name)
    ub = UserBriefcase(
        WeightManager(app_shares(), last_prices(), weights_map),
        user_data['ignored'].split(),
        user_data['favorites'].split(),
        user_data['capital'],
        user_data['shares'],
    )
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


@app.route("/weights", methods=['GET', 'POST'])
def weights_view():
    assert session['email']
    conn = get_db()
    cursor = conn.cursor()
    weights_names = db.fetch_weights_names(cursor)

    if request.args.get('use'):
        cursor.execute(
            "UPDATE users SET weight_name=? WHERE email=?",
            (request.args.get('use'), session['email'],))
        conn.commit()
        return redirect('/')

    if request.method == 'POST':
        content = request.form.get('content')
        name = request.form.get('name')
        if name and content:
            tickers = set(json.loads(content).keys())
            db.add_new_tickers(cursor, tickers)

            if name in weights_names:
                cursor.execute(
                    "UPDATE weights SET weights_json=? WHERE name=?",
                    (content, name, ))
            else:
                cursor.execute(
                    "INSERT INTO weights VALUES(?, ?)",
                    (name, content, ))
            conn.commit()
        else:
            return 'error'

    name = request.args.get('name')
    if name == 'new':
        return render_template('weights_form.html', content='', name='')
    elif name:
        weights_dict = db.fetch_weights(cursor, name)
        return render_template('weights_form.html', content=json.dumps(weights_dict), name=name)

    return htmx_response('weights.html', weights_names=weights_names, session=session)


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
