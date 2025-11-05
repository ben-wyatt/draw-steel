"""
contains core game mechanics data structures
"""

from typing import Literal, Optional

from pydantic import BaseModel

Characteristic = Literal["might", "agility", "reason", "intuition", "presence"]
ActionType = Literal[
    "main action", "maneuver", "move action", "triggered action", "none"
]
AbilityKeyword = Literal[
    "area",
    "charge",
    "magic",
    "melee",
    "psionic",
    "ranged",
    "strike",
    "weapon",
]
DamageType = Literal[
    "acid",
    "cold",
    "fire",
    "holy",
    "lightning",
    "poison",
    "psychic",
    "sonic",
    "corruption",
]
ResourceType = Literal[
    "malice",
    "wrath",
    "piety",
    "essence",
    "ferocity",
    "discipline",
    "insight",
    "focus",
    "clarity",
    "drama",
]
AreaOfEffect = Literal["aura", "burst", "cube", "line", "wall"]
Size = Literal["1T", "1S", "1M", "1L", "2", "3", "4", "5"]
Target = Literal[
    "creature", "object", "enemy", "ally", "self"
]  # unused because of combinatorial explosion
MovementType = Literal["climb", "swim", "fly", "hover", "burrow", "teleport"]
StructuredEffect = Literal["pull", "push", "slide"]
Condition = Literal[
    "bleeding",
    "dazed",
    "frightened",
    "grabbed",
    "prone",
    "restrained",
    "slowed",
    "taunted",
    "weakened",
]

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
    "solo",
]

"""\
Many abilities and other effects impose conditions and unique statuses on targets. \
But creatures sometimes get a chance to resist such effects. After all, a monster \
with a high Might should be harder to knock prone most of the time than a creature \
lacking in that characteristic.

Ability effects that have a potency are applied to a target only if the effect's \
potency value is higher than the target's indicated characteristic score. The \
characteristic a target uses to resist a potency is based on the ability used, \
while the value of the potency for your hero's abilities is based on one of your \
characteristics and determined by your class.

Your character has a weak, an average, and a strong potency value, as follows:
 - Your weak potency value is equal to your highest characteristic score - 2.
 - Your average potency value is equal to your highest characteristic score - 1.
 - Your strong potency value is equal to your highest characteristic score.

In abilities and other effects, a potency always appears as the single-letter \
abbreviation for the target's characteristic: Might, Agility, \
Reason, Intuition, or Presence. That characteristic is followed \
by the potency value—weak, average, or strong. \
"""


class StatBlock(BaseModel):
    might: int
    agility: int
    reason: int
    intuition: int
    presence: int


class SimpleEffect(BaseModel):
    name: str
    description: str


class MonstersPageClassification(BaseModel):
    detailed_image_descriptions: list[str]
    number_of_monster_stat_blocks: int
    names_of_monster_stat_blocks: Optional[list[str]]
    has_partial_monster_stat_blocks: bool
    includes_malice_features: bool
    includes_flavor_text: bool
    includes_table: bool
    includes_villain_action: bool
    page_is_only_image: bool
