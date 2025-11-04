from pydantic import BaseModel


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
