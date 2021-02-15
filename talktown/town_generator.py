"""Procedurally generates a town layout starting from an empty plot of land"""
import random
from random import gauss
import collections
from ordered_set import OrderedSet
import pyqtree
from .utils import clamp
from .corpora import Names
from .town_layout import (TownLayout, Street, Block, Lot, Tract, Parcel)


ParcelInfo = collections.namedtuple("ParcelInfo", ["x", "y", "width"])
StreetInfo = collections.namedtuple(
    "StreetInfo", ["direction", "starting_parcel", "ending_parcel"])


def generate_town_layout(gen_config, land_size=16):
    """Generates a new town layout"""
    parcel_info, street_info = _generate_parcel_and_street_info(land_size=land_size)
    street_objects, ns_streets, ew_streets, connections = _reify_streets(street_info, land_size, gen_config)
    parcels, lots, tracts = _specify_plots_and_lots(parcel_info, ns_streets, ew_streets)


def _generate_parcel_and_street_info(n_loci=3, n_samples=32, land_size=16):
    """Generate parcel divisions given the size of a plot of land

    Returns
    -------
    (List[ParcelInfo], List[StreetInfo])
      parcels of land and the positions of streets
    """

    # parcel coordinate and size information
    parcel_info = []
    # street information
    street_info = []
    # streets running north to south
    # ns_streets = dict()
    # streets running east to west
    # ew_streets = dict()
    # street segmentsused to construct entire streets
    ns_street_segments = dict()
    ew_street_segments = dict()

    # Randomly sample points that will be used
    # as centers for clusters of points sampled
    # while constructing the pyqtree
    loci = []
    for _ in range(n_loci):
        mean = land_size / 2.0
        std = land_size / 6.0
        loci.append([gauss(mean, std), gauss(mean, std)])

    # Construct a pyqtree to subdivide the land into squares
    tree = pyqtree.Index(bbox=[0, 0, land_size, land_size])
    for _ in range(n_samples):
        # Randomly choose one of the locus points defined above
        center = random.choice(loci)
        # Now randomly sample a point aroud the center and clamp
        # the value to be within the bounds of the land
        point = [
            clamp(gauss(center[0], land_size / 6.0), 0, land_size - 1),
            clamp(gauss(center[1], land_size / 6.0), 0, land_size - 1)
        ]
        point.append(point[0] + 1)
        point.append(point[1] + 1)
        tree.insert(point, point)

    def traverseTree(node):
        """Traverse the pyqtree object

        Each leaf node will become a parcel
        """
        if len(node.children) == 0 and node.width != 1:
            # Calculate the bounds of the parcel
            north = int(node.center[1] - node.width * 0.5)
            east = int(node.center[0] + node.width * 0.5)
            south = int(node.center[1] + node.width * 0.5)
            west = int(node.center[0] - node.width * 0.5)

            parcel_info.append(ParcelInfo(west, north, node.width))

            ns_street_segments[(west, north)] = (west, south)
            ns_street_segments[(east, north)] = (east, south)
            ew_street_segments[(west, north)] = (east, north)
            ew_street_segments[(west, south)] = (east, south)

        for child in node.children:
            traverseTree(child)

    traverseTree(tree)

    nsEnd = OrderedSet()
    ewEnd = OrderedSet()

    # Iterate from [0 to land_size] skipping every other value
    for i in range(0, land_size + 2, 2):
        # Iterate from [0 to land_size] skipping every other value
        for j in range(0, land_size + 2, 2):
            street = (i, j)

            if street in ns_street_segments:

                start = street
                end = ns_street_segments[start]

                while end in ns_street_segments:
                    end = ns_street_segments[end]

                if end not in nsEnd:
                    nsEnd.append(end)
                    street_info.append(StreetInfo('ns', start, end))

            if street in ew_street_segments:
                start = street
                end = ew_street_segments[start]

                while end in ew_street_segments:
                    end = ew_street_segments[end]

                if end not in ewEnd:
                    ewEnd.append(end)
                    street_info.append(StreetInfo('ew', start, end))

    return parcel_info, street_info

def _reify_streets(street_info, land_size, gen_config):
    """
    Parameters
    ----------
    street_info: List[StreetInfo]
      Information about the streats to create

    Returns
    -------
    (List[Street],
    Dict[(int,int), Street],
    Dict[(int,int), Street],
    Dict[(int,int), (int,int)])

    Tuple with a list of streets, dictionary of north-south streets,
    dictionary of east-west streets and a dictionary of parcels pairs
    to parcel pairs
    """

    streets = OrderedSet()
    ns_streets = dict()
    ew_streets = dict()
    connections = dict()

    for street in street_info:

        number = int(
            street.starting_parcel[0]/2 if street.direction == "ns" else street.starting_parcel[1]/2) + 1

        if (street.direction == "ns"):
            direction = ("N" if number < land_size / 4 else "S")
            starting_parcel = street.starting_parcel[1]
            ending_parcel = street.ending_parcel[1]
        else:
            direction = ("E" if number < land_size / 4 else "W")
            starting_parcel = street.starting_parcel[0]
            ending_parcel = street.ending_parcel[0]

        starting_parcel = int(starting_parcel / 2) + 1
        ending_parcel = int(ending_parcel / 2) + 1
        street_name = _generate_street_name(number, direction, gen_config)
        reifiedStreet = Street(
            street_name, number, direction, starting_parcel, ending_parcel)
        streets.add(reifiedStreet)

        for i in range(starting_parcel, ending_parcel + 1):
            if (street.direction == "ns"):
                ns_streets[(number, i)] = reifiedStreet
            else:
                ew_streets[(i, number)] = reifiedStreet

        for i in range(starting_parcel, ending_parcel):
            coord = None
            next = None

            if (street.direction == "ns"):
                coord = (number, i)
                next = (number, i + 1)
            else:
                coord = (i, number)
                next = (i + 1, number)

            if coord not in connections:
                connections[coord] = OrderedSet()
            connections[coord].add(next)

            if next not in connections:
                connections[next] = OrderedSet()
            connections[next].add(coord)

    return streets, ns_streets, ew_streets, connections

def _specify_plots_and_lots(parcel_info, ns_streets, ew_streets, land_size=16):
    """Create Parcels and Lots"""
    final_lots = OrderedSet()
    lots = dict()
    parcels = dict()
    tracts = OrderedSet()
    numberings = dict()
    corners = OrderedSet()
    connections = dict()
    n_buildings_per_parcel = 2

    def insertInto(dict, key, value):
        if (not key in dict):
            dict[key] = []
        dict[key].append(value)

    def insertOnce(dict, key, value):
        if (not key in dict):
            dict[key] = value

    for parcel in parcel_info:
        ew = int(parcel.x / 2) + 1
        ns = int(parcel.y / 2) + 1
        size_of_parcel = int(parcel.width / 2)
        tract = None

        if size_of_parcel > 1:
            tract = Tract(size_of_parcel)
            tracts.add(tract)

        for i in range(size_of_parcel + 1):
            insertOnce(
                parcels,
                (ew, ns + i, 'NS'),
                Parcel(ns_streets[(ew, ns)], (i + ns) * 100, (ew, ns + i)))
            insertOnce(
                numberings,
                (ew, ns + i, 'E'),
                Parcel.determine_house_numbering((i + ns) * 100, 'E'))
            insertOnce(
                parcels,
                (ew + i, ns, 'EW'),
                Parcel(ew_streets[(ew, ns)], (i + ew) * 100, (ew + i, ns)))
            insertOnce(
                numberings,
                (ew + i, ns, 'N'),
                Parcel.determine_house_numbering((i + ew) * 100, 'N'))
            insertOnce(
                parcels,
                (ew + size_of_parcel, ns + i, 'NS'),
                Parcel(ns_streets[(ew + size_of_parcel, ns)], (i + ns) * 100, (ew + size_of_parcel, ns + i)))
            insertOnce(
                numberings,
                (ew + size_of_parcel, ns + i, 'W'),
                Parcel.determine_house_numbering((i + ns) * 100, 'W'))
            insertOnce(
                parcels,
                (ew + i, ns + size_of_parcel, 'EW'),
                Parcel(ew_streets[(ew, ns + size_of_parcel)], (i + ew) * 100, (ew + i, ns + size_of_parcel)))
            insertOnce(
                numberings,
                (ew + i, ns + size_of_parcel, 'S'),
                Parcel.determine_house_numbering((i + ew) * 100, 'S'))

        neCorner = Lot()
        insertInto(lots, (ew, ns, 'N'), (0, neCorner))
        insertInto(lots, (ew, ns, 'E'), (0, neCorner))
        final_lots.add(neCorner)
        corners.add((ew, ns, 'EW', ew, ns, 'NS'))

        nwCorner = Lot()
        if (ew + size_of_parcel) <= (land_size / 2):
            insertInto(lots,
                       (ew + size_of_parcel - 1, ns, 'N'),
                       (n_buildings_per_parcel - 1, nwCorner))
        insertInto(lots, (ew + size_of_parcel, ns, 'W'), (0, nwCorner))
        corners.add((ew + size_of_parcel - 1, ns, 'EW',
                     ew + size_of_parcel, ns, 'NS'))
        final_lots.add(nwCorner)

        seCorner = Lot()
        insertInto(lots, (ew, ns + size_of_parcel, 'S'), (0, seCorner))
        if (ns + size_of_parcel) <= (land_size / 2):
            insertInto(lots,
                       (ew, ns + size_of_parcel - 1, 'E'),
                       (n_buildings_per_parcel - 1, seCorner))
        final_lots.add(seCorner)
        corners.add((ew, ns + size_of_parcel, 'EW',
                     ew, ns + size_of_parcel - 1, 'NS'))

        swCorner = Lot()
        insertInto(lots,
                   (ew + size_of_parcel - 1, ns + size_of_parcel, 'S'),
                   (n_buildings_per_parcel - 1, swCorner))
        insertInto(lots,
                   (ew + size_of_parcel, ns + size_of_parcel - 1, 'W'),
                   (n_buildings_per_parcel - 1, swCorner))
        corners.add((ew + size_of_parcel - 1, ns + size_of_parcel,
                     'EW', ew + size_of_parcel, ns + size_of_parcel - 1, 'NS'))
        final_lots.add(swCorner)

        for i in range(1, size_of_parcel * n_buildings_per_parcel - 1):
            parcel_n = int(i / 2)

            lot = Lot()
            final_lots.add(lot)
            insertInto(lots,
                       (ew, ns + parcel_n, 'E'),
                       (i % n_buildings_per_parcel, lot))

            lot = Lot()
            final_lots.add(lot)
            insertInto(lots,
                       (ew + parcel_n, ns, 'N'),
                       (i % n_buildings_per_parcel, lot))

            lot = Lot()
            final_lots.add(lot)
            insertInto(lots,
                       (ew + size_of_parcel, ns + parcel_n, 'W'),
                       (i % n_buildings_per_parcel, lot))

            lot = Lot()
            final_lots.add(lot)
            insertInto(lots,
                       (ew + parcel_n, ns + size_of_parcel, 'S'),
                       (i % n_buildings_per_parcel, lot))

        for lot_info in lots:
            direction = 'NS' if lot_info[2] == 'W' or lot_info[2] == 'E' else 'EW'
            parcel_object = parcels[(lot_info[0], lot_info[1], direction)]

            lot_list = lots[lot_info]

            for lot in lot_list:
                lot[1].add_parcel(
                    parcel_object, numberings[lot_info][lot[0]], lot_info[2], lot[0])
                parcel_object.lots.append(lot[1])

        for conn in connections:
            for neighbor in connections[conn]:
                dx = neighbor[0] - conn[0]
                dy = neighbor[1] - conn[1]
                if dx != 0:
                    if (conn[0], conn[1], 'EW') in parcels and (neighbor[0], neighbor[1], 'EW') in parcels:
                        parcels[(conn[0], conn[1], 'EW')].add_neighbor(
                            parcels[(neighbor[0], neighbor[1], 'EW')])
                if dy != 0:
                    if (conn[0], conn[1], 'NS') in parcels and (neighbor[0], neighbor[1], 'NS') in parcels:
                        parcels[(conn[0], conn[1], 'NS')].add_neighbor(
                            parcels[(neighbor[0], neighbor[1], 'NS')])
        for corner in corners:
            parcels[(corner[0], corner[1], corner[2])].add_neighbor(
                parcels[(corner[3], corner[4], corner[5])])
            parcels[(corner[3], corner[4], corner[5])].add_neighbor(
                parcels[(corner[0], corner[1], corner[2])])

    return parcels, final_lots, tracts

def _generate_street_name(number, direction, town_gen_config):
    """Generate a street name."""
    number_to_ordinal = {
        1: '1st', 2: '2nd', 3: '3rd', 4: '4th', 5: '5th',
        6: '6th', 7: '7th', 8: '8th', 9: '9th'
    }
    if direction == 'E' or direction == 'W':
        street_type = 'Street'
        if random.random() < town_gen_config.chance_street_gets_numbered_name:
            name = number_to_ordinal[number]
        else:
            if random.random() < 0.5:
                name = Names.any_surname()
            else:
                name = Names.a_place_name()
    else:
        street_type = 'Avenue'
        if random.random() < town_gen_config.chance_avenue_gets_numbered_name:
            name = number_to_ordinal[number]
        else:
            if random.random() < 0.5:
                name = Names.any_surname()
            else:
                name = Names.a_place_name()

    name = "{0} {1}".format(name, street_type)
    return name
