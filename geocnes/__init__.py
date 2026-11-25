"""
GeoCNES — obtenção e geocodificação de estabelecimentos de saúde do CNES.

Uso básico:

    from geocnes import geocnes
    gdf = geocnes("São Carlos", "SP", here_api="SUA_CHAVE_HERE")
"""

from .geocnes import (
    geocnes,
    obter_codigo,
    cnes_tab,
    fetch_cnes_data,
    fetch_cnes_data_chunks,
    geocode_chunks,
    process_locations,
    validate_locations,
)

__version__ = "2.0.0"

__all__ = [
    "geocnes",
    "obter_codigo",
    "cnes_tab",
    "fetch_cnes_data",
    "fetch_cnes_data_chunks",
    "geocode_chunks",
    "process_locations",
    "validate_locations",
]
