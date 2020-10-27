from dataclasses import dataclass

from PIL import Image


@dataclass
class Name:
    name: str
    title: str
    position_top: bool


@dataclass
class Job:
    name: str
    abbreviation: str
    abbr_job: str  # abbr_job is needed to fetch priority attributes from json file (these  depend on the job name)
    is_base_class: bool


@dataclass
class GrandCompany:
    member_of: bool = False
    name: str = None
    logo: Image = None


@dataclass
class FreeCompany:
    member_of: bool = False
    name: str = None
    tag: str = None
    crest: Image = None


@dataclass
class Collection:
    total: int
    collected: int
    percentage: int


@dataclass
class Character:
    name: Name
    job: Job
    server: str
    portrait: Image
    class_jobs: list
    gear: dict
    attributes: list
    minions: Collection
    mounts: Collection
    grand_company: GrandCompany
    free_company: FreeCompany
