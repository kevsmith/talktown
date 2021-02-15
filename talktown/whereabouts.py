class Whereabouts:
    """A collection of a character's true whereabouts on each timestep of his or her life.

    Attributes:
        person: Person being tracked
        date: A dict that maps individual timesteps to a person's whereabouts
    """

    def __init__(self, person):
        """Initialize a Whereabouts object."""
        self.person = person
        # Keys will be tuples of the form (ordinal_date, day_or_night_bit), where
        # day_or_night_bit == 0 if a day timestep else 1
        self.date = dict()

    def __str__(self):
        """Return string representation."""
        return "The whereabouts of {} over the course of {} life".format(
            self.person.name, self.person.possessive_pronoun
        )

    def record(self, occasion):
        """Record this character's current whereabouts by instantiating a Whereabout object."""
        sim = self.person.sim
        ordinal_date = sim.current_date.toordinal()
        day_or_night_bit = 0 if sim.time_of_day == 'day' else 1
        timestep_key = (ordinal_date, day_or_night_bit)
        self.date[timestep_key] = Whereabout(person=self.person, occasion=occasion)

    def recount(self):
        """Pretty-print this person's entire whereabouts."""
        timesteps = self.date.keys()
        timesteps.sort(key=lambda step: (step[0], step[1]))
        for timestep in timesteps:
            whereabout = self.date[timestep]
            print('{},\t{}:\t{}\t({})'.format(
                whereabout.date[7:] if whereabout.time_of_day == 'day' else whereabout.date[9:],
                whereabout.time_of_day, whereabout.location.name, whereabout.occasion
            ))

    @property
    def current_occasion(self):
        """Return the occasion for this person's current whereabouts."""
        sim = self.person.sim
        ordinal_date = sim.current_date.toordinal()
        day_or_night_bit = 0 if sim.time_of_day == 'day' else 1
        timestep_key = (ordinal_date, day_or_night_bit)
        return self.date[timestep_key].occasion


class Whereabout:
    """A character's true location on a single timestep, with associated metadata."""

    def __init__(self, person, occasion):
        """Initialize a Whereabout object."""
        self.person = person
        self.location = person.location
        # Attribute the occasion for this character being at the location on
        # this timestep; will either be 'work', 'school', 'home', 'errand', or 'leisure'
        self.occasion = occasion
        # Attribute metadata about the timestep of this whereabout
        self.date = person.sim.get_date_str()
        self.ordinal_date = person.sim.current_date.toordinal()
        self.time_of_day = person.sim.time_of_day

    def __str__(self):
        """Return string representation."""
        if self.occasion == 'work':
            return "Working at {} ({}) on the {}".format(
                self.location.name, self.location.address,
                self.date[0].lower()+self.date[1:]
            )
        elif self.occasion == 'school':
            return "Attending school at {} ({}) on the {}".format(
                self.location.name, self.location.address,
                self.date[0].lower()+self.date[1:]
            )
        elif self.occasion == 'home':
            return "At {} home ({}) on the {}".format(
                self.person.possessive_pronoun, self.location.address,
                self.date[0].lower()+self.date[1:]
            )
        elif self.occasion == 'errand':
            return "Running an errand at {} ({}) on the {}".format(
                self.location.name, self.location.address,
                self.date[0].lower()+self.date[1:]
            )
        elif self.occasion == 'errand':
            return "Out for leisure at {} ({}) on the {}".format(
                self.location.name, self.location.address,
                self.date[0].lower()+self.date[1:]
            )
