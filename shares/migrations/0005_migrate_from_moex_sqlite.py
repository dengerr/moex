# Generated by Django 4.2.5 on 2023-09-13 14:14
import json
import os.path
import sqlite3

from django.db import migrations


def get_data_from_flask_version(filename, apps):
    db = sqlite3.connect(filename)
    cursor = db.cursor()

    Share = apps.get_model("shares", "Share")
    Strategy = apps.get_model("shares", "Strategy")
    SharePriceBlock = apps.get_model("shares", "SharePriceBlock")
    Briefcase = apps.get_model("shares", "Briefcase")
    User = apps.get_model("auth", "User")

    result = cursor.execute("SELECT ticker, short_name FROM shares").fetchall()
    current = set(Share.objects.all().values_list('ticker', flat=True))
    for ticker, short_name in result:
        if ticker not in current:
            Share.objects.create(ticker=ticker, short_name=short_name)

    result = cursor.execute("SELECT price_map FROM prices ORDER BY dt DESC LIMIT 1").fetchone()
    prices = json.loads(result[0]) if result else None
    SharePriceBlock.objects.create(source='from_flask', price_map=prices)

    result = cursor.execute("SELECT name, weights_json FROM weights").fetchall()
    for name, weights_json in result:
        if not Strategy.objects.filter(name=name).exists():
            Strategy.objects.create(name=name, weights_json=json.loads(weights_json))

    users = cursor.execute("SELECT * FROM users").fetchall()
    for email, is_active, is_available, secret, shares, favorites, ignored, capital, weight_name in users:
        user = User.objects.filter(email=email).first()
        if not user:
            user = User.objects.create(email=email, username=email)

        strategy = Strategy.objects.get(name=weight_name)

        Briefcase.objects.create(
            user=user,
            shares=json.loads(shares),
            favorites=favorites,
            ignored=ignored,
            capital=capital,
            strategy=strategy,
        )

    db.close()


def code(apps, schema_editor):
    filename = 'moex.sqlite'
    if os.path.exists(filename):
        get_data_from_flask_version(filename, apps)


def reverse_code(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('shares', '0004_alter_briefcase_favorites_alter_briefcase_ignored_and_more'),
    ]

    operations = [
        migrations.RunPython(code, reverse_code),
    ]
