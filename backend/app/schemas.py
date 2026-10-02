from pydantic import BaseModel, Field


class Finding(BaseModel):
    name: str
    value: float
    unit: str = ""
    low: float
    high: float
    status: str  # "above" | "below" | "within"
    flag: str = ""


class Term(BaseModel):
    term: str
    meaning: str
    source_line: str = ""
    verified: bool = False


class Explanation(BaseModel):
    doc_type: str = "unknown"
    summary: str
    key_points: list[str] = Field(default_factory=list)
    terms: list[Term] = Field(default_factory=list)
    ask_professional: list[str] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)


class HindiVersion(BaseModel):
    summary: str
    key_points: list[str] = Field(default_factory=list)
    ask_professional: list[str] = Field(default_factory=list)
    term_meanings: list[str] = Field(default_factory=list)

class TermsOnly(BaseModel):
    doc_type: str = "unknown"
    terms: list[Term] = Field(default_factory=list)

class TermMeaningsHi(BaseModel):
    term_meanings: list[str] = Field(default_factory=list)