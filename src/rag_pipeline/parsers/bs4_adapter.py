from bs4 import BeautifulSoup
from typing import Set, Any
from .base import BaseParser, ParseResult

class BS4Adapter(BaseParser):
    """Parses HTML using BeautifulSoup."""
    
    async def parse(self, file_bytes: bytes, filename: str, metadata: dict[str, Any]) -> ParseResult:
        """Parses HTML bytes into a structured format for normalization."""
        try:
            html_content = file_bytes.decode('utf-8', errors='replace')
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract basic text and headings
            texts = []
            for tag in soup.find_all(['h1', 'h2', 'h3', 'p', 'li']):
                if tag.name.startswith('h'):
                    node_type = "heading"
                elif tag.name == 'li':
                    node_type = "list_item"
                else:
                    node_type = "paragraph"
                    
                text_content = tag.get_text(separator=' ', strip=True)
                if text_content:
                    texts.append({
                        "type": node_type,
                        "text": text_content,
                        "tag": tag.name
                    })
                    
            # Extract tables
            tables = []
            for table in soup.find_all('table'):
                rows = []
                for tr in table.find_all('tr'):
                    row = [td.get_text(strip=True) for td in tr.find_all(['th', 'td'])]
                    if row:
                        rows.append(row)
                if rows:
                    tables.append({
                        "rows": rows,
                        "caption": table.caption.get_text(strip=True) if table.caption else None
                    })
            
            raw_output = {
                "texts": texts,
                "tables": tables,
                "title": soup.title.string if soup.title else filename,
                "source": "bs4"
            }
            return ParseResult(raw_output=raw_output, page_count=1)
            
        except Exception as e:
            return ParseResult({"error": str(e), "texts": [], "tables": []}, page_count=1)

    @property
    def supported_formats(self) -> Set[str]:
        return {".html", ".htm"}

    @property
    def name(self) -> str:
        return "bs4"

    @property
    def version(self) -> str:
        import bs4
        return bs4.__version__
