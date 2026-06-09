import pandas as pd

from core.graph_loader import (
    load_graph,
    get_nearest_node
)

from core.route_planner import (
    shortest_route,
    route_distance
)

from visualization.map_renderer import (
    plot_graph_with_stores
)

from orders.order_generator import (
    generate_order
)

from agents.delivery_agent import (
    DeliveryAgent
)


def main():

    # -------------------------
    # LOAD GRAPH
    # -------------------------

    graph = load_graph()

    print(
        "Nodes:",
        len(graph.nodes)
    )

    print(
        "Edges:",
        len(graph.edges)
    )

    # -------------------------
    # LOAD STORES
    # -------------------------

    stores = pd.read_csv(

        "data/darkstores/darkstores.csv"

    )

    # -------------------------
    # CREATE AGENT
    # -------------------------

    first_store = stores.iloc[0]

    start_node = get_nearest_node(

        graph,

        first_store["lat"],

        first_store["lon"]

    )

    agent = DeliveryAgent(

        start_node

    )

    print(

        "Agent Start Node:",

        agent.current_node

    )

    # -------------------------
    # GENERATE ORDER
    # -------------------------

    order = generate_order(

        graph,

        stores,

        first_store["platform"]

    )

    print(
        "\nGenerated Order"
    )

    print(
        order
    )

    print(

        "Pickup Node:",

        order.pickup_node

    )

    print(

        "Customer Node:",

        order.customer_node

    )

    # -------------------------
    # AGENT -> PICKUP ROUTE
    # -------------------------

    pickup_route = shortest_route(

        graph,

        agent.current_node,

        order.pickup_node

    )

    # -------------------------
    # PICKUP -> CUSTOMER ROUTE
    # -------------------------

    import networkx as nx

    try:

        delivery_route = shortest_route(

            graph,

            order.pickup_node,

            order.customer_node

        )

    except nx.NetworkXNoPath:

        print(
            "Order unreachable. Regenerate."
        )

        return

    # -------------------------
    # FULL ROUTE
    # -------------------------

    full_route = (

        pickup_route +

        delivery_route[1:]

    )
    agent.current_route = full_route

    distance = route_distance(

        graph,

        full_route

    )

    print(

        "\nTotal Distance:",

        round(
            distance,
            2
        ),

        "meters"

    )

    print(

        "Route Nodes:",

        len(
            full_route
        )

    )

    # -------------------------
    # VISUALIZE
    # -------------------------

    plot_graph_with_stores(

        graph,

        agent,

        order,

        full_route

    )


if __name__ == "__main__":

    main()