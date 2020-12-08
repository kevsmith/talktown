class SalienceConfig:
    """Configuration parameters related to how salient characters are to one another."""
    # Salience increment from a single social interaction

    def __init__(self):
        self.salience_increment_for_social_interaction = 0.1
        self.salience_increment_from_relationship_change = {
            "acquaintance": 0.5,
            "former neighbor": 0.75,
            "former coworker": 1.0,
            "neighbor": 1.25,
            "coworker": 1.5,
            "descendant": 1.5,
            "ancestor": 1.5,
            "extended family": 1.5,
            "friend": 2,
            "enemy": 2,
            "immediate family": 2,
            "love interest": 3,
            "best friend": 1,  # Remember: this is a boost on top of the value for friend
            "worst enemy": 1,
            "significant other": 5,
            "self": float("inf"),
        }

    def salience_job_level_boost(self, job_level):
        # People with higher job levels are most salient to the residents of their towns
        return job_level * 0.35
