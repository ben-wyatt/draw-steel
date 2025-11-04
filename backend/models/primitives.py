"""
contains core game mechanics data structures
"""

from typing import List, Literal, Optional

from pydantic import BaseModel

Characteristic = Literal["might", "agility", "reason", "intuition", "presence"]
ActionType = Literal["main action", "maneuver", "move action", "trigger action"]
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
Target = Literal["creature", "object", "enemy", "ally", "self"]
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


class RollOutcome(BaseModel):
    """Determined effect from a power roll
    Examples:
     - "3+M holy damage; push 1; if A<0, prone"
     - "7+A poison damage; if I<2, dazed (save ends)"
    """

    base_damage: int = 0
    plus_damage_characteristic: Optional[Characteristic] = None
    damage_type: Optional[DamageType] = None

    effect: Optional[str] = None
    structured_effect: Optional[List[StructuredEffect]] = None
    potency_value: Optional[int] = None
    potency_characteristic: Optional[Characteristic] = None
    condition: Optional[Condition] = None
    save_ends: Optional[bool] = None


class PowerRoll(BaseModel):
    """outcomes for each tier of a power roll"""

    plus_roll_characteristic: Optional[Characteristic] = None
    tier_one: RollOutcome  # ≤11
    tier_two: RollOutcome  # 12–16
    tier_three: RollOutcome  # ≥17


class MonsterAbility(BaseModel):
    """Monster ability
    Example:
     name: Rip and Tear
     flavor_text: none
     plus_roll_amount: 2
     keywords: charge, melee, strike, weapon
     resource_cost: 0 #in this case: malice
     ActionType: main action
     distance: melee 1
     target: one creature or object
     <=11: 1 damage; push 1
     11-16: 2 damage; push 2; m<0, prone
     17+: 3 damage; push 2; m<2, prone
     effect: none
    """

    name: str
    flavor_text: Optional[str] = None
    keywords: Optional[List[AbilityKeyword]] = None
    plus_roll_amount: int = 0
    resource_cost: int = 0
    action_type: ActionType
    distance: str
    target: Target
    power_roll: Optional[PowerRoll] = None
    effect: Optional[str] = None


class CharacterAbility(BaseModel):
    name: str
    flavor_text: Optional[str] = None
    keywords: Optional[List[AbilityKeyword]] = None
    resource_cost: int = 0
    resource_type: Optional[ResourceType] = None
    action_type: ActionType
    distance: str
    target: Target
    power_roll: Optional[PowerRoll] = None
    effect: Optional[str] = None
