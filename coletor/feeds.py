"""Baixa e lê feeds RSS e Atom usando só a biblioteca padrão do Python.

Guardamos título, link, um resumo curto e a data. O texto completo das notícias
não é copiado: o leitor sempre vai ao site do veículo para ler a matéria.
"""

import email.utils
import html
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone

ATOM = "{http://www.w3.org/2005/Atom}"
CONTENT = "{http://purl.org/rss/1.0/modules/content/}"
DC = "{http://purl.org/dc/elements/1.1/}"
MEDIA = "{http://search.yahoo.com/mrss/}"

AGENTE = "OFarolColetor/0.1 (agregador de noticias em teste)"
LIMITE_BYTES = 5_000_000
TAMANHO_RESUMO = 280
TAGS = re.compile(r"<[^>]+>")
REDIRECIONAMENTO = re.compile(r"\*(https?://.+)$")
IMG = re.compile(r"""<img\b[^>]*?\bsrc\s*=\s*["']([^"']+)["']""", re.IGNORECASE)
EXTENSAO_IMAGEM = re.compile(r"\.(jpe?g|png|webp|gif|avif)(\?|$)", re.IGNORECASE)


class ErroFeed(Exception):
    pass


@dataclass
class Resposta:
    status: int
    conteudo: bytes
    etag: str | None
    modificado: str | None


def _contexto_tls():
    contexto = ssl.create_default_context()
    # Antivírus que inspecionam HTTPS (como o AVG) usam um certificado que o modo estrito
    # do Python 3.13+ recusa. A cadeia de certificados continua sendo verificada.
    contexto.verify_flags &= ~ssl.VERIFY_X509_STRICT
    return contexto


_TLS = _contexto_tls()


def baixar(url, etag=None, modificado=None, tempo_limite=20):
    """Baixa o feed. Com etag/modificado, o site pode responder 304 (nada mudou), o que poupa banda."""
    cabecalhos = {
        "User-Agent": AGENTE,
        "Accept": "application/rss+xml, application/atom+xml, application/xml;q=0.9, */*;q=0.5",
    }
    if etag:
        cabecalhos["If-None-Match"] = etag
    if modificado:
        cabecalhos["If-Modified-Since"] = modificado
    pedido = urllib.request.Request(url, headers=cabecalhos)
    try:
        with urllib.request.urlopen(pedido, timeout=tempo_limite, context=_TLS) as r:
            conteudo = r.read(LIMITE_BYTES + 1)
            if len(conteudo) > LIMITE_BYTES:
                raise ErroFeed("o feed passa de 5 MB")
            return Resposta(r.status, conteudo, r.headers.get("ETag"), r.headers.get("Last-Modified"))
    except urllib.error.HTTPError as e:
        if e.code == 304:
            return Resposta(304, b"", etag, modificado)
        raise ErroFeed(f"o site respondeu {e.code}") from e
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise ErroFeed(f"falha de conexão: {getattr(e, 'reason', e)}") from e


# Prefixos que os feeds usam sem declarar, ou que somem quando lemos item por item
PREFIXOS = {"content": CONTENT[1:-1], "dc": DC[1:-1], "media": MEDIA[1:-1], "atom": ATOM[1:-1],
            "wfw": "http://wellformedweb.org/CommentAPI/", "slash": "http://purl.org/rss/1.0/modules/slash/",
            "sy": "http://purl.org/rss/1.0/modules/syndication/"}
ENTIDADE = re.compile(rb"&(?!(?:amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)([A-Za-z][A-Za-z0-9]*;)?")
ITEM = re.compile(rb"<item\b.*?</item>", re.DOTALL)


def _consertar(conteudo):
    """Defeitos comuns de feeds de sites brasileiros: espaço antes do <?xml, entidades do HTML (&ocirc;)
    e & solto no texto."""
    conteudo = conteudo.lstrip(b"\xef\xbb\xbf \t\r\n")

    def entidade(m):
        if m.group(1):
            letra = html.unescape("&" + m.group(1).decode("ascii"))
            if letra != "&" + m.group(1).decode("ascii"):
                return "".join(f"&#{ord(c)};" for c in letra).encode("ascii")
        return b"&amp;" + (m.group(1) or b"")
    return ENTIDADE.sub(entidade, conteudo)


def _item_por_item(conteudo):
    """Último recurso: lê cada <item> sozinho e descarta só os que estão quebrados."""
    declaracoes = " ".join(f'xmlns:{p}="{u}"' for p, u in PREFIXOS.items())
    itens = []
    for bloco in ITEM.findall(conteudo):
        try:
            itens.append(ET.fromstring(f"<rss {declaracoes}>".encode() + bloco + b"</rss>").find("item"))
        except ET.ParseError:
            continue
    return itens


def ler(conteudo):
    """Transforma o XML do feed em uma lista de notícias."""
    try:
        raiz = ET.fromstring(conteudo)
    except ET.ParseError as e:
        consertado = _consertar(conteudo)
        try:
            raiz = ET.fromstring(consertado)
        except ET.ParseError:
            itens = [i for i in (_item_rss(x) for x in _item_por_item(consertado)) if i]
            if not itens:
                raise ErroFeed(f"o feed não é um XML válido ({e})") from e
            return itens
    if raiz.tag == ATOM + "feed":
        itens = (_item_atom(e) for e in raiz.iter(ATOM + "entry"))
    else:
        itens = (_item_rss(e) for e in raiz.iter("item"))
    return [i for i in itens if i]


def _item_rss(e):
    titulo = limpar(e.findtext("title"))
    link = normalizar_link(e.findtext("link"))
    if not titulo or not link:
        return None
    return {
        "titulo": titulo,
        "link": link,
        "guid": (e.findtext("guid") or link).strip(),
        "resumo": resumir(e.findtext("description") or e.findtext(CONTENT + "encoded")),
        "autor": limpar(e.findtext(DC + "creator") or e.findtext("author")) or None,
        "publicado_em": data_iso(e.findtext("pubDate") or e.findtext(DC + "date")),
        "imagem": imagem_do_item(e, e.findtext(CONTENT + "encoded"), e.findtext("description")),
    }


def _item_atom(e):
    titulo = limpar(e.findtext(ATOM + "title"))
    link = ""
    for elo in e.findall(ATOM + "link"):
        if elo.get("rel", "alternate") == "alternate" and elo.get("href"):
            link = normalizar_link(elo.get("href"))
            break
    if not titulo or not link:
        return None
    return {
        "titulo": titulo,
        "link": link,
        "guid": (e.findtext(ATOM + "id") or link).strip(),
        "resumo": resumir(e.findtext(ATOM + "summary") or e.findtext(ATOM + "content")),
        "autor": limpar(e.findtext(f"{ATOM}author/{ATOM}name")) or None,
        "publicado_em": data_iso(e.findtext(ATOM + "published") or e.findtext(ATOM + "updated")),
        "imagem": imagem_do_item(e, e.findtext(ATOM + "content"), e.findtext(ATOM + "summary")),
    }


def imagem_do_item(e, *textos):
    """A foto que o veículo anexou à notícia: media:content, media:thumbnail, enclosure ou o primeiro <img>
    do texto. Só endereços web; http vira https, porque o site é servido em https."""
    candidatos = []
    for m in list(e.iter(MEDIA + "content")) + list(e.iter(MEDIA + "thumbnail")):
        tipo = (m.get("type") or "") + (m.get("medium") or "")
        if m.tag == MEDIA + "thumbnail" or "image" in tipo or EXTENSAO_IMAGEM.search(m.get("url") or ""):
            candidatos.append(m.get("url"))
    for anexo in e.findall("enclosure") + [l for l in e.findall(ATOM + "link") if l.get("rel") == "enclosure"]:
        if (anexo.get("type") or "").startswith("image") or EXTENSAO_IMAGEM.search(anexo.get("url") or anexo.get("href") or ""):
            candidatos.append(anexo.get("url") or anexo.get("href"))
    for texto in textos:
        achado = IMG.search(html.unescape(texto or ""))
        if achado:
            candidatos.append(achado.group(1))
    for url in candidatos:
        url = html.unescape((url or "").strip())
        if url.startswith("//"):
            url = "https:" + url
        if url.startswith("http://"):
            url = "https://" + url[7:]
        if url.startswith("https://") and len(url) < 1000:
            return url
    return None


def normalizar_link(link):
    """Tira redirecionadores (ex.: redir.folha.com.br/...*https://...) e parâmetros de rastreamento utm_."""
    link = (link or "").strip()
    achado = REDIRECIONAMENTO.search(link)
    if achado:
        link = achado.group(1)
    partes = urllib.parse.urlsplit(link)
    if partes.query:
        consulta = [(k, v) for k, v in urllib.parse.parse_qsl(partes.query, keep_blank_values=True) if not k.startswith("utm_")]
        link = urllib.parse.urlunsplit(partes._replace(query=urllib.parse.urlencode(consulta)))
    return link


def limpar(texto):
    """Tira marcação HTML (inclusive a que vem escapada, como &lt;p&gt;) e espaços sobrando."""
    if not texto:
        return ""
    texto = html.unescape(TAGS.sub(" ", html.unescape(texto)))
    texto = " ".join(texto.split())
    return re.sub(r"\s+([),.;:!?])", r"\1", re.sub(r"\(\s+", "(", texto))


def resumir(texto, limite=TAMANHO_RESUMO):
    texto = limpar(texto)
    if len(texto) <= limite:
        return texto
    corte = texto[:limite].rsplit(" ", 1)[0]
    return corte.rstrip(".,;:–- ") + "…"


def data_iso(texto):
    """Converte datas de RSS (RFC 822) ou Atom (ISO 8601) para ISO em UTC."""
    if not texto:
        return None
    texto = texto.strip()
    try:
        data = email.utils.parsedate_to_datetime(texto)
    except (TypeError, ValueError, IndexError):
        try:
            data = datetime.fromisoformat(texto.replace("Z", "+00:00"))
        except ValueError:
            return None
    if data.tzinfo is None:
        data = data.replace(tzinfo=timezone.utc)
    return data.astimezone(timezone.utc).isoformat(timespec="seconds")
