import numpy as np
import pandas as pd
from ..models.data_models import ConstraintMatrices
from ..utils.time_utils import generate_timeslots, parse_unavailable_times, check_shift_availability


class ConstraintMatrixBuilder:
    """Pure matrix building - receives data, returns matrices."""
    
    def __init__(self):
        self.timeslots = generate_timeslots()
    
    def build_matrices(self, therapists: pd.DataFrame, 
                      prescriptions: pd.DataFrame, 
                      shifts: pd.DataFrame) -> ConstraintMatrices:
        """Build all matrices from normalized data."""
        # Get unique patients and therapists
        patient_ids = prescriptions['患者ID'].unique().tolist()
        therapist_ids = therapists['職員ID'].unique().tolist()
        
        return ConstraintMatrices(
            patient_availability=self.build_patient_availability(prescriptions, patient_ids),
            therapist_availability=self.build_therapist_availability(therapists, shifts, therapist_ids),
            compatibility=self.build_compatibility(therapists, prescriptions, patient_ids, therapist_ids),
            requirements=self.build_requirements(prescriptions, patient_ids),
            patient_ids=patient_ids,
            therapist_ids=therapist_ids,
            timeslots=self.timeslots
        )
    
    def build_patient_availability(self, prescriptions: pd.DataFrame, patient_ids: list[str] = None) -> np.ndarray:
        """Build patient × timeslot availability matrix."""
        if patient_ids is None:
            patient_ids = prescriptions['患者ID'].unique().tolist()
        
        matrix = np.ones((len(patient_ids), len(self.timeslots)), dtype=int)
        
        for i, patient_id in enumerate(patient_ids):
            patient = prescriptions[prescriptions['患者ID'] == patient_id].iloc[0]
            
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
    
    def build_therapist_availability(self, therapists: pd.DataFrame, 
                                   shifts: pd.DataFrame, 
                                   therapist_ids: list[str] = None) -> np.ndarray:
        """Build therapist × timeslot availability matrix."""
        if therapist_ids is None:
            therapist_ids = therapists['職員ID'].unique().tolist()
        
        matrix = np.zeros((len(therapist_ids), len(self.timeslots)), dtype=int)
        
        for i, therapist_id in enumerate(therapist_ids):
            # Find therapist name
            therapist_name = therapists[therapists['職員ID'] == therapist_id]['漢字氏名'].iloc[0]
            
            # Find shift entry
            shift_entry = shifts[shifts['therapist_name'] == therapist_name]
            if shift_entry.empty:
                continue
            
            availability_code = shift_entry.iloc[0]['availability']
            
            # Check each timeslot
            for j, slot in enumerate(self.timeslots):
                if check_shift_availability(availability_code, slot):
                    matrix[i, j] = 1
        
        return matrix
    
    def build_compatibility(self, therapists: pd.DataFrame, 
                          prescriptions: pd.DataFrame,
                          patient_ids: list[str] = None,
                          therapist_ids: list[str] = None) -> np.ndarray:
        """Build patient × therapist compatibility matrix."""
        if patient_ids is None:
            patient_ids = prescriptions['患者ID'].unique().tolist()
        if therapist_ids is None:
            therapist_ids = therapists['職員ID'].unique().tolist()
        
        matrix = np.zeros((len(patient_ids), len(therapist_ids)), dtype=int)
        
        # Create name to ID mapping
        name_to_id = dict(zip(therapists['漢字氏名'], therapists['職員ID']))
        
        for i, patient_id in enumerate(patient_ids):
            patient = prescriptions[prescriptions['患者ID'] == patient_id].iloc[0]
            patient_ward = patient['病棟']
            primary_therapist_name = patient.get('担当療法士')
            
            # Get primary therapist info
            primary_therapist_id = name_to_id.get(primary_therapist_name)
            primary_gender = None
            if primary_therapist_id:
                primary_info = therapists[therapists['職員ID'] == primary_therapist_id]
                if not primary_info.empty:
                    primary_gender = primary_info.iloc[0]['性別']
            
            for j, therapist_id in enumerate(therapist_ids):
                therapist = therapists[therapists['職員ID'] == therapist_id].iloc[0]
                
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
    
    def build_requirements(self, prescriptions: pd.DataFrame, patient_ids: list[str] = None) -> np.ndarray:
        """Build therapy requirements vector."""
        if patient_ids is None:
            patient_ids = prescriptions['患者ID'].unique().tolist()
        
        requirements = np.zeros(len(patient_ids), dtype=int)
        
        for i, patient_id in enumerate(patient_ids):
            patient = prescriptions[prescriptions['患者ID'] == patient_id].iloc[0]
            therapy_type = patient.get('算定区分', '')
            
            if '脳血管疾患' in str(therapy_type):
                requirements[i] = 180
            else:
                requirements[i] = 120
        
        return requirements
