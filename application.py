import shelve
from decimal import Decimal

from flask import request
from flask import Flask, render_template, render_template_string
from flask import redirect, make_response
from flask import session
from flask_qrcode import QRcode
import pyotp

from main import UserBriefcase, weights
import tink 
from users import User, USERS_FILENAME
import settings

app = Flask(__name__)
app.secret_key = settings.SECRET_KEY
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

    with shelve.open(USERS_FILENAME) as store:
        user = User(store, session['email'])

        if request.method == 'PATCH':
            for k, v in request.form.items():
                if k == 'kapital':
                    user.user['briefcase']['kapital'] = int(v)
                elif k == 'toggle_fav':
                    favs = user.user['briefcase']['favorites'].split()
                    if v in favs:
                        favs.remove(v)
                    else:
                        favs.append(v)
                    user.user['briefcase']['favorites'] = ' '.join(favs)
                elif k == 'toggle_ign':
                    ignored = user.user['briefcase']['ignored'].split()
                    if v in ignored:
                        ignored.remove(v)
                    elif not user.user['briefcase']['briefcase'].get(v):
                        ignored.append(v)
                    user.user['briefcase']['ignored'] = ' '.join(ignored)
                else:
                    user.user['briefcase']['briefcase'][k] = int(v)
            user.save()

        ub = init_briefcase(user.briefcase)

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
    tickers = [weight.code for weight in weights.values()]
    with tink.Client(tink.TOKEN) as client:
        shares = tink.get_shares(client, tickers)
        data = tink.save_prices(tink.get_prices(client, shares))
    for code, attr in data.items():
        if code in weights:
            weights[code].set_price(attr['price'], attr['lotsize'])
    return redirect('/')


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
                    session['email'] = email
                    return 'Login success, go to <a href="/">MOEX table</a>'

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
