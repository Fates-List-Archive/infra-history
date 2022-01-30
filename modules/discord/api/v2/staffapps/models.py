from pydantic import BaseModel

from ..base_models import APIResponse

class StaffAppQuestion(BaseModel):
    """
    A question for a staff application.
    """
    id: str
    title: str
    question: str
    answer: str | None = None
    minlength: int | None = 30
    maxlength: int | None = 2000

class StaffAppCreate(BaseModel):
    """
    A request to create a new staff application.

    Must be a dict of question id to the answer given
    """
    answers: dict[str, str]

class StaffAppQuestions(BaseModel):
    """
    A list of questions for a staff application.
    """
    questions: list[StaffAppQuestion]