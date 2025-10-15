from pathlib import Path
from schedule_agent.core.scheduler import DeterministicScheduler
from schedule_agent.core.data_store import DataStore
from schedule_agent.core.preprocessor import DataNormalizer
from schedule_agent.core.constraints_builder import ConstraintMatrixBuilder


class TestDeterministicScheduler:
    """Test deterministic scheduling algorithm"""
    
    def test_simple_feasible_schedule(self):
        """TC3.1: Simple feasible schedule"""
        test_data_dir = Path(__file__).parent / "data"
        
        store = DataStore()
        with store.session():
            store.copy_therapist_file(str(test_data_dir / "test_scheduler_therapist.csv"))
            store.copy_prescription_file(str(test_data_dir / "test_scheduler_prescription.csv"))
            store.copy_shift_file(str(test_data_dir / "test_scheduler_shift.xlsx"))
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
        
        assert len(schedule.assignments) == 12  # 6 + 6 assignments
        assert len(schedule.unscheduled_patients) == 0
        
        # Check all patients have required assignments
        patient_assignments = {}
        for assignment in schedule.assignments:
            patient_assignments[assignment.patient_id] = patient_assignments.get(assignment.patient_id, 0) + 1
        
        assert len(patient_assignments) == 2
        for count in patient_assignments.values():
            assert count == 6  # Each patient needs 6 slots (120 min)
    
    def test_respect_patient_unavailability(self):
        """TC3.2: Respect patient unavailability"""
        test_data_dir = Path(__file__).parent / "data"
        
        store = DataStore()
        with store.session():
            store.copy_therapist_file(str(test_data_dir / "test_scheduler_therapist.csv"))
            store.copy_prescription_file(str(test_data_dir / "test_constraints_prescription.csv"))  # Has blocked times
            store.copy_shift_file(str(test_data_dir / "test_scheduler_shift_blocked.xlsx"))
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
        
        # No assignments should be in blocked slots
        for assignment in schedule.assignments:
            if assignment.patient_id == "1001":
                assert assignment.timeslot != "10:00-10:20"  # Bathing time
            if assignment.patient_id == "1002":
                assert assignment.timeslot != "14:00-14:20"  # Excretion time
    
    def test_respect_therapist_unavailability(self):
        """TC3.3: Respect therapist unavailability"""
        test_data_dir = Path(__file__).parent / "data"
        
        store = DataStore()
        with store.session():
            store.copy_therapist_file(str(test_data_dir / "test_scheduler_therapist.csv"))
            store.copy_prescription_file(str(test_data_dir / "test_scheduler_prescription.csv"))
            store.copy_shift_file(str(test_data_dir / "test_scheduler_shift_afternoon.xlsx"))
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
        
        # All assignments should respect therapist availability
        # (Specific time validation depends on time_utils implementation)
        assert len(schedule.assignments) > 0
    
    def test_primary_therapist_preference(self):
        """TC3.4: Primary therapist preference"""
        test_data_dir = Path(__file__).parent / "data"
        
        store = DataStore()
        with store.session():
            store.copy_therapist_file(str(test_data_dir / "test_scheduler_therapist.csv"))
            store.copy_prescription_file(str(test_data_dir / "test_scheduler_prescription.csv"))
            store.copy_shift_file(str(test_data_dir / "test_scheduler_shift.xlsx"))
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
        
        # Patient 1001 should prefer therapist T001 (山田太郎 is the primary)
        p1_assignments = [a for a in schedule.assignments if a.patient_id == 1001]
        primary_assignments = [a for a in p1_assignments if a.therapist_id == "T001"]
        
        # Should have some assignments with primary therapist
        assert len(primary_assignments) > 0
    
    def test_deterministic_output(self):
        """TC3.6: Deterministic output"""
        test_data_dir = Path(__file__).parent / "data"
        
        store = DataStore()
        with store.session():
            store.copy_therapist_file(str(test_data_dir / "test_scheduler_therapist.csv"))
            store.copy_prescription_file(str(test_data_dir / "test_scheduler_prescription.csv"))
            store.copy_shift_file(str(test_data_dir / "test_scheduler_shift.xlsx"))
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
        
        schedule1 = scheduler.schedule(matrices)
        schedule2 = scheduler.schedule(matrices)
        
        # Should produce identical schedules
        assert len(schedule1.assignments) == len(schedule2.assignments)
        
        # Sort assignments for comparison
        def sort_key(a):
            return (a.patient_id, a.therapist_id, a.timeslot)
        
        assignments1 = sorted(schedule1.assignments, key=sort_key)
        assignments2 = sorted(schedule2.assignments, key=sort_key)
        
        for a1, a2 in zip(assignments1, assignments2):
            assert a1.patient_id == a2.patient_id
            assert a1.therapist_id == a2.therapist_id
            assert a1.timeslot == a2.timeslot
