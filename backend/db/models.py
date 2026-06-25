"""SQLModel persistence layer (backs backend/tools/patients.py).

Works with SQLite (dev, default) or Postgres via DATABASE_URL. Two tables are
enough for the demo: Patient and Procedure (CDT-coded). Prior radiographic
findings are *derived* from restorative procedures in patients.py rather than
stored separately — keeps the schema small and the data grounded in real rows.
"""
from typing import Optional

from sqlmodel import SQLModel, Field, create_engine, Session

from backend.config import DATABASE_URL

# check_same_thread=False so the SQLite connection is usable across the
# threads FastMCP runs sync tools in; harmless for Postgres (arg ignored).
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, echo=False, connect_args=_connect_args)


class Patient(SQLModel, table=True):
    patient_id: str = Field(primary_key=True)
    name: str
    last_visit: Optional[str] = None
    allergies: str = ""  # comma-separated for simplicity


class Procedure(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    patient_id: str = Field(foreign_key="patient.patient_id", index=True)
    code: str          # CDT / ADA code, e.g. "D2392"
    desc: str = ""
    tooth: str = ""
    date: str = ""


def init_db() -> None:
    """Create tables if they don't exist."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Session:
    """Open a new Session bound to the engine (caller manages the context)."""
    return Session(engine)
