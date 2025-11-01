from pydantic import BaseModel
from typing import Literal, Optional
from primitives import PowerRoll, Ancestry




class Class(BaseModel):
    pass

class Kit(BaseModel):
    pass

class Background(BaseModel):
    pass

class PlayerAbility(BaseModel): #maybe?
    #should include potency calcuations (p 74)
    pass




class Perk(BaseModel):
    pass

class Complication(BaseModel):
    pass


class PlayerCharacter(BaseModel):
    name: str
    level: int
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