"""Agent tools for schedule operations."""

from typing import Dict, Any, Optional
from pathlib import Path
import numpy as np
from strands import tool
from schedule_agent.core.data_store import DataStore
from schedule_agent.core.pipeline import SchedulingPipeline
from schedule_agent.utils.visualization import ScheduleVisualizer
from schedule_agent.models.data_models import Schedule


class ScheduleNotAvailableError(Exception):
    """Raised when attempting to access schedule before it's created."""
    pass


class PatientNotFoundError(Exception):
    """Raised when patient ID is not found in constraint matrices."""
    pass


class TherapistNotFoundError(Exception):
    """Raised when therapist ID is not found in constraint matrices."""
    pass


class InvalidTimeslotError(Exception):
    """Raised when timeslot format is invalid or not in available slots."""
    pass


def create_schedule_tools(data_store: DataStore):
    """Create schedule tools with shared data store."""
    
    pipeline = SchedulingPipeline(data_store)
    visualizer = ScheduleVisualizer()
    current_schedule = {"schedule": None}
    
    @tool
    def create_schedule(therapist_file: str, prescription_file: str, 
                       shift_file: str, target_date: str) -> Dict[str, Any]:
        """Execute complete scheduling workflow from raw data files to final schedule.
        
        Args:
            therapist_file: Path to therapist CSV file
            prescription_file: Path to prescription CSV file
            shift_file: Path to shift Excel file
            target_date: Target date in YYYY-MM-DD format
            
        Returns:
            Dictionary with date, total_assignments, unscheduled_patients count and IDs
        """
        data_store.initialize()
        data_store.copy_therapist_file(therapist_file)
        data_store.copy_prescription_file(prescription_file)
        data_store.copy_shift_file(shift_file)
        
        current_schedule["schedule"] = pipeline.full_pipeline(target_date)
        
        return {
            "date": target_date,
            "total_assignments": len(current_schedule["schedule"].assignments),
            "unscheduled_patients": len(current_schedule["schedule"].unscheduled_patients),
            "unscheduled_patient_ids": current_schedule["schedule"].unscheduled_patients,
        }
    
    @tool
    def export_schedule_excel(output_path: str) -> Dict[str, str]:
        """Generate comprehensive Excel workbook with multiple views.
        
        Creates multi-sheet workbook with:
        - 詳細: Individual assignment details
        - 患者別スケジュール: Patient-centered view with attributes
        - 職員別スケジュール: Therapist workload view
        - サマリー: Overall statistics
        
        Args:
            output_path: Path where Excel file should be saved
            
        Returns:
            Dictionary with file_path
        """
        if not current_schedule["schedule"]:
            raise ScheduleNotAvailableError("No schedule available. Create a schedule first using create_schedule()")
        
        therapists = data_store.load_normalized_therapists()
        prescriptions = data_store.load_normalized_prescriptions()
        
        visualizer.export_to_excel(
            current_schedule["schedule"], 
            therapists, 
            prescriptions, 
            Path(output_path)
        )
        return {"file_path": output_path}
    
    @tool
    def get_schedule_data(patient_id: Optional[str] = None, 
                         therapist_id: Optional[str] = None) -> Dict[str, Any]:
        """Get schedule data for visualization. Returns raw assignment data that can be transformed to Mermaid or other formats.
        
        Args:
            patient_id: Optional patient ID to filter assignments
            therapist_id: Optional therapist ID to filter assignments
            
        Returns:
            Dictionary with assignments list. Each assignment contains patient_id, therapist_id, timeslot, duration_minutes.
            If no filters provided, returns all assignments.
        """
        if not current_schedule["schedule"]:
            raise ScheduleNotAvailableError("No schedule available. Create a schedule first using create_schedule()")
        
        matrices = data_store.load_all_matrices()
        
        if patient_id and patient_id not in matrices.patient_ids:
            raise PatientNotFoundError(
                f"Patient '{patient_id}' not found in constraint matrices. "
                f"Available patients: {', '.join(matrices.patient_ids[:5])}..."
            )
        
        if therapist_id and therapist_id not in matrices.therapist_ids:
            raise TherapistNotFoundError(
                f"Therapist '{therapist_id}' not found in constraint matrices. "
                f"Available therapists: {', '.join(matrices.therapist_ids[:5])}..."
            )
        
        assignments = current_schedule["schedule"].assignments
        
        if patient_id:
            assignments = [a for a in assignments if a.patient_id == patient_id]
        
        if therapist_id:
            assignments = [a for a in assignments if a.therapist_id == therapist_id]
        
        return {
            "assignments": [
                {
                    "patient_id": a.patient_id,
                    "therapist_id": a.therapist_id,
                    "timeslot": a.timeslot,
                    "duration_minutes": a.duration_minutes,
                }
                for a in assignments
            ],
            "filter": {
                "patient_id": patient_id,
                "therapist_id": therapist_id,
            }
        }
    
    @tool
    def show_schedule_summary() -> Dict[str, Any]:
        """Display detailed statistics about the current schedule.
        
        Returns:
            Dictionary with total_assignments, unique_patients, unique_therapists,
            unscheduled_patients, therapist_utilization, and patient_minutes
        """
        if not current_schedule["schedule"]:
            raise ScheduleNotAvailableError("No schedule available. Create a schedule first using create_schedule()")
        
        assignments = current_schedule["schedule"].assignments
        therapist_loads = {}
        patient_coverage = {}
        
        for a in assignments:
            therapist_loads[a.therapist_id] = therapist_loads.get(a.therapist_id, 0) + 1
            patient_coverage[a.patient_id] = patient_coverage.get(a.patient_id, 0) + a.duration_minutes
        
        return {
            "total_assignments": len(assignments),
            "unique_patients": len(patient_coverage),
            "unique_therapists": len(therapist_loads),
            "unscheduled_patients": len(current_schedule["schedule"].unscheduled_patients),
            "therapist_utilization": therapist_loads,
            "patient_minutes": patient_coverage,
        }
    
    @tool
    def get_patient_details(patient_id: str) -> Dict[str, Any]:
        """Show specific patient's constraints, requirements, and current assignments.
        
        Args:
            patient_id: Patient identifier
            
        Returns:
            Dictionary with patient_id, required_minutes, available_timeslots, and current_assignments
        """
        matrices = data_store.load_all_matrices()
        
        if patient_id not in matrices.patient_ids:
            raise PatientNotFoundError(
                f"Patient '{patient_id}' not found in constraint matrices. "
                f"Available patients: {', '.join(matrices.patient_ids[:5])}..."
            )
        
        idx = matrices.patient_ids.index(patient_id)
        available_slots = [
            matrices.timeslots[i] 
            for i in range(len(matrices.timeslots)) 
            if matrices.patient_availability[idx, i] == 1
        ]
        
        assignments = []
        if current_schedule["schedule"]:
            assignments = [
                {"therapist": a.therapist_id, "timeslot": a.timeslot, "duration": a.duration_minutes}
                for a in current_schedule["schedule"].assignments 
                if a.patient_id == patient_id
            ]
        
        return {
            "patient_id": patient_id,
            "required_minutes": int(matrices.requirements[idx]),
            "available_timeslots": available_slots,
            "current_assignments": assignments,
        }
    
    @tool
    def get_therapist_details(therapist_id: str) -> Dict[str, Any]:
        """Display therapist's availability, current workload, and assigned patients.
        
        Args:
            therapist_id: Therapist identifier
            
        Returns:
            Dictionary with therapist_id, available_timeslots, current_assignments, and total_assigned_slots
        """
        matrices = data_store.load_all_matrices()
        
        if therapist_id not in matrices.therapist_ids:
            raise TherapistNotFoundError(
                f"Therapist '{therapist_id}' not found in constraint matrices. "
                f"Available therapists: {', '.join(matrices.therapist_ids[:5])}..."
            )
        
        idx = matrices.therapist_ids.index(therapist_id)
        available_slots = [
            matrices.timeslots[i] 
            for i in range(len(matrices.timeslots)) 
            if matrices.therapist_availability[idx, i] == 1
        ]
        
        assignments = []
        if current_schedule["schedule"]:
            assignments = [
                {"patient": a.patient_id, "timeslot": a.timeslot, "duration": a.duration_minutes}
                for a in current_schedule["schedule"].assignments 
                if a.therapist_id == therapist_id
            ]
        
        return {
            "therapist_id": therapist_id,
            "available_timeslots": available_slots,
            "current_assignments": assignments,
            "total_assigned_slots": len(assignments),
        }
    
    @tool
    def update_patient_availability(patient_id: str, timeslot: str, 
                                    available: bool) -> Dict[str, Any]:
        """Modify patient's availability for specific timeslots.
        
        Args:
            patient_id: Patient identifier
            timeslot: Timeslot in format "HH:MM-HH:MM"
            available: True to make available, False to make unavailable
            
        Returns:
            Dictionary with patient_id, timeslot, old_value, and new_value
        """
        matrices = data_store.load_all_matrices()
        
        if patient_id not in matrices.patient_ids:
            raise PatientNotFoundError(
                f"Patient '{patient_id}' not found in constraint matrices. "
                f"Available patients: {', '.join(matrices.patient_ids[:5])}..."
            )
        
        if timeslot not in matrices.timeslots:
            raise InvalidTimeslotError(
                f"Invalid timeslot '{timeslot}'. Must be one of: {', '.join(matrices.timeslots)}"
            )
        
        patient_idx = matrices.patient_ids.index(patient_id)
        slot_idx = matrices.timeslots.index(timeslot)
        
        old_value = matrices.patient_availability[patient_idx, slot_idx]
        matrices.patient_availability[patient_idx, slot_idx] = 1 if available else 0
        
        data_store.save_all_matrices(matrices)
        
        return {
            "patient_id": patient_id,
            "timeslot": timeslot,
            "old_value": int(old_value),
            "new_value": 1 if available else 0,
        }
    
    return [
        create_schedule,
        export_schedule_excel,
        get_schedule_data,
        show_schedule_summary,
        get_patient_details,
        get_therapist_details,
        update_patient_availability,
    ]
