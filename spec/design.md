# Hospital Scheduling Automation - Architecture Design

## Design Philosophy

This tool uses **deterministic optimization** for scheduling with **AI agents for debugging and conversational optimization**. The core scheduler is fast and predictable, while AI assists only when needed for error analysis or constraint modifications.

## Technology Stack

- **CLI Framework**: `click` (thin wrappers for AgentCore deployment)
- **Optimization**: `scipy.optimize` for constraint-based scheduling
- **AI Agents**: `strands-agents` (debugging and conversation only)
- **Data Processing**: `pandas`, `numpy`
- **Data Validation**: `pydantic`
- **Visualization**: `jinja2`, Mermaid

## Module Structure: `schedule_agent/`

### 1. `cli.py`
**Role**: Minimal CLI entry points for AgentCore deployment

**Functions**:
- `preprocess()`: Load and normalize raw data
- `schedule(date: str)`: Run deterministic scheduler
- `optimize(date: str)`: Start conversational optimization
- `debug(error_file: str)`: Analyze scheduling failures
- `visualize(date: str)`: Generate schedule visualization

**Design**: Each function is 3-5 lines calling core modules. AgentCore will host these as agent endpoints.

---

### 2. `core/preprocessor.py`
**Role**: Load and normalize raw data with encoding handling

**Classes**:
- `DataLoader`: Load CSV/Excel with cp932 encoding
- `DataNormalizer`: Normalize ward names, therapist IDs, time formats
- `InterimWriter`: Save processed data to `data/interim/`

**Key Methods**:
- `load_therapists() -> pd.DataFrame`
- `load_prescriptions() -> pd.DataFrame`
- `load_shifts(year_month: str) -> pd.DataFrame`
- `normalize_and_save() -> None`

---

### 3. `core/constraints_builder.py`
**Role**: Build constraint matrices from preprocessed data

**Classes**:
- `ConstraintMatrixBuilder`: Main builder coordinating all matrices
- `PatientAvailabilityBuilder`: Build patient × timeslot matrix (P × 18)
- `TherapistAvailabilityBuilder`: Build therapist × timeslot matrix (Th × 18)
- `CompatibilityBuilder`: Build patient × therapist compatibility matrix (P × Th)
- `RequirementsBuilder`: Build therapy requirements vector (P,)

**Key Methods**:
- `build_all_matrices() -> ConstraintMatrices`
- `save_matrices(output_dir: Path) -> None`

**Data Model**:
```python
@dataclass
class ConstraintMatrices:
    patient_availability: np.ndarray  # (P, 18) - 1=available, 0=unavailable
    therapist_availability: np.ndarray  # (Th, 18) - 1=available, 0=unavailable
    compatibility: np.ndarray  # (P, Th) - higher score = better match
    requirements: np.ndarray  # (P,) - required minutes per patient
    patient_ids: list[str]
    therapist_ids: list[str]
    timeslots: list[str]  # ["09:00-09:20", "09:20-09:40", ...]
```

---

### 4. `core/scheduler.py`
**Role**: Deterministic scheduling using scipy optimization

**Classes**:
- `DeterministicScheduler`: Main scheduler using constraint matrices
- `ScheduleValidator`: Validate schedule meets all constraints
- `AssignmentOptimizer`: Optimize therapist assignments using scipy

**Key Methods**:
- `schedule(matrices: ConstraintMatrices) -> Schedule`
- `validate(schedule: Schedule) -> ValidationResult`
- `optimize_assignments() -> np.ndarray`  # Uses scipy.optimize.linear_sum_assignment

**Algorithm**:
1. Sort patients by required minutes (180-min first)
2. For each patient, use scipy to find optimal therapist-timeslot assignments
3. Update availability matrices after each assignment
4. Raise `InfeasibleScheduleError` if constraints cannot be satisfied

**Data Model**:
```python
@dataclass
class Assignment:
    patient_id: str
    therapist_id: str
    timeslot: str
    duration_minutes: int

@dataclass
class Schedule:
    assignments: list[Assignment]
    date: str
    unscheduled_patients: list[str]
```

---

### 5. `core/debug_agent.py`
**Role**: AI agent for analyzing scheduling failures

**Classes**:
- `DebugAgent`: Strands agent with diagnostic tools
- `ConstraintAnalyzer`: Analyze constraint matrices for conflicts
- `SuggestionGenerator`: Generate specific fix recommendations

**Agent Tools**:
- `analyze_patient_constraints(patient_id: str) -> dict`
- `analyze_therapist_availability(therapist_id: str) -> dict`
- `find_bottlenecks() -> list[dict]`
- `suggest_fixes() -> list[str]`

**Key Methods**:
- `diagnose(error: InfeasibleScheduleError) -> DiagnosisReport`
- `chat(user_message: str) -> str`  # Interactive debugging

---

### 6. `core/constraint_agent.py`
**Role**: Conversational agent for constraint modification

**Classes**:
- `ConstraintAgent`: Strands agent for interactive optimization
- `MatrixModifier`: Modify constraint matrices based on user requests
- `ModificationLogger`: Log all constraint changes

**Agent Tools**:
- `update_patient_availability(patient_id: str, timeslot: str, available: bool) -> str`
- `update_compatibility(patient_id: str, therapist_id: str, score: int) -> str`
- `show_current_assignment(patient_id: str) -> dict`
- `list_compatible_therapists(patient_id: str) -> list[dict]`
- `reschedule() -> Schedule`

**Key Methods**:
- `chat(user_message: str) -> str`  # Main conversational interface
- `apply_modifications() -> ConstraintMatrices`

---

### 7. `models/data_models.py`
**Role**: Pydantic models for data validation

**Models**:
- `Therapist`: Therapist attributes from therapist.csv
- `Prescription`: Patient prescription from prescription.csv
- `ShiftEntry`: Therapist shift availability
- `TimeSlot`: 20-minute scheduling unit
- `InfeasibleScheduleError`: Custom exception with diagnostic info

---

### 8. `utils/time_utils.py`
**Role**: Time slot management utilities

**Functions**:
- `generate_timeslots() -> list[str]`: Generate 18 timeslots
- `parse_unavailable_times(time_str: str) -> list[str]`: Parse patient unavailable times
- `timeslot_to_index(timeslot: str) -> int`: Convert timeslot to matrix index
- `check_shift_availability(shift_code: str, timeslot: str) -> bool`: Check if therapist available

---

### 9. `utils/visualization.py`
**Role**: Generate schedule visualizations

**Classes**:
- `ScheduleVisualizer`: Generate Mermaid diagrams and Excel exports
- `GanttChartGenerator`: Create Gantt chart visualization

**Key Methods**:
- `generate_mermaid(schedule: Schedule) -> str`
- `export_to_excel(schedule: Schedule, output_path: Path) -> None`
- `create_gantt_chart(schedule: Schedule) -> str`

---

## Data Flow

```
Raw Data (CSV/Excel)
    ↓
[preprocessor.py] → data/interim/normalized_*.csv
    ↓
[constraints_builder.py] → data/interim/*.npy (constraint matrices)
    ↓
[scheduler.py] → Schedule object
    ↓
    ├─ Success → [visualization.py] → Excel/Mermaid output
    └─ Failure → [debug_agent.py] → Diagnosis & suggestions
    
User modifications → [constraint_agent.py] → Updated matrices → Re-schedule
```

## CLI Command Implementation

Each CLI command in `cli.py` is minimal:

```python
@click.command()
@click.option('--date', required=True)
def schedule(date: str):
    """Run deterministic scheduler."""
    matrices = load_constraint_matrices()
    scheduler = DeterministicScheduler()
    result = scheduler.schedule(matrices)
    save_schedule(result, date)
```

This design allows AgentCore to host these functions directly as agent endpoints with minimal wrapper code.

## Constraint Matrix Design

### Patient Availability Matrix (P × 18)
- Rows: Patients
- Columns: 18 timeslots (9:00-16:40)
- Values: 1 = available, 0 = unavailable (bathing, excretion, other restrictions)

### Therapist Availability Matrix (Th × 18)
- Rows: Therapists
- Columns: 18 timeslots
- Values: 1 = available, 0 = unavailable (shift codes: 〇, AN, PN)

### Compatibility Matrix (P × Th)
- Rows: Patients
- Columns: Therapists
- Values: Score (0-100)
  - 100: Primary therapist
  - 80: Same ward, same gender
  - 60: Same gender only
  - 40: Same ward only
  - 20: Different ward, different gender
  - 0: Incompatible (専従 constraint violation)

### Requirements Vector (P,)
- Index: Patient
- Value: Required minutes (180 or 120)

## Optimization Strategy

Using `scipy.optimize.linear_sum_assignment` for each patient:
1. Create cost matrix: `-compatibility × availability`
2. Find optimal therapist-timeslot pairs
3. Assign minimum required slots (6 or 9 slots)
4. Update availability matrices
5. Repeat for next patient

## Error Handling

When scheduling fails:
1. Save error state to `data/interim/error_state.json`
2. Automatically invoke `DebugAgent`
3. Agent analyzes constraint matrices
4. Agent provides specific recommendations:
   - "Patient P123 has only 2 available timeslots but needs 9"
   - "Therapist T005 is overbooked by 4 slots"
   - "Consider making Patient P123 available at 14:00-15:00"

## Conversational Optimization Flow

1. User: "Patient 123 can be available at 14:00"
2. Agent: Parses request → calls `update_patient_availability()`
3. Agent: Confirms modification → logs change
4. User: "Reschedule"
5. Agent: Calls `reschedule()` → returns updated schedule
6. Agent: Shows changes and new assignments

## File Structure

```
schedule_agent/
├── __init__.py
├── cli.py                          # Minimal CLI entry points
├── core/
│   ├── __init__.py
│   ├── preprocessor.py             # Data loading & normalization
│   ├── constraints_builder.py     # Build constraint matrices
│   ├── scheduler.py                # Deterministic scheduling (scipy)
│   ├── debug_agent.py              # AI debugging agent
│   └── constraint_agent.py         # Conversational optimization agent
├── models/
│   ├── __init__.py
│   └── data_models.py              # Pydantic models
└── utils/
    ├── __init__.py
    ├── time_utils.py               # Time slot utilities
    └── visualization.py            # Excel/Mermaid generation

data/
├── raw/                            # Original CSV/Excel files
├── interim/                        # Processed data & matrices
│   ├── normalized_therapists.csv
│   ├── normalized_prescriptions.csv
│   ├── normalized_shifts.csv
│   ├── patient_availability.npy
│   ├── therapist_availability.npy
│   ├── compatibility.npy
│   ├── requirements.npy
│   └── constraint_modifications.log
└── processed/                      # Final schedules
    └── schedule_2025-10-04.xlsx
```

## Development Priorities

1. **Phase 1**: Implement `preprocessor.py` and `constraints_builder.py`
2. **Phase 2**: Implement `scheduler.py` with scipy optimization
3. **Phase 3**: Implement `debug_agent.py` with diagnostic tools
4. **Phase 4**: Implement `constraint_agent.py` for conversational optimization
5. **Phase 5**: Add `visualization.py` and polish CLI

## Key Design Benefits

- **Fast**: Deterministic scheduler runs in seconds using scipy
- **Transparent**: Constraint matrices are inspectable numpy arrays
- **Flexible**: AI agents allow conversational constraint modification
- **AgentCore-Ready**: Minimal CLI wrappers for easy deployment
- **Debuggable**: Clear error messages with specific patient/therapist IDs
- **Cost-Effective**: AI only used for debugging and conversation, not core scheduling
