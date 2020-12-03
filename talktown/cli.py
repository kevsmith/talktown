import sys
import time
import argparse
import pathlib
import logging

from .simulation import Simulation



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
                        action='store_true',
                        help="Enable verbose output")

    return parser.parse_args()

def main():
    """Run Talk of the Town"""
    args = parse_args()

    # Configure logging
    logging.basicConfig(filename='talktown.log', level=logging.DEBUG)

    start_time = time.time()
    sim = Simulation(args.config)

    try:
        sim.establish_setting()  # This is the worldgen procedure; it will simulate until the date specified in basic_config.py
    except KeyboardInterrupt:  # Enter "ctrl+C" (a keyboard interrupt) to end worldgen early
        # In the case of keyboard interrupt, we need to tie up a few loose ends
        sys.stdout.flush()
        sys.stdout.write('\r{}'.format(' ' * 94))  # Clear out the last sampled event written to stdout
        sys.stdout.write('\rWrapping up...')
        sim.advance_time()
        for person in sorted(sim.town.residents):
            person.routine.enact()

    # Town generation was successful, so print out some basic info about the town
    print("\nAfter {time_elapsed}s, town generation was successful!".format(
        time_elapsed=int(time.time()-start_time)
    ))
    # Print out the town, population, and date
    print("\nIt is now the {date}, in the town of {town}, pop. {population}.\n".format(
        date=sim.date[0].lower() + sim.date[1:],
        town=sim.town.name,
        population=sim.town.population
    ))
    # Start excavating nuggets of dramatic intrigue from the raw emergent material produced
    # during the simulation of the town's history
    print("Excavating nuggets of dramatic intrigue...")
    sim.story_recognizer.excavate()

    if args.export is not None:
        print("Exporting simulation to '{}'".format(args.out))

if __name__ == "__main__":
    main()
