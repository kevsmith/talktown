import random
from random import gauss, randrange
from ordered_set import OrderedSet
import pyqtree
from . import business
from . import residence
from . import occupation
from .config import TownGenerationDetailsConfig
from .corpora import Names
from .config import Config
from .utils import clamp, PriorityQueue
from .town_layout import (TownLayout, Street, Block, Lot, Tract, Parcel)
from .town_generator import _generate_street_name


class Town:
    """A procedurally generated American small town on a 9x9 grid of city blocks.

        Most of the code for this class was written by Adam Summerville.

        name: str
            Name of the town

        founding_year: int
            Year the town was founded

        settlers: OrderedSet[Person]
            People who founded the town

        residents: OrderedSet[Person]
            People who current live in the town

        departed: OrderedSet[Person]
            People who have left the town (i.e., left the simulation)

        deceased: OrderedSet[Person]
            People who have died within the town

        houses: OrderedSet[House]
            Houses within the town

        residences: OrderedSet[Residence]
            Houses and ApartmentUnits within the town

        apartment_complexes: OrderedSet[ApartmentComplex]
            Apartment complexes in the town

        businesses: OrderedSet[Business]
            Open Businesses in the town

        former_businesses: OrderedSet[Business]
            Businesses that have closed in the town

        downtown: Lot
            The central hub of the town

        paths: Dict[]
            Paths from one location to another

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

        cemetery: Cemetery


        city_hall: CityHall


        fire_station: FireStation


        hospital: Hospital


        police_station: PoliceStation


        school: School


        university: University
    """

    def __init__(self, founding_year):
        """Initialize a Town object."""
        self.name = ""
        self.founding_year = founding_year

        # People
        self.mayor = None
        self.settlers = OrderedSet()  # Will get added to during Simulation.establish_setting()
        self.residents = OrderedSet()
        self.departed = OrderedSet()  # People who left the town
        self.deceased = OrderedSet()  # People who died in in the town

        # Residences
        self.houses = OrderedSet()
        self.residences = OrderedSet()  # Both houses and apartment units (not complexes)

        # Businesses in the town
        self.apartment_complexes = OrderedSet()
        self.businesses = OrderedSet()
        self.former_businesses = OrderedSet()

        # Town Layout
        self.downtown = None
        self.paths = dict()
        self.lots = OrderedSet()
        self.tracts = OrderedSet()
        self.streets = OrderedSet()
        self.parcels = OrderedSet()
        self.blocks = OrderedSet()

        # Key Businesses
        self.cemetery = None
        self.city_hall = None
        self.fire_station = None
        self.hospital = None
        self.police_station = None
        self.school = None
        self.university = None

    def generate_name(self, config):
        """Generate a name for the town"""
        if random.random() < config.town_generation.chance_town_gets_named_for_a_settler \
           and self.mayor is not None:

            self.name = self.mayor.last_name
        else:
            self.name = Names.a_place_name()

    @property
    def random_person(self):
        """Return a random person living in the town of this simulation instance."""
        return random.choice(self.residents)

    @property
    def random_business(self):
        """Return a random company in the town of this simulation instance."""
        return random.choice(self.businesses)

    @property
    def population(self):
        """Return the number of residents living in the town."""
        return len(self.residents)

    @property
    def buildings(self):
        """Return all businesses and houses (not apartment units) in this town."""
        houses = OrderedSet([d for d in self.residences if  isinstance(d, residence.House)])
        return houses | self.businesses

    @property
    def vacant_lots(self):
        """Return all vacant lots in the town."""
        vacant_lots = OrderedSet([lot for lot in self.lots if not lot.building])
        return vacant_lots

    @property
    def vacant_tracts(self):
        """Return all vacant tracts in the town."""
        vacant_tracts = OrderedSet([tract for tract in self.tracts if not tract.building])
        return vacant_tracts

    @property
    def vacant_homes(self):
        """Return all vacant homes in the town."""
        vacant_homes = OrderedSet([home for home in self.residences if len(home.residents) == 0])
        return vacant_homes

    @property
    def all_time_residents(self):
        """Return everyone who has at one time lived in the town."""
        return self.residents | self.deceased | self.departed

    @property
    def unemployed(self):
        """Return unemployed (mostly young) people, excluding retirees."""
        unemployed_people = OrderedSet()
        for resident in self.residents:
            if not resident.occupation and not resident.retired:
                if resident.in_the_workforce:
                    unemployed_people.add(resident)
        return unemployed_people

    def find_residents_by_name(self, name):
        """Return person living in this town with that name"""
        results = []
        for person in self.residents:
            if person.name == name:
                results.append(person)
        return results

    def find_deceased_by_name(self, name):
        """Return deceased person with that name"""
        results = []
        for person in self.deceased:
            if person.name == name:
                results.append(person)
        return results

    def get_person_by_id(self, id_number):
        """Return person with given id number"""
        all_people = self.residents | self.deceased | self.departed
        for person in all_people:
            if person.id == id_number:
                return person
        return None

    def get_business_by_name(self, name):
        """Return a business in this town with the given name."""
        for business in self.businesses:
            if business.name == name:
                return business
        return None

    def get_workers_of_trade(self, occupation):
        """Return all population in the town who practice to given occupation.

        @param occupation: The class pertaining to the occupation in question.
        """
        return [resident.occupation for resident in self.residents if isinstance(resident.occupation, occupation)]

    def get_businesses_of_type(self, business_type):
        """Return all business in this town of the given type.

            Parameters
            ----------
            business_class_name: str
                Type of business to search for

            Returns
            -------
            List[Business]
                All the businsesses in town with a given type
        """
        businesses_of_this_type = \
            [business for business in self.businesses if business.__class__.__name__ == business_type]
        return businesses_of_this_type

    def elect_mayor(self):
        """Choose randome resident to be mayor"""
        self.mayor = self.random_person

    def generate_layout(self, town_gen_config):
        """Generate layout for the town"""

        self.generate_lots(town_gen_config)

        while len(self.tracts) < town_gen_config.min_tracts:
            self.generate_lots(town_gen_config)

        # Set Lot neighbors and generate lot addresses
        for lot in self.lots | self.tracts:
            lot.set_neighboring_lots_for_town_generation()
            lot.init_generate_address()


        # Survey all town lots to instantiate conventional city blocks
        for lot in self.lots | self.tracts:
            number, street = lot.parcel_address_is_on.number, lot.parcel_address_is_on.street

            try:
                city_block = next(b for b in self.blocks if b.number == number and b.street is street)
                city_block.lots.append(lot)
                lot.block = city_block

            except StopIteration:
                city_block = Block(number=number, street=street)
                self.blocks.add(city_block)
                city_block.lots.append(lot)
                lot.block = city_block


        for block in self.blocks:
            block.lots.sort(key=lambda lot: lot.house_number)

        # Fill in any missing blocks, which I think gets caused by tracts being so large
        # in some cases; these blocks will not have any lots on them, so they'll never
        # have buildings on them, but it makes town navigation more natural during simplay
        for street in self.streets:
            street.blocks.sort(key=lambda block: block.number)
            current_block_number = min(street.blocks, key=lambda block: block.number).number
            largest_block_number = max(street.blocks, key=lambda block: block.number).number
            while current_block_number != largest_block_number:
                current_block_number += 100
                if not any(b for b in street.blocks if b.number == current_block_number):
                    self.blocks.add(Block(number=current_block_number, street=street))
            # Sort one last time to facilitate easy navigation during simplay
            street.blocks.sort(key=lambda block: block.number)

        self.generatePaths()
        # Determine coordinates for each lot in the town, which are critical for
        # graphically displaying the town
        self._determine_lot_coordinates()
        # Determine the lot central to the highest density of lots in the town and
        # make this lot downtown

        highest_density = -1
        for lot in self.lots:
            density = self.tertiary_density(lot)
            if density > highest_density:
                highest_density = density
                self.downtown = lot
        # Finally, reset the neighboring lots to all lots to be the other
        # lots on the same city block
        for lot in self.lots:
            lot.init_set_neighbors_lots_as_other_lots_on_same_city_block()

    def __str__(self):
        """Return the town's name and population."""
        return "{} (pop. {})".format(self.name, self.population)

    def get_parcels(self):
        """Return dict description of this town's parcels"""
        output_parcels = dict()
        for parcel in self.parcels:
            neighbors = []
            for neighbor in parcel.neighbors:
                neighbors.append(neighbor.id)
            lots = []
            for lot in parcel.lots:
                lots.append(lot.id)
            output_parcels[parcel.id] = {
                "street": parcel.street.id,
                "number": parcel.number,
                "coords": parcel.coords,
                "lots": lots,
                "neighbors": neighbors
            }
        return output_parcels

    def get_lots(self):
        """Return dict description of this town's lots"""
        output_lots = dict()
        for lot in self.lots | self.tracts:
            building_id = -1
            if lot.building is not None:
                building_id = lot.building.id
            parcel_ids = []
            for parcel in lot.parcels:
                parcel_ids.append(parcel.id)
            output_lots[lot.id] = {
                "index_of_street_address_will_be_on": lot.index_of_street_address_will_be_on,
                "building": building_id,
                "blocks": parcel_ids,
                "house_numbers": lot.house_numbers,
                "positionsInBlock": lot.positions_in_city_blocks,
                "sidesOfStreet": lot.sides_of_street
            }
        return output_lots

    def get_houses(self):
        """Return dict description of this houses in the town"""
        output = dict()
        for house in self.houses:
            people_here_now = OrderedSet([p.id for p in house.people_here_now])
            output[house.id] = {"address":house.address,"lot":house.lot.id, "people_here_now":people_here_now}
        return output

    def get_apartments(self):
        """Return dict description of apartment complexes in the town"""
        output = dict()
        for apartment in self.apartment_complexes:
            people_here_now = OrderedSet([p.id for p in apartment.people_here_now])
            for unit in apartment.units:
                people_here_now |= OrderedSet([q.id for q in unit.people_here_now])
            output[apartment.id] = {"address":apartment.name,"lot":apartment.lot.id, "people_here_now":people_here_now}
        return output

    def get_businesses(self):
        """Return dict description of this town's businesses"""
        output = dict()
        for business in self.businesses:
            people_here_now = OrderedSet([p.id for p in business.people_here_now])
            output[business.id] = {"address":business.name,"lot":business.lot.id, "people_here_now":people_here_now}
        return output

    def get_streets(self):
        """Return dict description of this town's streets"""
        output = dict()
        for street in self.streets:
            output[street.id] = {
                "number": street.number,
                "name": street.name,
                "startingBlock": street.starting_parcel,
                "endingBlock": street.ending_parcel,
                "direction": street.direction
            }
        return output

    def dist_from_downtown(self,lot):
        return self.distance_between(lot,self.downtown)

    def distance_between(self, lot1, lot2):
        min_dist = float("inf")
        for parcel in lot1.parcels:
            for other_parcel in lot2.parcels:
                if self.paths[(parcel, other_parcel)] < min_dist:
                    min_dist = self.paths[(parcel, other_parcel)]
        return min_dist

    def nearest_business_of_type(self, lot, business_type):
        """Return the Manhattan distance between this lot and the nearest company of the given type.

            Parameters
            ----------
            lot: Lot
                Lot we are starting measurement from
            business_class_name: str
                Type of businesses we are measuring the distance to
        """
        businesses_of_this_type = self.get_businesses_of_type(business_type)
        if businesses_of_this_type:
            return min(businesses_of_this_type, key=lambda b: self.distance_between(lot, b.lot))
        else:
            return None

    def dist_to_nearest_business_of_type(self, lot, business_type, exclusion):
        """Return the Manhattan distance between this lot and the nearest business of the given type.

        Parameters
        ----------
        business_type: Type[Business]
            The Class representing the type of business in question.

        exclusion: Business
            A bussiness who is being excluded from this determination because they
            are the ones making the call to this method, as they try to decide where
            to put their lot.
        """
        distances = [
            self.distance_between(lot, business.lot) for business in self.businesses if isinstance(business, business_type)
            and business is not exclusion
        ]
        if distances:
            return max(99, min(distances))  # Elsewhere, a max of 99 is relied on
        else:
            return None

    @staticmethod
    def secondary_population(lot):
        """Return the total population of this lot and its neighbors."""
        secondary_population = 0
        for neighbor in OrderedSet([lot]) | lot.neighboring_lots:
            secondary_population += neighbor.population
        return secondary_population

    @staticmethod
    def tertiary_population(lot):
        lots_already_considered = OrderedSet()
        tertiary_population = 0
        for neighbor in OrderedSet([lot]) | lot.neighboring_lots:
            if neighbor not in lots_already_considered:
                lots_already_considered.add(neighbor)
                tertiary_population += neighbor.population
                for neighbor_to_that_lot in neighbor.neighboring_lots:
                    if neighbor_to_that_lot not in lots_already_considered:
                        lots_already_considered.add(neighbor_to_that_lot)
                        tertiary_population += neighbor.population
        return tertiary_population

    @staticmethod
    def tertiary_density(lot):
        lots_already_considered = OrderedSet()
        tertiary_density = 0
        for neighbor in OrderedSet([lot]) | lot.neighboring_lots:
            if neighbor not in lots_already_considered:
                lots_already_considered.add(neighbor)
                tertiary_density += 1
                for neighbor_to_that_lot in neighbor.neighboring_lots:
                    if neighbor_to_that_lot not in lots_already_considered:
                        lots_already_considered.add(neighbor_to_that_lot)
                        tertiary_density += 1
        return tertiary_density

    def generate_lots(self, config):
        # ?? Just affects the number of ??focus points within the bounding box in pyqtree
        loci = 3
        samples = 32

        # ?? the length and width of the town's land in km
        size = 16
        lociLocations = []

        # ?? Determine main focus points of activity
        #    within the size x size bounding box defined
        #    in pyqtree
        for _ in range(loci):
            lociLocations.append([gauss(size/2.0,size/6.0), gauss(size/2.0,size/6.0)])

        tree = pyqtree.Index(bbox=[0,0,size,size])

        # ?? For each sample
        for _ in range(samples):
            # Randomly choose one of the locus points defined above
            center = lociLocations[randrange(len(lociLocations))]
            # Now randomly sample a point
            point = [clamp(gauss(center[0],size/6.0),0,size-1),clamp(gauss(center[1],size/6.0),0,size-1)]
            point.append(point[0]+1)
            point.append(point[1]+1)
            tree.insert(point,point)

        nsstreets = dict()
        ewstreets = dict()
        parcels = []
        lots = []

        nsEnd = []
        ewEnd = []
        streets = []

        def traverseTree(node):
            if (len(node.children)==0 and node.width != 1):
                w =int( node.center[0]-node.width*0.5)
                e =int( node.center[0]+node.width*0.5)
                n =int( node.center[1]-node.width*0.5)
                s =int( node.center[1]+node.width*0.5)
                parcels.append((w,n,node.width))

                nsstreets[ (w,n)] = (w,s)
                nsstreets[ (e,n)] = (e,s)
                ewstreets[ (w,n)] = (e,n)
                ewstreets[ (w,s)] = (e,s)

            for child in node.children:
                traverseTree(child)
        traverseTree(tree)

        for ii in range(0,size+2,2):
            for jj in range(0,size+2,2):
                street = (ii,jj)
                if street in nsstreets:
                    start = street
                    end = nsstreets[start]
                    while end in nsstreets:
                        end = nsstreets[end]
                    if (end not in nsEnd):
                        nsEnd.append(end)
                        streets.append(['ns',start, end])
                if street in ewstreets:
                    start = street
                    end = ewstreets[start]
                    while end in ewstreets:
                        end = ewstreets[end]
                    if (end not in ewEnd):
                        ewEnd.append(end)
                        streets.append(['ew',start, end])

        nsStreets = dict()
        ewStreets = dict()
        connections = dict()
        for street in streets:
            number = int(street[1][0]/2 if street[0] == "ns" else street[1][1]/2)+1
            direction = ""
            starting_parcel = 0
            ending_parcel = 0
            if (street[0] == "ns"):
                direction = ("N" if number < size/4 else "S")
                starting_parcel =  street[1][1]
                ending_parcel =  street[2][1]

            if (street[0] == "ew"):
                direction =( "E" if number < size/4 else "W")
                starting_parcel =  street[1][0]
                ending_parcel =  street[2][0]

            starting_parcel = int(starting_parcel/2)+1
            ending_parcel = int(ending_parcel/2)+1
            street_name = _generate_street_name(number, direction, config)
            reifiedStreet = Street(street_name, number, direction, starting_parcel, ending_parcel)
            self.streets.add(reifiedStreet)
            for ii in range(starting_parcel, ending_parcel+1):
                if (street[0] == "ns"):
                    nsStreets[(number,ii)] = reifiedStreet
                else:
                    ewStreets[(ii,number)] = reifiedStreet
            for ii in range(starting_parcel,ending_parcel):
                coord = None
                next = None
                if (street[0] == "ns"):
                    coord = (number,ii)
                    next = (number,ii+1)
                else:
                    coord = (ii,number)
                    next = (ii+1,number)
                if (not coord in connections):
                    connections[coord] = OrderedSet()
                connections[coord].add(next)
                if (not next in connections):
                    connections[next] = OrderedSet()
                connections[next].add(coord)


        def insertInto(dict,key,value):
            if (not key in dict):
                dict[key] = []
            dict[key].append(value)

        def insertOnce(dict,key,value):
            if (not key in dict):
                dict[key] = value

        lots = dict()
        Parcels = dict()
        Numberings = dict()
        n_buildings_per_parcel = 2

        corners = OrderedSet()
        for parcel in parcels:
            ew = int(parcel[0]/2)+1
            ns = int(parcel[1]/2)+1
            size_of_parcel = int(parcel[2]/2)
            tract = None
            if (size_of_parcel > 1):
                tract = Tract(size=size_of_parcel)
                self.tracts.add(tract)
            for ii in range(0,size_of_parcel+1):

                insertOnce(Parcels,(ew,ns+ii,'NS'),Parcel( nsStreets[(ew,ns)], (ii+ns)*100,(ew,ns+ii)))
                insertOnce(Numberings,(ew,ns+ii,'E'),Parcel.determine_house_numbering( (ii+ns)*100,'E'))
                insertOnce(Parcels,(ew+ii,ns,'EW'),Parcel( ewStreets[(ew,ns)], (ii+ew)*100,(ew+ii,ns)))
                insertOnce(Numberings,(ew+ii,ns,'N'),Parcel.determine_house_numbering( (ii+ew)*100,'N'))
                insertOnce(Parcels,(ew+size_of_parcel,ns+ii,'NS'),Parcel( nsStreets[(ew+size_of_parcel,ns)], (ii+ns)*100,(ew+size_of_parcel,ns+ii)))
                insertOnce(Numberings,(ew+size_of_parcel,ns+ii,'W'),Parcel.determine_house_numbering( (ii+ns)*100,'W'))
                insertOnce(Parcels,(ew+ii,ns+size_of_parcel,'EW'),Parcel( ewStreets[(ew,ns+size_of_parcel)], (ii+ew)*100,(ew+ii,ns+size_of_parcel)))
                insertOnce(Numberings,(ew+ii,ns+size_of_parcel,'S'),Parcel.determine_house_numbering( (ii+ew)*100,'S'))
                if (tract != None):
                    tract.add_parcel(Parcels[(ew,ns+ii,'NS')],Numberings[(ew,ns+ii,'E')][n_buildings_per_parcel],'E',0)
                    tract.add_parcel( Parcels[(ew+ii,ns,'EW')],Numberings[(ew+ii,ns,'N')][n_buildings_per_parcel] ,'N',0)
                    if (ew+size_of_parcel <= size/2):
                        tract.add_parcel(Parcels[(ew+size_of_parcel,ns+ii,'NS')],Numberings[(ew+size_of_parcel,ns+ii,'W')][n_buildings_per_parcel],'W',0)

                    if (ns+size_of_parcel <= size/2):
                        tract.add_parcel( Parcels[(ew+ii,ns+size_of_parcel,'EW')],Numberings[(ew+ii,ns+size_of_parcel,'S')][n_buildings_per_parcel],'S',0)

            neCorner = Lot()
            insertInto(lots,(ew,ns,'N'),(0,neCorner))
            insertInto(lots,(ew,ns,'E'),(0,neCorner))
            self.lots.add(neCorner)
            corners.add((ew,ns,'EW',ew,ns,'NS'))

            nwCorner = Lot()
            if (ew+size_of_parcel <= size/2):
                insertInto(lots,(ew+size_of_parcel-1,ns,'N'),(n_buildings_per_parcel-1,nwCorner))
            insertInto(lots,(ew+size_of_parcel,ns,'W'),(0,nwCorner))
            corners.add((ew+size_of_parcel-1,ns,'EW',ew+size_of_parcel,ns,'NS'))
            self.lots.add(nwCorner)

            seCorner = Lot()
            insertInto(lots,(ew,ns+size_of_parcel,'S'),(0,seCorner))
            if (ns+size_of_parcel <= size/2):
                insertInto(lots,(ew,ns+size_of_parcel-1,'E'),(n_buildings_per_parcel-1,seCorner))
            self.lots.add(seCorner)
            corners.add((ew,ns+size_of_parcel,'EW',ew,ns+size_of_parcel-1,'NS'))

            swCorner = Lot()
            insertInto(lots,(ew+size_of_parcel-1,ns+size_of_parcel,'S'),(n_buildings_per_parcel-1,swCorner))
            insertInto(lots,(ew+size_of_parcel,ns+size_of_parcel-1,'W'),(n_buildings_per_parcel-1,swCorner))
            corners.add((ew+size_of_parcel-1,ns+size_of_parcel,'EW',ew+size_of_parcel,ns+size_of_parcel-1,'NS'))
            self.lots.add(swCorner)

            for ii in range(1,size_of_parcel*n_buildings_per_parcel-1):
                parcel_n = int(ii/2)
                lot = Lot()
                self.lots.add(lot)
                insertInto(lots,(ew,ns+parcel_n,'E'),(ii %n_buildings_per_parcel,lot))
                lot = Lot()
                self.lots.add(lot)
                insertInto(lots,(ew+parcel_n,ns,'N'),(ii %n_buildings_per_parcel,lot))
                lot = Lot()
                self.lots.add(lot)
                insertInto(lots,(ew+size_of_parcel,ns+parcel_n,'W'),(ii %n_buildings_per_parcel,lot))
                lot = Lot()
                self.lots.add(lot)
                insertInto(lots,(ew+parcel_n,ns+size_of_parcel,'S'),(ii %n_buildings_per_parcel,lot))
        for parcel in lots:
            dir = 'NS' if parcel[2] == 'W' or parcel[2] == 'E' else 'EW'
            parcel_object = Parcels[(parcel[0],parcel[1],dir)]
            lotList = lots[parcel]

            for lot in lotList:
                lot[1].add_parcel(parcel_object,Numberings[parcel][lot[0]],parcel[2],lot[0])
                parcel_object.lots.append(lot[1])

        for conn in connections:
            for neighbor in connections[conn]:
                dx = neighbor[0] - conn[0]
                dy = neighbor[1] - conn[1]
                if dx != 0:
                    if (conn[0],conn[1],'EW') in Parcels and (neighbor[0],neighbor[1],'EW') in Parcels:
                        Parcels[(conn[0],conn[1],'EW')].add_neighbor(Parcels[(neighbor[0],neighbor[1],'EW')])
                if dy != 0:
                    if (conn[0],conn[1],'NS') in Parcels and (neighbor[0],neighbor[1],'NS') in Parcels:
                        Parcels[(conn[0],conn[1],'NS')].add_neighbor(Parcels[(neighbor[0],neighbor[1],'NS')])
        for corner in corners:
            Parcels[(corner[0],corner[1],corner[2])].add_neighbor(Parcels[(corner[3],corner[4],corner[5])])
            Parcels[(corner[3],corner[4],corner[5])].add_neighbor(Parcels[(corner[0],corner[1],corner[2])])

        for parcel in Parcels:
            self.parcels.add(Parcels[parcel])

    def _determine_lot_coordinates(self):
        """Determine coordinates for each lot in this town.

        Coordinates are of the form (number_of_east_west_street, number_of_north_south_street),
        but with the coordinate corresponding to the street that the lot's address is *not* on
        being set to either that street's number plus 0.25 or plus 0.75, depending on the lot's
        position on the city block (which can be inferred from its address).
        """
        for lot in self.lots | self.tracts:
            # Determine base x- and y-coordinates, which can be inferred from the
            # number of the street that the lot's address is on and the lot's house
            # number itself
            if lot.street_address_is_on.direction in ('E', 'W'):
                x_coordinate = int(lot.house_number/100.0)
                y_coordinate = lot.street_address_is_on.number
            else:
                x_coordinate = lot.street_address_is_on.number
                y_coordinate = int(lot.house_number/100.0)
            # Figure out this lot's position in its city block
            index_of_street_lot_address_is_on = lot.streets.index(lot.street_address_is_on)
            position_in_city_block = lot.positions_in_city_blocks[index_of_street_lot_address_is_on]
            # Convert this to an increase (on the axis matching the direction of the street
            # that this lot's address is on) of either 0.25 or 0.75; we do this so that lots
            # are spaced evenly
            if lot.street_address_is_on.direction in ('E', 'W'):
                x_coordinate = int(x_coordinate)+0.25 if position_in_city_block == 0 else int(x_coordinate)+0.75
            elif lot.street_address_is_on.direction in ('N', 'S'):
                y_coordinate = int(y_coordinate)+0.25 if position_in_city_block == 0 else int(y_coordinate)+0.75
            # Figure out what side of the street this lot is on
            index_of_street_lot_address_is_on = lot.streets.index(lot.street_address_is_on)
            lot_side_of_street_on_the_street_its_address_is_on = lot.sides_of_street[index_of_street_lot_address_is_on]
            # Update coordinates accordingly
            if lot_side_of_street_on_the_street_its_address_is_on == 'N':
                y_coordinate += 0.25
            elif lot_side_of_street_on_the_street_its_address_is_on == 'S':
                y_coordinate -= 0.25
            elif lot_side_of_street_on_the_street_its_address_is_on == 'E':
                x_coordinate += 0.25
            elif lot_side_of_street_on_the_street_its_address_is_on == 'W':
                x_coordinate -= 0.25
            # Attribute these coordinates to the lot
            lot.coordinates = (x_coordinate, y_coordinate)

    def generatePaths(self):
        """Find Manhattan distances between all the parcels in the town"""
        for start in self.parcels:
            for goal in self.parcels:
                if start == goal:
                     self.paths[(start,goal)] = 0.0
                else:
                    if (start, goal) not in self.paths:
                        came_from, _ = Town.a_star_search(start, goal)
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
