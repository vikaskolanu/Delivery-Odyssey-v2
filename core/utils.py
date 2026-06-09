import math


def haversine_distance(

    lat1,
    lon1,
    lat2,
    lon2

):

    R = 6371000

    lat1 = math.radians(
        lat1
    )

    lat2 = math.radians(
        lat2
    )

    dlat = math.radians(
        lat2 - lat1
    )

    dlon = math.radians(
        lon2 - lon1
    )

    a = (

        math.sin(dlat / 2) ** 2

        +

        math.cos(lat1)

        *

        math.cos(lat2)

        *

        math.sin(dlon / 2) ** 2

    )

    c = 2 * math.atan2(

        math.sqrt(a),

        math.sqrt(1 - a)

    )

    return R * c


def nearest_platform_store(

    stores,

    platform,

    customer_lat,

    customer_lon

):

    platform_stores = stores[

        stores["platform"] == platform

    ]

    nearest_store = None

    best_distance = float(
        "inf"
    )

    for _, store in platform_stores.iterrows():

        distance = haversine_distance(

            customer_lat,

            customer_lon,

            store["lat"],

            store["lon"]

        )

        if distance < best_distance:

            best_distance = distance

            nearest_store = store

    return nearest_store