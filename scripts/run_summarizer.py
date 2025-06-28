# run_summarizer.py
import click
from app.core.summarizer import Summarizer
from datetime import datetime


@click.command()
@click.option('--date', default=None, help='Target date in YYYY-MM-DD format (defaults to today)')
def run_summarizer(date):
    """
    Run the summarizer pipeline for a given date.
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    print(f"Running summarizer for {date}")
    summarizer = Summarizer(date_str=date)
    summarizer.update()


if __name__ == "__main__":
    run_summarizer()