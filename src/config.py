"""
Shared configuration module for PNCP API Integration
Contains Brazilian states, tender classifications, and system configurations
Used by both medical and lacre modules
"""

from enum import Enum
from typing import Dict, List

# Brazilian States and Federal District
BRAZILIAN_STATES = {
    'AC': 'Acre',
    'AL': 'Alagoas',
    'AP': 'Amapá',
    'AM': 'Amazonas',
    'BA': 'Bahia',
    'CE': 'Ceará',
    'DF': 'Distrito Federal',
    'ES': 'Espírito Santo',
    'GO': 'Goiás',
    'MA': 'Maranhão',
    'MT': 'Mato Grosso',
    'MS': 'Mato Grosso do Sul',
    'MG': 'Minas Gerais',
    'PA': 'Pará',
    'PB': 'Paraíba',
    'PR': 'Paraná',
    'PE': 'Pernambuco',
    'PI': 'Piauí',
    'RJ': 'Rio de Janeiro',
    'RN': 'Rio Grande do Norte',
    'RS': 'Rio Grande do Sul',
    'RO': 'Rondônia',
    'RR': 'Roraima',
    'SC': 'Santa Catarina',
    'SP': 'São Paulo',
    'SE': 'Sergipe',
    'TO': 'Tocantins'
}

# Government levels for tender classification
class GovernmentLevel(Enum):
    FEDERAL = "federal"
    STATE = "state"
    MUNICIPAL = "municipal"
    UNKNOWN = "unknown"

# Tender size classification by value (in BRL)
class TenderSize(Enum):
    SMALL = "small"      # < R$ 50,000
    MEDIUM = "medium"    # R$ 50,000 - R$ 500,000
    LARGE = "large"      # R$ 500,000 - R$ 5,000,000
    MEGA = "mega"        # > R$ 5,000,000

# Organization types
class OrganizationType(Enum):
    HOSPITAL = "hospital"
    CLINIC = "clinic"
    HEALTH_SECRETARIAT = "health_secretariat"
    UNIVERSITY = "university"
    GOVERNMENT_AGENCY = "government_agency"
    MILITARY = "military"
    OTHER = "other"

# PNCP Contracting Modalities (from API reference)
CONTRACTING_MODALITIES = {
    1: "Leilão - Eletrônico",
    2: "Diálogo Competitivo",
    3: "Concurso",
    4: "Concorrência - Eletrônica",
    5: "Concorrência - Presencial",
    6: "Pregão - Eletrônico",
    7: "Pregão - Presencial",
    8: "Dispensa de Licitação",
    9: "Inexigibilidade",
    10: "Manifestação de Interesse",
    11: "Pré-qualificação",
    12: "Credenciamento",
    13: "Leilão - Presencial"
}

# Tender size thresholds (in BRL)
class TenderSizeThresholds:
    """Value thresholds for tender size classification"""
    small_max: float = 50_000.0
    medium_max: float = 500_000.0
    large_max: float = 5_000_000.0

# Utility functions
def get_state_name(state_code: str) -> str:
    """Get full state name from code"""
    return BRAZILIAN_STATES.get(state_code.upper(), "Unknown")

def get_state_codes() -> List[str]:
    """Get list of all state codes"""
    return list(BRAZILIAN_STATES.keys())

def classify_tender_size(value: float) -> TenderSize:
    """Classify tender by value"""
    thresholds = TenderSizeThresholds()

    if value < thresholds.small_max:
        return TenderSize.SMALL
    elif value < thresholds.medium_max:
        return TenderSize.MEDIUM
    elif value < thresholds.large_max:
        return TenderSize.LARGE
    else:
        return TenderSize.MEGA

def classify_government_level(cnpj: str, org_name: str = "") -> GovernmentLevel:
    """
    Classify government level based on CNPJ and organization name
    This is a simplified classification - can be enhanced with more rules
    """
    if not cnpj:
        return GovernmentLevel.UNKNOWN

    org_name_lower = org_name.lower()

    # Federal indicators
    federal_keywords = [
        "ministério", "ministry", "federal", "união", "governo federal",
        "anvisa", "sus", "fiocruz", "inca", "funasa"
    ]

    # State indicators
    state_keywords = [
        "estado", "governo do estado", "secretaria de estado",
        "hospital do estado", "ses", "secretaria estadual"
    ]

    # Municipal indicators
    municipal_keywords = [
        "município", "prefeitura", "câmara municipal", "secretaria municipal",
        "hospital municipal", "upa", "sms", "secretaria de saúde municipal"
    ]

    # Check keywords in organization name
    for keyword in federal_keywords:
        if keyword in org_name_lower:
            return GovernmentLevel.FEDERAL

    for keyword in state_keywords:
        if keyword in org_name_lower:
            return GovernmentLevel.STATE

    for keyword in municipal_keywords:
        if keyword in org_name_lower:
            return GovernmentLevel.MUNICIPAL

    # Default classification based on CNPJ patterns (simplified)
    return GovernmentLevel.UNKNOWN

def get_modality_name(code: int) -> str:
    """Get contracting modality name from code"""
    return CONTRACTING_MODALITIES.get(code, f"Unknown ({code})")

# Export key components
__all__ = [
    'BRAZILIAN_STATES',
    'GovernmentLevel',
    'TenderSize',
    'OrganizationType',
    'CONTRACTING_MODALITIES',
    'TenderSizeThresholds',
    'get_state_name',
    'get_state_codes',
    'classify_tender_size',
    'classify_government_level',
    'get_modality_name'
]
