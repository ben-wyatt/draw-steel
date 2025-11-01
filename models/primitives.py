"""
contains core game mechanics data structures
"""

import re
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


# complete
class Characteristic(str, Enum):
    MIGHT = "might"
    AGILITY = "agility"
    REASON = "reason"
    INTUITION = "intuition"
    PRESENCE = "presence"

    # handle the shorthand
    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            v = value.strip().lower()
            alias = {
                "M".lower(): "might",
                "A".lower(): "agility",
                "R".lower(): "reason",
                "I".lower(): "intuition",
                "P".lower(): "presence",
            }.get(v)
            if alias is not None:
                return cls(alias)
        return None


# complete
class StatBlock(BaseModel):
    """values for each characteristic"""

    might: int = Field(..., validation_alias="M")
    agility: int = Field(..., validation_alias="A")
    reason: int = Field(..., validation_alias="R")
    intuition: int = Field(..., validation_alias="I")
    presence: int = Field(..., validation_alias="P")

    def __getitem__(self, characteristic: Characteristic) -> int:
        """Allow dictionary-style access with Characteristic enum"""
        char_name = (
            characteristic.value
            if isinstance(characteristic, Characteristic)
            else characteristic
        )
        return getattr(self, char_name)

    def __setitem__(self, characteristic: Characteristic, value: int) -> None:
        """Allow dictionary-style assignment with Characteristic enum"""
        char_name = (
            characteristic.value
            if isinstance(characteristic, Characteristic)
            else characteristic
        )
        setattr(self, char_name, value)


class ActionType(str, Enum):
    MAIN_ACTION = "main action"
    MANEUVER = "maneuver"
    MOVE_ACTION = "move action"
    TRIGGER_ACTION = "trigger action"


class Keyword(str, Enum):
    """attack type keywords"""

    AREA = "area"
    CHARGE = "charge"
    MAGIC = "magic"
    MELEE = "melee"
    PSIONIC = "psionic"
    RANGED = "ranged"
    STRIKE = "strike"
    WEAPON = "weapon"


class DamageType(str, Enum):
    ACID = "acid"
    COLD = "cold"
    FIRE = "fire"
    HOLY = "holy"
    LIGHTNING = "lightning"
    POISON = "poison"
    PSYCHIC = "psychic"
    SONIC = "sonic"
    CORRUPTION = "corruption"


class Size(str, Enum):
    ONET = "1T"
    ONES = "1S"
    ONEM = "1M"
    ONEL = "1L"
    TWO = "2"
    THREE = "3"
    FOUR = "4"
    FIVE = "5"


class MovementType(str, Enum):
    CLIMB = "climb"
    SWIM = "swim"
    FLY = "fly"
    HOVER = "hover"
    BURROW = "burrow"
    TELEPORT = "teleport"


# not sure how to structure this
class Potency(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    # described on page 74
    # if target's char score is less than potency_value, then they suffer effect
    potency_value: int = Field(..., alias="p_v", validation_alias="p_v")
    characteristic: Characteristic = Field(..., alias="c", validation_alias="c")


class Effect(BaseModel):
    """defines ability effect and optional potency trigger"""

    # described on page 74
    effect: str = Field(..., alias="e")
    potency: Optional[Potency] = Field(default=None, alias="p")

    # allow creating from a string like "push 1" or "A<2 prone"
    @classmethod
    def _coerce_str_to_data(cls, text: str):
        text = text.strip()
        potency_match = re.match(
            r"^(?P<char>[A-Za-z]+)\s*<\s*(?P<val>\d+)\s*[ ,]+(?P<eff>.+)$", text
        )
        if potency_match:
            char_text = potency_match.group("char")
            potency_value = int(potency_match.group("val"))
            eff_text = potency_match.group("eff").strip()
            return {
                "e": eff_text,
                "p": {
                    "c": char_text,
                    "p_v": potency_value,
                },
            }
        return {"e": text}

    @model_validator(mode="before")
    @classmethod
    def _parse_from_string(cls, data):
        if isinstance(data, str):
            return cls._coerce_str_to_data(data)
        return data

    def __init__(self, *args, **kwargs):
        if args and len(args) == 1 and isinstance(args[0], str):
            kwargs = {**self.__class__._coerce_str_to_data(args[0]), **kwargs}
            super().__init__(**kwargs)
            return
        super().__init__(**kwargs)

    def to_text(self) -> str:
        """Return compact effect text, e.g., 'A<1 prone' or 'push 1'."""
        if self.potency is None:
            return self.effect
        mapping = {
            Characteristic.MIGHT: "M",
            Characteristic.AGILITY: "A",
            Characteristic.REASON: "R",
            Characteristic.INTUITION: "I",
            Characteristic.PRESENCE: "P",
        }
        letter = mapping.get(self.potency.characteristic, "?")
        return f"{letter}<{self.potency.potency_value} {self.effect}".strip()


class Damage(BaseModel):
    """damage integer value, optional char addition, optional damage type"""

    # described on page 277
    base_damage: int = Field(..., alias="d")
    plus_characteristic: Optional[Characteristic] = Field(default=None, alias="c")
    damage_type: Optional[DamageType] = None

    # allow creating from a string like "3+M holy damage" or "7 damage"
    @classmethod
    def _coerce_str_to_data(cls, text: str):
        raw = text.strip()
        # pattern: number, optional + characteristic, optional damage type, optional word 'damage'
        dmg_regex = re.compile(
            r"^\s*(?P<base>\d+)\s*(?:\+\s*(?P<char>(?:[mM]|[aA]|[rR]|[iI]|[pP]|might|agility|reason|intuition|presence)))?\s*(?P<dtype>acid|cold|fire|holy|lightning|poison|psychic|sonic|corruption)?\s*(?:damage)?\s*$",
            re.IGNORECASE,
        )
        m = dmg_regex.match(raw)
        if not m:
            # if only a number present
            only_num = re.match(r"^\s*(\d+)\s*$", raw)
            if only_num:
                return {"d": int(only_num.group(1))}
            return {"d": raw}  # let validation raise later if truly invalid
        base = int(m.group("base"))
        char = m.group("char")
        dtype = m.group("dtype")
        return {
            "d": base,
            "c": char if char is not None else None,
            "damage_type": dtype.lower() if dtype is not None else None,
        }

    @model_validator(mode="before")
    @classmethod
    def _parse_from_string(cls, data):
        if isinstance(data, str):
            return cls._coerce_str_to_data(data)
        return data

    def __init__(self, *args, **kwargs):
        if args and len(args) == 1 and isinstance(args[0], str):
            kwargs = {**self.__class__._coerce_str_to_data(args[0]), **kwargs}
            super().__init__(**kwargs)
            return
        super().__init__(**kwargs)

    def to_text(self) -> str:
        """Human-readable damage string like '3+M holy damage' or '7 damage'."""

        def char_letter(ch: Optional[Characteristic]) -> Optional[str]:
            if ch is None:
                return None
            mapping = {
                Characteristic.MIGHT: "M",
                Characteristic.AGILITY: "A",
                Characteristic.REASON: "R",
                Characteristic.INTUITION: "I",
                Characteristic.PRESENCE: "P",
            }
            return mapping.get(ch)

        letter = char_letter(self.plus_characteristic)
        suffix = f"+{letter}" if letter else ""
        dtype = f" {self.damage_type.value}" if self.damage_type else ""
        return f"{self.base_damage}{suffix}{dtype} damage".strip()


class RollOutcome(BaseModel):
    """combine damage and effect"""

    # described on page 74
    # example from text would be: 3+M holy damage; push 1
    # or: 7+A damage; A<2 prone (for potency effect)
    damage: Damage = Field(..., alias="d")
    effect: Optional[List[Effect]] = Field(default=None, alias="e")

    # allow creating from a string like "3+M damage; push 1; A<2 prone"
    @classmethod
    def _coerce_str_to_data(cls, text: str):
        parts = [p.strip() for p in text.split(";")]
        parts = [p for p in parts if p]
        if not parts:
            return {"d": text}
        dmg_text = parts[0]
        eff_parts = parts[1:] if len(parts) > 1 else []
        return {
            "d": dmg_text,
            "e": eff_parts if eff_parts else None,
        }

    @model_validator(mode="before")
    @classmethod
    def _parse_from_string(cls, data):
        if isinstance(data, str):
            return cls._coerce_str_to_data(data)
        # coerce shorthand forms on dict input, e.g., single effect string
        if isinstance(data, dict):
            new_data = dict(data)
            if "e" in new_data and isinstance(new_data["e"], str):
                new_data["e"] = [new_data["e"]]
            if "effect" in new_data and isinstance(new_data["effect"], str):
                new_data["effect"] = [new_data["effect"]]
            return new_data
        return data

    def __init__(self, *args, **kwargs):
        if args and len(args) == 1 and isinstance(args[0], str):
            kwargs = {**self.__class__._coerce_str_to_data(args[0]), **kwargs}
            super().__init__(**kwargs)
            return
        super().__init__(**kwargs)

    def to_text(self) -> str:
        parts: List[str] = [self.damage.to_text()]
        if self.effect:
            for eff in self.effect:
                parts.append(eff.to_text())
        return "; ".join(parts)


class Consequence(BaseModel):
    pass


class Target(BaseModel):
    # TODO: implement Target
    pass


class PowerRoll(BaseModel):
    """outcomes for each tier of a power roll"""

    plus_characteristic: Optional[Characteristic] = Field(default=None, alias="c")
    tier_one: RollOutcome = Field(..., alias="t1")  # ≤11
    tier_two: RollOutcome = Field(..., alias="t2")  # 12–16
    tier_three: RollOutcome = Field(..., alias="t3")  # ≥17

    # dot-access alias for plus_characteristic
    @property
    def c(self) -> Optional[Characteristic]:
        return self.plus_characteristic

    @c.setter
    def c(self, value: Optional[Characteristic]) -> None:
        if value is None:
            self.plus_characteristic = None
        elif isinstance(value, Characteristic):
            self.plus_characteristic = value
        else:
            self.plus_characteristic = Characteristic(value)

    # dot-access aliases for tiers
    @property
    def t1(self) -> RollOutcome:
        return self.tier_one

    @t1.setter
    def t1(self, value: RollOutcome) -> None:
        self.tier_one = value

    @property
    def t2(self) -> RollOutcome:
        return self.tier_two

    @t2.setter
    def t2(self, value: RollOutcome) -> None:
        self.tier_two = value

    @property
    def t3(self) -> RollOutcome:
        return self.tier_three

    @t3.setter
    def t3(self, value: RollOutcome) -> None:
        self.tier_three = value

    def to_text(self) -> str:
        mapping = {
            Characteristic.MIGHT: "M",
            Characteristic.AGILITY: "A",
            Characteristic.REASON: "R",
            Characteristic.INTUITION: "I",
            Characteristic.PRESENCE: "P",
        }
        plus = (
            f" (+{mapping[self.plus_characteristic]})"
            if self.plus_characteristic
            else ""
        )
        lines = [f"Power Roll{plus}:"]
        lines.append(f"  1: {self.tier_one.to_text()}")
        lines.append(f"  2: {self.tier_two.to_text()}")
        lines.append(f"  3: {self.tier_three.to_text()}")
        return "\n".join(lines)


class Ability(BaseModel):
    """full ability definition: name, description, keywords, action type, target, power roll, effect"""

    model_config = ConfigDict(populate_by_name=True)
    name: str = Field(..., alias="n")
    description: Optional[str] = Field(default=None, alias="d")
    keywords: List[Keyword] = Field(default_factory=list, alias="k")
    action_type: ActionType = Field(..., alias="a")
    target: str = Field(
        ..., alias="t"
    )  # TODO: implement Target, "one creature or object"
    power_roll: PowerRoll = Field(..., alias="p")
    effect: Optional[Effect] = Field(default=None, alias="e")

    def pretty(self) -> str:
        """Human-readable multi-line representation for console output."""
        lines: List[str] = [self.name]
        # Description (if provided)
        if self.description:
            lines.append(self.description)
        # Meta
        kw = ", ".join(k.value for k in self.keywords) if self.keywords else ""
        if kw:
            lines.append(f"Keywords: {kw}")
        lines.append(f"Action: {self.action_type.value}")
        lines.append(f"Target: {self.target}")
        # Optional effect text
        if self.effect is not None:
            lines.append(f"Effect: {self.effect.to_text()}")
        # Power roll
        lines.append(self.power_roll.to_text())
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.pretty()


def show_examples():
    print("Potency:")
    potency = Potency(characteristic="might", potency_value=2)
    # or:
    potency = Potency(c="M", p_v=2)
    print(potency)

    print("Effect:")
    effect = Effect(e="prone")
    print(effect)

    print("effect with potency:")
    effect = Effect(e="prone", p=potency)
    print(effect)

    print("damage:")
    damage = Damage(c="m", d=3)
    print(damage)

    print("damage from string:")
    damage2 = Damage("3+M holy damage")
    print(damage2)

    print("RollOutcome:")
    roll_outcome = RollOutcome(d=damage, e=[effect])
    print(roll_outcome)

    print("RollOutcome from string:")
    ro_str = RollOutcome("3+M damage; push 1")
    print(ro_str)

    # implement basic power roll from page 74
    tier_one = RollOutcome("3+M damage; push 1")
    tier_two = RollOutcome("6+M damage; push 2")
    tier_three = RollOutcome("10+M damage; push 4")

    print("PowerRoll:")
    power_roll = PowerRoll(t1=tier_one, t2=tier_two, t3=tier_three)
    print(power_roll)

    # demonstrate c alias get/set
    print("PowerRoll c alias (before set):", power_roll.c)
    power_roll.c = "M"
    print(
        'PowerRoll c alias (after set to "M"): plus_characteristic=',
        power_roll.plus_characteristic,
        " c=",
        power_roll.c,
    )

    # implement intuition power roll from page 74
    print("\nIntuition power roll:")
    intution_roll = PowerRoll(
        t1=RollOutcome("3+I holy damage; A<0, prone"),
        t2=RollOutcome("6+I holy damage; A<1, prone"),
        t3=RollOutcome("9+I holy damage; A<2, prone"),
    )
    print(intution_roll)

    print("\n\nAbility:")
    power_roll = PowerRoll(
        t1=RollOutcome("3+M holy damage"),
        t2=RollOutcome("5+M holy damage"),
        t3=RollOutcome("8+M holy damage"),
        c="M",
    )
    ability = Ability(
        name="Your Allies Cannot Save You!",
        description="Your magic strike turns your foe's guilt into a burst of holy power.",
        keywords=[Keyword.MELEE, Keyword.STRIKE, Keyword.WEAPON],
        action_type=ActionType.MAIN_ACTION,
        target="one creature or object",
        power_roll=power_roll,
        effect=Effect(
            e="Each enemy adjacent to the target is pushed away from the target up to a number of squares equal to your Presence score."
        ),
    )
    print(ability)


if __name__ == "__main__":
    show_examples()


"""

"""
