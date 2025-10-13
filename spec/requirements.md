# Hospital Scheduling Automation - Requirements Specification

## Objective
Automate the scheduling of patients and therapists by assigning patients to therapists' available schedules while considering multiple constraints and priorities.

## Data Sources

### 1. therapist.csv (encoding: cp932)
- **Purpose**: List of available therapists with their attributes
- **Key Fields**:
  - `漢字氏名`: Primary key for matching with prescription and shift data
  - `性別`: Gender (crucial for patient assignment when primary therapist unavailable)
  - `専従`: Exclusive assignment flag ("〇" = cannot care for other location patients)
  - `担当病棟`: Assigned ward/location (W=West, E=East)

### 2. prescription.csv (encoding: cp932)
- **Purpose**: Time-series data of patient therapy prescriptions from doctors
- **Key Fields**:
  - Patient identification and therapy requirements
  - `病棟`: Patient location (constrains assignable therapists)
  - `担当療法士`: Assigned therapist (matches therapist.csv `漢字氏名`)
  - `算定区分`: Therapy classification (determines minimum daily time)
  - `入浴`: Bathing time (unavailable for therapy)
  - `排泄`: Excretion care time (unavailable for therapy)
  - `その他指定時間`: Other specified unavailable times
- **Data Handling**: Latest record per patient takes priority

### 3. shift_202510.xlsx
- **Purpose**: Therapist availability schedule
- **Structure**:
  - Data starts from row 2
  - Columns 0-3: Therapist attributes
  - Columns 4+: Date and day of week
- **Availability Codes**:
  - `〇`: Available full day
  - `AN`: Available 12:45-17:30 only
  - `PN`: Available 8:45-12:00 only

## Scheduling Constraints

### Time Management
1. **Time Unit**: 20 minutes = 1 scheduling unit
2. **Minimum Daily Therapy Time**:
   - Patients with `算定区分` containing "脳血管疾患": 180 minutes/day
   - All other patients: 120 minutes/day
3. **Available Time Slots**:
   - Morning: 9:00-9:40, 9:45-10:25, 10:30-11:10, 11:15-11:55
   - Afternoon: 13:00-13:40, 13:45-14:25, 14:30-15:10, 15:15-15:55, 16:00-16:40

### Patient Constraints
1. **Individual Care Times**: Must avoid `入浴` and `排泄` times
2. **Specified Restrictions**: Must consider `その他指定時間` constraints

### Therapist Assignment Priorities
When primary therapist (`担当療法士`) is unavailable, prioritize alternatives by:
1. **Primary**: `入浴` and `排泄` care requirements
2. **Secondary**: Avoid patient's unavailable times
3. **Tertiary**: Same gender (`性別`) as primary therapist
4. **Quaternary**: Same location (`担当病棟`) if therapist has `専従` = "〇"

## Success Criteria
- All patients receive minimum required therapy time
- No scheduling conflicts with patient care times
- Therapist assignments respect availability and constraints
- Optimal utilization of available therapy slots
