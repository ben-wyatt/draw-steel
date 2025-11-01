from enum import Enum

from pydantic import BaseModel

from models.primitives import Ability, DamageType, MovementType, Size, StatBlock


class Keyword(str, Enum):
    ABYSSAL = "abyssal"
    ACCURSED = "accursed"
    ANIMAL = "animal"
    BEAST = "beast"
    CONSTRUCT = "construct"
    DRAGON = "dragon"
    ELEMENTAL = "elemental"
    FEY = "fey"
    GIANT = "giant"
    HORROR = "horror"
    HUMANOID = "humanoid"
    INFERNAL = "infernal"
    OOZE = "ooze"
    PLANT = "plant"
    SWARM = "swarm"
    UNDEAD = "undead"
    OTHER = "other"


class CreatureOrganization(str, Enum):
    MINION = "minion"
    HORDE = "horde"
    PLATOON = "platoon"
    LEADER = "leader"
    ELITE = "elite"
    SOLO = "solo"


class CreatureRole(str, Enum):
    ABUSHER = "ambusher"
    ARTILLERY = "artillery"
    BRUTE = "brute"
    CONTROLLER = "controller"
    DEFENDER = "defender"
    HARRYER = "harrier"
    HEXER = "hexer"
    MOUNT = "mount"
    SUPPORT = "support"


# class MaliceFeature
# class VillainAction


class Trait(BaseModel):
    name: str
    description: str


class Monster(BaseModel):
    name: str
    keyword: Keyword
    level: int
    org: CreatureOrganization
    role: CreatureRole
    ev: str

    size: Size
    speed: int
    stamina: int
    stability: int
    free_strike: int
    immunities: list[DamageType] | None = None
    weaknesses: list[DamageType] | None = None
    movement: list[MovementType] | None = None
    stats: StatBlock
    signature_ability: Ability
    other_abilities: list[Ability] | None = None
    traits: list[Trait] | None = None
    # malice_features: list[MaliceFeature,None]
    # villain_actions: list[VillainAction,None]

    # other abilities???

    # malice??

    # villain actions
