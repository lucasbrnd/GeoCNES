"""
Geocodificação de estabelecimentos CNES com o geocodebr (Ipea).

O geocodebr geocodifica endereços brasileiros a partir do CNEFE
(Cadastro Nacional de Endereços para Fins Estatísticos / IBGE),
sem depender de API comercial. Este módulo:

1. Prepara os endereços do CNES no formato exigido pelo geocodebr
   (campos separados e limpos).
2. Executa o geocodebr (pacote Python: pip install geocodebr).
3. Devolve um GeoDataFrame com as mesmas colunas de coordenadas usadas
   pelo fluxo HERE (lat, lon, geometry), além das informações de
   precisão do geocodebr.

Na primeira execução, o geocodebr baixa os dados do CNEFE para o
cache local.
"""

import html
import re
import unicodedata

import geopandas as gpd
import geopy.distance
import pandas as pd


# ---------------------------------------------------------
# 1. Preparação dos endereços
# ---------------------------------------------------------

# Tipos de logradouro "de rua". Só nesses casos o texto após
# marcadores como ESQ, QD, LOTE ou ANDAR é tratado como ruído.
# Endereços no padrão de quadras (ex.: "QN 317 AREA ESPECIAL",
# comuns em Brasília) são mantidos como estão.
_TIPOS_RUA = (
    r"^(RUA|R|AVENIDA|AV|TRAVESSA|TV|ALAMEDA|AL|ESTRADA|EST|"
    r"RODOVIA|ROD|PRACA|PCA|LARGO|VIELA|BECO|LADEIRA)\b"
)

# Marcadores a partir dos quais o restante do logradouro é descartado
_MARCADORES_RUIDO = (
    r"\s+(ESQ|ESQUINA|C/|COM|QD|QUADRA|LT|LOTE|BLOCO|BL|SALA|SL|"
    r"ANDAR|TERREO|LOJA|BOX|FUNDOS|APTO|AP|PAVIMENTO|PAV)\b.*$"
)

_VAZIOS = {"", "NAN", "NONE", "NULL", "-", "0", "00000000"}


def _texto(valor):
    """Converte para texto em maiúsculas, sem entidades HTML
    nem espaços repetidos. Retorna None para valores vazios."""

    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return None

    txt = html.unescape(str(valor))
    txt = unicodedata.normalize("NFKC", txt).upper()
    txt = re.sub(r"\s+", " ", txt).strip(" ,.-")

    return None if txt in _VAZIOS else txt


def limpar_numero(numero, logradouro=None):
    """
    Extrai o número do imóvel como inteiro.

    - "S/N", "SN", "0" ou vazio → None
    - "123A", "123 FUNDOS"      → 123
    - Número vazio, mas logradouro terminado em ", 123" ou "Nº 123"
      → 123 (recuperado do logradouro)
    """

    txt = _texto(numero)

    if txt and not re.fullmatch(r"S\s*/?\s*N[º°O]?", txt):

        # Separador de milhar: "1.250" → "1250"
        txt = re.sub(r"(?<=\d)\.(?=\d{3}\b)", "", txt)

        m = re.match(r"\d+", txt)

        if m and int(m.group()) > 0:
            return int(m.group())

    lg = _texto(logradouro)

    if lg:

        m = re.search(r"(?:,|\bN[º°O]?\.?)\s*(\d+)\s*$", lg)

        if m and int(m.group(1)) > 0:
            return int(m.group(1))

    return None


def limpar_logradouro(logradouro):
    """
    Remove ruídos comuns do logradouro do CNES:

    - número no final (", 123" ou "Nº 123"), que vai para o campo número
    - complementos como "ESQ COM RUA 5", "QD 2A", "1 E 2 ANDAR",
      apenas quando o logradouro começa com um tipo de rua
      (RUA, AV, TRAVESSA...)

    Números que fazem parte do nome ("RUA 16 DE MAIO", "RUA 05")
    são preservados.
    """

    lg = _texto(logradouro)

    if not lg:
        return None

    lg = re.sub(r"(?:,|\bN[º°O]?\.?)\s*\d+\s*$", "", lg).strip(" ,")

    if re.match(_TIPOS_RUA, lg):

        # "AV HILDA 1 E 2 ANDAR" → "AV HILDA"
        limpo = re.sub(
            r"(\s+\d+[º°O]?(\s+E\s+\d+[º°O]?)*)?\s+(ANDAR|PAVIMENTO|PAV)\b.*$",
            "", lg,
        )

        limpo = re.sub(_MARCADORES_RUIDO, "", limpo).strip(" ,")

        # Evita reduzir o logradouro a apenas o tipo ("RUA")
        if len(limpo.split()) >= 2:
            lg = limpo

    return lg or None


def limpar_cep(cep):
    """Mantém apenas dígitos. Retorna o CEP com 8 dígitos
    (completando zeros à esquerda) ou None se inválido."""

    if cep is None or (isinstance(cep, float) and pd.isna(cep)):
        return None

    # CEP lido como número (ex.: 13560000.0)
    if isinstance(cep, (int, float)):
        cep = str(int(cep))

    dig = re.sub(r"\D", "", str(cep))

    if len(dig) == 7:
        dig = dig.zfill(8)

    if len(dig) != 8 or dig == "00000000":
        return None

    return dig


def preparar_enderecos(df, municipio_padrao=None, uf_padrao=None):
    """
    Prepara os endereços do CNES para o geocodebr.

    Parâmetros
    ----------
    df : pandas.DataFrame
        Saída de `fetch_cnes_data_chunks`, com as colunas
        CNES, Logradouro, Numero, Bairro, CEP, Municipio e UF.

    municipio_padrao, uf_padrao : str, opcional
        Usados quando Municipio/UF vierem vazios do CNES.

    Retorno
    -------
    pandas.DataFrame
        Colunas: id, logradouro, numero, cep, localidade,
        municipio, estado.
    """

    prep = pd.DataFrame({"id": range(len(df))})

    prep["logradouro"] = [limpar_logradouro(v) for v in df["Logradouro"]]

    prep["numero"] = pd.array(
        [
            limpar_numero(n, lg)
            for n, lg in zip(df["Numero"], df["Logradouro"])
        ],
        dtype="Int64",
    )

    prep["cep"] = [limpar_cep(v) for v in df["CEP"]]

    prep["localidade"] = [_texto(v) for v in df["Bairro"]]

    prep["municipio"] = [
        _texto(v) or _texto(municipio_padrao) for v in df["Municipio"]
    ]

    prep["estado"] = [_texto(v) or _texto(uf_padrao) for v in df["UF"]]

    return prep


# ---------------------------------------------------------
# 2. Execução do geocodebr
# ---------------------------------------------------------

def geocodificar_geocodebr(df, municipio_padrao=None, uf_padrao=None,
                           n_cores=None):
    """
    Geocodifica os estabelecimentos CNES com o geocodebr.

    Parâmetros
    ----------
    df : pandas.DataFrame
        Saída de `fetch_cnes_data_chunks`.

    municipio_padrao, uf_padrao : str, opcional
        Usados quando Municipio/UF vierem vazios do CNES.

    n_cores : int, opcional
        Núcleos usados pelo geocodebr (padrão: decisão do pacote).

    Retorno
    -------
    geopandas.GeoDataFrame
        Dados originais e as colunas:

        - lat, lon, geometry (EPSG:4326)
        - precisao : nível de precisão do geocodebr
          (numero, numero_aproximado, logradouro, cep, localidade,
          municipio)
        - tipo_resultado : código do caso de busca do geocodebr
        - desvio_metros : incerteza estimada da coordenada
        - endereco_encontrado : endereço do CNEFE correspondente
        - localidade_encontrada, similaridade_logradouro,
          contagem_cnefe, empate : detalhes da correspondência
        - endereco_geocodebr : endereço enviado após a limpeza
    """

    try:
        import pyarrow as pa
        from geocodebr import definir_campos, geocode
    except ImportError as e:
        raise ImportError(
            "O geocodificador 'geocodebr' requer o pacote geocodebr: "
            "pip install geocodebr"
        ) from e

    df = df.reset_index(drop=True).copy()

    prep = preparar_enderecos(df, municipio_padrao, uf_padrao)

    # Tipos explícitos: uma coluna inteiramente vazia (ex.: nenhum CEP)
    # seria lida como tipo nulo e recusada pela padronização.
    texto = ["logradouro", "cep", "localidade", "municipio", "estado"]

    tabela = pa.table(
        {
            "id": pa.array(prep["id"], type=pa.int64()),
            "numero": pa.array(
                prep["numero"].astype(object).where(
                    prep["numero"].notna(), None
                ),
                type=pa.int64(),
            ),
            **{
                c: pa.array(
                    prep[c].astype(object).where(prep[c].notna(), None),
                    type=pa.string(),
                )
                for c in texto
            },
        }
    )

    campos = definir_campos(
        estado="estado",
        municipio="municipio",
        logradouro="logradouro",
        numero="numero",
        cep="cep",
        localidade="localidade",
    )

    res = geocode(
        enderecos=tabela,
        campos_endereco=campos,
        resultado_completo=True,
        resolver_empates=True,
        verboso=False,
        cache=True,
        n_cores=n_cores,
    ).to_pandas()

    # Colunas de interesse do geocodebr
    manter = [
        c for c in [
            "id", "lat", "lon", "precisao", "tipo_resultado",
            "desvio_metros", "endereco_encontrado",
            "localidade_encontrada", "similaridade_logradouro",
            "contagem_cnefe", "empate",
        ]
        if c in res.columns
    ]

    res = res[manter].drop_duplicates("id")

    campos_txt = ["logradouro", "numero", "localidade", "cep",
                  "municipio", "estado"]

    out = df.copy()
    out["endereco_geocodebr"] = [
        ", ".join(str(v) for v in linha if pd.notna(v))
        for linha in prep[campos_txt].itertuples(index=False)
    ]

    # prep["id"] é a posição da linha em df (0..n-1)
    out = out.join(res.set_index("id"))

    return gpd.GeoDataFrame(
        out,
        geometry=gpd.points_from_xy(out["lon"], out["lat"]),
        crs="EPSG:4326",
    )


# ---------------------------------------------------------
# 3. Validação
# ---------------------------------------------------------

# Níveis de precisão do geocodebr, do mais preciso ao menos preciso
NIVEIS_PRECISAO = [
    "numero",
    "numero_aproximado",
    "logradouro",
    "cep",
    "localidade",
    "municipio",
]


def centro_municipio(code_mun):
    """Centróide do município (geobr), como (lon, lat)."""

    import geobr

    mun = geobr.read_municipality(code_muni=int(code_mun), year=2022)
    c = mun.to_crs(5880).geometry.centroid.to_crs(4326).iloc[0]

    return c.x, c.y


def validar_geocodebr(gdf, code_mun, precisao_minima="logradouro",
                      dist_max_km=50):
    """
    Valida o resultado do geocodebr.

    Um registro precisa de revisão (is_valid = False) quando:

    - não foi geocodificado
    - a precisão é pior que `precisao_minima`
      (ex.: com 'logradouro', resultados por CEP, bairro ou
      município ficam para revisão)
    - houve empate, ou seja, mais de um endereço do CNEFE
      corresponde à busca (ex.: a mesma rua e número em bairros
      diferentes). Em teste com 2.779 unidades, 45% dos empates
      ficaram a mais de 1 km da posição obtida pela HERE,
      contra 7% dos demais.
    - está a mais de `dist_max_km` do centro do município

    Retorno
    -------
    geopandas.GeoDataFrame com as colunas is_valid e validation_issues.
    """

    gdf = gdf.copy()

    limite = NIVEIS_PRECISAO.index(precisao_minima)

    try:
        c_lon, c_lat = centro_municipio(code_mun)
    except Exception:
        c_lon = c_lat = None

    validos, problemas = [], []

    for _, row in gdf.iterrows():

        issues = []

        if pd.isna(row["lat"]) or pd.isna(row["lon"]):

            issues.append("⚠ Endereço não encontrado no CNEFE")

        else:

            prec = row.get("precisao")

            if prec in NIVEIS_PRECISAO and \
                    NIVEIS_PRECISAO.index(prec) > limite:
                issues.append(f"Precisão baixa ({prec})")

            if str(row.get("empate")).upper() == "TRUE":
                issues.append(
                    "Empate: mais de um endereço possível no CNEFE"
                )

            if c_lat is not None:

                d = geopy.distance.distance(
                    (row["lat"], row["lon"]), (c_lat, c_lon)
                ).km

                if d > dist_max_km:
                    issues.append(
                        f"Distância elevada do centro ({d:.1f} km)"
                    )

        validos.append(not issues)
        problemas.append("; ".join(issues) if issues else None)

    gdf["is_valid"] = validos
    gdf["validation_issues"] = problemas

    return gdf
