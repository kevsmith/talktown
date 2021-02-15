import random


class Mind:
    """A person's mind."""

    def __init__(self, person):
        """Initialize a Mind object."""
        self.person = person
        if self.person.mother:  # Person object
            self.memory = self._init_memory()
        else:  # PersonExNihilo object
            self.memory = self._init_ex_nihilo_memory()

    def __str__(self):
        """Return string representation."""
        return "Mind of {person}".format(person=self.person.name)

    def _init_memory(self):
        """Determine a person's base memory capability, given their parents'."""
        config = self.person.sim.config
        if random.random() < config.misc_character.memory_heritability:
            takes_after = random.choice([self.person.biological_mother, self.person.biological_father])
            memory = random.normalvariate(takes_after.mind.memory, config.misc_character.memory_heritability_sd)
        else:
            takes_after = None
            memory = random.normalvariate(config.misc_character.memory_mean, config.misc_character.memory_sd)
        if self.person.male:  # Men have slightly worse memory (studies show)
            memory -= config.misc_character.memory_sex_diff
        if memory > config.misc_character.memory_cap:
            memory = config.misc_character.memory_cap
        elif memory < config.misc_character.memory_floor_at_birth:
            memory = config.misc_character.memory_floor_at_birth
        feature_object = Feature(value=memory, inherited_from=takes_after)
        return feature_object

    def _init_ex_nihilo_memory(self):
        """Determine this person's base memory capability."""
        config = self.person.sim.config
        memory = random.normalvariate(config.misc_character.memory_mean, config.misc_character.memory_sd)
        if self.person.male:  # Men have slightly worse memory (studies show)
            memory -= config.misc_character.memory_sex_diff
        if memory > config.misc_character.memory_cap:
            memory = config.misc_character.memory_cap
        elif memory < config.misc_character.memory_floor:
            memory = config.misc_character.memory_floor
        feature_object = Feature(value=memory, inherited_from=None)
        return feature_object


class Feature(float):
    """A feature representing a person's memory capability and metadata about that."""

    def __init__(self, value, inherited_from):
        """Initialize a Feature object.

        @param value: A float representing the value, on a scale from -1 to 1, of a
                      person's memory capability.
        @param inherited_from: The parent from whom this memory capability was
                               inherited, if any.
        """
        super().__init__()
        self.inherited_from = inherited_from

    def __new__(cls, value, inherited_from):
        """Do float stuff."""
        return float.__new__(cls, value)
