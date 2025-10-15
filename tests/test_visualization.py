import pytest
import pandas as pd
from pathlib import Path
from schedule_agent.core.data_store import DataStore
from schedule_agent.core.preprocessor import DataNormalizer
from schedule_agent.core.constraints_builder import ConstraintMatrixBuilder
from schedule_agent.core.scheduler import DeterministicScheduler
from schedule_agent.utils.visualization import ScheduleVisualizer


class TestVisualization:
    """Test visualization module with real test data"""
    
    def test_export_to_excel_basic(self, tmp_path):
        """Test export_to_excel creates valid Excel file with test data"""
        test_data_dir = Path(__file__).parent / "data"
        
        # Create schedule using test data
        store = DataStore()
        with store.session():
            store.copy_therapist_file(str(test_data_dir / "test_preprocessor_therapist.csv"))
            store.copy_prescription_file(str(test_data_dir / "test_preprocessor_prescription.csv"))
            store.copy_shift_file(str(test_data_dir / "test_preprocessor_shift.xlsx"))
            
            therapists = store.load_therapists()
            prescriptions = store.load_prescriptions()
            shifts = store.load_shifts()
            
            normalizer = DataNormalizer()
            normalized_therapists = normalizer.normalize_therapists(therapists)
            normalized_prescriptions = normalizer.normalize_prescriptions(prescriptions)
            normalized_shifts = normalizer.normalize_shifts(shifts, "2025-10-01")
            
            store.save_normalized_therapists(normalized_therapists)
            store.save_normalized_prescriptions(normalized_prescriptions)
            
            builder = ConstraintMatrixBuilder()
            matrices = builder.build_matrices(normalized_therapists, normalized_prescriptions, normalized_shifts)
            store.save_all_matrices(matrices)
            
            scheduler = DeterministicScheduler()
            schedule = scheduler.schedule(matrices)
            store.save_schedule(schedule)
            
            # Export to Excel
            visualizer = ScheduleVisualizer()
            output_path = tmp_path / "test_output.xlsx"
            result = visualizer.export_to_excel(store, output_path)
            
            # Verify file exists
            assert output_path.exists()
            assert result == output_path
            
            # Verify Excel has required sheets
            excel_file = pd.ExcelFile(output_path)
            assert '詳細' in excel_file.sheet_names
            assert '患者別スケジュール' in excel_file.sheet_names
            assert '職員別スケジュール' in excel_file.sheet_names
            assert 'サマリー' in excel_file.sheet_names
            
            # Verify detailed sheet has data
            df_detail = pd.read_excel(output_path, sheet_name='詳細')
            assert len(df_detail) > 0
            assert '患者ID' in df_detail.columns
            assert '職員ID' in df_detail.columns
            assert '時間帯' in df_detail.columns
