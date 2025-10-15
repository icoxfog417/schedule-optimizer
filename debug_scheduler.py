import numpy as np
from schedule_agent.models.data_models import (
    ConstraintMatrices,
    Schedule,
    Assignment,
    InfeasibleScheduleError,
)

def debug_assign_patient(
    patient_idx: int,
    required_slots: int,
    patient_avail: np.ndarray,
    therapist_avail: np.ndarray,
    matrices: ConstraintMatrices
) -> list[Assignment]:
    """Debug version of _assign_patient method."""
    patient_id = matrices.patient_ids[patient_idx]
    
    print(f"\n=== Assigning patient {patient_id} (needs {required_slots} slots) ===")
    
    # Get patient's available slots
    available_slots = np.where(patient_avail[patient_idx] == 1)[0]
    print(f"Patient available slots: {len(available_slots)} out of 18")
    
    if len(available_slots) < required_slots:
        raise InfeasibleScheduleError(
            f"Patient {patient_id} needs {required_slots} slots but only {len(available_slots)} available",
            patient_id=patient_id
        )
    
    # Build cost matrix for this patient
    # Rows: timeslots, Columns: therapists
    # Cost = -compatibility * availability
    cost_matrix = np.zeros((len(available_slots), len(matrices.therapist_ids)))
    
    print(f"Building cost matrix: {cost_matrix.shape}")
    for i, slot_idx in enumerate(available_slots[:3]):  # Debug first 3 slots
        for j, therapist_id in enumerate(matrices.therapist_ids):
            if therapist_avail[j, slot_idx] == 1:
                compatibility = matrices.compatibility[patient_idx, j]
                if compatibility > 0:
                    cost_matrix[i, j] = -compatibility
                    print(f"  Slot {i}, Therapist {j}: cost = -{compatibility}")
                else:
                    cost_matrix[i, j] = 1000  # Incompatible
                    print(f"  Slot {i}, Therapist {j}: incompatible (1000)")
            else:
                cost_matrix[i, j] = 1000  # Therapist not available
                print(f"  Slot {i}, Therapist {j}: unavailable (1000)")
    
    print(f"Cost matrix min: {cost_matrix.min()}")
    print(f"Cost matrix shape: {cost_matrix.shape}")
    
    # Find optimal assignment
    assignments = []
    assigned_slots = 0
    
    # Greedy approach: assign best therapist-slot pairs
    while assigned_slots < required_slots:
        print(f"\n--- Assignment {assigned_slots + 1}/{required_slots} ---")
        print(f"Current cost matrix min: {cost_matrix.min()}")
        
        if cost_matrix.min() >= 1000:
            print("ERROR: All costs >= 1000, cannot assign")
            raise InfeasibleScheduleError(
                f"Cannot find therapist for patient {patient_id}",
                patient_id=patient_id
            )
        
        # Find best slot-therapist pair
        slot_i, therapist_j = np.unravel_index(cost_matrix.argmin(), cost_matrix.shape)
        slot_idx = available_slots[slot_i]
        therapist_id = matrices.therapist_ids[therapist_j]
        timeslot = matrices.timeslots[slot_idx]
        
        print(f"Best assignment: slot {slot_i} ({timeslot}) -> therapist {therapist_j} ({therapist_id})")
        print(f"Cost: {cost_matrix[slot_i, therapist_j]}")
        
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
        cost_matrix[:, therapist_j] = 1000
        
        assigned_slots += 1
        print(f"Assignment created. Total: {assigned_slots}")
    
    return assignments

# Test with minimal data
patient_availability = np.ones((1, 18), dtype=int)
therapist_availability = np.ones((1, 18), dtype=int)
compatibility = np.array([[100]], dtype=int)
requirements = np.array([120], dtype=int)

timeslots = [f'{9+i//9}:{(i%9)*20:02d}-{9+i//9}:{(i%9)*20+20:02d}' for i in range(18)]

matrices = ConstraintMatrices(
    patient_availability=patient_availability,
    therapist_availability=therapist_availability,
    compatibility=compatibility,
    requirements=requirements,
    patient_ids=['P001'],
    therapist_ids=['T001'],
    timeslots=timeslots
)

try:
    assignments = debug_assign_patient(
        0,  # patient_idx
        6,  # required_slots
        patient_availability.copy(),
        therapist_availability.copy(),
        matrices
    )
    print(f"\nSUCCESS: Got {len(assignments)} assignments")
except Exception as e:
    print(f"\nFAILED: {e}")
