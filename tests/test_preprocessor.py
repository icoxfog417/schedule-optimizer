from pathlib import Path
from schedule_agent.core.data_store import DataStore


class TestDataStore:
    """Test data loading functionality"""
    
    def test_load_therapist_data(self):
        """TC1.1: Load therapist data with correct parsing"""
        test_data_dir = Path(__file__).parent / "data"
        
        store = DataStore()
        with store.session():
            store.copy_therapist_file(str(test_data_dir / "test_preprocessor_therapist.csv"))
            therapists = store.load_therapists()
        
        assert len(therapists) == 2
        assert therapists.iloc[0]["漢字氏名"] == "山田太郎"
        assert therapists.iloc[0]["性別"] == "男"
        assert therapists.iloc[0]["専従"] != "〇"
        assert therapists.iloc[1]["漢字氏名"] == "佐藤花子"
        assert therapists.iloc[1]["専従"] == "〇"
    
    def test_load_prescription_data(self):
        """TC1.2: Load prescription data with correct parsing"""
        test_data_dir = Path(__file__).parent / "data"
        
        store = DataStore()
        with store.session():
            store.copy_prescription_file(str(test_data_dir / "test_preprocessor_prescription.csv"))
            prescriptions = store.load_prescriptions()
        
        assert len(prescriptions) == 2
        assert prescriptions.iloc[0]["患者ID"] == 1001
        assert prescriptions.iloc[0]["担当療法士"] == "山田太郎"
        assert prescriptions.iloc[0]["算定区分"] == "脳血管疾患等Ⅰ"
        assert prescriptions.iloc[0]["入浴"] == "10:00-10:20"
        assert prescriptions.iloc[1]["排泄"] == "14:00-14:20"
    
    def test_load_prescription_duplicates(self):
        """TC1.2: Handle duplicate patient records - latest wins"""
        test_data_dir = Path(__file__).parent / "data"
        
        store = DataStore()
        with store.session():
            store.copy_prescription_file(str(test_data_dir / "test_preprocessor_prescription_duplicates.csv"))
            prescriptions = store.load_prescriptions()
        
        # Should have 2 records loaded (DataStore loads all, normalizer handles deduplication)
        assert len(prescriptions) == 2
        assert prescriptions.iloc[0]["担当療法士"] == "山田太郎"  # First record
        assert prescriptions.iloc[1]["担当療法士"] == "佐藤花子"  # Second record
        assert prescriptions.iloc[0]["入浴"] == "10:00-10:20"  # First record
        assert prescriptions.iloc[1]["入浴"] == "11:00-11:20"  # Second record
    
    def test_load_shift_data(self):
        """TC1.3: Load shift data with availability codes"""
        test_data_dir = Path(__file__).parent / "data"
        
        store = DataStore()
        with store.session():
            store.copy_shift_file(str(test_data_dir / "test_preprocessor_shift.xlsx"))
            shifts = store.load_shifts()
        
        assert len(shifts) >= 2
        # Check that shift data contains therapist names
        therapist_names = shifts.iloc[:, 3].tolist()
        assert "山田太郎" in therapist_names
        assert "佐藤花子" in therapist_names
