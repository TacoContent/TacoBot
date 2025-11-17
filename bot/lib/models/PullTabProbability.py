class PullTabProbability:
    def __init__(self, *, symbol: str, weight: float, reward: int):
        self.symbol = symbol
        self.weight = weight
        self.reward = reward
