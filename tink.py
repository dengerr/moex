from tinkoff.invest import Client
from tinkoff.invest.grpc.instruments_pb2 import INSTRUMENT_ID_TYPE_TICKER
from tinkoff.invest.utils import quotation_to_decimal

from main import PriceMap
from settings import TINKOFF_TOKEN

TOKEN = TINKOFF_TOKEN
CLASS_CODE = 'TQBR'
TICKERS = ['SBER', 'MOEX', 'ROSN', 'GMKN', 'LKOH']
Client = Client  # not autoremove import


def get_shares(client, tickers):
    # shares = client.instruments.shares()
    # shares = [inst for inst in shares.instruments if inst.ticker in tickers]
    shares = [
        client.instruments.share_by(
            id_type=INSTRUMENT_ID_TYPE_TICKER,
            class_code=CLASS_CODE,
            id=ticker,
        ).instrument
        for ticker in tickers]
    shares = [inst for inst in shares if inst.ticker in tickers]
    return {share.figi: share for share in shares}


def get_prices(client, shares) -> PriceMap:
    response = client.market_data.get_last_prices(
        figi=[share.figi for share in shares.values()])
    result = []
    for item in response.last_prices:
        result.append((shares[item.figi], quotation_to_decimal(item.price)))

    price_map = {
        share.ticker: {'price': float(price), 'lotsize': share.lot}
        for share, price in result}

    return price_map
