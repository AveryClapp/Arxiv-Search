import requests
from urllib.parse import urlencode

class ArxivReport():
    BASE_URL = "http://export.arxiv.org/api/query?"

    def __init__(self):
        self.api_str = BASE_URL

    def add_param(self, field: str, value: str):
        self.api_str = self.api_str = urlencode({field: value})

if __name__ == "__main__":
    reporter = ArxivReport()
    print(reporter.getLatest())

