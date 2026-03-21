.PHONY: install-frontend install-backend frontend-dev frontend-build backend-dev backend-migrate backend-check infra-up infra-down

install-frontend:
	cd apps/frontend && npm install

install-backend:
	cd apps/backend && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt

frontend-dev:
	cd apps/frontend && npm run dev

frontend-build:
	cd apps/frontend && npm run build

backend-dev:
	cd apps/backend && . .venv/bin/activate && python manage.py runserver 0.0.0.0:8000

backend-migrate:
	cd apps/backend && . .venv/bin/activate && python manage.py migrate

backend-check:
	cd apps/backend && . .venv/bin/activate && python manage.py check

infra-up:
	docker compose up -d postgres redis

infra-down:
	docker compose down
