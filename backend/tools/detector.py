"""Imaging detector. THIRD-PARTY / MOCK — no model is trained in this repo.

The default MockDetector returns deterministic fixture findings so the demo is
reproducible and free. To use a real off-the-shelf model, implement another
DetectorBackend (e.g. wrapping a Roboflow/YOLO model) and accept DICOM via pydicom
+ PNG/JPEG via Pillow. Keep the same return shape.
"""
from __future__ import annotations
import json
import pathlib
from abc import ABC, abstractmethod
from pydantic import BaseModel

_FIXTURES = pathlib.Path(__file__).resolve().parent.parent / "fixtures" / "detector_outputs.json"


class Finding(BaseModel):
    tooth_region: str
    label: str
    confidence: float
    bbox: list[float]  # [x, y, w, h]


class RadiographFindings(BaseModel):
    findings: list[Finding]          # at/above confidence threshold
    low_confidence: list[Finding]    # below threshold -> flag for dentist


class DetectorBackend(ABC):
    @abstractmethod
    def analyze(self, image_ref: str) -> list[Finding]:
        ...


class MockDetector(DetectorBackend):
    """Returns fixture findings keyed by image_ref. Clearly a placeholder."""

    def __init__(self, fixtures_path: pathlib.Path = _FIXTURES) -> None:
        self._data = json.loads(pathlib.Path(fixtures_path).read_text())

    def analyze(self, image_ref: str) -> list[Finding]:
        return [Finding(**f) for f in self._data.get(image_ref, [])]


# TODO(claude-code): optional RealDetector(DetectorBackend) wrapping an off-the-shelf model.
