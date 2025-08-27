import click
import json
from pathlib import Path
from arxiv_search.arxiv import ArxivReport

field_map = {
   "title": "ti:",
   "author": "au:",
   "category": "cat:",
   "report": "rn:",
   "id": "id:",
   "date": "submittedDate:",
   "all": "all:"
}

@click.command()
@click.option('--category', type=str, default=None, help="High-level research category (Math, CS, Physics, etc.)")
@click.option('--sub-category', type=str, default=None, help="Specific sub-topic within the high-level category")
@click.option('--author', type=str, default=None, help="Specific author in research paper")
@click.option('--title', type=str, default=None, help="Search for a keyphrase in titles")
@click.option('--start-date', type=str, default=None, help="Start date of range of papers")
@click.option('--citations', type=bool, default=True, help="Order by citations")
def main(topic: str, sub_topic: str, author: str, start_date: str, end_date: str, citations: bool) -> str:
    """
    Main driver behind the application.
    """
    ax = ArxivReport()

    # For all the parameters we've seen build out a report

@click.command()
@click.option("--domain", type=str, default=None, required=True, help="Prints all possible sub-categories in a high-level domain")
def categories(domain: str):
   """Print all arXiv subcategories for a given domain."""
   categories_file = Path(__file__).parent / "arxiv_categories.json"

   with open(categories_file, 'r') as f:
      data = json.load(f)

   domain = domain.lower()
   multi_domains = data["multi_category_domains"]
   single_categories = data["single_categories"]

   if domain in multi_domains:
      domain_info = multi_domains[domain]
      click.echo(f"\n{domain_info['name']} ({domain.upper()}) Categories:")
      click.echo("=" * 60)

      for code, description in domain_info["categories"].items():
         full_code = f"{domain}.{code}"
         click.echo(f"  {code:12} -> {full_code:20} | {description}")

   elif domain in single_categories:
      click.echo(f"\n{domain.upper()} Category:")
      click.echo("=" * 50)
      click.echo(f"  {domain:12} -> {domain:20} | {single_categories[domain]}")

   else:
      click.echo(f"Error: Unknown domain '{domain}'")
      click.echo("\nAvailable domains:")

      click.echo("\nMulti-category domains:")
      for d, info in multi_domains.items():
         click.echo(f"  {d:12} - {info['name']}")

      click.echo("\nSingle categories:")
      for d, desc in single_categories.items():
         click.echo(f"  {d:12} - {desc}")

@click.command()
def domains():
   """Display all available arXiv domains."""

   domains_file = Path(__file__).parent / "arxiv_domains.json"

   with open(domains_file, 'r') as f:
      domain_list = json.load(f)

   click.echo("Available ArXiv Domains:")
   click.echo("=" * 30)

   for i, domain in enumerate(domain_list, 1):
      click.echo(f"  {i:2d}. {domain}")
