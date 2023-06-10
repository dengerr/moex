from typing import Optional
import sys
from collections import namedtuple
from decimal import Decimal
import json

secure_columns = [
    'SECID', 'BOARDID', 'SHORTNAME', 'PREVPRICE', 'LOTSIZE', 'FACEVALUE', 'STATUS', 'BOARDNAME', 'DECIMALS', 'SECNAME',
    'REMARKS', 'MARKETCODE', 'INSTRID', 'SECTORID', 'MINSTEP', 'PREVWAPRICE', 'FACEUNIT', 'PREVDATE', 'ISSUESIZE',
    'ISIN', 'LATNAME', 'REGNUMBER', 'PREVLEGALCLOSEPRICE', 'CURRENCYID', 'SECTYPE', 'LISTLEVEL', 'SETTLEDATE']
Secur = namedtuple('Secur', secure_columns)
Plan = namedtuple('Plan', 'count amount')
Fact = namedtuple('Fact', 'count amount')

PAIRS = (
    ('SBER', 'SBERP'),
    ('TATN', 'TATNP'),
    ('SNGS', 'SNGSP'),
)
PAIRS_DICT = {code: pair for pair in PAIRS for code in pair}

class Weight:
    code: str
    weight: Decimal
    shortname: str
    _secur: Optional[Secur] = None

    def __init__(self, code, weight, shortname):
        self.code = code
        self.weight = Decimal(weight)
        self.shortname = shortname

    def __str__(self):
        return f'{self.code}'

    def set_secur(self, secur):
        self._secur = secur

    @property
    def price(self):
        return Decimal(self._secur.PREVPRICE)

    @property
    def lotsize(self):
        return self._secur.LOTSIZE

    @property
    def lotprice(self):
        return self.price * self.lotsize


# init
def get_rows():
    with open('securities.json', 'r') as fp:
        data = json.load(fp)['securities']
    rows = [Secur(*row) for row in data['data']]
    return rows


def get_weights():
    with open('weights.txt', 'r') as fp:
        data = fp.readlines()
    rows = [row.strip().split('\t') for row in data]
    return [Weight(*row) for row in rows]


weights = {}
for weight in get_weights():
    weights[weight.code] = weight
for row in get_rows():
    if row.SECID in weights:
        weights[row.SECID].set_secur(row)


class UserBriefcase:
    kapital = Decimal(1 * 1000 * 1000)
    briefcase: dict
    ignored: set
    favorites: set

    all_rur: Decimal  # сколько плановый портфель весит в рублях. Примерно равно kapital
    weights_sum: Decimal

    plans: dict
    facts: dict
    user_amount_sum: Decimal

    def __init__(self):
        self.ignored = set()
        self.favorites = set()
        self.set_weights_sum()
        self.briefcase = dict()

    @property
    def all(self):
        for we in weights.values():
            if we.code not in self.ignored:
                yield we

    def set_kapital(self, kapital):
        self.kapital = kapital
        # self.all_rur = sum((we.weight / self.weights_sum * kapital) for we in self.all)
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
        # _kapital = self.kapital * self.weights_sum / 100
        # print('_kap', _kapital, self.weights_sum)
        for we in self.all:
            in_rur = we.weight / self.weights_sum * self.kapital
            lot_count = round(in_rur / we.lotprice)
            count = lot_count * we.lotsize
            amount = lot_count * we.lotprice
            self.plans[we.code] = Plan(count, amount)

    def update_fact(self):
        self.facts = {}
        self.user_amount_sum = Decimal(0)
        for we in self.all:
            count = self.briefcase.get(we.code, 0)
            amount = we.price * count
            self.user_amount_sum += amount
            self.facts[we.code] = Fact(count, amount)

    def get_in_percent(self, code):
        # процент акции от планового по этой акции
        if code in PAIRS_DICT:
            # для парных акций считаем сумму и по плану, и по факту
            plan_amount = sum(self.plans[_code].amount for _code in PAIRS_DICT[code])
            fact_amount = sum(self.facts[_code].amount for _code in PAIRS_DICT[code])
        else:
            plan_amount = self.plans[code].amount
            fact_amount = self.facts[code].amount
        return self.in_percent(fact_amount, plan_amount)

    def percent_of_total(self, code):
        # процент акции от общего капитала
        fact_amount = self.facts[code].amount
        return self.in_percent(fact_amount, self.total())

    def total(self, use_rur=False):
        return self.all_rur if use_rur and self.all_rur else self.kapital

    def in_percent(self, cur, total):
        if cur and total:
            in_percent = cur / total
            return in_percent
        else:
            return 0

    def print_plan(self):
        for we in self.all:
            plan = self.plans[we.code]
            print(f"{we.code}, {plan.count}, {plan.amount:.2f}")

    def print_fact(self):
        for code, fact in self.facts.items():
            if fact.count:
                in_percent = self.get_in_percent(code)
                print(f'{code}: {fact.count} == {fact.amount} ({in_percent:.2%})')
        print(f'user_amount_sum: {self.user_amount_sum:.2f} / {self.all_rur:.2f}')

    def print_all(self, use_rur=False, only_fav=False):
        in_percent = 0
        total = self.total(use_rur)
        print(f"{' ':>20} {' ':>5} {' ':>9} {'plan':>7} {total:>10.0f} {'fact':>7} {self.user_amount_sum:>10.0f} ({self.in_percent(self.user_amount_sum, total):>7.0%})")
        print()

        print(f"{' ':>20} {'CODE':<5} {'price':>9} {'PI':>7} {'PRUR':>10} {'FI':>7} {'FRUR':>10} ({'%%%':^7})")
        for we in self.all:
            if only_fav and we.code not in self.favorites:
                continue
            plan = self.plans[we.code]
            fact = self.facts[we.code]
            in_percent = self.get_in_percent(we.code)
            fav = 'v' if not only_fav and we.code in self.favorites else ''
            ign = 'i' if we.code in self.ignored else ''
            print(f'{we.shortname[:20]:<20} {we.code:<5} {we.price:>9.2f} {plan.count:>7} {plan.amount:>10.0f} {fact.count:>7} {fact.amount:>10.0f} ({in_percent:>7.0%}) {fav or ign}')


if __name__ == '__main__':
    ub = UserBriefcase()
    with open('user_briefcase.json', 'r') as fp:
        user_data = json.load(fp)
        ignored = user_data.get('ignored', [])
        if 'all' not in sys.argv:
            ub.set_ignored(ignored if isinstance(ignored, list) else ignored.split())
        favorites = user_data.get('favorites', [])
        ub.set_favorites(favorites if isinstance(favorites, list) else favorites.split())
        ub.set_kapital(Decimal(user_data['kapital']))
        ub.set_briefcase(user_data['briefcase'])

    only_fav = 'fav' in sys.argv
    ub.print_all(only_fav=only_fav)
