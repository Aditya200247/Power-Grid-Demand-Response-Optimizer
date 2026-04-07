from pydantic import BaseModel, Field
from typing import List
from enum import Enum


class TaskDifficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

class LoadZone(int, Enum):
    NONE = 0
    ZONE_A = 1
    ZONE_B = 2


class PowerGridObservation(BaseModel):
    
    current_demand_kw: float = Field(..., description="Current power demand in kilowatts")
    grid_frequency_hz: float = Field(..., description="Target is 50.0 Hz")
    spot_price_dollars: float = Field(..., description="Current electricity price per kWh")
    
    
    battery_charge_level: float = Field(..., ge=0.0, le=1.0, description="Battery SOC from 0.0 (empty) to 1.0 (full)")
    
    
    forecast_solar_kw: List[float] = Field(..., description="Predicted solar yield for the next 5 timesteps")
    forecast_wind_kw: List[float] = Field(..., description="Predicted wind yield for the next 5 timesteps")
    forecast_demand_kw: List[float] = Field(..., description="Predicted demand for the next 5 timesteps")


class PowerGridAction(BaseModel):
    
    battery_flow: float = Field(..., ge=-1.0, le=1.0, description="-1.0 is full discharge, 1.0 is full charge")
    diesel_activation: float = Field(..., ge=0.0, le=1.0, description="0.0 is off, 1.0 is maximum diesel output")
    grid_trade: float = Field(..., ge=-1.0, le=1.0, description="-1.0 is selling to grid, 1.0 is buying from grid")
    

    shed_load_zone: LoadZone = Field(default=LoadZone.NONE, description="Drop power to a zone to save the grid")


class StepResponse(BaseModel):
    observation: PowerGridObservation
    reward: float = Field(..., description="Reward for the current step (0.0 to 1.0)")
    done: bool = Field(..., description="True if episode ends (e.g., grid collapse or time limit reached)")
    info: dict = Field(default_factory=dict, description="Extra metadata for debugging")
