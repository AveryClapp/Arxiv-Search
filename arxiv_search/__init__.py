import click
import json
from pathlib import Path
from arxiv_search.arxiv import ArxivReport
import sys

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

def format_paper_output(paper: dict, index: int, show_citations: bool = False) -> str:
   """Format paper information for display"""
   output = []
   output.append(f"\n{index}. {paper['title']}")
   output.append(f"   Authors: {', '.join(paper['authors'])}")
   output.append(f"   Category: {paper['category']}")
   output.append(f"   Published: {paper['published']}")
   output.append(f"   arXiv ID: {paper['arxiv_id']}")
   output.append(f"   URL: {paper['url']}")

   abstract = paper['summary']
   if len(abstract) > 300:
      abstract = abstract[:300] + "..."
   output.append(f"   Abstract: {abstract}")

   if show_citations:
      citation_count = paper.get('citation_count', 0)
      has_citations = paper.get('has_citations', False)

      if has_citations:
         output.append(f"   Citations: {citation_count}")
      else:
         output.append(f"   Citations: {citation_count} (estimate/unavailable)")

   return '\n'.join(output)

@click.command()
@click.option('--category', type=str, default=None, help="High-level research category (Math, CS, Physics, etc.)")
@click.option('--sub-category', type=str, default=None, help="Specific sub-topic within the high-level category")
@click.option('--author', type=str, default=None, help="Specific author in research paper")
@click.option('--title', type=str, default=None, help="Search for a keyphrase in titles")
@click.option('--start-date', type=str, default=None, help="Start date of range of papers (YYYY-MM-DD)")
@click.option('--end-date', type=str, default=None, help="End date of range of papers (YYYY-MM-DD)")
@click.option('--citations', is_flag=True, default=False, help="Show citation counts for papers")
@click.option('--sort-by-citations', is_flag=True, default=False, help="Find the most highly cited papers (searches historical data)")
@click.option('--max-results', type=int, default=10, help="Maximum number of results to return (default: 10)")
@click.option('--timeout', type=int, default=30, help="Timeout for citation lookup in seconds (default: 30)")
@click.option('--verbose', is_flag=True, default=False, help="Show detailed progress information")
def main(category: str, sub_category: str, author: str, title: str, start_date: str, end_date: str,
         citations: bool, sort_by_citations: bool, max_results: int, timeout: int, verbose: bool) -> None:

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

   if max_results < 1 or max_results > 100:
      click.echo("Error: --max-results must be between 1 and 100")
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

      if verbose:
         click.echo(f"Search query: {search_query}")
         if citations or sort_by_citations:
            click.echo("Citation lookup enabled - this may take longer...")
            if sort_by_citations:
               click.echo("Searching historical papers for most cited works...")

      if sort_by_citations:
         with click.progressbar(length=max_results, 
                                label='Finding most cited papers') as bar:
            results = searcher.get_historical_popular_papers(
               query=search_query,
               start_date=start_date,
               end_date=end_date,
               max_results=max_results
            )
            bar.update(len(results))
      elif citations:
         with click.progressbar(length=max_results, 
                                label='Fetching papers with citations') as bar:
            results = searcher.get_popular_papers(
               query=search_query,
               start_date=start_date,
               max_results=max_results
            )
            bar.update(len(results))
      else:
         results = searcher.search(
            query=search_query,
            start_date=start_date,
            end_date=end_date,
            max_results=max_results,
            sort_by='relevance'
         )

      if not results:
         click.echo("No results found for your search criteria.")
         return

      click.echo(f"\nFound {len(results)} results:")

      if citations:
         # Show citation statistics
         cited_papers = [p for p in results if p.get('has_citations', False)]
         uncited_papers = [p for p in results if not p.get('has_citations', False)]

         click.echo(f"Citation data available for {len(cited_papers)}/{len(results)} papers")
         if uncited_papers:
            click.echo(f"{len(uncited_papers)} papers show estimated/unavailable citation counts")

      click.echo("=" * 80)

      for i, paper in enumerate(results, 1):
         output = format_paper_output(paper, i, show_citations=citations)
         click.echo(output)

      if citations and verbose:
         # Show additional statistics
         if cited_papers:
            max_citations = max(p.get('citation_count', 0) for p in cited_papers)
            avg_citations = sum(p.get('citation_count', 0) for p in cited_papers) / len(cited_papers)
            click.echo(f"\nCitation Statistics:")
            click.echo(f"  Max citations: {max_citations}")
            click.echo(f"  Average citations (cited papers): {avg_citations:.1f}")

   except KeyboardInterrupt:
      click.echo("\nSearch interrupted by user.")
      sys.exit(1)
   except Exception as e:
      if verbose:
         import traceback
         traceback.print_exc()
      else:
         click.echo(f"Error performing search: {str(e)}")
         click.echo("Use --verbose for more detailed error information.")
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

@click.command()
@click.argument('arxiv_id')
@click.option('--citations', is_flag=True, default=False, help="Include citation information")
def get_paper(arxiv_id: str, citations: bool):
   """Get detailed information about a specific arXiv paper by ID"""

   try:
      searcher = ArxivReport()

      if citations:
         with click.progressbar(length=1, label='Fetching paper with citations') as bar:
            papers = searcher.search_with_citations(f'id:{arxiv_id}', max_results=1)
            bar.update(1)
      else:
         papers = searcher.search(f'id:{arxiv_id}', max_results=1)

      if not papers:
         click.echo(f"No paper found with arXiv ID: {arxiv_id}")
         return

      paper = papers[0]

      click.echo("=" * 80)
      output = format_paper_output(paper, 1, show_citations=citations)
      click.echo(output)

      # Additional details
      if paper.get('doi'):
         click.echo(f"   DOI: {paper['doi']}")
      if paper.get('comment'):
         click.echo(f"   Comments: {paper['comment']}")

      click.echo("=" * 80)

   except Exception as e:
      click.echo(f"Error fetching paper: {str(e)}")
      raise click.Abort()

# Add the new command to the CLI group
@click.group()
def cli():
   """ArXiv Search Tool - Enhanced research paper discovery"""
   pass

# Register commands
cli.add_command(main, name='search')
cli.add_command(categories, name='categories') 
cli.add_command(domains, name='domains')
cli.add_command(get_paper, name='get')

if __name__ == '__main__':
   cli()
