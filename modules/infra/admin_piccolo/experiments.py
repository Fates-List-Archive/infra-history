import enum
from pydantic import BaseModel

class Experiments(enum.IntEnum):
    Unknown = 0
    GetRolesSelector = 1
    LynxExperimentRolloutView = 2

class ExpStatus(enum.IntEnum):
    TODO = 0
    IN_PROGRESS = 1
    DONE = 2

class ExperimentProps(BaseModel):
    description: str
    status: ExpStatus

exp_props = {
    "Unknown": ExperimentProps(description="A test experiment", status=ExpStatus.DONE),
    "GetRolesSelector": ExperimentProps(description="Role selector on site experiment", status=ExpStatus.TODO),
    "LynxExperimentRolloutView": ExperimentProps(description="Lynx rollout view experiment", status=ExpStatus.IN_PROGRESS),
}