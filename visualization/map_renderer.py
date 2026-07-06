import folium
import pandas as pd
import json

from core.graph_loader import get_nearest_node



def platform_icon_path(platform):

    return {

        "Zepto":
        "assets/Zepto_Warehouse_Icon.png",

        "Blinkit":
        "assets/Blinkit_Warehouse_Icon.png",

        "Instamart":
        "assets/Instamart_Warehouse_Icon.png"

    }.get(

        platform,

        "assets/Warehouse_Icon.png"

    )


def nearest_graph_node(
    graph,
    lat,
    lon
):

    nearest_node = None
    best_distance = float("inf")

    for node, data in graph.nodes(data=True):

        distance = (
            (data["y"] - lat) ** 2
            +
            (data["x"] - lon) ** 2
        )

        if distance < best_distance:

            best_distance = distance
            nearest_node = node

    return nearest_node


def build_graph_payload(graph):

    nodes = {}
    adjacency = {}

    for node, data in graph.nodes(data=True):

        node_id = str(node)
        nodes[node_id] = [
            data["y"],
            data["x"]
        ]
        adjacency[node_id] = []

    for start, end, _, data in graph.edges(keys=True, data=True):

        adjacency[str(start)].append(
            {
                "to": str(end),
                "length": data.get("length", 1)
            }
        )

    return {
        "nodes": nodes,
        "adjacency": adjacency
    }


def build_stores_payload( 
    graph,
    stores
):

    payload = []

    for _, row in stores.iterrows():

        payload.append(
            {
                "platform": row["platform"],
                "name": row["name"],
                "lat": row["lat"],
                "lon": row["lon"],
                "nodeId": str(
                    nearest_graph_node(
                        graph,
                        row["lat"],
                        row["lon"]
                    )
                )
            }
        )

    return payload



def initial_order_payload(order):

    return {

        "platform": order.platform,

        "pickupNodeId": str(
            order.pickup_node
        ),

        "dropNodeId": str(
            order.customer_node
        ),

        "createdTime": getattr(
            order,
            "created_time",
            0
        ),

        "prepTime": getattr(
            order,
            "prep_time",
            3
        ),

        "slaMinutes": getattr(
            order,
            "sla_minutes",
            15
        ),

        "readyTime": getattr(
            order,
            "ready_time",
            3
        ),

        "deadlineTime": getattr(
            order,
            "deadline_time",
            15
        )

    }

def add_agent_animation(
    folium_map,
    graph,
    stores,
    route,
    required_stops,
    initial_order
):

    if not route:
        return

    map_name = folium_map.get_name()
    graph_json = json.dumps(
        build_graph_payload(graph)
    )
    stores_json = json.dumps(
        build_stores_payload(
            graph,
            stores
        )
    )
    route_json = json.dumps(
        [
            str(node)
            for node in route
        ]
    )
    required_stops_json = json.dumps(
        [
            str(node)
            for node in required_stops
        ]
    )
    initial_order_json = json.dumps(
        initial_order_payload(initial_order)
    )

    

    animation_script = f"""
        window.addEventListener("load", function () {{
            const AVERAGE_SPEED_M_PER_MIN = 350;
            const graphData = {graph_json};
            const storesData = {stores_json};
            const initialOrder = {initial_order_json};
            let activeRouteNodeIds = {route_json};
            let activeStopNodeIds = {required_stops_json};
            let activeStopLabels = {{}};
            
            const CUSTOMERS = [
                {{ name: "Vikas Kolanu", avatarId: 1 }},
                {{ name: "Rahul Singh", avatarId: 2 }},
                {{ name: "Rohan Gupta", avatarId: 4 }},
                {{ name: "Amit Kumar", avatarId: 5 }},
                {{ name: "Arjun Nair", avatarId: 1 }},
                {{ name: "Priya Sharma", avatarId: 3 }},
                {{ name: "Ananya Patel", avatarId: 3 }},
                {{ name: "Sneha Reddy", avatarId: 3 }},
                {{ name: "Kavya Iyer", avatarId: 3 }},
                {{ name: "Neha Desai", avatarId: 3 }}
            ];

            function getUniqueCustomer(currentActiveOrders) {{
                const activeNames = (currentActiveOrders || []).filter(o => !o.delivered).map(o => o.customerName);
                const available = CUSTOMERS.filter(c => !activeNames.includes(c.name));
                if (available.length > 0) {{
                    return available[Math.floor(Math.random() * available.length)];
                }}
                return CUSTOMERS[Math.floor(Math.random() * CUSTOMERS.length)];
            }}
            
            const initialPickupStore = storesData.find(
                (store) => String(store.nodeId) === String(initialOrder.pickupNodeId) && store.platform === initialOrder.platform
            );
            
            let initialCustomer = getUniqueCustomer([]);
            
            let activeOrders = [{{
                id: 1,
                platform: initialOrder.platform,
                customerName: initialCustomer.name,
                avatarId: initialCustomer.avatarId,
                pickupNodeId: initialOrder.pickupNodeId,
                dropNodeId: initialOrder.dropNodeId,
                createdTime: Number(initialOrder.createdTime || 0),
                prepTime: Number(initialOrder.prepTime || 4),
                slaMinutes: Number(initialOrder.slaMinutes || 15),
                readyTime: Number(initialOrder.readyTime || 4),
                deadlineTime: Number(initialOrder.deadlineTime || 15),
                status: "Preparing order",
                delivered: false,
                is_picked_up: false,
                storeName: initialPickupStore ? initialPickupStore.name : "Warehouse"
            }}];
            
            let nextOrderId = 2;
            let agentCurrentNodeId = String(activeRouteNodeIds[0] || initialOrder.pickupNodeId);
            let simulationMinutesElapsed = 0.0;
            let lastSegmentElapsedMinutes = 0.0;
            let currentSegmentTravelMinutes = 0.0;
            
            let isWaitingAtStore = false;
            let waitStartTimestamp = null;
            let waitDurationMs = 1500;
            let waitTargetMinutes = 0.0;
            let waitStartMinutes = 0.0;
            let isOptimizing = false;

            let customerMarkers = {{}};

            activeStopLabels[initialOrder.pickupNodeId] = `Pickup ${{initialOrder.platform}} from ${{initialPickupStore ? initialPickupStore.name : "Warehouse"}}`;
            activeStopLabels[initialOrder.dropNodeId] = `Drop ${{initialOrder.platform}} Customer`;

            let agentRoutePoints = activeRouteNodeIds.map(
                (nodeId) => graphData.nodes[String(nodeId)]
            );
            let pickFromMap = false;
            let candidateMarkers = [];
            let candidateRouteLine = null;

            const agentIcon = L.divIcon({{
                className: "moving-agent-icon",
                html: '<img id="moving-agent-image" src="assets/Delivery_Agent_Icon.png" style="width:28px;height:28px;object-fit:contain;display:block;">',
                iconSize: [28, 28],
                iconAnchor: [14, 14]
            }});

            const movingAgentMarker = L.marker(
                agentRoutePoints[0],
                {{
                    icon: agentIcon,
                    zIndexOffset: 1000
                }}
            ).addTo({map_name});

            const activeRouteLine = L.polyline(
                agentRoutePoints,
                {{
                    color: "#0066FF",
                    weight: 2,
                    opacity: 0.70,
                    lineCap: "round"
                }}
            ).addTo({map_name});

            let currentRouteIndex = 0;
            let animationFrameId = null;
            let isPlaying = false;
            let segmentStartTime = null;
            let segmentDurationMs = 600;
            let activeTurnSlowdown = 1;
            const minSegmentDurationMs = 120;
            const millisecondsPerMeter = 11;
            
            const agentImage = document.getElementById("moving-agent-image");
            const orderStatus = document.getElementById("order-status");
            const currentStatus = document.getElementById("current-status");
            
            function renderOrdersBoard() {{
                const listEl = document.getElementById("active-orders-list");
                const deliveredListEl = document.getElementById("delivered-orders-list");
                
                listEl.innerHTML = "";
                deliveredListEl.innerHTML = "";

                if (activeOrders.length === 0) {{
                    listEl.innerHTML = `<div class="empty-state">No active orders</div>`;
                    deliveredListEl.innerHTML = `<div class="empty-state">No delivered orders yet</div>`;
                    return;
                }}

                let hasActive = false;
                let hasDelivered = false;

                activeOrders.forEach(order => {{
                    if (order.delivered) {{
                        hasDelivered = true;
                        const dDiv = document.createElement("div");
                        dDiv.className = "delivered-item";
                        dDiv.innerHTML = `
                            <div class="checkmark">✓</div>
                            <div class="details">
                                <div class="name">${{order.customerName}}</div>
                                <div class="platform">${{order.platform}} Order</div>
                            </div>
                        `;
                        deliveredListEl.appendChild(dDiv);
                        return;
                    }}
                    
                    hasActive = true;
                    
                    const platformClass = order.platform.toLowerCase();
                    const div = document.createElement("div");
                    div.className = `order-card ${{platformClass}}`;
                    
                    const elapsed = simulationMinutesElapsed - order.createdTime;
                    const remaining = order.deadlineTime - simulationMinutesElapsed;

                    const slaColorClass = remaining < 0 ? "danger" : (remaining < 3 ? "warning" : "ok");

                    div.innerHTML = `
                        <div class="order-head">
                            <div class="order-customer-info">
                                <img src="assets/avatars/avatar_${{order.avatarId}}.jpg" class="order-avatar" alt="Avatar" />
                                <strong>${{order.customerName}}</strong>
                            </div>
                            <span class="badge badge-${{platformClass}}">${{order.platform}}</span>
                        </div>
                        <div class="order-status-row" style="display: flex; justify-content: space-between; align-items: center; margin-top: 12px;">
                            <span class="status-pill ${{orderStatusClass(order.status)}}">${{order.status}}</span>
                            <span style="font-size: 13px; font-weight: 500; color: #475569;">ETA: ${{Math.max(0, Math.round(remaining))}} min</span>
                        </div>
                    `;
                    listEl.appendChild(div);
                }});
                
                if (!hasActive) {{
                    listEl.innerHTML = `<div class="empty-state">No active orders</div>`;
                }}
                if (!hasDelivered) {{
                    deliveredListEl.innerHTML = `<div class="empty-state">No delivered orders yet</div>`;
                }}
            }}

            const mapPickButton = document.getElementById("map-pick-order");
            const optimizerUrl = "http://127.0.0.1:8001/optimize";

            const sidebarElement = document.querySelector(".do-sidebar");
            if (sidebarElement) {{
                L.DomEvent.disableClickPropagation(sidebarElement);
            }}

            const platformColors = {{
                "Zepto": "#7c3aed",
                "Blinkit": "#eab308",
                "Instamart": "#f97316"
            }};

            function addCustomerMarker(order) {{
                const dropId = String(order.dropNodeId);
                if (!customerMarkers[dropId]) {{
                    const dropNode = graphData.nodes[dropId];
                    if (dropNode) {{
                        const radius = 17;
                        const circumference = 2 * Math.PI * radius;
                        const html = `
                            <div class="customer-avatar-marker ${{order.platform.toLowerCase()}}">
                                <img src="assets/avatars/avatar_${{order.avatarId}}.jpg" alt="Avatar" />
                                <svg class="avatar-progress-ring ${{order.platform.toLowerCase()}}">
                                    <circle cx="20" cy="20" r="${{radius}}" 
                                            stroke-dasharray="${{circumference}}" 
                                            stroke-dashoffset="0"
                                            id="progress-${{order.id}}" />
                                </svg>
                            </div>
                        `;

                        customerMarkers[dropId] = L.marker(dropNode, {{
                            icon: L.divIcon({{
                                className: '',
                                html: html,
                                iconSize: [40, 40],
                                iconAnchor: [20, 20]
                            }})
                        }}).addTo({map_name});
                    }}
                }}
            }}

            addCustomerMarker(activeOrders[0]);

            function setStatus(html) {{
                orderStatus.innerHTML = html;
            }}

            function formatMinutes(value) {{
                return `${{Math.round(value)}}m`;
            }}

            function orderStatusClass(status) {{
                if (status.includes("Preparing")) return "preparing";
                if (status.includes("Ready")) return "ready";
                if (status.includes("On the way")) return "moving";
                if (status.includes("Arrived")) return "arrived";
                return "delivered";
            }}

            function updateOrderStatuses() {{
                activeOrders.forEach((order) => {{
                    if (order.delivered) {{
                        order.status = "Delivered";
                        return;
                    }}

                    // Check if we are physically at the pickup node and it's ready
                    if (!order.is_picked_up && activeRouteNodeIds[currentRouteIndex] === String(order.pickupNodeId)) {{
                        if (simulationMinutesElapsed >= order.readyTime + 0.5) {{
                            order.is_picked_up = true;
                        }} else if (!isWaitingAtStore) {{
                            isWaitingAtStore = true;
                            waitStartMinutes = simulationMinutesElapsed;
                            waitTargetMinutes = order.readyTime + 0.5; // Half minute handoff so "Ready" is visible
                            setStatus(`Waiting at warehouse for order preparation (${{(waitTargetMinutes - waitStartMinutes).toFixed(1)}} min)...`);
                        }}
                    }}

                    if (!order.is_picked_up) {{
                        if (simulationMinutesElapsed < order.readyTime) {{
                            order.status = "Preparing order";
                        }} else {{
                            order.status = "Ready to pickup";
                        }}
                    }} else {{
                        if (activeRouteNodeIds[currentRouteIndex] === String(order.dropNodeId)) {{
                            order.status = "Arrived at your location";
                        }} else {{
                            order.status = "On the way";
                        }}
                    }}

                    // Update progress ring if marker is rendered
                    const progressCircle = document.getElementById(`progress-${{order.id}}`);
                    if (progressCircle && !order.delivered) {{
                        const elapsed = Math.max(0, simulationMinutesElapsed - order.createdTime);
                        const total = order.deadlineTime - order.createdTime;
                        const percentage = Math.min(1, elapsed / total);
                        const radius = 17;
                        const circumference = 2 * Math.PI * radius;
                        progressCircle.style.strokeDashoffset = circumference * percentage;
                    }}
                }});
            }}

            function nextStopInfo() {{
                for (
                    let index = currentRouteIndex;
                    index < activeRouteNodeIds.length;
                    index += 1
                ) {{
                    const nodeId = activeRouteNodeIds[index];

                    if (activeStopLabels[nodeId]) {{
                        return {{
                            label: activeStopLabels[nodeId],
                            distance: Math.round(
                                routeDistanceNodeIds(
                                    activeRouteNodeIds.slice(
                                        currentRouteIndex,
                                        index + 1
                                    )
                                )
                            )
                        }};
                    }}
                }}

                return {{
                    label: "All committed drops complete",
                    distance: 0
                }};
            }}

            function updateCurrentStatus() {{
                if (activeRouteNodeIds.length === 0) {{
                    currentStatus.innerHTML = `
                        <strong>Rider is idle</strong><br>
                        No active route.
                    `;
                    return;
                }}

                currentStatus.innerHTML = `
                    <strong>Rider Status</strong><br>
                    <span class="status-big">${{formatMinutes(simulationMinutesElapsed)}} elapsed</span>
                    Active orders: ${{activeOrders.filter((order) => !order.delivered).length}}<br>
                    Next stop: ${{nextStopInfo().label}}
                `;
            }}

            function routeDistanceMeters(fromPoint, toPoint) {{
                const earthRadiusMeters = 6371000;
                const fromLat = fromPoint[0] * Math.PI / 180;
                const toLat = toPoint[0] * Math.PI / 180;
                const deltaLat = (toPoint[0] - fromPoint[0]) * Math.PI / 180;
                const deltaLon = (toPoint[1] - fromPoint[1]) * Math.PI / 180;
                const a =
                    Math.sin(deltaLat / 2) * Math.sin(deltaLat / 2) +
                    Math.cos(fromLat) * Math.cos(toLat) *
                    Math.sin(deltaLon / 2) * Math.sin(deltaLon / 2);
                const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

                return earthRadiusMeters * c;
            }}

            function routeBearing(fromPoint, toPoint) {{
                const fromLat = fromPoint[0] * Math.PI / 180;
                const toLat = toPoint[0] * Math.PI / 180;
                const deltaLon = (toPoint[1] - fromPoint[1]) * Math.PI / 180;
                const y = Math.sin(deltaLon) * Math.cos(toLat);
                const x =
                    Math.cos(fromLat) * Math.sin(toLat) -
                    Math.sin(fromLat) * Math.cos(toLat) * Math.cos(deltaLon);

                return (Math.atan2(y, x) * 180 / Math.PI + 360) % 360;
            }}

            function angularDifference(firstBearing, secondBearing) {{
                const difference = Math.abs(firstBearing - secondBearing) % 360;

                return difference > 180 ? 360 - difference : difference;
            }}

            function turnAngleAt(pointIndex) {{
                if (
                    pointIndex <= 0 ||
                    pointIndex >= agentRoutePoints.length - 1
                ) {{
                    return 0;
                }}

                const incomingBearing = routeBearing(
                    agentRoutePoints[pointIndex - 1],
                    agentRoutePoints[pointIndex]
                );
                const outgoingBearing = routeBearing(
                    agentRoutePoints[pointIndex],
                    agentRoutePoints[pointIndex + 1]
                );

                return angularDifference(incomingBearing, outgoingBearing);
            }}

            function turnSlowdownFactor() {{
                const currentTurnAngle = turnAngleAt(currentRouteIndex);
                const nextTurnAngle = turnAngleAt(currentRouteIndex + 1);
                const turnAngle = Math.max(currentTurnAngle, nextTurnAngle);

                if (turnAngle < 25) {{
                    return 1;
                }}

                return 1 + Math.min(0.45, turnAngle / 260);
            }}

            function rotateAgentTowardNextPoint() {{
                if (currentRouteIndex >= agentRoutePoints.length - 1) {{
                    return;
                }}

                const bearing = routeBearing(
                    agentRoutePoints[currentRouteIndex],
                    agentRoutePoints[currentRouteIndex + 1]
                );

                agentImage.style.transform = `rotate(${{bearing}}deg)`;
            }}

            function calculateSegmentDuration() {{
                if (currentRouteIndex >= agentRoutePoints.length - 1) {{
                    return minSegmentDurationMs;
                }}

                const distance = routeDistanceMeters(
                    agentRoutePoints[currentRouteIndex],
                    agentRoutePoints[currentRouteIndex + 1]
                );

                activeTurnSlowdown = turnSlowdownFactor();

                return Math.max(
                    minSegmentDurationMs,
                    distance * millisecondsPerMeter * activeTurnSlowdown
                );
            }}

            function interpolatePoint(fromPoint, toPoint, progress) {{
                return [
                    fromPoint[0] + (toPoint[0] - fromPoint[0]) * progress,
                    fromPoint[1] + (toPoint[1] - fromPoint[1]) * progress
                ];
            }}

            function smoothTurnProgress(progress) {{
                if (activeTurnSlowdown <= 1.05) {{
                    return progress;
                }}

                return progress * progress * (3 - 2 * progress);
            }}

            function nearestNodeId(lat, lon) {{
                let nearest = null;
                let bestDistance = Infinity;

                for (const [nodeId, point] of Object.entries(graphData.nodes)) {{
                    const distance =
                        (point[0] - lat) * (point[0] - lat) +
                        (point[1] - lon) * (point[1] - lon);

                    if (distance < bestDistance) {{
                        bestDistance = distance;
                        nearest = nodeId;
                    }}
                }}

                return nearest;
            }}

            function routeDistanceNodeIds(routeNodeIds) {{
                let distance = 0;

                for (let index = 0; index < routeNodeIds.length - 1; index += 1) {{
                    distance += edgeLengthMeters(
                        routeNodeIds[index],
                        routeNodeIds[index + 1]
                    );
                }}

                return distance;
            }}

            function edgeLengthMeters(fromNodeId, toNodeId) {{
                const edge = (graphData.adjacency[fromNodeId] || []).find(
                    (candidateEdge) => candidateEdge.to === toNodeId
                );

                if (edge) {{
                    return edge.length;
                }}

                return routeDistanceMeters(
                    graphData.nodes[fromNodeId],
                    graphData.nodes[toNodeId]
                );
            }}

            function updateActiveRoute(routeNodeIds) {{
                const wasIdle = (activeRouteNodeIds.length === 0);
                const traversed = activeRouteNodeIds.slice(0, currentRouteIndex);
                activeRouteNodeIds = traversed.concat(routeNodeIds.map(nodeId => String(nodeId)));
                
                agentRoutePoints = activeRouteNodeIds.map(
                    (nodeId) => graphData.nodes[nodeId]
                );

                if (wasIdle) {{
                    currentRouteIndex = 0;
                    lastSegmentElapsedMinutes = simulationMinutesElapsed;
                    movingAgentMarker.setLatLng(agentRoutePoints[0]);
                    rotateAgentTowardNextPoint();
                }}

                const remainingRoute = agentRoutePoints.slice(currentRouteIndex);
                activeRouteLine.setLatLngs(remainingRoute);

                updateCurrentStatus();
                renderOrdersBoard();

                if (isPlaying && !animationFrameId) {{
                    segmentStartTime = null;
                    animationFrameId = requestAnimationFrame(animateAgent);
                }}
            }}

            function resetLocalRouteState() {{
                activeOrders = [];
                for (const id in customerMarkers) {{
                    customerMarkers[id].remove();
                }}
                customerMarkers = {{}};
                activeRouteNodeIds = [];
                activeStopNodeIds = [];
                activeStopLabels = {{}};
                agentRoutePoints = [];
                currentRouteIndex = 0;
                simulationMinutesElapsed = 0.0;
                lastSegmentElapsedMinutes = 0.0;
                currentSegmentTravelMinutes = 0.0;
                activeRouteLine.setLatLngs([]);
            }}

            function animateAgent(timestamp) {{
                if (!isPlaying) {{
                    animationFrameId = null;
                    segmentStartTime = null;
                    waitStartTimestamp = null;
                    return;
                }}

                if (isWaitingAtStore) {{
                    if (waitStartTimestamp === null) {{
                        waitStartTimestamp = timestamp;
                    }}

                    const waitProgress = Math.min(1, (timestamp - waitStartTimestamp) / waitDurationMs);
                    simulationMinutesElapsed = waitStartMinutes + waitProgress * (waitTargetMinutes - waitStartMinutes);
                    
                    updateCurrentStatus();
                    updateOrderStatuses();
                    renderOrdersBoard();

                    if (waitProgress >= 1) {{
                        isWaitingAtStore = false;
                        waitStartTimestamp = null;
                        lastSegmentElapsedMinutes = waitTargetMinutes;
                        simulationMinutesElapsed = waitTargetMinutes;
                        segmentStartTime = null;
                    }}

                    if (isPlaying) {{
                        animationFrameId = requestAnimationFrame(animateAgent);
                    }}
                    return;
                }}

                if (currentRouteIndex >= agentRoutePoints.length - 1) {{
                    animationFrameId = null;
                    segmentStartTime = null;
                    activeRouteNodeIds = [];
                    activeStopNodeIds = [];
                    activeStopLabels = {{}};
                    agentRoutePoints = [];
                    currentRouteIndex = 0;
                    activeRouteLine.setLatLngs([]);
                    
                    // Mark the final order(s) as delivered since the route has ended
                    activeOrders.forEach((order) => {{
                        if (order.is_delivering) {{
                            order.delivered = true;
                            order.is_delivering = false;
                            order.status = "Delivered";
                            const dropIdStr = String(order.dropNodeId);
                            if (customerMarkers[dropIdStr]) {{
                                customerMarkers[dropIdStr].remove();
                                delete customerMarkers[dropIdStr];
                            }}
                            setStatus(`Order #${{order.id}} delivered!`);
                        }}
                    }});

                    setStatus("Delivery completed. Ready for the next order.");
                    updateCurrentStatus();
                    renderOrdersBoard();
                    return;
                }}

                if (segmentStartTime === null) {{
                    segmentStartTime = timestamp;
                    segmentDurationMs = calculateSegmentDuration();
                    
                    const currentPoint = agentRoutePoints[currentRouteIndex];
                    const nextPoint = agentRoutePoints[currentRouteIndex + 1];
                    const distance = routeDistanceMeters(currentPoint, nextPoint);
                    currentSegmentTravelMinutes = distance / AVERAGE_SPEED_M_PER_MIN;
                    
                    rotateAgentTowardNextPoint();
                }}

                const rawSegmentProgress = Math.min(
                    1,
                    (timestamp - segmentStartTime) / segmentDurationMs
                );
                const segmentProgress = smoothTurnProgress(rawSegmentProgress);
                const currentPoint = agentRoutePoints[currentRouteIndex];
                const nextPoint = agentRoutePoints[currentRouteIndex + 1];
                const markerPoint = interpolatePoint(
                    currentPoint,
                    nextPoint,
                    segmentProgress
                );

                movingAgentMarker.setLatLng(markerPoint);

                simulationMinutesElapsed = lastSegmentElapsedMinutes + rawSegmentProgress * currentSegmentTravelMinutes;
                updateCurrentStatus();
                updateOrderStatuses();
                renderOrdersBoard();

                if (rawSegmentProgress >= 1) {{
                    currentRouteIndex += 1;
                    movingAgentMarker.setLatLng(nextPoint);
                    
                    lastSegmentElapsedMinutes += currentSegmentTravelMinutes;
                    simulationMinutesElapsed = lastSegmentElapsedMinutes;

                    agentCurrentNodeId = String(activeRouteNodeIds[currentRouteIndex] || agentCurrentNodeId);

                    const remainingRoute = agentRoutePoints.slice(currentRouteIndex);
                    activeRouteLine.setLatLngs(remainingRoute);
                    
                    segmentStartTime = null;

                    const reachedNodeId = activeRouteNodeIds[currentRouteIndex];
                    
                    activeOrders.forEach((order) => {{
                        if (!order.delivered && String(order.pickupNodeId) === String(reachedNodeId)) {{
                            const dropIdx = activeRouteNodeIds.indexOf(String(order.dropNodeId));
                        }}

                        if (!order.delivered && String(order.dropNodeId) === String(reachedNodeId)) {{
                            const pickupIdx = activeRouteNodeIds.indexOf(String(order.pickupNodeId));
                            const reachedPickup = order.is_picked_up || (pickupIdx !== -1 && currentRouteIndex >= pickupIdx);
                            if (reachedPickup) {{
                                if (!order.is_delivering) {{
                                    order.is_delivering = true;
                                    isWaitingAtStore = true;
                                    waitStartMinutes = simulationMinutesElapsed;
                                    waitTargetMinutes = simulationMinutesElapsed + 0.5; // 0.5 min dropoff
                                    setStatus(`Arrived at location. Handing over order #${{order.id}}...`);
                                }}
                            }}
                        }}
                    }});
                }}

                // Mark any orders that finished delivering
                activeOrders.forEach((order) => {{
                    if (order.is_delivering && !isWaitingAtStore) {{
                        order.delivered = true;
                        order.is_delivering = false;
                        order.status = "Delivered";
                        const dropIdStr = String(order.dropNodeId);
                        if (customerMarkers[dropIdStr]) {{
                            customerMarkers[dropIdStr].remove();
                            delete customerMarkers[dropIdStr];
                        }}
                        setStatus(`Order #${{order.id}} delivered!`);
                    }}
                }});

                if (isPlaying) {{
                    animationFrameId = requestAnimationFrame(animateAgent);
                }}
            }}

            function playAgentRoute() {{
                if (isPlaying) return;
                isPlaying = true;
                animationFrameId = requestAnimationFrame(animateAgent);
            }}

            function pauseAgentRoute() {{
                isPlaying = false;
                cancelAnimationFrame(animationFrameId);
                animationFrameId = null;
                segmentStartTime = null;
            }}

            function restartAgentRoute() {{
                pauseAgentRoute();
                activeOrders = [];
                for (const id in customerMarkers) {{
                    customerMarkers[id].remove();
                }}
                customerMarkers = {{}};
                activeRouteNodeIds = [];
                activeStopNodeIds = [];
                activeStopLabels = {{}};
                agentRoutePoints = [];
                currentRouteIndex = 0;
                simulationMinutesElapsed = 0.0;
                lastSegmentElapsedMinutes = 0.0;
                currentSegmentTravelMinutes = 0.0;
                activeRouteLine.setLatLngs([]);
                
                movingAgentMarker.setLatLng(agentRoutePoints[0] || [0,0]);
                agentCurrentNodeId = String(initialOrder.pickupNodeId);
                
                updateCurrentStatus();
                renderOrdersBoard();
            }}
            document.getElementById("play-agent-route").addEventListener("click", playAgentRoute);
            document.getElementById("pause-agent-route").addEventListener("click", pauseAgentRoute);
            document.getElementById("restart-agent-route").addEventListener("click", restartAgentRoute);

            async function createOrderAtNode(customerNodeId) {{
                if (activeOrders.filter(o => !o.delivered).length >= 3) {{
                    setStatus("<strong>Capacity Full</strong><br>Agent cannot carry more than 3 active orders.");
                    return;
                }}

                if (isOptimizing) return;
                isOptimizing = true;
                const platform = document.getElementById("order-platform").value;
                const sla_minutes = Number(document.getElementById("order-sla").value || 15);
                
                try {{
                    const activeOrdersPayload = activeOrders
                        .filter(o => !o.delivered)
                        .map(o => ({{
                            id: o.id,
                            platform: o.platform,
                            pickup_node: Number(o.pickupNodeId),
                            customer_node: Number(o.dropNodeId),
                            created_time: Number(o.createdTime),
                            prep_time: Number(o.prepTime),
                            sla_minutes: Number(o.slaMinutes),
                            is_picked_up: Boolean(o.is_picked_up)
                        }}));

                    const currentNode = Number(agentCurrentNodeId);

                    setStatus("Calculating optimal route...");

                    const response = await fetch(
                        optimizerUrl,
                        {{
                            method: "POST",
                            headers: {{
                                "Content-Type": "application/json"
                            }},
                            body: JSON.stringify({{
                                platform,
                                customer_node: Number(customerNodeId),
                                sla_minutes,
                                current_node: currentNode,
                                current_time: simulationMinutesElapsed,
                                active_orders: activeOrdersPayload
                            }})
                        }}
                    );

                    const result = await response.json();

                    console.log("Optimizer Response:", result);

                    if (!result.accepted) {{
                        setStatus(`<strong>Order Rejected</strong><br>Reason: ${{result.reason || "SLA would be violated"}}`);
                        return;
                    }}

                    const acceptedRoute = result.route_nodes;
                    updateActiveRoute(acceptedRoute);

                    const newCustomer = getUniqueCustomer(activeOrders);
                    
                    const newOrderObj = {{
                        id: nextOrderId++,
                        platform: result.platform,
                        customerName: newCustomer.name,
                        avatarId: newCustomer.avatarId,
                        pickupNodeId: String(result.pickup_node),
                        dropNodeId: String(customerNodeId),
                        createdTime: simulationMinutesElapsed,
                        prepTime: Number(result.prep_time),
                        slaMinutes: sla_minutes,
                        readyTime: simulationMinutesElapsed + Number(result.prep_time),
                        deadlineTime: simulationMinutesElapsed + sla_minutes,
                        status: "Preparing order",
                        delivered: false,
                        is_picked_up: false,
                        storeName: result.store_name || "Warehouse"
                    }};

                    activeOrders.push(newOrderObj);
                    addCustomerMarker(newOrderObj);

                    activeStopLabels[String(result.pickup_node)] = `Pickup ${{result.platform}} from ${{result.store_name}}`;
                    activeStopLabels[String(customerNodeId)] = `Drop ${{result.platform}} Customer`;

                    setStatus(`
                        <strong>ORDER ACCEPTED</strong><br>
                        Added order from ${{result.store_name}}<br>
                        Added travel time: ${{result.travel_time.toFixed(1)}} min<br>
                        Sequence: ${{result.sequence.join(" → ")}}

                    `);

                    renderOrdersBoard();

                }} catch (error) {{
                    console.error("Error creating order:", error);
                    setStatus("Error optimizing route: " + error.toString());
                }} finally {{
                    isOptimizing = false;
                }}
            }}

            document.getElementById("random-order").addEventListener("click", function () {{
                const nodeIds = Object.keys(graphData.nodes);
                const customerNodeId = nodeIds[
                    Math.floor(Math.random() * nodeIds.length)
                ];
                createOrderAtNode(customerNodeId);
            }});

            document.getElementById("map-pick-order").addEventListener("click", function () {{
                pickFromMap = true;
                mapPickButton.classList.add("active");
                {map_name}.getContainer().style.cursor = "crosshair";
                setStatus("Click a customer location on the map.");
            }});

            {map_name}.on("click", function (event) {{
                if (!pickFromMap) return;
                pickFromMap = false;
                mapPickButton.classList.remove("active");
                {map_name}.getContainer().style.cursor = "";
                createOrderAtNode(
                    nearestNodeId(
                        event.latlng.lat,
                        event.latlng.lng
                    )
                );
            }});

            renderOrdersBoard();
            updateCurrentStatus();
        }});
    """

    with open(
        "visualization/ui/sidebar.html",
        "r"
    ) as f:

        sidebar_html = f.read()


    with open(
        "visualization/ui/styles.css",
        "r"
    ) as f:

        styles_css = f.read()

    folium_map.get_root().html.add_child(

        folium.Element(

            f"<style>{styles_css}</style>"

        )

    )

    folium_map.get_root().html.add_child(

        folium.Element(

            sidebar_html

        )

    )

    folium_map.get_root().script.add_child(
        folium.Element(animation_script)
    )


def plot_graph_with_stores(
    graph,
    agent,
    order,
    route
):

    stores = pd.read_csv(
        "data/darkstores/darkstores.csv"
    )

    customer_node = graph.nodes[
        order.customer_node
    ]

    center_lat = stores["lat"].mean()
    center_lon = stores["lon"].mean()

    m = folium.Map(

        location=[
            center_lat,
            center_lon
        ],

        zoom_start=13,

        tiles="CartoDB Voyager"

    )

    # -------------------------
    # DARK STORES
    # -------------------------

    for _, row in stores.iterrows():

        print(

            row["name"],

            row["platform"]

        )

        folium.Marker(

            [

                row["lat"],
                row["lon"]

            ],

            popup=row["name"],

            icon=folium.CustomIcon(

                platform_icon_path(
                    row["platform"]
                ),

                icon_size=(36, 36),

                icon_anchor=(18, 18)

            )

        ).add_to(m)

    # Initial Customer marker removed, we render avatars dynamically in Javascript.

    # -------------------------
    # ROUTE
    # -------------------------

    route_points = []

    for node in route:

        node_data = graph.nodes[node]

        route_points.append(

            [

                node_data["y"],

                node_data["x"]

            ]

        )

    print(
        "Route Nodes:",
        len(route)
    )

    add_agent_animation(
        m,
        graph,
        stores,
        route,
        [
            order.pickup_node,
            order.customer_node
        ],
        order
    )

    # Auto zoom to route

    m.fit_bounds(
        route_points
    )

    m.save(
        "map.html"
    )

    print(
        "Saved map.html"
    )
