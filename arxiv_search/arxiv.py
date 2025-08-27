import requests
import xml.etree.ElementTree as ET
from urllib.parse import urlencode, quote
from datetime import datetime
from typing import List, Dict, Optional
import re

class ArxivReport:
    BASE_URL = "http://export.arxiv.org/api/query"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'ArxivSearch/1.0 (Python/requests)'
        })

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
        """
        Search arXiv for papers matching the given criteria.

        Args:
            query: Search query string
            start_date: Start date filter (YYYY-MM-DD)
            end_date: End date filter (YYYY-MM-DD)
            max_results: Maximum number of results to return
            sort_by: Sort order ('relevance', 'lastUpdatedDate', 'submittedDate')
            start: Starting index for pagination

        Returns:
            List of paper dictionaries
        """

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
        """
        Get a specific paper by its arXiv ID.

        Args:
            arxiv_id: arXiv ID (e.g., '2301.12345')

        Returns:
            Paper dictionary or None if not found
        """
        try:
            results = self.search(f'id:{arxiv_id}', max_results=1)
            return results[0] if results else None
        except Exception:
            return None

    def _get_semantic_scholar_citations(self, arxiv_id: str, title: str) -> Optional[int]:
        try:
            if '/' in arxiv_id:
                url = f"https://api.semanticscholar.org/graph/v1/paper/{arxiv_id}"
            else:
                url = f"https://api.semanticscholar.org/graph/v1/paper/arXiv:{arxiv_id}"

            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get('citationCount', 0)

            search_url = "https://api.semanticscholar.org/graph/v1/paper/search"
            params = {
                'query': title,
                'fields': 'citationCount,title,arxivId',
                'limit': 5
            }

            response = self.session.get(search_url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                papers = data.get('data', [])
                for paper in papers:
                    if (paper.get('arxivId') == arxiv_id or 
                            self._similar_titles(paper.get('title', ''), title)):
                        return paper.get('citationCount', 0)

            return None
        except Exception:
            return None

    def _similar_titles(self, title1: str, title2: str, threshold: float = 0.8) -> bool:
        """Check if two titles are similar enough to be the same paper."""
        if not title1 or not title2:
            return False

        t1 = re.sub(r'[^\w\s]', '', title1.lower()).strip()
        t2 = re.sub(r'[^\w\s]', '', title2.lower()).strip()

        words1 = set(t1.split())
        words2 = set(t2.split())

        if len(words1) == 0 or len(words2) == 0:
            return False

        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))

        return intersection / union >= threshold

    def _enrich_with_citations(self, papers: List[Dict]) -> List[Dict]:
        """Enrich papers with citation counts from external sources."""
        enriched_papers = []

        for paper in papers:
            enriched_paper = paper.copy()

            if paper.get('arxiv_id') != 'N/A':
                citation_count = self._get_semantic_scholar_citations(
                    paper['arxiv_id'], 
                    paper['title']
                )

                if citation_count is not None:
                    enriched_paper['citation_count'] = citation_count
                    enriched_paper['has_citations'] = True
                else:
                    enriched_paper['citation_count'] = 0
                    enriched_paper['has_citations'] = False
            else:
                enriched_paper['citation_count'] = 0
                enriched_paper['has_citations'] = False

            enriched_papers.append(enriched_paper)

        return enriched_papers

    def search_with_citations(self, query: str, start_date: Optional[str] = None, 
                              end_date: Optional[str] = None, max_results: int = 10, 
                              sort_by: str = 'relevance') -> List[Dict]:
        """
        Search arXiv and enrich results with citation data from external sources.

        Args:
            query: Search query string
            start_date: Start date filter (YYYY-MM-DD)
            end_date: End date filter (YYYY-MM-DD)
            max_results: Maximum number of results to return
            sort_by: Sort order ('relevance', 'lastUpdatedDate', 'submittedDate')

        Returns:
            List of paper dictionaries with citation counts
        """
        papers = self.search(query, start_date, end_date, max_results, sort_by)

        enriched_papers = self._enrich_with_citations(papers)

        return enriched_papers

    def get_popular_papers(self, query: str, start_date: Optional[str] = None,
                           end_date: Optional[str] = None, max_results: int = 10) -> List[Dict]:
        """
        Get papers sorted by popularity (citation count).

        Args:
            query: Search query string
            start_date: Start date filter (YYYY-MM-DD)
            end_date: End date filter (YYYY-MM-DD)
            max_results: Maximum number of results to return

        Returns:
            List of papers sorted by citation count (descending)
        """
        initial_results = min(max_results * 3, 100)

        papers = self.search_with_citations(
            query, start_date, end_date, initial_results, 'relevance'
        )

        papers_with_citations = [p for p in papers if p.get('has_citations', False)]
        papers_without_citations = [p for p in papers if not p.get('has_citations', False)]

        papers_with_citations.sort(key=lambda x: x.get('citation_count', 0), reverse=True)

        sorted_papers = papers_with_citations + papers_without_citations

        return sorted_papers[:max_results]


if __name__ == "__main__":
    reporter = ArxivReport()

    print("Testing basic search...")
    results = reporter.search("machine learning", max_results=3)
    for paper in results:
        print(f"- {paper['title'][:60]}...")

    print("\nTesting citation search...")
    popular = reporter.get_popular_papers("neural networks", max_results=3)
    for paper in popular:
        citations = paper.get('citation_count', 'N/A')
        print(f"- {paper['title'][:60]}... (Citations: {citations})")
