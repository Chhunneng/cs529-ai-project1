from __future__ import annotations

from pydantic import BaseModel, Field


class HeaderLink(BaseModel):
    label: str
    url: str


class Header(BaseModel):
    full_name: str
    email: str
    phone: str
    location: str
    links: list[HeaderLink] = Field(default_factory=list)


class ExperienceItem(BaseModel):
    title: str
    company: str
    location: str
    start: str
    end: str
    bullets: list[str]


class EducationItem(BaseModel):
    school: str
    degree: str
    start: str
    end: str


class ResumeFillAtsV1(BaseModel):
    header: Header
    summary: str
    experience: list[ExperienceItem]
    education: list[EducationItem]
    skills: list[str]
