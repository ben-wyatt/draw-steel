Great start. The trick is to keep a small, stable core and push the irregular bits into either:
- simple, typed “terms” (damage, push, condition, move, resource change), and
- a rules_text escape hatch when something is too bespoke.

Below is a compact, extensible shape that matches the stat block without getting deeply nested. It uses:
- discriminated unions for effect terms,
- a lightweight gating clause for potency checks, and
- a tiered roll model (t1/t2/t3) like your examples.

Notes:
- For occasional nesting (a gate that applies a list of effects), Pydantic handles recursion with postponed annotations; call model_rebuild or use from __future__ import annotations to avoid forward-ref headaches [studyraid.com](https://app.studyraid.com/en/read/15002/518520/creating-nested-models-for-complex-data), [python.useinstructor.com](https://python.useinstructor.com/examples/recursive).  
- If you accept string input like "3+M damage; push 1", add a custom parser via Annotated+BeforeValidator to keep your public API ergonomic [getorchestra.io](https://getorchestra.io/guides/pydantic-custom-parsers-writing-custom-parsers-for-complex-field-types-in-fastapi).  
- FastAPI/Pydantic nested models work cleanly with these patterns and validation aliases you’re already using [fastapi.tiangolo.com](https://fastapi.tiangolo.com/tutorial/body-nested-models/).  
- To sanity‑check your design, generate an ER diagram (erdantic) from your Pydantic models [erdantic.drivendata.org](https://erdantic.drivendata.org/stable/examples/pydantic/).

Code skeleton (Pydantic v2)

```python
from __future__ import annotations

from enum import Enum
from typing import List, Optional, Union, Tuple, Set, Literal
from typing_extensions import Annotated
from pydantic import BaseModel, Field, ConfigDict
from pydantic.functional_validators import BeforeValidator

# ——— vocab you already have (kept) ———

class Characteristic(str, Enum):
    MIGHT = "might"
    AGILITY = "agility"
    REASON = "reason"
    INTUITION = "intuition"
    PRESENCE = "presence"
    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            v = value.strip().lower()
            alias = {"m": "might", "a":"agility", "r":"reason", "i":"intuition", "p":"presence"}.get(v)
            if alias:
                return cls(alias)

class StatBlock(BaseModel):
    might: int = Field(..., validation_alias='M')
    agility: int = Field(..., validation_alias='A')
    reason: int = Field(..., validation_alias='R')
    intuition: int = Field(..., validation_alias='I')
    presence: int = Field(..., validation_alias='P')

    def __getitem__(self, c: Characteristic) -> int:
        name = c.value if isinstance(c, Characteristic) else c
        return getattr(self, name)
    def __setitem__(self, c: Characteristic, value: int) -> None:
        name = c.value if isinstance(c, Characteristic) else c
        setattr(self, name, value)

class ActionType(str, Enum):
    MAIN_ACTION = "main action"
    MANEUVER = "maneuver"
    MOVE_ACTION = "move action"
    TRIGGER_ACTION = "trigger action"

class Keyword(str, Enum):
    AREA = "area"
    CHARGE = "charge"
    MAGIC = "magic"
    MELEE = "melee"
    PSIONIC = "psionic"
    RANGED = "ranged"
    STRIKE = "strike"
    WEAPON = "weapon"

# ——— core building blocks ———

class DamageType(str, Enum):
    PHYSICAL = "physical"
    HOLY = "holy"
    CORRUPTION = "corruption"
    TRUE = "true"

class Comparator(str, Enum):
    LT = "<"
    LE = "<="
    GT = ">"
    GE = ">="
    EQ = "=="

class Potency(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    potency_value: int = Field(..., validation_alias='p_v')
    characteristic: Characteristic = Field(..., validation_alias='c')
    op: Comparator = Comparator.LT  # defaults to "if target's score < potency_value"

class EffectText(BaseModel):
    kind: Literal["text"] = "text"
    text: str

class DamageFormula(BaseModel):
    base: int
    plus_characteristic: Optional[Characteristic] = Field(default=None, alias='c')
    type: Optional[DamageType] = None

# Optional ergonomic string parser, e.g. "3+M holy"
def _parse_damage(v):
    if isinstance(v, DamageFormula):
        return v
    if isinstance(v, str):
        # very small parser: "<base>[+<char>] [<type>]"
        # e.g. "3+M holy"
        parts = v.strip().split()
        base_plus = parts[0]
        dmg_type = parts[1] if len(parts) > 1 else None
        if '+' in base_plus:
            base_s, char_s = base_plus.split('+', 1)
            return DamageFormula(base=int(base_s), plus_characteristic=Characteristic(char_s), type=DamageType(dmg_type) if dmg_type else None)
        else:
            return DamageFormula(base=int(base_plus), type=DamageType(dmg_type) if dmg_type else None)
    raise ValueError("Invalid damage formula")

DamageFormulaOrStr = Annotated[DamageFormula, BeforeValidator(_parse_damage)]

# Effect terms (discriminated union keeps it flat and composable)
class DamageEffect(BaseModel):
    kind: Literal["damage"] = "damage"
    formula: DamageFormulaOrStr

class PushEffect(BaseModel):
    kind: Literal["push"] = "push"
    squares: int

class MoveEffect(BaseModel):
    kind: Literal["move"] = "move"
    squares: int
    straight: bool = False
    forced: bool = True

class ConditionEffect(BaseModel):
    kind: Literal["condition"] = "condition"
    name: str  # e.g., "prone", "grabbed", "weakened", "restrained", "dazed"
    save_ends: bool = True

class ResourceChange(BaseModel):
    kind: Literal["resource"] = "resource"
    name: str      # e.g., "malice"
    delta: int     # + or -

# A gate that applies effects only if a potency check passes (keeps nesting shallow)
class GateEffect(BaseModel):
    kind: Literal["gate"] = "gate"
    potency: Potency
    apply: List["EffectTerm"] = Field(default_factory=list)

EffectTerm = Annotated[
    Union[DamageEffect, PushEffect, MoveEffect, ConditionEffect, ResourceChange, GateEffect, EffectText],
    Field(discriminator="kind")
]
GateEffect.model_rebuild()

class RollOutcome(BaseModel):
    # Keep it simple: a flat list of terms; gates allow conditional branches
    terms: List[EffectTerm] = Field(default_factory=list)

# Your sample-friendly power roll
class PowerRoll(BaseModel):
    t1: RollOutcome
    t2: RollOutcome
    t3: RollOutcome
    plus_characteristic: Optional[Characteristic] = Field(default=None, alias="c")

# ——— Targeting and geometry ———

class TargetQuantifier(str, Enum):
    ONE = "one"
    TWO = "two"
    EACH = "each"
    SELF = "self"

class Allegiance(str, Enum):
    ENEMY = "enemy"
    CREATURE = "creature"
    OBJECT = "object"
    SELF = "self"

class TargetSpec(BaseModel):
    quantifier: TargetQuantifier
    of: List[Allegiance]

class Shape(str, Enum):
    LINE = "line"
    CUBE = "cube"
    BURST = "burst"
    SELF = "self"

class AreaSpec(BaseModel):
    shape: Shape
    size: Tuple[int, ...]  # e.g., (4, 1) for 4x1 line, or (4,) for 4-cube
    within: Optional[int] = None  # origin within N

class RangeSpec(BaseModel):
    # lightweight, keeps melee/ranged values readable without special rules
    text: str  # e.g., "melee 2", "within 10"

class ActionCost(BaseModel):
    malice: int = 0
    special: Optional[str] = None  # e.g., "Villain Action 2" or recharge text

class TriggerSpec(BaseModel):
    event: str  # e.g., "takes damage", "start of turn"
    condition: Optional[str] = None

class Ability(BaseModel):
    name: str
    description: Optional[str] = None
    keywords: Set[Keyword] = set()
    action_type: ActionType
    cost: Optional[ActionCost] = None
    target: Optional[TargetSpec] = None
    area: Optional[AreaSpec] = None
    range: Optional[RangeSpec] = None
    power_roll: Optional[PowerRoll] = None
    # A simple, always-on effect (for abilities that don't roll)
    effects: List[EffectTerm] = Field(default_factory=list)
    # Triggered actions and villain action typing
    trigger: Optional[TriggerSpec] = None
    villain_rank: Optional[int] = None  # 1/2/3 when it's a Villain Action
    # Fallback text when the rules are too bespoke to model
    rules_text: Optional[str] = None

# ——— Monster ———

class DefenseBlock(BaseModel):
    stamina: int
    strain: int
    free_strike: int

class Monster(BaseModel):
    name: str
    level: int
    role: str  # e.g., "Solo"
    ev: int
    types: List[str]  # e.g., ["Construct", "Undead"]
    size: int
    speed: int
    movement_modes: List[str] = Field(default_factory=list)  # e.g., ["Burrow"]
    stats: StatBlock
    defenses: DefenseBlock
    immunity: Optional[str] = None
    weakness: Optional[str] = None
    traits: List[Ability] = Field(default_factory=list)      # passives like "Solo Monster", "Bladed Body"
    actions: List[Ability] = Field(default_factory=list)     # mains/maneuvers
    triggered: List[Ability] = Field(default_factory=list)   # reactions/triggered
    villain_actions: List[Ability] = Field(default_factory=list)
```

Why this stays manageable
- Depth: You rarely exceed two levels (Action -> RollOutcome -> EffectTerm). Conditional branches use a single GateEffect node instead of arbitrary trees.
- Escape hatches: rules_text on Ability and EffectText in terms let you store exact wording when you don’t want to over-model.
- Ergonomic inputs: DamageFormula accepts strings via a BeforeValidator so authors can keep writing "3+M holy" while your code operates on structured fields [getorchestra.io](https://getorchestra.io/guides/pydantic-custom-parsers-writing-custom-parsers-for-complex-field-types-in-fastapi).
- Recursion: Only GateEffect is recursive, and Pydantic’s postponed annotations/model_rebuild make that safe [python.useinstructor.com](https://python.useinstructor.com/examples/recursive), [app.studyraid.com](https://app.studyraid.com/en/read/15002/518520/creating-nested-models-for-complex-data).
- FastAPI-friendly: These are standard nested models with discriminators, so request/response validation and docs work fine [fastapi.tiangolo.com](https://fastapi.tiangolo.com/tutorial/body-nested-models/).

Examples mapping from your strings

```python
# Equivalent to: "3+M damage; push 1"
tier1 = RollOutcome(terms=[
    DamageEffect(formula="3+M"),
    PushEffect(squares=1),
])

# With potency gate: "A<0, prone"
tier1.terms.append(
    GateEffect(
        potency=Potency(c="A", p_v=0, op=Comparator.LT),
        apply=[ConditionEffect(name="prone", save_ends=False)]
    )
)

# A power roll with three tiers like your examples
power_roll = PowerRoll(
    t1=tier1,
    t2=RollOutcome(terms=[DamageEffect(formula="6+M"), PushEffect(squares=2)]),
    t3=RollOutcome(terms=[DamageEffect(formula="10+M"), PushEffect(squares=4)]),
    c="M"
)

# An ability resembling "ImpalE 3 Malice ... 4x1 line within 1"
impale = Ability(
    name="Impale",
    action_type=ActionType.MAIN_ACTION,
    keywords={Keyword.MELEE, Keyword.WEAPON, Keyword.AREA},
    cost=ActionCost(malice=3),
    area=AreaSpec(shape=Shape.LINE, size=(4, 1), within=1),
    target=TargetSpec(quantifier=TargetQuantifier.EACH, of=[Allegiance.CREATURE]),
    power_roll=PowerRoll(
        t1=RollOutcome(terms=[DamageEffect(formula=DamageFormula(base=1, type=DamageType.CORRUPTION)),
                              ConditionEffect(name="impaled", save_ends=True)]),
        t2=RollOutcome(terms=[DamageEffect(formula="10+M corruption"),
                              ConditionEffect(name="impaled", save_ends=True)]),
        t3=RollOutcome(terms=[DamageEffect(formula="14+M corruption"),
                              ConditionEffect(name="impaled", save_ends=True)]),
        c="M"
    ),
    rules_text="Impaled creature is restrained and bleeding; moves with the hoarder. Up to three creatures can be impaled."
)

# A triggered ability like "Armor of Corpses — Trigger: takes damage"
armor_of_corpses = Ability(
    name="Armor of Corpses",
    action_type=ActionType.TRIGGER_ACTION,
    trigger=TriggerSpec(event="takes damage"),
    effects=[ResourceChange(name="malice", delta=-1)],
    rules_text="If one or more creatures are impaled, reduce malice cost by 1 and an impaled creature takes half the damage."
)
```

Practical tips
- Keep only these “term” kinds unless you really need another: damage, push/pull, move, condition, resource, gate, text. Most stat blocks fit.
- Prefer RangeSpec.text and rules_text for edge cases instead of inventing new structure.
- Add string parsers only where they buy authoring speed (damage formulas, simple “push N”).
- Use discriminators (`kind`) to keep unions robust and JSON-serializable.
- Visualize relationships with erdantic to ensure the model isn’t ballooning [erdantic.drivendata.org](https://erdantic.drivendata.org/stable/examples/pydantic/).

If you share one of the full abilities from the image verbatim, I can map it 1:1 into this shape so you can see the fidelity and where I’d lean on rules_text.