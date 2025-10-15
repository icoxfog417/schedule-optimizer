import pandas as pd


class DataNormalizer:
    """Pure data transformation - no I/O dependencies."""
    
    WARD_MAP = {
        '3階東病棟': '3E', '3階西病棟': '3W', '3階新病棟': '3W',
        '4階東病棟': '4E', '4階西病棟': '4W',
        '5階東病棟': '5E', '5階西病棟': '5W'
    }
    
    def normalize_therapists(self, therapists: pd.DataFrame) -> pd.DataFrame:
        normalized = therapists.copy()
        normalized['専従'] = normalized['専従'] == '〇'
        return normalized
    
    def normalize_prescriptions(self, prescriptions: pd.DataFrame) -> pd.DataFrame:
        normalized = prescriptions.copy()
        normalized['病棟'] = normalized['病棟'].map(self.WARD_MAP)
        return self._normalize_time_formats(normalized)
    
    def normalize_shifts(self, shifts: pd.DataFrame, target_date: str) -> pd.DataFrame:
        """Extract availability for target date."""
        df = shifts.copy()
        
        # Extract day from date (e.g., "2025-10-04" -> "4")
        day = target_date.split('-')[-1].lstrip('0')
        
        # Find column that contains the day number
        # Format is like " 1\n水" or " 1_x000D_\n水"
        date_col = None
        for col in df.columns[4:]:
            col_str = str(col).strip()
            # Handle both formats: with newline and with _x000D_
            if (col_str.startswith(f' {day}\n') or 
                col_str.startswith(f'{day}\n') or
                col_str.startswith(f' {day}_') or
                col_str.startswith(f'{day}_')):
                date_col = col
                break
        
        if date_col is None:
            raise ValueError(f"Date {target_date} (day {day}) not found in shift data")
        
        result = pd.DataFrame({
            'therapist_name': df.iloc[:, 3],
            'availability': df[date_col]
        })
        
        return result.dropna(subset=['therapist_name'])
    
    def _normalize_time_formats(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize time format strings."""
        return df
