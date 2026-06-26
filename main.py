import subprocess
import sys
import pandas as pd

from core.graph_loader import load_graph, get_nearest_node
from optimization.route_optimizer import find_best_route
from orders.order_generator import generate_order
from agents.delivery_agent import DeliveryAgent
from visualization.map_renderer import plot_graph_with_stores


def main():

    # ── Load graph ─────────────────────────────────────────────────────────
    graph = load_graph()
    stores = pd.read_csv("data/darkstores/darkstores.csv")

    # ── Place agent at first store ─────────────────────────────────────────
    first_store = stores.iloc[0]
    start_node = get_nearest_node(
        graph,
        first_store["lat"],
        first_store["lon"]
    )

    agent = DeliveryAgent(start_node)
    print(f"Agent Start Node: {agent.current_node}")

    # ── Generate a feasible seed order (retry until one works) ─────────────
    result = None
    order = None
    attempts = 0

    while result is None:
        attempts += 1

        order = generate_order(
            graph,
            stores,
            first_store["platform"],
            simulation_time=0
        )

        print(f"\nAttempt {attempts}: {order}")
        print(f"  Pickup node:   {order.pickup_node}")
        print(f"  Customer node: {order.customer_node}")

        result = find_best_route(
            graph,
            start_node,
            [order],
            current_time=0
        )

    agent.add_order(order)
    agent.update_route(result["route_nodes"])

    print(f"\nRoute found after {attempts} attempt(s)")
    print(f"  Distance:    {result['distance']:.0f} m")
    print(f"  Travel time: {result['travel_time']:.1f} min")
    print(f"  Wait time:   {result['waiting_time']:.1f} min")
    print(f"  Sequence:    {result['sequence']}")
    print(f"  Route nodes: {len(result['route_nodes'])}")

    # ── Render map ─────────────────────────────────────────────────────────
    plot_graph_with_stores(
        graph,
        agent,
        order,
        result["route_nodes"]
    )
    print("\nmap.html saved — open it in your browser")

    # ── Start FastAPI server ────────────────────────────────────────────────
    print("Starting API at http://127.0.0.1:8000\n")
    subprocess.run([
        sys.executable, "-m", "uvicorn",
        "api.server:app",
        "--reload",
        "--port", "8000",
        "--host", "127.0.0.1"
    ])


if __name__ == "__main__":
    main()