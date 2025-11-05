"""
Configuration module for PNCP Lacre (Security Seals) Tender Monitoring
Contains lacre-specific classifications and system configurations
"""

from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass

# Import shared configurations from base config (medical config has base definitions)
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'medical'))
from config import (
    BRAZILIAN_STATES, GovernmentLevel, TenderSize, OrganizationType,
    CONTRACTING_MODALITIES, TenderSizeThresholds, DatabaseConfig, APIConfig,
    get_state_name, get_state_codes, classify_tender_size,
    classify_government_level, get_modality_name
)

# Lacre product categories
class LacreType(Enum):
    SECURITY = "security"  # Lacre de segurança
    TAMPER_EVIDENT = "tamper_evident"  # Lacre inviolável
    ANTI_FRAUD = "anti_fraud"  # Lacre antifraude
    NUMBERED = "numbered"  # Lacre numerado
    PERSONALIZED = "personalized"  # Lacre personalizado
    VOID_LABEL = "void_label"  # Etiqueta void
    OTHER = "other"

class LacreMaterial(Enum):
    PLASTIC = "plastic"  # Plástico
    METAL = "metal"  # Metálico
    STEEL = "steel"  # Aço
    NYLON = "nylon"  # Nylon
    POLYPROPYLENE = "polypropylene"  # Polipropileno (PP)
    HDPE = "hdpe"  # PEAD (High-Density Polyethylene)
    MIXED = "mixed"  # Misto
    OTHER = "other"

class LacreApplication(Enum):
    WATER_METER = "water_meter"  # Hidrômetro / Medidor de água
    ENERGY_METER = "energy_meter"  # Medidor de energia
    GAS_METER = "gas_meter"  # Medidor de gás
    ENVELOPE = "envelope"  # Envelope com lacre
    WRISTBAND = "wristband"  # Pulseira com lacre
    GENERAL = "general"  # Uso geral
    OTHER = "other"

@dataclass
class LacreProcessingConfig:
    """Configuration for lacre tender processing parameters"""
    # States to process (empty list means all states)
    enabled_states: List[str] = None

    # Government levels to include
    government_levels: List[GovernmentLevel] = None

    # Minimum tender value to process (BRL)
    min_tender_value: float = 1_000.0

    # Maximum tender value to process (BRL)
    max_tender_value: Optional[float] = None

    # Date range for processing
    start_date: Optional[str] = None  # YYYYMMDD format
    end_date: Optional[str] = None    # YYYYMMDD format

    # Contracting modalities to include
    allowed_modalities: List[int] = None

    # Organization types to include
    allowed_org_types: List[OrganizationType] = None

    # Product matching minimum score
    min_match_score: float = 50.0

    # API rate limiting
    max_requests_per_minute: int = 60
    max_requests_per_hour: int = 1000

    # Lacre-specific filters
    allowed_lacre_types: List[LacreType] = None
    allowed_lacre_materials: List[LacreMaterial] = None
    allowed_lacre_applications: List[LacreApplication] = None

    # Filter for ongoing tenders only (set to False to include completed tenders)
    only_ongoing_tenders: bool = False

    def __post_init__(self):
        """Set defaults for None values"""
        if self.enabled_states is None:
            self.enabled_states = list(BRAZILIAN_STATES.keys())

        if self.government_levels is None:
            self.government_levels = [
                GovernmentLevel.FEDERAL,
                GovernmentLevel.STATE,
                GovernmentLevel.MUNICIPAL
            ]

        if self.allowed_modalities is None:
            # Use same modalities as Medical system for consistency
            # 1: Leilão Eletrônico
            # 4: Concorrência Eletrônica
            # 6: Pregão Eletrônico (80% of tenders) - HIGHEST PRIORITY
            # 8: Dispensa de Licitação
            # 12: Credenciamento (ongoing supply contracts) - Perfect for lacre seals
            self.allowed_modalities = [1, 4, 6, 8, 12]

        if self.allowed_org_types is None:
            # Lacres are used by various government agencies
            self.allowed_org_types = [
                OrganizationType.GOVERNMENT_AGENCY,
                OrganizationType.HEALTH_SECRETARIAT,
                OrganizationType.OTHER
            ]

        if self.allowed_lacre_types is None:
            self.allowed_lacre_types = list(LacreType)

        if self.allowed_lacre_materials is None:
            self.allowed_lacre_materials = list(LacreMaterial)

        if self.allowed_lacre_applications is None:
            self.allowed_lacre_applications = list(LacreApplication)

class LacreDatabaseConfig(DatabaseConfig):
    """Database configuration for lacre data - extends base config"""

    # Lacre database name (in same Cloud SQL instance)
    DATABASE_NAME = "pncp_lacre_data"

    # Table names (same structure as medical)
    TENDERS_TABLE = "tenders"
    TENDER_ITEMS_TABLE = "tender_items"
    ORGANIZATIONS_TABLE = "organizations"
    MATCHED_PRODUCTS_TABLE = "matched_products"
    HOMOLOGATED_RESULTS_TABLE = "homologated_results"
    PROCESSING_LOG_TABLE = "processing_log"

# Lacre relevance keywords - comprehensive list
LACRE_KEYWORDS = {
    # Core lacre terms
    'lacre', 'lacres', 'seal', 'seals', 'selo', 'selos',

    # Types of lacres
    'lacre de segurança', 'security seal', 'lacre inviolável',
    'tamper evident seal', 'lacre antifraude', 'anti-fraud seal',
    'lacre plástico', 'plastic seal', 'lacre metálico', 'metal seal',
    'lacre de aço', 'steel seal', 'lacre de nylon', 'nylon seal',
    'lacre de polipropileno', 'lacre pp', 'polypropylene seal',
    'lacre pead', 'hdpe seal',

    # Specialty lacres
    'selo-lacre', 'seal-lock', 'etiqueta void', 'void label',
    'lacre numerado', 'numbered seal', 'lacre personalizado', 'personalized seal',
    'lacre sequencial', 'sequential seal', 'gravação a laser', 'laser engraving',
    'lacre com numeração', 'lacre identificado', 'lacre rastreável',

    # Applications
    'lacre para hidrômetro', 'water meter seal',
    'lacre medidor de água', 'lacre hidrometria',
    'lacre medidor de energia', 'energy meter seal', 'lacre elétrico',
    'lacre medidor de gás', 'gas meter seal',
    'pulseira com lacre', 'wristband seal', 'pulseira inviolável',
    'envelope com lacre', 'envelope seal', 'envelope de segurança',

    # Features
    'inviolável', 'tamper evident', 'tamper proof',
    'à prova de violação', 'anti-violação', 'antiviolação',
    'segurança', 'security', 'proteção', 'protection',
    'identificação', 'identification', 'rastreabilidade', 'traceability',

    # Materials and construction
    'plástico', 'plastic', 'metálico', 'metallic',
    'aço', 'steel', 'nylon', 'polipropileno', 'polypropylene',
    'pead', 'hdpe', 'policarbonato', 'polycarbonate',

    # Locking mechanisms
    'trava', 'lock', 'travamento', 'locking',
    'fechamento', 'closure', 'dispositivo de segurança',

    # Related terms
    'selagem', 'sealing', 'lacração', 'vedação', 'seal closure',
    'dispositivo inviolável', 'sistema de lacre'
}

# High-relevance keywords (stronger indicators of lacre tenders)
HIGH_RELEVANCE_LACRE_KEYWORDS = {
    'lacre de segurança', 'lacre inviolável', 'lacre antifraude',
    'lacre numerado', 'lacre sequencial', 'etiqueta void',
    'lacre para hidrômetro', 'lacre medidor', 'selo-lacre',
    'pulseira inviolável', 'envelope de segurança',
    'lacre personalizado', 'gravação a laser'
}

# Material-specific keywords
MATERIAL_KEYWORDS = {
    LacreMaterial.PLASTIC: {'plástico', 'plastic', 'plastica', 'plastico'},
    LacreMaterial.METAL: {'metálico', 'metal', 'metalico'},
    LacreMaterial.STEEL: {'aço', 'steel', 'aco'},
    LacreMaterial.NYLON: {'nylon', 'náilon', 'nailon'},
    LacreMaterial.POLYPROPYLENE: {'polipropileno', 'polipropylene', 'pp'},
    LacreMaterial.HDPE: {'pead', 'hdpe', 'polietileno alta densidade'},
}

# Application-specific keywords
APPLICATION_KEYWORDS = {
    LacreApplication.WATER_METER: {
        'hidrômetro', 'hidrometro', 'water meter',
        'medidor de água', 'medidor agua', 'hidrometria'
    },
    LacreApplication.ENERGY_METER: {
        'medidor de energia', 'energy meter', 'medidor elétrico',
        'medidor eletrico', 'relógio de luz', 'relogio de luz'
    },
    LacreApplication.GAS_METER: {
        'medidor de gás', 'medidor de gas', 'gas meter',
        'medidor gás', 'medidor gas'
    },
    LacreApplication.ENVELOPE: {
        'envelope', 'envelopes', 'envelope de segurança',
        'envelope lacrado', 'envelope inviolável'
    },
    LacreApplication.WRISTBAND: {
        'pulseira', 'wristband', 'pulseiras', 'bracelete',
        'pulseira inviolável', 'pulseira de identificação'
    },
}

# Tender status values for ongoing tenders
ONGOING_TENDER_STATUS = {
    'aberta', 'open', 'em andamento', 'in progress',
    'publicada', 'published', 'vigente', 'active',
    'em disputa', 'in dispute', 'aguardando propostas',
    'recebendo propostas', 'receiving proposals'
}

# Tender status values to EXCLUDE (completed tenders)
COMPLETED_TENDER_STATUS = {
    'homologada', 'homologado', 'homologated',
    'concluída', 'concluido', 'concluded', 'completed',
    'adjudicada', 'adjudicado', 'adjudicated',
    'finalizada', 'finalizado', 'finalized',
    'cancelada', 'cancelado', 'cancelled',
    'deserta', 'deserto', 'deserted',
    'fracassada', 'fracassado', 'failed',
    'revogada', 'revogado', 'revoked'
}

def classify_lacre_type(description: str) -> LacreType:
    """Classify lacre type based on description"""
    desc_lower = description.lower()

    if any(kw in desc_lower for kw in ['inviolável', 'tamper evident', 'antiviolação']):
        return LacreType.TAMPER_EVIDENT
    elif any(kw in desc_lower for kw in ['antifraude', 'anti-fraude', 'anti fraud']):
        return LacreType.ANTI_FRAUD
    elif any(kw in desc_lower for kw in ['numerado', 'numbered', 'sequencial', 'sequential']):
        return LacreType.NUMBERED
    elif any(kw in desc_lower for kw in ['void', 'etiqueta void']):
        return LacreType.VOID_LABEL
    elif any(kw in desc_lower for kw in ['personalizado', 'customizado', 'personalized']):
        return LacreType.PERSONALIZED
    elif any(kw in desc_lower for kw in ['segurança', 'security']):
        return LacreType.SECURITY
    else:
        return LacreType.OTHER

def classify_lacre_material(description: str) -> LacreMaterial:
    """Classify lacre material based on description"""
    desc_lower = description.lower()

    # Check each material
    for material, keywords in MATERIAL_KEYWORDS.items():
        if any(kw in desc_lower for kw in keywords):
            return material

    return LacreMaterial.OTHER

def classify_lacre_application(description: str) -> LacreApplication:
    """Classify lacre application based on description"""
    desc_lower = description.lower()

    # Check each application
    for application, keywords in APPLICATION_KEYWORDS.items():
        if any(kw in desc_lower for kw in keywords):
            return application

    return LacreApplication.GENERAL

# Default configuration instance for lacre processing
DEFAULT_LACRE_CONFIG = LacreProcessingConfig()

# Export key components
__all__ = [
    'BRAZILIAN_STATES',
    'GovernmentLevel',
    'TenderSize',
    'OrganizationType',
    'LacreType',
    'LacreMaterial',
    'LacreApplication',
    'CONTRACTING_MODALITIES',
    'LacreProcessingConfig',
    'LacreDatabaseConfig',
    'APIConfig',
    'DEFAULT_LACRE_CONFIG',
    'LACRE_KEYWORDS',
    'HIGH_RELEVANCE_LACRE_KEYWORDS',
    'MATERIAL_KEYWORDS',
    'APPLICATION_KEYWORDS',
    'ONGOING_TENDER_STATUS',
    'COMPLETED_TENDER_STATUS',
    'get_state_name',
    'get_state_codes',
    'classify_tender_size',
    'classify_government_level',
    'get_modality_name',
    'classify_lacre_type',
    'classify_lacre_material',
    'classify_lacre_application'
]
