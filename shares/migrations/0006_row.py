# Generated by Django 4.2.5 on 2023-09-14 12:19

from django.db import migrations, models
import django.db.models.deletion


def code(apps, schema_editor):
    Share = apps.get_model("shares", "Share")
    Briefcase = apps.get_model("shares", "Briefcase")
    Row = apps.get_model("shares", "Row")
    for briefcase in Briefcase.objects.all():
        favorites = briefcase.favorites.split()
        ignored = briefcase.ignored.split()
        rows = [
            Row(
                briefcase=briefcase,
                share=(Share.objects.get_or_create(ticker=ticker))[0],
                is_favorite=ticker in favorites,
                is_ignored=ticker in ignored,
                count=count,
            ) for ticker, count in briefcase.shares.items()
        ]
        Row.objects.bulk_create(rows)


def reverse_code(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('shares', '0005_migrate_from_moex_sqlite'),
    ]

    operations = [
        migrations.CreateModel(
            name='Row',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_favorite', models.BooleanField(default=False)),
                ('is_ignored', models.BooleanField(default=False)),
                ('count', models.IntegerField(default=0)),
                ('description', models.TextField(blank=True, default='')),
                ('price_to_buy', models.DecimalField(decimal_places=18, max_digits=4, default='0.00')),
                ('price_target', models.DecimalField(decimal_places=18, max_digits=4, default='0.00')),
                ('briefcase', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rows',
                                                to='shares.briefcase')),
                ('share', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='shares.share')),
            ],
            options={
                'unique_together': {('briefcase', 'share')},
            },
        ),
        migrations.RunPython(code, reverse_code),
    ]
