import io
import pandas as pd
from typing import Set, Any
from .base import BaseParser, ParseResult

class PandasAdapter(BaseParser):
    """Parses spreadsheets using pandas + openpyxl."""
    
    async def parse(self, file_bytes: bytes, filename: str, metadata: dict[str, Any]) -> ParseResult:
        """Parses spreadsheet bytes into a structured format for normalization."""
        # Using openpyxl for xlsx, standard for csv
        ext = filename.lower().split('.')[-1]
        
        tables = []
        try:
            if ext == "csv":
                df = pd.read_csv(io.BytesIO(file_bytes))
                tables.append({"sheet_name": "Sheet1", "dataframe": df})
            else:
                # xlsx, xls
                excel_data = pd.read_excel(io.BytesIO(file_bytes), sheet_name=None)
                for sheet_name, df in excel_data.items():
                    tables.append({"sheet_name": sheet_name, "dataframe": df})
        except Exception as e:
            # Return empty structure on failure
            return ParseResult({"error": str(e), "tables": []}, page_count=1)

        raw_output = {
            "tables": tables,
            "texts": [],
            "source": "pandas"
        }
        
        return ParseResult(raw_output=raw_output, page_count=len(tables))

    @property
    def supported_formats(self) -> Set[str]:
        return {".csv", ".xlsx", ".xls"}

    @property
    def name(self) -> str:
        return "pandas"

    @property
    def version(self) -> str:
        import pandas
        return pandas.__version__
