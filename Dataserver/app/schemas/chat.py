"""Modelos Pydantic da API + validators de segurança/limites."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.config import settings

_ALLOWED_CHART_TYPES = {"bar", "line", "pie", "donut", "doughnut"}


class RequisicaoChat(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversa_id: Optional[int] = None


class NovaConversa(BaseModel):
    titulo: Optional[str] = Field(default=None, max_length=200)


class RenomearConversa(BaseModel):
    titulo: str = Field(min_length=1, max_length=200)


class ChartDataIn(BaseModel):
    type: str = Field(min_length=1, max_length=20)
    title: Optional[str] = Field(default="", max_length=200)
    labels: list[Any] = Field(default_factory=list)
    values: list[Any] = Field(default_factory=list)

    @field_validator("type")
    @classmethod
    def _check_type(cls, v: str) -> str:
        v = (v or "").strip().lower()
        if v not in _ALLOWED_CHART_TYPES:
            raise ValueError(
                f"type deve ser um de {sorted(_ALLOWED_CHART_TYPES)}"
            )
        return v

    @field_validator("labels")
    @classmethod
    def _check_labels(cls, v: list[Any]) -> list[Any]:
        if len(v) > settings.chart_max_points:
            raise ValueError(
                f"labels excede o limite ({settings.chart_max_points})"
            )
        out: list[Any] = []
        for item in v:
            s = str(item)
            if len(s) > settings.chart_label_max_len:
                s = s[: settings.chart_label_max_len]
            out.append(s)
        return out

    @field_validator("values")
    @classmethod
    def _check_values(cls, v: list[Any]) -> list[Any]:
        if len(v) > settings.chart_max_points:
            raise ValueError(
                f"values excede o limite ({settings.chart_max_points})"
            )
        for item in v:
            if not isinstance(item, (int, float)) or isinstance(item, bool):
                raise ValueError("values deve conter apenas números")
        return v

    @model_validator(mode="after")
    def _check_lengths(self) -> "ChartDataIn":
        if self.labels and self.values and len(self.labels) != len(self.values):
            raise ValueError("labels e values devem ter o mesmo tamanho")
        return self


class FixarChartIn(BaseModel):
    titulo: Optional[str] = Field(default=None, max_length=200)
    chartData: ChartDataIn


class ExportChartIn(BaseModel):
    """Payload para exportação de UM gráfico individual em PDF."""
    titulo: Optional[str] = Field(default=None, max_length=200)
    chartData: ChartDataIn
    suggested_insight: Optional[str] = Field(default=None, max_length=1000)
    analise: Optional[str] = Field(default=None, max_length=4000)


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=200)
