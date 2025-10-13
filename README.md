# Hospital Scheduling Automation

Automated patient-therapist scheduling system using deterministic optimization with AI-powered debugging and conversational constraint modification.

## Features

- **Fast Deterministic Scheduling**: Uses scipy optimization for predictable, reproducible schedules
- **AI Debug Assistant**: Analyzes scheduling failures and suggests specific fixes
- **Conversational Optimization**: Modify constraints through natural language
- **Constraint Matrices**: Transparent, inspectable numpy arrays for all scheduling rules
- **AgentCore Ready**: Minimal CLI wrappers for easy deployment

## Architecture Overview

```mermaid
flowchart TD
    A[Raw Data<br/>therapist.csv<br/>prescription.csv<br/>shift_202510.xlsx] --> B[Preprocessor<br/>cp932 encoding]
    B --> C[Constraint Matrices<br/>Patient Availability P×18<br/>Therapist Availability Th×18<br/>Compatibility P×Th<br/>Requirements P×1]
    C --> D[Deterministic Scheduler<br/>scipy optimization]
    
    D --> E{Success?}
    E -->|No| F[AI Debug Agent<br/>Analyze & Suggest Fixes]
    F --> G[Diagnosis Report]
    
    E -->|Yes| H[Initial Schedule]
    H --> I{Optimization<br/>Needed?}
    I -->|Yes| J[Conversational Agent<br/>Modify Constraints]
    J --> K[Update Matrices]
    K --> D
    I -->|No| L[Final Schedule<br/>Excel Output]
    
    style C fill:#ff9
    style D fill:#9f9
    style J fill:#99f
    style L fill:#9f9
```

## Quick Start

```bash
# Install dependencies
uv sync

# Preprocess raw data
uv run schedule-agent preprocess

# Run scheduler for specific date
uv run schedule-agent schedule --date 2025-10-04

# Visualize schedule
uv run schedule-agent visualize --date 2025-10-04
```

## Interactive Optimization

```bash
# Start conversational optimization
uv run schedule-agent optimize --date 2025-10-04
```

### Conversation Example (Japanese)

```
ユーザー: 患者123は14時から対応可能です

エージェント: 患者123の14:00-14:20の時間帯の空き状況を更新しました。
            スケジュールを再作成しますか？

ユーザー: はい

エージェント: スケジュールを更新しました。47件の割り当てが完了しました。
            患者123は療法士T005に14:00で割り当てられました。

ユーザー: 患者123を別の療法士に変更できますか？

エージェント: 現在の割り当て: 患者123 → 療法士T005 (スコア: 100, 担当療法士)
            互換性のある代替療法士:
            - 療法士T012 (スコア: 80, 同じ病棟)
            - 療法士T023 (スコア: 60, 同じ性別)
            どの療法士をご希望ですか？

ユーザー: T012でお願いします

エージェント: 患者123と療法士T012の互換性スコアを110に更新しました。
            「再スケジュール」と入力して変更を適用してください。
```

### Conversation Example (English)

```
User: Patient 123 can be available at 14:00

Agent: Updated Patient 123's availability for timeslot 14:00-14:20.
       Would you like to reschedule?

User: Yes

Agent: Schedule updated with 47 assignments.
       Patient 123 is now assigned to Therapist T005 at 14:00.

User: Can we use a different therapist for Patient 123?

Agent: Current assignment: Patient 123 → Therapist T005 (score: 100, primary therapist)
       Compatible alternatives:
       - Therapist T012 (score: 80, same ward)
       - Therapist T023 (score: 60, same gender)
       Which therapist would you prefer?

User: Use T012

Agent: Updated compatibility score for Patient 123 and Therapist T012 to 110.
       Type 'reschedule' to apply changes.
```

## Core Components

**Module Structure**:
- `preprocessor.py`: Load and normalize raw data (cp932 encoding)
- `constraints_builder.py`: Build constraint matrices
- `scheduler.py`: Deterministic scheduling using scipy
- `debug_agent.py`: AI debugging agent
- `constraint_agent.py`: Conversational optimization agent

**Data Flow**:

```mermaid
flowchart LR
    A[Raw Data] --> B[Preprocessor]
    B --> C[interim/<br/>normalized CSVs]
    C --> D[Constraints Builder]
    D --> E[interim/<br/>*.npy matrices]
    E --> F[Scheduler]
    F --> G[processed/<br/>schedule.xlsx]
    
    H[User] --> I[Constraint Agent]
    I --> E
    E --> F
    
    style C fill:#ffe
    style E fill:#ffe
    style G fill:#efe
```

## Requirements

See [spec/requirements.md](spec/requirements.md) for detailed requirements specification.

See [spec/design.md](spec/design.md) for detailed architecture documentation.

## Project Structure

```
schedule-optimizer/
├── schedule_agent/          # Main package
│   ├── cli.py              # CLI entry points
│   ├── core/               # Core scheduling logic
│   ├── models/             # Data models
│   └── utils/              # Utilities
├── data/                   # Data directories
│   ├── raw/               # Original files
│   ├── interim/           # Processed data & matrices
│   └── processed/         # Final schedules
└── spec/                  # Documentation
    ├── requirements.md    # Requirements specification
    └── design.md         # Architecture design
```

## Technology Stack

- **Optimization**: scipy
- **AI Agents**: strands-agents
- **CLI**: click
- **Data**: pandas, numpy
- **Validation**: pydantic
