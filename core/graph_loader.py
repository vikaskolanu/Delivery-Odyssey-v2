import os
import osmnx as ox
import networkx as nx


def load_graph():

    filepath = "data/maps/road_network.graphml"

    if os.path.exists(filepath):

        print("Loading cached graph")

        graph = ox.load_graphml(
            filepath
        )

    else:

        graph = ox.graph_from_place(

            "Whitefield, Bengaluru, Karnataka, India",

            network_type="drive"

        )

        ox.save_graphml(

            graph,

            filepath

        )

    # KEEP ONLY THE LARGEST CONNECTED ROAD NETWORK

    largest_component = max(

        nx.strongly_connected_components(
            graph
        ),

        key=len

    )

    graph = graph.subgraph(

        largest_component

    ).copy()

    return graph


def get_nearest_node(
    graph,
    lat,
    lon
):

    node = ox.distance.nearest_nodes(

        graph,

        X=lon,

        Y=lat

    )

    return node