# ProJect Docs Hub

Веб-приложение для сбора и управления документами и файлами проектов.

## Возможности

- **Проекты** — создавайте проекты и собирайте в них документы
- **Ссылки** — добавляйте ссылки на внешние ресурсы (Google Drive, Excel Online, Google Docs и т.д.)
- **Файлы** — загружайте файлы напрямую в приложение
- **Хранилище** — поддержка локального хранилища или S3 (MinIO, AWS S3, Yandex Cloud и др.)
- **Скачивание** — скачивайте загруженные файлы обратно (для S3 — через presigned URL, даже если бакет приватный)
- **Удаление** — удаляйте документы и проекты (файлы тоже удаляются из хранилища)

## Архитектура

```
app/
├── main.py           # Точка входа, lifespan, миграции, роутинг страниц
├── config.py         # Pydantic Settings (env-переменные)
├── database.py       # SQLAlchemy async engine + session
├── models.py         # ORM модели: Project, Section, Document, DocumentItem
├── schemas.py        # Pydantic схемы для валидации
├── storage.py        # Абстракция хранилища: LocalStorage / S3Storage
├── routers/
│   ├── projects.py   # CRUD проектов
│   └── documents.py  # CRUD разделов, групп, items, upload, download
├── templates/        # Jinja2 шаблоны
└── static/           # CSS + JS
```

### Стек

- **Backend**: FastAPI + SQLAlchemy 2.0 (async) + SQLite
- **Frontend**: Server-side rendering (Jinja2) + Bootstrap 5 + Vanilla JS
- **Storage**: локальная файловая система или S3-совместимое хранилище
- **Package Manager**: [uv](https://docs.astral.sh/uv/) — современный менеджер от создателей `ruff`

### Модель данных

**Project**
- `id`, `name`, `description`
- `created_at`, `updated_at`
- связи `sections` и `documents` (one-to-many, cascade delete)

**Section** (раздел / категория)
- `id`, `project_id`, `name`, `sort_order`
- связь `documents` (группы внутри раздела)

**Document** (группа)
- `id`, `project_id`, `section_id` (nullable)
- `title`, `category`, `sort_order`
- связь `items` (one-to-many, cascade delete)

**DocumentItem** (ссылка или файл внутри группы)
- `id`, `document_id`
- `item_type` (`link` | `file`), `title`
- `url` — для ссылок
- `file_path`, `file_name`, `file_size`, `mime_type` — для файлов

### Абстракция хранилища

`StorageBackend` — интерфейс с методами `save()`, `delete()`, `get_local_path()`, `get_download_url()`, `get_public_url()`.

Реализации:
- `LocalStorage` — сохраняет в `./data/uploads/`, отдаёт через `FileResponse`
- `S3Storage` — загружает в бакет S3, скачивание через **presigned URL** (даже для приватных бакетов)

Переключение через переменную окружения `STORAGE_TYPE=local` или `s3`.

## Установка и запуск

### Docker (рекомендуется для production и локального развёртывания)

```bash
# Production (без hot-reload)
docker compose up -d

# Development (с hot-reload, код пробрасывается из хоста)
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

Данные (SQLite + uploads) сохраняются в `./data/` на хосте.

Приложение доступно по адресу: http://localhost:8088

### Локальный запуск (без Docker)

Требуется [uv](https://docs.astral.sh/uv/getting-started/installation/):

```bash
# Автоматический запуск (uv сам создаст .venv, установит зависимости и запустит сервер)
uv run uvicorn app.main:app --host 0.0.0.0 --port 8088 --reload

# Или через скрипт
chmod +x run.sh
./run.sh
```

### Добавление dev-зависимостей

```bash
# Тесты и утилиты разработчика устанавливаются через группу dev
uv sync --group dev
```

## Подключение S3

Приложение поддерживает любое S3-совместимое хранилище. Для переключения на S3:

```bash
cp .env.example .env
# отредактируй .env
```

### Общие параметры

```env
STORAGE_TYPE=s3
S3_BUCKET_NAME=my-docs-bucket
S3_ACCESS_KEY_ID=YOUR_KEY
S3_SECRET_ACCESS_KEY=YOUR_SECRET
S3_REGION=ru-central1

# Endpoint URL (пустой для AWS)
S3_ENDPOINT_URL=https://storage.yandexcloud.net

# Path-style addressing (True для MinIO, False для облачных провайдеров)
S3_FORCE_PATH_STYLE=False

# Время жизни presigned-ссылки в секундах (по умолчанию 1 час)
S3_PRESIGNED_EXPIRES=3600
```

### Примеры для провайдеров

#### Yandex Cloud

```env
S3_ENDPOINT_URL=https://storage.yandexcloud.net
S3_REGION=ru-central1
S3_BUCKET_NAME=my-bucket
S3_ACCESS_KEY_ID=<идентификатор_ключа>
S3_SECRET_ACCESS_KEY=<секретный_ключ>
S3_FORCE_PATH_STYLE=False
```

Ключи создаются в [Yandex Cloud Console](https://console.cloud.yandex.ru/) → Сервисные аккаунты → Создать ключ доступа.

#### AWS S3

```env
S3_ENDPOINT_URL=              # оставь пустым!
S3_REGION=eu-west-1
S3_BUCKET_NAME=my-bucket
S3_ACCESS_KEY_ID=AKIA...
S3_SECRET_ACCESS_KEY=...
S3_FORCE_PATH_STYLE=False
```

Ключи — в AWS IAM → Users → Security credentials → Access keys.

#### MinIO (self-hosted / Docker)

```env
S3_ENDPOINT_URL=http://localhost:9000
S3_REGION=us-east-1
S3_BUCKET_NAME=projectdocs
S3_ACCESS_KEY_ID=minioadmin
S3_SECRET_ACCESS_KEY=minioadmin
S3_FORCE_PATH_STYLE=True
```

Запуск MinIO в Docker:

```bash
docker run -p 9000:9000 -p 9001:9001 \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin \
  minio/minio server /data --console-address ":9001"
```

Создай бакет через MinIO Console (http://localhost:9001) или `mc mb`.

#### Selectel

```env
S3_ENDPOINT_URL=https://s3.selcloud.ru
S3_REGION=ru-1
S3_BUCKET_NAME=my-bucket
S3_ACCESS_KEY_ID=...
S3_SECRET_ACCESS_KEY=...
S3_FORCE_PATH_STYLE=False
```

### Как это работает

1. **Загрузка**: файл через `boto3.upload_fileobj()` попадает в S3-бакет под уникальным ключом `uploads/{uuid}.{ext}`
2. **Скачивание**: приложение генерирует **presigned URL** через `generate_presigned_url()` с заголовком `Content-Disposition: attachment`. Это работает даже если бакет приватный — ссылка действует `S3_PRESIGNED_EXPIRES` секунд.
3. **Удаление**: при удалении документа из проекта файл удаляется из S3 через `delete_object()`.

## API Endpoints

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/projects` | Список проектов |
| POST | `/api/projects` | Создать проект |
| GET | `/api/projects/{id}` | Детали проекта |
| PATCH | `/api/projects/{id}` | Обновить проект |
| DELETE | `/api/projects/{id}` | Удалить проект (+ файлы из хранилища) |
| GET | `/api/projects/{id}/sections` | Разделы проекта |
| POST | `/api/projects/{id}/sections` | Создать раздел |
| PATCH | `/api/projects/{id}/sections/reorder` | Изменить порядок разделов |
| PATCH | `/api/projects/{id}/sections/{sec_id}` | Переименовать раздел |
| DELETE | `/api/projects/{id}/sections/{sec_id}` | Удалить раздел (группы переходят в "Без раздела") |
| GET | `/api/projects/{id}/documents` | Группы без раздела |
| POST | `/api/projects/{id}/documents` | Создать группу (form-data) |
| PATCH | `/api/projects/{id}/documents/{doc_id}` | Обновить группу / переместить в раздел |
| DELETE | `/api/projects/{id}/documents/{doc_id}` | Удалить группу (+ файлы из хранилища) |
| POST | `/api/projects/{id}/documents/{doc_id}/items` | Добавить ссылку или файл |
| PATCH | `/api/projects/{id}/documents/{doc_id}/items/{item_id}` | Редактировать item |
| DELETE | `/api/projects/{id}/documents/{doc_id}/items/{item_id}` | Удалить item (+ файл из хранилища) |
| GET | `/api/projects/{id}/documents/{doc_id}/items/{item_id}/download` | Скачать файл |
| GET | `/api/projects/{id}/documents/{doc_id}/items/{item_id}/preview` | Предпросмотр файла |

## Бэкапы

### Что бэкапить

Все данные хранятся в двух местах:
- `data/projectdocs.db` — база данных SQLite (проекты, разделы, группы, ссылки, метаданные файлов)
- `data/uploads/` — загруженные файлы

### Ручной бэкап

```bash
# В корне проекта
cd ~/ProJectDocsHub
tar -czvf backup_$(date +%Y%m%d_%H%M%S).tar.gz data/projectdocs.db data/uploads/
```

Получится архив вида `backup_20260520_143052.tar.gz`.

### Восстановление из бэкапа

```bash
# Распаковать в корень проекта
cd ~/ProJectDocsHub
tar -xzvf backup_20260520_143052.tar.gz
```

### Автоматический бэкап (cron)

Добавь в crontab:

```bash
# Каждый день в 3:00 утра
crontab -e
0 3 * * * cd /home/user/ProJectDocsHub && tar -czf /home/user/backups/projectdocs_$(date +\%Y\%m\%d).tar.gz data/projectdocs.db data/uploads/ >/dev/null 2>&1
```

### Бэкап при деплое на другой сервер

```bash
# На исходной машине
tar -czvf backup_$(date +%Y%m%d_%H%M%S).tar.gz data/projectdocs.db data/uploads/ .env

# На новом сервере
mkdir -p /opt/ProJectDocsHub && cd /opt/ProJectDocsHub
# Распакуй проект + данные
tar -xzvf deploy_20260520_143052.tar.gz
# Запуск
docker compose up -d --build
```

## Автор

**Shkola Olga**

## Лицензия

MIT
