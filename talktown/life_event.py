import random
from ordered_set import OrderedSet

from . import residence
from . import occupation
from .name import Name
from .person import Person
from .corpora import Names
from .residence import House
from .artifact import Gravestone

class Event:
    """A superclass that all event subclasses inherit from.

        Attributes
        ----------
        event_id: int
            Unique identifier of this event object
        date: datetime.date
            date of the event
    """
    # This gets incremented each time a new event is generated,
    # which affords a persistent ID for each person
    next_id = 0

    def __init__(self, date):
        self.event_id = Event.next_id; Event.next_id += 1
        self.date = date

    @property
    def year(self):
        return self.date.year

    @property
    def month(self):
        return self.date.month

    @property
    def day(self):
        return self.date.day

    @property
    def ordinal_date(self):
        return self.date.toordinal()

class Adoption(Event):
    """An adoption of a child by a person(s) who is/are not their biological parent.

        Note:
            Adoptions have not been fully implemented yet.

        Attributes:
            subject: Person
                Adoptee
            town:Town
                Town where the person was adopted
            adoptive_parents: Tuple[Person, Person]:
                Parents who adopted the subject
    """

    def __init__(self, adoptee, adoptive_parents, date):
        """Initialize an Adoption object"""
        super().__init__(date)
        self.adoptee = adoptee
        self.adoptive_parents = adoptive_parents

        # Add this event to everyone's life events set
        self.adoptee.life_events.add(self)
        for adoptive_parent in adoptive_parents:
            adoptive_parent.life_events.add(self)

    def __str__(self):
        """Return string representation."""
        return "Adoption of {0} by {1} in {2}".format(
            self.adoptee.name, ' and '.join(ap.name for ap in self.adoptive_parents), self.date.year)

class Birth(Event):
    """A birth of a person

        Attributes
        ----------
        biological_mother: Person
            The baby's biological mother
        biological_father: Person
            The baby's biological father
        mother: Person
            The baby's legal mother
        father: Person
            The baby's legal father2
    """

    def __init__(self, baby, mother, doctor, date):
        """Initialize a Birth object"""
        super().__init__(date)
        self.baby = baby
        self.biological_mother = mother
        self.biological_father = mother.impregnated_by
        self.mother = mother
        self.father = mother.spouse if mother.spouse and mother.spouse.male else None
        self.doctor = doctor
        self.hospital = None
        self.nurses = OrderedSet()

        # Add event to life events fot each person involved
        self.baby.life_events.add(self)
        self.biological_mother.life_events.add(self)

        if self.doctor:  # There won't be a doctor if the birth happened outside the town
            self.hospital = doctor.company
            self.nurses = OrderedSet([
                e.person for e in self.hospital.employees if isinstance(e, occupation.Nurse)
            ])

    def __str__(self):
        """Return string representation."""
        return "Birth of {} in {}".format(self.baby.name, self.date.year)

    @staticmethod
    def reset_pregnancy_attributes(mother):
        """Update attributes of the mother that are affected by this birth."""
        mother.conception_date = None
        mother.due_date = None
        mother.impregnated_by = None
        mother.pregnant = False

    @staticmethod
    def generate_baby_name(baby, config):
        """Name the baby.

        TODO: Support a child inheriting a person's middle name as their own
        first or middle name.
        """
        if baby.father is not None and baby.male:
            if not any(bro for bro in baby.brothers if bro.first_name == baby.father.first_name):
                if  random.random() < config.misc_character.chance_son_inherits_fathers_exact_name:
                    # Name the son after his father
                    baby.first_name = baby.father.first_name
                    baby.middle_name = baby.father.middle_name
                    baby.last_name = Birth._decide_last_name(baby)
                    baby.suffix = Birth.get_child_name_suffix(baby.father)
                    baby.named_for = (baby.father, baby.father)
                    return

        potential_namegivers = OrderedSet()

        if baby.male:
            potential_namegivers = Birth._get_potential_male_namegivers(baby, config)
        else:
            potential_namegivers = Birth._get_potential_female_namegivers(baby, config)

        # Make sure person doesn't end up with a sibling's name or their mother's name
        off_limits_names = OrderedSet([p.first_name for p in OrderedSet([baby.mother]) | baby.siblings])

        # Determine first name
        potential_first_name, first_name_namegiver = (
            Birth._decide_first_name(baby, potential_namegivers, config)
        )
        while potential_first_name in off_limits_names:
            potential_first_name, first_name_namegiver = (
                Birth._decide_first_name(baby, [], config)
            )
        baby.first_name = potential_first_name

        # Determine a middle name
        potential_middle_name, middle_name_namegiver = (
            Birth._decide_middle_name(baby, potential_namegivers, config)
        )
        while potential_middle_name == baby.first_name:
            potential_middle_name, middle_name_namegiver = (
                Birth._decide_middle_name(baby, [], config)
            )
        baby.middle_name = potential_middle_name


        baby.suffix = ''
        baby.named_for = (first_name_namegiver, middle_name_namegiver)
        baby.last_name = Birth._decide_last_name(baby)
        baby.maiden_name = baby.last_name

    @staticmethod
    def _decide_last_name(baby):
        """Return what will be the baby's last name."""
        if baby.mother.marriage and baby.father:
            if baby.mother.marriage.will_hyphenate_child_surnames:
                last_name = Birth._get_hyphenated_last_name(baby)
            else:
                last_name = baby.father.last_name
        else:
            last_name = baby.mother.last_name
        return last_name

    @staticmethod
    def _get_hyphenated_last_name(baby):
        """Get a hyphenated last name for the child, if the parents have decided to attribute one."""
        hyphenated_last_name = "{0}-{1}".format(
            baby.father.last_name, baby.mother.last_name
        )
        # Check if this child will be the progenitor of this hyphenated surname, i.e.,
        # whether an older sibling has already been given it
        if any(k for k in baby.mother.marriage.children_produced if k.maiden_name == hyphenated_last_name):
            older_sibling_with_hyphenated_surname = next(
                k for k in baby.mother.marriage.children_produced if k.maiden_name == hyphenated_last_name
            )
            hyphenated_surname_object = older_sibling_with_hyphenated_surname.maiden_name
        else:
            # Instantiate a new Name object with this child as the progenitor
            hyphenated_surname_object = Name(
                hyphenated_last_name, progenitor=baby, conceived_by=baby.parents,
                derived_from=(baby.mother.last_name, baby.father.last_name)
            )
        return hyphenated_surname_object

    @staticmethod
    def _decide_first_name(baby, potential_namegivers, config):
        """Return what will be the baby's first name."""
        if potential_namegivers and random.random() < config.misc_character.chance_child_inherits_first_name:
            first_name_namegiver = random.choice(potential_namegivers)
            first_name = first_name_namegiver.first_name
        else:
            first_name_namegiver = None
            if baby.male:
                first_name_rep = Names.a_masculine_name(year=baby.birth_year)
            else:
                first_name_rep = Names.a_feminine_name(year=baby.birth_year)
            first_name = Name(value=first_name_rep,
                              progenitor=baby,
                              conceived_by=baby.parents,
                              derived_from=())
        return first_name, first_name_namegiver

    @staticmethod
    def _decide_middle_name(baby, potential_namegivers, config):
        """Return what will be the baby's first name."""
        if potential_namegivers and random.random() < config.misc_character.chance_child_inherits_middle_name:
            middle_name_namegiver = random.choice(potential_namegivers)
            middle_name = middle_name_namegiver.first_name
        else:
            middle_name_namegiver = None
            if baby.male:
                middle_name_rep = Names.a_masculine_name(year=baby.birth_year)
            else:
                middle_name_rep = Names.a_feminine_name(year=baby.birth_year)
            middle_name = Name(value=middle_name_rep,
                               progenitor=baby,
                               conceived_by=baby.parents,
                               derived_from=())
        return middle_name, middle_name_namegiver

    @staticmethod
    def _get_potential_male_namegivers(baby, config):
        """Return a set of men on the father's side of the family whom the child may be named for."""
        namegivers = []
        for parent in baby.parents:
            # Add the child's legal father
            if parent.male:
                namegivers += [parent] * config.misc_character.frequency_of_naming_after_father
            # Add the child's (legal) great/grandfathers
            if parent.father:
                namegivers += [parent.father] * config.misc_character.frequency_of_naming_after_grandfather
                if parent.father.father:
                    namegivers += [parent.father.father] * config.misc_character.frequency_of_naming_after_greatgrandfather
                if parent.mother.father:
                    namegivers += [parent.mother.father] * config.misc_character.frequency_of_naming_after_greatgrandfather
            # Add a random sampling child's uncles and great uncles
            namegivers += random.sample(parent.brothers, random.randint(0, len(parent.brothers)))
            namegivers += random.sample(parent.uncles, random.randint(0, len(parent.uncles)))
        return namegivers

    @staticmethod
    def _get_potential_female_namegivers(baby, config):
        """Return a set of women on the father's side of the family whom the child may be named for."""
        namegivers = []
        for parent in baby.parents:
            # Add the child's mother
            if parent.female:
                namegivers += [parent] * config.misc_character.frequency_of_naming_after_mother
            # Add the child's (legal) great/grandmothers
            if parent.mother:
                namegivers += [parent.mother] * config.misc_character.frequency_of_naming_after_grandmother
                if parent.father is not None and parent.father.mother is not None:
                    namegivers += [parent.father.mother] * config.misc_character.frequency_of_naming_after_greatgrandmother
                if parent.mother.mother:
                    namegivers += [parent.mother.mother] * config.misc_character.frequency_of_naming_after_greatgrandmother
            # Add a random sampling child's aunts and great aunts
            namegivers += random.sample(parent.sisters, random.randint(0, len(parent.sisters)))
            namegivers += random.sample(parent.aunts, random.randint(0, len(parent.aunts)))
        return namegivers

    @staticmethod
    def get_child_name_suffix(father):
        """Return a suffix if the person shares their parent's full name, else an empty string."""

        increment_suffix = {
            '': 'II', 'II': 'III', 'III': 'IV', 'IV': 'V', 'V': 'VI',
            'VI': 'VII', 'VII': 'VIII', 'VIII': 'IX', 'IX': 'X'
        }
        if father.name_suffix in increment_suffix:
            return increment_suffix[father.name_suffix]
        return ""

    @staticmethod
    def mother_potentially_exit_workforce(mother, date, birth_event):
        """Have the mother potentially quit her job."""
        if not mother.town.get_businesses_of_type('DayCare'):
            # If there's no day care in town, have the mother quit her
            # job; TODO, model other solutions here, like the child staying
            # with a retired family member in town, etc.
            mother.occupation.terminate(reason=birth_event, date=date)
        else:
            if random.random() < mother.sim.config.life_cycle.chance_mother_of_young_children_stays_home(date.year):
                mother.occupation.terminate(reason=birth_event, date=date)

class BusinessConstruction(Event):
    """Construction of the building where a business is headquartered.

    This must be preceded by the business being founded -- the business makes the
    call to instantiate one of these objects -- where in a HouseConstruction the
    direction is opposite: a HouseConstruction object makes the call to instantiate
    a House object.

    Attributes:
        subject (person.Person): Person who is getting the business built
        architect (occupation.Architect or None): Person designing the business
        business (business.Business): Business being built
        construction_firm (business.Business): Company that built the business
        builders (OrderedSet(person.Person)): People who helped build the business
    """

    def __init__(self, subject, business, architect, date, demolition_that_preceded_this=None):
        """Initialize a BusinessConstruction object."""
        super().__init__(date)
        self.subject = subject
        self.architect = architect
        self.business = business
        self.construction_firm = None
        self.builders = OrderedSet()

        if self.architect:
            self.construction_firm = architect.company
            for employee in self.construction_firm.employees:
                if isinstance(employee, occupation.Builder):
                    self.builders.add(employee.person)

        else:
            # Build it yourself
            for p in subject.nuclear_family:
                if p.in_the_workforce:
                    self.builders.add(p)

        if demolition_that_preceded_this:
            demolition_that_preceded_this.reason = self

    def __str__(self):
        """Return string representation."""
        return "Construction of {} at {} in {}".format(
            self.business.name, self.business.address, self.date.year
        )

class BusinessClosure(Event):
    """The closure of a business.

        Attributes
        ----------
        business: Business
            Business that closed
        reason: Event
            Event that triggered closing
    """

    def __init__(self, business, date, reason=None):
        """Initialize a Demolition object."""
        super().__init__(date)
        self.business = business
        self.reason = reason

    def __str__(self):
        """Return string representation."""
        return "Closure of {} in {}".format(
            self.business.name, self.date.year
        )

class Death(Event):
    """A death of a person in the town.

    Attributes:
        town (town.Town): Town where the person died
        subject (person.Person): Person who died
        widow (person.Person): The subject's spouse
        casuse (Event): Reason for death
        mortitian (occupation.Mortitian): Motitian in the town
        cemetery (business.Cemetery): Cemetery where this person is burried
        next_of_kin (person.Person): The subject's next of kin
        cemetery_plot (int): Plot where the subject is burried in the cemetary
    """

    def __init__(self, subject, widow, mortician, cause_of_death, date):
        """Initialize a Death object."""
        super().__init__(date)
        self.subject = subject
        self.subject.death_year = self.date.year
        self.widow = widow  # Will get set by _update_attributes_of_deceased_and_spouse() if person was married
        self.cause = cause_of_death
        self.mortician = mortician
        self.cemetery = self.subject.town.cemetery
        self.next_of_kin = subject.next_of_kin
        if mortician:
            self.cemetery_plot = Death.inter_the_body(subject, self.cemetery)
        else:
            self.cemetery_plot = None

    def __str__(self):
        """Return string representation."""
        return "Death of {0} in {1}".format(
            self.subject.name, self.date.year
        )

    @staticmethod
    def update_attributes_of_deceased_and_spouse(person, death):
        person.alive = False
        if person.marriage is not None:
            widow = person.spouse
            widow.marriage.terminus = death
            widow.marriage = None
            widow.spouse = None
            widow.significant_other = None
            widow.widowed = True
            widow.grieving = True
            widow.chance_of_remarrying = person.sim.config.marriage.chance_spouse_changes_name_back(
                years_married=person.marriage.duration
            )

    @staticmethod
    def vacate_job_position_of_the_deceased(person, death):
        """Vacate the deceased's job position, if any."""
        if person.occupation:
            person.occupation.terminate(reason=death, date=death.date)

    @staticmethod
    def transfer_ownership_of_home_owned_by_the_deceased(person):
        """Transfer ownership of the deceased's home to another one of its residents."""
        person.home.former_owners.add(person)
        if any(r for r in person.home.residents if r.in_the_workforce):
            heir = next(r for r in person.home.residents if r.in_the_workforce)
            person.home.owners = OrderedSet([heir])

    @staticmethod
    def inter_the_body(person, cemetery):
        """Inter the body at the local cemetery."""
        return cemetery.inter_person(person=person)

class Demolition(Event):
    """The demolition of a house or other building."""

    def __init__(self, building, demolition_company, date, reason=None):
        """Initialize a Demolition object."""
        super().__init__(date)
        self.building = building
        self.demolition_company = demolition_company  # ConstructionFirm handling the demolition
        self.reason = reason  # May also get set by HouseConstruction or BusinessConstruction object __init__()

    @staticmethod
    def have_the_now_displaced_residents_move(house_or_apartment_unit, demolition):
        """Handle the full pipeline from them finding a place to moving into it."""
        an_owner = list(house_or_apartment_unit.owners)[0]
        home_they_will_move_into = an_owner.secure_home(demolition.date)
        if home_they_will_move_into:
            for resident in list(house_or_apartment_unit.residents):
                resident.move(new_home=home_they_will_move_into, reason=demolition)
        else:
            an_owner.depart_town(
                forced_nuclear_family=house_or_apartment_unit.residents
            )

    def __str__(self):
        """Return string representation."""
        if self.reason:
            return "Demolition of {} on behalf of {} in {}".format(
                self.building.name, self.reason.business, self.date.year
            )
        else:
            return "Demolition of {} in {}".format(
                self.building.name, self.date.year
            )

class Departure(Event):
    """A departure by which someone leaves the town (i.e., leaves the simulation)."""

    def __init__(self, subject, date):
        """Initialize a Departure object."""
        super().__init__(date)
        self.subject = subject

    @staticmethod
    def update_neighbor_attributes(person):
        """Update the neighbor attributes of the people moving and their new and former neighbors"""
        # Prepare the salience increment at play here, because attribute accessing
        # is expensive
        config = person.sim.config
        salience_change_for_former_neighbor = (
            config.salience.salience_increment_from_relationship_change['former neighbor'] -
            config.salience.salience_increment_from_relationship_change['neighbor']
        )
        # Remove the departed from all their old neighbor's .neighbors attribute...
        for old_neighbor in person.neighbors:
            old_neighbor.neighbors.remove(person)
            old_neighbor.former_neighbors.add(person)
            person.former_neighbors.add(old_neighbor)
            # ...and update the relevant salience values (because people still living in the
            # town may discuss this person)
            old_neighbor.update_salience_of(
                entity=person, change=salience_change_for_former_neighbor
            )
            person.update_salience_of(
                entity=old_neighbor, change=salience_change_for_former_neighbor
            )
        # Set the departed's .neighbors attribute to the empty set
        person.neighbors = OrderedSet()

    def __str__(self):
        """Return string representation."""
        return "Departure of {0} in {1}".format(
            self.subject.name, self.date.year)

    @staticmethod
    def vacate_job_position_of_the_departed(person, departure_event):
        """Vacate the departed's job position, if any."""
        if person.occupation:
            person.occupation.terminate(reason=departure_event, date=departure_event.date)

class Divorce(Event):
    """A divorce between two people in the town."""

    def __init__(self, subjects, lawyer, date):
        """Initialize a divorce object."""
        super().__init__(date)
        self.subjects = subjects
        self.lawyer = lawyer
        self.marriage = subjects[0].marriage
        self.law_firm = None
        if lawyer:
            self.law_firm = lawyer.company


    def __str__(self):
        """Return string representation."""
        return "Divorce of {0} and {1} in {2}".format(
            self.subjects[0].name, self.subjects[1].name, self.date.year
        )

    @staticmethod
    def update_divorcee_attributes(spouse1, spouse2, divorce_event):
        """Update divorcee attributes that pertain to marriage concerns."""
        config = spouse1.sim.config
        spouse1.marriage = None
        spouse2.marriage = None
        spouse1.spouse = None
        spouse2.spouse = None
        spouse1.significant_other = None
        spouse2.significant_other = None
        spouse1.divorces.append(divorce_event)
        spouse2.divorces.append(divorce_event)
        spouse1.immediate_family.remove(spouse2)
        spouse2.immediate_family.remove(spouse1)
        # Revert each back to their own extended families
        spouse1.extended_family = (
            spouse1.greatgrandparents | spouse1.immediate_family | spouse1.uncles | spouse1.aunts |
            spouse1.cousins | spouse1.nieces | spouse1.nephews
        )
        spouse2.extended_family = (
            spouse2.greatgrandparents | spouse2.immediate_family | spouse2.uncles | spouse2.aunts |
            spouse2.cousins | spouse2.nieces | spouse2.nephews
        )
        Divorce._have_divorcees_fall_out_of_love(divorcees=(spouse1, spouse2), config=config)
        # Update salience values
        salience_change = (
            spouse1.sim.config.salience.salience_increment_from_relationship_change['significant other'] +
            spouse1.sim.config.salience.salience_increment_from_relationship_change['immediate family']
        )
        spouse1.update_salience_of(entity=spouse2, change=-salience_change)  # Notice the minus sign
        spouse2.update_salience_of(entity=spouse1, change=-salience_change)

    @staticmethod
    def _have_divorcees_fall_out_of_love(divorcees, config):
        """Make the divorcees (probably) lose each other as their strongest love interests."""
        spouse1, spouse2 = divorcees
        if random.random() < config.marriage.chance_a_divorcee_falls_out_of_love:
            spouse1.relationships[spouse2].raw_spark = (
                config.marriage.new_raw_spark_value_for_divorcee_who_has_fallen_out_of_love
            )
            spouse1.relationships[spouse2].spark = config.social_sim.normalize_raw_spark(
                n_simulated_timesteps=spouse1.sim.n_simulated_timesteps,
                raw_spark=spouse1.relationships[spouse2].raw_spark
            )
            if spouse2 is spouse1.love_interest:
                new_love_interest = max(spouse1.relationships, key=lambda r: spouse1.relationships[r].spark)
                if spouse1.relationships[new_love_interest] > 0:
                    spouse1.love_interest = new_love_interest
                    spouse1.spark_of_love_interest = spouse1.relationships[new_love_interest].spark
        if random.random() < config.marriage.chance_a_divorcee_falls_out_of_love:
            spouse2.relationships[spouse1].raw_spark = (
                config.marriage.new_raw_spark_value_for_divorcee_who_has_fallen_out_of_love
            )
            spouse2.relationships[spouse1].spark = config.social_sim.normalize_raw_spark(
                n_simulated_timesteps=spouse2.sim.n_simulated_timesteps,
                raw_spark=spouse2.relationships[spouse1].raw_spark
            )
            if spouse1 is spouse2.love_interest:
                new_love_interest = max(spouse2.relationships, key=lambda r: spouse2.relationships[r].spark)
                if spouse2.relationships[new_love_interest] > 0:
                    spouse2.love_interest = new_love_interest
                    spouse2.spark_of_love_interest = spouse2.relationships[new_love_interest].spark

    @staticmethod
    def have_divorcees_split_up_money(spouse1, spouse2):
        """Have the divorcees split their money up (50/50)."""
        money_to_split_up = spouse1.marriage.money
        amount_given_to_each = money_to_split_up / 2
        spouse1.money = amount_given_to_each
        spouse2.money = amount_given_to_each

    @staticmethod
    def have_a_spouse_and_possibly_kids_change_name_back(spouse1, divorce_event):
        """Have a spouse and kids potentially change their names back."""
        config = spouse1.sim.config
        chance_of_a_name_reversion = config.marriage.chance_spouse_changes_name_back(
            years_married=spouse1.marriage.duration
        )
        if random.random() < chance_of_a_name_reversion:
            for name_change in spouse1.marriage.name_changes:
                name_change.subject.change_name(
                    new_last_name=name_change.old_last_name, reason=divorce_event
                )

    @staticmethod
    def decide_and_enact_new_living_arrangements(spouse1, spouse2, divorce_event):
        """Handle the full pipeline from discussion to one spouse (and possibly kids) moving out."""
        spouse_who_will_move_out = Divorce._decide_who_will_move_out(spouse1, spouse2)
        kids_who_will_move_out_also = Divorce._decide_which_kids_will_move_out(
            spouse2 if spouse_who_will_move_out is spouse1 else spouse1,
            spouse_who_will_move_out
        )
        family_members_who_will_move = OrderedSet([spouse_who_will_move_out]) | kids_who_will_move_out_also
        home_spouse_will_move_to = Divorce._decide_where_spouse_moving_out_will_live(
            spouse_who_will_move=spouse_who_will_move_out
        )

        Divorce._move_spouse_and_possibly_kids_out(
            home_spouse_will_move_to=home_spouse_will_move_to,
            family_members_who_will_move=family_members_who_will_move,
            divorce_event=divorce_event)

    @staticmethod
    def _decide_who_will_move_out(spouse1, spouse2):
        """Decide which of the divorcees will move out."""
        config = spouse1.sim.config
        if spouse1.male:
            if random.random() < config.marriage.chance_a_male_divorcee_is_one_who_moves_out:
                spouse_who_will_move_out = spouse1
            else:
                spouse_who_will_move_out = spouse2
        elif spouse2.male:
            if random.random() < config.marriage.chance_a_male_divorcee_is_one_who_moves_out:
                spouse_who_will_move_out = spouse2
            else:
                spouse_who_will_move_out = spouse2
        else:
            spouse_who_will_move_out = spouse1
        return spouse_who_will_move_out

    @staticmethod
    def _decide_which_kids_will_move_out(spouse_staying, spouse_moving):
        """Decide which kids will also be moving out, if any.

        This currently only has stepkids to the spouse who is staying move out
        along with the spouse who is moving out (who in this case would be their only
        biological parent in the marriage).
        """
        # In case of a blended family, have kids go with their own parent (these
        # will be empty sets otherwise)
        living_with_spouse_moving = spouse_moving.kids_at_home - spouse_staying.kids_at_home
        # Have any kids they had together stay in the home with that spouse
        return living_with_spouse_moving

    @staticmethod
    def _decide_where_spouse_moving_out_will_live(spouse_who_will_move):
        """Decide where the spouse who is moving out will live.

        This may require that they find a vacant lot to build a home on.
        """
        home_spouse_will_move_into = spouse_who_will_move.secure_home(spouse_who_will_move.sim.current_date)
        return home_spouse_will_move_into

    @staticmethod
    def _move_spouse_and_possibly_kids_out(home_spouse_will_move_to, family_members_who_will_move, divorce_event):
        """Move the two newlyweds (and any kids) in together.

        Note: The spouse/kids will depart the town (and thus the simulation) if they are
        unable to secure housing.
        """
        if home_spouse_will_move_to:
            for family_member in family_members_who_will_move:
                family_member.move(new_home=home_spouse_will_move_to, reason=divorce_event)
        else:
            for family_member in family_members_who_will_move:
                family_member.depart_town(divorce_event.date)

class Hiring(Event):
    """A hiring of a person by a company to serve in a specific occupational role.

    TODO: Add in data about who they beat out for the job.
    """

    def __init__(self, subject, company, occupation, date):
        """Initialize a Hiring object."""
        super().__init__(date)
        self.subject = subject
        self.company = company
        self.old_occupation = subject.occupation
        self.occupation = occupation
        self.promotion = False
        # Determine whether this was a promotion
        if self.old_occupation and self.old_occupation.company is self.company:
            self.promotion = True

    def __str__(self):
        """Return string representation."""
        return "Hiring of {} as {} at {} in {}".format(
            self.subject.name, self.occupation.__class__.__name__, self.company.name, self.date.year
        )

class HomePurchase(Event):
    """A purchase of a home by a person or couple, with the help of a realtor."""

    def __init__(self, subjects, home, realtor, date):
        """Initialize a HomePurchase object."""
        super().__init__(date)
        self.subjects = subjects
        self.home = home
        self.realtor = realtor
        self.realty_firm = None
        if realtor:
            self.realty_firm = realtor.company
            self.realtor.home_sales.add(self)

    def __str__(self):
        """Return string representation."""
        return "Purchase of {0} at {1} by {2} in {3}".format(
            "apartment" if isinstance(self.home, residence.Apartment) else "house", self.home.address,
            " and ".join(s.name for s in self.subjects), self.date.year)

    @staticmethod
    def transfer_ownership(home, new_owners):
        """Transfer ownership of this house to its new owners."""
        home.former_owners |= home.owners
        home.owners.clear()
        for p in new_owners:
            home.owners.add(p)

class HouseConstruction(Event):
    """Construction of a house."""

    def __init__(self, subjects, architect, lot, house, date, demolition_that_preceded_this=None):
        """Initialize a HouseConstruction object."""
        super().__init__(date)
        self.subjects = subjects
        self.architect = architect
        self.construction_firm = None
        self.builders = OrderedSet()
        self.house = house


        if self.architect:
            self.construction_firm = architect.company
            for employee in self.construction_firm.employees:
                if isinstance(employee, occupation.Builder):
                    self.builders.add(employee.person)

        for subject in self.subjects:
            subject.building_commissions.add(self)
        if demolition_that_preceded_this:
            demolition_that_preceded_this.reason = self

    def __str__(self):
        """Return string representation."""
        subjects_str = ', '.join(s.name for s in self.subjects)
        if self.construction_firm:
            return "Construction of house at {} by {} for {} in {}".format(
                self.house.address, self.construction_firm, subjects_str, self.date.year
            )
        else:
            return "Construction of house at {} for {} in {}".format(
                self.house.address, subjects_str, self.date.year
            )

class LayOff(Event):
    """A laying off of a person by a Business

        Attributes
        ----------
        person: Person
            Person who was laid-off
        occupation: Occupation
            Job they were laid-off from
        business: Business
            Business they were laid-off from
        reason: Event
            Reason for layoff
    """

    def __init__(self, person, occupation, business, date, reason):
        """Initialize a LayOff object."""
        super().__init__(date)
        self.person = person
        self.occupation = occupation
        self.business = business
        self.reason = reason

    def __str__(self):
        """Return string representation."""
        return "Laying off of {} as {} at {} in {}".format(
            self.person.name, self.occupation.__class__.__name__, self.business.name, self.date.year)

class Marriage(Event):
    """A marriage between two people in the town

        Attributes
        ----------
        subjects: Tuple[Person, Person]
            People getting married
        names_at_time_of_marriage: Tuple[str, str]
            Names of the people before getting married
        name_changes: List[NameChange]
            Name change events resulting form this marriage
        terminus: Event
            Event that ended the marriage
            May point to a Divorce or Death object
        money: int
            Money held collectively by couple
        children_produced: OrderedSet[Person]
            Children had by these people during their marriage

    """

    def __init__(self, subjects, date):
        """Initialize a Marriage object."""
        super().__init__(date)
        self.subjects = subjects
        self.names_at_time_of_marriage = (self.subjects[0].name, self.subjects[1].name)
        self.name_changes = []
        self.terminus = None
        self.money = None
        self.children_produced = OrderedSet()


        # self._update_newlywed_attributes()
        # self._have_newlyweds_pool_money_together()
        # self._have_one_spouse_and_possibly_stepchildren_take_the_others_name()
        self.will_hyphenate_child_surnames = self._decide_whether_children_will_get_hyphenated_names()


    def __str__(self):
        """Return string representation."""
        return "Marriage between {} and {} in {}".format(
            self.names_at_time_of_marriage[0], self.names_at_time_of_marriage[1], self.date.year)

    @property
    def duration(self):
        """Return the duration of this marriage."""
        if self.terminus:
            duration = self.terminus.year - self.date.year
        else:
            duration = self.subjects[0].sim.current_date.year - self.date.year
        return duration

    @staticmethod
    def update_newlywed_attributes(spouse1, spouse2, marriage_event):
        """Update newlywed attributes that pertain to marriage concerns."""
        spouse1.marriage = marriage_event
        spouse2.marriage = marriage_event
        spouse1.marriages.append(marriage_event)
        spouse2.marriages.append(marriage_event)
        spouse1.spouse = spouse2
        spouse2.spouse = spouse1
        spouse1.significant_other = spouse2
        spouse2.significant_other = spouse1
        spouse1.immediate_family.add(spouse2)
        spouse2.immediate_family.add(spouse1)
        spouse1.extended_family |= spouse2.extended_family  # TODO THIS IS NOT TOTALLY ACCURATE
        spouse2.extended_family |= spouse1.extended_family
        Marriage._cease_grieving_of_former_spouses((spouse1, spouse2))
        # Update salience values
        salience_change = (
            spouse1.sim.config.salience.salience_increment_from_relationship_change['significant other'] +
            spouse1.sim.config.salience.salience_increment_from_relationship_change['immediate family']
        )
        spouse1.update_salience_of(entity=spouse2, change=salience_change)
        spouse2.update_salience_of(entity=spouse1, change=salience_change)

    @staticmethod
    def _cease_grieving_of_former_spouses(newlyweds):
        """Make the newlyweds stop grieving former spouses, if applicable."""
        for newlywed in newlyweds:
            newlywed.grieving = False

    @staticmethod
    def have_newlyweds_pool_money_together(spouse1, spouse2, marriage_event):
        """Have the newlyweds combine their money holdings into a single account."""
        marriage_event.money = spouse1.money + spouse1.money
        spouse1.money = 0
        spouse2.money = 0

    @staticmethod
    def have_one_spouse_and_possibly_stepchildren_take_the_others_name(spouse1, spouse2, marriage_event):
        """Have one spouse (potentially) take the other's name.

        TODO: Have this be affected by the newlyweds' personalities."""
        config = spouse1.sim.config
        newlyweds = (spouse1, spouse2)
        if any(newlywed for newlywed in newlyweds if newlywed.female):
            spouse_who_may_take_name = next(newlywed for newlywed in newlyweds if newlywed.female)
        else:
            spouse_who_may_take_name = spouse1
        other_spouse = next(newlywed for newlywed in newlyweds if newlywed is not spouse_who_may_take_name)
        if spouse_who_may_take_name.last_name is not other_spouse.last_name:
            if random.random() < config.marriage.chance_one_newlywed_takes_others_name:
                spouse_who_may_take_name.change_name(new_last_name=other_spouse.last_name, reason=marriage_event)
        if random.random() < config.marriage.chance_stepchildren_take_stepparent_name:
            for stepchild in spouse_who_may_take_name.kids:
                if stepchild.age <= config.marriage.age_after_which_stepchildren_will_not_take_stepparent_name:
                    stepchild.change_name(new_last_name=other_spouse.last_name, reason=marriage_event)

    def _decide_whether_children_will_get_hyphenated_names(self):
        """Decide whether any children resulting from this marriage will get hyphenated names.

        TODO: Have this be affected by newlywed personalities.
        """
        if self.subjects[0].last_name != self.subjects[1].last_name:  # First, make sure they have different surnames
            config = self.subjects[0].sim.config
            if any(s for s in self.subjects if s.last_name.hyphenated):
                choice = False
            elif random.random() < config.marriage.chance_newlyweds_decide_children_will_get_hyphenated_surname:
                choice = True
            else:
                choice = False
        else:
            choice = False
        return choice

    @staticmethod
    def decide_and_enact_new_living_arrangements(spouse1, spouse2, marriage_event):
        """Handle the full pipeline from finding a place to moving into it."""
        home_they_will_move_into = Marriage._decide_where_newlyweds_will_live((spouse1, spouse2), marriage_event.date)
        # This method may spark a departure if they are not able to secure housing in town
        Marriage._move_spouses_and_any_kids_in_together(spouse1, spouse2, home_they_will_move_into, marriage_event)

    @staticmethod
    def _decide_where_newlyweds_will_live(newlyweds, date):
        """Decide where the newlyweds will live.

        This may require that they find a vacant lot to build a home on.
        """
        # If one of the newlyweds has their own place, have them move in there
        if any(s for s in newlyweds if s in s.home.owners):
            home_they_will_move_into = next(s for s in newlyweds if s in s.home.owners).home
        else:
            # If they both live at home, have them find a vacant home to move into
            # or a vacant lot to build on (it doesn't matter which person the method is
            # called for -- both will take part in the decision making)
            home_they_will_move_into = newlyweds[0].secure_home(date)
        return home_they_will_move_into

    @staticmethod
    def _move_spouses_and_any_kids_in_together(spouse1, spouse2, home_they_will_move_into, marriage_event):
        """Move the two newlyweds (and any kids) in together.

        Note: The family will depart the town (and thus the simulation) if they are
        unable to secure housing.
        """
        family_members_that_will_move = OrderedSet()
        if home_they_will_move_into is not spouse1.home:
            # Have (non-adult) children of spouse1, if any, also move too
            family_members_that_will_move.add(spouse1)
            for kid in spouse1.kids:
                if kid.present and kid.home is spouse1.home:
                    family_members_that_will_move.add(kid)
        if home_they_will_move_into is not spouse2.home:
            family_members_that_will_move.add(spouse2)
            # Have (non-adult) children of spouse2, if any, also move too
            for kid in spouse2.kids:
                if kid.present and not kid.marriage and kid.home is spouse2.home:
                    family_members_that_will_move.add(kid)
        if home_they_will_move_into:
            # Make sure both spouses are among the home's listed owners
            for spouse in (spouse1, spouse2):
                home_they_will_move_into.owners.add(spouse)
            # Move the whole family in
            for family_member in family_members_that_will_move:
                family_member.move(new_home=home_they_will_move_into, reason=marriage_event)
        else:
            # This will spark a Departure for each person in family_members_that_will_move
            spouse1.depart_town(
                forced_nuclear_family=family_members_that_will_move,
                date=marriage_event.date
            )

class Move(Event):
    """A move from one home into another, or from no home to a home."""

    def __init__(self, subjects, new_home, reason, date):
        """Initialize a Move object."""
        super().__init__(date)
        self.subjects = subjects
        self.old_home = self.subjects[0].home  # May be None if newborn or person moved from outside the town
        self.new_home = new_home
        self.reason = reason  # Will (likely) point to an Occupation object, or else a Marriage or Divorce object


    @staticmethod
    def update_mover_and_neighbor_attributes(movers, new_home):
        """Update the neighbor attributes of the people moving and their new and former neighbors"""
        # Collect relevant salience increments (because attribute accessing is expensive)
        config = movers[0].sim.config
        salience_change_for_former_neighbor = (
            config.salience.salience_increment_from_relationship_change['former neighbor'] -
            config.salience.salience_increment_from_relationship_change['neighbor']
        )
        salience_change_for_new_neighbor = (
            config.salience.salience_increment_from_relationship_change['neighbor']
        )

        # Collect all now former neighbors
        old_neighbors = OrderedSet()
        for mover in movers:
            old_neighbors |= mover.neighbors
        # Update the old neighbors' .neighbors and .former_neighbors attributes (no need
        # to update the movers' .neighbors attributes in this loop as those will be totally
        # overwritten below)
        for mover in movers:
            for this_movers_old_neighbor in mover.neighbors:
                this_movers_old_neighbor.neighbors.remove(mover)
                this_movers_old_neighbor.former_neighbors.add(mover)
                mover.former_neighbors.add(this_movers_old_neighbor)
                # Also update salience values
                this_movers_old_neighbor.update_salience_of(
                    entity=mover, change=salience_change_for_former_neighbor
                )
                mover.update_salience_of(
                    entity=this_movers_old_neighbor, change=salience_change_for_former_neighbor
                )
        # Update the movers' .neighbors attributes by...
        new_neighbors = OrderedSet()
        # ...surveying all people living on neighboring lots
        for lot in new_home.lot.neighboring_lots:
            if lot.building:
                new_neighbors |= lot.building.residents
        # ...surveying other people in the apartment complex, if new_home is an apartment unit;
        # note that we have to check whether the apartment even has units left, because this
        # method may be called for someone moving into the ApartmentComplex before it has even
        # been fully instantiated (i.e., someone hired to start working there moves into it before
        # its init() call has finished)
        if isinstance(new_home, residence.Apartment):
            neighbors_in_the_same_complex = new_home.complex.residents - movers
            new_neighbors |= neighbors_in_the_same_complex
        # Make sure none of the residents you will be moving in with were included (e.g.,
        # in the case of a baby being brought home)
        new_neighbors -= new_home.residents
        # Update the .neighbors attribute of all new neighbors, as well as salience values
        for mover in movers:
            mover.neighbors = OrderedSet(new_neighbors)
            for new_neighbor in new_neighbors:
                mover.update_salience_of(entity=new_neighbor, change=salience_change_for_new_neighbor)
                new_neighbor.neighbors.add(mover)
                new_neighbor.update_salience_of(entity=mover, change=salience_change_for_new_neighbor)

    def __str__(self):
        """Return string representation."""
        return "Move to {0} at {1} by {2} in {3}".format(
            "apartment" if isinstance(self.new_home, residence.Apartment) else "house", self.new_home.address,
            ", ".join(s.name for s in self.subjects), self.date.year
        )


class NameChange(Event):
    """A (legal) name change someone makes."""

    def __init__(self, subject, new_last_name, reason, lawyer, date):
        """Initialize a NameChange object."""
        super().__init__(date)
        self.subject = subject
        self.old_last_name = subject.last_name
        self.new_last_name = new_last_name
        self.old_name = subject.name
        self.lawyer = lawyer
        # Actually change the name
        subject.last_name = new_last_name
        self.new_name = subject.name
        self.reason = reason  # Likely will point to a Marriage or Divorce object
        if isinstance(reason, Marriage):
            reason.name_changes.append(self)
        subject.name_changes.append(self)
        if lawyer:
            self.law_firm = lawyer.company
            self.lawyer.filed_name_changes.add(self)
        else:
            self.law_firm = None

    def __str__(self):
        """Return string representation."""
        return "Name change by which {} became known as {} in {}".format(
            self.old_name, self.new_name, self.date.year
        )

class Retirement(Event):
    """A retirement by which a person ceases some occupation.

    Attributes:
        retiree: Person
            Person who retired
        occupation: Occupation
            Occupation retired from
        company: Business
            Business they retired from
    """

    def __init__(self, retiree, date):
        """Initialize a Retirement object."""
        super().__init__(date)
        self.retiree = retiree
        self.occupation = self.retiree.occupation
        self.company = self.retiree.occupation.company


    def __str__(self):
        """Return string representation."""
        return "Retirement of {} as {} at {} in {}".format(
            self.retiree.name, self.occupation.__class__.__name__, self.occupation.company.name, self.date.year)
