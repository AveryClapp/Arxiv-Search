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

def load_categories():
    """Load categories from JSON file."""
    categories_file = Path(__file__).parent / "arxiv_categories.json"
    with open(categories_file, 'r') as f:
        return json.load(f)

def load_domains():
    """Load domains from JSON file."""
    domains_file = Path(__file__).parent / "arxiv_domains.json"
    with open(domains_file, 'r') as f:
        return json.load(f)

def validate_category(category_value: str) -> bool:
   """Validate if category exists in our JSON files."""
   try:
      categories_data = load_categories()
      multi_domains = categories_data["multi_category_domains"]
      single_categories = categories_data["single_categories"]

      if subcategory in single_categories:
         return True

      if "." in subcategory:
         domain, subcat = subcategory.split(".", 1)
         if domain in multi_domains:
            return subcat in multi_domains[domain]["categories"]

      return False
   except:
      return False

def validate_high_level_category(category: str) -> bool:
    """Check if it's a valid high-level domain."""
    try:
        domain_map = load_domains()
        return category.lower() in domain_map.keys()
    except:
        return False

@click.command()
@click.option('--category', type=str, default=None, help="High-level research category (Math, CS, Physics, etc.)")
@click.option('--sub-category', type=str, default=None, help="Specific sub-topic within the high-level category")
@click.option('--author', type=str, default=None, help="Specific author in research paper")
@click.option('--title', type=str, default=None, help="Search for a keyphrase in titles")
@click.option('--start-date', type=str, default=None, help="Start date of range of papers")
@click.option('--citations', type=bool, default=True, help="Order by citations")
def main(category: str, sub_category: str, author: str, title: str, start_date: str, citations: bool) -> str:
   """
   Main driver behind the application
   """
   if category and sub_category:
      click.echo("Error: --category and --sub-category cannot be used together.")
      click.echo("Use --category for broad topics (e.g., 'Mathematics') or --sub-category for specific ones (e.g., 'cs.AI')")
      raise click.Abort()

   if category and not validate_category(category):
      click.echo(f"Error: Invalid category '{category}'")
      click.echo("Use 'get-domains' to see available high-level categories")
      click.echo("Use 'get-categories --domain <domain>' to see specific subcategories")
      raise click.Abort()

   if sub_category and not validate_category(sub_category):
      click.echo(f"Error: Invalid sub-category '{sub_category}'")
      click.echo("Use 'get-categories --domain <domain>' to see available subcategories")
      click.echo("Examples: cs.AI, math.NT, quant-ph")
      raise click.Abort()


   ax = ArxivReport()



@click.command()
@click.option("--domain", type=str, default=None, required=True, help="Prints all possible sub-categories in a high-level domain")
def categories(domain: str):
   """Print all arXiv subcategories for a given domain."""

   data = load_categories()
   domain = domain.lower()
   multi_domains = data["multi_category_domains"]
   single_categories = data["single_categories"]

   if domain in multi_domains:
      domain_info = multi_domains[domain]
      click.echo(f"\n{domain_info['name']} ({domain.upper()}) Categories:")
      click.echo("=" * 60)

      for code, description in domain_info["categories"].items():
         full_code = f"{domain}.{code}"
         click.echo(f"  {full_code:12} | {description}")

   elif domain in single_categories:
      click.echo(f"\n{domain.upper()} Category:")
      click.echo("=" * 50)
      click.echo(f"  {domain:12} | {single_categories[domain]}")

   else:
      click.echo(f"Error: Unknown domain '{domain}'")
      click.echo("Use 'get-domains' to see available high-level categories")

@click.command()
def domains():
   """Display all available arXiv domains."""

   domain_map = load_domains()

   click.echo("Available ArXiv Domains:")
   click.echo("=" * 30)

   for i, (code, full_name) in enumerate(domain_map.items(), 1):
        click.echo(f"  {i:2d}. {code:12} - {full_name}")
