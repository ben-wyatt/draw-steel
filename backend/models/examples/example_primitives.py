from backend.models.primitives import (
    CharacterAbility,
    MonsterAbility,
    PowerRoll,
    RollOutcome,
)

"""
Monster Ability:
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


# Monster Ability: Rip and Tear
rip_and_tear = MonsterAbility(
    name="Rip and Tear",
    flavor_text=None,
    keywords=["charge", "melee", "strike", "weapon"],
    plus_roll_amount=2,
    resource_cost=0,
    action_type="main action",
    distance="melee 1",
    target="creature",
    power_roll=PowerRoll(
        tier_one=RollOutcome(
            base_damage=1,
            structured_effect=["push"],
            effect="push 1",
        ),
        tier_two=RollOutcome(
            base_damage=2,
            structured_effect=["push"],
            potency_value=0,
            potency_characteristic="might",
            condition="prone",
            effect="push 2; if M<0, prone",
        ),
        tier_three=RollOutcome(
            base_damage=3,
            structured_effect=["push"],
            potency_value=2,
            potency_characteristic="might",
            condition="prone",
            effect="push 2; if M<2, prone",
        ),
    ),
    effect=None,
)

"""
Character Ability:
name: Harsh Critic
flavor_text: Just one bad review will ruin their day.
resource_cost: 3 # in this case: drama
keywords: magic, melee, ranged, strike
ActionType: main action
distance: melee 1 or ranged 10
target: one creature or object
<=11: 7 + P sonic damage
11-16: 10 + P sonic damage
17+: 13 + P sonic damage
effect: The first time the target uses an ability 
 before the start of your next turn, any effects from
 the ability's tier outcomes other than damage are 
 negated for all targets. Ability effects that always
 happen regardless of the power roll work as usual.
"""


# Character Ability: Harsh Critic
harsh_critic = CharacterAbility(
    name="Harsh Critic",
    flavor_text="Just one bad review will ruin their day.",
    keywords=["magic", "melee", "ranged", "strike"],
    resource_cost=3,
    resource_type="drama",
    action_type="main action",
    distance="melee 1 or ranged 10",
    target="creature",
    power_roll=PowerRoll(
        plus_roll_characteristic="presence",
        tier_one=RollOutcome(
            base_damage=7,
            plus_damage_characteristic="presence",
            damage_type="sonic",
        ),
        tier_two=RollOutcome(
            base_damage=10,
            plus_damage_characteristic="presence",
            damage_type="sonic",
        ),
        tier_three=RollOutcome(
            base_damage=13,
            plus_damage_characteristic="presence",
            damage_type="sonic",
        ),
    ),
    effect="The first time the target uses an ability before the start of your next turn, any effects from the ability's tier outcomes other than damage are negated for all targets. Ability effects that always happen regardless of the power roll work as usual.",
)

print("Monster Ability:")
print(rip_and_tear)
print("\n" + "=" * 80 + "\n")
print("Character Ability:")
print(harsh_critic)
