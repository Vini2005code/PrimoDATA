"""Modelos Pydantic da API."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class RequisicaoChat(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversa_id: Optional[int] = None


class NovaConversa(BaseModel):
    titulo: Optional[str] = None


class RenomearConversa(BaseModel):
    titulo: str = Field(min_length=1, max_length=200)


class ChartDataIn(BaseModel):
    type: str
    title: Optional[str] = ""
    labels: list[Any] = []
    values: list[Any] = []


class FixarChartIn(BaseModel):
    titulo: Optional[str] = None
    chartData: ChartDataIn


class ExportChartIn(BaseModel):
    """Payload para exportação de UM gráfico individual em PDF."""
    titulo: Optional[str] = None
    chartData: ChartDataIn
    suggested_insight: Optional[str] = None
    analise: Optional[str] = None
