from django.db import migrations

shares_dict = {
    'SBER': 'Сбербанк об.', 'SBERP': 'Сбербанк прив.', 'LKOH': 'ЛУКОЙЛ', 'GAZP': 'Газпром', 'GMKN': 'ГМК "Норникель"',
    'NVTK': 'НОВАТЭК', 'YNDX': 'Яндекс', 'ROSN': 'Роснефть', 'SNGS': 'Сургутнефтегаз об.',
    'SNGSP': 'Сургутнефтегаз прив.', 'TATN': 'Татнефть об.', 'TATNP': 'Татнефть прив.', 'TCSG': 'ТКС Групп (Тинькофф)',
    'PLZL': 'Полюс', 'MTSS': 'МТС', 'MGNT': 'Магнит', 'PHOR': 'ФосАгро', 'CHMF': 'Северсталь', 'POLY': 'Полиметалл',
    'NLMK': 'НЛМК', 'IRAO': 'Интер РАО', 'ALRS': 'АЛРОСА', 'PIKK': 'Группа Компаний ПИК', 'FIVE': 'Икс 5 Ритейл Груп',
    'MOEX': 'Московская Биржа', 'RUAL': 'РУСАЛ', 'VTBR': 'Банк ВТБ', 'OZON': 'Озон', 'MAGN': 'ММК',
    'RTKM': 'Ростелеком об.', 'TRNFP': 'Транснефть', 'VKCO': 'VK', 'CBOM': 'Московский Кредитный Банк (МКБ)',
    'AFKS': 'АФК "Система"', 'AFLT': 'Аэрофлот', 'HYDR': 'РусГидро', 'ENPG': 'En+', 'GLTR': 'Глобалтранс',
    'FIXP': 'Fix Price', 'AGRO': 'Русагро', 'BSPB': 'Банк Санкт-Петербург', 'RASP': 'Распадская', 'ELFV': 'ELFV',
    'CHMK': 'ЧМК', 'MRKP': 'MRKP', 'RENI': 'Ренессанс', 'FEES': 'FEES', 'MRKC': 'MRKC', 'BANEP': 'BANEP',
    'NKNCP': 'NKNCP', 'SIBN': 'SIBN', 'MVID': 'МВидео', 'LSRG': 'LSRG', 'RNFT': 'Русснефть', 'SMLT': 'Самолет'}

last_prices = {
    'SBER': {'price': 256.96, 'lotsize': 10}, 'SBERP': {'price': 256.55, 'lotsize': 10},
    'LKOH': {'price': 6636.0, 'lotsize': 1}, 'GAZP': {'price': 175.98, 'lotsize': 10},
    'GMKN': {'price': 16520.0, 'lotsize': 1}, 'NVTK': {'price': 1655.6, 'lotsize': 1},
    'YNDX': {'price': 2589.2, 'lotsize': 1}, 'ROSN': {'price': 561.7, 'lotsize': 1},
    'SNGS': {'price': 31.03, 'lotsize': 100}, 'SNGSP': {'price': 48.45, 'lotsize': 100},
    'TATN': {'price': 599.9, 'lotsize': 1}, 'TATNP': {'price': 588.2, 'lotsize': 1},
    'TCSG': {'price': 3493.0, 'lotsize': 1}, 'PLZL': {'price': 11457.0, 'lotsize': 1},
    'MTSS': {'price': 281.9, 'lotsize': 10}, 'MGNT': {'price': 5724.0, 'lotsize': 1},
    'PHOR': {'price': 7194.0, 'lotsize': 1}, 'CHMF': {'price': 1317.4, 'lotsize': 1},
    'POLY': {'price': 556.4, 'lotsize': 1}, 'NLMK': {'price': 187.08, 'lotsize': 10},
    'IRAO': {'price': 4.392, 'lotsize': 100}, 'ALRS': {'price': 79.76, 'lotsize': 10},
    'PIKK': {'price': 799.8, 'lotsize': 1}, 'FIVE': {'price': 2275.0, 'lotsize': 1},
    'MOEX': {'price': 167.12, 'lotsize': 10}, 'RUAL': {'price': 42.535, 'lotsize': 10},
    'VTBR': {'price': 0.02715, 'lotsize': 10000}, 'OZON': {'price': 2748.5, 'lotsize': 1},
    'MAGN': {'price': 51.49, 'lotsize': 10}, 'RTKM': {'price': 76.78, 'lotsize': 10},
    'TRNFP': {'price': 138450.0, 'lotsize': 1}, 'VKCO': {'price': 719.8, 'lotsize': 1},
    'CBOM': {'price': 6.791, 'lotsize': 100}, 'AFKS': {'price': 17.875, 'lotsize': 100},
    'AFLT': {'price': 42.06, 'lotsize': 10}, 'HYDR': {'price': 0.9645, 'lotsize': 1000},
    'ENPG': {'price': 530.2, 'lotsize': 1}, 'GLTR': {'price': 683.45, 'lotsize': 1},
    'FIXP': {'price': 404.7, 'lotsize': 1}, 'AGRO': {'price': 1283.2, 'lotsize': 1},
    'BSPB': {'price': 302.21, 'lotsize': 10}, 'RASP': {'price': 348.1, 'lotsize': 10},
    'ELFV': {'price': 0.8148, 'lotsize': 1000}, 'CHMK': {'price': 12400.0, 'lotsize': 1},
    'MRKP': {'price': 0.3579, 'lotsize': 10000}, 'RENI': {'price': 111.02, 'lotsize': 10},
    'FEES': {'price': 0.13252, 'lotsize': 10000}, 'MRKC': {'price': 0.582, 'lotsize': 1000},
    'BANEP': {'price': 1416.5, 'lotsize': 1}, 'NKNCP': {'price': 88.9, 'lotsize': 10},
    'SIBN': {'price': 651.3, 'lotsize': 1}, 'MVID': {'price': 192.0, 'lotsize': 1},
    'LSRG': {'price': 742.4, 'lotsize': 1}, 'RNFT': {'price': 181.9, 'lotsize': 1},
    'SMLT': {'price': 3841.0, 'lotsize': 1}}

weight_dict = {
    'SBER': 15.3, 'SBERP': 1.93, 'LKOH': 16.44, 'GAZP': 12.85, 'GMKN': 5.66, 'NVTK': 4.88, 'YNDX': 4.04, 'ROSN': 3.84,
    'SNGS': 1.9, 'SNGSP': 1.34, 'TATN': 2.97, 'TATNP': 0.63, 'TCSG': 2.56, 'PLZL': 2.32, 'MTSS': 1.93, 'MGNT': 1.82,
    'PHOR': 1.63, 'CHMF': 1.48, 'POLY': 1.37, 'NLMK': 1.33, 'IRAO': 1.31, 'ALRS': 1.26, 'PIKK': 1.11, 'FIVE': 1.09,
    'MOEX': 1.08, 'RUAL': 0.93, 'VTBR': 0.93, 'OZON': 0.9, 'MAGN': 0.79, 'RTKM': 0.6, 'TRNFP': 0.58, 'VKCO': 0.46,
    'CBOM': 0.45, 'AFKS': 0.43, 'AFLT': 0.39, 'HYDR': 0.36, 'ENPG': 0.3, 'GLTR': 0.29, 'FIXP': 0.27, 'AGRO': 0.27}


def code(apps, schema_editor):
    Share = apps.get_model("shares", "Share")
    Strategy = apps.get_model("shares", "Strategy")
    SharePriceBlock = apps.get_model("shares", "SharePriceBlock")

    for ticker, short_name in shares_dict.items():
        Share.objects.create(ticker=ticker, short_name=short_name)

    Strategy.objects.create(name='MOEX 2022', weights_json=weight_dict)
    SharePriceBlock.objects.create(source='init', price_map=last_prices)


def reverse_code(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('shares', '0002_alter_briefcase_favorites_alter_briefcase_ignored_and_more'),
    ]

    operations = [
        migrations.RunPython(code, reverse_code),
    ]
