import random
import heapq
import collections
from ordered_set import OrderedSet
from .residence import House, Apartment
from .corpora import Names
from . import life_event
from .name import Name
from .personality import Personality
from . import occupation
from .face import Face
from .mind import Mind
from .routine import Routine
from .whereabouts import Whereabouts
from .relationship import Acquaintance
from . import face
from .utils import get_random_day_of_year
from .artifact import Gravestone


class Person:
    """A person living in a procedurally generated American small town.

        Attributes
        ----------
        sim: Simulation
            Talk of the town simulation
        id: int
            Unique person identifier
        name_tuple: NameTuple
            Components of this person's name
        birth: life_event.Birth
            Birth event associated with this character
        town: Town
            Town this person lives in
        age: int
            How old is this person
        sex: str
            This person's current sex
        in_the_workforce: bool
            Is this person eligible to work
        biological_mother: Person
            Person who gave birth to this person
        biological_father: Person
            Person who impregnated the biological mother
        mother: Person
            This person's mlegal mother
        father: Person
            This person's legal father
        tags: OrderedSet
            Arbitrary strings describing the person
        death_year: int
            Year this person died (-1 if alive)
        alive: bool
            Is this person still alive
        attracted_to: OrderedSet
            Sexes this person is attracted to
        home: Residence
            Person's home
        life_events: OrderedSet[Event]
            Events in this person's life
        whereabouts: Whereabouts
            Tracks a person's whereabouts at every timestep of their life
        named_for: Tuple[Person, Person]
            From whom first and middle name originate, respectively
    """

    # This gets incremented each time a new person is born/generated,
    # which affords a persistent ID for each person
    next_id = 0

    def __init__(self, sim, first_name, last_name, town, biological_mother, biological_father, date, **kwargs):
        """Initialize a Person object."""
        # Set location and simplay instance
        self.sim = sim
        self.id = Person.next_id; Person.next_id += 1
        self.first_name = first_name
        self.middle_name = kwargs.get("middle_name", "")
        self.last_name = last_name
        self.name_suffix = kwargs.get("name_suffix", "")
        self.maiden_name = last_name
        self.town = town
        self.age = 0
        self.sex = random.choice(["male", "female"])
        self.in_the_workforce = False
        self.birth = kwargs.get("birth", None)
        self.biological_mother = biological_mother
        self.biological_father = biological_father
        self.mother = biological_mother
        self.father = biological_mother.spouse if biological_mother else None
        self.birth_year = date.year
        self.birthday = (date.month, date.day)
        self.tags = OrderedSet([])
        self.alive = True
        self.death_year = -1
        self.gravestone = None
        self.attracted_to = Person.generate_sexuality(self.sex, sim.config)
        self.home = kwargs.get("home", None)
        self.infertile = Person.generate_fertility(self.sex, sim.config)
        self.face = Face(self)
        self.personality = Personality(self)
        self.mind = Mind(self)
        self.routine = Routine(self)
        self.whereabouts = Whereabouts(person=self)
        self.life_events = OrderedSet([])
        self.named_for = kwargs.get("named_for", (None, None))
        # Prepare familial attributes that get populated by self.init_familial_attributes()
        self.ancestors = OrderedSet()  # Biological only
        self.descendants = OrderedSet()  # Biological only
        self.immediate_family = OrderedSet()
        self.extended_family = OrderedSet()
        self.greatgrandparents = OrderedSet()
        self.grandparents = OrderedSet()
        self.aunts = OrderedSet()
        self.uncles = OrderedSet()
        self.siblings = OrderedSet()
        self.full_siblings = OrderedSet()
        self.half_siblings = OrderedSet()
        self.brothers = OrderedSet()
        self.full_brothers = OrderedSet()
        self.half_brothers = OrderedSet()
        self.sisters = OrderedSet()
        self.full_sisters = OrderedSet()
        self.half_sisters = OrderedSet()
        self.cousins = OrderedSet()
        self.kids = OrderedSet()
        self.sons = OrderedSet()
        self.daughters = OrderedSet()
        self.nephews = OrderedSet()
        self.nieces = OrderedSet()
        self.grandchildren = OrderedSet()
        self.grandsons = OrderedSet()
        self.granddaughters = OrderedSet()
        self.greatgrandchildren = OrderedSet()
        self.greatgrandsons = OrderedSet()
        self.greatgranddaughters = OrderedSet()
        self.bio_grandparents = OrderedSet()
        self.bio_siblings = OrderedSet()
        self.bio_full_siblings = OrderedSet()
        self.bio_half_siblings = OrderedSet()
        self.bio_brothers = OrderedSet()
        self.bio_full_brothers = OrderedSet()
        self.bio_half_brothers = OrderedSet()
        self.bio_sisters = OrderedSet()
        self.bio_full_sisters = OrderedSet()
        self.bio_half_sisters = OrderedSet()
        self.bio_immediate_family = OrderedSet()
        self.bio_greatgrandparents = OrderedSet()
        self.bio_uncles = OrderedSet()
        self.bio_aunts = OrderedSet()
        self.bio_cousins = OrderedSet()
        self.bio_nephews = OrderedSet()
        self.bio_nieces = OrderedSet()
        self.bio_ancestors = OrderedSet()
        self.bio_extended_family = OrderedSet()
        # Prepare attributes representing this person's romantic relationships
        self.spouse = None
        self.widowed = False
        self.relationships = dict()
        self.sexual_partners = OrderedSet()
        # Prepare attributes representing this person's social relationships
        self.acquaintances = OrderedSet()
        self.friends = OrderedSet()
        self.enemies = OrderedSet()
        self.neighbors = OrderedSet()
        self.former_neighbors = OrderedSet()
        self.coworkers = OrderedSet()
        self.former_coworkers = OrderedSet()
        self.best_friend = None
        self.worst_enemy = None
        self.love_interest = None
        self.significant_other = None
        # These get used to track changes to a person's major relationships
        self.charge_of_best_friend = 0.0
        self.charge_of_worst_enemy = 0.0
        self.spark_of_love_interest = 0.0
        self.talked_to_this_year = OrderedSet()
        self.befriended_this_year = OrderedSet()
        # Maps potentially every other person to their salience to this person
        self.salience_of_other_people = collections.defaultdict(lambda: 0.0)
        self._init_salience_values()
        # Prepare attributes pertaining to pregnancy
        self.pregnant = False
        self.impregnated_by = None
        self.conception_year = None  # Year of conception
        # Actual ordinal date 270 days from conception (currently)
        self.due_date = None
        # Prepare attributes repre senting events in this person's life
        self.adoption = None    # Person's adoption
        self.marriage = None    # Person's current marriage
        self.marriages = []     # All this person's marriages
        self.divorces = []      # All this person's divorces
        self.adoptions = []     # All the times this person adopted someone
        self.moves = []         # All this persons moves to a new home
        self.lay_offs = []      # Being laid off by a company that goes out of business
        self.name_changes = []  # All the times this person changed their name
        # Constructions of houses or buildings that they commissioned
        self.building_commissions = OrderedSet()
        self.home_purchases = []
        self.retirement = None
        self.departure = None  # Leaving the town, i.e., leaving the simulation
        self.death = None
        # Set and prepare attributes pertaining to business affairs
        self.money = self._init_money()
        self.occupation = None  # Current job
        self.occupations = []   # All jobs ever held by this person
        self.former_contractors = OrderedSet()
        self.retired = False
        # Prepare attributes pertaining to education
        self.college_graduate = False
        # Prepare attributes pertaining to dynamic emotional considerations
        self.grieving = False  # After spouse dies
        # Prepare attribute pertaining to exact location for the current timestep; this
        # will always be modified by self.go_to()
        self.location = None
        # Prepare attributes pertaining to this person's knowledge
        # Used to make batch calls to Facet.decay_strength()
        self.all_belief_facets = OrderedSet()
        self.wedding_ring_on_finger = None

    @property
    def male(self):
        """Is this person male"""
        return self.sex == "male"

    @property
    def female(self):
        """Is this person female"""
        return self.sex == "female"

    @property
    def adult(self):
        """Is this person an adult"""
        return self.age >= 18

    @property
    def attracted_to_men(self):
        """Is this person attracted to men"""
        return "male" in self.attracted_to

    @property
    def attracted_to_women(self):
        """Is this person attracted to men"""
        return "female" in self.attracted_to

    @property
    def parents(self):
        parents = OrderedSet()
        if self.mother is not None:
            parents.add(self.mother)
        if self.father is not None:
            parents.add(self.father)
        return parents

    @property
    def biological_parents(self):
        biological_parents = OrderedSet()
        if self.biological_mother is not None:
            biological_parents.add(self.biological_mother)
        if self.biological_father is not None:
            biological_parents.add(self.biological_father)
        return biological_parents

    @property
    def most_recent_life_event(self):
        """Return the most recent event in this person's life"""
        if len(self.life_events) > 0:
            return self.life_events[-1]
        else:
            return None

    @staticmethod
    def generate_fertility(sex, config):
        """Determine whether this person will be able to reproduce."""
        x = random.random()
        if sex == "male" and x < config.misc_character.male_infertility_rate:
            infertile = True
        elif sex == "female" and x < config.misc_character.female_infertility_rate:
            infertile = True
        else:
            infertile = False
        return infertile

    @staticmethod
    def generate_sexuality(sex, config):
        """Determine this person's sexuality."""
        attracted_to = OrderedSet([])
        x = random.random()
        if x < config.misc_character.homosexuality_incidence:
            # Homosexual
            if sex == "male":
                attracted_to.add("male")
            else:
                attracted_to.add("female")

        elif x < config.misc_character.homosexuality_incidence + config.misc_character.bisexuality_incidence:
            # Bisexual
            attracted_to.add("male")
            attracted_to.add("female")

        elif x < config.misc_character.homosexuality_incidence + config.misc_character.bisexuality_incidence + config.misc_character.asexuality_incidence:
            # Asexual
            attracted_to.add("male")
            attracted_to.add("female")
        else:
            # Heterosexual
            if sex == "male":
                attracted_to.add("female")
            else:
                attracted_to.add("male")
        return attracted_to

    def _init_familial_attributes(self):
        """Populate lists representing this person's family members."""
        self._init_immediate_family()
        self._init_biological_immediate_family()
        self._init_extended_family()
        self._init_biological_extended_family()

    def _init_immediate_family(self):
        """Populate lists representing this person's (legal) immediate family."""
        self.grandparents = (self.father.parents if self.father else OrderedSet()) \
            | (self.mother.parents if self.mother else OrderedSet())

        self.siblings = (self.father.kids if self.father else OrderedSet()) \
            | (self.mother.kids if self.mother else OrderedSet())

        self.full_siblings = (self.father.kids if self.father else OrderedSet()) \
            & (self.mother.kids if self.mother else OrderedSet())

        self.half_siblings = (self.father.kids if self.father else OrderedSet()) \
            ^ (self.mother.kids if self.mother else OrderedSet())

        self.brothers = (self.father.sons if self.father else OrderedSet()) \
            | (self.mother.sons if self.mother else OrderedSet())

        self.full_brothers = (self.father.sons if self.father else OrderedSet()) \
            & (self.mother.sons if self.mother else OrderedSet())

        self.half_brothers = (self.father.sons if self.father else OrderedSet()) \
            ^ (self.mother.sons if self.mother else OrderedSet())

        self.sisters = (self.father.daughters if self.father else OrderedSet()) \
            | (self.mother.daughters if self.mother else OrderedSet())

        self.full_sisters = (self.father.daughters if self.father else OrderedSet()) \
            & (self.mother.daughters if self.mother else OrderedSet())

        self.half_sisters = (self.father.daughters if self.father else OrderedSet()) \
            ^ (self.mother.daughters if self.mother else OrderedSet())

        self.immediate_family = self.grandparents | self.parents | self.siblings

    def _init_biological_immediate_family(self):
        """Populate lists representing this person's immediate."""
        self.bio_grandparents = (self.biological_father.biological_parents if self.biological_father else OrderedSet()) \
            | (self.biological_mother.biological_parents if self.biological_mother else OrderedSet())

        self.bio_siblings = (self.biological_father.kids if self.biological_father else OrderedSet()) \
            | (self.biological_mother.kids if self.biological_mother else OrderedSet())

        self.bio_full_siblings = (self.biological_father.kids if self.biological_father else OrderedSet()) \
            & (self.biological_mother.kids if self.biological_mother else OrderedSet())

        self.bio_half_siblings = (self.biological_father.kids if self.biological_father else OrderedSet()) \
            ^ (self.biological_mother.kids if self.biological_mother else OrderedSet())

        self.bio_brothers = (self.biological_father.sons if self.biological_father else OrderedSet()) \
            | (self.biological_mother.sons if self.biological_mother else OrderedSet())

        self.bio_full_brothers = (self.biological_father.sons if self.biological_father else OrderedSet()) \
            & (self.biological_mother.sons if self.biological_mother else OrderedSet())

        self.bio_half_brothers = (self.biological_father.sons if self.biological_father else OrderedSet()) \
            ^ (self.biological_mother.sons if self.biological_mother else OrderedSet())

        self.bio_sisters = (self.biological_father.daughters if self.biological_father else OrderedSet()) \
            | (self.biological_mother.daughters if self.biological_mother else OrderedSet())

        self.bio_full_sisters = (self.biological_father.daughters if self.biological_father else OrderedSet()) \
            & (self.biological_mother.daughters if self.biological_mother else OrderedSet())

        self.bio_half_sisters = (self.biological_father.daughters if self.biological_father else OrderedSet()) \
            ^ (self.biological_mother.daughters if self.biological_mother else OrderedSet())

        self.bio_immediate_family = self.bio_grandparents | self.biological_parents | self.bio_siblings

    def _init_extended_family(self):
        """Populate lists representing this person's (legal) extended family."""
        self.greatgrandparents = (self.father.grandparents if self.father else OrderedSet()) \
            | (self.mother.grandparents if self.mother else OrderedSet())

        self.uncles = (self.father.brothers if self.father else OrderedSet()) \
            | (self.mother.brothers if self.mother else OrderedSet())

        self.aunts = (self.father.sisters if self.father else OrderedSet()) \
            | (self.mother.sisters if self.mother else OrderedSet())

        self.cousins = (self.father.nieces if self.father else OrderedSet()) \
            | (self.father.nephews if self.father else OrderedSet()) \
            | (self.mother.nieces if self.mother else OrderedSet()) \
            | (self.mother.nephews if self.mother else OrderedSet())

        self.nephews = (self.father.grandsons if self.father else OrderedSet()) \
            | (self.mother.grandsons if self.mother else OrderedSet())

        self.nieces = (self.father.granddaughters if self.father else OrderedSet()) \
            | (self.mother.granddaughters if self.mother else OrderedSet())

        self.ancestors = (self.father.ancestors if self.father else OrderedSet()) \
            | (self.mother.ancestors if self.mother else OrderedSet()) \
            | self.parents

        self.extended_family = self.greatgrandparents | self.immediate_family \
            | self.uncles | self.aunts | self.cousins | self.nieces | self.nephews

    def _init_biological_extended_family(self):
        """Populate lists representing this person's (legal) extended family."""
        self.bio_greatgrandparents = (self.biological_father.bio_greatgrandparents if self.biological_father else OrderedSet()) \
            | (self.biological_mother.bio_greatgrandparents if self.biological_mother else OrderedSet())

        self.bio_uncles = (self.biological_father.bio_brothers if self.biological_father else OrderedSet()) \
            | (self.biological_mother.bio_brothers if self.biological_mother else OrderedSet())

        self.bio_aunts = (self.biological_father.bio_sisters if self.biological_father else OrderedSet()) \
            | (self.biological_mother.bio_sisters if self.biological_mother else OrderedSet())

        self.bio_cousins = (self.biological_father.bio_nieces if self.biological_father else OrderedSet()) \
            | (self.biological_father.bio_nephews if self.biological_father else OrderedSet()) \
            | (self.biological_mother.bio_nieces if self.biological_mother else OrderedSet()) \
            | (self.biological_mother.bio_nephews if self.biological_mother else OrderedSet())

        self.bio_nephews = (self.biological_father.grandsons if self.biological_father else OrderedSet()) \
            | (self.biological_mother.grandsons if self.biological_mother else OrderedSet())

        self.bio_nieces = (self.biological_father.granddaughters if self.biological_father else OrderedSet()) \
            | (self.biological_mother.granddaughters if self.biological_mother else OrderedSet())

        self.bio_ancestors = (self.biological_father.bio_ancestors if self.biological_father else OrderedSet()) \
            | (self.biological_mother.bio_ancestors if self.biological_mother else OrderedSet()) \
            | self.biological_parents

        self.bio_extended_family = self.bio_greatgrandparents | self.bio_immediate_family \
            | self.bio_uncles | self.bio_aunts | self.bio_cousins | self.bio_nieces | self.bio_nephews

    def _init_update_familial_attributes_of_family_members(self):
        """Update familial attributes of myself and family members."""
        for member in self.immediate_family:
            member.immediate_family.add(self)
            member.update_salience_of(
                entity=self, change=self.sim.config.salience.salience_increment_from_relationship_change[
                    "immediate family"]
            )
        for member in self.extended_family:
            member.extended_family.add(self)
            member.update_salience_of(
                entity=self, change=self.sim.config.salience.salience_increment_from_relationship_change[
                    "extended family"]
            )
        # Update for gender-specific familial attributes
        if self.male:
            for g in self.greatgrandparents:
                g.greatgrandsons.add(self)
            for g in self.grandparents:
                g.grandsons.add(self)
            for p in self.parents:
                p.sons.add(self)
            for u in self.uncles:
                u.nephews.add(self)
            for a in self.aunts:
                a.nephews.add(self)
            for b in self.full_brothers:
                b.full_brothers.add(self)
                b.brothers.add(self)
            for s in self.full_sisters:
                s.full_brothers.add(self)
                s.brothers.add(self)
            for b in self.half_brothers:
                b.half_brothers.add(self)
                b.brothers.add(self)
            for s in self.half_sisters:
                s.half_brothers.add(self)
                s.brothers.add(self)
        elif self.female:
            for g in self.greatgrandparents:
                g.greatgranddaughters.add(self)
            for g in self.grandparents:
                g.granddaughters.add(self)
            for p in self.parents:
                p.daughters.add(self)
            for u in self.uncles:
                u.nieces.add(self)
            for a in self.aunts:
                a.nieces.add(self)
            for b in self.full_brothers:
                b.full_sisters.add(self)
                b.sisters.add(self)
            for s in self.full_sisters:
                s.full_sisters.add(self)
                s.sisters.add(self)
            for b in self.half_brothers:
                b.half_sisters.add(self)
                b.sisters.add(self)
            for s in self.half_sisters:
                s.half_sisters.add(self)
                s.sisters.add(self)
        # Update for non-gender-specific familial attributes
        for a in self.ancestors:
            a.descendants.add(self)
        for g in self.greatgrandparents:
            g.greatgrandchildren.add(self)
        for g in self.grandparents:
            g.grandchildren.add(self)
        for p in self.parents:
            p.kids.add(self)
        for fs in self.full_siblings:
            fs.siblings.add(self)
            fs.full_siblings.add(self)
        for hs in self.half_siblings:
            hs.siblings.add(self)
            hs.half_siblings.add(self)
        for c in self.cousins:
            c.cousins.add(self)
        for p in self.parents:
            p.kids.add(self)

    def _init_salience_values(self):
        """Determine an initial salience value for every other person associated with this newborn."""
        for person in self.ancestors:
            self.update_salience_of(
                entity=person, change=self.sim.config.salience.salience_increment_from_relationship_change[
                    "ancestor"]
            )
        for person in self.extended_family:
            self.update_salience_of(
                entity=person, change=self.sim.config.salience.salience_increment_from_relationship_change[
                    "extended family"]
            )
        for person in self.immediate_family:
            self.update_salience_of(
                entity=person, change=self.sim.config.salience.salience_increment_from_relationship_change[
                    "immediate family"]
            )
        self.update_salience_of(
            entity=self, change=self.sim.config.salience.salience_increment_from_relationship_change[
                "self"]
        )

    def _init_money(self):
        """Determine how much money this person has to start with."""
        return 0

    @property
    def subject_pronoun(self):
        """Return the appropriately gendered third-person singular subject pronoun."""
        return 'he' if self.male else 'she'

    @property
    def object_pronoun(self):
        """Return the appropriately gendered third-person singular object pronoun."""
        return 'him' if self.male else 'her'

    @property
    def possessive_pronoun(self):
        """Return appropriately gendered possessive subject_pronoun."""
        return 'his' if self.male else 'her'

    @property
    def reflexive_pronoun(self):
        """Return appropriately gendered reflexive subject_pronoun."""
        return 'himself' if self.male else 'herself'

    @property
    def honorific(self):
        """Return the correct honorific (e.g., 'Mr.') for this person."""
        if self.male:
            return 'Mr.'
        elif self.female:
            if self.spouse:
                return 'Mrs.'
            else:
                return 'Ms.'

    @property
    def full_name(self):
        """Return a person's full name."""
        if self.name_suffix != "":
            full_name = "{0} {1} {2} {3}".format(
                self.first_name, self.middle_name, self.last_name, self.name_suffix
            )
        else:
            full_name = "{0} {1} {2}".format(
                self.first_name, self.middle_name, self.last_name
            )
        return full_name

    @property
    def full_name_without_suffix(self):
        """Return a person's full name sans suffix.

        This is used to determine whether a child has the same full name as their parent,
        which would necessitate them getting a suffix of their own to disambiguate.
        """
        full_name = "{0} {1} {2}".format(
            self.first_name, self.middle_name, self.last_name
        )
        return full_name

    @property
    def name(self):
        """Return a person's name."""
        if self.name_suffix != "":
            name = "{0} {1} {2}".format(
                self.first_name, self.last_name, self.name_suffix)
        else:
            name = "{0} {1}".format(self.first_name, self.last_name)
        return name

    @property
    def dead(self):
        """Return whether this person is dead."""
        if not self.alive:
            return True
        else:
            return False

    @property
    def queer(self):
        """Return whether this person is not heterosexual."""
        if self.male and self.attracted_to_men:
            queer = True
        elif self.female and self.attracted_to_women:
            queer = True
        elif not self.attracted_to_men and not self.attracted_to_women:
            queer = True
        else:
            queer = False
        return queer

    @property
    def present(self):
        """Return whether the person is alive and in the town."""
        if self.alive and self.departure is None:
            return True
        else:
            return False

    @property
    def next_of_kin(self):
        """Return next of kin.

        A person's next of kin will make decisions about their estate and
        so forth upon the person's eeath.
        """
        if self.spouse and self.spouse.present:
            next_of_kin = self.spouse
        elif self.mother and self.mother.present:
            next_of_kin = self.mother
        elif self.father and self.father.present:
            next_of_kin = self.father
        elif any(k for k in self.kids if k.adult and k.present):
            next_of_kin = next(k for k in self.kids if k.adult and k.present)
        elif any(f for f in self.siblings if f.adult and f.present):
            next_of_kin = next(
                f for f in self.siblings if f.adult and f.present)
        elif any(f for f in self.extended_family if f.adult and f.present):
            next_of_kin = next(
                f for f in self.extended_family if f.adult and f.present)
        elif any(f for f in self.friends if f.adult and f.present):
            next_of_kin = next(
                f for f in self.friends if f.adult and f.present)
        else:
            next_of_kin = random.choice(
                [r for r in self.town.residents if r.adult and r.present]
            )
        return next_of_kin

    @property
    def nuclear_family(self):
        """Return this person's nuclear family."""
        nuclear_family = OrderedSet([self])
        if self.spouse and self.spouse.present:
            nuclear_family.add(self.spouse)
        for kid in self.spouse.kids & self.kids if self.spouse else self.kids:
            if kid.home is self.home and kid.present:
                nuclear_family.add(kid)
        return nuclear_family

    @property
    def kids_at_home(self):
        """Return kids of this person that live with them, if any."""
        kids_at_home = OrderedSet(
            [k for k in self.kids if k.home is self.home and k.present])
        return kids_at_home

    @property
    def year_i_moved_here(self):
        """Return the year this person moved to this town."""
        return self.moves[0].year

    @property
    def years_i_lived_here(self):
        """Return the number of years this person has lived in this town"""
        return self.sim.current_date.year - self.year_i_moved_here

    @property
    def age_and_gender_description(self):
        """Return a string broadly capturing this person's age."""
        if self.age < 1:
            return 'an infant boy' if self.male else 'an infant girl'
        elif self.age < 4:
            return 'a boy toddler' if self.male else 'a girl toddler'
        elif self.age < 10:
            return 'a young boy' if self.male else 'a young girl'
        elif self.age < 13:
            return 'a preteen boy' if self.male else 'a preteen girl'
        elif self.age < 20:
            return 'a teenage boy' if self.male else 'a teenage girl'
        elif self.age < 25:
            return 'a young man' if self.male else 'a young woman'
        elif self.age < 45:
            return 'a man' if self.male else 'a woman'
        elif self.age < 65:
            return 'a middle-aged man' if self.male else 'a middle-aged woman'
        elif self.age < 75:
            return 'an older man' if self.male else 'an older woman'
        else:
            return 'an elderly man' if self.male else 'an elderly woman'

    @property
    def basic_appearance_description(self):
        """Return a string broadly capturing this person's basic appearance."""
        features = []
        if self.face.distinctive_features.tattoo == 'yes':
            features.append('a prominent tattoo')
        if self.face.distinctive_features.scar == 'yes':
            features.append('a visible scar')
        if self.face.distinctive_features.birthmark == 'yes':
            features.append('a noticeable birthmark')
        if self.face.distinctive_features.freckles == 'yes':
            features.append('freckles')
        if self.face.distinctive_features.glasses == 'yes':
            features.append('glasses')
        if self.face.hair.length == 'bald':
            features.append('a bald head')
        else:
            features.append('{} {} hair'.format(
                'medium-length' if self.face.hair.length == 'medium' else self.face.hair.length,
                'blond' if self.male and self.face.hair.color == 'blonde' else self.face.hair.color
            )
            )
        if self.face.facial_hair.style == 'sideburns' and self.male and self.age > 14:
            features.append('sideburns')
        elif self.face.facial_hair.style != 'none' and self.male and self.age > 14:
            features.append('a {}'.format(str(self.face.facial_hair.style)))
        if len(features) > 2:
            return '{}, and {}'.format(', '.join(feature for feature in features[:-1]), features[-1])
        else:
            return ' and '.join(features)

    @property
    def description(self):
        """Return a basic description of this person."""
        broader_skin_color = {
            'black': 'dark', 'brown': 'dark',
            'beige': 'light', 'pink': 'light',
            'white': 'light'
        }
        # Cut off the article ('a' or 'an') at the beginning of the
        # age_and_gender_description so that we can prepend a
        # skin-color tidbit
        age_and_gender_description = ' '.join(
            self.age_and_gender_description.split()[1:])
        return "a {broad_skin_color}-skinned {age_and_gender} with {prominent_features}{deceased}".format(
            broad_skin_color=broader_skin_color[self.face.skin.color],
            age_and_gender=age_and_gender_description,
            prominent_features=self.basic_appearance_description,
            deceased=' (deceased)' if self.dead else ''
        )

    @property
    def boss(self):
        """Return this person's boss, if they have one, else None."""
        if not self.occupation:
            return None
        elif self.occupation.company.owner and self.occupation.company.owner.person is self:
            return None
        elif self.occupation.company.owner:
            return self.occupation.company.owner.person
        else:
            return None

    @property
    def first_home(self):
        return self.moves[0].new_home

    @property
    def requited_love_interest(self):
        """Return whether this person is their love interest's love interest."""
        return self.love_interest and self.love_interest.love_interest and self.love_interest.love_interest is self

    @property
    def unrequited_love_interest(self):
        """Return whether this person is not their love interest's love interest."""
        return self.love_interest and self.love_interest.love_interest is not self

    @property
    def is_captivated_by(self):
        """The set of people that this person is romantically captivated by."""
        spark_threshold_for_being_captivated = self.sim.config.story_recognition.spark_threshold_for_being_captivated
        return [p for p in self.relationships if self.relationships[p].spark > spark_threshold_for_being_captivated]

    def recount_life_history(self):
        """Print out the major life events in this person's simulated life."""
        for life_event in self.life_events:
            print(life_event)

    def _common_familial_relation_to_me(self, person):
        """Return the immediate common familial relation to the given person, if any.

        This method gets called by decision-making methods that get executed often,
        since it runs much more quickly than known_relation_to_me, which itself is much
        richer in the number of relations it checks for. Basically, this method
        is meant for quick decision making, and known_relation_to_me for dialogue generation.
        """
        if person is self.spouse:
            return 'husband' if person.male else 'wife'
        if person is self.father:
            return 'father'
        elif person is self.mother:
            return 'mother'
        elif person in self.brothers:
            return 'brother'
        elif person in self.sisters:
            return 'sister'
        elif person in self.aunts:
            return 'aunt'
        elif person in self.uncles:
            return 'uncle'
        elif person in self.sons:
            return 'son'
        elif person in self.daughters:
            return 'daughter'
        elif person in self.cousins:
            return 'cousin'
        elif person in self.nephews:
            return 'nephew'
        elif person in self.nieces:
            return 'niece'
        elif person in self.greatgrandparents:
            return 'greatgrandfather' if person.male else 'greatgrandmother'
        elif person in self.grandparents:
            return 'grandfather' if person.male else 'grandmother'
        elif person in self.grandchildren:
            return 'grandson' if person.male else 'granddaughter'
        else:
            return None

    def relation_to_me(self, person):
        """Return the primary relation of another person to me, if any.

        This method is much richer than _common_familial_relation_to_me
        in the number of relationships that it checks for. While the former is meant
        for quick character decision making, this method should be used for things
        like dialogue generation, where performance is much less important than
        richness and expressivity. Because this method is meant to be used to generate
        dialogue, it won't return specific relationships like 'first cousin, once removed',
        because everyday people don't know or reference these relationships.
        """
        if person is self:
            return 'self'
        elif person in self.greatgrandparents:
            return 'greatgrandfather' if person.male else 'greatgrandmother'
        elif person in self.grandparents:
            return 'grandfather' if person.male else 'grandmother'
        elif person is self.father:
            return 'father'
        elif person is self.mother:
            return 'mother'
        elif person in self.aunts:
            return 'aunt'
        elif person in self.uncles:
            return 'uncle'
        elif person in self.brothers:
            return 'brother'
        elif person in self.sisters:
            return 'sister'
        elif person in self.cousins:
            return 'cousin'
        elif person in self.sons:
            return 'son'
        elif person in self.daughters:
            return 'daughter'
        elif person in self.nephews:
            return 'nephew'
        elif person in self.nieces:
            return 'niece'
        elif person is self.spouse:
            return 'husband' if person.male else 'wife'
        elif self.divorces and any(d for d in self.divorces if person in d.subjects):
            return 'ex-husband' if person.male else 'ex-wife'
        elif self.widowed and any(m for m in self.marriages if person in m.subjects and m.terminus is person.death):
            return 'deceased husband' if person.male else 'deceased wife'
        elif person.spouse in self.siblings or self.spouse in person.siblings:
            return 'brother in law' if person.male else 'sister in law'
        elif self.father and any(d for d in self.father.divorces if person in d.subjects):
            return "father's ex-{}".format('husband' if person.male else 'wife')
        elif self.mother and any(d for d in self.mother.divorces if person in d.subjects):
            return "mother's ex-{}".format('husband' if person.male else 'wife')
        elif any(s for s in self.brothers if any(d for d in s.divorces if person in d.subjects)):
            return "brother's ex-{}".format('husband' if person.male else 'wife')
        elif any(s for s in self.sisters if any(d for d in s.divorces if person in d.subjects)):
            return "sister's ex-{}".format('husband' if person.male else 'wife')
        elif any(s for s in self.brothers if any(
                m for m in s.marriages if person in m.subjects and m.terminus is person.death)):
            return "brother's deceased {}".format('husband' if person.male else 'wife')
        elif any(s for s in self.sisters if any(
                m for m in s.marriages if person in m.subjects and m.terminus is person.death)):
            return "sister's deceased {}".format('husband' if person.male else 'wife')
        elif any(s for s in self.brothers if any(
                m for m in s.marriages if person in m.subjects and m.terminus is s.death)):
            return "deceased brother's former {}".format('husband' if person.male else 'wife')
        elif any(s for s in self.sisters if any(
                m for m in s.marriages if person in m.subjects and m.terminus is s.death)):
            return "deceased sister's former {}".format('husband' if person.male else 'wife')
        elif person.spouse in self.kids:
            return 'son in law' if person.male else 'daughter in law'
        elif self.spouse and person in self.spouse.parents:
            return 'father in law' if person.male else 'mother in law'
        elif self.spouse and person in self.spouse.sons:
            return 'stepson'
        elif self.spouse and person in self.spouse.daughters:
            return 'stepdaughter'
        elif self.mother and person is self.mother.spouse:
            return 'stepfather' if person.male else 'stepmother'
        elif self.father and person is self.father.spouse:
            return 'stepfather' if person.male else 'stepmother'
        elif self.greatgrandparents & person.greatgrandparents:
            return 'second cousin'
        elif self.greatgrandparents & person.siblings:
            return 'great uncle' if person.male else 'great aunt'
        elif person is self.best_friend:
            return 'best friend'
        elif person is self.worst_enemy:
            return 'worst enemy'
        elif person is self.significant_other:
            return 'boyfriend' if person.male else 'girlfriend'
        # elif person is self.love_interest:  # Commented out because no one would say this
        #     return 'love interest'
        elif person in self.coworkers:
            return 'coworker'
        elif person in self.neighbors:
            return 'neighbor'
        elif person in self.enemies:
            return 'enemy'
        elif any(p for p in self.parents if person is p.significant_other):
            p = next(p for p in self.parents if person is p.significant_other)
            return "{}'s {}".format(
                'father' if p.male else 'mother', 'boyfriend' if person.male else 'girlfriend'
            )
        elif any(k for k in self.kids if person is k.significant_other):
            k = next(k for k in self.kids if person is k.significant_other)
            return "{}'s {}".format(
                'son' if k.male else 'daughter', 'boyfriend' if person.male else 'girlfriend'
            )
        elif any(s for s in self.siblings if person is s.significant_other):
            s = next(s for s in self.siblings if person is s.significant_other)
            return "{}'s {}".format(
                'brother' if s.male else 'sister', 'boyfriend' if person.male else 'girlfriend'
            )
        elif self.spouse and person is self.spouse.best_friend:
            return "{}'s best friend".format('husband' if self.spouse.male else 'wife')
        elif self.mother and person is self.mother.best_friend:
            return "mother's best friend"
        elif self.father and person is self.father.best_friend:
            return "father's best friend"
        elif any(s for s in self.siblings if person is s.best_friend):
            s = next(s for s in self.siblings if person is s.best_friend)
            return "{}'s best friend".format('brother' if s.male else 'sister')
        elif any(k for k in self.kids if person is k.best_friend):
            k = next(k for k in self.kids if person is k.best_friend)
            return "{}'s best friend".format('son' if k.male else 'daughter')
        elif self.spouse and person in self.spouse.coworkers:
            return "{}'s coworker".format('husband' if self.spouse.male else 'wife')
        elif self.mother and person in self.mother.coworkers:
            return "mother's coworker"
        elif self.father and person in self.father.coworkers:
            return "father's coworker"
        elif person in self.friends:
            return 'friend'
        elif self.spouse and person in self.spouse.friends:
            return "{}'s friend".format('husband' if self.spouse.male else 'wife')
        elif self.mother and person in self.mother.friends:
            return "mother's friend"
        elif self.father and person in self.father.friends:
            return "father's friend"
        elif any(k for k in self.kids if person in k.friends):
            k = next(k for k in self.kids if person in k.friends)
            return "{}'s friend".format('son' if k.male else 'daughter')
        elif any(s for s in self.siblings if person in s.friends):
            s = next(s for s in self.siblings if person in s.friends)
            return "{}'s friend".format('brother' if s.male else 'sister')
        elif person in self.acquaintances:
            return 'acquaintance'
        else:
            return None

    def known_relation_to_me(self, person):
        """Return the primary relations of another person to me that are grounded in my knowledge, if any,
        as well as the hinge in our relationship, if any.

        An example of a hinge: if someone is my wife's friend, then my wife is the hinge.
        """
        # TODO ADD FURTHER PRECONDITIONS ON SOME, E.G., YOU MUST KNOW WHERE YOUR MOM WORKS
        relations = []
        if person is self:
            relation = 'self'
            hinge = None
            relations.append((relation, hinge))
        if person in self.greatgrandparents:
            relation = 'greatgrandfather' if person.male else 'greatgrandmother'
            hinge = None
            relations.append((relation, hinge))
        if person in self.grandparents:
            relation = 'grandfather' if person.male else 'grandmother'
            hinge = None
            relations.append((relation, hinge))
        if person is self.father:
            relation = 'father'
            hinge = None
            relations.append((relation, hinge))
        if person is self.mother:
            relation = 'mother'
            hinge = None
            relations.append((relation, hinge))
        if person in self.aunts:
            relation = 'aunt'
            hinge = None
            relations.append((relation, hinge))
        if person in self.uncles:
            relation = 'uncle'
            hinge = None
            relations.append((relation, hinge))
        if person in self.brothers:
            relation = 'brother'
            hinge = None
            relations.append((relation, hinge))
        if person in self.sisters:
            relation = 'sister'
            hinge = None
            relations.append((relation, hinge))
        if person in self.cousins:
            relation = 'cousin'
            hinge = None
            relations.append((relation, hinge))
        if person in self.sons:
            relation = 'son'
            hinge = None
            relations.append((relation, hinge))
        if person in self.daughters:
            relation = 'daughter'
            hinge = None
            relations.append((relation, hinge))
        if person in self.nephews:
            relation = 'nephew'
            hinge = None
            relations.append((relation, hinge))
        if person in self.nieces:
            relation = 'niece'
            hinge = None
            relations.append((relation, hinge))
        if person is self.spouse:
            relation = 'husband' if person.male else 'wife'
            hinge = None
            relations.append((relation, hinge))
        if self.divorces and any(d for d in self.divorces if person in d.subjects):
            relation = 'ex-husband' if person.male else 'ex-wife'
            hinge = None
            relations.append((relation, hinge))
        if self.widowed and any(m for m in self.marriages if person in m.subjects and m.terminus is person.death):
            relation = 'deceased husband' if person.male else 'deceased wife'
            hinge = None
            relations.append((relation, hinge))
        if person.spouse in self.siblings:
            relation = "{}'s {}".format(
                'sister' if person.spouse.female else 'brother', 'husband' if person.male else 'wife'
            )
            hinge = person.spouse
            relations.append((relation, hinge))
        if self.spouse in person.siblings:
            relation = "{}'s {}".format(
                'husband' if self.spouse.male else 'wife', 'brother' if person.male else 'sister'
            )
            hinge = self.spouse
            relations.append((relation, hinge))
        if self.father and any(d for d in self.father.divorces if person in d.subjects):
            relation = "father's ex-{}".format(
                'husband' if person.male else 'wife')
            hinge = self.father
            relations.append((relation, hinge))
        if self.mother and any(d for d in self.mother.divorces if person in d.subjects):
            relation = "mother's ex-{}".format(
                'husband' if person.male else 'wife')
            hinge = self.mother
            relations.append((relation, hinge))
        if any(s for s in self.brothers if any(d for d in s.divorces if person in d.subjects)):
            relation = "brother's ex-{}".format(
                'husband' if person.male else 'wife')
            hinge = next(
                s for s in self.brothers if any(d for d in s.divorces if person in d.subjects)
            )
            relations.append((relation, hinge))
        if any(s for s in self.sisters if any(d for d in s.divorces if person in d.subjects)):
            relation = "sister's ex-{}".format(
                'husband' if person.male else 'wife')
            hinge = next(
                s for s in self.sisters if any(d for d in s.divorces if person in d.subjects)
            )
            relations.append((relation, hinge))
        if any(s for s in self.brothers if any(
                m for m in s.marriages if person in m.subjects and m.terminus is person.death and
                person is not s)):
            relation = "brother's deceased {}".format(
                'husband' if person.male else 'wife')
            hinge = next(
                s for s in self.brothers if any(
                    m for m in s.marriages if person in m.subjects and m.terminus is person.death)
            )
            relations.append((relation, hinge))
        if any(s for s in self.sisters if any(
                m for m in s.marriages if person in m.subjects and m.terminus is person.death and
                person is not s)):
            relation = "sister's deceased {}".format(
                'husband' if person.male else 'wife')
            hinge = next(
                s for s in self.sisters if any(
                    m for m in s.marriages if person in m.subjects and m.terminus is person.death)
            )
            relations.append((relation, hinge))
        if any(s for s in self.brothers if any(
                m for m in s.marriages if person in m.subjects and m.terminus is s.death and
                person is not s)):
            relation = "deceased brother's former {}".format(
                'husband' if person.male else 'wife')
            hinge = next(
                s for s in self.brothers if any(
                    m for m in s.marriages if person in m.subjects and m.terminus is s.death)
            )
            relations.append((relation, hinge))
        if any(s for s in self.sisters if any(
                m for m in s.marriages if person in m.subjects and m.terminus is s.death and
                person is not s)):
            relation = "deceased sister's former {}".format(
                'husband' if person.male else 'wife')
            hinge = next(
                s for s in self.sisters if any(
                    m for m in s.marriages if person in m.subjects and m.terminus is s.death)
            )
            relations.append((relation, hinge))
        if person.spouse in self.kids:
            relation = "{}'s {}".format(
                "son" if person.spouse.male else "daughter", "husband" if person.male else "wife"
            )
            hinge = person.spouse
            relations.append((relation, hinge))
        if self.spouse and person in self.spouse.parents:
            relation = "{}'s {}".format(
                "husband" if self.spouse.male else "wife", "father" if person.male else "mother"
            )
            hinge = self.spouse
            relations.append((relation, hinge))
        if self.spouse and person in self.spouse.sons and person not in self.sons:
            relation = 'stepson'
            hinge = None
            relations.append((relation, hinge))
        if self.spouse and person in self.spouse.daughters and person not in self.daughters:
            relation = 'stepdaughter'
            hinge = None
            relations.append((relation, hinge))
        if self.mother and person is self.mother.spouse and person is not self.father:
            relation = 'stepfather' if person.male else 'stepmother'
            hinge = None
            relations.append((relation, hinge))
        if self.father and person is self.father.spouse and person is not self.mother:
            relation = 'stepfather' if person.male else 'stepmother'
            hinge = None
            relations.append((relation, hinge))
        if self.greatgrandparents & person.greatgrandparents and person not in self.siblings | self.cousins | OrderedSet([self]):
            relation = 'second cousin'
            hinge = None
            relations.append((relation, hinge))
        if self.greatgrandparents & person.siblings:
            relation = 'great uncle' if person.male else 'great aunt'
            hinge = None
            relations.append((relation, hinge))
        if person is self.best_friend:
            relation = 'best friend'
            hinge = None
            relations.append((relation, hinge))
        if person is self.worst_enemy:
            relation = 'worst enemy'
            hinge = None
            relations.append((relation, hinge))
        if person is self.significant_other and person is not self.spouse:
            relation = 'boyfriend' if person.male else 'girlfriend'
            hinge = None
            relations.append((relation, hinge))
        if person is self.love_interest:
            relation = 'love interest'
            hinge = None
            relations.append((relation, hinge))
        if person in self.coworkers:
            relation = 'coworker'
            hinge = None
            relations.append((relation, hinge))
        if person in self.former_coworkers:
            relation = 'former coworker'
            hinge = None
            relations.append((relation, hinge))
        if person in self.neighbors:
            relation = 'neighbor'
            hinge = None
            relations.append((relation, hinge))
        if person in self.former_neighbors:
            relation = 'former neighbor'
            hinge = None
            relations.append((relation, hinge))
        if person in self.former_contractors:
            relation = 'former contractor'
            hinge = None
            relations.append((relation, hinge))
        if person in self.enemies:
            relation = 'enemy'
            hinge = None
            relations.append((relation, hinge))
        if any(p for p in self.parents if person is p.significant_other and person is not p.spouse):
            p = next(p for p in self.parents if person is p.significant_other)
            relation = "{}'s {}".format(
                'father' if p.male else 'mother', 'boyfriend' if person.male else 'girlfriend'
            )
            hinge = p
            relations.append((relation, hinge))
        if any(k for k in self.kids if person is k.significant_other and person is not k.spouse):
            k = next(k for k in self.kids if person is k.significant_other)
            relation = "{}'s {}".format(
                'son' if k.male else 'daughter', 'boyfriend' if person.male else 'girlfriend'
            )
            hinge = k
            relations.append((relation, hinge))
        if any(s for s in self.siblings if person is s.significant_other and person is not s.spouse):
            s = next(s for s in self.siblings if person is s.significant_other)
            relation = "{}'s {}".format(
                'brother' if s.male else 'sister', 'boyfriend' if person.male else 'girlfriend'
            )
            hinge = s
            relations.append((relation, hinge))
        if self.spouse and person is self.spouse.best_friend:
            relation = "{}'s best friend".format(
                'husband' if self.spouse.male else 'wife')
            hinge = self.spouse
            relations.append((relation, hinge))
        if self.mother and person is self.mother.best_friend:
            relation = "mother's best friend"
            hinge = self.mother
            relations.append((relation, hinge))
        if self.father and person is self.father.best_friend:
            relation = "father's best friend"
            hinge = self.father
            relations.append((relation, hinge))
        if any(s for s in self.siblings if person is s.best_friend):
            s = next(s for s in self.siblings if person is s.best_friend)
            relation = "{}'s best friend".format(
                'brother' if s.male else 'sister')
            hinge = s
            relations.append((relation, hinge))
        if any(k for k in self.kids if person is k.best_friend):
            k = next(k for k in self.kids if person is k.best_friend)
            relation = "{}'s best friend".format(
                'son' if k.male else 'daughter')
            hinge = k
            relations.append((relation, hinge))
        if self.spouse and person in self.spouse.coworkers:
            relation = "{}'s coworker".format(
                'husband' if self.spouse.male else 'wife')
            hinge = self.spouse
            relations.append((relation, hinge))
        if self.mother and person in self.mother.coworkers:
            relation = "mother's coworker"
            hinge = self.mother
            relations.append((relation, hinge))
        if self.father and person in self.father.coworkers:
            relation = "father's coworker"
            hinge = self.father
            relations.append((relation, hinge))
        if person in self.friends:
            relation = 'friend'
            hinge = None
            relations.append((relation, hinge))
        if self.spouse and person in self.spouse.friends:
            relation = "{}'s friend".format(
                'husband' if self.spouse.male else 'wife')
            hinge = self.spouse
            relations.append((relation, hinge))
        if self.mother and person in self.mother.friends:
            relation = "mother's friend"
            hinge = self.mother
            relations.append((relation, hinge))
        if self.father and person in self.father.friends:
            relation = "father's friend"
            hinge = self.father
            relations.append((relation, hinge))
        if any(k for k in self.kids if person in k.friends):
            k = next(k for k in self.kids if person in k.friends)
            relation = "{}'s friend".format('son' if k.male else 'daughter')
            hinge = k
            relations.append((relation, hinge))
        if any(s for s in self.siblings if person in s.friends):
            s = next(s for s in self.siblings if person in s.friends)
            relation = "{}'s friend".format('brother' if s.male else 'sister')
            hinge = s
            relations.append((relation, hinge))
        if person in self.acquaintances:
            relation = 'acquaintance'
            hinge = None
            relations.append((relation, hinge))
        # Throw out any for which hinge in not in my mental model
        keepers = []
        for relation, hinge in relations:
            if not hinge or hinge in self.mind.mental_models:
                keepers.append((relation, hinge))
        return keepers

    def change_name(self, new_last_name, reason, date=None):
        """Change this person's (official) name."""
        lawyer = self.contract_person_of_certain_occupation(
            occupation_in_question=occupation.Lawyer)

        if date is None:
            date = get_random_day_of_year(self.sim.current_date.year)

        life_event.NameChange(subject=self,
                              new_last_name=new_last_name,
                              reason=reason,
                              lawyer=lawyer,
                              date=date)

    def have_sex(self, partner, protection, date=None):
        """Have sex with partner."""
        # TODO model social aspects surrounding sex, etc., beyond mere conception mechanism
        if date is None:
            date = self.sim.current_date

        self.sexual_partners.add(partner)
        partner.sexual_partners.add(self)
        if self != partner.male and not self.pregnant and not partner.pregnant:
            if (not protection) or random.random() < self.sim.config.life_cycle.chance_sexual_protection_does_not_work:
                self._determine_whether_pregnant(partner, date)

    def _determine_whether_pregnant(self, partner, date):
        """Determine whether self or partner is now pregnant."""
        # Determine whether child is conceived
        female_partner = self if self.female else partner
        chance_of_conception = self.sim.config.life_cycle.chance_of_conception(
            female_age=female_partner.age
        )
        if random.random() < chance_of_conception:
            female_partner.impregnated_by = self if female_partner is partner else partner
            female_partner.conception_year = date.year
            female_partner.due_date = date.toordinal() + 270
            female_partner.pregnant = True

    def marry(self, partner, date=None):
        """Marry partner."""
        assert(self.present and not self.spouse and partner.present and not partner.spouse), (
            "{0} tried to marry {1}, but one of them is dead, departed, or married.".format(
                self.name, partner.name)
        )

        if date is None:
            get_random_day_of_year(year=self.sim.current_date.year)

        if self.present and partner.present:
            marriage_event = life_event.Marriage(subjects=(self, partner), date=date)

            self.marriage = marriage_event
            self.life_events.add(marriage_event)

            partner.marriage = marriage_event
            partner.life_events.add(marriage_event)

            life_event.Marriage.update_newlywed_attributes(self, partner, marriage_event)
            life_event.Marriage.have_newlyweds_pool_money_together(self, partner, marriage_event)
            life_event.Marriage.have_one_spouse_and_possibly_stepchildren_take_the_others_name(self, partner, marriage_event)

            if self.town:
                life_event.Marriage.decide_and_enact_new_living_arrangements(self, partner, marriage_event)
            # If they're not in the town yet (marriage between two PersonsExNihilo during
            # world generation), living arrangements will be made once they move into it

            self.sim.register_event(marriage_event)

    def divorce(self, partner, date):
        """Divorce partner."""
        assert(
            self.alive and partner.alive), "{0} tried to divorce {1}, but one of them is dead."
        assert(partner is self.spouse and partner.spouse is self), (
            "{0} tried to divorce {1}, whom they are not married to.".format(
                self.name, partner.name)
        )
        # The soon-to-be divorcees will decide together which lawyer to hire, because they are
        # technically still married (and spouses are considered as part of this method call)
        lawyer = self.contract_person_of_certain_occupation(
            occupation_in_question=occupation.Lawyer)

        divorce = life_event.Divorce(subjects=(self, partner),
                                     lawyer=lawyer,
                                     date=date)
        spouse = self.spouse
        self.marriage.terminus = divorce
        life_event.Divorce.have_divorcees_split_up_money(self, spouse)
        life_event.Divorce.have_a_spouse_and_possibly_kids_change_name_back(self, divorce)
        life_event.Divorce.update_divorcee_attributes(self, spouse, divorce)


        if lawyer:
            lawyer.filed_divorces.add(divorce)

        if self.town:
            life_event.Divorce.decide_and_enact_new_living_arrangements(self, spouse, divorce)

        spouse.life_events.add(divorce)
        self.life_events.add(divorce)
        self.sim.register_event(divorce)

    def give_birth(self, date=None):
        """Select a doctor and go to the hospital to give birth."""

        if date is None:
            date = self.sim.current_date

        doctor = self.contract_person_of_certain_occupation(occupation.Doctor)

        baby = Person(self.sim, "", "", self.town, self, self.impregnated_by, date)
        baby._init_familial_attributes()
        baby._init_update_familial_attributes_of_family_members()
        life_event.Birth.generate_baby_name(baby, baby.sim.config)

        birth = life_event.Birth(baby=baby, mother=self, doctor=doctor, date=date)

        # Add birth to the involved parties' sets of life events
        baby.birth = birth
        baby.life_events.add(birth)
        self.life_events.add(birth)
        if baby.father:
            baby.father.life_events.add(birth)

        if doctor:
            doctor.baby_deliveries.add(birth)

        if baby.biological_father is self.spouse:
            self.marriage.children_produced.add(baby)

        if self.home:
            baby.move(new_home=self.home, reason=birth, date=date)

        if self.occupation:
            life_event.Birth.mother_potentially_exit_workforce(self, date, birth)

        life_event.Birth.reset_pregnancy_attributes(self)
        self.sim.register_birthday((date.month, date.day), baby)
        self.sim.register_event(birth)

        # Create adoption if the father is not the biological father
        if baby.father is not None and baby.father is not baby.biological_father:
            adoption = life_event.Adoption(adoptee=baby, adoptive_parents=(baby.father,), date=date)
            baby.father.life_events.add(adoption)
            self.sim.register_event(adoption)

    def die(self, cause_of_death, date):
        """Die and get interred at the local cemetery."""
        mortician = self.next_of_kin.contract_person_of_certain_occupation(
            occupation_in_question=occupation.Mortician)

        death = life_event.Death(subject=self,
                                 widow=self.spouse,
                                 mortician=mortician,
                                 cause_of_death=cause_of_death,
                                 date=date)

        life_event.Death.update_attributes_of_deceased_and_spouse(self, death)
        life_event.Death.vacate_job_position_of_the_deceased(self, death)

        self.death = death
        if mortician is not None:
            mortician.body_interments.add(death)


        self.go_to(destination=self.town.cemetery)
        self.gravestone = Gravestone(subject=self)

        # If this person has kids at home and no spouse to take care of them,
        # have those kids depart the town (presumably to live with relatives
        # elsewhere) -- TODO have the kids be adopted by a relative in town,
        # but watch out, because kids at home may be old maids still living with
        # their parents
        if self.kids_at_home and not self.spouse:
            for kid in self.kids_at_home:
                kid.depart_town(self.sim.current_date)

        # Update attributes of this person's home
        self.home.residents.remove(self)
        self.home.former_residents.add(self)

        if self in self.home.owners:
            self.home.owners.remove(self)
            if self.home.residents and not self.home.owners:
                life_event.Death.transfer_ownership_of_home_owned_by_the_deceased(self)

        self.town.residents.remove(self)
        self.town.deceased.add(self)

        self.life_events.add(death)
        self.sim.register_event(death)

    def look_for_work(self, date):
        """Attempt to find a job at a local business.

        This method has every business in town that had potential job vacancies
        rate this person as a candidate for those vacancies. The person then
        gets hired by the company who has rated them highest, assuming they
        qualify for any positions at all.
        """
        # If a family member owns a company, and you're employable at that position,
        # try to get hired by that company for one of their supplemental positions
        if any(f for f in self.extended_family if f.occupation and f.occupation.company.owner is f.occupation):
            self._find_job_at_the_family_company()
        else:
            # Try to get hired by any company in town for one of their supplemental positions
            scores = self._get_scored_as_job_candidate_by_all_companies()
            # If this person qualified for any position, have them be hired to the one
            # for which they were scored mostly highly
            if scores:
                company, position, shift = max(scores, key=scores.get)
                company.hire(occupation_of_need=position,
                             shift=shift, to_replace=None,
                             fills_supplemental_job_vacancy=True,
                             selected_candidate=self,
                             date=date)

    def _find_job_at_the_family_company(self):
        """Try to get hired by a company that your family member owns."""
        must_add_supplemental_position = False
        # First, see if your father or mother owns a company
        family_companies = self._assemble_family_companies()
        for family_company in family_companies:
            if family_company.supplemental_vacancies['day']:
                position, shift = family_company.supplemental_vacancies['day'][0], 'day'
            elif family_company.supplemental_vacancies['night']:
                position, shift = family_company.supplemental_vacancies['night'][0], 'night'
            # If its your parent, they will accommodate and add another supplemental position
            elif family_company.owner.person in self.parents:
                must_add_supplemental_position = True
                initial_job_vacancies = self.sim.config.business.initial_job_vacancies
                if self.sim.config.business.initial_job_vacancies[family_company.__class__]['day']:
                    position, shift = (
                        initial_job_vacancies[family_company.__class__]['day'][0], 'day'
                    )
                elif self.sim.config.business.initial_job_vacancies[family_company.__class__]['night']:
                    position, shift = (
                        initial_job_vacancies[family_company.__class__]['night'][0], 'night'
                    )
                elif self.sim.config.business.initial_job_vacancies[family_company.__class__]['supplemental day']:
                    position, shift = (
                        initial_job_vacancies[family_company.__class__]['supplemental day'][0], 'day'
                    )
                else:
                    position, shift = (
                        initial_job_vacancies[family_company.__class__]['supplemental night'][0], 'night'
                    )
            else:
                # Nothing can be done in this circumstance, so move on to the next
                # family company
                break
            i_am_qualified_for_this_position = (
                family_company.check_if_person_is_qualified_for_the_position(
                    candidate=self, occupation_of_need=position
                )
            )
            if i_am_qualified_for_this_position:
                if must_add_supplemental_position:
                    family_company.supplemental_vacancies[shift].append(
                        position)
                family_company.hire(
                    occupation_of_need=position, shift=shift, to_replace=None,
                    fills_supplemental_job_vacancy=True, selected_candidate=self,
                    hired_as_a_favor=must_add_supplemental_position,
                    date=get_random_day_of_year(self.sim.current_date.year)
                )
                break

    def _assemble_family_companies(self):
        """Assemble all the companies in town owned by a family member of yours."""
        family_companies = []
        # If one of your parents owns a company, put that one first in the list
        # of family companies you'll try to get hired by
        if any(p for p in self.parents if p.occupation and p.occupation.company.owner is p.occupation):
            parent_who_owns_a_company = next(
                p for p in self.parents if p.occupation and p.occupation.company.owner is p.occupation
            )
            family_companies.append(
                parent_who_owns_a_company.occupation.company)
        else:
            family_members_who_own_companies = (
                f for f in self.extended_family if f.occupation and f.occupation.company.owner is f.occupation
            )
            for relative in family_members_who_own_companies:
                family_companies.append(relative.occupation.company)
        return family_companies

    def _get_scored_as_job_candidate_by_all_companies(self):
        """Get scored as a job candidate by all companies in town for all their supplemental positions."""
        scores = dict()
        # Assemble scores of this person as a job candidate from all companies
        # in town for all of their open positions, day- or night-shift
        for company in self.sim.town.businesses:
            for shift in ('day', 'night'):
                for position in company.supplemental_vacancies[shift]:
                    i_am_qualified_for_this_position = (
                        company.check_if_person_is_qualified_for_the_position(
                            candidate=self, occupation_of_need=position
                        )
                    )
                    if i_am_qualified_for_this_position:
                        score = company.rate_job_candidate(person=self)
                        # The open positions are listed in order of priority, so
                        # penalize this position if its not the company's top priority
                        priority = company.supplemental_vacancies[shift].index(
                            position)
                        score /= priority+1
                        scores[(company, position, shift)] = score
        return scores

    def ff_parents(self, date):
        """Move out of parents' house."""
        home_to_move_into = self.secure_home(date)
        if home_to_move_into:
            self.move(new_home=home_to_move_into, reason=None, date=date)
        else:
            self.depart_town(date=date)

    def move_into_the_town(self, town, hiring_event, date):
        """Move into the town

            Parameters
            ----------
            town: Town
                Town to move into

            hiring_event: Hiring
                Hiring event that instigated the move

            date: datetime
                Date the charactes is moving into the town
        """
        self.town = town

        new_home = self.secure_home(date)

        if not new_home:
            someone_elses_home = random.choice(list(self.town.residences))
            self.move(new_home=someone_elses_home,
                      reason=hiring_event, date=date)
        if new_home:
            self.move(new_home=new_home, reason=hiring_event)
        else:
            # Have the closest apartment complex to downtown expand to add
            # another unit for this person to move into
            apartment_complexes_in_town = [
                # Check if they have units first -- have had the weird case of someone
                # trying to build a complex right downtown and then not being able to
                # expand that very complex itself to move into it, because it currently
                # has no units, and thus no unit number to give the expansion unit
                ac for ac in self.town.get_businesses_of_type('ApartmentComplex') if ac.units
            ]
            if len(apartment_complexes_in_town) > 3:
                complexes_closest_to_downtown = heapq.nlargest(
                    3, apartment_complexes_in_town,
                    key=lambda ac: self.town.distance_between(
                        ac.lot, self.town.downtown)
                )
                complex_that_will_expand = random.choice(
                    complexes_closest_to_downtown)
            else:
                complex_that_will_expand = min(
                    apartment_complexes_in_town,
                    key=lambda ac: self.town.distance_between(
                        ac.lot, self.town.downtown)
                )
            complex_that_will_expand.expand()  # This will add two new units to this complex
            self.move(
                new_home=complex_that_will_expand.units[-2],
                reason=hiring_event)

    def move(self, new_home, reason, date=None):
        """Move to an apartment or home."""
        if date is None:
            date = get_random_day_of_year(year=self.sim.current_date.year)

        move_event = life_event.Move(subjects=self.nuclear_family,
                                     new_home=new_home, reason=reason, date=date)


        if self.home:
            self.home.move_outs.append(move_event)
        new_home.move_ins.append(move_event)

        # Actually move the person(s)
        town = self.sim.town
        for person in self.nuclear_family | OrderedSet([self]):
            # Move out of old home, if any
            if person.home:
                person.home.residents.remove(person)
                person.home.former_residents.add(person)

            # Move into new home
            person.home = new_home
            new_home.residents.add(person)
            person.moves.append(move_event)

            # Add yourself to town residents, if you moved from outside the town
            town.residents.add(person)
            person.town = town

            # Go to your new home
            person.go_to(destination=new_home, occasion='home')
        # Update .neighbor attributes for subjects, as well as their new and now former neighbors
        life_event.Move.update_mover_and_neighbor_attributes(self.nuclear_family, new_home)

        self.life_events.add(move_event)
        self.sim.register_event(move_event)

    def go_to(self, destination, occasion=None):
        """Go to destination and spend this timestep there."""
        if self.location:  # People just being instantiated won't have a location yet
            self.location.people_here_now.remove(self)
        self.location = destination
        if destination and self.alive:  # 'destination' will be None for Departures, and dead people go_to cemetery
            destination.people_here_now.add(self)
            # Update this person's whereabouts
            self.whereabouts.record(occasion=occasion)


    def move_out_of_parents(self, date):
        """Move out of parents' house."""
        home_to_move_into = self.secure_home(date=date)
        if home_to_move_into:
            self.move(new_home=home_to_move_into, reason=None)
        else:
            self.depart_town(date=date)

    def pay(self, payee, amount):
        """Pay someone (for services rendered)."""
        if self.spouse:
            self.marriage.money -= amount
        else:
            self.money -= amount
        payee.money += amount

    def retire(self, date):
        """Retire from an occupation."""
        retire_event = life_event.Retirement(self, date)

        self.retired = True
        self.retirement = retire_event
        self.occupation.terminate(reason=retire_event, date=date)

        self.sim.register_event(retire_event)

    def depart_town(self, date, forced_nuclear_family=None):
        """Depart the town (and thus the simulation), never to return.

        forced_nuclear_family is reserved for Marriage events in which the newlyweds
        cannot find housing in the town and so depart, potentially with their entire
        new mixed family. In this case, a special procedure (_move_spouses_and_any_kids_
        in_together) determines which stepchildren will move with them; because this
        procedure returns a different set of people than self.nuclear_family does, we
        need to allow the assertion of a forced nuclear family for Marriage-related
        Departures.
        """

        departure = life_event.Departure(subject=self, date=date)
        self.life_events.add(departure)
        self.sim.register_event(departure)

        self.town.residents.remove(self)
        self.town.departed.add(self)
        self.departure = departure

        self.go_to(destination=None)
        self.home.residents.remove(self)
        self.home.former_residents.add(self)

        life_event.Departure.vacate_job_position_of_the_departed(self, departure)
        life_event.Departure.update_neighbor_attributes(self)

        # Have this person's nuclear family depart as well
        nuclear_family = forced_nuclear_family if forced_nuclear_family else self.nuclear_family
        for person in nuclear_family - OrderedSet([self]):
            if person in self.town.residents:
                event = life_event.Departure(subject=person, date=date)
                self.life_events.add(event)
                self.sim.register_event(event)

    def contract_person_of_certain_occupation(self, occupation_in_question):
        """Find a person of a certain occupation.

        Currently, a person scores all the potential hires in town and then selects
        one of the top three. TODO: Probabilistically select from all potential hires
        using the scores to derive likelihoods of selecting each.
        """
        if self.town:
            pool = list(self.town.get_workers_of_trade(occupation_in_question))
        else:  # PersonExNihilo who backstory is currently being retconned
            pool = []
        if pool:
            # If you or your spouse practice this occupation, DIY
            if isinstance(self.occupation, occupation_in_question):
                choice = self.occupation
            elif self.spouse and isinstance(self.spouse.occupation, occupation_in_question):
                choice = self.spouse.occupation
            # Otherwise, pick from the various people in town who do practice this occupation
            else:
                potential_hire_scores = self._rate_all_potential_contractors_of_certain_occupation(
                    pool=pool)
                if len(potential_hire_scores) >= 3:
                    # Pick from top three
                    top_three_choices = heapq.nlargest(
                        3, potential_hire_scores, key=potential_hire_scores.get)
                    if random.random() < 0.6:
                        choice = top_three_choices[0]
                    elif random.random() < 0.9:
                        choice = top_three_choices[1]
                    else:
                        choice = top_three_choices[2]
                else:
                    choice = max(potential_hire_scores)
        else:
            # This should only ever happen at the very beginning of a town's history where all
            # business types haven't been built in town yet
            choice = None
        return choice

    def _rate_all_potential_contractors_of_certain_occupation(self, pool):
        """Score all potential hires of a certain occupation."""
        scores = dict()
        for occupation in pool:
            scores[occupation] = self._rate_potential_contractor_of_certain_occupation(
                person=occupation.person)
        return scores

    def _rate_potential_contractor_of_certain_occupation(self, person):
        """Score a potential hire of a certain occupation, with preference to family, friends, former hires.

        TODO: Have this be affected by personality (beyond what being a friend captures).
        """
        score = 0
        # Rate according to social reasons
        if self.spouse:
            people_involved_in_this_decision = (self, self.spouse)
        else:
            people_involved_in_this_decision = (self,)
        for decision_maker in people_involved_in_this_decision:
            if person in decision_maker.immediate_family:
                score += decision_maker.sim.config.misc_character_decision_making.preference_to_contract_immediate_family
            # elif because immediate family is subset of extended family
            elif person in decision_maker.extended_family:
                score += decision_maker.sim.config.misc_character_decision_making.preference_to_contract_extended_family
            if person in decision_maker.friends:
                score += decision_maker.sim.config.misc_character_decision_making.preference_to_contract_friend
            elif person in decision_maker.acquaintances:
                score += decision_maker.sim.config.misc_character_decision_making.preference_to_contract_acquaintance
            if person in decision_maker.enemies:
                score += decision_maker.sim.config.misc_character_decision_making.dispreference_to_hire_enemy
            if person in decision_maker.former_contractors:
                score += decision_maker.sim.config.misc_character_decision_making.preference_to_contract_former_contract
        # Multiply score according to this person's experience in this occupation
        score *= person.sim.config.misc_character_decision_making.score_multiplier_bonus_for_experience(
            years_experience=person.occupation.years_experience
        )
        return score

    def purchase_home(self, purchasers, home, date):
        # TEMP THING DUE TO CIRCULAR DEPENDENCY -- SEE RESIDENCE.PY -- TODO
        event = life_event.HomePurchase(subjects=purchasers, home=home, realtor=None, date=date)
        self.life_events.add(event)
        self.sim.register_event(event)

    def secure_home(self, date):
        """Find a home to move into.

        The person (and their spouse, if any) will decide between all the vacant
        homes and vacant lots (upon which they would build a new home) in the town.
        """
        chosen_home_or_lot = self._choose_vacant_home_or_vacant_lot()
        if chosen_home_or_lot:
            if chosen_home_or_lot in self.town.vacant_lots:
                # A vacant lot was chosen, so build
                home_to_move_into = self._commission_construction_of_a_house(lot=chosen_home_or_lot, date=date)
            elif chosen_home_or_lot in self.town.vacant_homes:
                # A vacant home was chosen
                home_to_move_into = self._purchase_home(home=chosen_home_or_lot, date=date)
            else:
                raise Exception(
                    "{} has secured a lot or home that is not known to be vacant.".format(
                        self.name)
                )
        else:
            home_to_move_into = None  # The town is full; this will spark a departure
        return home_to_move_into

    def _commission_construction_of_a_house(self, lot, date):
        """Build a house to move into."""
        # Try to find an architect -- if you can't, you'll have to build it yourself
        architect = self.contract_person_of_certain_occupation(occupation_in_question=occupation.Architect)
        clients = OrderedSet([self])

        if self.spouse:
            clients.add(self.spouse)

        house = House(lot=lot, town=self.town, owners=clients)
        house.init_ownership(clients, date)
        construction_event = life_event.HouseConstruction(subjects=clients, architect=architect, lot=lot, house=house, date=date)

        house.construction = construction_event

        for person in clients:
            house.owners.add(person)
            person.life_events.add(construction_event)

        if architect is not None:
            architect.building_constructions.add(construction_event)

        self.sim.register_event(construction_event)

        return house

    def _purchase_home(self, home, date):
        """Purchase a house or apartment unit, with the help of a realtor."""
        # Try to find a realtor -- if you can't, you'll just deal directly with the person
        realtor = self.contract_person_of_certain_occupation(occupation_in_question=occupation.Realtor)
        clients = OrderedSet()
        clients.add(self)
        if self.spouse:
            clients.add(self.spouse)

        purchase_event = life_event.HomePurchase(subjects=clients, home=home, realtor=realtor, date=date)

        life_event.HomePurchase.transfer_ownership(home, clients)

        for person in clients:
            home.owners.add(person)
            person.life_events.add(purchase_event)
            person.home_purchases.append(purchase_event)

        home.transactions.append(purchase_event)

        if realtor is not None:
            realtor.home_sales.add(purchase_event)

        return home

    def _choose_vacant_home_or_vacant_lot(self):
        """Choose a vacant home to move into or a vacant lot to build on.

        Currently, a person scores all the vacant homes/lots in town and then selects
        one of the top three. TODO: Probabilistically select from all homes/lots using the
        scores to derive likelihoods of selecting each.
        """
        home_and_lot_scores = self._rate_all_vacant_homes_and_vacant_lots()
        if len(home_and_lot_scores) >= 3:
            # Pick from top three
            top_three_choices = heapq.nlargest(
                3, home_and_lot_scores, key=home_and_lot_scores.get)
            if random.random() < 0.6:
                choice = top_three_choices[0]
            elif random.random() < 0.9:
                choice = top_three_choices[1]
            else:
                choice = top_three_choices[2]
        elif home_and_lot_scores:
            choice = list(home_and_lot_scores)[0]
        else:
            choice = None
        return choice

    def _rate_all_vacant_homes_and_vacant_lots(self):
        """Rate all vacant homes and vacant lots."""
        scores = dict()
        for home in self.town.vacant_homes:
            my_score = self.rate_potential_lot(lot=home.lot)
            if self.spouse:
                spouse_score = self.spouse.rate_potential_lot(lot=home.lot)
            else:
                spouse_score = 0
            scores[home] = my_score + spouse_score
        for lot in self.town.vacant_lots:
            my_score = self.rate_potential_lot(lot=lot)
            if self.spouse:
                spouse_score = self.spouse.rate_potential_lot(lot=lot)
            else:
                spouse_score = 0
            scores[lot] = (
                (my_score + spouse_score) *
                self.sim.config.misc_character_decision_making.penalty_for_having_to_build_a_home_vs_buying_one
            )
        return scores

    def rate_potential_lot(self, lot):
        """Rate the desirability of living at the location of a lot.

        By this method, a person appraises a vacant home or lot in the town for
        how much they would like to move or build there, given considerations to the people
        that live nearby it (this reasoning via self.score_potential_home_or_lot()). There is
        a penalty that makes people less willing to build a home on a vacant lot than to move
        into a vacant home.
        """
        pull_to_live_near_that_relation = self.sim.config.misc_character_decision_making.pull_to_live_near_family
        pull_to_live_near_a_friend = self.sim.config.misc_character_decision_making.pull_to_live_near_a_friend
        desire_to_live_near_family = self._determine_desire_to_move_near_family()
        # Score home for its proximity to family (either positively or negatively, depending); only
        # consider family members that are alive, in town, and not living with you already (i.e., kids)
        relatives_in_town = OrderedSet(
            [f for f in self.extended_family if f.present and f.home is not self.home])
        score = 0
        for relative in relatives_in_town:
            relation_to_me = self._common_familial_relation_to_me(
                person=relative)
            pull_toward_someone_of_that_relation = pull_to_live_near_that_relation.get(
                relation_to_me, 0.0)
            dist = self.town.distance_between(
                relative.home.lot, lot) + 1.0  # To avoid ZeroDivisionError
            score += (desire_to_live_near_family *
                      pull_toward_someone_of_that_relation) / dist
        # Score for proximity to friends (only positively)
        for friend in self.friends:
            dist = self.town.distance_between(friend.home.lot, lot) + 1.0
            score += pull_to_live_near_a_friend / dist
        # Score for proximity to workplace (only positively) -- will be only criterion for person
        # who is new to the town (and thus accurate_belief no one there yet)
        if self.occupation:
            dist = self.town.distance_between(
                self.occupation.company.lot, lot) + 1.0
            score += self.sim.config.misc_character_decision_making.pull_to_live_near_workplace / dist
        return score

    def _determine_desire_to_move_near_family(self):
        """Decide how badly you want to move near/away from family.

        Currently, this relies on immutable personality traits, but eventually
        this desire could be made dynamic according to life events, etc.
        """
        # People with personality C-, O+ most likely to leave home (source [1])
        base_desire_to_live_near_family = self.sim.config.misc_character_decision_making.desire_to_live_near_family_base
        desire_to_live_near_family = self.personality.conscientiousness
        desire_to_live_away_from_family = self.personality.openness_to_experience
        final_desire_to_live_near_family = (
            base_desire_to_live_near_family +
            desire_to_live_near_family - desire_to_live_away_from_family
        )
        if final_desire_to_live_near_family < self.sim.config.misc_character_decision_making.desire_to_live_near_family_floor:
            final_desire_to_live_near_family = self.sim.config.misc_character_decision_making.desire_to_live_near_family_floor
        elif final_desire_to_live_near_family > self.sim.config.misc_character_decision_making.desire_to_live_near_family_cap:
            final_desire_to_live_near_family = self.sim.config.misc_character_decision_making.desire_to_live_near_family_cap
        return final_desire_to_live_near_family

    def socialize(self, missing_timesteps_to_account_for=1):
        """Socialize with nearby people."""
        if not self.location:
            raise Exception(
                "{} tried to socialize, but they have no location currently.".format(self.name))
        for person in list(self.location.people_here_now):
            if self._decide_to_instigate_social_interaction(other_person=person):
                if person not in self.relationships:
                    Acquaintance(owner=self, subject=person, preceded_by=None)
                if not self.relationships[person].interacted_this_timestep:
                    # Make sure they didn't already interact this timestep
                    self.relationships[person].progress_relationship(
                        missing_days_to_account_for=missing_timesteps_to_account_for
                    )
        # Also cheat to simulate socializing between people that live together,
        # regardless of where they are truly located (otherwise have things like
        # a kid who has never met his mother, because she works the night shift)
        for person in list(self.home.residents-OrderedSet([self])):
            if person not in self.relationships:
                Acquaintance(owner=self, subject=person, preceded_by=None)
            if not self.relationships[person].interacted_this_timestep:
                # Make sure they didn't already interact this timestep
                self.relationships[person].progress_relationship(
                    missing_days_to_account_for=missing_timesteps_to_account_for
                )

    def _decide_to_instigate_social_interaction(self, other_person):
        """Decide whether to instigate a social interaction with another person."""
        if other_person is self or other_person.age < 5:
            chance = 0.0
        else:
            extroversion_component = self._get_extroversion_component_to_chance_of_social_interaction()
            # If this person accurate_belief other_person, we look at their relationship to determine
            # how its strength will factor into the decision; if they don't know this person,
            # we then factor in this person's openness to experience instead
            if other_person not in self.relationships:
                friendship_or_openness_component = self._get_openness_component_to_chance_of_social_interaction()
            else:
                friendship_or_openness_component = self._get_friendship_component_to_chance_of_social_interaction(
                    other_person=other_person
                )
            chance = extroversion_component + friendship_or_openness_component
            if chance < self.sim.config.social_sim.chance_someone_instigates_interaction_with_other_person_floor:
                chance = self.sim.config.social_sim.chance_someone_instigates_interaction_with_other_person_floor
            elif chance > self.sim.config.social_sim.chance_someone_instigates_interaction_with_other_person_cap:
                chance = self.sim.config.social_sim.chance_someone_instigates_interaction_with_other_person_cap
        if random.random() < chance:
            return True
        else:
            return False

    def _get_extroversion_component_to_chance_of_social_interaction(self):
        """Return the effect of this person's extroversion on the chance of instigating social interaction."""
        extroversion_component = self.personality.extroversion
        if extroversion_component < self.sim.config.social_sim.chance_of_interaction_extroversion_component_floor:
            extroversion_component = self.sim.config.social_sim.chance_of_interaction_extroversion_component_floor
        elif extroversion_component > self.sim.config.social_sim.chance_of_interaction_extroversion_component_cap:
            extroversion_component = self.sim.config.social_sim.chance_of_interaction_extroversion_component_cap
        return extroversion_component

    def _get_openness_component_to_chance_of_social_interaction(self):
        """Return the effect of this person's openness on the chance of instigating social interaction."""
        openness_component = self.personality.openness_to_experience
        if openness_component < self.sim.config.social_sim.chance_of_interaction_openness_component_floor:
            openness_component = self.sim.config.social_sim.chance_of_interaction_openness_component_floor
        elif openness_component > self.sim.config.social_sim.chance_of_interaction_openness_component_cap:
            openness_component = self.sim.config.social_sim.chance_of_interaction_openness_component_cap
        return openness_component

    def _get_friendship_component_to_chance_of_social_interaction(self, other_person):
        """Return the effect of an existing friendship on the chance of instigating social interaction."""
        friendship_component = 0.0
        if other_person in self.friends:
            friendship_component += self.sim.config.social_sim.chance_of_interaction_friendship_component
        if other_person is self.best_friend:
            friendship_component += self.sim.config.social_sim.chance_of_interaction_best_friend_component
        return friendship_component

    def grow_older(self, year=None, retcon=False):
        """Check if it's this persons birth day; if it is, age them."""
        if year is None:
            year = self.sim.current_date.year

        consider_leaving_town = False

        self.age += 1

        # If you've just entered school age and your mother had been staying at
        # home to take care of you, she may now reenter the workforce
        try:
            if self.age == self.sim.config.life_cycle.age_children_start_going_to_school \
               and self.mother and not self.mother.intending_to_work:

                if not random.random() < self.sim.config.life_cycle.chance_mother_of_young_children_stays_home(year=year):
                    self.mother.intending_to_work = True

        except AttributeError:
            # We're retconning, which means the mother doesn't even have the attribute 'intending_to_work'
            # set yet, which throws an error; because we're retconning, we don't even want to be
            # actively modeling whether she is in the workforce anyway
            pass

        if self.age == self.sim.config.life_cycle.age_people_start_working(year=year):
            self.in_the_workforce = True
            consider_leaving_town = True


        # If you're now old enough to be developing romantic feelings for other characters,
        # it's time to (potentially) reset your spark increments for all your relationships
        if self.age == self.sim.config.social_sim.age_characters_start_developing_romantic_feelings:
            for other_person in self.relationships:
                self.relationships[other_person].reset_spark_increment()

        # If you haven't in a while (in the logarithmic sense, rather than absolute
        # sense), update all relationships you have to reflect the new age difference
        # between you and the respective other person
        if self.age in (
            1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 14, 16, 18,
            20, 23, 26, 29, 33, 37, 41, 45, 50, 55, 60,
            65, 70, 75, 80, 85, 90, 95, 100,
        ):
            for other_person in self.relationships:
                self.relationships[other_person].update_spark_and_charge_increments_for_new_age_difference()

        # Potentially have your hair turn gray (or white, if it's already gray) -- TODO MAKE THIS HERITABLE
        if self.age > self.sim.config.life_cycle.age_when_people_start_graying:
            if random.random() < self.sim.config.life_cycle.chance_someones_hair_goes_gray_or_white:
                new_color_str = 'gray' if self.face.hair.color != 'gray' else 'white'
                # Maintain the same face.Feature attributes as the original Feature had, but
                # create a new Feature object with the updated string -- TODO is this still inheritance?
                variant_id = self.face.hair.color.variant_id
                inherited_from = self.face.hair.color.inherited_from
                exact_variant_inherited = self.face.hair.color.exact_variant_inherited
                self.face.hair.color = face.Feature(
                    value=new_color_str, variant_id=variant_id, inherited_from=inherited_from,
                    exact_variant_inherited=exact_variant_inherited
                )
        # Potentially go bald, if male -- TODO MAKE THIS HERITABLE
        if self.male and self.age > self.sim.config.life_cycle.age_when_men_start_balding:
            if random.random() < self.sim.config.life_cycle.chance_someones_loses_their_hair_some_year:
                # Maintain the same face.Feature attributes as the original Feature had, but
                # create a new Feature object with the updated string -- TODO is this still inheritance?
                variant_id = self.face.hair.length.variant_id
                inherited_from = self.face.hair.length.inherited_from
                exact_variant_inherited = self.face.hair.length.exact_variant_inherited
                self.face.hair.length = face.Feature(
                    value='bald', variant_id=variant_id, inherited_from=inherited_from,
                    exact_variant_inherited=exact_variant_inherited)

        if not retcon \
           and consider_leaving_town \
           and random.random() < self.sim.config.basic.chance_a_new_adult_decides_to_leave_town:
            self.depart_town(self.sim.current_date)

    def update_salience_of(self, entity, change):
        """Increment your salience value for entity by change."""
        self.salience_of_other_people[entity] = \
            min(self.salience_of_other_people.get(entity, 0.0) + change, 100)

    def likes(self, person):
        """Return whether this person likes the given person."""
        if person not in self.relationships:
            return False
        else:
            return self.relationships[person].charge > self.sim.config.social_sim.charge_threshold_for_liking_someone

    def dislikes(self, person):
        """Return whether this person dislikes the given person."""
        if person not in self.relationships:
            return False
        else:
            return self.relationships[person].charge < self.sim.config.social_sim.charge_threshold_for_disliking_someone

    def hates(self, person):
        """Return whether this person hates the given person."""
        if person not in self.relationships:
            return False
        else:
            return self.relationships[person].charge < self.sim.config.charge_threshold_for_hating_someone

    def __str__(self):
        """Return string representation."""
        if self.present:
            return "{}, {} years old".format(self.name, self.age)
        elif self.departure:
            return "{}, left town in {}".format(self.name, self.departure.year)
        elif not self.alive:
            return "{}, {}-{}".format(self.name, self.birth_year, self.death_year)
        else:
            return "{}, {} years old".format(self.name, self.age)

    def __gt__(self, other):
        """Greater than"""
        return self.id > other.id

    def __lt__(self, other):
        """less than"""
        return self.id < other.id

class PersonExNihilo(Person):
    """A person who is generated from nothing, i.e., who has no parents.

    This is a subclass of Person whose objects are people that enter the simulation
    from outside the town, either as town founders or as new hires for open positions
    that could not be filled by anyone currently in the town. Because these people don't
    have parents, a subclass is needed to override any attributes or methods that rely
    on inheritance. Additionally, a family (i.e., a PersonExNihilo spouse and possibly Person
    children) may be generated for a person of this class.
    """

    def __init__(self, sim, job_opportunity_impetus=None, spouse=None):
        super().__init__(sim, "", "", None, None, None, sim.current_date)

        # Ensure this person is sexual compatible with their spouse
        if spouse is not None:
            self.sex = random.choice(spouse.attracted_to)
            self.attracted_to = OrderedSet([spouse.sex])

        elif job_opportunity_impetus is not None:
            # Make sure you have the appropriate sex for the job position you are coming
            # to town to accept; if you don't, swap your sex
            if not self.sim.config.business.employable_as_a[job_opportunity_impetus](applicant=self):
                self.sex = "female" if self.male else "male"

        # Determine a random birthday and overwrite birth year set by Person.__init__()
        job_level = self.sim.config.business.job_levels[job_opportunity_impetus]

        birth_date = PersonExNihilo.generate_birth_date(sim.current_date, job_level, sim.config)
        self.birth_year = birth_date.year
        self.birthday = (birth_date.month, birth_date.day)
        self.age = sim.current_date.year - birth_date.year

        # Check if this person is eligible to work
        self.in_the_workforce = self.age >= self.sim.config.life_cycle.age_people_start_working(self.sim.current_date.year)

        # Since they don't have a parent to name them, generate a name for this person (if
        # they get married outside the town, this will still potentially change, as normal)
        self.first_name, self.middle_name, self.last_name = self.generate_name(self.birth_year)
        self.maiden_name = self.last_name

        # If this person is being hired for a high job level, retcon that they have
        # a college education -- do the same for the town founder
        if (job_opportunity_impetus and
                job_opportunity_impetus in self.sim.config.business.occupations_requiring_college_degree):
            self.college_graduate = True

        self.money = sim.config.misc_character.amount_of_money_generated_people_from_outside_town_start_with

    @staticmethod
    def create_person(sim, job_opportunity_impetus=None, spouse=None):
        """Create PersonExNihilo and adds them to the town

            Also potentially generate and retcon a family that this person will have had prior
            to moving into the town; if the person is moving here to be a farmer, force that
            a family be retconned (mostly to ensure that at least some people in the present
            day will have roots in the town going back to its early foundations when it
            comprised a handful of farms)
        """
        person = PersonExNihilo(sim, job_opportunity_impetus=job_opportunity_impetus, spouse=spouse)
        person._init_potentially_retcon_family(spouse, job_opportunity_impetus)
        sim.register_birthday(person.birthday, person)
        return person

    def generate_name(self, birth_year):
        """Generate a name for a primordial person who has no parents."""
        if self.male:
            first_name_rep = Names.a_masculine_name(birth_year)
            middle_name_rep = Names.a_masculine_name(birth_year)
        else:
            first_name_rep = Names.a_feminine_name(birth_year)
            middle_name_rep = Names.a_feminine_name(birth_year)

        first_name = Name(value=first_name_rep, progenitor=self,
                          conceived_by=(), derived_from=())
        middle_name = Name(value=middle_name_rep,
                           progenitor=self, conceived_by=(), derived_from=())
        last_name = Name(value=Names.any_surname(),
                         progenitor=self, conceived_by=(), derived_from=())

        return (first_name, middle_name, last_name)

    @staticmethod
    def generate_birth_date(current_date, job_level, config):
        """Generate a birth year for this person that is consistent with the job level they/spouse will get."""
        age = config.misc_character.person_ex_nihilo_age_given_job_level(job_level)
        birth_year = current_date.year - age
        birth_date = get_random_day_of_year(birth_year)
        return birth_date

    def _init_potentially_retcon_family(self, spouse, job_opportunity_impetus):
        """Potentially generate and retcon a family that this person will have had prior
        to entering into the simulation.
        """
        if spouse is None:
            chance_of_having_family = \
                self.sim.config.misc_character.chance_person_ex_nihilo_starts_with_family(
                    self.sim.town.population)

            if random.random() < chance_of_having_family or job_opportunity_impetus.__name__ == 'Farmer':
                self._generate_family(job_opportunity_impetus)

    def _generate_family(self, job_opportunity_impetus):
        """Generate and retcon a family that this person will take with them into the town."""
        spouse = PersonExNihilo.create_person(self.sim, job_opportunity_impetus=job_opportunity_impetus, spouse=self)
        self._retcon_marriage(spouse)
        self._retcon_births_of_children()

    def _retcon_marriage(self, spouse):
        """Jump back in time to instantiate a marriage that began outside the town."""
        # Change actual sim year to marriage year, instantiate a Marriage object
        marriage_age_mean = self.sim.config.misc_character.person_ex_nihilo_age_at_marriage_mean
        marriage_age_sd = self.sim.config.misc_character.person_ex_nihilo_age_at_marriage_sd
        marriage_age_floor =  self.sim.config.misc_character.person_ex_nihilo_age_at_marriage_floor

        marriage_year = round(self.birth_year + random.normalvariate(marriage_age_mean, marriage_age_sd))

        # Make sure spouses aren't too young for marriage and that marriage isn't slated
        # to happen after the town has been founded
        if (marriage_year - self.birth_year < marriage_age_floor
            or marriage_year - spouse.birth_year < marriage_age_floor
            or marriage_year >= self.sim.current_date.year):
            # If so, don't bother regenerating -- just set marriage year to last year and move on
            marriage_year = self.sim.current_date.year - 1

        self.marry(spouse, get_random_day_of_year(marriage_year))

    def _retcon_births_of_children(self):
        """Simulate from marriage to the present day for children potentially being born."""
        # Simulate sex (and thus potentially birth) in marriage thus far
        for year in range(self.marriage.year, self.sim.current_date.year):

            for k in self.kids:
                k.grow_older(year=year, retcon=True)

            # Get a random day this year
            random_day = get_random_day_of_year(year)

            # If someone is pregnant and due this year, have them give birth
            if self.pregnant or self.spouse.pregnant:
                pregnant_one = self if self.pregnant else self.spouse
                if pregnant_one.conception_year < year:
                    pregnant_one.give_birth(random_day)

            chance_they_are_trying_to_conceive_this_year = \
                self.sim.config.marriage.chance_married_couple_are_trying_to_conceive(
                    n_kids=len(self.marriage.children_produced))

            if random.random() < chance_they_are_trying_to_conceive_this_year:
                self.have_sex(partner=self.spouse, protection=False, date=random_day)
            else:
                self.have_sex(partner=self.spouse, protection=True, date=random_day)
