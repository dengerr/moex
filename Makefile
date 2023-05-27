default: update main

main:
	python3 main.py
all:
	python3 main.py all

fav:
	python3 main.py fav

update:
	wget https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities.json -O securities.json

securities.json: update

settings.py:
	python -c "import secrets; print(f'SECRET_KEY = b\'{secrets.token_urlsafe(16)}\'')" > settings.py

dev: settings.py securities.json
	flask --app application run --debug --reload

start: settings.py securities.json
	gunicorn -w 1 'application:app' -b 0.0.0.0:8456

install:
	pip install -r requirements.txt
