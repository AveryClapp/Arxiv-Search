import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Dict, Optional
import re
import logging
from arxiv_search.citations import CitationManager

logger = logging.getLogger(__name__)

class ArxivReport:
    BASE_URL = "http://export.arxiv.org/api/query"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'ArxivSearch/1.0 (Python/requests)'
        })
        self.citation_manager = CitationManager()

    def _build_date_filter(self, start_date: Optional[str], end_date: Optional[str]) -> str:
        date_filters = []

        if start_date:
            try:
                datetime.strptime(start_date, '%Y-%m-%d')
                date_filters.append(f'submittedDate:[{start_date.replace("-", "")}* TO *]')
            except ValueError:
                raise ValueError(f"Invalid start date format: {start_date}. Use YYYY-MM-DD")

        if end_date:
            try:
                datetime.strptime(end_date, '%Y-%m-%d')
                date_filters.append(f'submittedDate:[* TO {end_date.replace("-", "")}*]')
            except ValueError:
                raise ValueError(f"Invalid end date format: {end_date}. Use YYYY-MM-DD")

        return ' AND '.join(date_filters)

    def _parse_arxiv_response(self, xml_content: str) -> List[Dict]:
        try:
            root = ET.fromstring(xml_content)

            namespaces = {
                'atom': 'http://www.w3.org/2005/Atom',
                'arxiv': 'http://arxiv.org/schemas/atom'
            }

            papers = []
            entries = root.findall('atom:entry', namespaces)

            for entry in entries:
                paper = {}

                title_elem = entry.find('atom:title', namespaces)
                paper['title'] = title_elem.text.strip().replace('\n', ' ') if title_elem is not None else 'N/A'

                authors = []
                for author in entry.findall('atom:author', namespaces):
                    name_elem = author.find('atom:name', namespaces)
                    if name_elem is not None:
                        authors.append(name_elem.text.strip())
                paper['authors'] = authors

                id_elem = entry.find('atom:id', namespaces)
                if id_elem is not None:
                    paper['url'] = id_elem.text.strip()
                    new_format = re.search(r'/abs/(\d{4}\.\d{4,5})(v\d+)?$', paper['url'])
                    old_format = re.search(r'/abs/([a-z-]+/\d{7})(v\d+)?$', paper['url'])

                    if new_format:
                        paper['arxiv_id'] = new_format.group(1)
                    elif old_format:
                        paper['arxiv_id'] = old_format.group(1)
                    else:
                        paper['arxiv_id'] = 'N/A'

                published_elem = entry.find('atom:published', namespaces)
                if published_elem is not None:
                    try:
                        pub_date = datetime.fromisoformat(published_elem.text.replace('Z', '+00:00'))
                        paper['published'] = pub_date.strftime('%Y-%m-%d')
                    except:
                        paper['published'] = published_elem.text[:10]
                else:
                    paper['published'] = 'N/A'

                updated_elem = entry.find('atom:updated', namespaces)
                if updated_elem is not None:
                    try:
                        upd_date = datetime.fromisoformat(updated_elem.text.replace('Z', '+00:00'))
                        paper['updated'] = upd_date.strftime('%Y-%m-%d')
                    except:
                        paper['updated'] = updated_elem.text[:10]
                else:
                    paper['updated'] = paper['published']

                categories = []
                for category in entry.findall('atom:category', namespaces):
                    term = category.get('term')
                    if term:
                        categories.append(term)
                paper['category'] = ', '.join(categories) if categories else 'N/A'
                paper['primary_category'] = categories[0] if categories else 'N/A'

                summary_elem = entry.find('atom:summary', namespaces)
                paper['summary'] = summary_elem.text.strip().replace('\n', ' ') if summary_elem is not None else 'N/A'

                doi_elem = entry.find('arxiv:doi', namespaces)
                paper['doi'] = doi_elem.text.strip() if doi_elem is not None else None

                comment_elem = entry.find('arxiv:comment', namespaces)
                paper['comment'] = comment_elem.text.strip() if comment_elem is not None else None

                papers.append(paper)

            return papers

        except ET.ParseError as e:
            raise ValueError(f"Failed to parse arXiv response: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"Error processing arXiv data: {str(e)}")

    def search(self, query: str, start_date: Optional[str] = None, end_date: Optional[str] = None,
               max_results: int = 10, sort_by: str = 'relevance', start: int = 0) -> List[Dict]:
        params = {
            'search_query': query,
            'start': start,
            'max_results': min(max_results, 1000),
            'sortBy': sort_by,
            'sortOrder': 'descending'
        }

        if start_date or end_date:
            date_filter = self._build_date_filter(start_date, end_date)
            if date_filter:
                params['search_query'] = f"({query}) AND ({date_filter})"

        try:
            response = self.session.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()

            if 'error' in response.text.lower() and 'malformed query' in response.text.lower():
                raise ValueError("Malformed search query. Please check your search parameters.")

            papers = self._parse_arxiv_response(response.text)
            return papers

        except requests.exceptions.Timeout:
            raise RuntimeError("Request timed out. Please try again.")
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Network error: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"Search failed: {str(e)}")

    def get_paper_by_id(self, arxiv_id: str) -> Optional[Dict]:
        try:
            results = self.search(f'id:{arxiv_id}', max_results=1)
            return results[0] if results else None
        except Exception:
            return None

    def search_with_citations(self, query: str, start_date: Optional[str] = None, 
                              end_date: Optional[str] = None, max_results: int = 10, 
                              sort_by: str = 'relevance', max_citation_papers: int = 10) -> List[Dict]:
        papers = self.search(query, start_date, end_date, max_results, sort_by)

        if not papers:
            return papers

        citation_papers = papers[:max_citation_papers]
        logger.info(f"Enriching {len(citation_papers)} papers with citation data...")

        try:
            enriched_papers = self.citation_manager.get_citations_batch(citation_papers, max_workers=1)

            if len(papers) > max_citation_papers:
                remaining_papers = papers[max_citation_papers:]
                for paper in remaining_papers:
                    paper['citation_count'] = 0
                    paper['has_citations'] = False
                enriched_papers.extend(remaining_papers)

            successful_citations = sum(1 for p in enriched_papers if p.get('has_citations', False))
            logger.info(f"Successfully retrieved citations for {successful_citations}/{len(citation_papers)} papers")

            return enriched_papers
        except Exception as e:
            logger.error(f"Citation enrichment failed: {str(e)}")
            for paper in papers:
                paper['citation_count'] = 0
                paper['has_citations'] = False
            return papers

    def get_popular_papers(self, query: str, start_date: Optional[str] = None,
                           end_date: Optional[str] = None, max_results: int = 10) -> List[Dict]:
        initial_results = min(max_results * 3, 50)
        max_citation_papers = min(initial_results, 15)

        papers = self.search_with_citations(
            query, start_date, end_date, initial_results, 'relevance', max_citation_papers
        )

        if not papers:
            return papers

        papers_with_citations = [p for p in papers if p.get('has_citations', False)]
        papers_without_citations = [p for p in papers if not p.get('has_citations', False)]

        papers_with_citations.sort(key=lambda x: x.get('citation_count', 0), reverse=True)

        sorted_papers = papers_with_citations + papers_without_citations

        return sorted_papers[:max_results]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    reporter = ArxivReport()

    print("Testing basic search...")
    results = reporter.search("machine learning", max_results=3)
    for paper in results:
        print(f"- {paper['title'][:60]}...")

    print("\nTesting citation search...")
    popular = reporter.get_popular_papers("neural networks", max_results=3)
    for paper in popular:
        citations = paper.get('citation_count', 'N/A')
        has_citations = paper.get('has_citations', False)
        status = "✓" if has_citations else "✗"
        print(f"- {paper['title'][:60]}... (Citations: {citations} {status})")
