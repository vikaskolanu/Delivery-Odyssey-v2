from pydantic import BaseModel
from typing import List


class ActiveOrderModel(BaseModel):
    id: int
    platform: str
    pickup_node: int
    customer_node: int
    created_time: float
    prep_time: float
    sla_minutes: float
    is_picked_up: bool


class OptimizeRequest(BaseModel):
    platform: str
    customer_node: int
    sla_minutes: int = 15
    current_node: int
    current_time: float
    active_orders: List[ActiveOrderModel]
