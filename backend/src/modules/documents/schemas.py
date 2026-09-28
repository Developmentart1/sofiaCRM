"""Document Pydantic schemas — mirror the frontend ``Document`` type.

The frontend ``Document`` has: id, name (=filename), mime_type, size
(=size_bytes), url (download path), contact/opportunity/company ids + names,
uploaded_by_id + name, folder, created_at.
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    mime_type: str | None = None
    size: int
    url: str
    contact_id: str | None = None
    contact_name: str | None = None
    opportunity_id: str | None = None
    opportunity_name: str | None = None
    company_id: str | None = None
    company_name: str | None = None
    uploaded_by_id: str
    uploaded_by_name: str | None = None
    folder: str | None = None
    created_at: datetime
