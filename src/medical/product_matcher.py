"""
PNCP Tender Item Matcher for Fernandes Medical Products
Matches tender items with Fernandes product list using keywords, dimensions, and fuzzy matching.
"""

import re
from fuzzywuzzy import fuzz
from typing import List, Dict, Tuple, Optional

class ProductMatcher:
    def __init__(self):
        # Medical product keywords in Portuguese/English
        self.keywords = {
            "CURATIVO": ["curativo", "bandage", "dressing", "band", "atadura"],
            "TRANSPARENTE": ["transparente", "transparent", "transp", "clear"],
            "FENESTRADO": ["fenestrado", "fenestrated", "window", "janela"],
            "BORDA": ["borda", "border", "frame", "moldura"],
            "IV": ["iv", "intravenoso", "intravenous", "venoso"],
            "PROTECTFILM": ["protectfilm", "protective", "film", "filme", "protect"],
            "ADESIVO": ["adesivo", "adhesive", "sticky", "cola"],
            "ESTERIL": ["esteril", "sterile", "estéril"],
            "FIXACAO": ["fixacao", "fixação", "fixing", "stabilization", "estabilização"]
        }

        # Dimension tolerance (±20% range)
        self.dimension_tolerance = 0.2

    def normalize_text(self, text: str) -> str:
        """Normalize text for better matching"""
        if not text:
            return ""
        text = text.upper()
        text = re.sub(r'[^\w\s.,]', ' ', text)  # Keep dots and commas for dimensions
        text = re.sub(r'\s+', ' ', text)        # Multiple spaces to single
        return text.strip()

    def extract_dimensions(self, text: str) -> List[Tuple[float, float]]:
        """Extract dimensions from text (e.g., '5x7', '10,5x12,5')"""
        text = self.normalize_text(text)
        # Match patterns like "5x7", "10x12", "8,5x11,5", "5.5x7.2"
        pattern = r'(\d+(?:[.,]\d+)?)\s*[xX×]\s*(\d+(?:[.,]\d+)?)'
        matches = re.findall(pattern, text)

        dimensions = []
        for match in matches:
            try:
                # Convert comma decimal to dot decimal
                width = float(match[0].replace(',', '.'))
                height = float(match[1].replace(',', '.'))
                dimensions.append((width, height))
            except ValueError:
                continue

        return dimensions

    def calculate_keyword_score(self, tender_text: str, product_description: str) -> float:
        """Calculate keyword matching score"""
        tender_normalized = self.normalize_text(tender_text)
        product_normalized = self.normalize_text(product_description)

        total_keywords = len(self.keywords)
        matched_keywords = 0

        for category, keywords in self.keywords.items():
            # Check if any keyword from this category appears in both texts
            tender_has_keyword = any(keyword in tender_normalized for keyword in keywords)
            product_has_keyword = any(keyword in product_normalized for keyword in keywords)

            if tender_has_keyword and product_has_keyword:
                matched_keywords += 1

        return (matched_keywords / total_keywords) * 100 if total_keywords > 0 else 0

    def calculate_dimension_score(self, tender_text: str, product_description: str) -> float:
        """Calculate dimension matching score with tolerance"""
        tender_dims = self.extract_dimensions(tender_text)
        product_dims = self.extract_dimensions(product_description)

        if not tender_dims or not product_dims:
            return 0

        best_score = 0
        for t_width, t_height in tender_dims:
            for p_width, p_height in product_dims:
                # Calculate tolerance ranges
                width_tolerance = p_width * self.dimension_tolerance
                height_tolerance = p_height * self.dimension_tolerance

                # Check if tender dimensions are within tolerance
                width_match = (p_width - width_tolerance) <= t_width <= (p_width + width_tolerance)
                height_match = (p_height - height_tolerance) <= t_height <= (p_height + height_tolerance)

                if width_match and height_match:
                    # Calculate similarity score (closer = higher score)
                    width_diff = abs(t_width - p_width) / p_width
                    height_diff = abs(t_height - p_height) / p_height
                    avg_diff = (width_diff + height_diff) / 2
                    score = max(0, 100 - (avg_diff * 100))
                    best_score = max(best_score, score)

        return best_score

    def calculate_fuzzy_score(self, tender_text: str, product_description: str) -> float:
        """Calculate fuzzy string matching score"""
        tender_normalized = self.normalize_text(tender_text)
        product_normalized = self.normalize_text(product_description)

        # Use partial ratio for better matching of substrings
        return fuzz.partial_ratio(tender_normalized, product_normalized)

    def calculate_composite_score(self, tender_item: str, product: Dict) -> float:
        """Calculate composite matching score"""
        product_description = product.get('DESCRIÇÃO', '')

        # Calculate individual scores
        keyword_score = self.calculate_keyword_score(tender_item, product_description)
        dimension_score = self.calculate_dimension_score(tender_item, product_description)
        fuzzy_score = self.calculate_fuzzy_score(tender_item, product_description)

        # Weighted composite score
        composite_score = (
            keyword_score * 0.4 +      # 40% weight for keywords
            dimension_score * 0.35 +   # 35% weight for dimensions
            fuzzy_score * 0.25         # 25% weight for fuzzy matching
        )

        return composite_score

    def find_best_match(self, tender_item: str, product_list: List[Dict],
                       min_score: float = 50.0) -> Optional[Tuple[Dict, float]]:
        """Find the best matching product for a tender item"""
        if not tender_item or not product_list:
            return None

        best_match = None
        best_score = 0

        for product in product_list:
            score = self.calculate_composite_score(tender_item, product)

            if score > best_score and score >= min_score:
                best_score = score
                best_match = product

        return (best_match, best_score) if best_match else None

    def batch_match(self, tender_items: List[str], product_list: List[Dict],
                   min_score: float = 50.0) -> List[Dict]:
        """Match multiple tender items against product list"""
        results = []

        for i, tender_item in enumerate(tender_items):
            match_result = self.find_best_match(tender_item, product_list, min_score)

            if match_result:
                product, score = match_result
                results.append({
                    'tender_item_index': i,
                    'tender_item_description': tender_item,
                    'matched_product_code': product.get('CÓDIGO', 'N/A'),
                    'matched_product_description': product.get('DESCRIÇÃO', 'N/A'),
                    'match_score': round(score, 2),
                    'fob_price_usd': product.get('FOB NINGBO USD/unit', 'N/A'),
                    'moq': product.get('MOQ/unit', 'N/A')
                })
            else:
                results.append({
                    'tender_item_index': i,
                    'tender_item_description': tender_item,
                    'matched_product_code': None,
                    'matched_product_description': None,
                    'match_score': 0,
                    'fob_price_usd': None,
                    'moq': None
                })

        return results


# Example usage and test function
def test_matcher():
    """Test the matcher with sample data"""

    # Sample Fernandes product list (from PDF)
    sample_products = [
        {
            'CÓDIGO': 'IVFS.5057',
            'DESCRIÇÃO': 'CURATIVO IV TRANSP. FENESTRADO COM BORDA E DUAS FITAS DE ESTABILIZAÇÃO - 5X5-7CM',
            'FOB NINGBO USD/unit': 0.0741,
            'MOQ/unit': 40000
        },
        {
            'CÓDIGO': 'IVFS.67',
            'DESCRIÇÃO': 'CURATIVO IV TRANSP. FENESTRADO COM BORDA E UMA FITA DE IDENTIFICAÇÃO - 6X7CM',
            'FOB NINGBO USD/unit': 0.0541,
            'MOQ/unit': 50000
        },
        {
            'CÓDIGO': 'PRFS67',
            'DESCRIÇÃO': 'CURATIVO TRANSP. 6X7 FRAME STYLE BORDA PROTECT',
            'FOB NINGBO USD/unit': 0.0454,
            'MOQ/unit': 100000
        }
    ]

    # Sample tender items (slightly different descriptions)
    tender_items = [
        "CURATIVO TRANSPARENTE FENESTRADO 5X5CM COM BORDA ADESIVA",
        "BANDAGEM IV TRANSPARENTE 6X7CM COM MOLDURA PROTETORA",
        "CURATIVO ADESIVO TRANSPARENTE 10X12CM ESTERIL"
    ]

    # Test the matcher
    matcher = ProductMatcher()
    results = matcher.batch_match(tender_items, sample_products)

    print("=== MATCHING RESULTS ===")
    for result in results:
        print(f"Tender Item: {result['tender_item_description']}")
        print(f"Best Match: {result['matched_product_description']}")
        print(f"Product Code: {result['matched_product_code']}")
        print(f"Match Score: {result['match_score']}%")
        print(f"FOB Price: ${result['fob_price_usd']}")
        print("-" * 50)

if __name__ == "__main__":
    test_matcher()