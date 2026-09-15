from pydantic import BaseModel, ConfigDict

class ProvinceResponse(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)
