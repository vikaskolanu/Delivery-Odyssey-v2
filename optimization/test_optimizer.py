import pandas as pd

from core.graph_loader import (
    load_graph,
    get_nearest_node
)

from orders.order import Order

from optimization.route_optimizer import (
    find_best_route
)


graph = load_graph()

stores = pd.read_csv(
    "data/darkstores/darkstores.csv"
)

store = stores.iloc[0]

pickup_node = get_nearest_node(
    graph,
    store["lat"],
    store["lon"]
)

order_a = Order(
    platform="Zepto",
    pickup_node=pickup_node,
    customer_node=list(graph.nodes)[50],
    created_time=0,
    prep_time=2,
    sla_minutes=15
)

order_b = Order(
    platform="Blinkit",
    pickup_node=pickup_node,
    customer_node=list(graph.nodes)[100],
    created_time=1,
    prep_time=3,
    sla_minutes=15
)

result = find_best_route(

    graph,

    pickup_node,

    [order_a, order_b],

    0

)

print("\nBEST RESULT\n")

print(
    "Distance:",
    round(result["distance"], 2)
)

print(
    "Travel Time:",
    round(result["travel_time"], 2)
)

print(
    "Waiting Time:",
    round(result["waiting_time"], 2)
)

print(
    "Sequence:",
    result["sequence"]
)

print(
    "Route Nodes:",
    len(result["route_nodes"])
)