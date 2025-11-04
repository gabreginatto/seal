"""
Tender Classification System for PNCP Data
Classifies tenders by government level, size, organization type, and relevance to medical supplies
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from config import (
    GovernmentLevel, TenderSize, OrganizationType,
    classify_tender_size, CONTRACTING_MODALITIES, BRAZILIAN_STATES
)

logger = logging.getLogger(__name__)

@dataclass
class ClassificationResult:
    """Result of tender classification"""
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
    is_material: Optional[bool]  # True if materialOuServico="M"

    # Size and relevance
    tender_size: TenderSize
    is_medical_relevant: bool
    medical_relevance_score: float
    medical_keywords_found: List[str]
    reasoning: str

class TenderClassifier:
    """Classifies tenders based on organization data and tender content"""

    def __init__(self):
        # Keywords for government level classification
        self.federal_keywords = {
            # Federal ministries and agencies
            'ministério', 'ministry', 'governo federal', 'federal government',
            'união', 'union', 'presidente da república', 'presidência',
            # Health agencies
            'anvisa', 'agência nacional de vigilância sanitária',
            'sus', 'sistema único de saúde',
            'ministério da saúde', 'ministry of health',
            'fiocruz', 'fundação oswaldo cruz',
            'inca', 'instituto nacional do câncer',
            'funasa', 'fundação nacional de saúde',
            'hemobrás', 'empresa brasileira de hemoderivados',
            # Federal hospitals
            'hospital federal', 'instituto nacional', 'centro nacional',
            # Federal universities with hospitals
            'universidade federal', 'hospital universitário federal',
            'hospital de clínicas federal'
        }

        self.state_keywords = {
            # State government indicators
            'governo do estado', 'state government', 'secretaria de estado',
            'estado de', 'state of', 'governo estadual', 'state government',
            # State health secretariats
            'secretaria estadual de saúde', 'secretaria de saúde do estado',
            'ses', 'saúde estadual', 'state health',
            # State hospitals
            'hospital do estado', 'state hospital', 'hospital estadual',
            'centro estadual', 'instituto estadual',
            # State universities
            'universidade estadual', 'state university',
            'hospital universitário estadual'
        }

        self.municipal_keywords = {
            # Municipal government indicators
            'município', 'municipality', 'prefeitura', 'city hall',
            'câmara municipal', 'city council', 'governo municipal',
            # Municipal health
            'secretaria municipal de saúde', 'secretaria de saúde municipal',
            'sms', 'saúde municipal', 'municipal health',
            # Municipal health facilities
            'hospital municipal', 'municipal hospital',
            'upa', 'unidade de pronto atendimento',
            'posto de saúde', 'health center',
            'centro de saúde municipal', 'municipal health center',
            'policlínica municipal', 'municipal polyclinic'
        }

        # Keywords for organization type classification
        self.hospital_keywords = {
            'hospital', 'hospital', 'nosocomial', 'hospitalar',
            'clínica', 'clinic', 'clinica', 'clinical',
            'maternidade', 'maternity', 'maternidad',
            'santa casa', 'irmandade', 'brotherhood',
            'instituto do coração', 'heart institute',
            'instituto do câncer', 'cancer institute',
            'centro médico', 'medical center',
            'complexo hospitalar', 'hospital complex',
            'hospital de base', 'base hospital',
            'hospital regional', 'regional hospital'
        }

        self.health_secretariat_keywords = {
            'secretaria de saúde', 'health secretariat',
            'secretaria da saúde', 'department of health',
            'vigilância sanitária', 'health surveillance',
            'vigilância epidemiológica', 'epidemiological surveillance',
            'centro de controle', 'control center',
            'fundação de saúde', 'health foundation'
        }

        self.university_keywords = {
            'universidade', 'university', 'universidad',
            'faculdade', 'faculty', 'college',
            'instituto federal', 'federal institute',
            'centro universitário', 'university center',
            'escola superior', 'higher school'
        }

        self.military_keywords = {
            'exército', 'army', 'marinha', 'navy',
            'aeronáutica', 'air force', 'militar', 'military',
            'comando', 'command', 'quartel', 'barracks',
            'hospital militar', 'military hospital',
            'policlínica militar', 'military polyclinic'
        }

        # Medical relevance keywords
        self.medical_keywords = {
            # Medical supplies
            'curativo', 'bandage', 'dressing', 'atadura',
            'gaze', 'gauze', 'esparadrapo', 'tape',
            'algodão', 'cotton', 'seringa', 'syringe',
            'agulha', 'needle', 'cateter', 'catheter',
            'sonda', 'probe', 'tubo', 'tube',
            'máscara', 'mask', 'luva', 'glove',
            'avental', 'gown', 'protetor', 'protector',

            # Medical equipment
            'equipamento médico', 'medical equipment',
            'aparelho médico', 'medical device',
            'instrumental médico', 'medical instruments',
            'material médico', 'medical materials',
            'insumo médico', 'medical supplies',
            'material hospitalar', 'hospital materials',
            'descartável', 'disposable',

            # Medical procedures/areas
            'cirúrgico', 'surgical', 'cirurgia', 'surgery',
            'esterilização', 'sterilization', 'antisséptico', 'antiseptic',
            'assepsia', 'asepsis', 'curativo', 'dressing',
            'ferida', 'wound', 'lesão', 'lesion',
            'tratamento', 'treatment', 'terapia', 'therapy',

            # Medical specialties
            'cardiologia', 'cardiology', 'oncologia', 'oncology',
            'pediatria', 'pediatrics', 'ginecologia', 'gynecology',
            'emergência', 'emergency', 'uti', 'icu',
            'centro cirúrgico', 'surgical center',

            # Health context
            'saúde', 'health', 'medicina', 'medicine',
            'enfermagem', 'nursing', 'farmácia', 'pharmacy',
            'laboratório', 'laboratory', 'diagnóstico', 'diagnosis'
        }

        # High-relevance keywords (stronger indicators)
        self.high_relevance_keywords = {
            'curativo', 'bandage', 'dressing', 'transparente', 'adesivo',
            'fenestrado', 'borda', 'iv', 'intravenoso', 'filme',
            'protectfilm', 'esterilização', 'cirúrgico'
        }

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
        score = min(len(found_keywords) / len(keywords) * 100, 100)
        return score, found_keywords

    def classify_government_level(self, cnpj: str, org_name: str,
                                tender_title: str = "", tender_description: str = "",
                                structured_data: Dict = None) -> Tuple[GovernmentLevel, float, str]:
        """Classify government level using structured data and keyword analysis"""

        # First try to use structured API data if available
        if structured_data:
            # Check if organization has sphere indicators from API
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

        # CNPJ-based rules (simplified - would need more sophisticated logic in practice)
        cnpj_boost = 0
        if cnpj and len(cnpj) >= 14:
            # Federal government CNPJs often start with certain patterns
            if cnpj.startswith(('26', '00', '34')):  # Common federal patterns
                federal_score += 20
                cnpj_boost = 20

        # Determine classification
        max_score = max(federal_score, state_score, municipal_score)

        reasoning_parts = []

        if max_score < 10:  # Very low confidence
            return GovernmentLevel.UNKNOWN, max_score, "Insufficient keywords to determine government level"

        if federal_score == max_score:
            level = GovernmentLevel.FEDERAL
            reasoning_parts.append(f"Federal keywords: {federal_keywords[:3]}")
            if cnpj_boost > 0:
                reasoning_parts.append(f"CNPJ pattern suggests federal (+{cnpj_boost}%)")
        elif state_score == max_score:
            level = GovernmentLevel.STATE
            reasoning_parts.append(f"State keywords: {state_keywords[:3]}")
        else:
            level = GovernmentLevel.MUNICIPAL
            reasoning_parts.append(f"Municipal keywords: {municipal_keywords[:3]}")

        reasoning = "; ".join(reasoning_parts)
        confidence = min(max_score, 95)  # Cap at 95% to account for uncertainty

        return level, confidence, reasoning

    def classify_organization_type(self, org_name: str, tender_title: str = "",
                                 tender_description: str = "", structured_data: Dict = None) -> Tuple[OrganizationType, float, str]:
        """Classify organization type using structured data and keyword analysis"""

        combined_text = f"{org_name} {tender_title} {tender_description}".lower()

        # Calculate scores for each type
        scores = {}
        keywords_found = {}

        scores['hospital'], keywords_found['hospital'] = self._calculate_keyword_score(
            combined_text, self.hospital_keywords)
        scores['health_secretariat'], keywords_found['health_secretariat'] = self._calculate_keyword_score(
            combined_text, self.health_secretariat_keywords)
        scores['university'], keywords_found['university'] = self._calculate_keyword_score(
            combined_text, self.university_keywords)
        scores['military'], keywords_found['military'] = self._calculate_keyword_score(
            combined_text, self.military_keywords)

        # Find best match
        best_type = max(scores.keys(), key=lambda k: scores[k])
        max_score = scores[best_type]

        if max_score < 10:
            return OrganizationType.OTHER, max_score, "No specific organization type keywords found"

        # Map to enum
        type_mapping = {
            'hospital': OrganizationType.HOSPITAL,
            'health_secretariat': OrganizationType.HEALTH_SECRETARIAT,
            'university': OrganizationType.UNIVERSITY,
            'military': OrganizationType.MILITARY
        }

        org_type = type_mapping.get(best_type, OrganizationType.OTHER)
        confidence = min(max_score, 90)
        reasoning = f"Keywords found: {keywords_found[best_type][:3]}"

        return org_type, confidence, reasoning

    def assess_medical_relevance(self, tender_title: str, tender_description: str,
                               items_description: str = "") -> Tuple[bool, float, List[str], str]:
        """Assess if tender is relevant to medical supplies"""

        combined_text = f"{tender_title} {tender_description} {items_description}".lower()

        # Calculate general medical relevance
        medical_score, medical_keywords_found = self._calculate_keyword_score(combined_text, self.medical_keywords)

        # Calculate high-relevance score (for products we specifically sell)
        high_rel_score, high_rel_keywords = self._calculate_keyword_score(combined_text, self.high_relevance_keywords)

        # Combined score with weight on high-relevance keywords
        combined_score = (medical_score * 0.6) + (high_rel_score * 0.4)

        # Determine relevance
        is_relevant = combined_score >= 15 or high_rel_score >= 10

        all_keywords_found = list(set(medical_keywords_found + high_rel_keywords))

        reasoning_parts = []
        if high_rel_keywords:
            reasoning_parts.append(f"High-relevance keywords: {high_rel_keywords[:3]}")
        if medical_keywords_found:
            reasoning_parts.append(f"Medical keywords: {medical_keywords_found[:5]}")

        reasoning = "; ".join(reasoning_parts) if reasoning_parts else "No significant medical keywords found"

        return is_relevant, combined_score, all_keywords_found, reasoning

    def extract_location_info(self, tender_data: Dict) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Extract state, state name, and city from tender data"""

        # Try to get location from structured API fields
        state_code = None
        city = None

        # Look for organization address info
        org_data = tender_data.get('orgao', {})
        if isinstance(org_data, dict):
            # Check for address fields
            endereco = org_data.get('endereco', {})
            if isinstance(endereco, dict):
                state_code = endereco.get('uf') or endereco.get('estado')
                city = endereco.get('municipio') or endereco.get('cidade')

        # Also check top-level fields
        if not state_code:
            state_code = tender_data.get('uf') or tender_data.get('estado')
        if not city:
            city = tender_data.get('municipio') or tender_data.get('cidade')

        # If still no state, try to infer from organization name or CNPJ patterns
        if not state_code:
            org_name = tender_data.get('organization_name', '') or tender_data.get('razaoSocial', '')
            state_code = self._infer_state_from_text(org_name)

        # Get state name from code
        state_name = None
        if state_code and state_code.upper() in BRAZILIAN_STATES:
            state_name = BRAZILIAN_STATES[state_code.upper()]
            state_code = state_code.upper()

        return state_code, state_name, city

    def _infer_state_from_text(self, text: str) -> Optional[str]:
        """Try to infer state from organization name or text"""
        if not text:
            return None

        text_lower = text.lower()

        # Look for explicit state mentions
        for code, name in BRAZILIAN_STATES.items():
            if name.lower() in text_lower or f"estado de {name.lower()}" in text_lower:
                return code

        # Look for common patterns
        state_patterns = {
            'são paulo': 'SP', 'rio de janeiro': 'RJ', 'minas gerais': 'MG',
            'rio grande do sul': 'RS', 'paraná': 'PR', 'santa catarina': 'SC',
            'bahia': 'BA', 'goiás': 'GO', 'pernambuco': 'PE', 'ceará': 'CE'
        }

        for pattern, code in state_patterns.items():
            if pattern in text_lower:
                return code

        return None

    def classify_tender(self, tender_data: Dict) -> ClassificationResult:
        """Complete tender classification with enhanced location and API data extraction"""

        # Extract basic data
        cnpj = tender_data.get('cnpj', '')
        org_name = tender_data.get('organization_name', '') or tender_data.get('razaoSocial', '')
        tender_title = tender_data.get('title', '') or tender_data.get('objeto', '')
        tender_description = tender_data.get('description', '') or tender_data.get('informacaoComplementar', '')
        items_description = tender_data.get('items_summary', '')

        # Extract values - prioritize homologated over estimated
        total_value = (
            tender_data.get('total_homologated_value') or
            tender_data.get('valorTotalHomologado') or
            tender_data.get('total_estimated_value') or
            tender_data.get('valorTotalEstimado') or 0
        )

        # Extract location information
        state_code, state_name, city = self.extract_location_info(tender_data)

        # Extract structured API data
        modality_id = tender_data.get('modalidadeId')
        modality_name = tender_data.get('modalidadeNome')

        # Check if this involves materials (vs services)
        is_material = None
        items = tender_data.get('itens', []) or tender_data.get('itensCompra', [])
        if items:
            # Check if any items are materials
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

        # Assess medical relevance
        is_medical, medical_score, medical_keywords, medical_reasoning = self.assess_medical_relevance(
            tender_title, tender_description, items_description)

        # Enhanced reasoning with location
        reasoning_parts = [f"Gov Level: {gov_reasoning}", f"Org Type: {org_reasoning}", f"Medical: {medical_reasoning}"]
        if state_name:
            reasoning_parts.append(f"Location: {city or 'Unknown city'}, {state_name}")
        if modality_name:
            reasoning_parts.append(f"Modality: {modality_name}")
        combined_reasoning = "; ".join(reasoning_parts)

        return ClassificationResult(
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
            # Size and relevance
            tender_size=tender_size,
            is_medical_relevant=is_medical,
            medical_relevance_score=medical_score,
            medical_keywords_found=medical_keywords,
            reasoning=combined_reasoning
        )

    def batch_classify(self, tenders_data: List[Dict]) -> List[ClassificationResult]:
        """Classify multiple tenders efficiently"""
        results = []
        for tender_data in tenders_data:
            try:
                result = self.classify_tender(tender_data)
                results.append(result)
            except Exception as e:
                logger.error(f"Error classifying tender {tender_data.get('control_number', 'unknown')}: {e}")
                # Return unknown classification with new fields
                results.append(ClassificationResult(
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
                    tender_size=TenderSize.SMALL,
                    is_medical_relevant=False,
                    medical_relevance_score=0,
                    medical_keywords_found=[],
                    reasoning=f"Classification failed: {str(e)}"
                ))
        return results

    def filter_relevant_tenders(self, tenders_data: List[Dict],
                              min_medical_score: float = 15.0,
                              allowed_gov_levels: List[GovernmentLevel] = None,
                              min_value: float = 1000.0) -> List[Dict]:
        """Filter tenders based on relevance criteria"""

        if allowed_gov_levels is None:
            allowed_gov_levels = [GovernmentLevel.FEDERAL, GovernmentLevel.STATE, GovernmentLevel.MUNICIPAL]

        classifications = self.batch_classify(tenders_data)
        filtered_tenders = []

        for tender_data, classification in zip(tenders_data, classifications):
            # Check medical relevance
            if classification.medical_relevance_score < min_medical_score:
                continue

            # Check government level
            if classification.government_level not in allowed_gov_levels:
                continue

            # Check minimum value
            total_value = tender_data.get('total_homologated_value', 0) or tender_data.get('total_estimated_value', 0)
            if total_value < min_value:
                continue

            # Add classification data to tender
            tender_data['classification'] = classification
            filtered_tenders.append(tender_data)

        logger.info(f"Filtered {len(filtered_tenders)} relevant tenders from {len(tenders_data)} total")
        return filtered_tenders


# Utility functions for analysis
def analyze_classifications(classifications: List[ClassificationResult]) -> Dict[str, any]:
    """Analyze classification results for insights"""

    analysis = {
        'total_tenders': len(classifications),
        'government_level_distribution': {},
        'organization_type_distribution': {},
        'tender_size_distribution': {},
        'medical_relevance_stats': {
            'relevant_count': 0,
            'avg_medical_score': 0,
            'top_medical_keywords': {}
        },
        'location_distribution': {},
        'modality_distribution': {}
    }

    # Count distributions
    for result in classifications:
        # Government level
        gov_level = result.government_level.value
        analysis['government_level_distribution'][gov_level] = \
            analysis['government_level_distribution'].get(gov_level, 0) + 1

        # Organization type
        org_type = result.organization_type.value
        analysis['organization_type_distribution'][org_type] = \
            analysis['organization_type_distribution'].get(org_type, 0) + 1

        # Tender size
        size = result.tender_size.value
        analysis['tender_size_distribution'][size] = \
            analysis['tender_size_distribution'].get(size, 0) + 1

        # Medical relevance
        if result.is_medical_relevant:
            analysis['medical_relevance_stats']['relevant_count'] += 1

        # Medical keywords
        for keyword in result.medical_keywords_found:
            analysis['medical_relevance_stats']['top_medical_keywords'][keyword] = \
                analysis['medical_relevance_stats']['top_medical_keywords'].get(keyword, 0) + 1

        # Location distribution
        if result.state_name:
            analysis['location_distribution'][result.state_name] = \
                analysis['location_distribution'].get(result.state_name, 0) + 1

        # Modality distribution
        if result.contracting_modality_name:
            analysis['modality_distribution'][result.contracting_modality_name] = \
                analysis['modality_distribution'].get(result.contracting_modality_name, 0) + 1

    # Calculate averages
    if classifications:
        analysis['medical_relevance_stats']['avg_medical_score'] = \
            sum(r.medical_relevance_score for r in classifications) / len(classifications)

    return analysis


# Test function
def test_classifier():
    """Test the classifier with sample data"""

    sample_tenders = [
        {
            'cnpj': '26.989.715/0001-23',
            'organization_name': 'MINISTÉRIO DA SAÚDE',
            'razaoSocial': 'MINISTÉRIO DA SAÚDE',
            'title': 'PREGÃO ELETRÔNICO - AQUISIÇÃO DE CURATIVOS TRANSPARENTES',
            'objeto': 'PREGÃO ELETRÔNICO - AQUISIÇÃO DE CURATIVOS TRANSPARENTES',
            'description': 'Aquisição de materiais médicos hospitalares: curativos transparentes fenestrados com borda adesiva',
            'valorTotalHomologado': 150000.00,
            'modalidadeId': 6,
            'modalidadeNome': 'Pregão - Eletrônico',
            'uf': 'DF',
            'municipio': 'Brasília',
            'esferaFederal': True,
            'itens': [{'materialOuServico': 'M'}]
        },
        {
            'cnpj': '87.316.755/0001-86',
            'organization_name': 'PREFEITURA MUNICIPAL DE SÃO PAULO',
            'razaoSocial': 'PREFEITURA MUNICIPAL DE SÃO PAULO',
            'title': 'COMPRA DE EQUIPAMENTOS DE INFORMÁTICA',
            'objeto': 'COMPRA DE EQUIPAMENTOS DE INFORMÁTICA',
            'description': 'Aquisição de computadores e equipamentos de TI para secretarias municipais',
            'valorTotalHomologado': 75000.00,
            'modalidadeId': 6,
            'modalidadeNome': 'Pregão - Eletrônico',
            'uf': 'SP',
            'municipio': 'São Paulo',
            'esferaMunicipal': True,
            'itens': [{'materialOuServico': 'M'}]
        },
        {
            'cnpj': '46.374.500/0001-19',
            'organization_name': 'HOSPITAL DAS CLÍNICAS DA UNIVERSIDADE DE SÃO PAULO',
            'razaoSocial': 'HOSPITAL DAS CLÍNICAS DA UNIVERSIDADE DE SÃO PAULO',
            'title': 'MATERIAIS MÉDICO-HOSPITALARES',
            'objeto': 'MATERIAIS MÉDICO-HOSPITALARES',
            'description': 'Curativos, gazes, seringas, materiais para centro cirúrgico',
            'valorTotalHomologado': 500000.00,
            'modalidadeId': 4,
            'modalidadeNome': 'Concorrência - Eletrônica',
            'uf': 'SP',
            'municipio': 'São Paulo',
            'esferaEstadual': True,
            'itens': [{'materialOuServico': 'M'}, {'materialOuServico': 'M'}]
        }
    ]

    classifier = TenderClassifier()
    results = classifier.batch_classify(sample_tenders)

    print("=== TENDER CLASSIFICATION RESULTS ===")
    for tender, result in zip(sample_tenders, results):
        print(f"\nOrganization: {tender['organization_name']}")
        print(f"Title: {tender['title']}")
        print(f"Location: {result.city or 'Unknown'}, {result.state_name or 'Unknown State'} ({result.state_code or 'N/A'})")
        print(f"Government Level: {result.government_level.value} (confidence: {result.government_level_confidence:.1f}%)")
        print(f"Organization Type: {result.organization_type.value} (confidence: {result.organization_type_confidence:.1f}%)")
        print(f"Contracting Modality: {result.contracting_modality_name or 'Unknown'} (ID: {result.contracting_modality_id or 'N/A'})")
        print(f"Is Material: {result.is_material}")
        print(f"Tender Size: {result.tender_size.value}")
        print(f"Medical Relevant: {result.is_medical_relevant} (score: {result.medical_relevance_score:.1f})")
        print(f"Medical Keywords: {result.medical_keywords_found[:5]}")
        print(f"Reasoning: {result.reasoning}")
        print("-" * 50)

    # Test filtering
    filtered = classifier.filter_relevant_tenders(sample_tenders)
    print(f"\nFiltered {len(filtered)} relevant tenders from {len(sample_tenders)} total")

if __name__ == "__main__":
    test_classifier()