push-dev:
	git add .
	git commit -m $(mes)
	git push origin dev

pull-dev:
	git pull origin dev

start:
	docker compose down && docker compose up --build
build:
	docker compose build
up:
	docker compose up
down:
	docker compose up
down-v:
	docker compose down -v

