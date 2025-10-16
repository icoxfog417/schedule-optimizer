import numpy as np
from ..models.data_models import (
    ConstraintMatrices,
    Schedule,
    Assignment,
    InfeasibleScheduleError,
    ValidationResult,
)


class DeterministicScheduler:
    """Deterministic scheduling using scipy optimization."""
    
    def schedule(self, matrices: ConstraintMatrices) -> Schedule:
        """Create schedule from constraint matrices."""
        assignments = []
        unscheduled = []
        
        # Create working copies
        patient_avail = matrices.patient_availability.copy()
        therapist_avail = matrices.therapist_availability.copy()
        
        # Sort patients by required minutes (180-min first)
        patient_order = np.argsort(-matrices.requirements)
        
        for patient_idx in patient_order:
            patient_id = matrices.patient_ids[patient_idx]
            required_minutes = matrices.requirements[patient_idx]
            required_slots = required_minutes // 20
            
            try:
                patient_assignments = self._assign_patient(
                    patient_idx,
                    required_slots,
                    patient_avail,
                    therapist_avail,
                    matrices
                )
                assignments.extend(patient_assignments)
            except InfeasibleScheduleError:
                unscheduled.append(patient_id)
        
        return Schedule(
            assignments=assignments,
            date="",
            unscheduled_patients=unscheduled
        )
    
    def _assign_patient(
        self,
        patient_idx: int,
        required_slots: int,
        patient_avail: np.ndarray,
        therapist_avail: np.ndarray,
        matrices: ConstraintMatrices
    ) -> list[Assignment]:
        """Assign timeslots for a single patient."""
        patient_id = matrices.patient_ids[patient_idx]
        
        # Get patient's available slots
        available_slots = np.where(patient_avail[patient_idx] == 1)[0]
        
        if len(available_slots) < required_slots:
            raise InfeasibleScheduleError(
                f"Patient {patient_id} needs {required_slots} slots but only {len(available_slots)} available",
                patient_id=patient_id
            )
        
        # Build cost matrix for this patient
        # Rows: timeslots, Columns: therapists
        # Cost = -compatibility + workload_penalty (5 points per assignment)
        therapist_assignments = np.sum(1 - therapist_avail, axis=1)
        workload_penalty = therapist_assignments * 5
        
        cost_matrix = np.zeros((len(available_slots), len(matrices.therapist_ids)))
        
        for i, slot_idx in enumerate(available_slots):
            for j, therapist_id in enumerate(matrices.therapist_ids):
                if therapist_avail[j, slot_idx] == 1:
                    compatibility = matrices.compatibility[patient_idx, j]
                    if compatibility > 0:
                        cost_matrix[i, j] = -compatibility + workload_penalty[j]
                    else:
                        cost_matrix[i, j] = 1000  # Incompatible
                else:
                    cost_matrix[i, j] = 1000  # Therapist not available
        
        # Find optimal assignment
        assignments = []
        assigned_slots = 0
        
        # Greedy approach: assign best therapist-slot pairs
        while assigned_slots < required_slots:
            if cost_matrix.min() >= 1000:
                raise InfeasibleScheduleError(
                    f"Cannot find therapist for patient {patient_id}",
                    patient_id=patient_id
                )
            
            # Find best slot-therapist pair
            slot_i, therapist_j = np.unravel_index(cost_matrix.argmin(), cost_matrix.shape)
            slot_idx = available_slots[slot_i]
            therapist_id = matrices.therapist_ids[therapist_j]
            timeslot = matrices.timeslots[slot_idx]
            
            # Create assignment
            assignments.append(Assignment(
                patient_id=patient_id,
                therapist_id=therapist_id,
                timeslot=timeslot,
                duration_minutes=20
            ))
            
            # Update availability
            patient_avail[patient_idx, slot_idx] = 0
            therapist_avail[therapist_j, slot_idx] = 0
            
            # Mark this slot-therapist pair as used
            cost_matrix[slot_i, :] = 1000
            
            assigned_slots += 1
        
        return assignments


class ScheduleValidator:
    """Validate schedule meets all constraints."""
    
    def validate(self, schedule: Schedule, matrices: ConstraintMatrices) -> ValidationResult:
        """Validate schedule against constraints."""
        errors = []
        
        # Check each patient has required minutes
        patient_minutes = {}
        for assignment in schedule.assignments:
            patient_minutes[assignment.patient_id] = patient_minutes.get(assignment.patient_id, 0) + 20
        
        for i, patient_id in enumerate(matrices.patient_ids):
            required = matrices.requirements[i]
            actual = patient_minutes.get(patient_id, 0)
            if actual < required:
                errors.append(f"Patient {patient_id}: needs {required}min, got {actual}min")
        
        # Check no double-booking
        therapist_slots = {}
        for assignment in schedule.assignments:
            key = (assignment.therapist_id, assignment.timeslot)
            if key in therapist_slots:
                errors.append(f"Double booking: {assignment.therapist_id} at {assignment.timeslot}")
            therapist_slots[key] = True
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors
        )
