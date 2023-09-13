default: update

update:
	wget https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities.json -O securities.json

securities.json: update

dev:
	./manage.py runserver --settings=moex.local_settings

start:
	DJANGO_SETTINGS_MODULE=moex.production gunicorn -w 1 'moex.wsgi:application' -b 0.0.0.0:8456

install:
	pip install -r requirements.txt
	./manage.py migrate
	./manage.py collectstatic --noinput
