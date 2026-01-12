"""arXiv Paper Fetcher: Download and parse papers from arXiv API."""

import requests
import feedparser
import io
from typing import List, Optional
from llama_index.core import Document
from pypdf import PdfReader


def ingest_arxiv_paper(title: str) -> Optional[List[Document]]:
    """
    Fetch arXiv paper by title and return as Document objects.
    
    Args:
        title: Exact paper title to search
        
    Returns:
        List[Document] with metadata, or None if not found
    """
    # Query arXiv API
    api_url = "http://export.arxiv.org/api/query"
    params = {
        'search_query': f'ti:"{title}"',
        'max_results': 1
    }
    
    response = requests.get(api_url, params=params)
    response.raise_for_status()
    
    # Parse Atom XML
    feed = feedparser.parse(response.content)
    
    if not feed.entries:
        print(f"No results found for: {title}")
        return None
    
    entry = feed.entries[0]
    
    # Extract PDF URL
    pdf_url = None
    for link in entry.links:
        if link.get('type') == 'application/pdf':
            pdf_url = link.href
            break
    
    if not pdf_url:
        print("PDF URL not found")
        return None
    
    # Extract metadata
    metadata = {
        'title': entry.title,
        'authors': [author.name for author in entry.authors],
        'arxiv_id': entry.id.split('/')[-1],
        'abstract': entry.summary,
        'pdf_url': pdf_url,
        'published': entry.published
    }
    
    print(f"Found: {metadata['title']}")
    print(f"arXiv ID: {metadata['arxiv_id']}")
    
    # Fetch PDF in-memory
    pdf_response = requests.get(pdf_url)
    pdf_response.raise_for_status()
    
    pdf_file = io.BytesIO(pdf_response.content)
    
    # Parse PDF in-memory with pypdf
    pdf_reader = PdfReader(pdf_file)
    documents = []
    
    for page_num, page in enumerate(pdf_reader.pages, start=1):
        text = page.extract_text()
        
        # Create Document with page-specific metadata
        doc_metadata = metadata.copy()
        doc_metadata['page_label'] = str(page_num)
        doc_metadata['file_name'] = f"{metadata['arxiv_id']}.pdf"
        doc_metadata['file_type'] = 'application/pdf'
        
        doc = Document(
            text=text,
            metadata=doc_metadata
        )
        documents.append(doc)
    
    print(f"Loaded {len(documents)} pages")
    
    return documents
