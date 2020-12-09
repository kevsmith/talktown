import sys
import time
import argparse
import pathlib
import logging

from .simulation import Simulation
from .serializer import serialize_to_file
from .config import Config


def parse_args():
    """Configure command line arguments"""
    parser = argparse.ArgumentParser(description="Run Talk of the Town simulation")

    parser.add_argument("--config",
                        type=pathlib.Path,
                        help="Specify JSON configuration file")

    parser.add_argument("--export",
                        choices=['people', 'events', 'all'],
                        nargs='+',
                        help="Export simulation components to JSON")

    parser.add_argument("--out",
                        type=str,
                        default='sim.json',
                        help="Specify path to save exported simulation")

    parser.add_argument("--verbose",
                        default=False,
                        action='store_true',
                        help="Enable verbose output")

    return parser.parse_args()

def main():
    """Run Talk of the Town"""
    args = parse_args()

    # Configure logging
    logging.basicConfig(filename='talktown.log', level=logging.DEBUG)

    sim_config = Config()

    if args.config:
        sim_config.load_json(args.config)

    start_time = time.time()
    sim = Simulation(sim_config, verbose=args.verbose)

    try:
        sim.establish_setting()  # This is the worldgen procedure; it will simulate until the date specified in basic_config.py
    except KeyboardInterrupt:  # Enter "ctrl+C" (a keyboard interrupt) to end worldgen early
        # In the case of keyboard interrupt, we need to tie up a few loose ends
        if args.verbose:
            print('Wrapping up...')

        sim.advance_time()
        for person in sim.town.residents:
            person.routine.enact()

    # Town generation was successful, so print out some basic info about the town
    if args.verbose:
        print("\nAfter {time_elapsed}s, town generation was successful!".format(
            time_elapsed=int(time.time()-start_time)))

        # Print out the town, population, and date
        print("\nIt is now the {date}, in the town of {town}, pop. {population}.\n".format(
            date=sim.get_date_str(),
            town=sim.town.name,
            population=sim.town.population))

    # Start excavating nuggets of dramatic intrigue from the raw emergent material produced
    # during the simulation of the town's history
    sim.story_recognizer.excavate(verbose=args.verbose)

    if args.export is not None:
        if args.verbose:
            print("Exporting simulation to '{}'".format(args.out))
        serialize_to_file(sim, args.out)


if __name__ == "__main__":
    main()
