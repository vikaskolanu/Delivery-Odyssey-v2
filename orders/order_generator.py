import random
import networkx as nx

from orders.order import Order

from core.utils import (
    nearest_platform_store
)

from core.graph_loader import (
    get_nearest_node
)


def generate_order(

    graph,

    stores,

    platform,

    simulation_time

):

    while True:

        customer_node = random.choice(

            list(graph.nodes)

        )

        customer_data = graph.nodes[
            customer_node
        ]

        customer_lat = customer_data["y"]

        customer_lon = customer_data["x"]

        selected_store = nearest_platform_store(

            stores,

            platform,

            customer_lat,

            customer_lon

        )

        pickup_node = get_nearest_node(

            graph,

            selected_store["lat"],

            selected_store["lon"]

        )

        try:

            nx.shortest_path(

                graph,

                pickup_node,

                customer_node,

                weight="length"

            )

            break

        except nx.NetworkXNoPath:

            continue

    prep_time = random.randint(

        2,

        6

    )

    sla_minutes = 15

    return Order(

        platform=platform,

        pickup_node=pickup_node,

        customer_node=customer_node,

        created_time=simulation_time,

        prep_time=prep_time,

        sla_minutes=sla_minutes

    )