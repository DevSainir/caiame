# Выкат

Один сервер, один `docker compose`. Ничего, кроме Docker, на хосте не нужно.

## Первый раз

```bash
ssh caiame-hetzner
apt-get update && apt-get install -y docker.io docker-compose-v2
systemctl enable --now docker
mkdir -p /opt/caiame
```

Код заливается с рабочей машины экспортом из git — так на сервер попадают ровно
закоммиченные файлы, без `node_modules`, `.venv` и локального `.env`:

```bash
git archive main | ssh caiame-hetzner 'tar -x -C /opt/caiame'
```

Секреты создаются **на сервере** и в репозиторий не попадают:

```bash
ssh caiame-hetzner 'cat > /opt/caiame/.env' <<CONF
POSTGRES_PASSWORD=$(openssl rand -hex 24)
JWT_SECRET=$(openssl rand -hex 32)
COOKIE_SECURE=false
CORS_ORIGINS=["http://<адрес сервера>"]
CONF
```

`COOKIE_SECURE=false` — временно, пока сайт живёт по HTTP. Как только появится домен и
сертификат, значение переводится в `true`: без этого cookie с refresh-токеном ходит по
сети открытым текстом.

## Запуск и обновление

```bash
cd /opt/caiame
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml run --rm api alembic upgrade head
docker compose -f docker-compose.prod.yml run --rm api python scripts/seed.py
```

Миграции запускаются отдельным шагом, а не при старте контейнера: так их видно в выводе
выката, и они не выполняются повторно каждым перезапуском.

## Что открыто наружу

Только 80-й порт контейнера `web`. Postgres и Redis портов не публикуют вообще и доступны
лишь изнутри сети compose.
