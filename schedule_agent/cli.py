import click
from pathlib import Path
import json
from .core.preprocessor import DataLoader, DataNormalizer, InterimWriter
from .core.constraints_builder import ConstraintMatrixBuilder
from .core.scheduler import DeterministicScheduler, ScheduleValidator
from .utils.visualization import ScheduleVisualizer


@click.group()
def cli():
    """Hospital Scheduling Automation CLI."""
    pass


@cli.command()
@click.option('--date', required=True, help='Target date (e.g., 2025-10-04)')
def preprocess(date: str):
    """Preprocess raw data and build constraint matrices."""
    loader = DataLoader()
    normalizer = DataNormalizer()
    writer = InterimWriter()
    
    # Load data
    therapists = loader.load_therapists()
    prescriptions = loader.load_prescriptions()
    shifts = loader.load_shifts("202510")
    
    # Normalize
    therapists_norm = normalizer.normalize_therapists(therapists)
    prescriptions_norm = normalizer.normalize_prescriptions(prescriptions)
    shifts_norm = normalizer.normalize_shifts(shifts, date)
    
    # Save
    writer.save_therapists(therapists_norm)
    writer.save_prescriptions(prescriptions_norm)
    writer.save_shifts(shifts_norm)
    writer.save_name_mapping(therapists)
    
    # Build matrices
    builder = ConstraintMatrixBuilder()
    matrices = builder.build_all_matrices()
    builder.save_matrices(matrices)
    
    click.echo(f"✓ Preprocessed data for {date}")
    click.echo(f"  Patients: {len(matrices.patient_ids)}")
    click.echo(f"  Therapists: {len(matrices.therapist_ids)}")


@cli.command()
@click.option('--date', required=True, help='Target date')
def schedule(date: str):
    """Run deterministic scheduler."""
    builder = ConstraintMatrixBuilder()
    matrices = builder.load_matrices()
    
    scheduler = DeterministicScheduler()
    result = scheduler.schedule(matrices)
    result.date = date
    
    # Save schedule
    output_dir = Path("data/interim")
    schedule_data = {
        "date": result.date,
        "assignments": [
            {
                "patient_id": a.patient_id,
                "therapist_id": a.therapist_id,
                "timeslot": a.timeslot,
                "duration_minutes": a.duration_minutes
            }
            for a in result.assignments
        ],
        "unscheduled_patients": result.unscheduled_patients
    }
    
    with open(output_dir / "schedule.json", "w", encoding="utf-8") as f:
        json.dump(schedule_data, f, ensure_ascii=False, indent=2)
    
    click.echo(f"✓ Schedule created for {date}")
    click.echo(f"  Assignments: {len(result.assignments)}")
    click.echo(f"  Unscheduled: {len(result.unscheduled_patients)}")
    
    if result.unscheduled_patients:
        click.echo(f"  Warning: {result.unscheduled_patients}")


@cli.command()
@click.option('--date', required=True, help='Target date')
def visualize(date: str):
    """Generate schedule visualization."""
    # Load schedule
    schedule_file = Path("data/interim/schedule.json")
    if not schedule_file.exists():
        click.echo("Error: No schedule found. Run 'schedule' command first.")
        return
    
    with open(schedule_file, "r", encoding="utf-8") as f:
        schedule_data = json.load(f)
    
    # Reconstruct schedule object
    from .models.data_models import Schedule, Assignment
    schedule = Schedule(
        assignments=[
            Assignment(**a) for a in schedule_data["assignments"]
        ],
        date=schedule_data["date"],
        unscheduled_patients=schedule_data["unscheduled_patients"]
    )
    
    # Load matrices
    builder = ConstraintMatrixBuilder()
    matrices = builder.load_matrices()
    
    # Export to Excel
    visualizer = ScheduleVisualizer()
    output_path = Path("data/processed") / f"schedule_{date}.xlsx"
    visualizer.export_to_excel(schedule, matrices, output_path)
    
    click.echo(f"✓ Visualization created: {output_path}")


@cli.command()
@click.option('--date', required=True, help='Target date')
def optimize(date: str):
    """Start conversational optimization."""
    click.echo(f"Conversational optimization for {date} (not implemented yet)")


@cli.command()
@click.option('--error-file', required=True, help='Error state file')
def debug(error_file: str):
    """Analyze scheduling failures."""
    click.echo(f"Debug mode for {error_file} (not implemented yet)")


if __name__ == '__main__':
    cli()
