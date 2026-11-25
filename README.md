# GeoCNES

Ferramenta em Python para **obter e geocodificar estabelecimentos de saúde do CNES** (Cadastro Nacional de Estabelecimentos de Saúde / DATASUS) de qualquer município brasileiro.

A partir do nome do município e da UF, o GeoCNES consulta o portal do CNES, coleta os dados cadastrais de cada unidade, geocodifica os endereços com a API HERE, valida as coordenadas obtidas e salva o resultado em GeoPackage (`.gpkg`).

O GeoCNES é um dos módulos do [GeoSaúde](https://github.com/lucasbrnd/geosaude), ferramenta de apoio à decisão para a escolha de locais para novas unidades de saúde.

---

## Autoria

**Lucas Brandão Monteiro de Assis**
Departamento de Engenharia de Transportes — EESC/USP

---

## Como funciona

1. **Código IBGE**: identifica o município a partir do nome e da UF (via `geobr`).
2. **Lista CNES**: consulta o portal CNES/DATASUS e obtém os estabelecimentos do tipo escolhido.
3. **Dados detalhados**: coleta nome, endereço, CEP e número de profissionais de cada unidade, em lotes e com novas tentativas automáticas quando o servidor falha.
4. **Geocodificação**: converte os endereços em coordenadas com a API HERE.
5. **Validação**: marca como suspeitas as coordenadas ausentes, as que estão a mais de 50 km do centro do município e as idênticas ao centro (sinal de geocodificação genérica).
6. **Relatório e saída**: mostra quantas localizações são válidas e quais precisam de revisão, e salva tudo em `./data/resultados/<cidade>/cnes_<cidade>_<UF>_<tipo>.gpkg`.

---

## Requisitos

* Python 3.10+
* Chave de API **HERE Geocoding** ([developer.here.com](https://developer.here.com/))

---

## Instalação

Direto do GitHub:

```bash
pip install git+https://github.com/lucasbrnd/GeoCNES.git
```

Ou clonando o repositório:

```bash
git clone https://github.com/lucasbrnd/GeoCNES.git
cd GeoCNES
pip install -e .
```

> Em ambientes Anaconda, recomenda-se instalar `geopandas` antes, via `conda install -c conda-forge geopandas`.

---

## Uso

```python
import os
from geocnes import geocnes

gdf = geocnes(
    cidade_n="São Carlos",
    uf="SP",
    here_api=os.environ["HERE_API_KEY"],
    code_un="02",
)
```

Veja também [`exemplos/exemplo.py`](exemplos/exemplo.py).

> Não coloque sua chave HERE diretamente no código que vai para o GitHub. Use uma variável de ambiente.

### Parâmetros

| Parâmetro  | Tipo | Padrão | Descrição |
|------------|------|--------|-----------|
| `cidade_n` | str  | —      | Nome do município |
| `uf`       | str  | —      | Sigla da UF (ex.: `"SP"`) |
| `here_api` | str  | —      | Chave da API HERE |
| `code_un`  | str  | `"02"` | Tipo de estabelecimento CNES |
| `chunk`    | int  | `20`   | Registros processados por lote |
| `ano`      | str  | `"00"` | Competência CNES (`AAMM`); `"00"` usa a mais recente |

### Tipos de estabelecimento mais usados (`code_un`)

| Código | Tipo |
|--------|------|
| `02` | Centro de Saúde / Unidade Básica |
| `05` | Hospital Geral |
| `73` | Pronto Atendimento (UPA) |

### Saída

Um `GeoDataFrame` (EPSG:4326) com as colunas:

| Coluna | Descrição |
|--------|-----------|
| `CNES` | Código do estabelecimento |
| `Nome_Fantasia` | Nome da unidade |
| `Logradouro`, `Numero`, `Complemento`, `Bairro`, `CEP`, `Municipio`, `UF` | Endereço |
| `prof` | Número de profissionais cadastrados |
| `lat`, `lon`, `geometry` | Coordenadas geocodificadas |
| `is_valid` | Indica se a localização passou na validação |
| `validation_issues` | Motivo de a localização precisar de revisão |

---

## Versões anteriores

A primeira versão (notebook `GeoCNES_1.0.ipynb`, 2024) está em [`legado/`](legado/).
