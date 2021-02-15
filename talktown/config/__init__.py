import pathlib
import json
from queue import Queue

from .appearance_config import AppearanceConfig
from .artifact_config import ArtifactConfig
from .basic_config import BasicConfig
from .businesses_config import BusinessesConfig
from .life_cycle_config import LifeCycleConfig
from .marriage_config import MarriageConfig
from .misc_character_config import MiscellaneousCharacterConfig
from .misc_decision_making_config import MiscellaneousCharacterDecisionMakingConfig
from .personality_config import PersonalityConfig
from .routine_config import RoutineConfig
from .salience_config import SalienceConfig
from .social_sim_config import SocialSimConfig
from .story_recognition_config import StoryRecognitionConfig
from .town_generation_details_config import TownGenerationDetailsConfig

class Config:
    """A class that aggregates all author-defined configuration parameters."""

    def __init__(self):
        """Instantiate config and subconfigs"""
        self.appearance = AppearanceConfig()
        self.artifact = ArtifactConfig()
        self.basic = BasicConfig()
        self.business = BusinessesConfig()
        self.life_cycle = LifeCycleConfig()
        self.marriage = MarriageConfig()
        self.misc_character = MiscellaneousCharacterConfig()
        self.misc_character_decision_making = MiscellaneousCharacterDecisionMakingConfig()
        self.personality = PersonalityConfig()
        self.routine = RoutineConfig()
        self.salience = SalienceConfig()
        self.social_sim = SocialSimConfig()
        self.story_recognition = StoryRecognitionConfig()
        self.town_generation = TownGenerationDetailsConfig()

    def load_json(self, filepath):
        """Loads configuration from JSON file(s)"""
        # Other config files referenced by this one
        referenced_files = Queue()

        referenced_files.put(filepath)

        # Run BFS on the file references
        while not referenced_files.empty():

            filename = referenced_files.get()

            if not isinstance(filename, pathlib.Path):
                filename = pathlib.Path(filename)

            if not str(filename).lower().endswith('.json'):
                raise ValueError("Given file {} needs to have a .json extension".format(filename))

            with open(filename, 'r') as f:
                config_data = json.load(f)

                if 'references' in config_data:
                    [referenced_files.put(ref) for ref in config_data['references']]

                # Overwrite default parameters
                # Basic config parameters are at the root level of the file
                # others are within nested dictionaries

                subconfigurations = vars(self)

                # Loop through the keys of the root level
                for json_subconfig_key in config_data.keys():
                    # Check if the key corresponds to any of this
                    # Config's subconfiguration variables
                    if json_subconfig_key in subconfigurations.keys():

                        subconfig = vars(self)[json_subconfig_key]

                        # Loop through the keys of the nested json configuration
                        # objcet and overwite values in the Python Config's
                        # subconfiguration if the names match
                        for key in config_data[json_subconfig_key].keys():
                            if key in vars(subconfig):
                                subconfig.__dict__[key] = config_data[json_subconfig_key][key]
