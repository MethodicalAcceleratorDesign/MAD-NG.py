class last_counter:
  def __init__(self, size: int):
    self.counter = list(range(size, 0, -1))

  def get(self):
    assert (
        len(self.counter) > 0
    ), "Assigned too many anonymous variables, increase num_temp_vars or assign the variables into MAD"
    return self.counter.pop()

  def set(self, idx):
    self.counter.append(idx)
