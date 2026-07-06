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
            
            let agentRoutePoints = activeRouteNodeIds.map(
                (nodeId) => graphData.nodes[nodeId]
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
                html: '<img id="moving-agent-image" src="assets/Delivery_Agent_Icon.png">',
                iconSize: [35, 35],
                iconAnchor: [17, 17]
            }});

            const movingAgentMarker = L.marker(
                agentRoutePoints[0],
                {{
                    icon: agentIcon,
                    zIndexOffset: 1000
                }}
            ).addTo({map_name}).bindPopup("Delivery Agent");

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
            let isPlaying = false;
            let segmentStartTime = null;
            let segmentDurationMs = 600;
            let activeTurnSlowdown = 1;
            const minSegmentDurationMs = 120;
            const millisecondsPerMeter = 11;
            const agentImage = document.getElementById("moving-agent-image");
            const orderStatus = document.getElementById("order-status");
            const currentStatus = document.getElementById("current-status");
            const mapPickButton = document.getElementById("map-pick-order");
            const optimizerUrl = "http://127.0.0.1:8001/optimize";
            const agentResetUrl = "http://127.0.0.1:8001/agent/reset";

            const sidebarElement = document.querySelector(".do-sidebar");

            if (sidebarElement) {{
                L.DomEvent.disableClickPropagation(sidebarElement);
            }}

            function setStatus(html) {{
                orderStatus.innerHTML = html;
            }}

            async function resetBackendAgentState() {{
                try {{
                    await fetch(
                        agentResetUrl,
                        {{
                            method: "POST"
                        }}
                    );
                }} catch (error) {{
                    console.warn("Failed to reset backend state", error);
                }}
            }}

            function resetLocalRouteState() {{
                activeOrderCount = 0;
                activeRouteNodeIds = [];
                activeStopNodeIds = [];
                activeStopLabels = {{}};
                agentRoutePoints = [];
                currentRouteIndex = 0;
                activeRouteLine.setLatLngs([]);
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
                const nextStop = nextStopInfo();

                currentStatus.innerHTML = `
                    <strong>Rider is carrying ${{activeOrderCount}} active order${{activeOrderCount === 1 ? "" : "s"}}</strong><br>
                    Next: ${{nextStop.label}}<br>
                    Distance to next stop: ${{nextStop.distance}} m<br>
                    Committed reward: ₹${{committedReward}}
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

                    (
                        extraTime <= 12 &&
                        detourRatio <= 0.65
                    ) ||
                    order.reward / Math.max(1, extraDistance) >= 0.03

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

            function createOrderAtNode(customerNodeId) {{
                const platform = document.getElementById("order-platform").value;
                const order = evaluateOrder(platform, customerNodeId);

                if (order) {{
                    renderOrder(order);
                }}
            }}

            function updateActiveRoute(routeNodeIds) {{
                pauseAgentRoute();
                activeRouteNodeIds = routeNodeIds;
                agentRoutePoints = activeRouteNodeIds.map(
                    (nodeId) => graphData.nodes[nodeId]
                );
                currentRouteIndex = 0;
                activeRouteLine.setLatLngs(agentRoutePoints);
                movingAgentMarker.setLatLng(agentRoutePoints[0]);
                rotateAgentTowardNextPoint();
                {map_name}.fitBounds(agentRoutePoints);
                updateCurrentStatus();
            }}

            updateCurrentStatus();
            rotateAgentTowardNextPoint();

            function animateAgent(timestamp) {{
                if (!isPlaying) {{
                    animationFrameId = null;
                    segmentStartTime = null;
                    return;
                }}

                if (currentRouteIndex >= agentRoutePoints.length - 1) {{
                    animationFrameId = null;
                    segmentStartTime = null;
                    resetLocalRouteState();
                    resetBackendAgentState();
                    setStatus("Delivery completed. Ready for the next order.");
                    updateCurrentStatus();
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

                if (isPlaying) {{
                    animationFrameId = requestAnimationFrame(animateAgent);
                }}
            }}

            function playAgentRoute() {{
                if (isPlaying) {{
                    return;
                }}

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

            document
                .getElementById("accept-order")
                .addEventListener("click", function () {{
                    if (!candidateOrder) {{
                        setStatus("Create an order before accepting.");
                        return;
                    }}

                    const acceptedRoute = [
                        ...activeRouteNodeIds.slice(0, currentRouteIndex),
                        ...candidateOrder.insertion.route
                    ];

                    updateActiveRoute(acceptedRoute);
                    activeStopNodeIds.push(candidateOrder.pickupNodeId);
                    activeStopNodeIds.push(candidateOrder.dropNodeId);
                    activeStopLabels[candidateOrder.pickupNodeId] = `Pickup ${{candidateOrder.platform}} from ${{candidateOrder.store.name}}`;
                    activeStopLabels[candidateOrder.dropNodeId] = `Drop ${{candidateOrder.platform}} customer`;
                    activeOrderCount += 1;
                    committedReward += candidateOrder.reward;
                    updateCurrentStatus();
                    setStatus(`
                        Accepted ${{candidateOrder.platform}} order.<br>
                        Reward gained: ₹${{candidateOrder.reward}}<br>
                        New route distance: ${{Math.round(candidateOrder.insertion.newDistance)}} m
                    `);
                    candidateOrder = null;
                    clearCandidateMarkers();
                }});

            document
                .getElementById("reject-order")
                .addEventListener("click", function () {{
                    candidateOrder = null;
                    clearCandidateMarkers();
                    pickFromMap = false;
                    mapPickButton.classList.remove("active");
                    {map_name}.getContainer().style.cursor = "";
                    setStatus("Order rejected. Generate another candidate.");
                }});
        }});
    """
