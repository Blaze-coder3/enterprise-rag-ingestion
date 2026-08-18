import uuid
from typing import Any, List
from ..core.models import (
    CanonicalDocument,
    ContentNode,
    NodeType,
    BoundingBox,
    TableNode,
    FigureNode,
    ParseQualityMetrics
)
from .base import ParseResult

class DocumentNormalizer:
    """Transforms parser-specific outputs into a unified CanonicalDocument."""
    
    def normalize(self, document_id: str, tenant_id: str, version_id: str,
                  title: str, parse_result: ParseResult, parser_name: str, 
                  parser_version: str, quality_metrics: ParseQualityMetrics,
                  collection_id: str = "default") -> CanonicalDocument:
                  
        doc = CanonicalDocument(
            document_id=document_id,
            tenant_id=tenant_id,
            collection_id=collection_id,
            version_id=version_id,
            title=title,
            page_count=parse_result.page_count,
            parser_name=parser_name,
            parser_version=parser_version,
            parse_quality=quality_metrics
        )
        
        raw = parse_result.raw_output
        
        if parser_name == "docling":
            self._normalize_docling(doc, raw)
        elif parser_name == "azure_di":
            self._normalize_adi(doc, raw)
            
        return doc
        
    def _normalize_docling(self, doc: CanonicalDocument, raw: dict[str, Any]) -> None:
        """Converts Docling export_to_dict() format into CanonicalDocument."""
        
        texts = raw.get("texts", [])
        for item in texts:
            label = item.get("label", "paragraph")
            node_type = NodeType.HEADING if "header" in label else NodeType.PARAGRAPH
            
            bbox = None
            prov = item.get("prov", [])
            page_num = 1
            if prov and len(prov) > 0:
                p = prov[0]
                page_num = p.get("page_no", 1)
                b = p.get("bbox", {})
                if b:
                    bbox = BoundingBox(page=page_num, left=b.get("l", 0), top=b.get("t", 0), 
                                       right=b.get("r", 0), bottom=b.get("b", 0))
            
            node = ContentNode(
                node_type=node_type,
                content=item.get("text", ""),
                page_number=page_num,
                bounding_box=bbox,
                section_id=str(uuid.uuid4())
            )
            doc.content_tree.append(node)
            
        tables = raw.get("tables", [])
        for tbl in tables:
            bbox = None
            prov = tbl.get("prov", [])
            page_num = 1
            if prov and len(prov) > 0:
                p = prov[0]
                page_num = p.get("page_no", 1)
                b = p.get("bbox", {})
                if b:
                    bbox = BoundingBox(page=page_num, left=b.get("l", 0), top=b.get("t", 0), 
                                       right=b.get("r", 0), bottom=b.get("b", 0))
                                       
            data = tbl.get("data", {})
            cells = data.get("table_cells", [])
            
            # Very simplified table reconstruction for the demo
            # In production, this would handle spans and grid layout accurately
            num_rows = data.get("num_rows", 1)
            num_cols = data.get("num_cols", 1)
            
            grid = [["" for _ in range(num_cols)] for _ in range(num_rows)]
            for cell in cells:
                r = cell.get("start_row_offset_idx", 0)
                c = cell.get("start_col_offset_idx", 0)
                if r < num_rows and c < num_cols:
                    grid[r][c] = cell.get("text", "")
                    
            # Generate markdown
            md = ""
            for i, row in enumerate(grid):
                md += "| " + " | ".join(row) + " |\n"
                if i == 0:
                    md += "|" + "|".join(["---" for _ in row]) + "|\n"
                    
            table_node = TableNode(
                caption=None,
                markdown=md,
                rows=grid,
                page_number=page_num,
                bounding_box=bbox,
                section_id=str(uuid.uuid4())
            )
            doc.tables.append(table_node)
            
            # Also add to content tree as a placeholder
            doc.content_tree.append(ContentNode(
                node_type=NodeType.TABLE,
                content=md, # Store markdown directly for now
                page_number=page_num,
                bounding_box=bbox,
                section_id=table_node.section_id
            ))

    def _normalize_adi(self, doc: CanonicalDocument, raw: dict[str, Any]) -> None:
        """Converts ADI JSON format into CanonicalDocument."""
        
        paragraphs = raw.get("paragraphs", [])
        for item in paragraphs:
            role = item.get("role", "paragraph")
            node_type = NodeType.HEADING if role in ["sectionHeading", "title"] else NodeType.PARAGRAPH
            
            # Skip headers/footers for core content
            if role in ["pageHeader", "pageFooter", "pageNumber"]:
                continue
                
            bbox = None
            page_num = 1
            regions = item.get("boundingRegions", [])
            if regions and len(regions) > 0:
                reg = regions[0]
                page_num = reg.get("pageNumber", 1)
                poly = reg.get("polygon", [])
                if poly and len(poly) >= 8:
                    # simplified bbox from polygon
                    bbox = BoundingBox(page=page_num, left=min(poly[0], poly[6]), top=min(poly[1], poly[3]), 
                                       right=max(poly[2], poly[4]), bottom=max(poly[5], poly[7]))
                                       
            node = ContentNode(
                node_type=node_type,
                content=item.get("content", ""),
                page_number=page_num,
                bounding_box=bbox,
                section_id=str(uuid.uuid4())
            )
            doc.content_tree.append(node)
            
        tables = raw.get("tables", [])
        for tbl in tables:
            page_num = 1
            bbox = None
            regions = tbl.get("boundingRegions", [])
            if regions and len(regions) > 0:
                reg = regions[0]
                page_num = reg.get("pageNumber", 1)
                poly = reg.get("polygon", [])
                if poly and len(poly) >= 8:
                    bbox = BoundingBox(page=page_num, left=min(poly[0], poly[6]), top=min(poly[1], poly[3]), 
                                       right=max(poly[2], poly[4]), bottom=max(poly[5], poly[7]))
                                       
            rows = tbl.get("rowCount", 0)
            cols = tbl.get("columnCount", 0)
            cells = tbl.get("cells", [])
            
            grid = [["" for _ in range(cols)] for _ in range(rows)]
            for cell in cells:
                r = cell.get("rowIndex", 0)
                c = cell.get("columnIndex", 0)
                if r < rows and c < cols:
                    grid[r][c] = cell.get("content", "")
                    
            # Generate markdown
            md = ""
            for i, row in enumerate(grid):
                md += "| " + " | ".join(row) + " |\n"
                if i == 0:
                    md += "|" + "|".join(["---" for _ in row]) + "|\n"
                    
            table_node = TableNode(
                caption=None,
                markdown=md,
                rows=grid,
                page_number=page_num,
                bounding_box=bbox,
                section_id=str(uuid.uuid4())
            )
            doc.tables.append(table_node)
            
            # Add to content tree
            doc.content_tree.append(ContentNode(
                node_type=NodeType.TABLE,
                content=md,
                page_number=page_num,
                bounding_box=bbox,
                section_id=table_node.section_id
            ))
