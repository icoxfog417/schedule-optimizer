import numpy as np
import pandas as pd
from pathlib import Path
from ..models.data_models import ConstraintMatrices
from ..utils.time_utils import generate_timeslots, parse_unavailable_times, check_shift_availability


class ConstraintMatrixBuilder:
    """Build all constraint matrices from preprocessed data."""
    
    def __init__(self, interim_dir: Path = Path("data/interim")):
        self.interim_dir = interim_dir
        self.timeslots = generate_timeslots()
    
    def build_all_matrices(self) -> ConstraintMatrices:
        therapists_df = pd.read_csv(self.interim_dir / "normalized_therapists.csv")
        prescriptions_df = pd.read_csv(self.interim_dir / "normalized_prescriptions.csv")
        shifts_df = pd.read_csv(self.interim_dir / "normalized_shifts.csv")
        
        # Get unique patients and therapists
        patient_ids = prescriptions_df['患者ID'].unique().tolist()
        therapist_ids = therapists_df['職員ID'].unique().tolist()
        
        # Build matrices
        patient_avail = self._build_patient_availability(prescriptions_df, patient_ids)
        therapist_avail = self._build_therapist_availability(therapists_df, shifts_df, therapist_ids)
        compatibility = self._build_compatibility(prescriptions_df, therapists_df, patient_ids, therapist_ids)
        requirements = self._build_requirements(prescriptions_df, patient_ids)
        
        return ConstraintMatrices(
            patient_availability=patient_avail,
            therapist_availability=therapist_avail,
            compatibility=compatibility,
            requirements=requirements,
            patient_ids=patient_ids,
            therapist_ids=therapist_ids,
            timeslots=self.timeslots
        )
    
    def _build_patient_availability(self, prescriptions_df: pd.DataFrame, patient_ids: list[str]) -> np.ndarray:
        """Build patient × timeslot availability matrix."""
        matrix = np.ones((len(patient_ids), len(self.timeslots)), dtype=int)
        
        for i, patient_id in enumerate(patient_ids):
            patient = prescriptions_df[prescriptions_df['患者ID'] == patient_id].iloc[0]
            
            unavailable_slots = []
            
            # Parse bathing time
            if pd.notna(patient.get('入浴')):
                unavailable_slots.extend(parse_unavailable_times(patient['入浴']))
            
            # Parse excretion time
            if pd.notna(patient.get('排泄')):
                unavailable_slots.extend(parse_unavailable_times(patient['排泄']))
            
            # Parse other unavailable times
            if pd.notna(patient.get('その他指定時間')):
                unavailable_slots.extend(parse_unavailable_times(patient['その他指定時間']))
            
            # Mark unavailable slots
            for slot in unavailable_slots:
                if slot in self.timeslots:
                    j = self.timeslots.index(slot)
                    matrix[i, j] = 0
        
        return matrix
    
    def _build_therapist_availability(self, therapists_df: pd.DataFrame, shifts_df: pd.DataFrame, therapist_ids: list[str]) -> np.ndarray:
        """Build therapist × timeslot availability matrix."""
        matrix = np.zeros((len(therapist_ids), len(self.timeslots)), dtype=int)
        
        # Create name to ID mapping
        name_to_id = dict(zip(therapists_df['漢字氏名'], therapists_df['職員ID']))
        
        for i, therapist_id in enumerate(therapist_ids):
            # Find therapist name
            therapist_name = therapists_df[therapists_df['職員ID'] == therapist_id]['漢字氏名'].iloc[0]
            
            # Find shift entry
            shift_entry = shifts_df[shifts_df['therapist_name'] == therapist_name]
            if shift_entry.empty:
                continue
            
            availability_code = shift_entry.iloc[0]['availability']
            
            # Check each timeslot
            for j, slot in enumerate(self.timeslots):
                if check_shift_availability(availability_code, slot):
                    matrix[i, j] = 1
        
        return matrix
    
    def _build_compatibility(self, prescriptions_df: pd.DataFrame, therapists_df: pd.DataFrame, patient_ids: list[str], therapist_ids: list[str]) -> np.ndarray:
        """Build patient × therapist compatibility matrix."""
        matrix = np.zeros((len(patient_ids), len(therapist_ids)), dtype=int)
        
        # Create name to ID mapping
        name_to_id = dict(zip(therapists_df['漢字氏名'], therapists_df['職員ID']))
        
        for i, patient_id in enumerate(patient_ids):
            patient = prescriptions_df[prescriptions_df['患者ID'] == patient_id].iloc[0]
            patient_ward = patient['病棟']
            primary_therapist_name = patient.get('担当療法士')
            
            # Get primary therapist info
            primary_therapist_id = name_to_id.get(primary_therapist_name)
            primary_gender = None
            if primary_therapist_id:
                primary_info = therapists_df[therapists_df['職員ID'] == primary_therapist_id]
                if not primary_info.empty:
                    primary_gender = primary_info.iloc[0]['性別']
            
            for j, therapist_id in enumerate(therapist_ids):
                therapist = therapists_df[therapists_df['職員ID'] == therapist_id].iloc[0]
                
                # Primary therapist
                if therapist_id == primary_therapist_id:
                    matrix[i, j] = 100
                    continue
                
                # Check 専従 constraint
                if therapist['専従'] and therapist['担当病棟'] != patient_ward:
                    matrix[i, j] = 0
                    continue
                
                # Calculate compatibility score
                score = 20
                if therapist['担当病棟'] == patient_ward:
                    score += 20
                if primary_gender and therapist['性別'] == primary_gender:
                    score += 40
                
                matrix[i, j] = score
        
        return matrix
    
    def _build_requirements(self, prescriptions_df: pd.DataFrame, patient_ids: list[str]) -> np.ndarray:
        """Build therapy requirements vector."""
        requirements = np.zeros(len(patient_ids), dtype=int)
        
        for i, patient_id in enumerate(patient_ids):
            patient = prescriptions_df[prescriptions_df['患者ID'] == patient_id].iloc[0]
            therapy_type = patient.get('算定区分', '')
            
            if '脳血管疾患' in str(therapy_type):
                requirements[i] = 180
            else:
                requirements[i] = 120
        
        return requirements
    
    def save_matrices(self, matrices: ConstraintMatrices):
        """Save matrices to .npy files."""
        np.save(self.interim_dir / "patient_availability.npy", matrices.patient_availability)
        np.save(self.interim_dir / "therapist_availability.npy", matrices.therapist_availability)
        np.save(self.interim_dir / "compatibility.npy", matrices.compatibility)
        np.save(self.interim_dir / "requirements.npy", matrices.requirements)
        
        # Save metadata
        import json
        metadata = {
            "patient_ids": matrices.patient_ids,
            "therapist_ids": matrices.therapist_ids,
            "timeslots": matrices.timeslots
        }
        with open(self.interim_dir / "matrices_metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)
    
    def load_matrices(self) -> ConstraintMatrices:
        """Load matrices from .npy files."""
        import json
        
        with open(self.interim_dir / "matrices_metadata.json", "r") as f:
            metadata = json.load(f)
        
        return ConstraintMatrices(
            patient_availability=np.load(self.interim_dir / "patient_availability.npy"),
            therapist_availability=np.load(self.interim_dir / "therapist_availability.npy"),
            compatibility=np.load(self.interim_dir / "compatibility.npy"),
            requirements=np.load(self.interim_dir / "requirements.npy"),
            patient_ids=metadata["patient_ids"],
            therapist_ids=metadata["therapist_ids"],
            timeslots=metadata["timeslots"]
        )
