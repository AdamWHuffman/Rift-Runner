from pydantic import BaseModel


class ResetAccountRequest(BaseModel):
    confirm: str
