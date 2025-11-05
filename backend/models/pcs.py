from typing import List, Optional

from pydantic import BaseModel, Field

from backend.models.primitives import (
    AbilityKeyword,
    ActionType,
    Characteristic,
    Condition,
    DamageType,
    ResourceType,
    StatBlock,
)


class CharacterRollOutcome(BaseModel):
    """Determined effect from a power roll
    Examples:
     - "3+M holy damage; push 1; if A<0, prone"
     - "7+A poison damage; if I<2, dazed (save ends)"
    """

    base_damage: int = 0
    plus_damage_characteristic: Optional[Characteristic] = None
    damage_type: Optional[DamageType] = None

    effect: Optional[str] = Field(
        default=None,
        description="plain text description of ability effect, such as 'push 2",
    )
    potency_value: Optional[int] = Field(
        default=None,
        description="some outcomes include a potency, such as 'A<0, prone'",
    )
    potency_characteristic: Optional[Characteristic] = Field(
        default=None,
        description="characteristic of the potency, such as 'might' or 'agility', written as a single letter",
    )
    condition: Optional[Condition] = None
    save_ends: Optional[bool] = Field(
        default=None, description="specified phrase sometimes included in effects"
    )


class CharacterPowerRoll(BaseModel):
    """outcomes for each tier of a power roll"""

    plus_roll_characteristic: Optional[Characteristic] = None
    tier_one: CharacterRollOutcome  # ≤11
    tier_two: CharacterRollOutcome  # 12–16
    tier_three: CharacterRollOutcome  # ≥17


class CharacterAbility(BaseModel):
    name: str
    flavor_text: Optional[str] = None
    keywords: Optional[List[AbilityKeyword]] = None
    resource_cost: int = 0
    resource_type: Optional[ResourceType] = None
    action_type: ActionType
    distance: str
    target: str
    power_roll: Optional[CharacterPowerRoll] = None
    effect: Optional[str] = None


class Class(BaseModel):
    pass


class Kit(BaseModel):
    pass


class Background(BaseModel):
    pass


class Perk(BaseModel):
    pass


class Complication(BaseModel):
    pass


class Ancestry(BaseModel):
    pass


class PlayerCharacter(BaseModel):
    name: str
    level: int
    stats: StatBlock
    player_class: Class
    kit: Kit
    background: Background
    ancestry: Ancestry
    perks: list[Perk]
    complications: list[Complication]
    # abilities: list[Ability]
    pass


if __name__ == "__main__":
    pass
