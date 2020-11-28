import pathlib
import json
from queue import Queue
import random

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

ALL_CONFIG_FILES = [
    AppearanceConfig, ArtifactConfig, BasicConfig, BusinessesConfig, LifeCycleConfig, MarriageConfig,
    MiscellaneousCharacterConfig, MiscellaneousCharacterDecisionMakingConfig, PersonalityConfig,
    RoutineConfig, SalienceConfig, SocialSimConfig, StoryRecognitionConfig, TownGenerationDetailsConfig
]

class Config:
    """A class that aggregates all author-defined configuration parameters."""

    def __init__(self, config_json=None):
        self.settings = {}
        # This short script will slurp up all the parameters included in the various configuration
        # files -- specified as attributes on the classes defined in those files -- and set those
        # as attributes on the Config class defined above; this class will then be set as an attribute
        # on the Simulation object constructed by Simulation.__init__(), which will make all of the
        # config parameters accessible through 'Simulation.config'
        for config_file in ALL_CONFIG_FILES:
            for parameter, value in config_file.__dict__.items():
                self.settings[parameter] = value
                self.__dict__[parameter] = value

        if config_json is not None:
            self.load(config_json)

    def get(self, key):
        """Retrieve configuration value"""
        return self.settings[key]

    def load(self, filepath):
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

                if 'basic' in config_data:

                    if 'seed' in config_data['basic']:
                        self.settings['seed'] = config_data['basic']['seed']
                        self.__dict__['seed'] = config_data['basic']['seed']
