import json

from tinkoff.invest import Client
from tinkoff.invest.grpc.instruments_pb2 import INSTRUMENT_ID_TYPE_TICKER
from tinkoff.invest.utils import quotation_to_decimal

from settings import TINKOFF_TOKEN

TOKEN = TINKOFF_TOKEN
CLASS_CODE = 'TQBR'
TICKERS = ['SBER', 'MOEX', 'ROSN', 'GMKN', 'LKOH']


def get_shares(client, tickers):
    # shares = client.instruments.shares()
    # shares = [inst for inst in shares.instruments if inst.ticker in tickers]
    shares = [
        client.instruments.share_by(id_type=INSTRUMENT_ID_TYPE_TICKER, class_code=CLASS_CODE, id=ticker).instrument
        for ticker in tickers]
    shares = [inst for inst in shares if inst.ticker in tickers]
    return {share.figi: share for share in shares}


def get_prices(client, shares, ):
    response = client.market_data.get_last_prices(figi=[share.figi for share in shares.values()])
    result = []
    for item in response.last_prices:
        print(item.figi, ' = ', item.price, shares[item.figi].name, )
        result.append((shares[item.figi], quotation_to_decimal(item.price)))
    return result


def save_prices(shares):
    result = {}
    for share, price in shares:
        result[share.ticker] = {'price': float(price), 'lotsize': share.lot}

    with open('prices.json', 'w') as fp:
        json.dump(result, fp)


def main_fun():
    with Client(TOKEN) as client:
        for acc in client.users.get_accounts().accounts:
            print(acc)
        import main
        tickers = [weight.code for weight in main.weights.values()]
        shares = get_shares(client, tickers)
        save_prices(get_prices(client, shares))


if __name__ == "__main__":
    main_fun()
