"""
Tender Classification System for Lacre (Security Seals) Tenders
Classifies tenders by government level, size, organization type, and relevance to lacre products
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from .config_lacre import (
    GovernmentLevel, TenderSize, OrganizationType,
    LacreType, LacreMaterial, LacreApplication,
    classify_tender_size, CONTRACTING_MODALITIES, BRAZILIAN_STATES,
    LACRE_KEYWORDS, HIGH_RELEVANCE_LACRE_KEYWORDS,
    MATERIAL_KEYWORDS, APPLICATION_KEYWORDS,
    ONGOING_TENDER_STATUS, COMPLETED_TENDER_STATUS,
    classify_lacre_type, classify_lacre_material, classify_lacre_application
)

logger = logging.getLogger(__name__)

@dataclass
class LacreClassificationResult:
    """Result of lacre tender classification"""
    # Location information
    state_code: Optional[str]
    state_name: Optional[str]
    city: Optional[str]

    # Government classification
    government_level: GovernmentLevel
    government_level_confidence: float

    # Organization classification
    organization_type: OrganizationType
    organization_type_confidence: float

    # Structured API data
    contracting_modality_id: Optional[int]
    contracting_modality_name: Optional[str]
    is_material: Optional[bool]

    # Tender status
    tender_status: Optional[str]
    is_ongoing: bool

    # Size and relevance
    tender_size: TenderSize
    is_lacre_relevant: bool
    lacre_relevance_score: float
    lacre_keywords_found: List[str]

    # Lacre-specific classifications
    lacre_type: Optional[LacreType]
    lacre_material: Optional[LacreMaterial]
    lacre_application: Optional[LacreApplication]

    reasoning: str

class LacreTenderClassifier:
    """Classifies tenders based on organization data and lacre product relevance"""

    def __init__(self):
        # Government level keywords (reuse from medical classifier)
        self.federal_keywords = {
            'ministério', 'ministry', 'governo federal', 'federal government',
            'união', 'union', 'presidente da república', 'presidência',
            'agência nacional', 'instituto nacional', 'centro nacional',
            'universidade federal', 'federal university'
        }

        self.state_keywords = {
            'governo do estado', 'state government', 'secretaria de estado',
            'estado de', 'state of', 'governo estadual',
            'secretaria estadual', 'state secretariat',
            'universidade estadual', 'state university'
        }

        self.municipal_keywords = {
            'município', 'municipality', 'prefeitura', 'city hall',
            'câmara municipal', 'city council', 'governo municipal',
            'secretaria municipal', 'municipal secretariat',
            'companhia municipal', 'empresa municipal'
        }

        # Organization type keywords
        self.utility_company_keywords = {
            'companhia', 'company', 'empresa', 'enterprise',
            'serviços de água', 'water services', 'saneamento', 'sanitation',
            'sabesp', 'copasa', 'caesb', 'cedae', 'embasa',
            'energia', 'energy', 'elétrica', 'electric',
            'cemig', 'celpe', 'coelba', 'light', 'cpfl',
            'gás', 'gas', 'comgas', 'naturgy'
        }

        self.government_agency_keywords = {
            'secretaria', 'secretariat', 'departamento', 'department',
            'autarquia', 'diretoria', 'coordenadoria',
            'fundação', 'foundation', 'instituto', 'institute',
            'agência', 'agency', 'órgão', 'organ'
        }

        # Lacre keywords
        self.lacre_keywords = LACRE_KEYWORDS
        self.high_relevance_keywords = HIGH_RELEVANCE_LACRE_KEYWORDS

    def _calculate_keyword_score(self, text: str, keywords: Set[str]) -> Tuple[float, List[str]]:
        """Calculate keyword matching score and return found keywords"""
        if not text:
            return 0.0, []

        text_lower = text.lower()
        found_keywords = []

        for keyword in keywords:
            if keyword in text_lower:
                found_keywords.append(keyword)

        # Score based on number of unique keywords found
        score = min(len(found_keywords) / max(len(keywords), 1) * 100, 100)
        return score, found_keywords

    def classify_government_level(self, cnpj: str, org_name: str,
                                tender_title: str = "", tender_description: str = "",
                                structured_data: Dict = None) -> Tuple[GovernmentLevel, float, str]:
        """Classify government level using structured data and keyword analysis"""

        # First try to use structured API data if available
        if structured_data:
            if structured_data.get('esferaFederal'):
                return GovernmentLevel.FEDERAL, 95.0, "API data indicates federal sphere"
            elif structured_data.get('esferaEstadual'):
                return GovernmentLevel.STATE, 95.0, "API data indicates state sphere"
            elif structured_data.get('esferaMunicipal'):
                return GovernmentLevel.MUNICIPAL, 95.0, "API data indicates municipal sphere"
            elif structured_data.get('esferaDistrital'):
                return GovernmentLevel.FEDERAL, 90.0, "API data indicates district sphere (federal)"

        # Fall back to keyword analysis
        combined_text = f"{org_name} {tender_title} {tender_description}".lower()

        # Calculate scores for each level
        federal_score, federal_keywords = self._calculate_keyword_score(combined_text, self.federal_keywords)
        state_score, state_keywords = self._calculate_keyword_score(combined_text, self.state_keywords)
        municipal_score, municipal_keywords = self._calculate_keyword_score(combined_text, self.municipal_keywords)

        # Determine classification
        max_score = max(federal_score, state_score, municipal_score)

        reasoning_parts = []

        if max_score < 10:
            return GovernmentLevel.UNKNOWN, max_score, "Insufficient keywords to determine government level"

        if federal_score == max_score:
            level = GovernmentLevel.FEDERAL
            reasoning_parts.append(f"Federal keywords: {federal_keywords[:3]}")
        elif state_score == max_score:
            level = GovernmentLevel.STATE
            reasoning_parts.append(f"State keywords: {state_keywords[:3]}")
        else:
            level = GovernmentLevel.MUNICIPAL
            reasoning_parts.append(f"Municipal keywords: {municipal_keywords[:3]}")

        reasoning = "; ".join(reasoning_parts)
        confidence = min(max_score, 95)

        return level, confidence, reasoning

    def classify_organization_type(self, org_name: str, tender_title: str = "",
                                 tender_description: str = "", structured_data: Dict = None) -> Tuple[OrganizationType, float, str]:
        """Classify organization type - lacre buyers are typically utility companies or government agencies"""

        combined_text = f"{org_name} {tender_title} {tender_description}".lower()

        # Calculate scores for each type
        scores = {}
        keywords_found = {}

        scores['utility'], keywords_found['utility'] = self._calculate_keyword_score(
            combined_text, self.utility_company_keywords)
        scores['government'], keywords_found['government'] = self._calculate_keyword_score(
            combined_text, self.government_agency_keywords)

        # Find best match
        best_type = max(scores.keys(), key=lambda k: scores[k])
        max_score = scores[best_type]

        if max_score < 10:
            return OrganizationType.OTHER, max_score, "No specific organization type keywords found"

        # Map to enum
        if best_type == 'utility':
            org_type = OrganizationType.GOVERNMENT_AGENCY  # Utilities often government-owned
            reasoning = f"Utility company keywords: {keywords_found['utility'][:3]}"
        else:
            org_type = OrganizationType.GOVERNMENT_AGENCY
            reasoning = f"Government agency keywords: {keywords_found['government'][:3]}"

        confidence = min(max_score, 90)

        return org_type, confidence, reasoning

    def assess_lacre_relevance(self, tender_title: str, tender_description: str,
                               items_description: str = "") -> Tuple[bool, float, List[str], str]:
        """Assess if tender is relevant to lacre products"""

        combined_text = f"{tender_title} {tender_description} {items_description}".lower()

        # Calculate general lacre relevance
        lacre_score, lacre_keywords_found = self._calculate_keyword_score(combined_text, self.lacre_keywords)

        # Calculate high-relevance score (for specific lacre products)
        high_rel_score, high_rel_keywords = self._calculate_keyword_score(combined_text, self.high_relevance_keywords)

        # Combined score with weight on high-relevance keywords
        combined_score = (lacre_score * 0.6) + (high_rel_score * 0.4)

        # Determine relevance - must have "lacre" or related term
        has_core_term = any(term in combined_text for term in ['lacre', 'selo', 'seal', 'inviolável', 'tamper'])
        is_relevant = has_core_term and (combined_score >= 15 or high_rel_score >= 10)

        all_keywords_found = list(set(lacre_keywords_found + high_rel_keywords))

        reasoning_parts = []
        if high_rel_keywords:
            reasoning_parts.append(f"High-relevance keywords: {high_rel_keywords[:3]}")
        if lacre_keywords_found:
            reasoning_parts.append(f"Lacre keywords: {lacre_keywords_found[:5]}")
        if not has_core_term:
            reasoning_parts.append("Missing core lacre terms")

        reasoning = "; ".join(reasoning_parts) if reasoning_parts else "No significant lacre keywords found"

        return is_relevant, combined_score, all_keywords_found, reasoning

    def check_tender_status(self, tender_data: Dict) -> Tuple[Optional[str], bool]:
        """Check if tender is ongoing (not completed)"""

        # Check various status fields from API
        status = (
            tender_data.get('situacaoCompra') or
            tender_data.get('situacao') or
            tender_data.get('statusCompra') or
            tender_data.get('status') or
            ''
        ).lower()

        # Check if status indicates ongoing tender
        is_ongoing = any(ongoing_status in status for ongoing_status in ONGOING_TENDER_STATUS)

        # Check if status indicates completed tender (should be excluded)
        is_completed = any(completed_status in status for completed_status in COMPLETED_TENDER_STATUS)

        # If no clear status, check dates to infer
        if not is_ongoing and not is_completed:
            # Check if tender has publication date but no homologation date
            has_pub_date = tender_data.get('dataPublicacao') or tender_data.get('dataPublicacaoPncp')
            has_homolog_date = tender_data.get('dataHomologacao') or tender_data.get('dataResultado')

            if has_pub_date and not has_homolog_date:
                is_ongoing = True
                status = 'inferred_ongoing'

        return status, is_ongoing and not is_completed

    def extract_location_info(self, tender_data: Dict) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Extract state, state name, and city from tender data"""

        state_code = None
        city = None

        # Look for organization address info
        org_data = tender_data.get('orgao', {})
        if isinstance(org_data, dict):
            endereco = org_data.get('endereco', {})
            if isinstance(endereco, dict):
                state_code = endereco.get('uf') or endereco.get('estado')
                city = endereco.get('municipio') or endereco.get('cidade')

        # Also check top-level fields
        if not state_code:
            state_code = tender_data.get('uf') or tender_data.get('estado')
        if not city:
            city = tender_data.get('municipio') or tender_data.get('cidade')

        # Get state name from code
        state_name = None
        if state_code and state_code.upper() in BRAZILIAN_STATES:
            state_name = BRAZILIAN_STATES[state_code.upper()]
            state_code = state_code.upper()

        return state_code, state_name, city

    def classify_tender(self, tender_data: Dict) -> LacreClassificationResult:
        """Complete tender classification for lacre products"""

        # Extract basic data
        cnpj = tender_data.get('cnpj', '')
        org_name = tender_data.get('organization_name', '') or tender_data.get('razaoSocial', '')
        tender_title = tender_data.get('title', '') or tender_data.get('objeto', '')
        tender_description = tender_data.get('description', '') or tender_data.get('informacaoComplementar', '')
        items_description = tender_data.get('items_summary', '')

        # Extract values
        total_value = (
            tender_data.get('total_estimated_value') or
            tender_data.get('valorTotalEstimado') or
            tender_data.get('total_homologated_value') or
            tender_data.get('valorTotalHomologado') or 0
        )

        # Extract location information
        state_code, state_name, city = self.extract_location_info(tender_data)

        # Extract structured API data
        modality_id = tender_data.get('modalidadeId')
        modality_name = tender_data.get('modalidadeNome')

        # Check tender status (ongoing vs completed)
        tender_status, is_ongoing = self.check_tender_status(tender_data)

        # Check if this involves materials (vs services)
        is_material = None
        items = tender_data.get('itens', []) or tender_data.get('itensCompra', [])
        if items:
            material_items = [item for item in items if item.get('materialOuServico') == 'M']
            is_material = len(material_items) > 0

        # Classify government level
        gov_level, gov_confidence, gov_reasoning = self.classify_government_level(
            cnpj, org_name, tender_title, tender_description, tender_data)

        # Classify organization type
        org_type, org_confidence, org_reasoning = self.classify_organization_type(
            org_name, tender_title, tender_description, tender_data)

        # Classify tender size
        tender_size = classify_tender_size(total_value)

        # Assess lacre relevance
        is_lacre, lacre_score, lacre_keywords, lacre_reasoning = self.assess_lacre_relevance(
            tender_title, tender_description, items_description)

        # Classify lacre specifics if relevant
        combined_desc = f"{tender_title} {tender_description} {items_description}"
        lacre_type = classify_lacre_type(combined_desc) if is_lacre else None
        lacre_material = classify_lacre_material(combined_desc) if is_lacre else None
        lacre_application = classify_lacre_application(combined_desc) if is_lacre else None

        # Enhanced reasoning
        reasoning_parts = [
            f"Gov Level: {gov_reasoning}",
            f"Org Type: {org_reasoning}",
            f"Lacre: {lacre_reasoning}",
            f"Status: {tender_status or 'unknown'} (ongoing={is_ongoing})"
        ]
        if state_name:
            reasoning_parts.append(f"Location: {city or 'Unknown city'}, {state_name}")
        if modality_name:
            reasoning_parts.append(f"Modality: {modality_name}")
        if lacre_type:
            reasoning_parts.append(f"Lacre Type: {lacre_type.value}")
        if lacre_material:
            reasoning_parts.append(f"Material: {lacre_material.value}")
        if lacre_application:
            reasoning_parts.append(f"Application: {lacre_application.value}")

        combined_reasoning = "; ".join(reasoning_parts)

        return LacreClassificationResult(
            # Location
            state_code=state_code,
            state_name=state_name,
            city=city,
            # Government classification
            government_level=gov_level,
            government_level_confidence=gov_confidence,
            # Organization classification
            organization_type=org_type,
            organization_type_confidence=org_confidence,
            # Structured API data
            contracting_modality_id=modality_id,
            contracting_modality_name=modality_name,
            is_material=is_material,
            # Tender status
            tender_status=tender_status,
            is_ongoing=is_ongoing,
            # Size and relevance
            tender_size=tender_size,
            is_lacre_relevant=is_lacre,
            lacre_relevance_score=lacre_score,
            lacre_keywords_found=lacre_keywords,
            # Lacre specifics
            lacre_type=lacre_type,
            lacre_material=lacre_material,
            lacre_application=lacre_application,
            reasoning=combined_reasoning
        )

    def batch_classify(self, tenders_data: List[Dict]) -> List[LacreClassificationResult]:
        """Classify multiple tenders efficiently"""
        results = []
        for tender_data in tenders_data:
            try:
                result = self.classify_tender(tender_data)
                results.append(result)
            except Exception as e:
                logger.error(f"Error classifying tender {tender_data.get('control_number', 'unknown')}: {e}")
                # Return unknown classification
                results.append(LacreClassificationResult(
                    state_code=None,
                    state_name=None,
                    city=None,
                    government_level=GovernmentLevel.UNKNOWN,
                    government_level_confidence=0,
                    organization_type=OrganizationType.OTHER,
                    organization_type_confidence=0,
                    contracting_modality_id=None,
                    contracting_modality_name=None,
                    is_material=None,
                    tender_status=None,
                    is_ongoing=False,
                    tender_size=TenderSize.SMALL,
                    is_lacre_relevant=False,
                    lacre_relevance_score=0,
                    lacre_keywords_found=[],
                    lacre_type=None,
                    lacre_material=None,
                    lacre_application=None,
                    reasoning=f"Classification failed: {str(e)}"
                ))
        return results

    def filter_relevant_tenders(self, tenders_data: List[Dict],
                              min_lacre_score: float = 15.0,
                              allowed_gov_levels: List[GovernmentLevel] = None,
                              min_value: float = 1000.0,
                              only_ongoing: bool = True) -> List[Dict]:
        """Filter tenders based on lacre relevance criteria"""

        if allowed_gov_levels is None:
            allowed_gov_levels = [GovernmentLevel.FEDERAL, GovernmentLevel.STATE, GovernmentLevel.MUNICIPAL]

        classifications = self.batch_classify(tenders_data)
        filtered_tenders = []

        for tender_data, classification in zip(tenders_data, classifications):
            # Check lacre relevance
            if classification.lacre_relevance_score < min_lacre_score:
                continue

            # Check government level
            if classification.government_level not in allowed_gov_levels:
                continue

            # Check minimum value
            total_value = tender_data.get('total_estimated_value', 0) or tender_data.get('total_homologated_value', 0)
            if total_value < min_value:
                continue

            # Check if ongoing (if required)
            if only_ongoing and not classification.is_ongoing:
                continue

            # Add classification data to tender
            tender_data['classification'] = classification
            filtered_tenders.append(tender_data)

        logger.info(f"Filtered {len(filtered_tenders)} relevant lacre tenders from {len(tenders_data)} total")
        return filtered_tenders


# Test function
def test_lacre_classifier():
    """Test the lacre classifier with sample data"""

    sample_tenders = [
        {
            'cnpj': '87.316.755/0001-86',
            'organization_name': 'COMPANHIA DE SANEAMENTO BÁSICO DO ESTADO DE SÃO PAULO - SABESP',
            'razaoSocial': 'SABESP',
            'title': 'PREGÃO ELETRÔNICO - AQUISIÇÃO DE LACRES DE SEGURANÇA PARA HIDRÔMETROS',
            'objeto': 'Aquisição de lacres de segurança invioláveis em polipropileno para hidrômetros',
            'description': 'Lacre de segurança numerado, inviolável, em polipropileno (PP), para aplicação em hidrômetros',
            'valorTotalEstimado': 250000.00,
            'modalidadeId': 6,
            'modalidadeNome': 'Pregão - Eletrônico',
            'uf': 'SP',
            'municipio': 'São Paulo',
            'esferaEstadual': True,
            'situacaoCompra': 'Em andamento',
            'itens': [{'materialOuServico': 'M'}]
        },
        {
            'cnpj': '46.374.500/0001-19',
            'organization_name': 'COMPANHIA ENERGÉTICA DE MINAS GERAIS - CEMIG',
            'razaoSocial': 'CEMIG',
            'title': 'LACRES METÁLICOS PARA MEDIDORES DE ENERGIA',
            'objeto': 'Aquisição de lacres metálicos numerados para medidores de energia elétrica',
            'description': 'Lacre de segurança metálico, inviolável, com numeração sequencial gravada a laser',
            'valorTotalEstimado': 180000.00,
            'modalidadeId': 6,
            'modalidadeNome': 'Pregão - Eletrônico',
            'uf': 'MG',
            'municipio': 'Belo Horizonte',
            'esferaEstadual': True,
            'situacaoCompra': 'Aberta',
            'itens': [{'materialOuServico': 'M'}]
        },
        {
            'cnpj': '12.345.678/0001-90',
            'organization_name': 'PREFEITURA MUNICIPAL DE BRASÍLIA',
            'razaoSocial': 'PREFEITURA MUNICIPAL DE BRASÍLIA',
            'title': 'AQUISIÇÃO DE COMPUTADORES',
            'objeto': 'Compra de equipamentos de informática',
            'description': 'Computadores desktop para secretarias',
            'valorTotalEstimado': 50000.00,
            'modalidadeId': 6,
            'modalidadeNome': 'Pregão - Eletrônico',
            'uf': 'DF',
            'municipio': 'Brasília',
            'esferaMunicipal': True,
            'situacaoCompra': 'Em andamento',
            'itens': [{'materialOuServico': 'M'}]
        }
    ]

    classifier = LacreTenderClassifier()
    results = classifier.batch_classify(sample_tenders)

    print("=== LACRE TENDER CLASSIFICATION RESULTS ===")
    for tender, result in zip(sample_tenders, results):
        print(f"\nOrganization: {tender['organization_name']}")
        print(f"Title: {tender['title']}")
        print(f"Location: {result.city or 'Unknown'}, {result.state_name or 'Unknown State'}")
        print(f"Status: {result.tender_status} (Ongoing: {result.is_ongoing})")
        print(f"Government Level: {result.government_level.value}")
        print(f"Lacre Relevant: {result.is_lacre_relevant} (score: {result.lacre_relevance_score:.1f})")
        if result.is_lacre_relevant:
            print(f"Lacre Type: {result.lacre_type.value if result.lacre_type else 'N/A'}")
            print(f"Material: {result.lacre_material.value if result.lacre_material else 'N/A'}")
            print(f"Application: {result.lacre_application.value if result.lacre_application else 'N/A'}")
            print(f"Keywords: {result.lacre_keywords_found[:5]}")
        print(f"Reasoning: {result.reasoning[:200]}...")
        print("-" * 80)

    # Test filtering
    filtered = classifier.filter_relevant_tenders(sample_tenders, only_ongoing=True)
    print(f"\n✓ Filtered {len(filtered)} relevant ongoing lacre tenders from {len(sample_tenders)} total")

if __name__ == "__main__":
    test_lacre_classifier()
