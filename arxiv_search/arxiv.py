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
        if not start_date:
            start_formatted = "199501010000"
        else:
            try:
                datetime.strptime(start_date, '%Y-%m-%d')
                start_formatted = start_date.replace("-", "") + "0000"
            except ValueError:
                raise ValueError(f"Invalid end date format: {start_date}. Use YYYY-MM-DD")

        if not end_date:
            end_formatted = datetime.today().strftime("%Y%m%d%H%M")
        else:
            try:
                datetime.strptime(end_date, '%Y-%m-%d')
                end_formatted = end_date.replace("-", "") + "0000"
            except ValueError:
                raise ValueError(f"Invalid end date format: {end_date}. Use YYYY-MM-DD")



        date_filters.append(f'submittedDate:[{start_formatted} TO {end_formatted}]')
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
               max_results: int = 10, sort_by: str = 'submittedDate', start: int = 0) -> List[Dict]:
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

    def get_historical_popular_papers(self, query: str, start_date: Optional[str] = None,
                                      end_date: Optional[str] = None, max_results: int = 10) -> List[Dict]:
        """
        Search through historical papers to find the most cited ones.
        Searches in batches across different time periods to find highly cited papers.
        """
        if not end_date:
            end_date = datetime.datetime.today().strftime("%Y%m%d%H%M")
        if not start_date:
            start_date = "199501010000"

        logger.info(f"Searching for highly cited papers from {start_date} to {end_date}")

        all_papers_with_citations = []
        batch_size = 30
        max_batches = 8  # Search up to 240 papers total

        # Search in batches
        for batch_num in range(max_batches):
            start_idx = batch_num * batch_size

            try:
                logger.info(f"Fetching batch {batch_num + 1}/{max_batches} (papers {start_idx+1}-{start_idx+batch_size})")

                batch_papers = self.search(
                    query=query,
                    start_date=start_date,
                    end_date=end_date,
                    max_results=batch_size,
                    sort_by='submittedDate',
                    start=start_idx
                )

                if not batch_papers:
                    logger.info(f"No more papers found, stopping search")
                    break

                logger.info(f"Found {len(batch_papers)} papers in batch {batch_num + 1}")

                # Get citations for a subset of papers to save time
                citation_papers = batch_papers[:20]  # Only process first 20 per batch
                logger.info(f"Getting citations for {len(citation_papers)} papers...")

                cited_batch = self.citation_manager.get_citations_batch(citation_papers, max_workers=1)

                # Add papers with any citations
                papers_with_citations = [p for p in cited_batch if p.get('citation_count', 0) > 0]
                if papers_with_citations:
                    logger.info(f"Found {len(papers_with_citations)} papers with citations in this batch")
                    all_papers_with_citations.extend(papers_with_citations)

                # Add remaining papers without citation lookup (they'll have 0 citations)
                remaining_papers = batch_papers[20:]
                for paper in remaining_papers:
                    paper['citation_count'] = 0
                    paper['has_citations'] = False
                all_papers_with_citations.extend(remaining_papers)

                # If we have some good highly-cited papers, we can be more selective
                high_cite_papers = [p for p in all_papers_with_citations if p.get('citation_count', 0) >= 5]
                if len(high_cite_papers) >= max_results:
                    logger.info(f"Found {len(high_cite_papers)} papers with 5+ citations, stopping early")
                    break

            except Exception as e:
                logger.error(f"Error in batch {batch_num + 1}: {str(e)}")
                continue

        if not all_papers_with_citations:
            logger.warning("No papers found in historical search")
            return []

        # Sort all papers by citation count
        all_papers_with_citations.sort(key=lambda x: x.get('citation_count', 0), reverse=True)

        # Return top papers
        top_papers = all_papers_with_citations[:max_results]

        if top_papers:
            highest_citations = top_papers[0].get('citation_count', 0)
            cited_papers = [p for p in top_papers if p.get('citation_count', 0) > 0]
            if cited_papers:
                avg_citations = sum(p.get('citation_count', 0) for p in cited_papers) / len(cited_papers)
                logger.info(f"Returning {len(top_papers)} papers. Highest: {highest_citations}, Average: {avg_citations:.1f}")
            else:
                logger.info(f"Returning {len(top_papers)} papers, but none have citation data")

        return top_papers
    def get_popular_papers(self, query: str, start_date: Optional[str] = None,
                           end_date: Optional[str] = None, max_results: int = 10) -> List[Dict]:
        """
        Get recent papers sorted by popularity (citation count).
        Uses recent papers and limited search for faster results.
        """
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
