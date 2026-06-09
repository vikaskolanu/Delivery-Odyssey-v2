import networkx as nx


def shortest_route(
    graph,
    start,
    end
):

    return nx.shortest_path(

        graph,

        source=start,

        target=end,

        weight="length"

    )


def route_distance(
    graph,
    route
):

    distance = 0

    for i in range(

        len(route)-1

    ):

        edge = graph.get_edge_data(

            route[i],

            route[i+1]

        )

        distance += edge[0]["length"]

    return distance