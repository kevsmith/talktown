import math


class SocialSimConfig:
    """Configuration parameters related to character social interactions.

    Key Terms
    ---------
    "Charge": platonic affinity

    "Spark": romantic affinity

    Attributes
    ----------

    chance_of_interaction_extroversion_component_floor: float
        Floor value when determining interaction with extroversion

    chance_of_interaction_extroversion_component_cap: float
        Ceiling value when determining interaction with extroversion

    chance_of_interaction_openness_component_floor: float
        Floor value when determining interaction with openness

    chance_of_interaction_openness_component_cap: float
        Ceiling value when determining interaction with openness

    chance_of_interaction_friendship_component: float
        Boost to the chance of interaction if the other
        person is a friend

    chance_of_interaction_best_friend_component: float
        Boost to the chance of interaction if the other
        person is a best friend

    chance_someone_instigates_interaction_with_other_person_floor: float
        Floor value when determining if a person starts
        interactiing with another person

    chance_someone_instigates_interaction_with_other_person_cap: float
        Ceiling value when determining if a person starts
        interactiing with another person
    """

    def __init__(self):

        # The chance someone will spark up an interaction with someone else has to do with their 'extroversion'
        # and 'openness to experience' personality exponents, as well as how well they already know that person
        self.chance_of_interaction_extroversion_component_floor = 0.05
        self.chance_of_interaction_extroversion_component_cap = 0.7
        self.chance_of_interaction_openness_component_floor = 0.01
        self.chance_of_interaction_openness_component_cap = 0.7
        self.chance_of_interaction_friendship_component = 0.5  # Boost to chance if person is a friend
        self.chance_of_interaction_best_friend_component = 0.2  # Boost to chance if person is a best friend
        self.chance_someone_instigates_interaction_with_other_person_floor = 0.05
        self.chance_someone_instigates_interaction_with_other_person_cap = 0.95

        # These values help to determine the charge increment for an Acquaintance/Friendship/Enmity
        # and get multiplied by its owner's extroversion and subject's agreeableness, respectively;
        # the resulting value then gets added to the two people's compatibility, which will be on
        # a scale from -1 to 1, and so these represent the proportion, relative to compatibility,
        # that these values will play in determining charge increments
        self.owner_extroversion_boost_to_charge_multiplier = 0.25
        self.subject_agreeableness_boost_to_charge_multiplier = 0.25
        self.charge_intensity_reduction_due_to_sex_difference = 0.5

        # These values help determine the initial spark increment for an Acquaintance; the accumulation
        # of spark represents a person's romantic attraction toward the acquaintance. Values here
        # come from source [5]: the first set are dependent on the acquaintance's personality, and the
        # second on the person themself's personality (i.e., generally how likely they are to be attracted
        # to other people based on their own personality alone)
        #       Affected by own personality        #
        self.self_openness_boost_to_spark_multiplier = {
            'm': 0.2, 'f': 0.55
        }
        self.self_conscientiousness_boost_to_spark_multiplier = {
            'm': -0.09, 'f': -0.1
        }
        self.self_extroversion_boost_to_spark_multiplier = {
            'm': 0.13, 'f': 0.43
        }
        self.self_agreeableness_boost_to_spark_multiplier = {
            'm': 0.3, 'f': 0.19
        }
        self.self_neuroticism_boost_to_spark_multiplier = {
            'm': 0.01, 'f': 0.05
        }
        #       Affected by partner personality     #
        self.openness_boost_to_spark_multiplier = {
            'm': -0.39, 'f': -0.37
        }
        self.conscientiousness_boost_to_spark_multiplier = {
            'm': 0.5, 'f': 0.38
        }
        self.extroversion_boost_to_spark_multiplier = {
            'm': 0.5, 'f': 0.49
        }
        self.agreeableness_boost_to_spark_multiplier = {
            'm': 0.52, 'f': 0.31
        }
        self.neuroticism_boost_to_spark_multiplier = {
            'm': -0.36, 'f': -0.63
        }

        # Age characters start developing romantic feelings
        self.age_characters_start_developing_romantic_feelings = 13
        # Spark decay rate
        self.spark_decay_rate = 0.8
        # Once the charge of an Acquaintance exceeds these thresholds, a Friendship or Enmity
        # (whichever is appropriate, of course) object will get instantiated
        self.charge_threshold_friendship = 15.0
        self.charge_threshold_enmity = -10.0
        # Thresholds for liking or disliking people
        self.charge_threshold_for_liking_someone = 10
        self.charge_threshold_for_disliking_someone = -8
        self.charge_threshold_for_hating_someone = -20


    def normalize_raw_charge(self, n_simulated_timesteps, raw_charge):
        """
        This function normalizes charge values so that 100 represents the charge one typically would
        have for their best friend (charge values may eclipse 100, however) and -100 represents the charge
        one would typically have for their worst enemies (values may also fall below -100); this was
        tuned empirically, and it's pretty hairy -- I don't recommend altering it
        """
        if raw_charge >= 0:
            return int(round((500.0/n_simulated_timesteps) * (raw_charge**0.568)))
        else:
            return -(int(round((500.0/n_simulated_timesteps) * (abs(raw_charge)**0.73))))


    def determine_how_age_difference_reduces_charge_intensity(self, age1, age2):
        """
        This makes people with large age differences more indifferent about potentially
        becoming friends or enemies
        """
        return max(0.05, 1 - (abs(math.sqrt(age1) - math.sqrt(age2)) / 4.5))


    def determine_how_job_level_difference_reduces_charge_intensity(self, job_level1, job_level2):
        """This makes people with job-level differences more indifferent about potentially
        becoming friends or enemies
        """
        return max(0.05, 1 - (abs(math.sqrt(job_level1) - math.sqrt(job_level2))))


    def normalize_raw_spark(self, n_simulated_timesteps, raw_spark):
        """normalizes spark values

        100 represents the spark one typically would have for their love interest
        (spark values may eclipse 100, however) and -100 represents the
        spark one would typically have for the person they are least romantically attracted to (values
        may also fall below -100); this was tuned empirically, and it's pretty hairy -- I don't recommend
        altering it
        """
        if raw_spark >= 0:
            return int(round((500.0/n_simulated_timesteps) * (raw_spark**0.765)))
        else:
            return -(int(round((500.0/n_simulated_timesteps) * (abs(raw_spark)**0.765))))


    def determine_how_age_difference_reduces_spark_increment(self, age1, age2):
        """ How does age difference affect developing romantic feelings

        People with larger age gaps are less likely to develop romantic feelings
        (missing source)
        """
        return max(0.01, 1 - (abs(math.sqrt(age1) - math.sqrt(age2)) / 1.5))


    def determine_how_job_level_difference_reduces_spark_increment(self, job_level1, job_level2):
        """
        This makes people with job-level differences less likely to develop romantic feelings
        for one another (missing source)
        """
        return max(0.05, 1 - (abs(math.sqrt(job_level1) - math.sqrt(job_level2))))
