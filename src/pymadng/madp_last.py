class last_counter:
    """A class to keep track of the special variable named '__last__' in MAD-NG

    The '__last__' variable contains the last value returned by a function in MAD-NG. 
    This allows the user to use pythonic syntax and get a return value from a function in MAD-NG, as an object in Python.

    Args:
      size (int): The maximum number of '__last__' variables to keep track of in the MAD-NG environment
    """

    def __init__(self, size: int):
        self.counter = list(range(size, 0, -1))

    def get(self):
        assert (
            len(self.counter) > 0
        ), "Assigned too many anonymous variables, increase num_temp_vars or assign the variables into MAD"
        return self.counter.pop()

    def set(self, idx):
        self.counter.append(idx)
