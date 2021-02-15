class TownGenerationDetailsConfig:
    """Configuration parameters related to details of the generated towns.

    Attributes
    ----------
    chance_town_gets_named_for_a_settler: float

    chance_avenue_gets_numbered_name: float

    chance_street_gets_numbered_name: float
    """
    def __init__(self):
        self.chance_town_gets_named_for_a_settler = 0.3
        self.chance_avenue_gets_numbered_name = 0.0
        self.chance_street_gets_numbered_name = 0.8
        self.min_tracts = 3
