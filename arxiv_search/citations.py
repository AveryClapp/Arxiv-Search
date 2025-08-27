import requests
import time
import concurrent.futures
import logging
import re
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

class CitationProvider:
    def get_citation_count(self, arxiv_id: str, title: str, authors: List[str]) -> Optional[int]:
        raise NotImplementedError

class OpenCitationsProvider(CitationProvider):
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'ArxivSearch/1.0 (mailto:your.email@example.com)',
            'Accept': 'application/json'
        })
        self.base_url = "https://opencitations.net/index/api/v1"
        self.cache = {}
        self.request_delay = 1.0
        self.last_request_time = 0

    def _rate_limit(self):
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.request_delay:
            sleep_time = self.request_delay - time_since_last
            time.sleep(sleep_time)
        self.last_request_time = time.time()

    def get_citation_count(self, arxiv_id: str, title: str, authors: List[str]) -> Optional[int]:
        doi = self._get_doi_from_crossref(arxiv_id, title)
        if not doi:
            return None

        cache_key = f"oc:{doi}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        self._rate_limit()

        try:
            url = f"{self.base_url}/citation-count/{doi}"
            response = self.session.get(url, timeout=15)

            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    citation_count = int(data[0].get('count', 0))
                    self.cache[cache_key] = citation_count
                    logger.info(f"OpenCitations: {doi} has {citation_count} citations")
                    return citation_count
                else:
                    self.cache[cache_key] = 0
                    return 0

            elif response.status_code == 404:
                logger.info(f"DOI {doi} not found in OpenCitations")
                self.cache[cache_key] = 0
                return 0

            else:
                logger.warning(f"OpenCitations returned status {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"OpenCitations API error for {doi}: {str(e)}")
            return None

    def _get_doi_from_crossref(self, arxiv_id: str, title: str) -> Optional[str]:
        if arxiv_id == 'N/A' or not arxiv_id.strip():
            return None

        cache_key = f"doi:{arxiv_id}:{title[:30]}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            search_url = "https://api.crossref.org/works"
            params = {
                'query': f'{title}',
                'rows': 5
            }

            self._rate_limit()
            response = self.session.get(search_url, params=params, timeout=15)

            if response.status_code == 200:
                data = response.json()
                items = data.get('message', {}).get('items', [])

                for item in items:
                    item_title = ' '.join(item.get('title', ['']))
                    if self._similar_titles(item_title, title, threshold=0.7):
                        doi = item.get('DOI')
                        if doi:
                            self.cache[cache_key] = doi
                            logger.info(f"Found DOI for {arxiv_id}: {doi}")
                            return doi

                self.cache[cache_key] = None
                return None

        except Exception as e:
            logger.error(f"CrossRef DOI lookup error for {arxiv_id}: {str(e)}")
            self.cache[cache_key] = None
            return None

    def _similar_titles(self, title1: str, title2: str, threshold: float = 0.7) -> bool:
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

class CrossRefProvider(CitationProvider):
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'ArxivSearch/1.0 (mailto:your.email@example.com)',
            'Accept': 'application/json'
        })
        self.cache = {}
        self.request_delay = 0.5
        self.last_request_time = 0

    def _rate_limit(self):
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.request_delay:
            time.sleep(self.request_delay - time_since_last)
        self.last_request_time = time.time()

    def get_citation_count(self, arxiv_id: str, title: str, authors: List[str]) -> Optional[int]:
        cache_key = f"cr:{arxiv_id}:{title[:30]}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        self._rate_limit()

        try:
            search_url = "https://api.crossref.org/works"
            params = {
                'query': title,
                'rows': 5
            }

            response = self.session.get(search_url, params=params, timeout=15)

            if response.status_code == 200:
                data = response.json()
                items = data.get('message', {}).get('items', [])

                for item in items:
                    item_title = ' '.join(item.get('title', ['']))
                    if self._similar_titles(item_title, title, threshold=0.7):
                        citation_count = item.get('is-referenced-by-count', 0)
                        self.cache[cache_key] = citation_count
                        logger.info(f"CrossRef: found {citation_count} citations for {title[:50]}...")
                        return citation_count

                self.cache[cache_key] = 0
                return 0

        except Exception as e:
            logger.error(f"CrossRef API error: {str(e)}")
            self.cache[cache_key] = 0
            return 0

    def _similar_titles(self, title1: str, title2: str, threshold: float = 0.7) -> bool:
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

class SemanticScholarProvider(CitationProvider):
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'ArxivSearch/1.0 (mailto:your.email@example.com)'
        })
        self.cache = {}
        self.request_delay = 2.0
        self.last_request_time = 0
        self.consecutive_failures = 0
        self.max_failures = 3

    def _rate_limit(self):
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        required_delay = self.request_delay
        if self.consecutive_failures > 0:
            required_delay *= (2 ** min(self.consecutive_failures, 3))

        if time_since_last < required_delay:
            sleep_time = required_delay - time_since_last
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def get_citation_count(self, arxiv_id: str, title: str, authors: List[str]) -> Optional[int]:
        if self.consecutive_failures >= self.max_failures:
            logger.warning("Semantic Scholar disabled due to repeated failures")
            return None

        cache_key = f"ss:{arxiv_id}:{title[:30]}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        self._rate_limit()

        try:
            if '/' in arxiv_id:
                url = f"https://api.semanticscholar.org/graph/v1/paper/{arxiv_id}"
            else:
                url = f"https://api.semanticscholar.org/graph/v1/paper/arXiv:{arxiv_id}"

            response = self.session.get(url, timeout=15)

            if response.status_code == 200:
                data = response.json()
                citation_count = data.get('citationCount', 0)
                self.consecutive_failures = 0
                self.cache[cache_key] = citation_count
                logger.info(f"Semantic Scholar: {arxiv_id} has {citation_count} citations")
                return citation_count

            elif response.status_code == 429:
                logger.warning("Semantic Scholar rate limited - disabling provider")
                self.consecutive_failures += 1
                return None

            elif response.status_code == 404:
                self.consecutive_failures = 0
                self.cache[cache_key] = 0
                return 0

            else:
                logger.warning(f"Semantic Scholar returned status {response.status_code}")
                self.consecutive_failures += 1
                return None

        except Exception as e:
            logger.error(f"Semantic Scholar error for {arxiv_id}: {str(e)}")
            self.consecutive_failures += 1
            return None

class CitationManager:
    def __init__(self):
        self.providers = [
            OpenCitationsProvider(),
            CrossRefProvider(),
            SemanticScholarProvider()
        ]

    def get_citation_count(self, arxiv_id: str, title: str, authors: List[str]) -> Tuple[int, bool]:
        for provider in self.providers:
            try:
                count = provider.get_citation_count(arxiv_id, title, authors)
                if count is not None:
                    return count, True
            except Exception as e:
                logger.warning(f"Provider {type(provider).__name__} failed: {str(e)}")
                continue

        return 0, False

    def get_citations_batch(self, papers: List[Dict], max_workers: int = 1) -> List[Dict]:
        enriched_papers = []

        def get_citation_for_paper(paper):
            enriched_paper = paper.copy()

            if paper.get('arxiv_id') != 'N/A':
                citation_count, success = self.get_citation_count(
                    paper['arxiv_id'],
                    paper['title'],
                    paper.get('authors', [])
                )
                enriched_paper['citation_count'] = citation_count
                enriched_paper['has_citations'] = success
            else:
                enriched_paper['citation_count'] = 0
                enriched_paper['has_citations'] = False

            return enriched_paper

        if max_workers == 1:
            for i, paper in enumerate(papers, 1):
                logger.info(f"Processing paper {i}/{len(papers)}: {paper['title'][:60]}...")
                try:
                    enriched_paper = get_citation_for_paper(paper)
                    enriched_papers.append(enriched_paper)
                except Exception as e:
                    failed_paper = paper.copy()
                    failed_paper['citation_count'] = 0
                    failed_paper['has_citations'] = False
                    enriched_papers.append(failed_paper)
                    logger.error(f"Failed to get citations for paper: {str(e)}")
        else:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_paper = {
                    executor.submit(get_citation_for_paper, paper): paper 
                    for paper in papers
                }

                for future in concurrent.futures.as_completed(future_to_paper, timeout=120):
                    try:
                        enriched_paper = future.result()
                        enriched_papers.append(enriched_paper)
                    except Exception as e:
                        original_paper = future_to_paper[future]
                        failed_paper = original_paper.copy()
                        failed_paper['citation_count'] = 0
                        failed_paper['has_citations'] = False
                        enriched_papers.append(failed_paper)
                        logger.error(f"Failed to get citations for paper: {str(e)}")

        enriched_papers.sort(key=lambda x: papers.index(next((p for p in papers if p['title'] == x['title']), papers[0])))
        return enriched_papers
