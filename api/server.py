from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import pandas as pd
import networkx as nx

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


@app.post("/agent/reset")
def reset_agent():
    global active_orders, agent_current_node, current_time
    active_orders.clear()
    agent_current_node = None
    current_time = 0.0
    return {"ok": True, "remaining": 0}


# ───────────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "running"}


@app.get("/health")
def health():
    return {"optimizer": "ready"}


@app.post("/optimize")
def optimize(request: OptimizeRequest):

    customer_node = request.customer_node

    # Validate node exists in graph
    if customer_node not in graph.nodes:
        return {"accepted": False, "reason": "Node not in graph"}

    customer_data = graph.nodes[customer_node]
    customer_lat = customer_data["y"]
    customer_lon = customer_data["x"]

    platform_stores = stores[stores["platform"] == request.platform]
    best_overall_result = None
    best_store = None
    best_pickup_node = None
    best_new_order = None
    
    prep_time = 4.0

    for _, store in platform_stores.iterrows():
        pickup_node = get_nearest_node(
            graph,
            store["lat"],
            store["lon"]
        )

        try:
            nx.shortest_path(graph, pickup_node, customer_node, weight="length")
        except nx.NetworkXNoPath:
            continue

        new_order = Order(
            platform=request.platform,
            pickup_node=pickup_node,
            customer_node=customer_node,
            created_time=request.current_time,
            prep_time=prep_time,
            sla_minutes=request.sla_minutes,
            is_picked_up=False
        )

        candidate_orders = []
        for o in request.active_orders:
            order_obj = Order(
                platform=o.platform,
                pickup_node=o.pickup_node,
                customer_node=o.customer_node,
                created_time=o.created_time,
                prep_time=o.prep_time,
                sla_minutes=o.sla_minutes,
                is_picked_up=o.is_picked_up
            )
            candidate_orders.append(order_obj)

        candidate_orders.append(new_order)

        result = find_best_route(
            graph,
            request.current_node,
            candidate_orders,
            request.current_time
        )
        
        if result is not None:
            if best_overall_result is None or result["finish_time"] < best_overall_result["finish_time"]:
                best_overall_result = result
                best_store = store
                best_pickup_node = pickup_node
                best_new_order = new_order

    if best_overall_result is None:
        return {
            "accepted": False,
            "reason": "No feasible route — SLA would be violated for all possible warehouses"
        }
        
    result = best_overall_result
    selected_store = best_store
    pickup_node = best_pickup_node
    new_order = best_new_order

    # Build readable sequence labels
    seq_labels = []
    for stop_type, idx in result["sequence"]:
        is_new = (idx == len(candidate_orders) - 1)
        if is_new:
            label = f"P (New)" if stop_type == "P" else f"D (New)"
        else:
            orig_order = request.active_orders[idx]
            label = f"P (Order {orig_order.id})" if stop_type == "P" else f"D (Order {orig_order.id})"
        seq_labels.append(label)

    return {
        "accepted": True,
        "store_name": selected_store["name"],
        "platform": request.platform,
        "pickup_node": pickup_node,
        "prep_time": prep_time,
        "ready_time": new_order.ready_time,
        "deadline_time": new_order.deadline_time,
        "sequence": seq_labels,
        "distance": round(result["distance"], 2),
        "travel_time": round(result["travel_time"], 2),
        "waiting_time": round(result["waiting_time"], 2),
        "route_nodes": result["route_nodes"]
    }
