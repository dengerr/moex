from decimal import Decimal
import json
from flask import Flask, render_template
from main import UserBriefcase

app = Flask(__name__)

def init_briefcase():
    ub = UserBriefcase()
    with open('user_briefcase.json', 'r') as fp:
        user_data = json.load(fp)
        ignored = user_data.get('ignored', [])
        ub.set_ignored(ignored if isinstance(ignored, list) else ignored.split())
        favorites = user_data.get('favorites', [])
        ub.set_favorites(favorites if isinstance(favorites, list) else favorites.split())
        ub.set_kapital(Decimal(user_data['kapital']))
        ub.set_briefcase(user_data['briefcase'])

    # ub.print_all(only_fav=False)
    return ub

@app.route("/")
def hello_world():
    ub = init_briefcase()
    return render_template('table.html', ub=ub)


@app.route("/clicked", methods=['GET', 'POST'])
def clicked():
    print('click')
    return """ test """

