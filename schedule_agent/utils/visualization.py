import pandas as pd
from pathlib import Path
from typing import Type
from schedule_agent.core.data_store import DataStore
from schedule_agent.models.data_models import Schedule


class ScheduleVisualizer:
    """Generate schedule visualizations."""
    
    def export_to_excel(self, data_store: Type[DataStore], output_path: Path) -> None:
        """Export schedule to Excel format.
        
        Args:
            data_store: DataStore instance to load schedule and data from
            output_path: Path where Excel file should be saved
        """
        # Load schedule and data from data_store
        schedule = data_store.load_schedule()
        matrices = data_store.load_all_matrices()
        therapists_df = data_store.load_normalized_therapists()
        prescriptions_df = data_store.load_normalized_prescriptions()
        
        # Create DataFrame from assignments
        data = []
        for assignment in schedule.assignments:
            data.append({
                '患者ID': assignment.patient_id,
                '職員ID': assignment.therapist_id,
                '時間帯': assignment.timeslot,
                '時間(分)': assignment.duration_minutes
            })
        
        df = pd.DataFrame(data)
        
        # Sort by patient and timeslot
        df = df.sort_values(['患者ID', '時間帯'])
        
        # Create pivot table for patient schedule
        pivot = df.pivot_table(
            index='患者ID',
            columns='時間帯',
            values='職員ID',
            aggfunc='first'
        )
        pivot = pivot[sorted(pivot.columns, key=lambda x: matrices.timeslots.index(x) if x in matrices.timeslots else 999)]
        
        # Add patient attributes
        patient_attrs = prescriptions_df[['患者ID', '氏名', '病棟', '担当療法士', '算定区分']].drop_duplicates('患者ID')
        pivot_with_attrs = pivot.reset_index().merge(patient_attrs, on='患者ID', how='left')
        # Reorder columns: attributes first, then timeslots
        attr_cols = ['患者ID', '氏名', '病棟', '担当療法士', '算定区分']
        time_cols = [c for c in pivot_with_attrs.columns if c not in attr_cols]
        pivot_with_attrs = pivot_with_attrs[attr_cols + time_cols]
        
        # Create pivot table for therapist schedule
        therapist_pivot = df.pivot_table(
            index='職員ID',
            columns='時間帯',
            values='患者ID',
            aggfunc='first'
        )
        therapist_pivot = therapist_pivot[sorted(therapist_pivot.columns, key=lambda x: matrices.timeslots.index(x) if x in matrices.timeslots else 999)]
        
        # Add therapist attributes
        therapist_attrs = therapists_df[['職員ID', '漢字氏名', '性別', '職種', '担当病棟']].drop_duplicates('職員ID')
        therapist_pivot_with_attrs = therapist_pivot.reset_index().merge(therapist_attrs, on='職員ID', how='left')
        # Reorder columns: attributes first, then timeslots
        attr_cols = ['職員ID', '漢字氏名', '性別', '職種', '担当病棟']
        time_cols = [c for c in therapist_pivot_with_attrs.columns if c not in attr_cols]
        therapist_pivot_with_attrs = therapist_pivot_with_attrs[attr_cols + time_cols]
        
        # Write to Excel with multiple sheets
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Sheet 1: Detailed assignments
            df.to_excel(writer, sheet_name='詳細', index=False)
            
            # Sheet 2: Patient schedule with attributes
            pivot_with_attrs.to_excel(writer, sheet_name='患者別スケジュール', index=False)
            
            # Sheet 3: Therapist schedule with attributes
            therapist_pivot_with_attrs.to_excel(writer, sheet_name='職員別スケジュール', index=False)
            
            # Sheet 4: Summary
            summary_data = {
                '項目': ['総割当数', '患者数', '職員数', '未割当患者数'],
                '値': [
                    len(schedule.assignments),
                    len(matrices.patient_ids),
                    len(matrices.therapist_ids),
                    len(schedule.unscheduled_patients)
                ]
            }
            pd.DataFrame(summary_data).to_excel(writer, sheet_name='サマリー', index=False)
        
        return output_path
    
    def generate_mermaid(self, schedule: Schedule, patient_id: str = None) -> str:
        """Generate Mermaid Gantt chart for a patient."""
        if not patient_id and schedule.assignments:
            patient_id = schedule.assignments[0].patient_id
        
        patient_assignments = [a for a in schedule.assignments if a.patient_id == patient_id]
        
        lines = [
            "gantt",
            f"    title Patient {patient_id} Schedule",
            "    dateFormat HH:mm",
            "    axisFormat %H:%M",
            ""
        ]
        
        for i, assignment in enumerate(patient_assignments):
            start_time = assignment.timeslot.split('-')[0]
            end_time = assignment.timeslot.split('-')[1]
            lines.append(f"    {assignment.therapist_id} : {start_time}, {end_time}")
        
        return "\n".join(lines)
