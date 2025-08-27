# Arxiv-Search

A cleaner way to search and discover research papers on [arXiv](https://arxiv.org). Supports advanced filtering, citation analysis, and finding the most impactful papers in any field.

## Why?

The arXiv website is great, but lacks some basic features:

- No way to sort by citation count or popularity
- Hard to find the most influential papers in a field
- Limited filtering and search capabilities
- No easy way to discover related work

This tool fixes that.

## Features

- **Search by topic, author, or keywords**
- **Filter by date ranges and categories**
- **Citation data** from multiple sources (OpenCitations, CrossRef, Semantic Scholar)
- **Historical search** to discover landmark papers
- **Clean command-line interface**

## Installation

```bash
git clone https://github.com/yourusername/arxiv-search
cd arxiv-search
pip install -e .
```

## Quick Start

```bash
# Basic search
arxiv-search --category math --max-results 10


# Search specific topics with citations
arxiv-search --title "neural networks" --citations

# Filter by date and author
arxiv-search --author "Hinton" --start-date 2010-01-01 --citations
```

## Usage

### Basic Search

```bash
arxiv-search --category cs                    # Computer science papers
arxiv-search --sub-category cs.AI             # Specific subcategory
arxiv-search --title "machine learning"       # Search titles
arxiv-search --author "LeCun"                # Search by author
```

### Citation Analysis

```bash
arxiv-search --category math --citations              # Show citation counts
```

### Date Filtering

```bash
arxiv-search --category cs --start-date 2020-01-01    # Papers since 2020
arxiv-search --title "transformers" --start-date 2017-01-01 --end-date 2019-12-31
```

### Discovery Tools

```bash
# Discover influential AI research
arxiv-search --sub-category cs.AI --citations --start-date 2000-01-01
```

## Available Categories

View all categories:

```bash
arxiv-search domains           # List all high-level domains
arxiv-search categories --domain cs    # List CS subcategories
```

**Main domains:** `math`, `cs`, `physics`, `stat`, `q-bio`, `q-fin`, `econ`, `eess`

## Citation Sources

The tool aggregates citation data from:

- **OpenCitations** - Open citation database
- **CrossRef** - Publisher citation data
- **Semantic Scholar** - AI-powered academic search

Citation counts may vary between sources. Papers without DOIs or recent papers may show lower counts.

## Examples

**Find the most cited math papers:**

```bash
arxiv-search --category math --max-results 15
```

**Discover recent AI breakthroughs:**

```bash
arxiv-search --sub-category cs.AI --start-date 2020-01-01 --citations
```

**Research a specific topic:**

```bash
arxiv-search --title "attention mechanism" --citations
```

**Papers by a specific author:**

```bash
arxiv-search --author "Geoffrey Hinton" --citations --max-results 10
```

## Options

| Flag             | Description                                 |
| ---------------- | ------------------------------------------- |
| `--category`     | High-level domain (math, cs, physics, etc.) |
| `--sub-category` | Specific field (cs.AI, math.NT, etc.)       |
| `--title`        | Search paper titles                         |
| `--author`       | Search by author name                       |
| `--start-date`   | Start date (YYYY-MM-DD)                     |
| `--end-date`     | End date (YYYY-MM-DD)                       |
| `--citations`    | Show citation counts                        |
| `--max-results`  | Number of results (default: 10)             |
| `--verbose`      | Show detailed progress                      |

## Notes

- Citation lookups add ~2-3 seconds per paper due to API rate limits
- Recent papers may show low citation counts as they haven't had time to accumulate citations
- Some arXiv papers lack DOIs and may not have citation data available

## Contributing

Pull requests welcome. Please keep the CLI interface clean and focused.

## License

MIT
