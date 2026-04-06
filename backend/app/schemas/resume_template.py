from datetime import datetime

from pydantic import BaseModel


class ResumeTemplateListItem(BaseModel):
    id: str
    name: str
    storage_path: str
    created_at: datetime


class ResumeTemplateDetail(BaseModel):
    id: str
    name: str
    storage_path: str
    schema_json: dict
    created_at: datetime
