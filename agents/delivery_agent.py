class DeliveryAgent:

    def __init__(

        self,

        start_node

    ):

        self.current_node = start_node

        self.current_route = []

        self.active_orders = []

        self.completed_orders = []

        self.current_time = 0

        self.total_distance = 0

    def get_position(

        self

    ):

        return self.current_node

    def add_order(

        self,

        order

    ):

        self.active_orders.append(

            order

        )

    def complete_order(

        self,

        order

    ):

        if order in self.active_orders:

            self.active_orders.remove(

                order

            )

            self.completed_orders.append(

                order

            )

    def update_route(

        self,

        route_nodes

    ):

        self.current_route = route_nodes

    def active_order_count(

        self

    ):

        return len(

            self.active_orders

        )