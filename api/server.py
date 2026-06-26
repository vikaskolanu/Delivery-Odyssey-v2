from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import pandas as pd

from api.models import (
    OptimizeRequest
)

from core.graph_loader import (
    load_graph,
    get_nearest_node
)

from core.utils import (
    nearest_platform_store
)

from orders.order import (
    Order
)

from optimization.route_optimizer import (
    find_best_route
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

graph = load_graph()

stores = pd.read_csv(
    "data/darkstores/darkstores.csv"
)

active_orders = []

current_time = 0.0

agent_current_node = None


# ── New: let the JS animation sync the agent position ──────────────────────

class AgentSyncRequest(BaseModel):
    current_node: int
    current_time: float


@app.post("/agent/sync")
def agent_sync(request: AgentSyncRequest):
    global agent_current_node, current_time
    agent_current_node = request.current_node
    current_time = request.current_time
    return {"ok": True}


# ── New: mark an order delivered so it leaves active_orders ────────────────

@app.post("/agent/complete/{order_index}")
def complete_order(order_index: int):
    global active_orders
    if 0 <= order_index < len(active_orders):
        active_orders.pop(order_index)
    return {"remaining": len(active_orders)}


# ───────────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "running"}


@app.get("/health")
def health():
    return {"optimizer": "ready"}


@app.post("/optimize")
def optimize(request: OptimizeRequest):

    global agent_current_node

    customer_node = request.customer_node

    # Validate node exists in graph
    if customer_node not in graph.nodes:
        return {"accepted": False, "reason": "Node not in graph"}

    customer_data = graph.nodes[customer_node]
    customer_lat = customer_data["y"]
    customer_lon = customer_data["x"]

    selected_store = nearest_platform_store(
        stores,
        request.platform,
        customer_lat,
        customer_lon
    )

    pickup_node = get_nearest_node(
        graph,
        selected_store["lat"],
        selected_store["lon"]
    )

    new_order = Order(
        platform=request.platform,
        pickup_node=pickup_node,
        customer_node=customer_node,
        created_time=current_time,
        prep_time=3,
        sla_minutes=15
    )

    # FIX: use pickup_node as starting position if agent not yet placed
    start_node = agent_current_node if agent_current_node is not None else pickup_node

    # Try with new order added
    candidate_orders = list(active_orders) + [new_order]

    result = find_best_route(
        graph,
        start_node,
        candidate_orders,
        current_time
    )

    if result is None:
        return {
            "accepted": False,
            "reason": "No feasible route — SLA would be violated"
        }

    # Commit order
    active_orders.append(new_order)

    # FIX: update agent_current_node to the end of the new route
    # so the next order routes from the correct position
    if result["route_nodes"]:
        agent_current_node = result["route_nodes"][-1]

    # Build readable sequence labels e.g. ["P1","D1","P2","D2"]
    seq_labels = []
    for stop_type, idx in result["sequence"]:
        order = candidate_orders[idx]
        label = f"P{idx + 1}" if stop_type == "P" else f"D{idx + 1}"
        seq_labels.append(label)

    return {
        "accepted": True,
        "store_name": selected_store["name"],
        "platform": request.platform,
        "sequence": seq_labels,
        "distance": round(result["distance"], 2),
        "travel_time": round(result["travel_time"], 2),
        "waiting_time": round(result["waiting_time"], 2),
        "route_nodes": result["route_nodes"]
    }