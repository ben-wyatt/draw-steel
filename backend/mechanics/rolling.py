"""might get scrapped but this is a test to implement a power roll"""

from models.primitives import PowerRoll, RollOutcome, Characteristic, StatBlock
from typing import List
import random


def roll_power_roll(power_roll: PowerRoll,user_stat_block:StatBlock) -> RollOutcome:
    #get the user's char score for the power roll
    user_char_score = user_stat_block[power_roll.c]

    #roll 2d10, add plus_characteristic to the roll
    roll = roll_2d10() + user_char_score
    if roll <= 11:
        return power_roll.t1
    elif roll <= 16:
        return power_roll.t2
    else:
        return power_roll.t3
    

    #TODO: implement critical hits (free new action)



def roll_2d10() -> int:
    return random.randint(1, 10) + random.randint(1, 10)


if __name__ == "__main__":
    #implement basic power roll from page 74
    tier_one=RollOutcome("3+M damage; push 1")
    tier_two=RollOutcome("6+M damage; push 2")
    tier_three=RollOutcome("10+M damage; push 4")

    print('PowerRoll:')
    power_roll = PowerRoll(t1=tier_one, t2=tier_two, t3=tier_three)
    print(power_roll)