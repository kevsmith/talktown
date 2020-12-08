from ordered_set import OrderedSet

class Place:
    """Abstract class of a physical place in the town

    Attributes
    ----------
    id: int
        Unique identifier for this place
    people_here_now : list of people
        People at this place during the current timestep
    """

    next_id = 0

    def __init__(self):
        self.id = Place.next_id; Place.next_id += 1
        self.people_here_now = OrderedSet()

    def __lt__(self, other):
        """Less Than"""
        return self.id < other.id

    def __gt__(self, other):
        """Greater than"""
        return self.id > other.id
