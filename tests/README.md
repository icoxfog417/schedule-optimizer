# Hospital Scheduling System - Test Implementation

## Background

The approach focuses on **critical path testing**: preprocessing → constraint building → scheduling, as these are the core components that determine system functionality.

### Test Strategy Rationale

From the test case planning document:
- **Focus on critical path**: Other components (time_utils, visualization, CLI) are tested implicitly through core workflows
- **17 focused test cases** across 4 modules provide comprehensive coverage
- **Real data structure**: Tests use actual hospital data formats (cp932 encoding, Excel shift files)
- **Deterministic validation**: Scheduling algorithm must produce consistent, predictable results

## Test Implementation Overview

### 1. Preprocessor Tests (`test_preprocessor.py`) - 7 test cases

**Purpose**: Validate data loading and normalization from raw files with Japanese encoding

#### TC1.1: Load therapist data
- **File**: `test_preprocessor_therapist.csv`
- **Data Content**:
  ```csv
  職員ID,漢字氏名,性別,職種,担当病棟,専従
  T001,山田太郎,男,理学療法士,3階西病棟,
  T002,佐藤花子,女,作業療法士,3階東病棟,〇
  ```
- **Why this satisfies requirements**: 
  - Tests cp932 encoding with Japanese characters (漢字氏名)
  - Validates parsing of key fields: 性別 (gender), 専従 (exclusive flag)
  - Includes both empty and filled 専従 values to test constraint logic
  - Uses realistic hospital ward names (3階西病棟, 3階東病棟)

#### TC1.2: Load prescription data
- **File**: `test_preprocessor_prescription.csv`
- **Data Content**:
  ```csv
  患者ID,氏名,病棟,年齢,病名,担当療法士,依頼科,算定区分,入浴,排泄,早食,経管栄養,その他指定時間
  1001,患者A,3階西病棟,65,脳梗塞,山田太郎,神経内科,脳血管疾患等Ⅰ,10:00-10:20,,,,
  1002,患者B,3階東病棟,70,骨折,佐藤花子,整形外科,運動器疾患Ⅰ,,14:00-14:20,,,
  ```
- **Why this satisfies requirements**:
  - Tests both therapy types: 脳血管疾患等Ⅰ (180 min) and 運動器疾患Ⅰ (120 min)
  - Validates time constraint parsing: 入浴 (bathing) and 排泄 (excretion) times
  - Matches therapist names with therapist.csv for relationship validation
  - Uses realistic patient IDs (numeric) and ward assignments

#### TC1.2: Handle duplicate patient records
- **File**: `test_preprocessor_prescription_duplicates.csv`
- **Data Content**:
  ```csv
  患者ID,氏名,病棟,年齢,病名,担当療法士,依頼科,算定区分,入浴,排泄,早食,経管栄養,その他指定時間
  1001,患者A,3階西病棟,65,脳梗塞,山田太郎,神経内科,脳血管疾患等Ⅰ,10:00-10:20,,,,
  1001,患者A,3階西病棟,65,脳梗塞,佐藤花子,神経内科,脳血管疾患等Ⅰ,11:00-11:20,,,,
  ```
- **Why this satisfies requirements**:
  - Same patient ID (1001) with different therapist assignments
  - Different bathing times (10:00 vs 11:00) to verify latest record wins
  - Tests real-world scenario where prescriptions are updated over time

#### TC1.3: Load shift data
- **File**: `test_preprocessor_shift.xlsx`
- **Excel Structure**:
  ```
  Row 0: [Empty header row]
  Row 1: [利用者属性, 職種, 療法区分, 名前, 1\n水, 2\n木, 3\n金, 4\n土]
  Row 2: [, 理学療法士, 理学, 山田太郎, ○, ○, ○, 週]
  Row 3: [, 作業療法士, 作業, 佐藤花子, AN, PN, ○, 週]
  ```
- **Why this satisfies requirements**:
  - Matches actual Excel format from requirements (data starts row 2, columns 4+)
  - Tests all availability codes: ○ (full day), AN (afternoon), PN (morning), 週 (weekly)
  - Uses realistic therapist names matching other test files
  - Validates Excel parsing with Japanese headers and newline characters

### 2. Constraints Builder Tests (`test_constraints_builder.py`) - 6 test cases

**Purpose**: Validate constraint matrix generation from preprocessed data

#### TC2.1: Patient availability matrix
- **File**: `test_constraints_prescription.csv`
- **Key Data**: Patient 1001 has 入浴=10:00-10:20, Patient 1002 has 排泄=14:00-14:20
- **Why this satisfies requirements**:
  - Tests blocking of specific timeslots based on care times
  - Validates 18-timeslot matrix generation (9:00-16:40 in 20-min units)
  - Ensures unavailable times are marked as 0, available as 1

#### TC2.2: Therapist availability matrix
- **Files**: `test_constraints_therapist.csv` + `test_constraints_shift.xlsx`
- **Key Data**: 山田太郎 has ○ (full availability), 佐藤花子 has AN (afternoon only)
- **Why this satisfies requirements**:
  - Tests shift code interpretation: ○ = all 18 slots, AN = slots 9-17 only
  - Validates therapist-timeslot matrix (Th × 18) generation
  - Ensures proper availability mapping from Excel shift data

#### TC2.3: Compatibility matrix
- **Files**: `test_constraints_therapist.csv` + `test_constraints_prescription.csv`
- **Key Relationships**: 
  - Patient 1001 → Primary therapist 山田太郎
  - Patient 1002 → Primary therapist 佐藤花子
- **Why this satisfies requirements**:
  - Tests primary therapist scoring (should be 100)
  - Validates cross-assignment scoring based on gender/ward matching
  - Ensures patient-therapist compatibility matrix (P × Th) generation

#### TC2.4: Exclusive ward constraint
- **Files**: `test_constraints_therapist_exclusive.csv` + `test_constraints_prescription_exclusive.csv`
- **Key Data**: 
  ```csv
  # Therapist: T001,山田太郎,男,理学療法士,3階西病棟,〇  (exclusive)
  # Patient: 1002,患者B,3階東病棟,... (different ward)
  ```
- **Why this satisfies requirements**:
  - Tests 専従="〇" constraint: therapist cannot care for other ward patients
  - Validates compatibility score = 0 for incompatible ward assignments
  - Ensures exclusive constraint blocks cross-ward assignments

#### TC2.5: Requirements vector
- **File**: `test_constraints_prescription.csv`
- **Key Data**: 
  - Patient 1001: 算定区分=脳血管疾患等Ⅰ (should require 9 slots = 180 min)
  - Patient 1002: 算定区分=運動器疾患Ⅰ (should require 6 slots = 120 min)
- **Why this satisfies requirements**:
  - Tests therapy type to time requirement mapping
  - Validates requirements vector generation (P,) with correct slot counts
  - Ensures minimum daily therapy time constraints are properly encoded

### 3. Scheduler Tests (`test_scheduler.py`) - 6 test cases

**Purpose**: Validate deterministic scheduling algorithm with constraint matrices

#### TC3.1: Simple feasible schedule
- **Files**: `test_scheduler_therapist.csv` + `test_scheduler_prescription.csv` + `test_scheduler_shift.xlsx`
- **Key Data**: 
  - 2 patients requiring 6 slots each (運動器疾患Ⅰ)
  - 2 therapists with full availability (○)
  - Total capacity: 36 slots (2 therapists × 18 slots)
  - Total demand: 12 slots (2 patients × 6 slots)
- **Why this satisfies requirements**:
  - Tests basic feasible scheduling with ample capacity
  - Validates all patients receive required therapy time
  - Ensures no scheduling conflicts or unscheduled patients

#### TC3.2: Respect patient unavailability
- **Files**: Uses constraint data with blocked times (bathing/excretion)
- **Key Constraints**: Patient 1001 blocked at 10:00, Patient 1002 blocked at 14:00
- **Why this satisfies requirements**:
  - Tests avoidance of patient care times (入浴, 排泄)
  - Validates scheduler respects patient availability matrix
  - Ensures no assignments during blocked timeslots

#### TC3.3: Respect therapist unavailability
- **File**: `test_scheduler_shift_afternoon.xlsx`
- **Key Data**: Therapist with AN availability (afternoon only)
- **Why this satisfies requirements**:
  - Tests shift code constraint enforcement
  - Validates scheduler respects therapist availability matrix
  - Ensures no morning assignments for afternoon-only therapists

#### TC3.4: Primary therapist preference
- **Data**: Patients assigned to their primary therapists in test data
- **Why this satisfies requirements**:
  - Tests compatibility matrix utilization in scheduling
  - Validates preference for primary therapist (score 100)
  - Ensures optimal therapist-patient matching

#### TC3.6: Deterministic output
- **Method**: Run same constraints twice, compare results
- **Why this satisfies requirements**:
  - Tests scipy optimization consistency
  - Validates reproducible scheduling results
  - Ensures algorithm stability for production use

### 4. End-to-End Tests (`test_e2e.py`) - 2 test cases

**Purpose**: Validate complete workflow from raw data to schedule output

#### TC4.1: Full pipeline
- **Files**: Complete set of preprocessor test files
- **Workflow**: Raw data → Preprocessing → Constraints → Scheduling → Validation
- **Why this satisfies requirements**:
  - Tests entire system integration
  - Validates data flow through all modules
  - Ensures end-to-end functionality with realistic data

#### TC4.2: Pipeline with constraints
- **Files**: Constraint test files with blocked times and availability restrictions
- **Why this satisfies requirements**:
  - Tests realistic constraint handling in full pipeline
  - Validates complex scheduling scenarios
  - Ensures constraint violations are properly avoided

## Test Data Design Principles

### 1. Minimal but Complete
Each test file contains only the data needed for specific test cases, avoiding unnecessary complexity while maintaining realistic structure.

### 2. Realistic Hospital Data
- Japanese characters and encoding (cp932)
- Actual ward names (3階西病棟, 3階東病棟)
- Real therapy types (脳血管疾患等Ⅰ, 運動器疾患Ⅰ)
- Authentic time formats (10:00-10:20)

### 3. Constraint Validation
Test data is designed to trigger specific constraint scenarios:
- Blocked timeslots (bathing/excretion times)
- Therapist availability restrictions (AN, PN codes)
- Ward exclusivity constraints (専従 flag)
- Therapy time requirements (180 min vs 120 min)

### 4. Relationship Consistency
All test files maintain consistent relationships:
- Therapist names match across files
- Patient-therapist assignments are valid
- Ward assignments are consistent
- Time constraints are realistic

## Running Tests

```bash
# All tests (17 test cases)
pytest tests/ -v

# Individual modules
pytest tests/test_preprocessor.py -v      # 7 test cases
pytest tests/test_constraints_builder.py -v  # 6 test cases  
pytest tests/test_scheduler.py -v        # 6 test cases
pytest tests/test_e2e.py -v             # 2 test cases

# With coverage report
pytest tests/ --cov=schedule_agent --cov-report=html
```

## Expected Test Results

- **All 17 tests should pass** with properly implemented modules
- **Coverage should exceed 80%** for core modules
- **Test execution should complete in < 10 seconds**
- **No encoding errors** with Japanese character data
- **Deterministic results** across multiple test runs

This test suite provides comprehensive validation of the hospital scheduling system's core functionality while maintaining focus on the critical path components that determine system success.
