from itertools import permutations

from core.route_planner import (
    shortest_route,
    route_distance
)

AVERAGE_SPEED_M_PER_MIN = 350


def distance_to_minutes(distance):
    return distance / AVERAGE_SPEED_M_PER_MIN


def generate_valid_sequences(orders):

    stops = []

    for i, order in enumerate(orders):
        stops.append(("P", i))
        stops.append(("D", i))

    valid_sequences = []

    for sequence in permutations(stops):

        valid = True
        picked = set()

        for stop_type, order_id in sequence:
            if stop_type == "P":
                picked.add(order_id)
            elif stop_type == "D":
                if order_id not in picked:
                    valid = False
                    break

        if valid:
            valid_sequences.append(sequence)

    return valid_sequences


def get_stop_node(stop, orders):

    stop_type, order_id = stop
    order = orders[order_id]

    if stop_type == "P":
        return order.pickup_node

    return order.customer_node


def simulate_route(
    graph,
    current_position,
    sequence,
    orders,
    current_time
):
    total_distance = 0
    total_wait_time = 0
    current_node = current_position
    simulation_time = current_time

    for stop in sequence:

        stop_type, order_id = stop
        order = orders[order_id]
        target_node = get_stop_node(stop, orders)

        # FIX: shortest_route now returns None instead of raising
        route = shortest_route(graph, current_node, target_node)

        if route is None:
            return {"feasible": False}

        distance = route_distance(graph, route)
        travel_time = distance_to_minutes(distance)

        total_distance += distance
        simulation_time += travel_time

        # Wait at warehouse if order isn't ready yet
        if stop_type == "P":
            if simulation_time < order.ready_time:
                wait_time = order.ready_time - simulation_time
                total_wait_time += wait_time
                simulation_time += wait_time

        # SLA check at delivery
        if stop_type == "D":
            if simulation_time > order.deadline_time:
                return {"feasible": False}

        current_node = target_node

    return {
        "feasible": True,
        "distance": total_distance,
        # FIX: return elapsed time, not absolute simulation clock
        "travel_time": simulation_time - current_time,
        "waiting_time": total_wait_time,
        "finish_time": simulation_time,
        "sequence": sequence
    }


def build_route_nodes(
    graph,
    current_position,
    sequence,
    orders
):
    full_route = []
    current_node = current_position
    first_segment = True

    for stop in sequence:

        target_node = get_stop_node(stop, orders)

        route = shortest_route(graph, current_node, target_node)

        if route is None:
            return []

        if first_segment:
            full_route.extend(route)
            first_segment = False
        else:
            full_route.extend(route[1:])

        current_node = target_node

    return full_route


def find_best_route(
    graph,
    current_position,
    orders,
    current_time
):
    sequences = generate_valid_sequences(orders)

    best_result = None

    for sequence in sequences:

        result = simulate_route(
            graph,
            current_position,
            sequence,
            orders,
            current_time
        )

        # FIX: use .get() so infeasible dict {"feasible": False} doesn't KeyError
        if not result.get("feasible"):
            continue

        if best_result is None:
            best_result = result
            continue

        if result["travel_time"] < best_result["travel_time"]:
            best_result = result

    if best_result is None:
        return None

    best_result["route_nodes"] = build_route_nodes(
        graph,
        current_position,
        best_result["sequence"],
        orders
    )

    return best_result