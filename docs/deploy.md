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
DOMAIN=caiame.org
COOKIE_SECURE=true
CORS_ORIGINS=["https://caiame.org"]
CONF
```

## Сертификат

Выдаётся через webroot, без остановки сайта — nginx уже отдаёт путь челленджа по HTTP:

```bash
certbot certonly --webroot -w /opt/caiame/acme-webroot -d caiame.org -d www.caiame.org
```

Продление делает системный таймер certbot. Чтобы nginx подхватил новый сертификат, стоит
хук перезагрузки в `/etc/letsencrypt/renewal-hooks/deploy/`. Проверить всё целиком:

```bash
certbot renew --dry-run
```

`COOKIE_SECURE=true` требует HTTPS: без него браузер откажется хранить cookie с
refresh-токеном и никто не сможет остаться в системе.

## Запуск и обновление

```bash
cd /opt/caiame
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml run --rm api alembic upgrade head
docker compose -f docker-compose.prod.yml run --rm api python scripts/seed.py
```

Миграции запускаются отдельным шагом, а не при старте контейнера: так их видно в выводе
выката, и они не выполняются повторно каждым перезапуском.

## Резервные копии

Описаны отдельно — `docs/backups.md`.

## Что открыто наружу

Только 80-й порт контейнера `web`. Postgres и Redis портов не публикуют вообще и доступны
лишь изнутри сети compose.
