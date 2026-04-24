"""Pydantic schemas para Relatórios Primordial."""
from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class ReportFormat(str, Enum):
    CSV = "csv"
    JSON = "json"
    XML = "xml"
    PDF = "pdf"


DataType = Literal["bruto", "agregado", "metrica"]


class ReportFilters(BaseModel):
    """Filtros aplicados ao relatório do mês atual.

    - `bruto`:    requer `fields` (≥1)
    - `agregado`: requer `group_by`
    - `metrica`:  ignora `fields`/`group_by`
    """

    data_type: DataType = Field(..., description="bruto | agregado | metrica")
    fields: list[str] = Field(default_factory=list, max_length=20)
    limit: int = Field(default=50, ge=1, le=1000)
    group_by: str | None = Field(default=None, max_length=40)
    status: list[str] | None = Field(default=None, max_length=10)
    convenio: list[str] | None = Field(default=None, max_length=20)

    @field_validator("fields", mode="before")
    @classmethod
    def _strip_fields(cls, v):
        if not v:
            return []
        if not isinstance(v, list):
            raise ValueError("fields deve ser uma lista de strings.")
        out: list[str] = []
        for f in v:
            if not isinstance(f, str):
                raise ValueError("Cada campo deve ser string.")
            f2 = f.strip().lower()
            if not f2 or len(f2) > 40:
                raise ValueError("Nome de campo inválido.")
            out.append(f2)
        # remove duplicatas preservando ordem
        seen = set()
        return [f for f in out if not (f in seen or seen.add(f))]

    @field_validator("group_by", mode="before")
    @classmethod
    def _norm_group_by(cls, v):
        if v is None or v == "":
            return None
        if not isinstance(v, str) or len(v) > 40:
            raise ValueError("group_by inválido.")
        return v.strip().lower()

    @field_validator("status", "convenio", mode="before")
    @classmethod
    def _norm_string_list(cls, v):
        if v is None:
            return None
        if not isinstance(v, list):
            raise ValueError("Filtro deve ser lista de strings.")
        out: list[str] = []
        for s in v:
            if not isinstance(s, str):
                raise ValueError("Filtro deve conter apenas strings.")
            s2 = s.strip()
            if not s2 or len(s2) > 80:
                raise ValueError("Valor de filtro inválido.")
            out.append(s2)
        return out or None

    @model_validator(mode="after")
    def _check_consistency(self):
        if self.data_type == "bruto" and not self.fields:
            raise ValueError(
                "Para data_type='bruto' selecione pelo menos um campo em 'fields'."
            )
        if self.data_type == "agregado" and not self.group_by:
            raise ValueError(
                "Para data_type='agregado' informe 'group_by'."
            )
        return self
