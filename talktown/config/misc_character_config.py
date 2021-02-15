import random

class MiscellaneousCharacterConfig:
    """Configuration parameters related to assorted aspects of characters."""


    def __init__(self):
        # Infertility parameters (defined using a source that I failed to record)
        self.male_infertility_rate = 0.07
        self.female_infertility_rate = 0.11
        # Sexuality parameters (defined using a source that I failed to record)
        self.homosexuality_incidence = 0.045
        self.bisexuality_incidence = 0.01
        self.asexuality_incidence = 0.002
        # Memory parameters; memory is important in the full Talk of the Town framework, since
        # it affects the likelihood of misremembering knowledge -- that's been taken out here, but
        # I can imagine memory still being useful in some way, so I'm keeping that here
        self.memory_mean = 1.0
        self.memory_sd = 0.05
        self.memory_cap = 1.0
        self.memory_floor = 0.5  # After severe memory loss from aging
        self.memory_floor_at_birth = 0.8  # Worst possible memory of newborn
        self.memory_sex_diff = 0.03  # Men have worse memory, studies show
        self.memory_heritability = 0.6  # Couldn't quickly find a study on this -- totally made up
        self.memory_heritability_sd = 0.05
        # Parameters relating to the naming of children
        self.chance_son_inherits_fathers_exact_name = 0.03
        self.chance_child_inherits_first_name = 0.1
        self.chance_child_inherits_middle_name = 0.25
        self.frequency_of_naming_after_father = 12  # These are relative frequencies
        self.frequency_of_naming_after_grandfather = 5
        self.frequency_of_naming_after_greatgrandfather = 2
        self.frequency_of_naming_after_mother = 0
        self.frequency_of_naming_after_grandmother = 5
        self.frequency_of_naming_after_greatgrandmother = 2

        self.person_ex_nihilo_age_at_marriage_mean = 23
        self.person_ex_nihilo_age_at_marriage_sd = 2.7
        self.person_ex_nihilo_age_at_marriage_floor = 17
        # Parameters related to character money -- this is a system I never quite fleshed out (initially
        # characters would be paid for working and would remunerate others for contract work, but I took
        # that out); leaving this in in case it inspires anyone to do something along economic lines
        self.amount_of_money_generated_people_from_outside_town_start_with = 5000

    # People ex nihilo are characters who originate from outside the town (and
    # thus were born outside the simulation, which means they do not have actual parents
    # who were also characters in the simulation); see the PersonExNihilo subclass in
    # person.py for more info
    def person_ex_nihilo_age_given_job_level(self, job_level):
        return 18 + random.randint(2 * job_level, 7 * job_level)

    def chance_person_ex_nihilo_starts_with_family(self, town_pop):
        # The larger the town population, the lower the chance a P.E.N. moves
        # into town with a family
        return (200.0 - town_pop) / 1000.0
