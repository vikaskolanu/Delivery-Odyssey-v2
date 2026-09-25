from core.route_planner import (
    shortest_route,
    route_distance
)

AVERAGE_SPEED_M_PER_MIN = 350


def distance_to_minutes(distance):
    return distance / AVERAGE_SPEED_M_PER_MIN


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
    current_time,
    path_cache=None
):
    """
    Simulates executing a sequence of stops from current_position.
    Validates prep times, travel times, and SLA deadlines.
    Returns feasibility status, total distance, finish time, and chronological delivery times.
    """
    total_distance = 0
    total_wait_time = 0
    current_node = current_position
    simulation_time = current_time
    delivery_times = {}

    for stop in sequence:
        stop_type, order_id = stop
        order = orders[order_id]
        target_node = get_stop_node(stop, orders)

        cache_key = (current_node, target_node)
        if path_cache is not None and cache_key in path_cache:
            route, distance = path_cache[cache_key]
        else:
            route = shortest_route(graph, current_node, target_node)
            if route is None:
                if path_cache is not None:
                    path_cache[cache_key] = (None, float('inf'))
                return {"feasible": False}
            distance = route_distance(graph, route)
            if path_cache is not None:
                path_cache[cache_key] = (route, distance)

        if route is None:
            return {"feasible": False}

        travel_time = distance_to_minutes(distance)
        total_distance += distance
        simulation_time += travel_time

        # Wait at warehouse if order is not ready yet
        if stop_type == "P":
            if simulation_time < order.ready_time:
                wait_time = order.ready_time - simulation_time
                total_wait_time += wait_time
                simulation_time += wait_time

        # SLA check at customer delivery
        if stop_type == "D":
            if simulation_time > order.deadline_time:
                return {"feasible": False}
            delivery_times[order_id] = simulation_time

        current_node = target_node

    chrono_delivery_times = tuple(
        delivery_times.get(i, simulation_time) for i in range(len(orders))
    )

    return {
        "feasible": True,
        "distance": total_distance,
        "travel_time": simulation_time - current_time,
        "waiting_time": total_wait_time,
        "finish_time": simulation_time,
        "sequence": tuple(sequence),
        "delivery_times": chrono_delivery_times
    }


def generate_insertion_candidates(current_sequence, order_id, order):
    """
    Generates all valid insertions of an order into an existing sequence of stops.
    - If order is already picked up: inserts D at all positions (m+1 candidates).
    - If order is not picked up: inserts P at index i and D at index j where i <= j ((m+1)*(m+2)/2 candidates).
    """
    candidates = []
    m = len(current_sequence)
    is_picked_up = getattr(order, "is_picked_up", False)

    if is_picked_up:
        # Only delivery needs to be inserted
        for pos in range(m + 1):
            new_seq = list(current_sequence)
            new_seq.insert(pos, ("D", order_id))
            candidates.append(tuple(new_seq))
    else:
        # Both Pickup and Delivery must be inserted, with Pickup before Delivery
        for i in range(m + 1):
            for j in range(i, m + 1):
                new_seq = list(current_sequence)
                new_seq.insert(i, ("P", order_id))
                new_seq.insert(j + 1, ("D", order_id))
                candidates.append(tuple(new_seq))

    return candidates


def refine_with_local_search(
    graph,
    current_position,
    sequence,
    orders,
    current_time,
    path_cache=None
):
    """
    Runs a 2-opt / relocation local search over the sequence to explore
    further improvements while strictly preserving precedence (P before D).
    """
    best_seq = list(sequence)
    best_eval = simulate_route(graph, current_position, best_seq, orders, current_time, path_cache)
    if not best_eval.get("feasible"):
        return sequence, best_eval

    improved = True
    while improved:
        improved = False
        n = len(best_seq)

        for i in range(n):
            for j in range(n):
                if i == j:
                    continue

                # Try relocating element i to position j
                candidate = list(best_seq)
                elem = candidate.pop(i)
                candidate.insert(j, elem)

                # Check precedence constraint (P must precede D for each order)
                valid_precedence = True
                picked = set()
                for stop_type, order_idx in candidate:
                    if stop_type == "P":
                        picked.add(order_idx)
                    elif stop_type == "D":
                        if not getattr(orders[order_idx], "is_picked_up", False) and order_idx not in picked:
                            valid_precedence = False
                            break

                if not valid_precedence:
                    continue

                eval_res = simulate_route(graph, current_position, candidate, orders, current_time, path_cache)
                if eval_res.get("feasible"):
                    if eval_res["finish_time"] < best_eval["finish_time"] - 1e-4:
                        best_seq = candidate
                        best_eval = eval_res
                        improved = True
                        break
            if improved:
                break

    return tuple(best_seq), best_eval


def build_route_nodes(
    graph,
    current_position,
    sequence,
    orders,
    path_cache=None
):
    full_route = []
    current_node = current_position
    first_segment = True

    for stop in sequence:
        target_node = get_stop_node(stop, orders)

        cache_key = (current_node, target_node)
        if path_cache is not None and cache_key in path_cache and path_cache[cache_key][0] is not None:
            route = path_cache[cache_key][0]
        else:
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
    """
    Finds the optimal delivery route for a set of orders using Cheapest Feasible Insertion (CFI)
    combined with local search refinement and shortest-path memoization.
    Time Complexity: O(k^2) instead of O((2k)!/2^k).
    """
    if not orders:
        return {
            "feasible": True,
            "distance": 0.0,
            "travel_time": 0.0,
            "waiting_time": 0.0,
            "finish_time": current_time,
            "sequence": (),
            "route_nodes": []
        }

    path_cache = {}
    current_sequence = ()

    # Incremental cheapest feasible insertion for each order
    for order_id, order in enumerate(orders):
        candidates = generate_insertion_candidates(current_sequence, order_id, order)
        best_candidate = None
        best_candidate_eval = None

        for cand in candidates:
            # Simulate candidate with sub-list of orders evaluated so far
            eval_res = simulate_route(
                graph,
                current_position,
                cand,
                orders[:order_id + 1],
                current_time,
                path_cache
            )

            if not eval_res.get("feasible"):
                continue

            if best_candidate_eval is None or eval_res["finish_time"] < best_candidate_eval["finish_time"]:
                best_candidate = cand
                best_candidate_eval = eval_res

        if best_candidate is None:
            # No feasible insertion found that satisfies all deadlines
            return None

        current_sequence = best_candidate

    # Refine the final route with local search (2-opt / relocate)
    refined_sequence, final_eval = refine_with_local_search(
        graph,
        current_position,
        current_sequence,
        orders,
        current_time,
        path_cache
    )

    if not final_eval.get("feasible"):
        return None

    final_eval["route_nodes"] = build_route_nodes(
        graph,
        current_position,
        refined_sequence,
        orders,
        path_cache
    )

    return final_eval

