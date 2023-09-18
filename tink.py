import pickle
from typing import Iterable, List

from django.conf import settings
from tinkoff.invest import Client, PortfolioResponse, Bond
from tinkoff.invest.grpc.instruments_pb2 import INSTRUMENT_ID_TYPE_TICKER, INSTRUMENT_ID_TYPE_UID
from tinkoff.invest.grpc.users_pb2 import ACCOUNT_TYPE_TINKOFF, ACCOUNT_TYPE_TINKOFF_IIS
from tinkoff.invest.utils import quotation_to_decimal, money_to_decimal

from main import PriceMap

TOKEN = settings.TINKOFF_TOKEN
SHARE_CLASS_CODE = 'TQBR'
BOND_CLASS_CODE = 'TQOB'
EXAMPLE_TICKERS = ['SBER', 'MOEX', 'ROSN', 'GMKN', 'LKOH']
Client = Client  # not autoremove import


def save(name: str, obj):
    with open(f'{name}.pickle', 'wb') as fp:
        pickle.dump(obj, fp)


def load(name: str):
    with open(f'{name}.pickle', 'rb') as fp:
        return pickle.load(fp)


def get_shares(client, tickers: Iterable) -> list:
    shares = [
        client.instruments.share_by(
            id_type=INSTRUMENT_ID_TYPE_TICKER,
            class_code=SHARE_CLASS_CODE,
            id=ticker,
        ).instrument
        for ticker in tickers]
    return shares


def get_prices_by_ticker(client, tickers: Iterable) -> PriceMap:
    # deprecated
    shares = {share.uid: share for share in get_shares(client, tickers)}
    response = client.market_data.get_last_prices(
        instrument_id=[share.uid for share in shares.values()])
    result = []
    for item in response.last_prices:
        result.append((shares[item.instrument_uid], quotation_to_decimal(item.price)))

    price_map = {
        share.ticker: {'price': float(price), 'lotsize': share.lot}
        for share, price in result}

    return price_map


def get_prices_by_uid(client, tickers, uids, lotsizes) -> PriceMap:
    response = client.market_data.get_last_prices(instrument_id=uids)
    prices = (
        quotation_to_decimal(item.price)
        for item in response.last_prices
    )
    price_map = {
        ticker: {'price': float(price), 'lotsize': lotsize}
        for ticker, price, lotsize in zip(tickers, prices, lotsizes)
    }
    return price_map


"""
3  добавить бонды в БД
4  экспорт портфолио в портфелио
5  показ раздельные портфели и объединенный
"""


def find(query):
    with Client(TOKEN) as client:
        result = client.instruments.find_instrument(query=query)
        return result


def get_bonds(uids):
    with Client(TOKEN) as client:
        instruments = [
            client.instruments.bond_by(
                # id_type=INSTRUMENT_ID_TYPE_TICKER,
                # class_code=BOND_CLASS_CODE,
                # id=ticker,
                id_type=INSTRUMENT_ID_TYPE_UID,
                id=uid,
            ).instrument
            for uid in uids]

        response = client.market_data.get_last_prices(
            instrument_id=[instr.uid for instr in instruments])
        # цена: отклонение в процентах умножить на номинал
        for item in response.last_prices:
            print(quotation_to_decimal(item.price) / 100 *
                  quotation_to_decimal(instruments[0].nominal))
    return instruments


def get_portfolio():
    # по счету возвращает показатели (стоимости разных инструментов) и positions
    with Client(TOKEN) as client:
        accounts = client.users.get_accounts()
        save('accounts', accounts)
        print(accounts)

        result = []
        for account in accounts.accounts:
            # инвесткопилка не поддерживается
            if account.type in (ACCOUNT_TYPE_TINKOFF, ACCOUNT_TYPE_TINKOFF_IIS):
                # https://tinkoff.github.io/investAPI/operations/#portfolioresponse
                portfolio = client.operations.get_portfolio(account_id=account.id)
                result.append(portfolio)
                # текущая стоимость счета
                print(account.name)
                print(quotation_to_decimal(portfolio.total_amount_portfolio))

    save('portfolio', result)

    return result


def print_portfolio():
    from shares import models
    uid_name = {
        str(uid): ticker for uid, ticker in
        models.Share.objects.all().values_list('instrument_uid', 'short_name')}
    portfolios: List[PortfolioResponse] = load('portfolio')
    accounts = load('accounts')
    bonds_instruments: List[Bond] = load('bonds')
    for bond in bonds_instruments:
        uid_name[bond.uid] = bond.name

    # diff
    # briefcase = models.Briefcase.objects.get(id=1)
    # rows = {str(k): v for k, v in briefcase.rows.all().values_list(
    #     'share__ticker', 'count')}
    # print(rows)
    # tin_rows = {}

    # bonds = set()

    total = 0
    total_shares = 0
    for acc, port in zip(accounts.accounts, portfolios):
        print(f'{acc.name} {money_to_decimal(port.total_amount_portfolio):.0f}')
        for pos in port.positions:
            name = uid_name.get(pos.instrument_uid, pos.figi)
            quantity = quotation_to_decimal(pos.quantity)
            price = money_to_decimal(pos.current_price)
            summ = ((price + money_to_decimal(pos.current_nkd)) * quantity)
            expected_yield = money_to_decimal(pos.expected_yield)
            wasted = money_to_decimal(pos.average_position_price) * quantity
            app_percent = (summ * 100 / wasted) - 100
            print(f'{name:<40}{summ:>20.2f}')
            print(f'{quantity:>10.0f}{price:>20.2f}{expected_yield:>20.2f}{app_percent:>9.2f}%')
            total += summ
            if pos.instrument_type == 'share':
                total_shares += summ

                # diff
                # tin_rows.setdefault(name, 0)
                # tin_rows[name] += quantity

            # elif pos.instrument_type == 'bond' and pos.instrument_uid not in bonds:
            #     bonds.add(pos.instrument_uid)
            # print(pos)
        print()
    print(f'total: {total:.0f}')
    print(f'total_shares: {total_shares:.0f}')

    # save('bonds', get_bonds(bonds))

    # diff
    # for ticker, count in rows.items():
    #     if int(tin_rows.get(ticker, 0)) != count:
    #         print('not equal, ticker', ticker)
    #         print(f'{count} != {tin_rows.get(ticker)}')


def get_positions():
    # более быстрый, чем портфолио, запрос, без цен и статистики, только количества
    with Client(TOKEN) as client:
        accounts = client.users.get_accounts()
        print(accounts)

        result = []
        for account in accounts.accounts:
            # https://tinkoff.github.io/investAPI/operations/#positionsresponse
            positions = client.operations.get_positions(account_id=account.id)
            result.append(positions)
            # example: positions.securities[0]
            # PositionsSecurities(figi='BBG004730JJ5', blocked=0, balance=450,
            # position_uid='1b33fa68-cfc8-43e1-bd0e-2155d0199e7d',
            # instrument_uid='5e1c2634-afc4-4e50-ad6d-f78fc14a539a',
            # exchange_blocked=False, instrument_type='share')

    save('positions', positions)
    return result


def print_positions_info():
    # тут нет цен, надо подтягивать из БД или отдельным запросом
    acc_positions = load('positions')
    for positions in acc_positions:
        for pos in positions.securities:
            print(pos)
        print()
