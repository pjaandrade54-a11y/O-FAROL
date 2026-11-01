"""Cálculo de evidências: classifica uma notícia só com matemática, sem IA.

1. Cada notícia vira um vetor de palavras (TF-IDF): título com peso 2, resumo com peso 1; nomes próprios e
   números valem 1,5 vez mais; palavras que aparecem em muitas notícias do período valem pouco.
2. Duas notícias tratam do mesmo fato quando a similaridade de cosseno entre os vetores passa de LIMIAR_FATO
   e elas saíram com até 72 horas de diferença. Se as duas trazem números e nenhum coincide (o concurso 3079
   e o 3080, R$ 42 mil e R$ 2 mil), a similaridade cai pela metade: números diferentes são fatos diferentes.
3. Cada grupo de mídia diferente do original que publicou o mesmo fato é uma confirmação independente, com
   força p = peso do tipo de veículo × (0,6 + 0,4 × quanto a similaridade passa do limiar).
4. As confirmações se somam como evidências independentes: confiança C = 1 − Π(1 − p).
5. Sinais da própria notícia ajustam a confiança como numa atualização bayesiana: a confiança vira
   chances (C ÷ (1 − C)), cada sinal multiplica as chances (fonte oficial citada × 1,5, autor × 1,15,
   confirmação por tipos diferentes de veículo × 1,15, atribuição vaga × 0,7, sensacionalismo × 0,75,
   sem data × 0,9) e o resultado volta a ser porcentagem. Uma confirmação com texto quase idêntico ao
   original (90% ou mais) é provável reprodução e vale 60% da força.
6. Confirmada exige ao menos dois grupos independentes e confiança final ≥ CONFIANCA_CONFIRMADA.

Tudo é determinístico: a mesma entrada dá sempre o mesmo resultado, e cada número aparece no site.
"""

import math
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timedelta

LIMIAR_FATO = 0.48          # similaridade mínima para considerar o mesmo fato
SIMILARIDADE_FORTE = 0.80   # a partir daqui, a confirmação tem força máxima
CONFIANCA_CONFIRMADA = 0.70
LIMIAR_CHECAGEM = 0.50      # checagem tão parecida assim com a notícia gera aviso
NUMEROS_DIFERENTES = 0.5    # as duas trazem números e nenhum coincide (concurso 3079 x 3080): fatos diferentes
HORAS = 72
MINIMO_DE_PALAVRAS = 4      # menos que isso, não há texto para comparar
COMUM_DEMAIS = 0.05         # palavra em mais de 5% das notícias não serve para achar o mesmo fato

REPRODUCAO = 0.90          # texto quase idêntico: provável reprodução do mesmo texto, não apuração própria
FATOR_REPRODUCAO = 0.6

# Sinais da própria notícia: (fator que multiplica as chances, explicação)
FATOR_FONTE_OFICIAL = 1.5
FATOR_AUTOR = 1.15
FATOR_TIPOS_DIFERENTES = 1.15
FATOR_ATRIBUICAO_VAGA = 0.7
FATOR_SENSACIONALISMO = 0.75   # por sinal, até dois
FATOR_SEM_DATA = 0.9
FONTE_OFICIAL_NOME = re.compile(
    r"\b(pol[ií]cia (militar|civil|federal|rodovi[aá]ria federal)|corpo de bombeiros|bombeiros|defesa civil|"
    r"prefeitura|governo (federal|do estado|estadual)|minist[eé]rio|secretaria|tribunal|justi[cç]a eleitoral|"
    r"c[aâ]mara (municipal|dos deputados)|senado|assembleia legislativa|banco central|receita federal|"
    r"di[aá]rio oficial|caixa econ[oô]mica|instituto nacional)\b", re.I)
FONTE_OFICIAL_SIGLA = re.compile(
    r"\b(PM|PF|PRF|IBGE|Ipea|Inmet|Anvisa|Fiocruz|STF|STJ|TSE|TRE|TCU|TJ[A-Z]{0,2}|MPF|MP[A-Z]{2}|INSS|DOU|"
    r"OMS|ONU|Ibama|ICMBio|Detran|SUS|Petrobras|Aneel|Anatel|Datafolha|Quaest)\b")
ATRIBUICAO_VAGA = re.compile(
    r"\b(fontes? (dizem|afirmam|apontam|ouvidas)|segundo rumores|rumores?|circula(m)? nas redes|viraliza|"
    r"nas redes sociais|teria(m)? (sido|dito|feito)|supostamente|suposto|boato|dizem que)\b", re.I)
SENSACIONALISMO = re.compile(
    r"\b(chocante|urgente|bomba|inacredit[aá]vel|absurdo|esc[aâ]ndalo|bizarro|voc[eê] n[aã]o vai acreditar|"
    r"surpreende|revoltante|assustador|imperd[ií]vel|polêmica|pol[eê]mica)\b", re.I)
CAIXA_ALTA_PERMITIDA = {"VIDEO", "VÍDEO", "FOTOS", "PODCAST", "AO", "VIVO", "AGORA"}

# Quanto vale a confirmação de cada tipo de veículo (checador não confirma fato: ele verifica)
PESO_TIPO = {"agencia": 0.85, "jornal": 0.9, "tv": 0.9, "radio": 0.85, "revista": 0.85,
             "portal": 0.75, "blog": 0.55, "checador": 0.0}
PESO_PADRAO = 0.7

VAZIAS = set("""
a o as os um uma uns umas de da do das dos em na no nas nos por para pela pelo pelas pelos com sem sob
e ou mas que se ao aos à às como mais menos sobre entre apos antes desde ainda ser sera serao foi foram
esta este estao essa esse isso isto aquele aquela quando onde qual quais quem porque tambem muito muita
muitos muitas outro outra outros outras mesmo mesma depois durante contra cada todo toda todos todas seu
sua seus suas nosso nossa diz dizem afirma segundo anuncia apos ha tem teve sao veja confira saiba entenda
video fotos ano anos dia dias hoje ontem amanha nesta neste nessa nesse pode podem vai vao deve devem
noticia noticias apareceu primeiro post leia mais
""".split())
OPINIAO_TITULO = re.compile(r"\b(opini[aã]o|artigo|coluna|editorial|cr[oô]nica)\b", re.I)
OPINIAO_LINK = re.compile(r"/(opiniao|colunas?|colunistas?|artigos?|blogs?|editorial)/", re.I)
CHECAGEM_FALSO = re.compile(r"\b(fals[oa]s?|enganos[oa]s?|fake|sem provas|boato|mentira|mente|distorcid[oa]|"
                            r"fora de contexto|n[aã]o [eé] verdade)\b", re.I)


def _sem_acento(texto):
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()


def termos(texto, peso=1.0):
    """Contagem ponderada das palavras do texto: minúsculas, sem acento, sem plural simples."""
    contagem = Counter()
    for i, bruta in enumerate(re.findall(r"[\wÀ-ÿ]+", texto or "")):
        palavra = _sem_acento(bruta.lower())
        if palavra in VAZIAS or (len(palavra) < 3 and not palavra.isdigit()):
            continue
        if len(palavra) > 4 and palavra.endswith("s") and not palavra.endswith("ss"):
            palavra = palavra[:-1]
        destaque = 1.5 if palavra.isdigit() or (i > 0 and bruta[:1].isupper()) else 1.0
        contagem[palavra] += peso * destaque
    return contagem


def numeros(*textos):
    """Números que identificam o fato (dois dígitos ou mais): concursos, valores, placares, idades."""
    return {n.replace(".", "").replace(",", "") for t in textos for n in re.findall(r"\d[\d.,]*\d", t or "")}


def _quando(linha):
    try:
        return datetime.fromisoformat(linha["publicado_em"] or linha["coletado_em"])
    except (TypeError, ValueError):
        return None


class Corpus:
    """Vetores TF-IDF das notícias recentes, calculados uma vez por execução."""

    def __init__(self, linhas):
        self.linhas = {l["link"]: l for l in linhas}
        brutos = {l["link"]: termos(l["titulo"], 2.0) + termos(l["resumo"], 1.0) for l in linhas}
        total = max(1, len(brutos))
        df = Counter(p for c in brutos.values() for p in c)
        self.idf = {p: math.log((total + 1) / (n + 1)) + 1 for p, n in df.items()}
        self.comum_demais = {p for p, n in df.items() if n > max(5, total * COMUM_DEMAIS)}
        self.vetores = {link: self._vetor(c) for link, c in brutos.items()}
        self.numeros = {l["link"]: numeros(l["titulo"], l["resumo"]) for l in linhas}
        self.por_palavra = defaultdict(set)
        for link, vetor in self.vetores.items():
            for p in vetor:
                if p not in self.comum_demais:
                    self.por_palavra[p].add(link)

    def _vetor(self, contagem):
        vetor = {p: (1 + math.log(n)) * self.idf.get(p, 1.0) for p, n in contagem.items() if n > 0}
        norma = math.sqrt(sum(v * v for v in vetor.values())) or 1.0
        return {p: v / norma for p, v in vetor.items()}

    def vetor(self, noticia):
        if noticia["link"] in self.vetores:
            return self.vetores[noticia["link"]]
        return self._vetor(termos(noticia["titulo"], 2.0) + termos(noticia["resumo"], 1.0))

    def parecidas(self, noticia):
        """(similaridade, linha) das notícias de outros veículos publicadas até 72 h antes ou depois."""
        alvo = self.vetor(noticia)
        quando = _quando(noticia)
        candidatas = set()
        for p in alvo:
            candidatas |= self.por_palavra.get(p, set())
        saida = []
        for link in candidatas:
            outra = self.linhas[link]
            if link == noticia["link"] or outra["veiculo_id"] == noticia["veiculo_id"]:
                continue
            quando_outra = _quando(outra)
            if quando and quando_outra and abs(quando - quando_outra) > timedelta(hours=HORAS):
                continue
            vetor = self.vetores[link]
            similaridade = sum(v * vetor.get(p, 0.0) for p, v in alvo.items())
            meus, deles = numeros(noticia["titulo"], noticia["resumo"]), self.numeros[link]
            if meus and deles and not meus & deles:
                similaridade *= NUMEROS_DIFERENTES
            saida.append((similaridade, outra))
        saida.sort(key=lambda x: x[0], reverse=True)
        return saida


def _grupo(veiculo, veiculo_id):
    if not veiculo:
        return veiculo_id
    return veiculo.get("grupo") or (veiculo.get("transparencia") or {}).get("dono") or veiculo["id"]


def sinais_da_noticia(noticia, tipos_diferentes=False):
    """Sinais do texto e dos dados da própria notícia: [(descrição, fator)]."""
    titulo, resumo = noticia["titulo"] or "", noticia["resumo"] or ""
    texto = f"{titulo} {resumo}"
    sinais = []
    oficial = FONTE_OFICIAL_NOME.search(texto) or FONTE_OFICIAL_SIGLA.search(texto)
    if oficial:
        sinais.append((f"cita fonte oficial ({oficial.group(0)})", FATOR_FONTE_OFICIAL))
    if _campo(noticia, "autor"):
        sinais.append(("autor identificado", FATOR_AUTOR))
    if tipos_diferentes:
        sinais.append(("confirmada por tipos diferentes de veículo", FATOR_TIPOS_DIFERENTES))
    vaga = ATRIBUICAO_VAGA.search(texto)
    if vaga:
        sinais.append((f"atribuição vaga (“{vaga.group(0)}”)", FATOR_ATRIBUICAO_VAGA))
    alarmes = []
    if "!" in titulo:
        alarmes.append("exclamação no título")
    gritos = [p for p in re.findall(r"\b[A-ZÀ-Ý]{5,}\b", titulo) if p not in CAIXA_ALTA_PERMITIDA]
    if gritos:
        alarmes.append("palavra em caixa alta no título")
    termo = SENSACIONALISMO.search(titulo)
    if termo:
        alarmes.append(f"termo sensacionalista (“{termo.group(0)}”)")
    for alarme in alarmes[:2]:
        sinais.append((alarme, FATOR_SENSACIONALISMO))
    if not _campo(noticia, "publicado_em"):
        sinais.append(("sem data de publicação", FATOR_SEM_DATA))
    return sinais


def _campo(noticia, nome):
    try:
        return noticia[nome]
    except (KeyError, IndexError):
        return None


def ajustar(base, sinais):
    """Atualização bayesiana: as chances da confiança base são multiplicadas pelos fatores dos sinais."""
    if base <= 0:
        return 0.0
    chances = min(base, 0.999) / (1 - min(base, 0.999))
    for _, fator in sinais:
        chances *= fator
    return chances / (1 + chances)


def classificar(noticia, corpus, veiculos_por_id):
    """Rótulo, confiança (0 a 1), motivos, provas e avisos, todos calculados."""
    if OPINIAO_TITULO.search(noticia["titulo"]) or OPINIAO_LINK.search(noticia["link"]):
        return {"rotulo": "opiniao", "confianca": None, "provas": [], "avisos": [],
                "motivos": ["O título ou o endereço indicam texto de opinião; não recebe rótulo de veracidade."]}

    informativas = [p for p in corpus.vetor(noticia) if p not in corpus.comum_demais]
    if len(informativas) < MINIMO_DE_PALAVRAS:
        return {"rotulo": "dados-insuficientes", "confianca": None, "provas": [], "avisos": [],
                "motivos": ["O título e o resumo têm poucas palavras para comparar com outros veículos."]}

    original = veiculos_por_id.get(noticia["veiculo_id"])
    grupo_original = _grupo(original, noticia["veiculo_id"])
    por_grupo, checagens = {}, []
    for similaridade, outra in corpus.parecidas(noticia):
        if similaridade < LIMIAR_FATO:
            break
        veiculo = veiculos_por_id.get(outra["veiculo_id"]) or {}
        checador = outra["uso"] == "checagens" or veiculo.get("tipo") == "checador"
        if checador:
            if similaridade >= LIMIAR_CHECAGEM and CHECAGEM_FALSO.search(outra["titulo"]):
                checagens.append((similaridade, outra, veiculo))
            continue
        grupo = _grupo(veiculo, outra["veiculo_id"])
        if grupo == grupo_original or grupo in por_grupo:
            continue  # o mesmo grupo de mídia conta uma vez só, e o do original não conta
        forca = min(1.0, (similaridade - LIMIAR_FATO) / (SIMILARIDADE_FORTE - LIMIAR_FATO))
        p = PESO_TIPO.get(veiculo.get("tipo"), PESO_PADRAO) * (0.6 + 0.4 * forca)
        if similaridade >= REPRODUCAO:
            p *= FATOR_REPRODUCAO  # texto quase idêntico: mais provável que reproduza, não que confirme
        por_grupo[grupo] = (p, similaridade, outra, veiculo)

    base = 1 - math.prod(1 - p for p, *_ in por_grupo.values())
    tipos = {(v.get("tipo") or "") for _, _, _, v in por_grupo.values()}
    sinais = sinais_da_noticia(noticia, len({t for t in tipos if t}) >= 2)
    confianca = ajustar(base, sinais)
    provas = [{"linha": outra, "veiculo": veiculo.get("nome") or outra["veiculo_id"],
               "explicacao": f"Mesmo fato (similaridade {round(s * 100)}%, peso da confirmação {round(p * 100)}%"
                             + (", texto quase idêntico: provável reprodução" if s >= REPRODUCAO else "") + ")"}
              for p, s, outra, veiculo in sorted(por_grupo.values(), key=lambda x: x[0], reverse=True)]
    conta = (f"Confirmações: {round(base * 100)}% (1 − Π(1 − p) sobre {len(por_grupo)} grupo(s) de mídia "
             f"independente(s)).")
    if sinais and por_grupo:
        conta += (" Sinais da notícia: " + "; ".join(f"{t} (× {str(f).replace('.', ',')})" for t, f in sinais)
                  + f". Confiança final: {round(confianca * 100)}%.")
    if not por_grupo:
        conta = ("Sinais da notícia: " + "; ".join(t for t, _ in sinais) + ".") if sinais else None
    avisos = []
    for s, outra, veiculo in checagens[:1]:
        avisos.append(f"Checagem parecida encontrada ({veiculo.get('nome') or outra['veiculo_id']}, "
                      f"similaridade {round(s * 100)}%): o cálculo não lê o texto para saber se ela desmente esta notícia.")
        provas.append({"linha": outra, "veiculo": veiculo.get("nome") or outra["veiculo_id"],
                       "explicacao": f"Checagem sobre assunto parecido (similaridade {round(s * 100)}%)"})

    if len(por_grupo) >= 2 and confianca >= CONFIANCA_CONFIRMADA and not checagens:
        nomes = ", ".join(p["veiculo"] for p in provas[:len(por_grupo)])
        return {"rotulo": "confirmada", "confianca": confianca, "provas": provas, "avisos": avisos,
                "motivos": [f"{len(por_grupo)} veículos de grupos diferentes publicaram o mesmo fato: {nomes}.", conta]}
    if por_grupo:
        falta = ("falta mais um grupo de mídia independente" if len(por_grupo) < 2
                 else f"a confiança precisa chegar a {round(CONFIANCA_CONFIRMADA * 100)}%")
        motivo = f"{len(por_grupo)} grupo(s) de mídia diferente(s) publicaram o mesmo fato; {falta}."
    else:
        motivo = "Nenhum outro veículo acompanhado publicou este fato até agora."
    return {"rotulo": "em-apuracao", "confianca": confianca, "provas": provas, "avisos": avisos,
            "motivos": [motivo] + ([conta] if conta else [])}
