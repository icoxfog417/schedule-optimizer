import pytest
import numpy as np
from pathlib import Path
from schedule_agent.core.constraints_builder import ConstraintMatrixBuilder
from schedule_agent.core.data_store import DataStore
from schedule_agent.core.preprocessor import DataNormalizer


class TestConstraintMatrixBuilder:
    """Test constraint matrix generation"""
    
    def test_build_patient_availability_matrix(self):
        """TC2.1: Patient availability matrix with blocked slots"""
        test_data_dir = Path(__file__).parent / "data"
        
        store = DataStore()
        with store.session():
            store.copy_prescription_file(str(test_data_dir / "test_constraints_prescription.csv"))
            prescriptions = store.load_prescriptions()
        
        normalizer = DataNormalizer()
        normalized_prescriptions = normalizer.normalize_prescriptions(prescriptions)
        
        builder = ConstraintMatrixBuilder()
        matrix = builder.build_patient_availability(normalized_prescriptions)
        
        assert matrix.shape[0] == 2  # 2 patients
        assert matrix.shape[1] == 18  # 18 timeslots
        
        # Matrix should be mostly 1s (available) with some 0s (blocked)
        assert np.sum(matrix) < matrix.size  # Some slots should be blocked
    
    def test_build_therapist_availability_matrix(self):
        """TC2.2: Therapist availability with shift codes"""
        test_data_dir = Path(__file__).parent / "data"
        
        store = DataStore()
        with store.session():
            store.copy_therapist_file(str(test_data_dir / "test_constraints_therapist.csv"))
            store.copy_shift_file(str(test_data_dir / "test_constraints_shift.xlsx"))
            therapists = store.load_therapists()
            shifts = store.load_shifts()
        
        normalizer = DataNormalizer()
        normalized_therapists = normalizer.normalize_therapists(therapists)
        normalized_shifts = normalizer.normalize_shifts(shifts, "2025-10-01")  # Use day 1
        
        builder = ConstraintMatrixBuilder()
        matrix = builder.build_therapist_availability(normalized_therapists, normalized_shifts)
        
        assert matrix.shape[0] == 2  # 2 therapists
        assert matrix.shape[1] == 18  # 18 timeslots
    
    def test_build_compatibility_matrix(self):
        """TC2.3: Compatibility scoring"""
        test_data_dir = Path(__file__).parent / "data"
        
        store = DataStore()
        with store.session():
            store.copy_therapist_file(str(test_data_dir / "test_constraints_therapist.csv"))
            store.copy_prescription_file(str(test_data_dir / "test_constraints_prescription.csv"))
            therapists = store.load_therapists()
            prescriptions = store.load_prescriptions()
        
        normalizer = DataNormalizer()
        normalized_therapists = normalizer.normalize_therapists(therapists)
        normalized_prescriptions = normalizer.normalize_prescriptions(prescriptions)
        
        builder = ConstraintMatrixBuilder()
        matrix = builder.build_compatibility(normalized_therapists, normalized_prescriptions)
        
        assert matrix.shape == (2, 2)  # 2 patients, 2 therapists
        
        # Primary therapist assignments should have score 100
        assert np.max(matrix) == 100
    
    def test_exclusive_ward_constraint(self):
        """TC2.4: Exclusive ward constraint blocks incompatible assignments"""
        test_data_dir = Path(__file__).parent / "data"
        
        store = DataStore()
        with store.session():
            store.copy_therapist_file(str(test_data_dir / "test_constraints_therapist_exclusive.csv"))
            store.copy_prescription_file(str(test_data_dir / "test_constraints_prescription_exclusive.csv"))
            therapists = store.load_therapists()
            prescriptions = store.load_prescriptions()
        
        normalizer = DataNormalizer()
        normalized_therapists = normalizer.normalize_therapists(therapists)
        normalized_prescriptions = normalizer.normalize_prescriptions(prescriptions)
        
        builder = ConstraintMatrixBuilder()
        matrix = builder.build_compatibility(normalized_therapists, normalized_prescriptions)
        
        # Check that exclusive therapist from different ward has score 0
        # This depends on the specific data structure, but should have some 0 scores
        assert np.min(matrix) == 0  # Some assignments should be blocked
    
    def test_build_requirements_vector(self):
        """TC2.5: Requirements based on therapy type"""
        test_data_dir = Path(__file__).parent / "data"
        
        store = DataStore()
        with store.session():
            store.copy_prescription_file(str(test_data_dir / "test_constraints_prescription.csv"))
            prescriptions = store.load_prescriptions()
        
        normalizer = DataNormalizer()
        normalized_prescriptions = normalizer.normalize_prescriptions(prescriptions)
        
        builder = ConstraintMatrixBuilder()
        requirements = builder.build_requirements(normalized_prescriptions)
        
        assert requirements.shape == (2,)
        assert 180 in requirements  # 脳血管疾患等Ⅰ = 180 min
        assert 120 in requirements  # 運動器疾患Ⅰ = 120 min
