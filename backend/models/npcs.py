from typing import Literal

from models.primitives import DamageType, MonsterAbility, MovementType, Size
from pydantic import BaseModel

MonsterKeyword = Literal[
    "abyssal",
    "accursed",
    "animal",
    "beast",
    "construct",
    "dragon",
    "elemental",
    "fey",
    "giant",
    "horror",
    "humanoid",
    "infernal",
    "ooze",
    "plant",
    "swarm",
    "undead",
    "other",
]

CreatureOrganization = Literal[
    "minion",
    "horde",
    "platoon",
    "leader",
    "elite",
    "solo",
]

CreatureRole = Literal[
    "ambusher",
    "artillery",
    "brute",
    "controller",
    "defender",
    "harrier",
    "hexer",
    "mount",
    "support",
]


# class MaliceFeature
# class VillainAction


class Trait(BaseModel):
    name: str
    description: str


class Monster(BaseModel):
    name: str
    keyword: MonsterKeyword
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
    # stats:
    signature_ability: MonsterAbility
    other_abilities: list[MonsterAbility] | None = None
    traits: list[Trait] | None = None
    # malice_features: list[MaliceFeature,None]
    # villain_actions: list[VillainAction,None]

    # other abilities???

    # malice??

    # villain actions
