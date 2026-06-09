class Order:

    def __init__(
        self,
        platform,
        pickup_node,
        customer_node,
        reward
    ):

        self.platform = platform
        self.pickup_node = pickup_node
        self.customer_node = customer_node
        self.reward = reward

    def __str__(self):

        return (
            f"{self.platform} | "
            f"Reward: {self.reward}"
        )