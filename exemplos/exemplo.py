"""
Exemplo de uso do GeoCNES.

Defina sua chave da API HERE na variável de ambiente HERE_API_KEY
(nunca coloque a chave diretamente no código que vai para o GitHub).

    Windows (PowerShell):  $env:HERE_API_KEY = "sua_chave"
    Linux/macOS:           export HERE_API_KEY="sua_chave"
"""

import os

from geocnes import geocnes

here_api = os.environ["HERE_API_KEY"]

# code_un: tipo de estabelecimento CNES
#   '02' = Centro de Saúde / Unidade Básica
#   '05' = Hospital Geral
#   '73' = Pronto Atendimento (UPA)
gdf = geocnes(
    cidade_n="São Carlos",
    uf="SP",
    here_api=here_api,
    code_un="02",
)

if gdf is not None:
    print(gdf[["CNES", "Nome_Fantasia", "is_valid"]].head())
