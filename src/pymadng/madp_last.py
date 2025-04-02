class last_counter:
    """Maintain a counter for anonymous '_last' variables in MAD-NG.

    The __last__ variable stores the most recent function result in MAD-NG.
    This helper class tracks available temporary variable indices.

    Args:
        size (int): The maximum number of temporary '_last' variables available.
    """

    def __init__(self, size: int):
        self.counter = list(range(size, 0, -1))

    def get(self):
        assert len(self.counter) > 0, (
            "Assigned too many anonymous variables, increase num_temp_vars or assign the variables into MAD"
        )
        return self.counter.pop()

    def set(self, idx):
        self.counter.append(idx)
