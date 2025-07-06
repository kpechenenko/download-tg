import typing as tp

import pydantic
import yaml


class User(pydantic.BaseModel):
    """
    Configuration for user authentication details.
    """
    api_id: str
    api_hash: str
    phone_number: str
    session_file: str


class App(pydantic.BaseModel):
    """
    Configuration for running the app.
    """
    download_at_same_time_size: int
    log_file: str
    download_video: bool
    download_audio: bool


class Search(pydantic.BaseModel):
    """
    Configuration for search parameters.
    """
    channel_id: int
    key_words: tp.Optional[tp.Set[str]] = None


class Storage(pydantic.BaseModel):
    """
    Configuration for storage settings.
    """
    sqlite_file: str
    video_dir: str
    audio_dir: str


class Config(pydantic.BaseModel):
    """
    Main configuration class aggregating all sub-configurations.
    """
    user: User
    search: Search
    storage: Storage
    app: App

    @staticmethod
    def load_from_yaml(filename: str) -> 'Config':
        """
       Load configuration from a YAML file.
       :param filename: Path to the YAML configuration file.
       :return: An instance of the Config class populated with the YAML data.
       """
        with open(filename) as file:
            data = yaml.safe_load(file)
            cfg = Config(**data)
        return cfg
