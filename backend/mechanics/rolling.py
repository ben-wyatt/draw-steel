"""might get scrapped but this is a test to implement a power roll"""

import random


def roll_2d10() -> int:
    return random.randint(1, 10) + random.randint(1, 10)


if __name__ == "__main__":
    print(roll_2d10())
