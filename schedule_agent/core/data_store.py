import tempfile
import shutil
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, Any
from contextlib import contextmanager
import json
from ..models.data_models import ConstraintMatrices, Schedule


class DataStore:
    """Unified data storage with session safety and file-specific operations."""
    
    def __init__(self, therapist_file: str = "therapist.csv", 
                 prescription_file: str = "prescription.csv",
                 shift_file: str = "shift.xlsx") -> None:
        self._temp_dir: Optional[Path] = None
        self._session_active: bool = False
        
        # Configurable file names
        self.therapist_file = therapist_file
        self.prescription_file = prescription_file
        self.shift_file = shift_file
    
    # Session Management
    def initialize(self) -> Path:
        """Initialize session only if not already active."""
        if self._session_active and self._temp_dir and self._temp_dir.exists():
            return self._temp_dir
        
        if self._temp_dir:
            self.cleanup()
        
        self._temp_dir = Path(tempfile.mkdtemp(prefix="schedule_agent_"))
        (self._temp_dir / "raw").mkdir()
        (self._temp_dir / "interim").mkdir()
        (self._temp_dir / "processed").mkdir()
        self._session_active = True
        return self._temp_dir
    
    def cleanup(self) -> None:
        """Clean up only if session is active."""
        if self._session_active and self._temp_dir and self._temp_dir.exists():
            shutil.rmtree(self._temp_dir)
            self._temp_dir = None
            self._session_active = False
    
    @contextmanager
    def session(self):
        """Context manager with session state tracking."""
        was_active = self._session_active
        try:
            yield self.initialize()
        finally:
            if not was_active:
                self.cleanup()
    
    # File Input Operations
    def copy_input(self, source_path: str, target_name: Optional[str] = None) -> Path:
        """Copy file from local path to raw directory."""
        if not self._temp_dir:
            raise RuntimeError("Session not initialized")
        
        source = Path(source_path)
        if not source.exists():
            raise FileNotFoundError(f"Input file not found: {source_path}")
        
        dest_name = target_name or source.name
        dest = self._temp_dir / "raw" / dest_name
        shutil.copy2(source, dest)
        return dest
    
    # Convenience methods for key files
    def copy_therapist_file(self, source_path: str) -> Path:
        return self.copy_input(source_path, self.therapist_file)
    
    def copy_prescription_file(self, source_path: str) -> Path:
        return self.copy_input(source_path, self.prescription_file)
    
    def copy_shift_file(self, source_path: str) -> Path:
        return self.copy_input(source_path, self.shift_file)
    
    # Raw Data Loading
    def load_therapists(self) -> pd.DataFrame:
        path = self._temp_dir / "raw" / self.therapist_file
        return pd.read_csv(path, encoding="cp932")
    
    def load_prescriptions(self) -> pd.DataFrame:
        path = self._temp_dir / "raw" / self.prescription_file
        return pd.read_csv(path, encoding="cp932")
    
    def load_shifts(self) -> pd.DataFrame:
        path = self._temp_dir / "raw" / self.shift_file
        return pd.read_excel(path, header=1)
    
    # Normalized Data Operations
    def save_normalized_therapists(self, data: pd.DataFrame) -> None:
        self._save_interim_csv(data, "normalized_therapists.csv")
    
    def load_normalized_therapists(self) -> pd.DataFrame:
        return self._load_interim_csv("normalized_therapists.csv")
    
    def save_normalized_prescriptions(self, data: pd.DataFrame) -> None:
        self._save_interim_csv(data, "normalized_prescriptions.csv")
    
    def load_normalized_prescriptions(self) -> pd.DataFrame:
        return self._load_interim_csv("normalized_prescriptions.csv")
    
    def save_normalized_shifts(self, data: pd.DataFrame) -> None:
        self._save_interim_csv(data, "normalized_shifts.csv")
    
    def load_normalized_shifts(self) -> pd.DataFrame:
        return self._load_interim_csv("normalized_shifts.csv")
    
    # Constraint Matrix Operations
    def save_patient_availability(self, matrix: np.ndarray) -> None:
        self._save_interim_numpy(matrix, "patient_availability.npy")
    
    def load_patient_availability(self) -> np.ndarray:
        return self._load_interim_numpy("patient_availability.npy")
    
    def save_therapist_availability(self, matrix: np.ndarray) -> None:
        self._save_interim_numpy(matrix, "therapist_availability.npy")
    
    def load_therapist_availability(self) -> np.ndarray:
        return self._load_interim_numpy("therapist_availability.npy")
    
    def save_compatibility_matrix(self, matrix: np.ndarray) -> None:
        self._save_interim_numpy(matrix, "compatibility.npy")
    
    def load_compatibility_matrix(self) -> np.ndarray:
        return self._load_interim_numpy("compatibility.npy")
    
    def save_requirements_vector(self, vector: np.ndarray) -> None:
        self._save_interim_numpy(vector, "requirements.npy")
    
    def load_requirements_vector(self) -> np.ndarray:
        return self._load_interim_numpy("requirements.npy")
    
    # Complete matrix operations
    def save_all_matrices(self, matrices: ConstraintMatrices) -> None:
        self.save_patient_availability(matrices.patient_availability)
        self.save_therapist_availability(matrices.therapist_availability)
        self.save_compatibility_matrix(matrices.compatibility)
        self.save_requirements_vector(matrices.requirements)
        
        # Save metadata
        metadata = {
            'patient_ids': matrices.patient_ids,
            'therapist_ids': matrices.therapist_ids,
            'timeslots': matrices.timeslots
        }
        self._save_interim_json(metadata, "matrices_metadata.json")
    
    def load_all_matrices(self) -> ConstraintMatrices:
        metadata = self._load_interim_json("matrices_metadata.json")
        return ConstraintMatrices(
            patient_availability=self.load_patient_availability(),
            therapist_availability=self.load_therapist_availability(),
            compatibility=self.load_compatibility_matrix(),
            requirements=self.load_requirements_vector(),
            patient_ids=metadata['patient_ids'],
            therapist_ids=metadata['therapist_ids'],
            timeslots=metadata['timeslots']
        )
    
    # Schedule Operations
    def save_schedule(self, schedule: Schedule) -> None:
        schedule_df = self._schedule_to_dataframe(schedule)
        self._save_processed_excel(schedule_df, f"schedule_{schedule.date}.xlsx")
    
    def save_error_state(self, error_data: dict) -> None:
        self._save_interim_json(error_data, "error_state.json")
    
    def load_error_state(self) -> dict:
        return self._load_interim_json("error_state.json")
    
    # Private helper methods
    def _save_interim_csv(self, data: pd.DataFrame, filename: str) -> Path:
        path = self._temp_dir / "interim" / filename
        data.to_csv(path, index=False, encoding="utf-8")
        return path
    
    def _save_interim_numpy(self, data: np.ndarray, filename: str) -> Path:
        path = self._temp_dir / "interim" / filename
        np.save(path, data)
        return path
    
    def _save_processed_excel(self, data: pd.DataFrame, filename: str) -> Path:
        path = self._temp_dir / "processed" / filename
        data.to_excel(path, index=False)
        return path
    
    def _save_interim_json(self, data: Any, filename: str) -> Path:
        path = self._temp_dir / "interim" / filename
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return path
    
    def _load_interim_csv(self, filename: str) -> pd.DataFrame:
        path = self._temp_dir / "interim" / filename
        return pd.read_csv(path)
    
    def _load_interim_numpy(self, filename: str) -> np.ndarray:
        path = self._temp_dir / "interim" / filename
        return np.load(path)
    
    def _load_interim_json(self, filename: str) -> dict:
        path = self._temp_dir / "interim" / filename
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _schedule_to_dataframe(self, schedule: Schedule) -> pd.DataFrame:
        """Convert Schedule object to DataFrame for Excel export."""
        data = []
        for assignment in schedule.assignments:
            data.append({
                'Patient ID': assignment.patient_id,
                'Therapist ID': assignment.therapist_id,
                'Time Slot': assignment.timeslot,
                'Duration (min)': assignment.duration_minutes
            })
        return pd.DataFrame(data)
