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
4. **Geocodificação**: converte os endereços em coordenadas com a API HERE ou com o geocodebr (Ipea).
5. **Validação**: marca como suspeitas as coordenadas ausentes, as que estão a mais de 50 km do centro do município e as idênticas ao centro (sinal de geocodificação genérica).
6. **Relatório e saída**: mostra quantas localizações são válidas e quais precisam de revisão, e salva tudo em `./data/resultados/<cidade>/cnes_<cidade>_<UF>_<tipo>.gpkg`.

---

## Requisitos

* Python 3.10+
* Um dos geocodificadores:
  * chave de API **HERE Geocoding** ([developer.here.com](https://developer.here.com/)), ou
  * **R** com o pacote [geocodebr](https://ipeagit.github.io/geocodebr/) (gratuito, sem chave)

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

### Geocodificação com o geocodebr (Ipea), sem chave de API

Como alternativa à HERE, o GeoCNES pode usar o [geocodebr](https://ipeagit.github.io/geocodebr/), do Ipea. Ele geocodifica a partir do CNEFE (cadastro de endereços do IBGE), é gratuito e roda localmente:

```python
gdf = geocnes("São Carlos", "SP", geocodificador="geocodebr")
```

Requer o R instalado com o pacote geocodebr (`install.packages("geocodebr")`). O `Rscript` é localizado automaticamente. Para indicar outro, defina a variável de ambiente `GEOCNES_RSCRIPT`. Na primeira execução, o geocodebr baixa a base do CNEFE para o cache local.

Antes da geocodificação, os endereços do CNES passam por uma limpeza:

* **Número**: `S/N` ou `0` viram vazio, `123A` vira 123, `1.250` vira 1250. Se o campo vier vazio, tenta-se recuperar o número do final do logradouro (`AV BRASIL, 1500`).
* **Logradouro**: remove o número final e complementos como `ESQ COM RUA 5`, `QD 2A` ou `1 E 2 ANDAR`, apenas quando o endereço começa com um tipo de rua (RUA, AV, TRAVESSA...). Nomes com números (`RUA 16 DE MAIO`) e endereços por quadra (`QN 317 AREA ESPECIAL`) são preservados.
* **CEP**: só dígitos, com 8 posições.
* **Bairro, município e UF**: usados como `localidade`, `municipio` e `estado`.

Um registro fica marcado para revisão (`is_valid = False`) quando:

* não é encontrado;
* a precisão é pior que `precisao_minima` (padrão `"logradouro"`, ou seja, resultados por CEP, bairro ou município);
* há empate (mais de um endereço possível no CNEFE);
* está a mais de 50 km do centro do município.

Colunas adicionais da saída: `precisao`, `tipo_resultado`, `desvio_metros`, `endereco_encontrado`, `localidade_encontrada`, `similaridade_logradouro`, `contagem_cnefe`, `empate` e `endereco_geocodebr` (o endereço enviado após a limpeza). O arquivo é salvo com o sufixo `_geocodebr`.

> **Limitação:** endereços no padrão de quadras e conjuntos (como em Brasília) raramente têm correspondência por logradouro no CNEFE e tendem a ser localizados apenas pelo CEP.

> Não coloque sua chave HERE diretamente no código que vai para o GitHub. Use uma variável de ambiente.

### Parâmetros

| Parâmetro  | Tipo | Padrão | Descrição |
|------------|------|--------|-----------|
| `cidade_n` | str  | —      | Nome do município |
| `uf`       | str  | —      | Sigla da UF (ex.: `"SP"`) |
| `here_api` | str  | `None` | Chave da API HERE (obrigatória com `geocodificador="here"`) |
| `geocodificador` | str | `"here"` | `"here"` ou `"geocodebr"` |
| `precisao_minima` | str | `"logradouro"` | Só para o geocodebr: precisão mínima aceita sem revisão |
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
