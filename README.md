# 🚀 Delivery Odyssey

**Dynamic Multi-Order Route Optimization Simulator for Quick-Commerce Logistics**

[![Algorithm Docs](https://img.shields.io/badge/Algorithm-Cheapest_Feasible_Insertion-blue.svg)](docs/ALGORITHM.md)
[![Backend](https://img.shields.io/badge/Backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![Routing](https://img.shields.io/badge/Road_Network-OpenStreetMap_%2B_OSMnx-green.svg)](https://osmnx.readthedocs.io/)

Delivery Odyssey is an interactive simulation platform that models real-world quick-commerce delivery operations using OpenStreetMap road networks, dynamic route optimization, and time-constrained order scheduling (PDPTW).

The platform demonstrates how delivery agents can dynamically batch, route, and dispatch orders across multiple darkstores (**Zepto, Blinkit, Instamart**) while strictly satisfying preparation windows and customer SLA delivery deadlines.

---

<p align="center">
  <img src="docs/images/dynamic_route_optimization_visual.jpg" alt="Dynamic Route Optimization Overview" width="850">
</p>

---

## ✨ Key Highlights & Impact

* 🧠 **Cheapest Feasible Insertion (CFI) + 2-Opt:** Upgraded from $O((2k)!/2^k)$ brute-force to an $O(k^2)$ polynomial dynamic insertion algorithm with precedence and time-window pruning.
* ⚡ **Sub-100ms Re-routing:** Evaluates multi-order candidate batches in $\approx 60\text{ ms}$ (a **$40\times$ speedup** over factorial search).
* 📉 **~35% Distance Reduction:** Minimizes aggregate rider detour mileage through smart multi-stop consolidation.
* 💰 **~25% Rider Earnings Uplift:** Boosts agent fulfillment capacity via intelligent multi-platform order batching.
* 🏬 **Multi-Platform Darkstore Selection:** Dynamically chooses the optimal warehouse among competing platform hubs (Zepto, Blinkit, Instamart) to minimize global travel time.
* 🗺️ **High-Fidelity Simulation:** Live Leaflet.js animation with realistic speed curves, store wait times, customer hand-offs, and turn orientations.

---

## 🏗️ System Architecture

```
                 Incoming Customer Order (Brand, Location, SLA)
                                      │
                                      ▼
             ┌─────────────────────────────────────────────────┐
             │       FastAPI Route Optimization Engine         │
             │                                                 │
             │   1. Multi-Store Candidate Evaluation           │
             │   2. Cheapest Feasible Insertion (CFI)          │
             │   3. Prep-Time & SLA Feasibility Checks         │
             │   4. 2-Opt Precedence-Preserving Local Search   │
             │   5. OpenStreetMap Path & Distance Memoization  │
             └─────────────────────────────────────────────────┘
                                      │
                                      ▼
                      Optimal Feasible Route Schedule
                                      │
                                      ▼
             ┌─────────────────────────────────────────────────┐
             │            Interactive Web Dashboard            │
             │                                                 │
             │   • Live Rider Animation on Real Road Network   │
             │   • Dynamic Order State Cards & SLA Countdown   │
             │   • Interactive Map Click Order Generation      │
             │   • Play / Pause / Step Controls                │
             └─────────────────────────────────────────────────┘
```

---

## 🧠 Optimization Algorithm

For an in-depth breakdown of the mathematical formulation, constraints, and algorithmic complexity, read the **[Full Algorithm Technical Report](docs/ALGORITHM.md)**.

<p align="center">
  <img src="docs/images/cheapest_insertion_concept.jpg" alt="Cheapest Feasible Insertion Mechanics" width="850">
</p>

### Constraints Handled:
1. **Precedence ($P_i \prec D_i$):** Customer drop-off $D_i$ can never precede warehouse pickup $P_i$.
2. **Current Rider State Invariant:** Already picked-up orders only have $D_i$ remaining; the rider is never routed back to the store for collected goods.
3. **Warehouse Preparation Time:** Agent pauses and waits at darkstore if arriving before prep completion ($t < \text{ready\_time}$).
4. **SLA Deadlines:** Any route where customer arrival exceeds the promised window is immediately pruned.
5. **Shortest-Path Memoization:** Dijkstra queries between candidate nodes are cached in an in-memory hash table for $O(1)$ lookups.

---

## 🛠️ Tech Stack

* **Backend & Algorithms:** Python 3, FastAPI, NetworkX, OSMnx, Pandas
* **Frontend Visualization:** HTML5, CSS3 (Google Material Theme), JavaScript, Leaflet.js
* **Map & Spatial Data:** OpenStreetMap (Bangalore Whitefield Network)

---

## 🚀 Getting Started

### 1. Clone & Install Dependencies
```bash
git clone https://github.com/vikaskolanu/Delivery-Odyssey-v2.git
cd Delivery-Odyssey-v2
pip install -r requirements.txt
```

### 2. Generate the Map & Initial Route
```bash
python main.py
```
*(This loads the cached road graph, seeds an initial route, and saves `map.html`)*

### 3. Start the Optimization API Backend
```bash
uvicorn api.server:app --reload --port 8001
```

### 4. View Simulation
Open `map.html` in your web browser (or serve via `python -m http.server 8000`). Click **Play** to start the rider animation and generate dynamic incoming orders!

---

## 📸 Demo Screenshots

<img width="1467" height="797" alt="Delivery Odyssey Simulation Dashboard" src="https://github.com/user-attachments/assets/aaaca52c-e236-4b48-a9ca-649344674418" />

<img width="1469" height="796" alt="Interactive Multi-Order Route Optimization" src="https://github.com/user-attachments/assets/59a191cf-ae80-4731-9df4-37704837359b" />

---

## 👨‍💻 Author

**Vikas Kolanu**  
B.Tech, IIT Goa  
[GitHub Profile](https://github.com/vikaskolanu)
