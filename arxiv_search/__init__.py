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
   categories_file = Path(__file__).parent / "arxiv_categories.json"
   with open(categories_file, 'r') as f:
      return json.load(f)

def load_domains():
   domains_file = Path(__file__).parent / "arxiv_domains.json"
   with open(domains_file, 'r') as f:
      return json.load(f)

def validate_category(category_value: str) -> bool:
   try:
      categories_data = load_categories()
      multi_domains = categories_data["multi_category_domains"]
      single_categories = categories_data["single_categories"]

      if category_value in single_categories:
         return True

      if "." in category_value:
         domain, subcat = category_value.split(".", 1)
         if domain in multi_domains:
            return subcat in multi_domains[domain]["categories"]

      return False
   except:
      return False

def validate_high_level_category(category: str) -> bool:
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
@click.option('--start-date', type=str, default=None, help="Start date of range of papers (YYYY-MM-DD)")
@click.option('--citations', is_flag=True, default=False, help="Order by citations and show citation counts")
def main(category: str, sub_category: str, author: str, title: str, start_date: str, 
         citations: bool) -> None:

   if category and sub_category:
      click.echo("Error: --category and --sub-category cannot be used together.")
      click.echo("Use --category for broad topics (e.g., 'cs') or --sub-category for specific ones (e.g., 'cs.AI')")
      raise click.Abort()

   if category and not validate_high_level_category(category):
      click.echo(f"Error: Invalid category '{category}'")
      click.echo("Use 'get-domains' to see available high-level categories")
      click.echo("Use 'get-categories --domain <domain>' to see specific subcategories")
      raise click.Abort()

   if sub_category and not validate_category(sub_category):
      click.echo(f"Error: Invalid sub-category '{sub_category}'")
      click.echo("Use 'get-categories --domain <domain>' to see available subcategories")
      click.echo("Examples: cs.AI, math.NT, quant-ph")
      raise click.Abort()

   try:
      searcher = ArxivReport()

      query_parts = []

      if title:
         query_parts.append(f'ti:"{title}"')

      if author:
         query_parts.append(f'au:"{author}"')

      if category:
         query_parts.append(f'cat:{category}.*')
      elif sub_category:
         query_parts.append(f'cat:{sub_category}')

      if not query_parts:
         query_parts.append('all:*')

      search_query = ' AND '.join(query_parts)

      if citations:
         results = searcher.get_popular_papers(
            query=search_query,
            start_date=start_date,
            max_results=10
         )
      else:
         results = searcher.search(
            query=search_query,
            start_date=start_date,
            max_results=10,
            sort_by='relevance'
         )

      if not results:
         click.echo("No results found for your search criteria.")
         return

      click.echo(f"\nFound {len(results)} results:\n")
      click.echo("=" * 80)

      for i, paper in enumerate(results, 1):
         click.echo(f"\n{i}. {paper['title']}")
         click.echo(f"   Authors: {', '.join(paper['authors'])}")
         click.echo(f"   Category: {paper['category']}")
         click.echo(f"   Published: {paper['published']}")
         click.echo(f"   arXiv ID: {paper['arxiv_id']}")
         click.echo(f"   URL: {paper['url']}")

         abstract = paper['summary']
         if len(abstract) > 300:
            abstract = abstract[:300] + "..."
            click.echo(f"   Abstract: {abstract}")

            if citations and 'citation_count' in paper:
               click.echo(f"   Citations: {paper['citation_count']}")

   except Exception as e:
      click.echo(f"Error performing search: {str(e)}")
      raise click.Abort()

@click.command()
@click.option("--domain", type=str, default=None, required=True, 
              help="Prints all possible sub-categories in a high-level domain")
def categories(domain: str):

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
         click.echo(f"  {full_code:15} | {description}")

   elif domain in single_categories:
      click.echo(f"\n{domain.upper()} Category:")
      click.echo("=" * 50)
      click.echo(f"  {domain:15} | {single_categories[domain]}")

   else:
      click.echo(f"Error: Unknown domain '{domain}'")
      click.echo("Use 'get-domains' to see available high-level categories")

@click.command()
def domains():

   domain_map = load_domains()

   click.echo("\nAvailable ArXiv Domains:")
   click.echo("=" * 30)

   for i, (code, full_name) in enumerate(domain_map.items(), 1):
      click.echo(f"  {i:2d}. {code:15} - {full_name}")
