import tink
from shares import models


def update_prices() -> None:
    tickers = list(models.Share.all_tickers_as_dict().keys())
    with tink.Client(tink.TOKEN) as client:
        shares = tink.get_shares(client, tickers)
        price_map = tink.get_prices(client, shares)
    models.Share.update_empty_names(shares)
    models.SharePriceBlock.objects.create(
        source='tinkoff',
        price_map=price_map,
    )
