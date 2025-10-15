# Schedule Agent Implementation

## Overview

Unified AI agent for hospital therapy scheduling using Strands Agents framework. The agent orchestrates existing proven components (SchedulingPipeline, ScheduleVisualizer, DataStore) to handle the complete workflow: creation, visualization, error analysis, and optimization.

## Architecture

```
schedule_agent/agent/
├── config.py      # Agent configuration and system prompt (separated from implementation)
├── tools.py       # Tool implementations with meaningful exceptions
├── agent.py       # Main agent creation and configuration
└── run.py         # CLI entry point for interactive mode
```

## Key Design Decisions

### 1. Configuration Separation
- `config.py` contains all prompts, model settings, and parameters
- Implementation in `tools.py` and `agent.py` is independent
- Easy to modify agent behavior without touching code

### 2. Meaningful Exceptions
Tools raise specific exceptions instead of returning error dictionaries:
- `ScheduleNotAvailableError`: No schedule created yet
- `PatientNotFoundError`: Patient ID not in matrices
- `TherapistNotFoundError`: Therapist ID not in matrices
- `InvalidTimeslotError`: Invalid timeslot format

This gives the agent better insight into what went wrong and how to guide the user.

### 3. Agent-Generated Visualizations
- `get_schedule_data()` returns raw assignment data
- Agent transforms data into Mermaid Gantt charts itself
- Leverages Claude's native capability for format transformation
- More flexible than pre-generated visualizations

### 4. Exception-Based Error Analysis
- No separate `analyze_scheduling_error()` tool
- Agent reads exception messages from scheduling failures
- Uses `get_patient_details()` and `get_therapist_details()` to investigate
- More natural and context-aware error handling

## Tools

### Core Pipeline Operations
- **create_schedule**: Execute complete workflow from data files to final schedule

### Visualization Tools
- **export_schedule_excel**: Generate comprehensive Excel workbook with multiple sheets
- **get_schedule_data**: Get raw assignment data for visualization (agent transforms to Mermaid)
- **show_schedule_summary**: Display detailed assignment statistics

### Analysis Tools
- **get_patient_details**: Show patient constraints, requirements, and current assignments
- **get_therapist_details**: Display therapist availability, workload, and assigned patients

### Constraint Modification Tools
- **update_patient_availability**: Modify patient timeslot availability

## Usage

### Interactive Mode
```bash
python -m schedule_agent.agent.run
```

### Programmatic Usage
```python
from schedule_agent.core.data_store import DataStore
from schedule_agent.agent.agent import create_schedule_agent

data_store = DataStore()
agent = create_schedule_agent(data_store)

response = agent.run("Create schedule for October 4th using files in data/raw/")
print(response)
```

## Model Configuration

- **Model**: `us.anthropic.claude-sonnet-4-20250514-v1:0`
- **Provider**: Amazon Bedrock
- **Temperature**: 0.7
- **Max Tokens**: 4096

## Agent Behavior

- **Max Iterations**: 50
- **Memory**: Enabled (maintains conversation context)
- **Verbose**: Enabled (shows tool calls and reasoning)

## Example Workflows

### Successful Scheduling
```
User: "Create schedule for October 4th using data/raw/therapist.csv, 
       data/raw/prescription.csv, and data/raw/shift.xlsx"
Agent: [Calls create_schedule()]
       "Schedule created successfully for 2025-10-04:
        - Total assignments: 127
        - Unscheduled patients: 0
        Would you like to see a visualization or export to Excel?"

User: "Show me patient 1001's schedule"
Agent: [Calls get_schedule_data(patient_id="1001")]
       [Generates Mermaid Gantt chart from data]
       "Here's patient 1001's schedule:
        [Mermaid diagram showing therapist assignments across timeslots]"
```

### Error Recovery
```
User: "Create schedule for October 5th"
Agent: [Calls create_schedule() - raises exception]
       "Scheduling failed. Let me investigate the issue..."
       [Calls get_patient_details() for patients mentioned in exception]
       "The issue is that Patient 1001 needs 180 minutes (9 slots) but only 
        has 5 available timeslots. Would you like to make them available 
        during additional times?"

User: "Make Patient 1001 available from 13:00 to 14:00"
Agent: [Calls update_patient_availability() for each slot]
       "Updated Patient 1001's availability. Shall I try scheduling again?"

User: "Yes"
Agent: [Calls create_schedule() - succeeds]
       "Schedule created successfully!"
```

### Visualization Options
```
User: "Show all patients' schedules"
Agent: [Calls get_schedule_data() with no filters]
       [Generates comprehensive Mermaid Gantt with sections per patient]

User: "Show therapist 佐藤花子's schedule"
Agent: [Calls get_schedule_data(therapist_id="佐藤花子")]
       [Generates Mermaid Gantt showing all patients assigned to this therapist]
```

## Future Enhancements (Not in Initial Release)

- **update_compatibility_score**: Adjust patient-therapist compatibility (complex to implement correctly)
- **Batch availability updates**: Update multiple timeslots at once
- **What-if analysis**: Preview scheduling impact before committing changes
