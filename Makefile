default: update main

main:
	python3 main.py
all:
	python3 main.py all

fav:
	python3 main.py fav

update:
	wget https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities.json -O securities.json
