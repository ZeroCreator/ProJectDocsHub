"""
ProJectDocsHub — веб-приложение для сбора и управления документами проектов.

Author: Shkola Olga
"""
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
from sqlalchemy import text

from app.database import engine, Base
from app.routers import projects, documents
from app.config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Migration: split Document (old flat model) into Document (group) + DocumentItem
        tables = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        table_names = [r[0] for r in tables.fetchall()]

        if "document_items" not in table_names:
            # Create items table manually if SQLAlchemy hasn't yet
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS document_items (
                    id INTEGER PRIMARY KEY,
                    document_id INTEGER NOT NULL,
                    item_type VARCHAR(10) NOT NULL,
                    url TEXT,
                    file_path VARCHAR(500),
                    file_name VARCHAR(255),
                    file_size INTEGER,
                    mime_type VARCHAR(100),
                    sort_order INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
                )
            """))

        # Check if old flat schema still exists (has doc_type column in documents)
        doc_cols = await conn.execute(text("PRAGMA table_info(documents)"))
        doc_column_names = [r[1] for r in doc_cols.fetchall()]

        if "doc_type" in doc_column_names:
            # Migrate old flat documents into group + items
            await conn.execute(text("""
                INSERT INTO document_items (document_id, item_type, url, file_path, file_name, file_size, mime_type, sort_order, created_at)
                SELECT id, doc_type, url, file_path, file_name, file_size, mime_type, sort_order, created_at FROM documents
            """))

            # Rebuild documents table without old flat columns
            await conn.execute(text("ALTER TABLE documents RENAME TO documents_old"))
            await conn.execute(text("""
                CREATE TABLE documents (
                    id INTEGER PRIMARY KEY,
                    project_id INTEGER NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    category VARCHAR(50),
                    sort_order INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                )
            """))
            await conn.execute(text("""
                INSERT INTO documents (id, project_id, title, category, sort_order, created_at, updated_at)
                SELECT id, project_id, title, category, sort_order, created_at, updated_at FROM documents_old
            """))
            await conn.execute(text("DROP TABLE documents_old"))

            # Fix sequence only if sqlite_sequence table exists (AUTOINCREMENT tables)
            seq_tables = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='sqlite_sequence'"))
            if seq_tables.fetchone():
                await conn.execute(text("""
                    INSERT OR REPLACE INTO sqlite_sequence (name, seq)
                    SELECT 'documents', COALESCE(MAX(id), 0) FROM documents
                """))

        # Fix broken FK: if document_items still references documents_old, rebuild it
        fk_info = await conn.execute(text("PRAGMA foreign_key_list(document_items)"))
        for row in fk_info.fetchall():
            if row[2] == "documents_old":
                await conn.execute(text("""
                    CREATE TABLE document_items_new (
                        id INTEGER PRIMARY KEY,
                        document_id INTEGER NOT NULL,
                        item_type VARCHAR(10) NOT NULL,
                        url TEXT,
                        file_path VARCHAR(500),
                        file_name VARCHAR(255),
                        file_size INTEGER,
                        mime_type VARCHAR(100),
                        sort_order INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
                    )
                """))
                await conn.execute(text("""
                    INSERT INTO document_items_new (id, document_id, item_type, url, file_path, file_name, file_size, mime_type, sort_order, created_at)
                    SELECT id, document_id, item_type, url, file_path, file_name, file_size, mime_type, sort_order, created_at FROM document_items
                """))
                await conn.execute(text("DROP TABLE document_items"))
                await conn.execute(text("ALTER TABLE document_items_new RENAME TO document_items"))
                break

        # Add missing columns to document_items
        item_cols = await conn.execute(text("PRAGMA table_info(document_items)"))
        item_column_names = [r[1] for r in item_cols.fetchall()]
        if "category" not in item_column_names:
            await conn.execute(text("ALTER TABLE document_items ADD COLUMN category VARCHAR(50)"))
        if "title" not in item_column_names:
            await conn.execute(text("ALTER TABLE document_items ADD COLUMN title VARCHAR(255)"))

        # Cleanup old backup table if still exists
        old_tables = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='documents_old'"))
        if old_tables.fetchone():
            await conn.execute(text("DROP TABLE documents_old"))

        # Migration: add sections support
        if "sections" not in table_names:
            await conn.execute(text("""
                CREATE TABLE sections (
                    id INTEGER PRIMARY KEY,
                    project_id INTEGER NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    sort_order INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                )
            """))
        doc_cols2 = await conn.execute(text("PRAGMA table_info(documents)"))
        doc_col_names2 = [r[1] for r in doc_cols2.fetchall()]
        if "section_id" not in doc_col_names2:
            await conn.execute(text("ALTER TABLE documents ADD COLUMN section_id INTEGER"))
    yield
    await engine.dispose()


app = FastAPI(title=settings.app_name, lifespan=lifespan)

# Static & templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Routers
app.include_router(projects.router)
app.include_router(documents.router)
app.include_router(documents.section_router)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "title": settings.app_name})


@app.get("/projects/{project_id}", response_class=HTMLResponse)
async def project_page(request: Request, project_id: int):
    return templates.TemplateResponse("project.html", {"request": request, "project_id": project_id, "title": settings.app_name})
