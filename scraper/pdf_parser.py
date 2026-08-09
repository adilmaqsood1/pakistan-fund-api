import os
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("pdf_parser")

def extract_top_holdings_from_pdf(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Parses an AMC Fund Manager Report (FMR) PDF file using pdfplumber 
    to extract top holdings tables.
    """
    try:
        import pdfplumber
    except ImportError:
        logger.warning("pdfplumber package is not installed. PDF parsing unavailable.")
        return []

    if not os.path.exists(pdf_path):
        logger.error(f"PDF file not found at: {pdf_path}")
        return []

    holdings = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        if not row or len(row) < 2:
                            continue
                        
                        # Clean cell text
                        cleaned_row = [str(cell).strip() if cell else "" for cell in row]
                        header_str = " ".join(cleaned_row).lower()

                        if "top 10" in header_str or "holdings" in header_str or "portfolio" in header_str:
                            continue

                        # Check if row looks like symbol/name and percentage
                        name = cleaned_row[0]
                        if not name or "asset" in name.lower() or "holding" in name.lower():
                            continue

                        weight_pct = 0.0
                        for item in cleaned_row[1:]:
                            clean_item = item.replace("%", "").replace(",", "").strip()
                            try:
                                val = float(clean_item)
                                if 0.01 <= val <= 100.0:
                                    weight_pct = val
                                    break
                            except ValueError:
                                continue

                        if weight_pct > 0:
                            holdings.append({
                                "asset_name": name,
                                "weight_pct": weight_pct,
                                "page": page_num
                            })
    except Exception as e:
        logger.error(f"Error parsing PDF {pdf_path}: {e}")

    return holdings[:10]
