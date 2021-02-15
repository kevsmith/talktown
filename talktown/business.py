import random
import heapq
from ordered_set import OrderedSet
from . import life_event
from .place import Place
from .occupation import Architect, Lawyer, Apprentice
from .person import PersonExNihilo
from .residence import Residence, House, Apartment
from .corpora import Names
from .utils import get_random_day_of_year


class Business(Place):
    """A business in a town (representing both the notion of a company and its physical building).

    Objects of a business class represents both the company itself and the building
    at which it is headquartered. All business subclasses inherit generic attributes
    and methods from the superclass Business, and each define their own methods as
    appropriate.

    Attributes
    ----------
    founder: Person
        Person who founded the business

    owner: Occupation
        Current owner of the business

    town: Town
        Town the business is in

    founded: int
        Year the business was founded

    construction: BusinessConstruction
        Business Construction event from building this business

    employees: OrderedSet[Occupation]
        People who work at this business

    demise: int
        specifies a year at which point it is highly likely
        this business will close down (due to being
        anachronistic at that point, e.g., a dairy past 1930)

    services: Tuple[str, str,...]
        a tuple specifying the services offered by this business,
        given its type
    """

    def __init__(self, founder, date, town, config):
        """Initialize a Business object"""
        super().__init__()
        self.sim = founder.sim
        self.config = config
        self.founder = founder
        self.owner = None
        self.name = ""
        self.employees = OrderedSet()
        self.town = town
        self.founded = date.year
        self.demise = config.business.business_types_advent_demise_and_minimum_population[self.__class__][1]
        self.services = config.business.services_provided_by_business_of_type[self.__class__]

        # First, hire employees -- this is done first because the first-ever business, a
        # construction firm started by the town founder, will need to hire the town's
        # first architect before it can construct its own building
        self.former_employees = OrderedSet()
        self.former_owners = OrderedSet()

        # Also set the vacancies this company will initially have that may get filled
        # up gradually by people seeking employment (most often, this will be kids who
        # grow up and are ready to work and people who were recently laid off)
        self.supplemental_vacancies = {
            'day': list(config.business.initial_job_vacancies[self.__class__]['supplemental day']),
            'night': list(config.business.initial_job_vacancies[self.__class__]['supplemental night'])
        }

        # Set miscellaneous attributes
        self.demolition = None  # Potentially gets set by event.Demolition.__init__()
        self.out_of_business = False  # Potentially gets changed by go_out_of_business()
        self.closure = None  # BusinessClosure object itself
        self.closed = None  # Year closed

        # Set address
        self.lot, self.construction = self.secure_lot(founder, town, date, config)
        self.lot.building = self
        self.address = self.lot.address
        self.house_number = self.lot.house_number
        self.street_address_is_on = self.lot.street_address_is_on
        self.block = self.lot.block

    @staticmethod
    def create_business(class_type, sim, founder=None):
        """Create a business and add it to the town

            Parameters
            ----------
            class_type: Type
                Class of business to instantiate
            sim: Simulation
                Talk of the Town simulation
            founder: Person
                Person who will found the business
            date: datetime
                Date this business was founded
        """
        business = class_type(founder,
                              date=sim.current_date,
                              town=sim.town,
                              config=sim.config)

        sim.town.businesses.add(business)

        if class_type not in sim.config.business.public_company_types:
            owner_occupation_class = \
                sim.config.business.owner_occupations_for_each_business_type[business.__class__]

            business.hire(owner_occupation_class,
                          "day",
                          sim.current_date,
                          selected_candidate=founder)

        business.hire_initial_employees(sim.current_date)

        business.generate_name()

    def secure_lot(self, founder, town, date, config):
        """Find a lot to build this business"""
        construction = None
        demolition = None
        if len(town.vacant_lots) > 0 \
           and not (self.__class__ in config.business.companies_that_get_established_on_tracts):

            lot = self._init_choose_vacant_lot()

        elif len(town.vacant_tracts) > 0 \
           and self.__class__ in config.business.companies_that_get_established_on_tracts:

           lot = self._init_choose_vacant_lot()

        else:
            lot = self._init_acquire_currently_occupied_lot()
            demolition_company = None

            if len(self.town.get_businesses_of_type('ConstructionFirm')) > 0:
                demolition_company = random.choice(town.get_businesses_of_type('ConstructionFirm'))

            demolition = life_event.Demolition(building=lot.building,
                                               demolition_company=demolition_company,
                                               date=date)
            lot.building.on_demolition(demolition)
            founder.sim.register_event(demolition)

        if self.__class__ not in self.sim.config.business.companies_that_get_established_on_tracts:
            # Try to find an architect -- if you can't, you'll have to build it yourself
            architect = founder.contract_person_of_certain_occupation(occupation_in_question=Architect)

            construction = life_event.BusinessConstruction(subject=founder, business=self, architect=architect, date=date)

            if architect is not None:
                architect.building_constructions.add(construction)

            founder.building_commissions.add(construction)

            founder.sim.register_event(construction)

            # If a demolition of an earlier building preceded the construction of this business,
            # attribute our new BusinessConstruction object as the .reason attribute for that
            # Demolition attribute
            if demolition is not None:
                demolition.reason = construction

        return lot, construction

    def on_demolition(self, demolition_event):
        """Callback function triggered when business is demolished"""
        self.demolition = demolition_event
        self.lot.building = None
        self.lot.former_buildings.append(self)

    def generate_name(self):
        """Get named by the owner of this building (the client for which it was constructed)."""
        name = ""


        if self.__class__ not in self.config.business.classes_that_get_special_names:
            if random.random() < self.config.business.chance_company_gets_named_after_owner:
                prefix = self.owner.person.last_name
            else:
                prefix = self.street_address_is_on.name
            name = "{0} {1}".format(prefix, self.config.business.class_to_company_name_component[self.__class__])

        elif self.__class__ is Park:
            if len(self.lot.former_buildings) > 0 \
               and self.lot.former_buildings[-1].__class__ in Business.__subclasses__():
                business_here_previously = self.lot.former_buildings[-1]
                if business_here_previously.__class__ is Farm:
                    owner = business_here_previously.owner.person
                    x = random.random()
                    if x < 0.25:
                        name = '{} {} Park'.format(
                            owner.first_name, owner.last_name
                        )
                    elif x < 0.5:
                        name = '{} Farm Park'.format(
                            owner.last_name
                        )

                    elif x < 0.75:
                        name = '{} Park'.format(
                            owner.last_name
                        )
                    elif x < 0.8:
                        name = 'Old Farm Park'
                    elif x < 0.9:
                        name = '{} {} Memorial Park'.format(
                            owner.first_name, owner.last_name
                        )
                    elif x < 0.97:
                        name = '{} Memorial Park'.format(
                            owner.last_name
                        )
                    else:
                        name = '{} Park'.format(self.town.name)
                elif business_here_previously.__class__ is Quarry:
                    owner = business_here_previously.owner.person
                    x = random.random()
                    if x < 0.25:
                        name = '{} {} Park'.format(
                            owner.first_name, owner.last_name
                        )
                    elif x < 0.5:
                        name = '{} Park'.format(
                            business_here_previously.name
                        )

                    elif x < 0.75:
                        name = '{} Park'.format(
                            owner.last_name
                        )
                    elif x < 0.8:
                        name = 'Old Quarry Park'
                    elif x < 0.9:
                        name = '{} {} Memorial Park'.format(
                            owner.first_name, owner.last_name
                        )
                    elif x < 0.97:
                        name = '{} Quarry Park'.format(
                            owner.last_name
                        )
                    else:
                        name = '{} Park'.format(self.town.name)
                elif business_here_previously.__class__ is CoalMine:
                    owner = business_here_previously.owner.person
                    x = random.random()
                    if x < 0.25:
                        name = '{} {} Park'.format(
                            owner.first_name, owner.last_name
                        )
                    elif x < 0.5:
                        name = '{} Park'.format(
                            business_here_previously.name
                        )

                    elif x < 0.75:
                        name = '{} Park'.format(
                            owner.last_name
                        )
                    elif x < 0.8:
                        name = 'Old Mine Park'
                    elif x < 0.9:
                        name = '{} {} Memorial Park'.format(
                            owner.first_name, owner.last_name
                        )
                    elif x < 0.97:
                        name = '{} Coal Mine Park'.format(
                            owner.last_name
                        )
                    elif x < 0.99:
                        name = '{} Coal Park'.format(
                            owner.last_name
                        )
                    else:
                        name = '{} Park'.format(self.town.name)
            else:
                name = "{} Park".format(self.founder.last_name)
        else:

            raise Exception("A company of class {} was unable to be named.".format(self.__class__.__name__))
        self.name = name

    def __str__(self):
        """Return string representation."""
        if not self.out_of_business:
            return "{}, {} (founded {})".format(self.name, self.address, self.founded)
        else:
            return "{}, {} ({}-{})".format(self.name, self.address, self.founded, self.closed)

    def hire_initial_employees(self, date):
        """Fill all the positions that are vacant at the time of this company forming."""
        # Hire employees for the day shift
        for vacant_position in self.config.business.initial_job_vacancies[self.__class__]['day']:
            self.hire(occupation_of_need=vacant_position, shift="day", date=date)
        # Hire employees for the night shift
        for vacant_position in self.config.business.initial_job_vacancies[self.__class__]['night']:
            self.hire(occupation_of_need=vacant_position, shift="night", date=date)

    def _init_acquire_currently_occupied_lot(self):
        """If there are no vacant lots in town, acquire a lot and demolish the home currently on it."""
        lot_scores = self._rate_all_occupied_lots()
        if len(lot_scores) >= 3:
            # Pick from top three
            top_three_choices = heapq.nlargest(3, lot_scores, key=lot_scores.get)
            if random.random() < 0.6:
                choice = top_three_choices[0]
            elif random.random() < 0.9:
                choice = top_three_choices[1]
            else:
                choice = top_three_choices[2]
        elif lot_scores:
            choice = max(lot_scores)
        else:
            raise Exception("A company attempted to secure an *occupied* lot in town but somehow could not.")
        return choice

    def _rate_all_occupied_lots(self):
        """Rate all lots currently occupied by homes for their desirability as business locations."""
        lots_with_homes_on_them = (
            l for l in self.town.lots if l.building and isinstance(l.building, Residence)
        )
        scores = {}
        for lot in lots_with_homes_on_them:
            scores[lot] = self._rate_potential_lot(lot=lot)
        return scores

    def _init_choose_vacant_lot(self):
        """Choose a vacant lot on which to build the company building.

        Currently, a company scores all the vacant lots in town and then selects
        one of the top three. TODO: Probabilistically select from all lots using
        the scores to derive likelihoods of selecting each.
        """
        if self.__class__ in self.config.business.companies_that_get_established_on_tracts:
            vacant_lots_or_tracts = self.town.vacant_tracts
        else:
            vacant_lots_or_tracts = self.town.vacant_lots
        assert vacant_lots_or_tracts, (
            "{} is attempting to found a {}, but there's no vacant lots/tracts in {}".format(
                self.founder.name, self.__class__.__name__, self.town.name
            )
        )
        lot_scores = self._rate_all_vacant_lots()
        if len(lot_scores) >= 3:
            # Pick from top three
            top_three_choices = heapq.nlargest(3, lot_scores, key=lot_scores.get)
            if random.random() < 0.6:
                choice = top_three_choices[0]
            elif random.random() < 0.9:
                choice = top_three_choices[1]
            else:
                choice = top_three_choices[2]
        elif lot_scores:
            choice = max(lot_scores)
        else:
            raise Exception("A company attempted to secure a lot in town when in fact none are vacant.")
        return choice

    def _rate_all_vacant_lots(self):
        """Rate all vacant lots for the desirability of their locations.
        """
        if self.__class__ in self.config.business.companies_that_get_established_on_tracts:
            vacant_lots_or_tracts = self.town.vacant_tracts
        else:
            vacant_lots_or_tracts = self.town.vacant_lots
        scores = {}
        for lot in vacant_lots_or_tracts:
            scores[lot] = self._rate_potential_lot(lot=lot)
        return scores

    def _rate_potential_lot(self, lot):
        """Rate a vacant lot for the desirability of its location.

        By this method, a company appraises a vacant lot in the town for how much they
        would like to build there, given considerations to its proximity to downtown,
        proximity to other businesses of the same type, and to the number of people living
        near the lot.
        """
        score = 0
        # As (now) the only criterion, rate lots according to their distance
        # from downtown; this causes a downtown commercial area to naturally emerge
        score -= self.town.dist_from_downtown(lot)
        return score

    @property
    def locked(self, time_of_day):
        """Return True if the entrance to this building is currently locked, else false."""
        locked = False
        # Apartment complexes are always locked
        if self.__class__ is ApartmentComplex:
            locked = True
        # Public institutions, like parks and cemeteries and city hall, are also always locked at night
        if (time_of_day == "night" and
                self.__class__ in self.config.business.public_places_closed_at_night):
            locked = True
        # Other businesses are locked only when no one is working, or
        # at night when only a janitor is working
        else:
            if not self.working_right_now:
                locked = True
            elif not any(e for e in self.working_right_now if e[0] != 'janitor'):
                locked = True
        return locked

    @property
    def residents(self):
        """Return the employees that work here.

         This is meant to facilitate a Lot reasoning over its population and the population
         of its local area. This reasoning is needed so that developers can decide where to
         build businesses. For all businesses but ApartmentComplex, this just returns the
         employees that work at this building (which makes sense in the case of, e.g., building
         a restaurant nearby where people work); for ApartmentComplex, this is overridden
         to return the employees that work there and also the people that live there.
         """
        return OrderedSet([employee.person for employee in self.employees])

    @property
    def working_right_now(self):
        people_working = [p for p in self.people_here_now if p.routine.working]
        return [(p.occupation.vocation, p) for p in people_working]

    @property
    def day_shift(self):
        """Return all employees who work the day shift here."""
        day_shift = OrderedSet([employee for employee in self.employees if employee.shift == "day"])
        return day_shift

    @property
    def night_shift(self):
        """Return all employees who work the night shift here."""
        night_shift = OrderedSet([employee for employee in self.employees if employee.shift == "night"])
        return night_shift

    @property
    def sign(self):
        """Return a string representing this business's sign."""
        if self.__class__ in self.config.business.public_company_types:
            return self.name
        elif self.sim.current_date.year - self.founded > 8:
            return '{}, since {}'.format(self.name, self.founded)
        else:
            return self.name

    def _find_candidate(self, occupation_of_need):
        """Find the best available candidate to fill the given occupation of need."""
        # If you have someone working here who is an apprentice, hire them outright
        if (self.config.business.job_levels[occupation_of_need] > self.config.business.job_levels[Apprentice] and
                any(e for e in self.employees if e.__class__ == Apprentice and e.years_experience > 0)):
            selected_candidate = next(
                e for e in self.employees if e.__class__ == Apprentice and e.years_experience > 0
            ).person
        else:
            job_candidates_in_town = self._assemble_job_candidates(occupation_of_need=occupation_of_need)
            if job_candidates_in_town:
                candidate_scores = self._rate_all_job_candidates(candidates=job_candidates_in_town)
                selected_candidate = self._select_candidate(candidate_scores=candidate_scores)
            else:
                selected_candidate = self._find_candidate_from_outside_the_town(occupation_of_need=occupation_of_need)
        return selected_candidate

    def hire(self, occupation_of_need, shift, date, to_replace=None,
             fills_supplemental_job_vacancy=False, selected_candidate=None, hired_as_a_favor=False):
        """Hire the given selected candidate."""

        if not selected_candidate:
            selected_candidate = self._find_candidate(occupation_of_need=occupation_of_need)

        # Instantiate the new occupation -- this means that the subject may
        # momentarily have two occupations simultaneously
        new_position = occupation_of_need(person=selected_candidate, company=self, shift=shift)

        # If this person is being hired to replace a now-former employee, attribute
        # this new position as the successor to the former one
        if to_replace:
            to_replace.succeeded_by = new_position
            new_position.preceded_by = to_replace
            # If this person is being hired to replace the owner, they are now the owner --
            # TODO not all businesses should transfer ownership using the standard hiring process
            if to_replace is self.owner:
                self.owner = new_position

        owner_occupation_class = \
                self.config.business.owner_occupations_for_each_business_type[self.__class__]

        if occupation_of_need == owner_occupation_class:
            self.owner = new_position

        # Now instantiate a Hiring object to hold data about the hiring
        hiring = life_event.Hiring(subject=selected_candidate, company=self, occupation=new_position, date=date)
        new_position.hiring = hiring
        selected_candidate.life_events.add(hiring)
        selected_candidate.sim.register_event(hiring)

        # Now terminate the person's former occupation, if any (which may cause
        # a hiring chain and this person's former position goes vacant and is filled,
        # and so forth); this has to happen after the new occupation is instantiated, or
        # else they may be hired to fill their own vacated position, which will cause problems
        # [Actually, this currently wouldn't happen, because lateral job movement is not
        # possible given how companies assemble job candidates, but it still makes more sense
        # to have this person put in their new position *before* the chain sets off, because it
        # better represents what really is a domino-effect situation)
        if selected_candidate.occupation:
            selected_candidate.occupation.terminate(reason=hiring, date=date)

        # Now you can set the employee's occupation to the new occupation (had you done it
        # prior, either here or elsewhere, it would have terminated the occupation that this
        # person was just hired for, triggering endless recursion as the company tries to
        # fill this vacancy in a Sisyphean nightmare)
        selected_candidate.occupation = new_position


        # If this is a law firm and the new hire is a lawyer, change the name
        # of this firm to include the new lawyer's name
        if self.__class__ == "LawFirm" and new_position == Lawyer:
            self._init_get_named()
        # If this position filled one of this company's "supplemental" job vacancies (see
        # config.py), then remove an instance of this position from that list
        if fills_supplemental_job_vacancy:
            self.supplemental_vacancies[shift].remove(occupation_of_need)
            # This position doesn't have to be refilled immediately if terminated, so
            # attribute to it that it is supplemental
            selected_candidate.occupation.supplemental = True
        # Being hired as a favor means this business created an additional position
        # beyond all their supplemental positions (because those were all filled)
        # specifically to facilitate the hiring of this person (who will have been
        # a family member of this company's owner); because of this, when this position
        # terminates we don't want to add it back to the supplemental vacancies of this
        # company, because they really don't need to refill the position ever and if they
        # do, it yields rampant population growth due to there being way too many jobs
        # in town
        selected_candidate.occupation.hired_as_favor = hired_as_a_favor
        # Lastly, if the person was hired from outside the town, have them move to it
        if selected_candidate.town is not self.town:
            selected_candidate.move_into_the_town(self.town, hiring, date=date)

    @staticmethod
    def _select_candidate(candidate_scores):
        """Select a person to serve in a certain occupational capacity."""
        if len(candidate_scores) >= 3:
            # Pick from top three
            top_three_choices = heapq.nlargest(3, candidate_scores, key=candidate_scores.get)
            if random.random() < 0.6:
                chosen_candidate = top_three_choices[0]
            elif random.random() < 0.9:
                chosen_candidate = top_three_choices[1]
            else:
                chosen_candidate = top_three_choices[2]
        else:
            chosen_candidate = max(candidate_scores)
        return chosen_candidate

    def _find_candidate_from_outside_the_town(self, occupation_of_need):
        """Generate a PersonExNihilo to move into the town for this job."""
        return PersonExNihilo.create_person(self.sim, job_opportunity_impetus=occupation_of_need)

    def _rate_all_job_candidates(self, candidates):
        """Rate all job candidates."""
        scores = {}
        for candidate in candidates:
            scores[candidate] = self.rate_job_candidate(person=candidate)
        return scores

    def rate_job_candidate(self, person):
        """Rate a job candidate, given an open position and owner biases."""
        decision_maker = self.owner.person if self.owner else self.town.mayor
        score = 0.0
        if person in self.employees:
            score += self.config.misc_character_decision_making.preference_to_hire_from_within_company
        if person in decision_maker.immediate_family:
            score += self.config.misc_character_decision_making.preference_to_hire_immediate_family
        elif person in decision_maker.extended_family:
            score += self.config.misc_character_decision_making.preference_to_hire_extended_family
        if person.immediate_family & self.employees:
            score += self.config.misc_character_decision_making.preference_to_hire_immediate_family_of_an_employee
        elif person.extended_family & self.employees:
            score += self.config.misc_character_decision_making.preference_to_hire_extended_family_of_an_employee
        if person in decision_maker.friends:
            score += self.config.misc_character_decision_making.preference_to_hire_friend
        elif person in decision_maker.acquaintances:
            score += self.config.misc_character_decision_making.preference_to_hire_acquaintance
        if person in decision_maker.enemies:
            score += self.config.misc_character_decision_making.dispreference_to_hire_enemy
        if person.occupation:
            score *= person.occupation.level
        else:
            score *= self.config.misc_character_decision_making.unemployment_occupation_level
        return score

    def _assemble_job_candidates(self, occupation_of_need):
        """Assemble a group of job candidates for an open position."""
        candidates = OrderedSet()
        # Consider people that already work in this town -- this will subsume
        # reasoning over people that could be promoted from within this company
        for company in self.town.businesses:
            for position in company.employees:
                person_is_qualified = self.check_if_person_is_qualified_for_the_position(
                    candidate=position.person, occupation_of_need=occupation_of_need
                )
                if person_is_qualified:
                    candidates.add(position.person)
        # Consider unemployed (mostly young) people if they are qualified
        for person in self.town.unemployed:
            person_is_qualified = self.check_if_person_is_qualified_for_the_position(
                candidate=person, occupation_of_need=occupation_of_need
            )
            if person_is_qualified:
                candidates.add(person)
        return candidates

    def check_if_person_is_qualified_for_the_position(self, candidate, occupation_of_need):
        """Check if the job candidate is qualified for the position you are hiring for."""
        qualified = False
        level_of_this_position = self.config.business.job_levels[occupation_of_need]
        # Make sure they are not already at a job of higher prestige; people that
        # used to work higher-level jobs may stoop back to lower levels if they are
        # now out of work
        if candidate.occupation:
            candidate_job_level = candidate.occupation.level
        elif candidate.occupations:
            candidate_job_level = max(candidate.occupations, key=lambda o: o.level).level
        else:
            candidate_job_level = 0
        if not (candidate.occupation and candidate_job_level >= level_of_this_position):
            # Make sure they have a college degree if one is required to have this occupation
            if occupation_of_need in self.config.business.occupations_requiring_college_degree:
                if candidate.college_graduate:
                    qualified = True
            else:
                qualified = True
        # Make sure the candidate meets the essential preconditions for this position;
        # note: most of these preconditions are meant to maintain basic historically accuracy
        if not self.config.business.employable_as_a[occupation_of_need](applicant=candidate):
            qualified = False
        # Lastly, make sure they have been at their old job for at least a year,
        # if they had one
        if candidate.occupation and candidate.occupation.years_experience < 1:
            qualified = False
        return qualified

    def go_out_of_business(self, sim, reason, date):
        """Cease operation of this business."""
        closure_event = life_event.BusinessClosure(business=self, reason=reason, date=date)
        sim.register_event(closure_event)
        self.closure = closure_event
        self.out_of_business = True
        self.closed = date.year

        # Lay off employees
        for employee in self.employees:
            layoff_event = life_event.LayOff(person=employee.person,
                                  occupation=employee,
                                  business=self,
                                  date=date,
                                  reason=closure_event)
            employee.person.lay_offs.append(layoff_event)
            employee.person.life_events.add(layoff_event)
            employee.terminate(reason=layoff_event, date=date)
            sim.register_event(layoff_event)


        # Remove the business from the town
        self.town.businesses.remove(self)
        self.town.former_businesses.add(self)

         # Demolish the building -- TODO reify buildings separately from companies
        if self.town.get_businesses_of_type('ConstructionFirm'):
            demolition_company = random.choice(self.town.get_businesses_of_type('ConstructionFirm'))
        else:
            demolition_company = None
        demolition_event = life_event.Demolition(building=self, demolition_company=demolition_company, reason=closure_event, date=date)

        self.on_demolition(demolition_event)
        sim.register_event(demolition_event)


class ApartmentComplex(Business):
    """An apartment complex."""

    def __init__(self, owner, town, date, config):
        """Initialize an ApartmentComplex object.

        @param owner: The owner of this business.
        """
        # Have to do this to allow .residents to be able to return a value before
        # this object has its units attributed -- this is because new employees
        # hired to work here may actually move in during the larger init() call
        self.units = []
        super().__init__(owner, date, town, config)
        self.units = self._init_apartment_units(owner)

    def _init_apartment_units(self, owner):
        """Instantiate objects for the individual units in this apartment complex."""
        n_units_to_build = random.randint(
            self.config.business.number_of_apartment_units_in_new_complex_min,
            self.config.business.number_of_apartment_units_in_new_complex_max
        )
        if n_units_to_build % 2 != 0:
            # Make it a nice even number
            n_units_to_build -= 1
        apartment_units = []
        for i in range(n_units_to_build):
            unit_number = i + 1
            apartment_units.append(
                Apartment(apartment_complex=self, owners=(owner,),lot=self.lot, unit_number=unit_number, town=self.town)
            )
        return apartment_units

    @property
    def residents(self):
        """Return the residents that live here."""
        residents = OrderedSet()
        for unit in self.units:
            residents |= unit.residents
        return residents

    def expand(self):
        """Add two extra units in this complex.

        The impetus for this method being called is to accommodate a new person in town seeking housing.
        Since apartment complexes in this simulation always have an even number of units, we add two extra
        ones to maintain that property.
        """
        currently_highest_unit_number = max(self.units, key=lambda u: u.unit_number).unit_number
        next_unit_number = currently_highest_unit_number + 1
        self.units.append(
            Apartment(apartment_complex=self, owners=(self.owner,), lot=self.lot, unit_number=next_unit_number, town=self.town)
        )
        self.units.append(
            Apartment(apartment_complex=self, owners=(self.owner,), lot=self.lot, unit_number=next_unit_number+1, town=self.town)
        )

    def on_demolition(self, demolition_event):
        """Callback function triggered when business is demolished"""
        super().on_demolition(demolition_event)
        for unit in self.units:
            self.town.residences.remove(unit)
            if unit.residents:
                life_event.Demolition.have_the_now_displaced_residents_move(unit, demolition_event)

class Bakery(Business):
    """A bakery."""

    def __init__(self, owner, date, town, config):
        """Initialize a Bakery object.

        @param owner: The owner of this business.
        """
        super().__init__(owner, date, town, config=config)


class Bank(Business):
    """A bank."""

    def __init__(self, owner, date, town, config):
        """Initialize a Bank object.

        @param owner: The owner of this business.
        """
        super().__init__(owner, date, town, config=config)


class Bar(Business):
    """A bar."""

    def __init__(self, owner, date, town, config):
        """Initialize a Restaurant object.

        @param owner: The owner of this business.
        """
        super().__init__(owner, date, town, config=config)

    def generate_name(self):
        return Names.a_bar_name()

class Barbershop(Business):
    """A barbershop."""

    def __init__(self, owner, date, town, config):
        """Initialize a Barbershop object.

        @param owner: The owner of this business.
        """
        super().__init__(owner, date, town, config=config)


class BlacksmithShop(Business):
    """A blacksmith business."""

    def __init__(self, owner, date, town, config):
        """Initialize a BlacksmithShop object.

        @param owner: The owner of this business.
        """
        super().__init__(owner, date, town, config=config)


class Brewery(Business):
    """A brewery."""

    def __init__(self, owner, date, town, config):
        """Initialize a Brewery object.

        @param owner: The owner of this business.
        """
        super().__init__(owner, date, town, config=config)


class BusDepot(Business):
    """A bus depot."""

    def __init__(self, owner, date, town, config):
        """Initialize a BusDepot object.

        @param owner: The owner of this business.
        """
        super().__init__(owner, date, town, config=config)


class ButcherShop(Business):
    """A butcher business."""

    def __init__(self, owner, date, town, config):
        """Initialize a ButcherShop object.

        @param owner: The owner of this business.
        """
        super().__init__(owner, date, town, config=config)


class CandyStore(Business):
    """A candy store."""

    def __init__(self, owner, date, town, config):
        """Initialize a CandyStore object.

        @param owner: The owner of this business.
        """
        super().__init__(owner, date, town, config=config)


class CarpentryCompany(Business):
    """A carpentry company."""

    def __init__(self, owner, date, town, config):
        """Initialize a CarpentryCompany object.

        @param owner: The owner of this business.
        """
        super().__init__(owner, date, town, config=config)


class Cemetery(Business):
    """A cemetery on a tract in a town."""

    def __init__(self, owner, date, town, config):
        """Initialize a Cemetery object."""
        super().__init__(owner, date, town, config=config)
        self.town.cemetery = self
        self.plots = {}

    def inter_person(self, person):
        """Inter a new person by assigning them a plot in the graveyard."""
        if not self.plots:
            new_plot_number = 1
        else:
            new_plot_number = max(self.plots) + 1
        self.plots[new_plot_number] = person
        return new_plot_number

    def generate_name(self):
        return "{0} {1}".format(self.town.name, self.config.business.class_to_company_name_component[Cemetery])



class CityHall(Business):
    """The city hall."""

    def __init__(self, owner, date, town, config):
        """Initialize a CityHall object.

        @param owner: The owner of this business.
        """
        super().__init__(owner, date, town, config=config)
        self.town.city_hall = self

    def generate_name(self):
        return "{0} {1}".format(self.town.name, self.config.business.class_to_company_name_component[CityHall])


class ClothingStore(Business):
    """A store that sells clothing only; i.e., not a department store."""

    def __init__(self, owner, date, town, config):
        """Initialize a ClothingStore object.

        @param owner: The owner of this business.
        """
        super().__init__(owner, date, town, config=config)


class CoalMine(Business):
    """A coal mine."""

    def __init__(self, owner, date, town, config):
        """Initialize a ClothingStore object.

        @param owner: The owner of this business.
        """
        super().__init__(owner, date, town, config=config)


class ConstructionFirm(Business):
    """A construction firm."""

    def __init__(self, owner, date, town, config):
        """Initialize an ConstructionFirm object.

        @param owner: The owner of this business.
        """
        super().__init__(owner, date, town, config=config)

    @property
    def house_constructions(self):
        """Return all house constructions."""
        house_constructions = OrderedSet()
        for employee in self.employees | self.former_employees:
            if hasattr(employee, 'house_constructions'):
                house_constructions |= employee.house_constructions
        return house_constructions

    @property
    def building_constructions(self):
        """Return all building constructions."""
        building_constructions = OrderedSet()
        for employee in self.employees | self.former_employees:
            if hasattr(employee, 'building_constructions'):
                building_constructions |= employee.building_constructions
        return building_constructions


class Dairy(Business):
    """A store where milk is sold and from which milk is distributed."""

    def __init__(self, owner, date, town, config):
        """Initialize a Dairy object.

        @param owner: The owner of this business.
        """
        super().__init__(owner, date, town, config=config)


class DayCare(Business):
    """A day care center for young children."""

    def __init__(self, owner, date, town, config):
        """Initialize a DayCare object.

        @param owner: The owner of this business.
        """
        super().__init__(owner, date, town, config=config)


class Deli(Business):
    """A delicatessen."""

    def __init__(self, owner, date, town, config):
        """Initialize a Deli object.

        @param owner: The owner of this business.
        """
        super().__init__(owner, date, town, config=config)


class DentistOffice(Business):
    """A dentist office."""

    def __init__(self, owner, date, town, config):
        """Initialize a DentistOffice object.

        @param owner: The owner of this business.
        """
        super().__init__(owner, date, town, config=config)


class DepartmentStore(Business):
    """A department store."""

    def __init__(self, owner, date, town, config):
        """Initialize a DepartmentStore object.

        @param owner: The owner of this business.
        """
        super().__init__(owner, date, town, config=config)


class Diner(Business):
    """A diner."""

    def __init__(self, owner, date, town, config):
        """Initialize a Diner object.

        @param owner: The owner of this business.
        """
        super().__init__(owner, date, town, config=config)


class Distillery(Business):
    """A whiskey distillery."""

    def __init__(self, owner, date, town, config):
        """Initialize a Distillery object.

        @param owner: The owner of this business.
        """
        super().__init__(owner, date, town, config=config)


class DrugStore(Business):
    """A drug store."""

    def __init__(self, owner, date, town, config):
        """Initialize a DrugStore object.

        @param owner: The owner of this business.
        """
        super().__init__(owner, date, town, config=config)


class Farm(Business):
    """A farm on a tract in a town."""

    def __init__(self, owner, date, town, config):
        """Initialize a Farm object.

        @param owner: The owner of this business.
        """
        super().__init__(owner, date, town, config=config)

    def generate_name(self):
        name = "{}'s farm".format(self.owner.person.name)
        if any(c for c in self.town.businesses if c.name == name):
            name = "{}'s farm".format(self.owner.person.full_name)
        return name

class FireStation(Business):
    """A fire station."""

    def __init__(self, owner, date, town, config):
        """Initialize an FireStation object.

        @param owner: The owner of this business.
        """
        super().__init__(owner, date, town, config=config)
        self.town.fire_station = self

    def generate_name(self):
        return "{0} {1}".format(self.town.name, self.config.business.class_to_company_name_component[FireStation])



class Foundry(Business):
    """A metal foundry."""

    def __init__(self, owner, date, town, config):
        """Initialize a Foundry object.

        @param owner: The owner of this business.
        """
        super().__init__(owner, date, town, config=config)


class FurnitureStore(Business):
    """A furniture store."""

    def __init__(self, owner, date, town, config):
        """Initialize a FurnitureStore object.

        @param owner: The owner of this business.
        """
        super().__init__(owner, date, town, config=config)


class GeneralStore(Business):
    """A general store."""

    def __init__(self, owner, date, town, config):
        """Initialize a GeneralStore object.

        @param owner: The owner of this business.
        """
        super().__init__(owner, date, town, config=config)


class GroceryStore(Business):
    """A grocery store."""

    def __init__(self, owner, date, town, config):
        """Initialize a GroceryStore object.

        @param owner: The owner of this business.
        """
        super().__init__(owner, date, town, config=config)


class HardwareStore(Business):
    """A hardware store."""

    def __init__(self, owner, date, town, config):
        """Initialize a HardwareStore object.

        @param owner: The owner of this business.
        """
        super().__init__(owner, date, town, config=config)


class Hospital(Business):
    """A hospital."""

    def __init__(self, owner, date, town, config):
        """Initialize an Hospital object.

        @param owner: The owner of this business.
        """
        super().__init__(owner, date, town, config=config)
        self.town.hospital = self

    @property
    def baby_deliveries(self):
        """Return all baby deliveries."""
        baby_deliveries = OrderedSet()
        for employee in self.employees | self.former_employees:
            if hasattr(employee, 'baby_deliveries'):
                baby_deliveries |= employee.baby_deliveries
        return baby_deliveries

    def generate_name(self):
        return "{0} {1}".format(self.town.name, self.config.business.class_to_company_name_component[Hospital])



class Hotel(Business):
    """A hotel."""

    def __init__(self, owner, date, town, config):
        """Initialize a Hotel object.

        @param owner: The owner of this business.
        """
        super().__init__(owner, date, town, config=config)


class Inn(Business):
    """An inn."""

    def __init__(self, owner, date, town, config):
        """Initialize an Inn object.

        @param owner: The owner of this business.
        """
        super().__init__(owner, date, town, config=config)


class InsuranceCompany(Business):
    """An insurance company."""

    def __init__(self, owner, date, town, config):
        """Initialize an InsuranceCompany object.

        @param owner: The owner of this business.
        """
        super().__init__(owner, date, town, config=config)


class JeweleryShop(Business):
    """A jewelry company."""

    def __init__(self, owner, date, town, config):
        """Initialize a JeweleryShop object.

        @param owner: The owner of this business.
        """
        super().__init__(owner, date, town, config=config)


class LawFirm(Business):
    """A law firm."""

    def __init__(self, owner, date, town, config):
        """Initialize a LawFirm object.

        @param owner: The owner of this business.
        """
        super().__init__(owner, date, town, config=config)

    def generate_name(self):
        associates = [e for e in self.employees if e.__class__ is Lawyer]
        suffix = "{0} & {1}".format(
            ', '.join(a.person.last_name for a in associates[:-1]), associates[-1].person.last_name
        )
        name = "{0} {1}".format(self.config.business.class_to_company_name_component[LawFirm], suffix)
        return name

    def rename_due_to_lawyer_change(self):
        """Rename this company due to the hiring of a new lawyer."""
        partners = [e for e in self.employees if e.__class__ is Lawyer]
        if len(partners) > 1:
            partners_str = "{} & {}".format(
                ', '.join(a.person.last_name for a in partners[:-1]),
                partners[-1].person.last_name
            )
            self.name = "Law Offices of {}".format(partners_str)
        elif partners:
            # If there's only one lawyer at this firm now, have its
            # name be 'Law Offices of [first name] [last name]'
            self.name = "Law Offices of {} {}".format(
                partners[0].person.first_name, partners[0].person.last_name
            )
        else:
            # The only lawyer working here retired or departed the town -- the
            # business will shut down shortly and this will be its final name
            pass

    @property
    def filed_divorces(self):
        """Return all divorces filed through this law firm."""
        filed_divorces = OrderedSet()
        for employee in self.employees | self.former_employees:
            if hasattr(employee, 'filed_divorces'):
                filed_divorces |= employee.filed_divorces
        return filed_divorces

    @property
    def filed_name_changes(self):
        """Return all name changes filed through this law firm."""
        filed_name_changes = OrderedSet()
        for employee in self.employees | self.former_employees:
            filed_name_changes |= employee.filed_name_changes
        return filed_name_changes


class OptometryClinic(Business):
    """An optometry clinic."""

    def __init__(self, owner, date, town, config):
        """Initialize an OptometryClinic object.

        @param owner: The owner of this business.
        """
        super().__init__(owner, date, town, config=config)


class PaintingCompany(Business):
    """A painting company."""

    def __init__(self, owner, date, town, config):
        """Initialize a PaintingCompany object."""
        super().__init__(owner, date, town, config=config)


class Park(Business):
    """A park on a tract in a town."""

    def __init__(self, owner, date, town, config):
        """Initialize a Park object."""
        super().__init__(owner, date, town, config=config)


class Pharmacy(Business):
    """A pharmacy."""

    def __init__(self, owner, date, town, config):
        """Initialize a Pharmacy object."""
        super().__init__(owner, date, town, config=config)


class PlasticSurgeryClinic(Business):
    """A plastic-surgery clinic."""

    def __init__(self, owner, date, town, config):
        """Initialize a PlasticSurgeryClinic object.

        @param owner: The owner of this business.
        """
        super().__init__(owner, date, town, config=config)


class PlumbingCompany(Business):
    """A plumbing company."""

    def __init__(self, owner, date, town, config):
        """Initialize a PlumbingCompany object.

        @param owner: The owner of this business.
        """
        super().__init__(owner, date, town, config=config)


class PoliceStation(Business):
    """A police station."""

    def __init__(self, owner, date, town, config):
        """Initialize a PoliceStation object.

        @param owner: The owner of this business.
        """
        super().__init__(owner, date, town, config=config)
        self.town.police_station = self

    def generate_name(self):
        return "{0} {1}".format(self.town.name, self.config.business.class_to_company_name_component[PoliceStation])


class Quarry(Business):
    """A rock quarry."""

    def __init__(self, owner, date, town, config):
        """Initialize a Quarry object.

        @param owner: The owner of this business.
        """
        super().__init__(owner, date, town, config=config)


class RealtyFirm(Business):
    """A realty firm."""

    def __init__(self, owner, date, town, config):
        """Initialize an RealtyFirm object.

        @param owner: The owner of this business.
        """
        super().__init__(owner, date, town, config=config)

    @property
    def home_sales(self):
        """Return all home sales."""
        home_sales = OrderedSet()
        for employee in self.employees | self.former_employees:
            if hasattr(employee, 'home_sales'):
                home_sales |= employee.home_sales
        return home_sales


class Restaurant(Business):
    """A restaurant."""

    def __init__(self, owner, date, town, config):
        """Initialize a Restaurant object.

        @param owner: The owner of this business.
        """
        super().__init__(owner, date, town, config=config)

    def generate_name(self):
        return Names.a_restaurant_name()

class School(Business):
    """The local K-12 school."""

    def __init__(self, owner, date, town, config):
        """Initialize a School object.

        @param owner: The owner of this business.
        """
        super().__init__(owner, date, town, config=config)
        self.town.school = self

    def generate_name(self):
        return "{0} {1}".format(self.town.name, self.config.business.class_to_company_name_component[School])


class ShoemakerShop(Business):
    """A shoemaker's company."""

    def __init__(self, owner, date, town, config):
        """Initialize an ShoemakerShop object.

        @param owner: The owner of this business.
        """
        super().__init__(owner, date, town, config=config)


class Supermarket(Business):
    """A supermarket on a lot in a town."""

    def __init__(self, owner, date, town, config):
        """Initialize an Supermarket object.

        @param owner: The owner of this business.
        """
        super().__init__(owner, date, town, config=config)


class TailorShop(Business):
    """A tailor."""

    def __init__(self, owner, date, town, config):
        """Initialize a TailorShop object.

        @param owner: The owner of this business.
        """
        super().__init__(owner, date, town, config=config)


class TattooParlor(Business):
    """A tattoo parlor."""

    def __init__(self, owner, date, town, config):
        """Initialize a TattooParlor object.

        @param owner: The owner of this business.
        """
        super().__init__(owner, date, town, config=config)


class Tavern(Business):
    """A place where alcohol is served in the 19th century, maintained by a barkeeper."""

    def __init__(self, owner, date, town, config):
        """Initialize a Tavern object.

        @param owner: The owner of this business.
        """
        super().__init__(owner, date, town, config=config)


class TaxiDepot(Business):
    """A taxi depot."""

    def __init__(self, owner, date, town, config):
        """Initialize a TaxiDepot object.

        @param owner: The owner of this business.
        """
        super().__init__(owner, date, town, config=config)


class University(Business):
    """The local university."""

    def __init__(self, date, town, config):
        """Initialize a University object.

        @param owner: The owner of this business.
        """
        super().__init__(None, date, town, config=config)
        self.town.university = self

    def generate_name(self):
        return "{} College".format(self.town.name)
