class Order:

    def __init__(
        self,
        platform,
        pickup_node,
        customer_node,
        created_time,
        prep_time=3,
        sla_minutes=15,
        is_picked_up=False
    ):

        self.platform = platform

        self.pickup_node = pickup_node

        self.customer_node = customer_node

        # Time attributes

        self.created_time = created_time

        self.prep_time = prep_time

        self.ready_time = (
            created_time +
            prep_time
        )

        self.sla_minutes = sla_minutes

        self.deadline_time = (
            created_time +
            sla_minutes
        )

        self.is_picked_up = is_picked_up

    def __str__(self):

        return (

            f"{self.platform} | "

            f"Ready: {self.ready_time} min | "

            f"Deadline: {self.deadline_time} min"

        )
