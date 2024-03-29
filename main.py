import json
import sys
from collections import namedtuple
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Mapping, Sequence

from db import Ticker, PriceMap, WeightMap, fetch_weights

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
        self.price = 1
        self.lotsize = 1

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
                        for ticker, shortname in names.items() if ticker in weights_map}
        self.set_prices(prices)

    def values(self):
        return self.weights.values()

    def strategy_and_bought(self, ignored: set, briefcase: Mapping):
        # акции из стратегии + уже купленные
        for weight in self.weights.values():
            if (weight.ticker in ignored) and (briefcase.get(weight.ticker, 0) <= 0):
                # убрать continue, если акция куплена
                continue
            yield weight

        for ticker, shortname in self.names.items():
            if ticker in self.weights:
                continue
            if (briefcase.get(ticker, 0) <= 0) or (ticker in ignored):
                continue

            attr = self.prices[ticker]
            weight = Weight(ticker, 0, shortname)
            weight.set_price(attr['price'], attr['lotsize'])
            yield weight

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
    capital: Decimal
    briefcase: Mapping
    ignored: set
    favorites: set
    weights: WeightManager

    all_rur: Decimal  # Сколько плановый портфель весит в рублях. Примерно равно capital
    weights_sum: Decimal

    plans: dict
    facts: dict
    user_amount_sum: Decimal
    __slots__ = ['weight_manager', 'capital', 'briefcase',
                 'ignored', 'favorites', 'all', 'weights_sum', 'all_rur',
                 'plans', 'facts', 'user_amount_sum']

    def __init__(
            self,
            weight_manager: WeightManager,
            ignored: Sequence,
            favorites: Sequence,
            capital: int,
            briefcase: Mapping):
        self.weight_manager = weight_manager
        self.capital = Decimal(capital or 1 * 1000 * 1000)
        self.briefcase = briefcase
        self.ignored = set(ignored)
        self.favorites = set(favorites)

        self.all = tuple(self.get_all())
        self.weights_sum = Decimal(sum(we.weight for we in self.all))
        self.update_plan()
        self.all_rur = Decimal(sum(plan.amount for plan in self.plans.values()))
        self.update_fact()

    def get_all(self):
        for we in self.weight_manager.strategy_and_bought(self.ignored, self.briefcase):
            yield we

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
            plan_amount = sum(
                self.plans[_ticker].amount for _ticker in PAIRS_DICT[ticker]
                if _ticker in self.plans)
            fact_amount = sum(
                self.facts[_ticker].amount for _ticker in PAIRS_DICT[ticker]
                if _ticker in self.facts)
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
