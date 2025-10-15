import click
from .core.data_store import DataStore
from .core.pipeline import SchedulingPipeline
from .models.data_models import InfeasibleScheduleError


@click.group()
def cli():
    """Hospital Scheduling Automation CLI."""
    pass


@cli.command()
@click.option('--therapist-file', required=True, help='Path to therapist CSV file')
@click.option('--prescription-file', required=True, help='Path to prescription CSV file')
@click.option('--shift-file', required=True, help='Path to shift Excel file')
@click.option('--date', required=True, help='Target date (YYYY-MM-DD)')
def schedule(therapist_file: str, prescription_file: str, shift_file: str, date: str):
    """Complete scheduling pipeline."""
    store = DataStore()
    
    with store.session():
        # Copy input files
        store.copy_therapist_file(therapist_file)
        store.copy_prescription_file(prescription_file)
        store.copy_shift_file(shift_file)
        
        # Execute pipeline
        pipeline = SchedulingPipeline(store)
        try:
            result = pipeline.full_pipeline(date)
            click.echo(f"Schedule completed: {len(result.assignments)} assignments")
            if result.unscheduled_patients:
                click.echo(f"Unscheduled patients: {len(result.unscheduled_patients)}")
        except InfeasibleScheduleError as e:
            click.echo(f"Scheduling failed: {e}")
            store.save_error_state({
                'error': str(e),
                'patient_id': e.patient_id,
                'details': e.details
            })


@cli.command()
@click.option('--therapist-file', required=True)
@click.option('--prescription-file', required=True)
@click.option('--shift-file', required=True)
@click.option('--date', required=True)
def preprocess(therapist_file: str, prescription_file: str, shift_file: str, date: str):
    """Preprocess raw data only."""
    store = DataStore()
    
    with store.session():
        store.copy_therapist_file(therapist_file)
        store.copy_prescription_file(prescription_file)
        store.copy_shift_file(shift_file)
        
        pipeline = SchedulingPipeline(store)
        pipeline.preprocess_all(date)
        click.echo("Preprocessing completed")


@cli.command()
@click.option('--therapist-file', required=True)
@click.option('--prescription-file', required=True)
@click.option('--shift-file', required=True)
@click.option('--date', required=True)
def build_constraints(therapist_file: str, prescription_file: str, shift_file: str, date: str):
    """Build constraint matrices."""
    store = DataStore()
    
    with store.session():
        store.copy_therapist_file(therapist_file)
        store.copy_prescription_file(prescription_file)
        store.copy_shift_file(shift_file)
        
        pipeline = SchedulingPipeline(store)
        pipeline.preprocess_all(date)
        pipeline.build_all_constraints()
        click.echo("Constraint matrices built")


@cli.command()
@click.option('--date', required=True)
def optimize(date: str):
    """Start conversational optimization (placeholder)."""
    click.echo(f"Conversational optimization for {date} - Not implemented yet")


@cli.command()
@click.option('--error-file', required=True)
def debug(error_file: str):
    """Analyze scheduling failures (placeholder)."""
    click.echo(f"Debug analysis for {error_file} - Not implemented yet")


@cli.command()
@click.option('--date', required=True)
def visualize(date: str):
    """Generate schedule visualization (placeholder)."""
    click.echo(f"Visualization for {date} - Not implemented yet")


if __name__ == '__main__':
    cli()
