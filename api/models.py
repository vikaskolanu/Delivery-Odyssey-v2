from pydantic import BaseModel


class OptimizeRequest(BaseModel):

    platform: str

    customer_node: int