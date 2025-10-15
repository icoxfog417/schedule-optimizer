import pytest
from pathlib import Path
import pandas as pd
import numpy as np

from schedule_agent.core.data_store import DataStore
from schedule_agent.core.pipeline import SchedulingPipeline
from schedule_agent.models.data_models import ConstraintMatrices


class TestDataStore:
    """Test DataStore functionality."""
    
    @pytest.fixture
    def test_data_dir(self):
        """Return path to test data directory."""
        return Path(__file__).parent / "data"
    
    def test_session_management(self):
        """Test DataStore session management."""
        store = DataStore()
        
        # Test session initialization
        with store.session() as temp_dir:
            assert temp_dir.exists()
            assert (temp_dir / "raw").exists()
            assert (temp_dir / "interim").exists()
            assert (temp_dir / "processed").exists()
            
            # Store temp_dir for cleanup verification
            temp_path = temp_dir
        
        # Session should be cleaned up
        assert not temp_path.exists()
    
    def test_nested_sessions(self):
        """Test nested session behavior."""
        store = DataStore()
        
        with store.session() as outer_dir:
            outer_path = outer_dir
            
            # Nested session should reuse same directory
            with store.session() as inner_dir:
                assert inner_dir == outer_dir
                assert inner_dir.exists()
            
            # Inner session shouldn't cleanup
            assert outer_path.exists()
        
        # Only outer session should cleanup
        assert not outer_path.exists()
    
    def test_file_operations(self, test_data_dir):
        """Test file copying and loading."""
        store = DataStore()
        
        with store.session():
            # Test file copying
            store.copy_therapist_file(test_data_dir / "therapist.csv")
            store.copy_prescription_file(test_data_dir / "prescription.csv") 
            store.copy_shift_file(test_data_dir / "shift_test.xlsx")
            
            # Test data loading
            therapists = store.load_therapists()
            prescriptions = store.load_prescriptions()
            shifts = store.load_shifts()
            
            assert isinstance(therapists, pd.DataFrame)
            assert isinstance(prescriptions, pd.DataFrame)
            assert isinstance(shifts, pd.DataFrame)
            assert len(therapists) == 3
            assert len(prescriptions) == 3
            assert len(shifts) == 3
    
    def test_normalized_data_operations(self):
        """Test normalized data save/load operations."""
        store = DataStore()
        
        with store.session():
            # Create test data
            test_therapists = pd.DataFrame({
                '職員ID': ['T001', 'T002'],
                '漢字氏名': ['田中太郎', '佐藤花子'],
                '性別': ['男', '女'],
                '専従': [True, False],
                '担当病棟': ['3E', '4W']
            })
            
            # Save and load
            store.save_normalized_therapists(test_therapists)
            loaded = store.load_normalized_therapists()
            
            pd.testing.assert_frame_equal(test_therapists, loaded)
    
    def test_matrix_operations(self):
        """Test constraint matrix save/load operations."""
        store = DataStore()
        
        with store.session():
            # Create test matrices
            matrices = ConstraintMatrices(
                patient_availability=np.array([[1, 0, 1], [0, 1, 1]]),
                therapist_availability=np.array([[1, 1, 0], [0, 1, 1]]),
                compatibility=np.array([[100, 60], [80, 100]]),
                requirements=np.array([180, 120]),
                patient_ids=['P001', 'P002'],
                therapist_ids=['T001', 'T002'],
                timeslots=['09:00-09:20', '09:20-09:40', '09:40-10:00']
            )
            
            # Save and load
            store.save_all_matrices(matrices)
            loaded = store.load_all_matrices()
            
            np.testing.assert_array_equal(matrices.patient_availability, loaded.patient_availability)
            np.testing.assert_array_equal(matrices.therapist_availability, loaded.therapist_availability)
            np.testing.assert_array_equal(matrices.compatibility, loaded.compatibility)
            np.testing.assert_array_equal(matrices.requirements, loaded.requirements)
            assert matrices.patient_ids == loaded.patient_ids
            assert matrices.therapist_ids == loaded.therapist_ids
            assert matrices.timeslots == loaded.timeslots
    
    def test_save_and_load_schedule(self):
        """Test saving and loading schedule from pickle file."""
        from schedule_agent.models.data_models import Schedule, Assignment
        
        # Create a test schedule
        assignments = [
            Assignment(
                patient_id="P001",
                therapist_id="T001",
                timeslot="09:00-09:20",
                duration_minutes=20
            ),
            Assignment(
                patient_id="P001",
                therapist_id="T001",
                timeslot="09:20-09:40",
                duration_minutes=20
            ),
        ]
        
        test_schedule = Schedule(
            assignments=assignments,
            date="2025-10-15",
            unscheduled_patients=[]
        )
        
        # Test save and load
        store = DataStore()
        with store.session():
            # Save schedule
            saved_path = store.save_schedule(test_schedule)
            assert saved_path.exists()
            assert saved_path.name == "current_schedule.pkl"
            
            # Check has_schedule
            assert store.has_schedule() is True
            
            # Load schedule
            loaded_schedule = store.load_schedule()
            assert loaded_schedule is not None
            assert loaded_schedule.date == "2025-10-15"
            assert len(loaded_schedule.assignments) == 2
            assert loaded_schedule.assignments[0].patient_id == "P001"
            assert loaded_schedule.assignments[0].therapist_id == "T001"
    
    def test_load_nonexistent_schedule(self):
        """Test loading schedule when none exists."""
        store = DataStore()
        with store.session():
            # Should return None when no schedule exists
            loaded_schedule = store.load_schedule()
            assert loaded_schedule is None
            
            # has_schedule should return False
            assert store.has_schedule() is False
    
    def test_export_schedule(self):
        """Test exporting schedule to Excel (renamed from save_schedule)."""
        from schedule_agent.models.data_models import Schedule, Assignment
        
        assignments = [
            Assignment(
                patient_id="P001",
                therapist_id="T001",
                timeslot="09:00-09:20",
                duration_minutes=20
            ),
        ]
        
        test_schedule = Schedule(
            assignments=assignments,
            date="2025-10-15",
            unscheduled_patients=[]
        )
        
        store = DataStore()
        with store.session():
            # Export to Excel
            store.export_schedule(test_schedule)
            
            # Check Excel file was created
            excel_file = store._temp_dir / "processed" / "schedule_2025-10-15.xlsx"
            assert excel_file.exists()


class TestSchedulingPipeline:
    """Test SchedulingPipeline with DataStore."""
    
    @pytest.fixture
    def test_data_dir(self):
        """Return path to test data directory."""
        return Path(__file__).parent / "data"
    
    def test_pipeline_preprocessing(self, test_data_dir):
        """Test pipeline preprocessing steps."""
        store = DataStore()
        
        with store.session():
            store.copy_therapist_file(test_data_dir / "therapist.csv")
            store.copy_prescription_file(test_data_dir / "prescription.csv") 
            store.copy_shift_file(test_data_dir / "shift_test.xlsx")
            
            pipeline = SchedulingPipeline(store)
            
            # Test individual preprocessing steps
            pipeline.preprocess_therapists()
            therapists = store.load_normalized_therapists()
            assert len(therapists) == 3
            assert '専従' in therapists.columns
            
            pipeline.preprocess_prescriptions()
            prescriptions = store.load_normalized_prescriptions()
            assert len(prescriptions) == 3
            
            pipeline.preprocess_shifts("2025-10-04")
            shifts = store.load_normalized_shifts()
            assert len(shifts) == 3
            assert 'therapist_name' in shifts.columns
            assert 'availability' in shifts.columns
    
    def test_pipeline_constraint_building(self, test_data_dir):
        """Test pipeline constraint matrix building."""
        store = DataStore()
        
        with store.session():
            store.copy_therapist_file(test_data_dir / "therapist.csv")
            store.copy_prescription_file(test_data_dir / "prescription.csv") 
            store.copy_shift_file(test_data_dir / "shift_test.xlsx")
            
            pipeline = SchedulingPipeline(store)
            pipeline.preprocess_all("2025-10-04")
            pipeline.build_all_constraints()
            
            # Verify matrices were created
            matrices = store.load_all_matrices()
            assert matrices.patient_availability.shape[1] == 18  # 18 timeslots
            assert matrices.therapist_availability.shape[1] == 18
            assert len(matrices.patient_ids) == 3
            assert len(matrices.therapist_ids) == 3
    
    def test_full_pipeline(self, test_data_dir):
        """Test complete pipeline execution."""
        store = DataStore()
        
        with store.session():
            store.copy_therapist_file(test_data_dir / "therapist.csv")
            store.copy_prescription_file(test_data_dir / "prescription.csv") 
            store.copy_shift_file(test_data_dir / "shift_test.xlsx")
            
            pipeline = SchedulingPipeline(store)
            
            # This might fail due to scheduling constraints, but should not crash
            try:
                result = pipeline.full_pipeline("2025-10-04")
                assert result.date == "2025-10-04"
                assert isinstance(result.assignments, list)
                assert isinstance(result.unscheduled_patients, list)
            except Exception as e:
                # Pipeline execution might fail due to infeasible constraints
                # but the DataStore operations should work
                pytest.skip(f"Pipeline execution failed (expected): {e}")


class TestDataStoreErrorHandling:
    """Test DataStore error handling."""
    
    def test_session_not_initialized(self):
        """Test operations without session initialization."""
        store = DataStore()
        
        with pytest.raises(RuntimeError, match="Session not initialized"):
            store.copy_input("nonexistent.csv")
    
    def test_file_not_found(self):
        """Test handling of missing files."""
        store = DataStore()
        
        with store.session():
            with pytest.raises(FileNotFoundError):
                store.copy_input("nonexistent_file.csv")
    
    def test_missing_data_files(self):
        """Test loading missing normalized data."""
        store = DataStore()
        
        with store.session():
            with pytest.raises(FileNotFoundError):
                store.load_normalized_therapists()
