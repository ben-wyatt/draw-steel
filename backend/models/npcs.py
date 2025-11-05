from typing import List, Optional

from pydantic import BaseModel

from backend.models.primitives import (
    AbilityKeyword,
    ActionType,
    Characteristic,
    Condition,
    CreatureOrganization,
    CreatureRole,
    DamageType,
    MonsterKeyword,
    MovementType,
    Size,
    StatBlock,
    StructuredEffect,
)


class MonsterRollOutcome(BaseModel):
    damage: int = 0
    damage_type: Optional[DamageType] = None
    structured_effect: Optional[List[StructuredEffect]] = None
    effect: Optional[str] = None
    potency_value: Optional[int] = None
    potency_characteristic: Optional[Characteristic] = None
    condition: Optional[Condition] = None
    save_ends: Optional[bool] = None


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


class MonsterAbility(BaseModel):
    name: str
    flavor_text: Optional[str] = None
    keywords: Optional[List[AbilityKeyword]] = None
    plus_roll_amount: int = 0
    required_malice_cost: int = 0
    action_type: ActionType
    distance_type_and_amount: str
    target: str
    trigger_description: Optional[str] = None
    less_than_11_outcome: Optional[str] = None
    eleven_to_sixteen_outcome: Optional[str] = None
    seventeen_and_above_outcome: Optional[str] = None
    effect: Optional[str] = None


class MaliceFeature(BaseModel):
    name: str
    effect: str
    malice_cost: int


# we will do a separate LLM parse for Malice Features
class MaliceFeatures(BaseModel):
    name: str
    description: str
    malice_features: list[MaliceFeature]


class Trait(BaseModel):
    name: str
    description: str


class Monster(BaseModel):
    name: str
    level: int
    org: CreatureOrganization
    role: CreatureRole
    keywords: list[MonsterKeyword]
    ev: int
    size: Size
    speed: int
    stamina: int
    stability: int
    free_strike: int
    immunities: list[str] | None = None
    weaknesses: list[str] | None = None
    movement: list[MovementType] | None = None
    stats: StatBlock
    solo_monster_end_effect: str | None = None
    solo_monster_solo_turns: str | None = None
    signature_ability: MonsterAbility
    other_abilities: list[MonsterAbility] | None = None
    traits: list[Trait] | None = None
    villain_actions: list[MonsterAbility] | None = None


class Monsters(BaseModel):
    monsters: list[Monster]


"""
nesting depth:
Monster
 MonsterAbility
  MonsterPowerRoll
   MonsterRollOutcome
"""
