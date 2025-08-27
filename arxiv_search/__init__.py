import click

@click.command()
@click.option('--topic', type=str, default=None, required=True, help="High-level research topic (Math, CS, Physics, etc.)")
@click.option('--sub-topic', type=str, default=None, required=True, help="Specific sub-topic within the high-level category")
@click.option('--author', type=str, default=None, help="Specific author in research paper")
@click.option('--start-date', type=str, default=None, help="Start date of range of papers")
@click.option('--end-date', type=str, default="today", help="End date of range of papers")
@click.option('--citations', type=bool, default=True, help="Order by citations")
def main(topic: str, sub_topic: str, author: str, start_date: str, end_date: str, citations: bool) -> str:
    print("test")

