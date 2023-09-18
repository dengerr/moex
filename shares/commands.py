from operator import itemgetter

import tink
from shares import models


def update_prices() -> None:
    values = [(ticker, str(uid), lotsize) for ticker, uid, lotsize in
              models.Share.objects.all().values_list('ticker', 'instrument_uid', 'lotsize')]
    tickers = tuple(map(itemgetter(0), values))
    uids = tuple(map(itemgetter(1), values))
    lotsizes = tuple(map(itemgetter(2), values))
    with tink.Client(tink.TOKEN) as client:
        price_map = tink.get_prices_by_uid(client, tickers, uids, lotsizes)
    models.SharePriceBlock.objects.create(
        source='tinkoff',
        price_map=price_map,
    )


def fill_figi() -> None:
    models.Share.fill_figi()
