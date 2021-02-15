import random
from collections import OrderedDict
from ordered_set import OrderedSet
from .utils import PriorityQueue

class TownLayout:
    """Geographic layout of a town

    Attributes
    ----------
    downtown: Lot
        The central hub of the town

    paths: OrderedDict[Tuple[int, int], int]
        Paths from one location to another
        Tuples of lot numbers map to the distance between
        the lots

    lots: OrderedSet[Lot]
        Lots of land within the town

    tracts: OrderedSet[Tract]
        Tracts of land within the town

    streets: OrderedSet[Street]
        Streets within the town

    parcels: OrderedSet[Parcels]
        Parcels of land within the town

    blocks: OrderedSet[Block]
        City block within the town
    """

    def __init__(self):
        self.downtown = None
        self.paths = OrderedDict()
        self.lots = OrderedSet()
        self.tracts = OrderedSet()
        self.streets = OrderedSet()
        self.parcels = OrderedSet()
        self.blocks = OrderedSet()

    def dist_from_downtown(self,lot):
        """Manhattan distance from a given lot to downtown"""
        return self.distance_between(lot,self.downtown)

    def distance_between(self, lot1, lot2):
        """Minimum Manhattan distance between two given lots"""
        min_dist = float("inf")
        for parcel in lot1.parcels:
            for other_parcel in lot2.parcels:
                if self.paths[(parcel, other_parcel)] < min_dist:
                    min_dist = self.paths[(parcel, other_parcel)]
        return min_dist

    def generatePaths(self):
        """Find Manhattan distances between all the parcels in the town"""
        for start in self.parcels:
            for goal in self.parcels:
                if start == goal:
                     self.paths[(start,goal)] = 0.0
                else:
                    if (start, goal) not in self.paths:
                        came_from, _ = TownLayout.a_star_search(start, goal)
                        current = goal
                        count = 0
                        while current != start:
                            current = came_from[current]
                            count += 1
                        self.paths[(start, goal)] = count
                        self.paths[(goal, start)] = count

    @staticmethod
    def a_star_search(start, goal):


        frontier = PriorityQueue()
        frontier.put(start, 0)
        came_from = dict()
        cost_so_far = dict()
        came_from[start] = None
        cost_so_far[start] = 0

        while not frontier.empty():
            current = frontier.get()

            if current == goal:
                break

            for next in current.neighbors:
                new_cost = cost_so_far[current] + 1
                if next not in cost_so_far or new_cost < cost_so_far[next]:
                    cost_so_far[next] = new_cost
                    priority = new_cost + Parcel.manhattan_distance(goal, next)
                    frontier.put(next, priority)
                    came_from[next] = current

        return came_from, cost_so_far

class Street:
    """A street in a town.

    Attributes
    ----------
    id: int
        Unique identifier

    name: str
        Street name

    number: int
        Street number

    directions: string
        Street direction ("North", "South", "East", "West")
        relative to the center of the town

    starting_parcel: int
        Parcel this street starts on

    ending_parcel: int
        Parcel this street ends on

    blocks: List[Block]
        Blocks along this street
    """

    counter = 0

    def __init__(self, name, number, direction, starting_parcel, ending_parcel):
        """Initialize a Street object."""
        self.id = Street.counter; Street.counter += 1
        self.name = name
        self.number = number
        self.direction = direction
        self.starting_parcel = starting_parcel
        self.ending_parcel = ending_parcel
        self.blocks = []  # Gets appended to by Block.__init__()

    def __str__(self):
        """Return string representation."""
        return self.name

class Block:
    """A city block in the conventional sense, e.g., the 400 block of Hennepin Ave.

    Attributes
    ----------
    number: int
        Address number

    street: Street
        Street this Block is on

    lots: List[Lot]
        Lots within this block

    starting_coordinates: Tuple[int, float]
        Street number and the number of this block divided by 100

    ending_coordinates: Tuple[float, int]
        Number of this block divided by 100 and the Street number
    """

    def __init__(self, number, street):
        """Initialize a block object."""
        self.number = number
        self.street = street
        self.street.blocks.append(self)
        self.lots = []
        # Helper attributes for rendering a town
        if self.street.direction in ('N', 'S'):
            self.starting_coordinates = (self.street.number, self.number / 100)
            self.ending_coordinates = (self.starting_coordinates[0], self.starting_coordinates[1] + 1)
        else:
            self.starting_coordinates = (self.number / 100, self.street.number)
            self.ending_coordinates = (self.starting_coordinates[0] + 1, self.starting_coordinates[1])

    def __str__(self):
        """Return string representation."""
        return "{} block of {}".format(self.number, str(self.street))

    @property
    def direction(self):
        return 'n-s' if self.street.direction.lower() in ('n', 's') else 'e-w'

    @property
    def buildings(self):
        """Return all the buildings on this block."""
        return [lot.building for lot in self.lots if lot.building]

class Lot:
    """A lot on a city block (and multiple parcels) in a town, upon which buildings and houses get erected.

        Note
        ----
        parcels, streets, and house numbers should all have the same length
    """

    counter = 0

    def __init__(self):
        """Initialize a Lot object."""
        self.id = Lot.counter; Lot.counter += 1
        self.streets = []
        self.parcels = []
        self.block = None
        self.sides_of_street = []
        self.house_numbers = []  # In the event a business is erected here, it inherits this
        self.building = None
        # Positions in city blocks correspond to streets this lot is on and elements of this list
        # will be either 0 or 1, indicating whether this is the leftmost/topmost lot on its side
        # of the street of its city block or else rightmost/bottommost
        self.positions_in_city_blocks = []
        # This one gets set by Town.set_neighboring_lots_for_town_generation() after all lots have
        # been generated
        self.neighboring_lots = OrderedSet()
        # This gets set by Town._determine_lot_coordinates()
        self.coordinates = None
        # These get set by init_generate_address(), which gets called by Town
        self.house_number = None
        self.address = None
        self.street_address_is_on = None
        self.parcel_address_is_on = None
        self.index_of_street_address_will_be_on = None
        self.former_buildings = []

    def __str__(self):
        """Return string representation."""
        if self.building:
            return 'A lot at {} on which {} has been erected'.format(
                self.address, self.building.name)
        else:
            return 'A vacant lot at {}'.format(self.address)

    @property
    def population(self):
        """Return the number of people living/working on the lot."""
        if self.building:
            population = len(self.building.residents)
        else:
            population = 0
        return population

    def add_parcel(self, parcel, number, side_of_street, position_in_parcel):
        self.streets.append(parcel.street)
        self.parcels.append(parcel)
        self.sides_of_street.append(side_of_street)
        self.house_numbers.append(number)
        self.positions_in_city_blocks.append(position_in_parcel)

    def set_neighboring_lots_for_town_generation(self):
        neighboring_lots = OrderedSet()
        for parcel in self.parcels:
            for lot in parcel.lots:
                if lot is not self:
                    neighboring_lots.add(lot)
        self.neighboring_lots = neighboring_lots

    def init_generate_address(self):
        """Generate an address, given the lot building is on."""
        self.index_of_street_address_will_be_on = random.randint(0, len(self.streets) - 1)
        house_number = self.house_numbers[self.index_of_street_address_will_be_on]
        self.house_number = int(house_number)
        street = self.streets[self.index_of_street_address_will_be_on]
        self.address = "{} {}".format(house_number, street.name)
        self.street_address_is_on = street
        self.parcel_address_is_on = self.parcels[self.index_of_street_address_will_be_on]

    def init_set_neighbors_lots_as_other_lots_on_same_city_block(self):
        """Set the neighbors to this lot as all the other lots on the same city block.

        This makes for more intuitive sim-play, since we're delimiting the player's
        sim-play to city blocks, so it would seem right that people reason about
        other people in that same locality when asked about their neighbors.
        """
        self.neighboring_lots = OrderedSet(self.block.lots)


    def __gt__(self, other):
        """Greater than

        Return True if this lot's ID is greater than the other lot's
        """
        return self.id > self.id


    def __lt__(self, other):
        """Less Than

        Return true if this lot's ID is less than the other lots's
        """
        return self.id < self.id

class Tract(Lot):
    """A tract of land on multiple parcels in a town, upon which businesses requiring
    extensive land (e.g., parks and cemeteries) are established.
    """

    def __init__(self, size):
        """Initialize a Tract object."""
        super().__init__()
        self.size = size

    def __str__(self):
        """Return string description"""
        if self.building:
            return 'A tract of land at {} that is the site of {}'.format(
                self.address, self.building.name)
        else:
            return 'A vacant tract of land at {}'.format(self.address)

class Parcel:
    """A collection of between zero and four contiguous lots in a town."""

    counter = 0

    def __init__(self, street, number, coords):
        """Initialize a Parcel object."""
        self.id = Parcel.counter; Parcel.counter += 1
        self.street = street
        self.number = number
        self.lots = []
        self.neighbors = []
        self.coords = coords

    @staticmethod
    def manhattan_distance(parcel_a, parcel_b):
        """Find Manhattan distance between two parcels"""
        (x1, y1) = parcel_a.coords
        (x2, y2) = parcel_b.coords
        return abs(x1 - x2) + abs(y1 - y2)

    @staticmethod
    def determine_house_numbering(block_number, side_of_street):
        """Devise an appropriate house numbering scheme given the number of buildings on the block."""
        n_buildings = 3
        house_numbers = []
        house_number_increment = int(100.0 / n_buildings)
        even_or_odd = 0 if side_of_street == "E" or side_of_street == "N" else 1
        for i in range(n_buildings):
            base_house_number = (i * house_number_increment) - 1
            house_number = base_house_number + int(random.random() * house_number_increment)
            if house_number % 2 == (1-even_or_odd):
                house_number += 1
            if house_number < 1+even_or_odd:
                house_number = 1+even_or_odd
            elif house_number > 98+even_or_odd:
                house_number = 98+even_or_odd
            house_number += block_number
            house_numbers.append(house_number)
        return house_numbers

    def add_neighbor(self, other):
        self.neighbors.append(other)

    def __lt__(self, other):
        return self.id < other.id

    def __gt__(self, other):
        return self.id > other.id
