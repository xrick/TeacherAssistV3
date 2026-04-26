"""TXT2PPTX template strategies registry.

Each registered strategy is a TemplateStrategy subclass that knows the
recalculated parameters (layout indices, placeholder positions, font scale)
for one specific .pptx template file.

To add a new template, run:
  python utils/inspect_template.py <name>.pptx
  python utils/scaffold_template_class.py <name>.pptx
  # edit the generated file to resolve TODOs
  python utils/validate_template_class.py <ClassName>
  # add the entry to STRATEGIES below
"""
from typing import Optional, Type

from .base import TemplateStrategy
from .ocean_gradient import OceanGradientStrategy
from .college_elegance import CollegeEleganceStrategy
from .data_centric import DataCentricStrategy
from .high_contrast import HighContrastStrategy
from .minimalist_corporate import MinimalistCorporateStrategy
from .modernist import ModernistStrategy
from .startup_edge import StartupEdgeStrategy
from .zen_serenity import ZenSerenityStrategy

# All concrete strategy classes registered here become available through
# the /api/generate endpoint via the request.template field.
# The dict key MUST match the .pptx filename stem inside templates/.
STRATEGIES: dict[str, Type[TemplateStrategy]] = {
    "ocean_gradient":       OceanGradientStrategy,
    "College_Elegance":     CollegeEleganceStrategy,
    "Data_Centric":         DataCentricStrategy,
    "High_Contrast":        HighContrastStrategy,
    "Minimalist_Corporate": MinimalistCorporateStrategy,
    "Modernist":            ModernistStrategy,
    "Startup_Edge":         StartupEdgeStrategy,
    "Zen_Serenity":         ZenSerenityStrategy,
}


def get_strategy(template_id: str) -> Optional[Type[TemplateStrategy]]:
    """Return the strategy class for a template_id, or None if unregistered."""
    return STRATEGIES.get(template_id)


def is_registered(template_id: str) -> bool:
    return template_id in STRATEGIES


def list_registered() -> list[str]:
    return sorted(STRATEGIES.keys())


__all__ = [
    "TemplateStrategy",
    "OceanGradientStrategy",
    "STRATEGIES",
    "get_strategy",
    "is_registered",
    "list_registered",
]
