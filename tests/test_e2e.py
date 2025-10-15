import pytest
from pathlib import Path
from schedule_agent.core.data_store import DataStore
from schedule_agent.core.preprocessor import DataNormalizer
from schedule_agent.core.constraints_builder import ConstraintMatrixBuilder
from schedule_agent.core.scheduler import DeterministicScheduler


class TestEndToEndPipeline:
    """Test complete workflow from raw data to schedule output"""
    
    def test_full_pipeline(self):
        """TC4.1: Full pipeline test"""
        test_data_dir = Path(__file__).parent / "data"
        
        # Step 1: Load data
        store = DataStore()
        with store.session():
            store.copy_therapist_file(str(test_data_dir / "test_preprocessor_therapist.csv"))
            store.copy_prescription_file(str(test_data_dir / "test_preprocessor_prescription.csv"))
            store.copy_shift_file(str(test_data_dir / "test_preprocessor_shift.xlsx"))
            therapists = store.load_therapists()
            prescriptions = store.load_prescriptions()
            shifts = store.load_shifts()
        
        # Step 2: Normalize data
        normalizer = DataNormalizer()
        normalized_therapists = normalizer.normalize_therapists(therapists)
        normalized_prescriptions = normalizer.normalize_prescriptions(prescriptions)
        normalized_shifts = normalizer.normalize_shifts(shifts, "2025-10-01")
        
        # Step 3: Build constraints
        builder = ConstraintMatrixBuilder()
        matrices = builder.build_matrices(normalized_therapists, normalized_prescriptions, normalized_shifts)
        
        # Step 4: Run scheduler
        scheduler = DeterministicScheduler()
        schedule = scheduler.schedule(matrices)
        
        # Verify results
        assert len(schedule.assignments) > 0
        assert len(schedule.unscheduled_patients) == 0
        
        # Verify all patients scheduled with correct requirements
        patient_assignments = {}
        for assignment in schedule.assignments:
            if assignment.patient_id not in patient_assignments:
                patient_assignments[assignment.patient_id] = 0
            patient_assignments[assignment.patient_id] += 1
        
        # Patient with 脳血管疾患等Ⅰ should have 9 assignments (180 min)
        # Patient with 運動器疾患Ⅰ should have 6 assignments (120 min)
        assert len(patient_assignments) == 2
        assignment_counts = list(patient_assignments.values())
        assert 9 in assignment_counts  # 脳血管疾患等Ⅰ
        assert 6 in assignment_counts  # 運動器疾患Ⅰ
    
    def test_pipeline_with_constraints(self):
        """TC4.2: Pipeline with realistic constraints"""
        test_data_dir = Path(__file__).parent / "data"
        
        # Run full pipeline with constraint data
        store = DataStore()
        with store.session():
            store.copy_therapist_file(str(test_data_dir / "test_constraints_therapist.csv"))
            store.copy_prescription_file(str(test_data_dir / "test_constraints_prescription.csv"))
            store.copy_shift_file(str(test_data_dir / "test_constraints_shift.xlsx"))
            therapists = store.load_therapists()
            prescriptions = store.load_prescriptions()
            shifts = store.load_shifts()
        
        normalizer = DataNormalizer()
        normalized_therapists = normalizer.normalize_therapists(therapists)
        normalized_prescriptions = normalizer.normalize_prescriptions(prescriptions)
        normalized_shifts = normalizer.normalize_shifts(shifts, "2025-10-01")
        
        builder = ConstraintMatrixBuilder()
        matrices = builder.build_matrices(normalized_therapists, normalized_prescriptions, normalized_shifts)
        
        scheduler = DeterministicScheduler()
        schedule = scheduler.schedule(matrices)
        
        # Verify constraints are respected
        for assignment in schedule.assignments:
            # Patient with bathing at 10:00 should not be assigned at that time
            if assignment.patient_id == "1001":
                assert assignment.timeslot != "10:00-10:20"
            
            # Patient with excretion at 14:00 should not be assigned at that time
            if assignment.patient_id == "1002":
                assert assignment.timeslot != "14:00-14:20"
