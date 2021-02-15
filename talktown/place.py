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

class Building(Place):
    """Abstract class of a building within the town

        Attributes
        ----------
        lot: Lot
            Lot that this building is on

        demolition: Demolition
            Demolition event for this building
    """

    def __init__(self, lot):
        super().__init__()
        self.lot = lot
        self.demolition = None

    def on_demolition(self, demolition_event):
        """Callback function triggered when business is demolished"""
        self.demolition = demolition_event
        self.lot.building = None
        self.lot.former_buildings.append(self)
