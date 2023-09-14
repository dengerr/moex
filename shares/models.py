from django.contrib.auth.models import User
from django.db import models


class Share(models.Model):
    ticker = models.CharField(max_length=8, unique=True)
    short_name = models.CharField(max_length=64)

    @classmethod
    def all_tickers_as_dict(cls):
        return dict(cls.objects.all().values_list('ticker', 'short_name'))

    @classmethod
    def add_new_tickers(cls, tickers: set):
        db_tickers = set(cls.objects.all().values_list('ticker', flat=True))
        for ticker in tickers - db_tickers:
            cls.objects.create(ticker=ticker, short_name=ticker)

    def __str__(self):
        return self.ticker

    @classmethod
    def update_empty_names(cls, tinkoff_shares: dict):
        ticker_name_mapping = {
            share.ticker: share.name
            for share in tinkoff_shares.values()
        }
        for ticker, short_name in cls.all_tickers_as_dict().items():
            if ticker == short_name:
                cls.objects.filter(ticker=ticker).update(
                    short_name=ticker_name_mapping[ticker],
                )


class Briefcase(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='briefcases')
    shares = models.JSONField(default=dict, blank=True)
    favorites = models.TextField(default='', blank=True)
    ignored = models.TextField(default='', blank=True)
    capital = models.PositiveBigIntegerField(default=1000000)
    strategy = models.ForeignKey('Strategy', on_delete=models.SET_NULL, null=True, blank=True)

    @property
    def my_strategy(self):
        return self.strategy or Strategy.objects.filter(name='MOEX 2023').first()

    @classmethod
    def get_for_user(cls, user):
        return user.briefcases.first() or user.briefcases.create()

    def __str__(self):
        return self.user.email


class Strategy(models.Model):
    name = models.CharField(max_length=64, unique=True)
    weights_json = models.JSONField(default=dict)

    def __str__(self):
        return self.name

    @classmethod
    def names(cls):
        return cls.objects.all().values_list('name', flat=True)


class SharePriceBlock(models.Model):
    dt = models.DateTimeField(auto_now_add=True)
    source = models.CharField(max_length=64)
    price_map = models.JSONField()

    def __str__(self):
        return f'{self.dt} {self.source}'

    @classmethod
    def last_prices(cls):
        return dict(cls.objects.all().order_by('-dt')[0].price_map)
