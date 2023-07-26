import json
import sys
from collections import namedtuple
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Mapping, Union, Dict

Ticker = str
PriceMap = Mapping[Ticker, Mapping[str, Union[float, int]]]
# share.ticker: {'price': float(price), 'lotsize': share.lot}
WeightMap = Mapping[Ticker, float]

Plan = namedtuple('Plan', 'count amount')
Fact = namedtuple('Fact', 'count amount')

PAIRS = (
    ('SBER', 'SBERP'),
    ('TATN', 'TATNP'),
    ('SNGS', 'SNGSP'),
)
PAIRS_DICT = {ticker: pair for pair in PAIRS for ticker in pair}


@dataclass
class WeightFull:
    ticker: str
    weight: Decimal
    shortname: str
    price: Decimal
    lotsize: int


class Weight:
    ticker: str
    weight: Decimal
    shortname: str
    __slots__ = ['ticker', 'weight', 'shortname', 'price', 'lotsize']

    def __init__(self, ticker, weight, shortname):
        self.ticker = ticker
        self.weight = Decimal(weight)
        self.shortname = shortname

    def __str__(self):
        return f'{self.ticker}'

    def __repr__(self):
        return f'{self.ticker} -> {self.weight}'

    def set_price(self, price, lotsize: int):
        self.price = Decimal(price)
        self.lotsize = lotsize

    @property
    def lotprice(self):
        return self.price * self.lotsize


def fetch_names(cursor) -> Dict[str, str]:
    result = cursor.execute("SELECT ticker, short_name FROM shares ORDER BY ticker").fetchall()
    return {ticker: short_name for ticker, short_name in result}


def fetch_last_prices(cursor) -> PriceMap:
    result = cursor.execute("SELECT price_map FROM prices ORDER BY dt DESC LIMIT 1").fetchone()
    return json.loads(result[0]) if result else None


def fetch_weights(cursor, name) -> WeightMap:
    result = cursor.execute("SELECT weights_json FROM weights WHERE name = ?", (name,)).fetchone()
    return json.loads(result[0]) if result else None


class WeightManager:
    names: Mapping[Ticker, str]
    prices: PriceMap
    weights_map: WeightMap
    weights: Mapping[Ticker, Weight]
    __slots__ = ['names', 'prices', 'weights_map', 'weights']

    def __init__(self, names, prices: PriceMap, weights_map: WeightMap):
        self.names = names
        self.prices = prices
        self.weights_map = weights_map
        self.weights = {ticker: Weight(ticker, weights_map[ticker], shortname)
                        for ticker, shortname in names.items()}
        self.set_prices(prices)

    def values(self):
        return self.weights.values()

    @staticmethod
    def save_to_sqlite(conn, source: str, price_map: PriceMap):
        data = (datetime.utcnow(), source, json.dumps(price_map))
        cursor = conn.cursor()
        cursor.execute("INSERT INTO prices VALUES(?, ?, ?)", data)
        conn.commit()

    def set_prices(self, price_map: PriceMap):
        for ticker, attr in price_map.items():
            if ticker in self.weights:
                self.weights[ticker].set_price(attr['price'], attr['lotsize'])


class UserBriefcase:
    capital = Decimal(1 * 1000 * 1000)
    briefcase: dict
    ignored: set
    favorites: set
    weights: WeightManager

    all_rur: Decimal  # Сколько плановый портфель весит в рублях. Примерно равно capital
    weights_sum: Decimal

    plans: dict
    facts: dict
    user_amount_sum: Decimal

    def __init__(self, weight_manager: WeightManager):
        self.weight_manager = weight_manager
        self.ignored = set()
        self.favorites = set()
        self.set_weights_sum()
        self.briefcase = dict()

    @property
    def all(self):
        for we in self.weight_manager.values():
            if we.ticker not in self.ignored:
                yield we

    def set_capital(self, capital):
        self.capital = capital
        # self.all_rur = sum((we.weight / self.weights_sum * capital) for we in self.all)
        self.update_plan()
        self.all_rur = Decimal(sum(plan.amount for plan in self.plans.values()))

    def set_briefcase(self, briefcase):
        self.briefcase = briefcase
        self.set_weights_sum()
        self.update_fact()

    def set_ignored(self, ignored):
        self.ignored = set(ignored)
        self.set_weights_sum()

    def set_favorites(self, favorites):
        self.favorites = set(favorites)
        self.set_weights_sum()

    def set_weights_sum(self):
        self.weights_sum = Decimal(sum(we.weight for we in self.all))

    def update_plan(self):
        self.plans = {}
        # _capital = self.capital * self.weights_sum / 100
        # print('_kap', _capital, self.weights_sum)
        for we in self.all:
            in_rur = we.weight / self.weights_sum * self.capital
            lot_count = round(in_rur / we.lotprice)
            count = lot_count * we.lotsize
            amount = lot_count * we.lotprice
            self.plans[we.ticker] = Plan(count, amount)

    def update_fact(self):
        self.facts = {}
        self.user_amount_sum = Decimal(0)
        for we in self.all:
            count = self.briefcase.get(we.ticker, 0)
            amount = we.price * count
            self.user_amount_sum += amount
            self.facts[we.ticker] = Fact(count, amount)

    def get_in_percent(self, ticker):
        # процент акции от планового по этой акции
        if ticker in PAIRS_DICT:
            # для парных акций считаем сумму и по плану, и по факту
            plan_amount = sum(self.plans[_code].amount for _code in PAIRS_DICT[ticker])
            fact_amount = sum(self.facts[_code].amount for _code in PAIRS_DICT[ticker])
        else:
            plan_amount = self.plans[ticker].amount
            fact_amount = self.facts[ticker].amount
        return self.in_percent(fact_amount, plan_amount)

    def percent_of_total(self, ticker):
        # процент акции от общего капитала
        fact_amount = self.facts[ticker].amount
        return self.in_percent(fact_amount, self.total())

    def total(self, use_rur=False):
        return self.all_rur if use_rur and self.all_rur else self.capital

    def in_percent(self, cur, total):
        if cur and total:
            in_percent = cur / total
            return in_percent
        else:
            return 0

    def print_plan(self):
        for we in self.all:
            plan = self.plans[we.ticker]
            print(f"{we.ticker}, {plan.count}, {plan.amount:.2f}")

    def print_fact(self):
        for ticker, fact in self.facts.items():
            if fact.count:
                in_percent = self.get_in_percent(ticker)
                print(f'{ticker}: {fact.count} == {fact.amount} ({in_percent:.2%})')
        print(f'user_amount_sum: {self.user_amount_sum:.2f} / {self.all_rur:.2f}')

    def print_all(self, use_rur=False, only_fav=False):
        total = self.total(use_rur)
        print(
            f"{' ':>20} {' ':>5} {' ':>9} {'plan':>7} {total:>10.0f} {'fact':>7} {self.user_amount_sum:>10.0f} ({self.in_percent(self.user_amount_sum, total):>7.0%})")
        print()

        print(f"{' ':>20} {'CODE':<5} {'price':>9} {'PI':>7} {'PRUR':>10} {'FI':>7} {'FRUR':>10} ({'%%%':^7})")
        for we in self.all:
            if only_fav and we.ticker not in self.favorites:
                continue
            plan = self.plans[we.ticker]
            fact = self.facts[we.ticker]
            in_percent = self.get_in_percent(we.ticker)
            fav = 'v' if not only_fav and we.ticker in self.favorites else ''
            ign = 'i' if we.ticker in self.ignored else ''
            print(
                f'{we.shortname[:20]:<20} {we.ticker:<5} {we.price:>9.2f} {plan.count:>7} {plan.amount:>10.0f} {fact.count:>7} {fact.amount:>10.0f} ({in_percent:>7.0%}) {fav or ign}')


if __name__ == '__main__':
    weights_map = fetch_weights(get_db().cursor(), 'MOEX 2022')
    weight_manager = WeightManager(app_shares(), last_prices(), weights_map)
    ub = UserBriefcase(weight_manager)
    with open('user_briefcase.json', 'r') as fp:
        user_data = json.load(fp)
        ignored = user_data.get('ignored', [])
        if 'all' not in sys.argv:
            ub.set_ignored(ignored if isinstance(ignored, list) else ignored.split())
        favorites = user_data.get('favorites', [])
        ub.set_favorites(favorites if isinstance(favorites, list) else favorites.split())
        ub.set_capital(Decimal(user_data['capital']))
        ub.set_briefcase(user_data['shares'])

    only_fav = 'fav' in sys.argv
    ub.print_all(only_fav=only_fav)
