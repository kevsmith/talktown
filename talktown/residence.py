import random
from ordered_set import OrderedSet
from .place import Place
from . import life_event

class Residence(Place):
    """A dwelling place in a town."""

    def __init__(self, lot, owners, town, address):
        """Initialize a Residence object.

        @param lot: A Lot object representing the lot this building is on.
        """
        super().__init__()
        self.town = town
        self.town.residences.add(self)
        self.lot = lot
        self.address = address
        self.house_number = lot.house_number
        self.block = lot.block
        self.residents = OrderedSet()
        self.former_residents = OrderedSet()
        self.transactions = []
        self.move_ins = []
        self.move_outs = []
        self.owners = OrderedSet()  # Gets set via self._init_ownership()
        self.former_owners = OrderedSet()
        self.demolition = None  # Potentially gets set by event.Demolition.__init__()

    def __str__(self):
        """Return string representation."""
        return "{}, {}".format(self.name, self.address)


    @property
    def locked(self):
        """Return True if the door to this dwelling place is currently locked, else false."""
        locked = False
        if not self.owners:
            locked = True
        elif self.town.sim.time_of_day == 'day' and not self.people_here_now:
            # Randomly decide who was the last to leave this home today
            index_in_owners_of_last_to_leave = int(
                round(self.town.sim.random_number_this_timestep * len(self.owners))
            )
            index_in_owners_of_last_to_leave -= 1
            last_to_leave = sorted(self.owners)[index_in_owners_of_last_to_leave]
            if self.town.sim.random_number_this_timestep > last_to_leave.personality.neuroticism:
                locked = True
        elif self.town.sim.time_of_day == "night":
            most_neurotic_owner = max(self.owners, key=lambda o: o.personality.neuroticism)
            if self.town.sim.random_number_this_timestep > most_neurotic_owner.personality.neuroticism:
                locked = True
        return locked

    @property
    def name(self):
        """Return the name of this residence."""
        if self.owners:
            owner_surnames = OrderedSet([o.last_name for o in self.owners])
            name = "{} residence".format('-'.join(owner_surnames))
        else:
            name = 'Uninhabited residence'
        return name

    def init_ownership(self, initial_owners, date):
        """Set the initial owners of this dwelling place."""
        # I'm doing this klugey thing for now because of circular-dependency issue
        list(initial_owners)[0].purchase_home(purchasers=initial_owners, home=self, date=date)
        # HomePurchase(subjects=initial_owners, home=self, realtor=None)


class Apartment(Residence):
    """An individual apartment unit in an apartment building in a town."""

    def __init__(self, apartment_complex, owners, lot, unit_number, town):
        super().__init__(lot, owners=owners, town=town, address=lot.address)
        self.complex = apartment_complex
        self.unit_number = unit_number
        self.address = self._init_generate_address()

    def _init_generate_address(self):
        """Generate an address, given the lot building is on."""
        return "{0} (Unit #{1})".format(self.lot.address, self.unit_number)

    def __str__(self):
        """Return string representation."""
        if self.complex.demolition:
            construction_year = self.complex.construction.year
            demolition_year = self.complex.demolition.year
            return "{}, {} ({}-{})".format(self.name, self.address, construction_year, demolition_year)
        else:
            return "{}, {}".format(self.name, self.address)

class House(Residence):
    """A house in a town.

    @param lot: A Lot object representing the lot this building is on.
    @param construction: A BusinessConstruction object holding data about
                         the construction of this building.
    """

    def __init__(self, lot, town, owners):
        super().__init__(lot, owners, town, lot.address)
        self.construction = None
        self.lot.building = self


    def on_demolition(self, demolition_event):
        """Callback function triggered when business is demolished"""
        self.demolition = demolition_event
        self.lot.building = None
        self.lot.former_buildings.append(self)
        self.town.residences.remove(self)
        if self.residents:
            life_event.Demolition.have_the_now_displaced_residents_move(self, demolition_event)

    def __str__(self):
        """Return string representation."""
        if self.demolition is not None:
            construction_year = self.construction.year
            demolition_year = self.demolition.year
            return "{}, {} ({}-{})".format(self.name, self.address, construction_year, demolition_year)
        else:
            return "{}, {}".format(self.name, self.address)
