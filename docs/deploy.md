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
git archive main -o /tmp/caiame-deploy.tar && scp /tmp/caiame-deploy.tar caiame-hetzner:/tmp/
ssh caiame-hetzner 'set -e
rm -rf /tmp/caiame-new && mkdir -p /tmp/caiame-new
tar -xf /tmp/caiame-deploy.tar -C /tmp/caiame-new
rsync -a --delete \
  --exclude ".env" --exclude ".env.bak-*" --exclude "acme-webroot/" --exclude "backup-age.key" \
  /tmp/caiame-new/ /opt/caiame/
rm -rf /tmp/caiame-new /tmp/caiame-deploy.tar'
```

**Через промежуточный каталог и `rsync --delete`, а не `tar -x` прямо в `/opt/caiame`.**
Распаковка поверх только добавляет и перезаписывает: файл, удалённый из репозитория,
остаётся на сервере навсегда. Так там прожили полтора десятка обложек от старого каталога
и — что хуже — фотография, которую убрали из-за водяного знака: в базе стоял новый адрес,
а по старому сервер продолжал её отдавать.

Исключения — это то, что живёт только на сервере: секреты, их резервные копии, каталог
челленджа Let's Encrypt и ключ шифрования бэкапов. Всё остальное приводится к тому, что
лежит в `main`.

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
docker compose -f docker-compose.prod.yml build api web
docker compose -f docker-compose.prod.yml run --rm api alembic upgrade head
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml run --rm api python scripts/seed.py
```

**Порядок здесь важен, и не тот, который кажется.** Сборка идёт первой: `run --rm api`
запускает существующий образ, и миграция до сборки накатывает не то, что вы только что
залили, а то, что лежало здесь до вас. Вывод при этом выглядит успешным — просто новых
миграций в старом образе нет.

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

## Место на диске

Две вещи растут сами и обе кончаются одинаково — «сайт лёг, потому что кончился диск».

Логи контейнеров ограничены в `docker-compose.prod.yml`: 10 МБ на файл, три файла на
сервис. Это несколько дней истории — достаточно, чтобы разобрать вчерашнюю поломку,
и не настолько, чтобы съесть раздел.

Кэш сборки растёт с каждым выкатом, и его убирает еженедельный таймер:

```bash
sudo cp /opt/caiame/ops/housekeeping/caiame-housekeeping.{service,timer} /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now caiame-housekeeping.timer
```

Убирается только кэш старше недели и висячие образы. Предыдущий тег остаётся на месте:
это то, на что откатываются, когда новый образ оказался хуже старого. Посмотреть, сколько
занято сейчас, — `docker system df`.

## Что открыто наружу

Только 80-й порт контейнера `web`. Postgres и Redis портов не публикуют вообще и доступны
лишь изнутри сети compose.
