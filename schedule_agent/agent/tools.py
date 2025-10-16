"""Agent tools for schedule operations."""

from typing import Dict, Any, Optional
from pathlib import Path
from strands import tool
from schedule_agent.core.data_store import DataStore
from schedule_agent.core.pipeline import SchedulingPipeline
from schedule_agent.utils.visualization import ScheduleVisualizer


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
    
    @tool
    def search_patients(query: str) -> Dict[str, Any]:
        """Search patients by partial name, ID, or ward code."""
        df = data_store.load_normalized_prescriptions()
        
        mask = (
            df['患者ID'].str.contains(query, case=False, na=False) |
            df['氏名'].str.contains(query, case=False, na=False) |
            df['病棟'].str.contains(query, case=False, na=False)
        )
        
        matches = df[mask].drop_duplicates('患者ID')
        
        results = []
        for _, row in matches.iterrows():
            results.append({
                "patient_id": row['患者ID'],
                "name": row['氏名'],
                "ward": row['病棟'],
                "primary_therapist": row['担当療法士']
            })
        
        return {
            "query": query,
            "found_count": len(results),
            "patients": results
        }

    @tool  
    def search_therapists(query: str) -> Dict[str, Any]:
        """Search therapists by partial name, ID, or ward code."""
        df = data_store.load_normalized_therapists()
        
        mask = (
            df['職員ID'].str.contains(query, case=False, na=False) |
            df['漢字氏名'].str.contains(query, case=False, na=False) |
            df['担当病棟'].str.contains(query, case=False, na=False)
        )
        
        matches = df[mask]
        
        results = []
        for _, row in matches.iterrows():
            results.append({
                "therapist_id": row['職員ID'],
                "name": row['漢字氏名'],
                "gender": row['性別'],
                "ward": row['担当病棟'],
                "exclusive": row['専従'] == "〇"
            })
        
        return {
            "query": query,
            "found_count": len(results),
            "therapists": results
        }

    @tool
    def list_available_timeslots() -> Dict[str, Any]:
        """List all available time slots."""
        from schedule_agent.utils.time_utils import generate_timeslots
        
        slots = generate_timeslots()
        
        morning_slots = []
        afternoon_slots = []
        
        for i, slot in enumerate(slots):
            slot_info = {"index": i, "timeslot": slot}
            if i < 8:  # 9:00-12:00
                morning_slots.append(slot_info)
            else:  # 13:00-16:40
                afternoon_slots.append(slot_info)
        
        return {
            "total_slots": len(slots),
            "morning_slots": morning_slots,
            "afternoon_slots": afternoon_slots
        }

    @tool
    def create_schedule(target_date: str) -> Dict[str, Any]:
        """Execute complete scheduling workflow from raw data - rebuilds all constraints.
        
        Use this for initial schedule creation or when starting fresh.
        
        Args:
            target_date: Target date in YYYY-MM-DD format
            
        Returns:
            Dictionary with date, total_assignments, unscheduled_patients count and IDs
        """
        # Full pipeline with fresh constraint building
        schedule = pipeline.full_pipeline(target_date, load=False)
        
        # Save schedule to DataStore for persistence
        data_store.save_schedule(schedule)
        
        return {
            "date": target_date,
            "total_assignments": len(schedule.assignments),
            "unscheduled_patients": len(schedule.unscheduled_patients),
            "unscheduled_patient_ids": schedule.unscheduled_patients,
        }
    
    @tool
    def update_schedule(target_date: str) -> Dict[str, Any]:
        """Re-run scheduling using existing constraint matrices with any modifications.
        
        Use this after making constraint changes with update_patient_availability.
        
        Args:
            target_date: Target date in YYYY-MM-DD format
            
        Returns:
            Dictionary with date, total_assignments, unscheduled_patients count and IDs
        """
        # Use existing matrices (preserves modifications)
        schedule = pipeline.full_pipeline(target_date, load=True)
        
        # Save schedule to DataStore for persistence
        data_store.save_schedule(schedule)
        
        return {
            "date": target_date,
            "total_assignments": len(schedule.assignments),
            "unscheduled_patients": len(schedule.unscheduled_patients),
            "unscheduled_patient_ids": schedule.unscheduled_patients,
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
            Dictionary with file_path and base64-encoded file_content
        """
        if not data_store.load_schedule():
            raise ScheduleNotAvailableError("No schedule available. Create a schedule first using create_schedule()")
        
        visualizer.export_to_excel(data_store, Path(output_path))
        
        # Read and encode file for client download
        import base64
        with open(output_path, 'rb') as f:
            file_content = base64.b64encode(f.read()).decode()
        
        return {"file_path": output_path, "file_content": file_content}
    
    @tool
    def get_schedule_data(patient_id: Optional[str] = None, 
                         therapist_id: Optional[str] = None) -> Dict[str, Any]:
        """Get schedule data for visualization. Returns raw assignment data that can be transformed to Mermaid or other formats.
        
        Args:
            patient_id: Optional patient ID to filter assignments
            therapist_id: Optional therapist ID to filter assignments
            
        Returns:
            Dictionary with enriched assignments list including patient and therapist attributes.
        """
        if not data_store.load_schedule():
            raise ScheduleNotAvailableError("No schedule available. Create a schedule first using create_schedule()")
        
        matrices = data_store.load_all_matrices()
        
        if patient_id and patient_id not in matrices.patient_ids:
            raise PatientNotFoundError(
                f"Patient '{patient_id}' not found in constraint matrices. "
                f"Available patients: {', '.join(map(str, matrices.patient_ids[:5]))}..."
            )
        
        if therapist_id and therapist_id not in matrices.therapist_ids:
            raise TherapistNotFoundError(
                f"Therapist '{therapist_id}' not found in constraint matrices. "
                f"Available therapists: {', '.join(map(str, matrices.therapist_ids[:5]))}..."
            )
        
        assignments = data_store.load_schedule().assignments
        therapists_df = data_store.load_normalized_therapists()
        prescriptions_df = data_store.load_normalized_prescriptions()
        
        if patient_id:
            assignments = [a for a in assignments if a.patient_id == patient_id]
        
        if therapist_id:
            assignments = [a for a in assignments if a.therapist_id == therapist_id]
        
        # Enrich assignments with attributes
        enriched_assignments = []
        for a in assignments:
            assignment_data = {
                "patient_id": a.patient_id,
                "therapist_id": a.therapist_id,
                "timeslot": a.timeslot,
                "duration_minutes": a.duration_minutes,
            }
            
            # Add patient attributes
            patient_row = prescriptions_df[prescriptions_df['患者ID'] == a.patient_id]
            if not patient_row.empty:
                assignment_data["patient_name"] = patient_row.iloc[0]['氏名']
                assignment_data["patient_ward"] = patient_row.iloc[0]['病棟']
                assignment_data["primary_therapist"] = patient_row.iloc[0]['担当療法士']
                assignment_data["category"] = patient_row.iloc[0]['算定区分']
            
            # Add therapist attributes
            therapist_row = therapists_df[therapists_df['職員ID'] == a.therapist_id]
            if not therapist_row.empty:
                assignment_data["therapist_name"] = therapist_row.iloc[0]['漢字氏名']
                assignment_data["therapist_gender"] = therapist_row.iloc[0]['性別']
                assignment_data["therapist_profession"] = therapist_row.iloc[0]['職種']
                assignment_data["therapist_ward"] = therapist_row.iloc[0]['担当病棟']
            
            enriched_assignments.append(assignment_data)
        
        return {
            "assignments": enriched_assignments,
            "filter": {
                "patient_id": patient_id,
                "therapist_id": therapist_id,
            }
        }
    
    @tool
    def describe_current_schedule() -> Dict[str, Any]:
        """Display detailed statistics about the current schedule.
        
        Returns:
            Dictionary with schedule_date, total_assignments, unique_patients, unique_therapists,
            unscheduled_patients, therapist_utilization, and patient_minutes
        """
        # Always load schedule from DataStore
        schedule = data_store.load_schedule()
        
        if not schedule:
            raise ScheduleNotAvailableError("No schedule available. Create a schedule first using create_schedule()")
        
        assignments = schedule.assignments
        therapist_loads = {}
        patient_coverage = {}
        
        for a in assignments:
            therapist_loads[a.therapist_id] = therapist_loads.get(a.therapist_id, 0) + 1
            patient_coverage[a.patient_id] = patient_coverage.get(a.patient_id, 0) + a.duration_minutes
        
        return {
            "schedule_date": schedule.date,
            "total_assignments": len(assignments),
            "unique_patients": len(patient_coverage),
            "unique_therapists": len(therapist_loads),
            "unscheduled_patients": len(schedule.unscheduled_patients),
            "therapist_utilization": therapist_loads,
            "patient_minutes": patient_coverage,
        }
    
    @tool
    def get_patient_schedule(patient_id: str) -> Dict[str, Any]:
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
                f"Available patients: {', '.join(map(str, matrices.patient_ids[:5]))}..."
            )
        
        idx = matrices.patient_ids.index(patient_id)
        available_slots = [
            matrices.timeslots[i] 
            for i in range(len(matrices.timeslots)) 
            if matrices.patient_availability[idx, i] == 1
        ]
        
        assignments = []
        if data_store.load_schedule():
            assignments = [
                {"therapist": a.therapist_id, "timeslot": a.timeslot, "duration": a.duration_minutes}
                for a in data_store.load_schedule().assignments 
                if a.patient_id == patient_id
            ]
        
        return {
            "patient_id": patient_id,
            "required_minutes": int(matrices.requirements[idx]),
            "available_timeslots": available_slots,
            "current_assignments": assignments,
        }
    
    @tool
    def get_therapist_schedule(therapist_id: str) -> Dict[str, Any]:
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
                f"Available therapists: {', '.join(map(str, matrices.therapist_ids[:5]))}..."
            )
        
        idx = matrices.therapist_ids.index(therapist_id)
        available_slots = [
            matrices.timeslots[i] 
            for i in range(len(matrices.timeslots)) 
            if matrices.therapist_availability[idx, i] == 1
        ]
        
        assignments = []
        if data_store.load_schedule():
            assignments = [
                {"patient": a.patient_id, "timeslot": a.timeslot, "duration": a.duration_minutes}
                for a in data_store.load_schedule().assignments 
                if a.therapist_id == therapist_id
            ]
        
        return {
            "therapist_id": therapist_id,
            "available_timeslots": available_slots,
            "current_assignments": assignments,
            "total_assigned_slots": len(assignments),
        }
    
    @tool
    def update_patient_availability(patient_id: str, timeslots: str, 
                                    available: bool) -> Dict[str, Any]:
        """Modify patient's availability for specific timeslots.
        
        Args:
            patient_id: Patient identifier
            timeslots: Single timeslot "HH:MM-HH:MM" or comma-separated multiple timeslots "HH:MM-HH:MM,HH:MM-HH:MM"
            available: True to make available, False to make unavailable
            
        Returns:
            Dictionary with patient_id, changes made, and summary
        """
        matrices = data_store.load_all_matrices()
        
        if patient_id not in matrices.patient_ids:
            raise PatientNotFoundError(
                f"Patient '{patient_id}' not found in constraint matrices. "
                f"Available patients: {', '.join(map(str, matrices.patient_ids[:5]))}..."
            )
        
        # Parse timeslots - handle both single and multiple
        timeslot_list = [slot.strip() for slot in timeslots.split(',')]
        
        patient_idx = matrices.patient_ids.index(patient_id)
        changes = []
        
        for timeslot in timeslot_list:
            if timeslot not in matrices.timeslots:
                raise InvalidTimeslotError(
                    f"Invalid timeslot '{timeslot}'. Must be one of: {', '.join(map(str, matrices.timeslots))}"
                )
            
            slot_idx = matrices.timeslots.index(timeslot)
            old_value = matrices.patient_availability[patient_idx, slot_idx]
            new_value = 1 if available else 0
            
            matrices.patient_availability[patient_idx, slot_idx] = new_value
            
            changes.append({
                "timeslot": timeslot,
                "old_value": int(old_value),
                "new_value": new_value
            })
        
        data_store.save_all_matrices(matrices)
        
        return {
            "patient_id": patient_id,
            "total_changes": len(changes),
            "changes": changes,
            "status": "available" if available else "unavailable"
        }

    return [
        create_schedule,
        update_schedule,
        export_schedule_excel,
        get_schedule_data,
        describe_current_schedule,
        get_patient_schedule,
        get_therapist_schedule,
        update_patient_availability,
        search_patients,
        search_therapists,
        list_available_timeslots,
    ]
