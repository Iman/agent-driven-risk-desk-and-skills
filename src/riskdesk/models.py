"""Input contracts. Amounts are already translated into the stated base currency."""
from datetime import date
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Provenance(StrictModel):
    as_of: date
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    source: str = Field(min_length=1, max_length=500)
    data_mode: Literal["synthetic", "user-licensed"]


class TailRequest(Provenance):
    pnl: list[float] = Field(min_length=2, max_length=1_000_000)
    confidence: float = Field(gt=0, lt=1)
    horizon_days: int = Field(gt=0, le=3650, strict=True)
    portfolio_value: float = Field(gt=0)


class Position(StrictModel):
    id: str = Field(min_length=1)
    asset: str = Field(min_length=1)
    market_value: float
    instrument_type: Literal["linear"]


class PortfolioRequest(Provenance):
    nav: float = Field(gt=0)
    positions: list[Position] = Field(min_length=1, max_length=100_000)

    @model_validator(mode="after")
    def unique_positions(self):
        if len({p.id for p in self.positions}) != len(self.positions):
            raise ValueError("position ids must be unique")
        return self


class Scenario(StrictModel):
    name: str = Field(min_length=1)
    shocks: dict[str, float] = Field(min_length=1)


class StressRequest(PortfolioRequest):
    scenarios: list[Scenario] = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def complete_scenarios(self):
        assets = {p.asset for p in self.positions}
        if len({s.name for s in self.scenarios}) != len(self.scenarios):
            raise ValueError("scenario names must be unique")
        for scenario in self.scenarios:
            if set(scenario.shocks) != assets:
                raise ValueError("every scenario must name exactly the portfolio assets")
            if any(value < -1 for value in scenario.shocks.values()):
                raise ValueError("linear asset return shocks cannot be less than -100%")
        return self
