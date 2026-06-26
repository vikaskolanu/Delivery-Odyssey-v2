import folium
import pandas as pd
import json



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
            const MAX_EXTRA_TIME = 7;
            const graphData = {graph_json};
            const storesData = {stores_json};
            const initialOrder = {initial_order_json};
            let activeRouteNodeIds = {route_json};
            let activeStopNodeIds = {required_stops_json};
            let activeStopLabels = {{}};
            let activeOrderCount = 0;
            let customerMarker = null;
            let pickupMarker = null;
            
            let agentRoutePoints = activeRouteNodeIds.map(
                (nodeId) => graphData.nodes[String(nodeId)]
            );
            let candidateOrder = null;
            let pickFromMap = false;
            let candidateMarkers = [];
            let candidateRouteLine = null;

            const initialPickupStore = storesData.find(
                (store) => store.nodeId === initialOrder.pickupNodeId
            );
            activeStopLabels[initialOrder.pickupNodeId] = `Pickup ${{initialOrder.platform}} from ${{initialPickupStore ? initialPickupStore.name : "warehouse"}}`;
            activeStopLabels[initialOrder.dropNodeId] = "Drop original customer";

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
            ).addTo({map_name}).bindTooltip("Delivery Route");

            let currentRouteIndex = 0;
            let animationFrameId = null;
            let segmentStartTime = null;
            let segmentDurationMs = 600;
            let activeTurnSlowdown = 1;
            const minSegmentDurationMs = 120;
            const millisecondsPerMeter = 11;
            const agentImage = document.getElementById("moving-agent-image");
            const orderStatus = document.getElementById("order-status");
            const currentStatus = document.getElementById("current-status");
            const mapPickButton = document.getElementById("map-pick-order");

            L.DomEvent.disableClickPropagation(
                document.querySelector(".order-sidebar")
            );

            function setStatus(html) {{
                orderStatus.innerHTML = html;
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

                const currentStatus =
                    document.getElementById(
                        "current-status"
                    );

                if (
                    activeRouteNodeIds.length === 0
                ) {{

                    currentStatus.innerHTML = `
                        Rider is idle
                    `;

                    return;
                }}

                currentStatus.innerHTML = `
                    <strong>
                        Active Delivery
                    </strong><br>

                    Remaining Stops:
                    ${{
                        activeRouteNodeIds.length
                        -
                        currentRouteIndex
                    }}
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

            function nearestPlatformStore(platform, customerPoint) {{
                let nearest = null;
                let bestDistance = Infinity;

                for (const store of storesData) {{
                    if (store.platform !== platform) {{
                        continue;
                    }}

                    const distance = routeDistanceMeters(
                        [store.lat, store.lon],
                        customerPoint
                    );

                    if (distance < bestDistance) {{
                        bestDistance = distance;
                        nearest = store;
                    }}
                }}

                return nearest;
            }}

            function shortestPath(startNodeId, endNodeId) {{
                const distances = {{}};
                const previous = {{}};
                const visited = new Set();
                const queue = new Set(Object.keys(graphData.nodes));

                for (const nodeId of queue) {{
                    distances[nodeId] = Infinity;
                }}

                distances[startNodeId] = 0;

                while (queue.size > 0) {{
                    let current = null;
                    let bestDistance = Infinity;

                    for (const nodeId of queue) {{
                        if (distances[nodeId] < bestDistance) {{
                            bestDistance = distances[nodeId];
                            current = nodeId;
                        }}
                    }}

                    if (current === null || current === endNodeId) {{
                        break;
                    }}

                    queue.delete(current);
                    visited.add(current);

                    for (const edge of graphData.adjacency[current] || []) {{
                        if (visited.has(edge.to)) {{
                            continue;
                        }}

                        const candidateDistance = distances[current] + edge.length;

                        if (candidateDistance < distances[edge.to]) {{
                            distances[edge.to] = candidateDistance;
                            previous[edge.to] = current;
                        }}
                    }}
                }}

                if (
                    startNodeId !== endNodeId &&
                    previous[endNodeId] === undefined
                ) {{
                    return null;
                }}

                const path = [endNodeId];
                let cursor = endNodeId;

                while (cursor !== startNodeId) {{
                    cursor = previous[cursor];
                    path.unshift(cursor);
                }}

                return path;
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

            function skippedRouteContainsStop(
                routeNodeIds,
                pickupIndex,
                dropIndex
            ) {{
                const skippedNodes = new Set(
                    routeNodeIds.slice(pickupIndex + 1, dropIndex)
                );

                return activeStopNodeIds.some(
                    (stopNodeId) => skippedNodes.has(stopNodeId)
                );
            }}

            function buildCandidateRoute(
                remainingRoute,
                pickupNodeId,
                dropNodeId
            ) {{
                const oldDistance = routeDistanceNodeIds(remainingRoute);
                let best = null;

                for (
                    let pickupIndex = 0;
                    pickupIndex < remainingRoute.length;
                    pickupIndex += 1
                ) {{
                    for (
                        let dropIndex = pickupIndex;
                        dropIndex < remainingRoute.length;
                        dropIndex += 1
                    ) {{
                        if (
                            skippedRouteContainsStop(
                                remainingRoute,
                                pickupIndex,
                                dropIndex
                            )
                        ) {{
                            continue;
                        }}

                        const pickupPath = shortestPath(
                            remainingRoute[pickupIndex],
                            pickupNodeId
                        );
                        const deliveryPath = shortestPath(
                            pickupNodeId,
                            dropNodeId
                        );
                        const rejoinPath = shortestPath(
                            dropNodeId,
                            remainingRoute[dropIndex]
                        );

                        if (!pickupPath || !deliveryPath || !rejoinPath) {{
                            continue;
                        }}

                        const candidateRoute = [
                            ...remainingRoute.slice(0, pickupIndex + 1),
                            ...pickupPath.slice(1),
                            ...deliveryPath.slice(1),
                            ...rejoinPath.slice(1),
                            ...remainingRoute.slice(dropIndex + 1)
                        ];
                        const newDistance = routeDistanceNodeIds(candidateRoute);
                        const extraDistance = Math.max(
                            0,
                            newDistance - oldDistance
                        );

                        if (
                            best === null ||
                            extraDistance < best.extraDistance
                        ) {{
                            best = {{
                                route: candidateRoute,
                                oldDistance,
                                newDistance,
                                extraDistance,
                                pickupIndex,
                                dropIndex
                            }};
                        }}
                    }}
                }}

                return best;
            }}

            function clearCandidateMarkers() {{
                for (const marker of candidateMarkers) {{
                    marker.remove();
                }}

                candidateMarkers = [];

                if (candidateRouteLine) {{
                    candidateRouteLine.remove();
                    candidateRouteLine = null;
                }}
            }}

            function showCandidateMarkers(order) {{
                clearCandidateMarkers();

                candidateMarkers.push(
                    L.marker(
                        [order.store.lat, order.store.lon],
                        {{
                            title: order.store.name
                        }}
                    ).addTo({map_name}).bindPopup(`Pickup: ${{order.store.name}}`)
                );
                candidateMarkers.push(
                    L.circleMarker(
                        graphData.nodes[order.dropNodeId],
                        {{
                            radius: 8,
                            color: "#b42318",
                            fill: true,
                            fillColor: "#ffdd55",
                            fillOpacity: 1
                        }}
                    ).addTo({map_name}).bindPopup("Candidate Customer")
                );

                candidateRouteLine = L.polyline(
                    order.insertion.route.map(
                        (nodeId) => graphData.nodes[nodeId]
                    ),
                    {{
                        color: "#ff8a00",
                        weight: 4,
                        opacity: 0.85,
                        dashArray: "8 8",
                        lineCap: "round"
                    }}
                ).addTo({map_name}).bindTooltip("Candidate Route");
            }}

            function evaluateOrder(platform, customerNodeId) {{

                const customerPoint = graphData.nodes[customerNodeId];

                const store = nearestPlatformStore(
                    platform,
                    customerPoint
                );

                const pickupNodeId = store.nodeId;

                const orderPath = shortestPath(
                    pickupNodeId,
                    customerNodeId
                );

                if (!orderPath) {{

                    setStatus(
                        "No route found for this order."
                    );

                    return null;
                }}

                const orderDistance =
                    routeDistanceNodeIds(
                        orderPath
                    );

                const remainingRoute =
                    activeRouteNodeIds.slice(
                        currentRouteIndex
                    );

                const insertion =
                    buildCandidateRoute(
                        remainingRoute,
                        pickupNodeId,
                        customerNodeId
                    );

                if (!insertion) {{

                    setStatus(
                        "No insertion route found."
                    );

                    return null;
                }}

                const extraDistance = Math.max(
                    1,
                    insertion.extraDistance
                );

                const extraTime =
                    extraDistance /
                    AVERAGE_SPEED_M_PER_MIN;

                const detourRatio =
                    extraDistance /
                    Math.max(
                        1,
                        orderDistance
                    );

                let recommendation;
                let reason;

                // IDLE RIDER

                if (activeOrderCount === 0) {{

                    recommendation = "ACCEPT";

                    reason =
                        "Rider is idle";
                }}

                // ACTIVE RIDER

                else if (

                    extraTime <= 7 &&
                    detourRatio <= 0.4

                ) {{

                    recommendation = "ACCEPT";

                    reason =
                        `Adds only ${{extraTime.toFixed(1)}} min`;
                }}

                else {{

                    recommendation = "REJECT";

                    reason =
                        `Adds ${{extraTime.toFixed(1)}} min and detour is too large`;
                }}

                return {{

                    platform,

                    store,

                    pickupNodeId,

                    dropNodeId:
                        customerNodeId,

                    orderDistance,

                    insertion,

                    extraDistance,

                    extraTime,

                    detourRatio,

                    reason,

                    recommendation

                }};
            }}

            function renderOrder(order) {{
                candidateOrder = order;
                showCandidateMarkers(order);

                setStatus(`
                    <strong>${{order.recommendation}}</strong><br>
                    Platform: ${{order.platform}}<br>
                    Pickup: ${{order.store.name}}<br>
                    Customer: selected map node<br>
                    Reward: ₹${{order.reward}}<br>
                    Direct order distance: ${{Math.round(order.orderDistance)}} m<br>
                    Extra distance: ${{Math.round(order.insertion.extraDistance)}} m<br>
                    Score: ${{order.score.toFixed(3)}} ₹/extra m<br>
                    Detour ratio: ${{order.detourRatio.toFixed(2)}}
                `);
            }}

            async function createOrderAtNode(customerNodeId) {{

                const platform =
                    document.getElementById(
                        "order-platform"
                    ).value;

                try {{

                    if (customerMarker) {{
                        customerMarker.remove();
                    }}

                    if (pickupMarker) {{
                        pickupMarker.remove();
                    }}

                    customerMarker = L.circleMarker(

                        graphData.nodes[String(customerNodeId)],

                        {{

                            radius: 10,

                            color: "red",

                            fillColor: "red",

                            fillOpacity: 1

                        }}

                    ).addTo({map_name});

                    const response = await fetch(

                        "http://127.0.0.1:8000/optimize",

                        {{

                            method: "POST",

                            headers: {{

                                "Content-Type":
                                    "application/json"

                            }},

                            body: JSON.stringify({{

                                platform,

                                customer_node:
                                    Number(customerNodeId)

                            }})

                        }}

                    );

                    const result =
                        await response.json();

                    console.log(
                        "Optimizer Response:",
                        result
                    );

                    if (!result.accepted) {{

                        setStatus(
                            "Order Rejected"
                        );

                        return;
                    }}

                    setStatus(`

                        <strong>ORDER ACCEPTED</strong><br>

                        Customer:
                        ${{
                            customerNodeId
                        }}<br>

                        Distance:
                        ${{
                            result.distance.toFixed(0)
                        }} m<br>

                        Travel Time:
                        ${{
                            result.travel_time.toFixed(1)
                        }} min

                    `);

                    updateActiveRoute(
                        result.route_nodes
                    );

                }}

                catch(error) {{

                    console.error(
                        error
                    );

                    setStatus(
                        error.toString()
                    );

                }}

            }}

            function updateActiveRoute(routeNodeIds) {{

                activeRouteNodeIds = routeNodeIds.map(
                    nodeId => String(nodeId)
                );

                agentRoutePoints = activeRouteNodeIds.map(
                    nodeId => graphData.nodes[nodeId]
                );

                activeRouteLine.setLatLngs(
                    agentRoutePoints
                );

                updateCurrentStatus();

            }}

            updateCurrentStatus();
            rotateAgentTowardNextPoint();

            function animateAgent(timestamp) {{
                if (currentRouteIndex >= agentRoutePoints.length - 1) {{
                    animationFrameId = null;
                    segmentStartTime = null;
                    return;
                }}

                if (segmentStartTime === null) {{
                    segmentStartTime = timestamp;
                    segmentDurationMs = calculateSegmentDuration();
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

                if (rawSegmentProgress >= 1) {{
                    currentRouteIndex += 1;
                    movingAgentMarker.setLatLng(
                        nextPoint
                    );

                    // NEW ---- shrink visible route
                    const remainingRoute = agentRoutePoints.slice(
                        currentRouteIndex
                    );
                    activeRouteLine.setLatLngs(
                        remainingRoute
                    );
                    segmentStartTime = null;
                    updateCurrentStatus();
                }}

                animationFrameId = requestAnimationFrame(animateAgent);
            }}

            function playAgentRoute() {{
                if (animationFrameId !== null) {{
                    return;
                }}

                animationFrameId = requestAnimationFrame(animateAgent);
            }}

            function pauseAgentRoute() {{
                cancelAnimationFrame(animationFrameId);
                animationFrameId = null;
                segmentStartTime = null;
            }}

            function restartAgentRoute() {{
                pauseAgentRoute();
                currentRouteIndex = 0;
                movingAgentMarker.setLatLng(agentRoutePoints[0]);
                rotateAgentTowardNextPoint();
            }}

            document
                .getElementById("play-agent-route")
                .addEventListener("click", playAgentRoute);

            document
                .getElementById("pause-agent-route")
                .addEventListener("click", pauseAgentRoute);

            document
                .getElementById("restart-agent-route")
                .addEventListener("click", restartAgentRoute);

            document
                .getElementById("random-order")
                .addEventListener("click", function () {{
                    const nodeIds = Object.keys(graphData.nodes);
                    const customerNodeId = nodeIds[
                        Math.floor(Math.random() * nodeIds.length)
                    ];

                    createOrderAtNode(customerNodeId);
                }});

            document
                .getElementById("map-pick-order")
                .addEventListener("click", function () {{
                    pickFromMap = true;
                    mapPickButton.classList.add("active");
                    {map_name}.getContainer().style.cursor = "crosshair";
                    setStatus("Click a customer location on the map.");
                }});

            {map_name}.on("click", function (event) {{
                if (!pickFromMap) {{
                    return;
                }}

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

    # -------------------------
    # CUSTOMER
    # -------------------------

    folium.CircleMarker(

        [

            customer_node["y"],

            customer_node["x"]

        ],

        radius=10,

        color="green",

        fill=True,

        fill_color="green",

        fill_opacity=1,

        popup="Customer"

    ).add_to(m)

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