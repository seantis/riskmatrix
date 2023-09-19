from riskmatrix.models import Asset
from riskmatrix.models import Risk
from riskmatrix.models import RiskAssessment
from riskmatrix.models import RiskCatalog

from .organization_factory import organization_factory
from .root_factory import root_factory
from .uuid_factory import create_uuid_factory


asset_factory = create_uuid_factory(Asset)
risk_factory = create_uuid_factory(Risk)
risk_assessment_factory = create_uuid_factory(RiskAssessment)
risk_catalog_factory = create_uuid_factory(RiskCatalog)

__all__ = (
    'asset_factory',
    'organization_factory',
    'risk_factory',
    'risk_assessment_factory',
    'risk_catalog_factory',
    'root_factory'
)
