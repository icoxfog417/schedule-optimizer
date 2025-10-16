from .data_store import DataStore
from .preprocessor import DataNormalizer
from .constraints_builder import ConstraintMatrixBuilder
from .scheduler import DeterministicScheduler
from ..models.data_models import Schedule


class SchedulingPipeline:
    """Orchestrates processing using DataStore for I/O."""
    
    def __init__(self, data_store: DataStore):
        self.store = data_store
        self.normalizer = DataNormalizer()
        self.builder = ConstraintMatrixBuilder()
        self.scheduler = DeterministicScheduler()
    
    # Granular operations
    def preprocess_therapists(self) -> None:
        therapists = self.store.load_therapists()
        normalized = self.normalizer.normalize_therapists(therapists)
        self.store.save_normalized_therapists(normalized)
    
    def preprocess_prescriptions(self) -> None:
        prescriptions = self.store.load_prescriptions()
        normalized = self.normalizer.normalize_prescriptions(prescriptions)
        self.store.save_normalized_prescriptions(normalized)
    
    def preprocess_shifts(self, target_date: str) -> None:
        shifts = self.store.load_shifts()
        normalized = self.normalizer.normalize_shifts(shifts, target_date)
        self.store.save_normalized_shifts(normalized)
    
    def build_patient_constraints(self) -> None:
        prescriptions = self.store.load_normalized_prescriptions()
        matrix = self.builder.build_patient_availability(prescriptions)
        self.store.save_patient_availability(matrix)
    
    def build_therapist_constraints(self) -> None:
        therapists = self.store.load_normalized_therapists()
        shifts = self.store.load_normalized_shifts()
        matrix = self.builder.build_therapist_availability(therapists, shifts)
        self.store.save_therapist_availability(matrix)
    
    def build_compatibility_matrix(self) -> None:
        therapists = self.store.load_normalized_therapists()
        prescriptions = self.store.load_normalized_prescriptions()
        matrix = self.builder.build_compatibility(therapists, prescriptions)
        self.store.save_compatibility_matrix(matrix)
    
    def build_requirements_vector(self) -> None:
        prescriptions = self.store.load_normalized_prescriptions()
        vector = self.builder.build_requirements(prescriptions)
        self.store.save_requirements_vector(vector)
    
    # Complete operations
    def preprocess_all(self, target_date: str) -> None:
        self.preprocess_therapists()
        self.preprocess_prescriptions()
        self.preprocess_shifts(target_date)
    
    def build_all_constraints(self) -> None:
        therapists = self.store.load_normalized_therapists()
        prescriptions = self.store.load_normalized_prescriptions()
        shifts = self.store.load_normalized_shifts()
        
        matrices = self.builder.build_matrices(therapists, prescriptions, shifts)
        self.store.save_all_matrices(matrices)
    
    def schedule(self, date: str) -> Schedule:
        matrices = self.store.load_all_matrices()
        schedule = self.scheduler.schedule(matrices)
        schedule.date = date
        self.store.save_schedule(schedule)
        return schedule
    
    def full_pipeline(self, date: str, load: bool = False) -> Schedule:
        if not load:
            # Fresh creation: preprocess and build constraints
            self.preprocess_all(date)
            self.build_all_constraints()
        # For load=True: skip preprocessing and constraint building, use existing matrices
        
        return self.schedule(date)
