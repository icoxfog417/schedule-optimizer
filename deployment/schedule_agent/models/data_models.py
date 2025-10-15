from dataclasses import dataclass
from typing import Optional
import numpy as np


@dataclass
class Therapist:
    therapist_id: str
    name: str
    gender: str
    exclusive: bool  # 専従
    ward: str  # 担当病棟


@dataclass
class Prescription:
    patient_id: str
    ward: str
    assigned_therapist: str
    therapy_type: str  # 算定区分
    bathing_time: Optional[str]
    excretion_time: Optional[str]
    other_unavailable: Optional[str]


@dataclass
class ShiftEntry:
    therapist_name: str
    date: str
    availability: str  # ○, AN, PN


@dataclass
class TimeSlot:
    index: int
    time_str: str  # "09:00-09:20"


@dataclass
class Assignment:
    patient_id: str
    therapist_id: str
    timeslot: str
    duration_minutes: int = 20


@dataclass
class Schedule:
    assignments: list[Assignment]
    date: str
    unscheduled_patients: list[str]


@dataclass
class ConstraintMatrices:
    patient_availability: np.ndarray  # (P, 18)
    therapist_availability: np.ndarray  # (Th, 18)
    compatibility: np.ndarray  # (P, Th)
    requirements: np.ndarray  # (P,)
    patient_ids: list[str]
    therapist_ids: list[str]
    timeslots: list[str]


@dataclass
class ValidationResult:
    is_valid: bool
    errors: list[str]


class InfeasibleScheduleError(Exception):
    def __init__(self, message: str, patient_id: str = None, details: dict = None):
        super().__init__(message)
        self.patient_id = patient_id
        self.details = details or {}
