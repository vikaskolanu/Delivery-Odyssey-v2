class DeliveryAgent:

    def __init__(self, start_node):

        self.current_node = start_node
        self.active_orders = []
        self.total_earnings = 0

    def get_position(self):

        return self.current_node