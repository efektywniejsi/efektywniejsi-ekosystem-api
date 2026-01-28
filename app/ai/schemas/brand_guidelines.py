from pydantic import BaseModel


class BrandGuidelinesResponse(BaseModel):
    tone: str = ""
    style: str = ""
    target_audience: str = ""
    unique_selling_proposition: str = ""
    language: str = "pl"
    avoid_phrases: str = ""
    preferred_phrases: str = ""
    company_description: str = ""
    additional_instructions: str = ""

    model_config = {"from_attributes": True}


class BrandGuidelinesUpdate(BaseModel):
    tone: str = ""
    style: str = ""
    target_audience: str = ""
    unique_selling_proposition: str = ""
    language: str = "pl"
    avoid_phrases: str = ""
    preferred_phrases: str = ""
    company_description: str = ""
    additional_instructions: str = ""
