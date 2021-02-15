class StoryRecognitionConfig:
    """Configuration parameters related to story recognition.

    Attributes
    ----------
    spark_threshold_for_being_captivated: int
        For finding Love triangles

    minimum_number_of_disliked_people_to_be_misanthrope: int
        For finding Misanthropes
    """

    def __init__(self):
        self.spark_threshold_for_being_captivated = 20
        self.minimum_number_of_disliked_people_to_be_misanthrope = 10
