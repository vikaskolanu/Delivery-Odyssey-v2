from core.utils import distance_to_minutes


MAX_EXTRA_TIME = 7


def evaluate_order(
    active_orders_count,
    extra_distance_meters
):

    # Rider is idle

    if active_orders_count == 0:

        return {

            "decision": "ACCEPT",

            "reason": "Rider is idle",

            "extra_time": 0

        }

    extra_time = distance_to_minutes(

        extra_distance_meters

    )

    if extra_time <= MAX_EXTRA_TIME:

        return {

            "decision": "ACCEPT",

            "reason": f"Only adds {extra_time} min",

            "extra_time": extra_time

        }

    return {

        "decision": "REJECT",

        "reason": f"Adds {extra_time} min",

        "extra_time": extra_time

    }