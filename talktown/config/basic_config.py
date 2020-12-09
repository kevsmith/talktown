import random

class BasicConfig:
    """Configuration parameters related to basic aspects of the simulation.

    Attributes
    ----------
    seed: int
        Seed value fed psuedorandom number generator. Identical
        seed value should yield identical worlds if all other variables
        are held constant

    date_worldgen_begins: str
        Date (YYYY-MM-DD) that world generation starts

    date_worldgen_ends: str
        Date (YYY-MM-DD) that world generation ends

    timesteps_to_simulate_per_year: int
        Number of timesteps to simulate each year during world
        generation. Each day has two timesteps
        (day & night) and this parameter specifies how many will
        actually be simulated) (Setting for Bad News: 3.6)

    unemployment_to_departure_time: int
        Years until an unemployed person is expected to leave
        the town

    chance_a_new_adult_decides_to_leave_town: float
        Chance that a person will leave town (and thus the simulation)
        upon the birthday that represents them reaching adulthood
        (which birthday this is differs by era)

    new_businesses_per_year: float
        Average number of new businesses that will
        open per year

    average_business_lifespan: int
        Average numbe of years that a business remains open
    """

    def __init__(self):
        self.seed = int(random.random()*9999999)
        self.date_worldgen_begins = "1839-8-19"
        self.date_worldgen_ends = "1979-8-19"
        self.timesteps_to_simulate_per_year = 10
        # -- LEVERS FOR ADJUSTING POPULATIONS --
        # The primary driver of population growth is new businesses, which may cause new people
        # to enter the simulation to begin working there, or at the least may prevent unemployed
        # people from leaving town (and thus the simulation) for work; the primary drivers of population
        # decrease are businesses shutting down (which cause people to become unemployed, which may
        # compel them to leave town) and, more directly, the explicit probabilities of unemployed people
        # and new adults leaving town (which are adjustable below)
        # --
        self.unemployment_to_departure_time = 4
        self.chance_a_new_adult_decides_to_leave_town = 0.1
        self.new_businesses_per_year = 0.7
        self.average_business_lifespan = 60

    def chance_of_a_timestep_being_simulated(self):
        """Chance of timestep being simulated"""
        return self.timesteps_to_simulate_per_year / (365 * 2.0)

    def chance_an_unemployed_person_departs(self):
        """Chance of an unemployed person leaving the town"""
        # Currently set so that an unemployed person would be expected to leave the
        # town after four years of being unemployed (so change the 4.0 to change this); I
        # have it set at four so that characters in times where people start working at
        # 18 may get a college degree (which currently happens automatically when someone
        # is 22 and unemployed)
        return 1.0 / (self.chance_of_a_timestep_being_simulated() * (365 * 2.0) * self.unemployment_to_departure_time)

    def chance_a_business_opens(self):
        """Chance of a business opening on any timestep

        (businesses may be opened on timesteps that aren't actually being simulated)
        """
        return (1 / 730.) * self.new_businesses_per_year

    def chance_a_business_closes(self):
        """Return chance that a business will close on a simulated timestep"""
        return (1 / 730.0) / self.average_business_lifespan
