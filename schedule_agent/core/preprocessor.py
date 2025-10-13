import pandas as pd
from pathlib import Path
import json


class DataLoader:
    """Load CSV/Excel with cp932 encoding."""
    
    def __init__(self, data_dir: Path = Path("data/raw")):
        self.data_dir = data_dir
    
    def load_therapists(self) -> pd.DataFrame:
        return pd.read_csv(self.data_dir / "therapist.csv", encoding="cp932")
    
    def load_prescriptions(self) -> pd.DataFrame:
        return pd.read_csv(self.data_dir / "prescription.csv", encoding="cp932")
    
    def load_shifts(self, year_month: str) -> pd.DataFrame:
        return pd.read_excel(self.data_dir / f"shift_{year_month}.xlsx", header=1)


class DataNormalizer:
    """Normalize ward names, therapist IDs, time formats."""
    
    WARD_MAP = {
        '3階東病棟': '3E', '3階西病棟': '3W', '3階新病棟': '3W',
        '4階東病棟': '4E', '4階西病棟': '4W',
        '5階東病棟': '5E', '5階西病棟': '5W'
    }
    
    def normalize_therapists(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df['専従'] = df['専従'] == '〇'
        return df
    
    def normalize_prescriptions(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df['病棟'] = df['病棟'].map(self.WARD_MAP)
        return df
    
    def normalize_shifts(self, df: pd.DataFrame, target_date: str) -> pd.DataFrame:
        """Extract availability for target date."""
        df = df.copy()
        
        # Extract day from date (e.g., "2025-10-04" -> "4")
        day = target_date.split('-')[-1].lstrip('0')
        
        # Find column that starts with the day number
        date_col = None
        for col in df.columns[4:]:
            col_str = str(col).strip()
            if col_str.startswith(f' {day}_') or col_str.startswith(f'{day}_'):
                date_col = col
                break
        
        if date_col is None:
            raise ValueError(f"Date {target_date} (day {day}) not found in shift data")
        
        result = pd.DataFrame({
            'therapist_name': df.iloc[:, 3],
            'availability': df[date_col]
        })
        
        return result.dropna(subset=['therapist_name'])


class InterimWriter:
    """Save processed data to data/interim/."""
    
    def __init__(self, output_dir: Path = Path("data/interim")):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def save_therapists(self, df: pd.DataFrame):
        df.to_csv(self.output_dir / "normalized_therapists.csv", index=False, encoding="utf-8")
    
    def save_prescriptions(self, df: pd.DataFrame):
        df.to_csv(self.output_dir / "normalized_prescriptions.csv", index=False, encoding="utf-8")
    
    def save_shifts(self, df: pd.DataFrame):
        df.to_csv(self.output_dir / "normalized_shifts.csv", index=False, encoding="utf-8")
    
    def save_name_mapping(self, therapists_df: pd.DataFrame):
        mapping = dict(zip(therapists_df['漢字氏名'], therapists_df['職員ID']))
        with open(self.output_dir / "name_to_id_mapping.json", "w", encoding="utf-8") as f:
            json.dump(mapping, f, ensure_ascii=False, indent=2)
