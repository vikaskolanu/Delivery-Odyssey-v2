import networkx as nx


def shortest_route(
    graph,
    start,
    end
):
    if start == end:
        return [start]

    try:
        return nx.shortest_path(
            graph,
            source=start,
            target=end,
            weight="length"
        )
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return None


def route_distance(
    graph,
    route
):
    if not route or len(route) < 2:
        return 0.0

    distance = 0.0

    for i in range(len(route) - 1):

        edges = graph.get_edge_data(
            route[i],
            route[i + 1]
        )

        # OSMnx returns a dict of parallel edges {0: {...}, 1: {...}}
        # Pick the shortest one
        distance += min(
            data.get("length", 0)
            for data in edges.values()
        )

    return distance