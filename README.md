
# 🚀 Delivery Odyssey

**Dynamic Multi-Order Route Optimization Simulator for Quick-Commerce Logistics**

Delivery Odyssey is an interactive simulation platform that models real-world quick-commerce delivery operations using OpenStreetMap road networks, dynamic route optimization, and time-constrained order scheduling.

The project demonstrates how delivery riders can be assigned and re-routed intelligently while satisfying preparation times and delivery deadlines.

---

## ✨ Features

* 🌍 Real road-network routing using OpenStreetMap
* 🚴 Dynamic rider movement simulation
* 🏬 Multi-platform warehouse support (Zepto, Blinkit, Instamart)
* 📦 Time-aware order generation
* 🧠 Multi-order route optimization
* ⚡ FastAPI optimization backend
* 🗺️ Interactive map visualization
* 📍 Custom order placement on the map
* 🎮 Simulation controls (Play, Pause, Restart)

---

## 🏗️ System Architecture

```
          User

            │

            ▼

 Interactive Map UI

            │

            ▼

      FastAPI Backend

            │

            ▼

 Route Optimization Engine

            │

            ▼

 Best Feasible Route

            │

            ▼

 Rider Simulation
```

---

## 🧠 Optimization Strategy

Each incoming order contains:

* Pickup location
* Customer location
* Preparation time
* Delivery deadline

Instead of greedily assigning the new order, the optimizer generates every valid pickup-delivery sequence while respecting the constraint that every pickup must occur before its corresponding delivery.

Each feasible sequence is simulated over the real road network.

For every route the simulator evaluates:

* Travel distance
* Travel time
* Waiting time at stores
* Delivery deadlines

The route with the lowest feasible completion time is selected.

---

## 🛠️ Tech Stack

**Backend**

* Python
* FastAPI
* NetworkX
* OSMnx

**Frontend**

* HTML
* CSS
* JavaScript
* Leaflet.js

**Mapping**

* OpenStreetMap

---

## 🚀 Future Improvements

* Fleet-level optimization with multiple riders
* Dynamic order insertion without restarting routes
* Intelligent order batching
* Traffic-aware routing
* Machine-learning based order acceptance
* Live analytics dashboard

---

## 📸 Demo

<img width="1463" height="795" alt="Screenshot 2026-06-26 at 12 01 49 PM" src="https://github.com/user-attachments/assets/e03e64b0-3296-469a-bf89-8518d2086b4f" />

---

## 👨‍💻 Author

**Vikas Kolanu**

B.Tech, IIT Goa

