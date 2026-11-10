from pydantic import BaseModel, Field


class HorusecScanDTO(BaseModel):
    project_id: str = Field(
        ..., description="Project ID"
    )

    source: str = Field(
        ..., description="Path to ZIP file containing source code"
    )


