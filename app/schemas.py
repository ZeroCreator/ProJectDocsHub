from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import List, Optional
from app.models import DocType


class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(ProjectBase):
    name: Optional[str] = None
    description: Optional[str] = None


class DocumentItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    document_id: int
    title: Optional[str] = None
    item_type: DocType
    url: Optional[str] = None
    file_path: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    category: Optional[str] = None
    sort_order: int = 0
    created_at: datetime


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    section_id: Optional[int] = None
    title: str
    category: Optional[str] = None
    sort_order: int = 0
    created_at: datetime
    updated_at: datetime
    items: List[DocumentItemOut] = []


class SectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    name: str
    sort_order: int = 0
    created_at: datetime
    documents: List[DocumentOut] = []


class SectionCreate(BaseModel):
    name: str


class SectionUpdate(BaseModel):
    name: Optional[str] = None


class DocumentCreate(BaseModel):
    title: str
    category: Optional[str] = None


class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    section_id: Optional[int] = None


class DocumentItemCreate(BaseModel):
    item_type: DocType
    url: Optional[str] = None


class DocumentItemUpdate(BaseModel):
    item_type: Optional[DocType] = None
    url: Optional[str] = None


class ReorderRequest(BaseModel):
    document_ids: List[int]


class SectionReorderRequest(BaseModel):
    section_ids: List[int]


class ProjectOut(ProjectBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime
    documents: List[DocumentOut] = []
    sections: List[SectionOut] = []


class ProjectDetailOut(ProjectOut):
    pass
