class Place:
    """Abstract class of a physical place in the town"""

    next_id = 0

    def __init__(self):
        self.id = Place.next_id; Place.next_id += 1
