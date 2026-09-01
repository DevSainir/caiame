# Targets that exist today. The list grows with the app, not ahead of it.
.DEFAULT_GOAL := help
PY := backend/.venv/bin

.PHONY: help figma-extract tokens tailwind design covers lint-tokens db migrate seed api web \
        backup-verify test-fast test-integration lint typecheck audit hooks \
        reset-catalog reseed admin test-e2e

help: ## Показать список целей
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

figma-extract: ## Скачать макет и собрать design-audit.json (--refresh для перекачки)
	node tools/figma-extract/index.mjs --page "profile" --root-width 1440

tokens: ## design-audit.json -> tokens.json + docs/tokens-mapping.md
	node tools/design-tokens/build.mjs

tailwind: ## tokens.json -> frontend/tailwind.config.js
	node tools/design-tokens/tailwind.mjs

covers: ## Перегенерировать обложки-заглушки курсов из палитры
	node tools/covers/generate.mjs

design: tokens tailwind ## Пересобрать токены и конфиг из текущего аудита

db: ## Поднять Postgres и Redis в docker (host-порты 5433 и 6380)
	docker compose up -d db redis

migrate: ## Накатить миграции
	cd backend && .venv/bin/alembic upgrade head

backup-verify: ## Проверить восстановлением последнюю копию (запускается на сервере)
	cd /opt/caiame && PYTHONPATH=ops/backup python3 ops/backup/backup.py --verify

seed: ## Заполнить базу каталогом
	cd backend && .venv/bin/python scripts/seed.py

admin: ## Завести администратора: make admin EMAIL=you@example.org (пароль спросит)
	cd backend && .venv/bin/python scripts/grant_admin.py $(EMAIL)

reset-catalog: ## Стереть каталог целиком (курсы, программы, отзывы, прогресс)
	cd backend && .venv/bin/python scripts/reset_catalog.py

reseed: reset-catalog seed ## Переложить каталог заново: стереть и засеять

api: ## Запустить бэкенд на :8001 (8000 занят чужим контейнером)
	cd backend && PYTHONPATH=src .venv/bin/uvicorn main:app --reload --port 8001

web: ## Запустить фронтенд на :5173
	npm run dev --prefix frontend

lint-tokens: ## Проверить вёрстку на произвольные значения и цвета вне шкалы
	cd frontend && npm run lint:tokens:self-test && npm run lint:tokens

test-fast: ## Юнит и компонентные тесты бэкенда, юнит фронтенда — гейт перед коммитом
	cd backend && .venv/bin/pytest -q -m "unit or component"
	npm test --prefix frontend

test-e2e: ## Сценарии через браузер: нужен поднятый API (make api) и база
	npx playwright test

test-integration: ## Тесты против настоящего Postgres
	cd backend && .venv/bin/pytest -q -m integration

lint: lint-tokens ## ruff, eslint, prettier и линтер токенов
	cd backend && .venv/bin/ruff check . && .venv/bin/ruff format --check .
	backend/.venv/bin/ruff check ops && backend/.venv/bin/ruff format --check ops
	npm run lint --prefix frontend
	npm run format:check --prefix frontend

typecheck: ## mypy --strict
	cd backend && .venv/bin/mypy src scripts tests

audit: ## Проверить зависимости на известные уязвимости
	cd backend && uv run --with pip-audit pip-audit --skip-editable

hooks: ## Поставить pre-commit (делается один раз после клона)
	pre-commit install
	pre-commit run --all-files
