"""Linha de comando do coletor. Rode na pasta do projeto:

    python -m coletor coletar                 coleta todos os feeds e atualiza dados/noticias.json
    python -m coletor coletar --veiculo g1    coleta só um veículo
    python -m coletor exportar                só regenera dados/noticias.json
    python -m coletor veiculos listar         mostra o cadastro e a situação de cada feed
    python -m coletor veiculos validar        confere o arquivo dados/veiculos.json
    python -m coletor veiculos testar [ID]    baixa e lê os feeds sem gravar nada
    python -m coletor veiculos adicionar ...  cadastra um veículo (veja --help)
    python -m coletor veiculos desativar ID   para de coletar um veículo (ativar ID volta)
"""

import argparse
import sys

from . import banco, cadastro, coleta, exportar
from . import feeds as leitor
from .cadastro import ABRANGENCIAS, TIPOS, UFS, ErroCadastro


def cmd_coletar(args):
    veiculos = cadastro.carregar()
    conexao = banco.abrir()
    print("Coletando notícias…")
    r = coleta.coletar(conexao, veiculos, so_veiculo=args.veiculo, cidades=cadastro.carregar_cidades())
    print(f"\n{r['feeds']} feeds lidos: {r['novas']} notícias novas, {r['sem_mudanca']} sem mudança, {r['erros']} com erro.")
    removidas = coleta.remover_antigas(conexao)
    if removidas:
        print(f"{removidas} notícias com mais de 30 dias apagadas do banco.")
    if not args.sem_exportar:
        _exportar(conexao, veiculos)
    return 1 if r["feeds"] and r["erros"] == r["feeds"] else 0


def cmd_exportar(args):
    _exportar(banco.abrir(), cadastro.carregar())
    return 0


def _exportar(conexao, veiculos):
    contagem = exportar.exportar(conexao, veiculos)
    partes = ", ".join(f"{k}: {n}" for k, n in contagem.items())
    print(f"dados/noticias.json atualizado ({partes}).")


def cmd_listar(args):
    veiculos = cadastro.carregar()
    conexao = banco.abrir()
    totais = dict(conexao.execute("SELECT veiculo_id, COUNT(*) FROM noticias GROUP BY veiculo_id").fetchall())
    for v in veiculos:
        situacao = "ativo" if v.get("ativo", True) else "DESATIVADO"
        lugar = v.get("cidade") or v.get("uf") or ""
        print(f"{v['id']:<20} {v['nome']:<24} {v['abrangencia']:<13} {lugar:<16} {situacao:<11} {totais.get(v['id'], 0):>5} notícias")
        for f in v["feeds"]:
            estado = conexao.execute(
                "SELECT ultimo_status, ultimo_erro, falhas_seguidas, ultima_coleta FROM feeds WHERE url = ?", (f["url"],)
            ).fetchone()
            if not estado:
                texto = "nunca coletado"
            elif estado["ultimo_status"] == "ok":
                texto = f"ok em {estado['ultima_coleta']}"
            else:
                texto = f"ERRO ({estado['falhas_seguidas']}x seguidas): {estado['ultimo_erro']}"
            uso = " [checagens]" if f.get("uso") == "checagens" else ""
            print(f"    {f['url']}{uso}\n      {texto}")
    return 0


def cmd_validar(args):
    cadastro.carregar()
    print("Cadastro válido.")
    return 0


def _testar_feed(url):
    try:
        itens = leitor.ler(leitor.baixar(url).conteudo)
    except leitor.ErroFeed as e:
        print(f"    ERRO: {e}")
        return False
    if not itens:
        print("    ERRO: o feed respondeu, mas sem nenhuma notícia")
        return False
    print(f"    ok, {len(itens)} notícias. Mais recente: {itens[0]['titulo'][:70]}")
    return True


def cmd_testar(args):
    veiculos = cadastro.carregar()
    if args.id:
        veiculos = [cadastro.buscar(veiculos, args.id)]
    falhas = 0
    for v in veiculos:
        print(v["nome"])
        for f in v["feeds"]:
            print(f"  {f['url']}")
            falhas += not _testar_feed(f["url"])
    return 1 if falhas else 0


def cmd_adicionar(args):
    veiculos = cadastro.carregar()
    if any(v["id"] == args.id for v in veiculos):
        raise ErroCadastro(f"Já existe um veículo com o id {args.id}.")
    feeds = [{"url": url} for url in args.feed]
    if args.checagens:
        for f in feeds:
            f["uso"] = "checagens"
    novo = cadastro.novo_veiculo(
        args.id, args.nome, args.site, args.tipo, args.abrangencia, feeds,
        grupo=args.grupo, uf=args.uf, cidade=args.cidade,
    )
    erros = cadastro.validar([novo])
    if erros:
        raise ErroCadastro("Não cadastrado:\n- " + "\n- ".join(erros))
    if not args.sem_testar:
        print("Testando os feeds antes de cadastrar…")
        if not all(_testar_feed(f["url"]) for f in feeds):
            print("Não cadastrado: corrija o feed ou use --sem-testar.")
            return 1
    cadastro.gravar(veiculos + [novo])
    print(f"{args.nome} cadastrado. Complete dono, CNPJ e os demais dados de transparência em dados/veiculos.json.")
    return 0


def cmd_ativar(args, ativo):
    veiculos = cadastro.carregar()
    cadastro.buscar(veiculos, args.id)["ativo"] = ativo
    cadastro.gravar(veiculos)
    print(f"{args.id} {'ativado' if ativo else 'desativado'}.")
    return 0


def montar_parser():
    p = argparse.ArgumentParser(prog="python -m coletor", description="Coletor de notícias do Farol.")
    sub = p.add_subparsers(dest="comando", required=True)

    c = sub.add_parser("coletar", help="coleta os feeds e atualiza dados/noticias.json")
    c.add_argument("--veiculo", help="coleta só o veículo com este id")
    c.add_argument("--sem-exportar", action="store_true", help="não atualiza dados/noticias.json")
    c.set_defaults(func=cmd_coletar)

    sub.add_parser("exportar", help="regenera dados/noticias.json").set_defaults(func=cmd_exportar)

    v = sub.add_parser("veiculos", help="cadastro de veículos").add_subparsers(dest="acao", required=True)
    v.add_parser("listar", help="mostra o cadastro").set_defaults(func=cmd_listar)
    v.add_parser("validar", help="confere dados/veiculos.json").set_defaults(func=cmd_validar)

    t = v.add_parser("testar", help="baixa e lê os feeds sem gravar")
    t.add_argument("id", nargs="?", help="id de um veículo (sem id, testa todos)")
    t.set_defaults(func=cmd_testar)

    a = v.add_parser("adicionar", help="cadastra um veículo")
    a.add_argument("--id", required=True, help="identificador curto, ex.: diario-de-pernambuco")
    a.add_argument("--nome", required=True)
    a.add_argument("--site", required=True)
    a.add_argument("--tipo", required=True, choices=sorted(TIPOS))
    a.add_argument("--abrangencia", required=True, choices=list(ABRANGENCIAS))
    a.add_argument("--feed", required=True, action="append", help="endereço do feed RSS/Atom (pode repetir)")
    a.add_argument("--grupo", help="grupo empresarial dono do veículo")
    a.add_argument("--uf", choices=sorted(UFS))
    a.add_argument("--cidade")
    a.add_argument("--checagens", action="store_true", help="o feed publica checagens de fatos")
    a.add_argument("--sem-testar", action="store_true", help="cadastra sem testar o feed")
    a.set_defaults(func=cmd_adicionar)

    for nome, ativo in (("ativar", True), ("desativar", False)):
        x = v.add_parser(nome, help=f"{nome} a coleta de um veículo")
        x.add_argument("id")
        x.set_defaults(func=lambda args, ativo=ativo: cmd_ativar(args, ativo))
    return p


def main(argv=None):
    args = montar_parser().parse_args(argv)
    try:
        return args.func(args)
    except ErroCadastro as e:
        print(e, file=sys.stderr)
        return 2
    except FileNotFoundError as e:
        print(f"Arquivo não encontrado: {e.filename}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
