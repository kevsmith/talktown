import sys
import time
import datetime
import random
import logging
from tqdm import tqdm
from collections import defaultdict
from ordered_set import OrderedSet
from .utils import is_leap_year, get_random_day_of_year
from . import business
from .town import Town
from . import occupation
from . import residence
from .config import Config
from .drama import StoryRecognizer
from .person import Person, PersonExNihilo
from .corpora import Names
from .business import Business

def print_simulation_msg(msg, char_limit=94):
    """Print status message to the console"""
    clear_str = '\r{}'.format(' ' * char_limit)
    sys.stdout.write('{}\r{}'.format(clear_str,msg[:char_limit]))
    sys.stdout.flush()

class Simulation:
    """A simulation instance.

        A Talk of the Town Simulation instance

        Attributes
        ----------
        config: dict
            Configuration parameters

        current_date: datetime.datetime
            Current date within the simulation

        ending_date: datetime.datetime
            Date that world generation ends

        time_of_day: str
            "day" or "night"

        town: Town
            Town being simulated

        events: List[Event]
            List of all simulated events

        birthdays: Dict[Tuple(int, int), OrderedSet[Person]]
            collection of all people born on each day -- this is used to
            age people on their birthdays; we start with (2, 29) initialized because
            we need to perform a check every March 1 to ensure that all leap-year babies
            celebrate their birthday that day on non-leap years

        random_number_this_timestep: float
            Prepare a number that will hold a single random number
            that is generated daily -- this facilitates certain things
            that should be determined randomly but remain constant across
            a timestep, e.g., whether a person locked their door before leaving home

        weather: str
            Current weather in town may be "good" or "bad"

        last_simulated_day: int
            Date of last day simulated

        n_simulated_timesteps: int
            Number of simulated timesteps

        story_recognizer: drama.StoryRecognizer
            whose job is to excavate nuggets of dramatic
            intrigue from the raw emergent material generated
            by this simulation

        leap_year: bool
            Tracked across the year to help with managing the
            aging of leap-year babies

        verbose: bool
            Should output be printed to the console
    """

    def __init__(self, config=None, verbose=True):
        """Initialize a Simulation object."""
        self.config = config if config is not None else Config()
        self.current_date = datetime.datetime.strptime(self.config.basic.date_worldgen_begins, '%Y-%m-%d')
        self.ending_date = datetime.datetime.strptime(self.config.basic.date_worldgen_ends, '%Y-%m-%d')
        self.time_of_day = "day"
        self.leap_year = False
        self.town = None
        self.events = OrderedSet()
        self.birthdays = defaultdict(lambda: OrderedSet())
        self.random_number_this_timestep = 0.0
        self.weather = "good"
        self.last_simulated_day = self.current_date.toordinal()
        self.n_simulated_timesteps = 0
        self.story_recognizer = StoryRecognizer(simulation=self)
        self.verbose = verbose

    def get_date_str(self):
        """Return a formatted date string"""
        return "{} of {}".format(
            self.time_of_day.title(),
            self.current_date.strftime("%A %d, %B %Y"))

    def recent_events(self, n=5):
        """Pretty-print the last n simulated events (for debugging purposes)."""
        for recent_event in self.events[-n:]:
            print(recent_event)

    def register_birthday(self, birthday, person):
        """Add person to dictionary of birthdays"""
        self.birthdays[birthday].add(person)

    def register_event(self, event):
        """Add event to history"""
        self.events.add(event)

    def establish_setting(self):
        """Establish the town that will be simulated."""
        if self.verbose:
            print("Generating a town (world seed: {})..."
                .format(self.config.basic.seed))

        random.seed(self.config.basic.seed)

        self.current_date = datetime.datetime.strptime(self.config.basic.date_worldgen_begins, '%Y-%m-%d')
        self.ending_date = datetime.datetime.strptime(self.config.basic.date_worldgen_ends, '%Y-%m-%d')

        self.town = Town(self.current_date.year)
        self.town.generate_layout(self.config.town_generation)

        # Have families establish farms on all of the town tracts except one,
        # which will be a cemetery
        for _ in range(len(self.town.tracts) - 2):
            person = PersonExNihilo.create_person(self, job_opportunity_impetus=occupation.Farmer)
            Business.create_business(business.Farm, self, person)

        # For the last tract, potentially have a quarry or coal mine instead of a farm
        if random.random() <  self.config.business.chance_of_a_coal_mine_at_time_of_town_founding:
            person = PersonExNihilo.create_person(self, job_opportunity_impetus=occupation.Owner)
            Business.create_business(business.CoalMine, self, person)

        elif random.random() < self.config.business.chance_of_a_quarry_at_time_of_town_founding:
            person = PersonExNihilo.create_person(self, job_opportunity_impetus=occupation.Owner)
            Business.create_business(business.Quarry, self, person)

        else:
            person = PersonExNihilo.create_person(self, job_opportunity_impetus=occupation.Farmer)
            Business.create_business(business.Farm, self, person)

        # Name the town -- has to come before the cemetery is instantiated,
        # so that the cemetery can be named after it
        self.town.elect_mayor()
        self.town.generate_name(self.config)

        # Establish a cemetery -- it doesn't matter who the owner is for
        # public institutions like a cemetery, it will just be used as a
        # reference with which to access this simulation instance
        Business.create_business(business.Cemetery, self, self.town.random_person)

        self.town.settlers = self.town.residents.copy()

        if self.verbose:
            print("Simulating {n} years of history...".format(
                n=self.ending_date.year - self.current_date.year))

        # Now simulate until the specified date that worldgen ends
        n_days_until_worldgen_ends = self.ending_date.toordinal() - self.current_date.toordinal()
        n_timesteps_until_worldgen_ends = n_days_until_worldgen_ends * 2
        self.simulate(n_timesteps=n_timesteps_until_worldgen_ends)

    def simulate(self, n_timesteps=1):
        """Simulate activity in this town for the given number of timesteps."""

        for _ in tqdm(range(n_timesteps)):
            # Do some basic bookkeeping, regardless of whether the timestep will be simulated
            self.advance_time()
            self._progress_town_businesses()
            self._simulate_births()

            # Potentially simulate the timestep
            if random.random() < self.config.basic.chance_of_a_timestep_being_simulated():
                self._simulate_timestep()

            # if self.verbose and len(self.events) > 0:
            #     print_simulation_msg(str(self.events[-1]))

        if self.verbose:
           print_simulation_msg("Wrapping up...")

    def advance_time(self):
        """Advance time of day and date, if it's a new day."""
        # Update the time of day
        self.time_of_day = "night" if self.time_of_day == "day" else "day"
        # If it's a new day, update the date and simulate birthdays
        if self.time_of_day == "day":
            self._update_date()
            self._execute_birthdays()
        # Set a new random number for this timestep
        self.random_number_this_timestep = random.random()
        # Lastly, update the weather for today
        self.weather = random.choice(['good', 'bad'])

    def _update_date(self):
        """Update the current date, given that it's a new day."""
        prev_year = self.current_date.year
        self.current_date = self.current_date + datetime.timedelta(days=1)
        if prev_year != self.current_date.year:
            # Happy new year!
            self.leap_year = is_leap_year(self.current_date.year)

    def _execute_birthdays(self):
        """Execute the effects of any birthdays happening today."""
        # Age any present (not dead, not departed) character whose birthday is today
        if (self.current_date.month, self.current_date.day) not in self.birthdays:
            self.birthdays[(self.current_date.month, self.current_date.day)] = OrderedSet()
        else:
            for person in self.birthdays[(self.current_date.month, self.current_date.day)]:
                if person.present:
                    person.grow_older()

            # Don't forget leap-year babies on non leap years
            if (not self.leap_year) and (self.current_date.month, self.current_date.day) == (3, 1):
                for person in self.birthdays[(2, 29)]:
                    if person.present:
                        person.grow_older()

    def _progress_town_businesses(self):
        """Potentially have new businesses establish and/or existing businesses close down."""
        self._potentially_establish_a_new_business()
        self._potentially_shut_down_businesses()

    def _simulate_births(self):
        """Simulate births, even if this timestep will not actually be simulated."""
        for person in self.town.residents:
            if person.pregnant:
                if self.current_date.toordinal() >= person.due_date:  # Not worth the computation to be realistic about late births
                    if self.time_of_day == 'day':
                        if random.random() < 0.5:
                            person.give_birth()
                    else:
                        person.give_birth()

    def _potentially_establish_a_new_business(self):
        """Potentially have a new business get constructed in town."""
        # If there's less than 30 vacant homes in this town and no apartment complex
        # yet, have one open up
        if len(self.town.vacant_lots) < 30 and not self.town.get_businesses_of_type('ApartmentComplex'):
            owner = self._determine_who_will_establish_new_business(business.ApartmentComplex)
            Business.create_business(business.ApartmentComplex, self, owner)

        elif random.random() < self.config.basic.chance_a_business_opens():
            all_business_types = business.Business.__subclasses__()
            type_of_business_that_will_open = None
            tries = 0
            while not type_of_business_that_will_open:
                tries += 1
                randomly_selected_type = random.choice(all_business_types)
                advent, demise, min_pop = self.config.business.business_types_advent_demise_and_minimum_population[
                    randomly_selected_type
                ]
                # Check if the business type is era-appropriate
                if advent < self.current_date.year < demise and self.town.population > min_pop:
                    # Check if there aren't already too many businesses of this type in town
                    max_number_for_this_type = self.config.business.max_number_of_business_types_at_one_time[randomly_selected_type]
                    if (len(self.town.get_businesses_of_type(randomly_selected_type.__name__)) <
                            max_number_for_this_type):
                        # Lastly, if this is a business that only forms on a tract, make sure
                        # there is a vacant tract for it to be established upon
                        need_tract = randomly_selected_type in self.config.business.companies_that_get_established_on_tracts
                        if (need_tract and self.town.vacant_tracts) or not need_tract:
                            type_of_business_that_will_open = randomly_selected_type
                if self.town.population < 50 or tries > 10:  # Just not ready for more businesses yet -- grow naturally
                    break
            if type_of_business_that_will_open in self.config.business.public_company_types:
                type_of_business_that_will_open(owner=self.town.mayor, town=self.town, date=self.current_date, config=self.config)
                Business.create_business(type_of_business_that_will_open, self, self.town.mayor)

            elif type_of_business_that_will_open:
                owner = self._determine_who_will_establish_new_business(business_type=type_of_business_that_will_open)
                Business.create_business(type_of_business_that_will_open, self, owner)

    def _determine_who_will_establish_new_business(self, business_type):
        """Select a person who will establish a new business of the given type."""
        owner_occupation_class = \
            self.config.business.owner_occupations_for_each_business_type[business_type]

        if owner_occupation_class in self.config.business.occupations_requiring_college_degree:
            # get a list of residents in the town who are colleeg graduates and
            # have no prior jobs
            applicants = [p for p in self.town.residents
                                    if p.college_graduate
                                    and len(p.occupations) == 0
                                    and self.config.business.employable_as_a[owner_occupation_class](applicant=p)]

            if len(applicants) > 0:
                return random.choice(applicants)
            else:
                return PersonExNihilo.create_person(self, job_opportunity_impetus=owner_occupation_class)

        else:
            if self.config.business.job_levels[owner_occupation_class] < 3:
                applicants = [p for p in self.town.residents
                                            if p.in_the_workforce
                                            and len(p.occupations) == 0
                                            and self.config.business.employable_as_a[owner_occupation_class](applicant=p)]

                # Have a young person step up and start their career as a tradesman
                if len(applicants) > 0:
                    return random.choice(applicants)

                applicants = [p for p in self.town.residents
                                            if not p.retired
                                            and p.occupation is None
                                            and p.in_the_workforce
                                            and self.config.business.employable_as_a[owner_occupation_class](applicant=p)]

                # Have any unemployed person in town try their hand at running a business
                if len(applicants) > 0:
                    return random.choice(applicants)
                else:
                    # Have someone from outside the town come in
                    return PersonExNihilo.create_person(self, job_opportunity_impetus=owner_occupation_class)


        return PersonExNihilo.create_person(self, job_opportunity_impetus=owner_occupation_class)

    def _potentially_shut_down_businesses(self):
        """Potentially have a new business get constructed in town."""
        chance_a_business_shuts_down_this_timestep = self.config.basic.chance_a_business_closes()
        chance_a_business_shuts_down_on_timestep_after_its_demise = (
            # Once its anachronistic, like a Dairy in 1960
            self.config.business.chance_a_business_shuts_down_on_timestep_after_its_demise
        )
        for company in self.town.businesses:
            if company.demise <= self.current_date.year:
                if random.random() < chance_a_business_shuts_down_on_timestep_after_its_demise:
                    if company.__class__ not in self.config.business.public_company_types :
                        company.go_out_of_business(self, reason=None, date=self.current_date)
            elif random.random() < chance_a_business_shuts_down_this_timestep:
                if company.__class__ not in self.config.business.public_company_types:
                    if not (
                        # Don't shut down an apartment complex with people living in it,
                        # or an apartment complex that's the only one in town
                        company.__class__ is business.ApartmentComplex and company.residents or
                        len(self.town.get_businesses_of_type('ApartmentComplex')) == 1
                    ):
                        company.go_out_of_business(self, reason=None, date=self.current_date)

    def _simulate_timestep(self):
        """Simulate town activity for a single timestep."""
        self.n_simulated_timesteps += 1

        for person in self.town.residents:
            self._simulate_life_events_for_a_person_on_this_timestep(person=person)

        days_since_last_simulated_day = self.current_date.toordinal() - self.last_simulated_day

        # Reset all Relationship interacted_this_timestep attributes
        for person in self.town.residents:
            for other_person in person.relationships:
                person.relationships[other_person].interacted_this_timestep = False

        # Have people go to the location they will be at this timestep
        for person in self.town.residents:
            person.routine.enact(date=self.current_date)

        # Have people initiate social interactions with one another
        for person in self.town.residents:
            # Person may have married (during an earlier iteration of this loop) and
            # then immediately departed because the new couple could not find home,
            # so we still have to make sure they actually live in the town currently before
            # having them socialize
            if person in self.town.residents:
                if person.age > 3:  # Must be at least four years old to socialize
                    person.socialize(missing_timesteps_to_account_for=days_since_last_simulated_day * 2)

        self.last_simulated_day = self.current_date.toordinal()

    def _simulate_life_events_for_a_person_on_this_timestep(self, person):
        """Simulate the life of the given person on this timestep."""
        # First, we need to make sure that this person didn't already die or leave town
        # on an earlier iteration of this loop (e.g., a child whose parents decided to move)
        if person.present:
            self._simulate_prospect_of_death(person=person)
            # Throughout this block, we have to keep checking that the person is still present
            # because one of the steps in this procedure may cause them to either die or
            # leave town, and upon either of those occurring we stop simulating their life
            if person.present and not person.spouse:
                self._simulate_dating(person=person)
            if person.present and person.spouse:
                self._simulate_marriage(person=person)
            if person.present and person.occupation:
                self._simulate_prospect_of_retirement(person=person)
            elif person.present and person.in_the_workforce and not person.occupation and not person.retired:
                self._simulate_unemployment(person=person)
            elif person.present and person not in person.home.owners:
                self._simulate_moving_out_of_parents(person=person)

    def _simulate_prospect_of_death(self, person):
        """Simulate the potential for this person to die on this timestep."""
        if person.age > 68 and random.random() > self.config.life_cycle.chance_someone_dies:
            person.die(cause_of_death="Natural causes", date=self.current_date)

    def _simulate_dating(self, person):
        """Simulate the dating life of this person."""
        # I haven't yet implemented any systems modeling/simulating characters dating
        # or leading romantic lives at all, really; I'd love to do this at some point,
        # but currently all that is happening is characters evolve their romantic
        # affinities for one another (as a function of nonreciprocal romantic affinities
        # and amount of time spent together; see relationship.py), and if a threshold
        # for mutual romantic affinity is eclipsed, they may marry (right on this timestep)
        if person.age >= self.config.marriage.marriageable_age:
            min_mutual_spark_for_proposal = self.config.marriage.min_mutual_spark_value_for_someone_to_propose_marriage
            people_they_have_strong_romantic_feelings_for = [
                p for p in person.relationships if person.relationships[p].spark > min_mutual_spark_for_proposal
            ]
            for prospective_partner in people_they_have_strong_romantic_feelings_for:
                if prospective_partner.age >= self.config.marriage.marriageable_age:
                    if prospective_partner.present and not prospective_partner.spouse:
                        if prospective_partner.relationships[person].spark > min_mutual_spark_for_proposal:
                            person.marry(partner=prospective_partner, date=self.current_date)
                            break

    def _simulate_marriage(self, person):
        """Simulate basic marriage activities for this person."""
        self._simulate_prospect_of_conception(person=person)
        self._simulate_prospect_of_divorce(person=person)

    def _simulate_prospect_of_conception(self, person):
        """Simulate the potential for conception today in the course of this person's marriage."""
        chance_they_are_trying_to_conceive_this_year = self.config.marriage.chance_married_couple_are_trying_to_conceive(
                len(person.marriage.children_produced))

        chance_they_are_trying_to_conceive = (
            # Don't need 720, which is actual number of timesteps in a year, because their spouse will also
            # be iterated over on this timestep
            chance_they_are_trying_to_conceive_this_year / (self.config.basic.chance_of_a_timestep_being_simulated() * 365))

        if random.random() < chance_they_are_trying_to_conceive:
            person.have_sex(partner=person.spouse, protection=False)
        # Note: sex doesn't happen otherwise because no interesting phenomena surrounding it are
        # modeled/simulated; it's currently just a mechanism for bringing new characters into the world

    def _simulate_prospect_of_divorce(self, person):
        """Simulate the potential for divorce today in the course of this person's marriage."""
        # Check if this person is significantly more in love with someone else in town
        if person.love_interest:
            if person.love_interest is not person.spouse and person.love_interest.present:
                if random.random() < self.config.marriage.chance_of_divorce:
                    person.divorce(partner=person.spouse, date=self.current_date)

    def _simulate_prospect_of_retirement(self, person):
        """Simulate the potential for this person to retire on this timestep."""
        if person.occupation and person.age > max(65, random.random() * 100):
            person.retire(date=self.current_date)

    def _simulate_unemployment(self, person):
        """Simulate the given person searching for work, which may involve them getting a
        college education or deciding to leave town.
        """
        person.look_for_work(date=self.current_date)
        if not person.occupation:  # Means look_for_work() didn't succeed
            if self.current_date.year < 1920:
                if (not person.college_graduate) and person.age > 22 and person.male:
                    person.college_graduate = True
                    return
            else:
                person.college_graduate = True
                return

            if random.random() < self.config.basic.chance_an_unemployed_person_departs():
                if not (person.spouse and person.spouse.occupation):
                    person.depart_town(date=self.current_date)

    def _simulate_moving_out_of_parents(self, person):
        """Simulate the potential for this person to move out of their parents' home."""
        if person.occupation:
            if random.random() < self.config.life_cycle.chance_employed_adult_will_move_out_of_parents:
                person.move_out_of_parents()
