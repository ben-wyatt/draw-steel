from pydantic import BaseModel


class HeroesPageClassification(BaseModel):
    detailed_image_descriptions: list[str]
    includes_flavor_text: bool  # maybe not?
    includes_table: bool
    page_is_only_image: bool


# need other ideas here
