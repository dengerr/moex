import json

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views import View

import tink
from main import UserBriefcase, WeightManager
from shares import models
from shares.utils import htmx_response


def get_user_briefcase(briefcase: models.Briefcase) -> UserBriefcase:
    weights_map = briefcase.my_strategy.weights_json
    shares_as_dict = models.Share.all_tickers_as_dict()
    last_prices = models.SharePriceBlock.last_prices()
    return UserBriefcase(
        WeightManager(shares_as_dict, last_prices, weights_map),
        briefcase.ignored.split(),
        briefcase.favorites.split(),
        briefcase.capital,
        briefcase.shares,
    )


class IndexView(View):
    def get(self, request, *args, **kwargs):
        briefcase = models.Briefcase.get_for_user(request.user)
        ub = get_user_briefcase(briefcase)

        templates = {
            'desktop': 'table.html',
            'mobile': 'table-mobile.html',
        }
        layout = request.COOKIES.get('layout', '')
        template = templates.get(layout, templates['mobile'])

        strategies = models.Strategy.objects.all()

        rows_qs = briefcase.rows.all().select_related('share')
        rows = {row.share.ticker: row for row in rows_qs}
        return htmx_response(
            request, template, ub=ub, rows=rows, strategies=strategies,
            show_target=request.GET.get('show_target'),
        )

    def post(self, request):
        user_briefcase = models.Briefcase.get_for_user(request.user)

        for k, v in request.POST.items():
            if k == 'capital':
                user_briefcase.capital = int(v)
                user_briefcase.save()
            elif k == 'toggle_fav':
                favs = user_briefcase.favorites.split()
                if v in favs:
                    favs.remove(v)
                else:
                    favs.append(v)
                user_briefcase.favorites = ' '.join(favs)
                user_briefcase.save()
            elif k == 'toggle_ign':
                ignored = user_briefcase.ignored.split()
                if v in ignored:
                    ignored.remove(v)
                elif not user_briefcase.shares.get(v):
                    ignored.append(v)
                user_briefcase.ignored = ' '.join(ignored)
                user_briefcase.save()
            else:
                user_briefcase.set_row_attr(k, 'count', v)
        return self.get(request)


@login_required
def set_row(request):
    briefcase: models.Briefcase = models.Briefcase.get_for_user(request.user)
    for k, value in request.POST.items():
        attr, ticker = k.split('-')
        briefcase.set_row_attr(ticker, attr, value)
    return IndexView().get(request)


@login_required
def settings_view(request):
    layout = request.GET.get('layout', '')
    response = redirect('/')
    if layout in ('desktop', 'mobile'):
        response.set_cookie('layout', layout)
    return response


@login_required
def use_strategy(request, id):
    new_strategy = models.Strategy.objects.get(id=id)
    briefcase = models.Briefcase.get_for_user(request.user)
    briefcase.strategy = new_strategy
    briefcase.save()
    return IndexView().get(request)


class StrategyView(View):
    def get(self, request):
        name = request.GET.get('name')
        # action: use this strategy
        if request.GET.get('use'):
            new_strategy = models.Strategy.objects.get(name=request.GET.get('use'))
            briefcase = models.Briefcase.get_for_user(request.user)
            briefcase.strategy = new_strategy
            briefcase.save()
            return redirect('/')
        # show add form
        elif name == 'new':
            return render(request, 'weights_form.html', {'content': '', 'name': ''})
        # show edit form
        elif name:
            strategy = models.Strategy.objects.get(name=name)
            return render(request, 'weights_form.html', {
                'content': json.dumps(strategy.weights_json),
                'name': strategy.name,
            })
        # show only names
        else:
            weights_names = models.Strategy.names()
            return htmx_response(request, 'weights.html', weights_names=weights_names)

    # insert or update
    def post(self, request):
        content = json.loads(request.POST.get('content'))
        name = request.POST.get('name')
        if name and content:
            tickers = set(content.keys())
            models.Share.add_new_tickers(tickers)

            try:
                strategy = models.Strategy.objects.get(name=name)
            except models.Strategy.DoesNotExist:
                strategy = models.Strategy(name=name)
            strategy.weights_json = content
            strategy.save()
        else:
            return 'error'

        weights_names = models.Strategy.names()
        return htmx_response(request, 'weights.html', weights_names=weights_names)


@login_required
def update_prices_view(request):
    tickers = list(models.Share.all_tickers_as_dict().keys())
    with tink.Client(tink.TOKEN) as client:
        shares = tink.get_shares(client, tickers)
        price_map = tink.get_prices(client, shares)

    models.Share.update_empty_names(shares)

    models.SharePriceBlock.objects.create(
        source='tinkoff',
        price_map=price_map,
    )

    return redirect('/')
