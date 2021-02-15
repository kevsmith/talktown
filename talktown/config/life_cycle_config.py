class LifeCycleConfig:
    """Configuration parameters related to character life cycles (birth, life, death, sex, aging, etc.)."""

    def __init__(self):
        """Initialize Life Cycle Configuration"""
        # Sex
        self.chance_sexual_protection_does_not_work = 0.01
        # Aging
        self.age_when_people_start_graying = 48
        self.age_when_men_start_balding = 48
        self.chance_someones_hair_goes_gray_or_white = 0.02
        self.chance_someones_loses_their_hair_some_year = 0.02
        # Death
        self.chance_someone_dies = 0.125
        # Life phases
        self.age_children_start_going_to_school = 5
        self.chance_employed_adult_will_move_out_of_parents = 0.1

    # Pregnancy
    def chance_of_conception(self, female_age):
        # Decreases exponentially with age (source missing)
        return max(female_age / 10000., (100 - ((female_age ** 1.98) / 20.)) / 100)

    def chance_a_widow_remarries(self, years_married):
        return 1.0 / (int(years_married) + 4)

    def age_people_start_working(self, year):
        if year < 1920:
            return 14
        if year < 1960:
            return 16
        else:
            return 18

    def chance_mother_of_young_children_stays_home(self, year):
        # Determines the chance the mother of a new child will intend to
        # enter the workforce (versus staying home), given a partner who
        # is in the workforce; this changes over time according to results
        # of a study of census data by ancestry.com
        if year < 1910:
            return 0.07
        if year < 1920:
            return 0.08
        if year < 1930:
            return 0.09
        if year < 1941:
            return 0.11
        if year < 1950:
            return 0.16
        if year < 1960:
            return 0.28
        if year < 1970:
            return 0.40
        if year < 1980:
            return 0.54
        if year < 1990:
            return 0.67
        if year < 2000:
            return 0.64
        return 0.71
