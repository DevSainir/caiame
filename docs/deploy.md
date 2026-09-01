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

## Администратор

`seed.py` в продакшене аккаунтов не создаёт — его пароль лежит в репозитории. Первый
администратор заводится отдельной командой, и пароль она спрашивает у терминала, а не
берёт из аргумента: аргумент остался бы в истории оболочки и в списке процессов.

```bash
cd /opt/caiame
docker compose -f docker-compose.prod.yml run --rm -it api python scripts/grant_admin.py you@example.org --name "Имя Фамилия"
```

Существующий аккаунт та же команда поднимает до администратора и пароль ему не трогает.
`--reset-password` задаёт новый и заодно гасит все живые сессии этого аккаунта: иначе
refresh-токен пережил бы пароль, под которым был выдан.

## Хранилище материалов

Видео и файлы лекций лежат в S3-совместимом хранилище, а не на диске приложения: контейнер
эфемерный, и всё загруженное в него исчезнет при первом же выкате.

Нужен **отдельный бакет** `caiame-private`, не тот, в котором лежат резервные копии. Он
закрыт целиком: наружу оттуда ведут только подписанные ссылки с коротким сроком жизни.
Заведён 1 сентября 2026. Публичный бакет под обложки появится вместе с самими обложками —
сейчас их рисует генератор и они лежат в сборке фронтенда.

Бакету нужен CORS на домен сайта: файл едет из браузера прямо туда, минуя приложение, и
без разрешённого источника браузер этот запрос не отправит. Настроен там же.

```json
[{ "AllowedOrigins": ["https://caiame.org"],
   "AllowedMethods": ["PUT", "GET", "HEAD"],
   "AllowedHeaders": ["*"], "MaxAgeSeconds": 3600 }]
```

Ключи доступа и адрес кладутся в серверный `.env` — переменные `MEDIA_S3_*` и
`MEDIA_BUCKET_*` из `.env.example`. Локально ничего заводить не нужно: `docker compose up`
поднимает MinIO и создаёт оба бакета сам.

## Резервные копии

Описаны отдельно — `docs/backups.md`.

## Что открыто наружу

Только 80-й порт контейнера `web`. Postgres и Redis портов не публикуют вообще и доступны
лишь изнутри сети compose.
