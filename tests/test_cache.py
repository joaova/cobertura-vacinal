"""Regressão: atualização e substituição do SQLite devem renovar todos os caches."""
import os
import sqlite3

import pytest

import common as c


def criar_banco(caminho, nome, cobertura):
    with sqlite3.connect(caminho) as con:
        con.executescript("""
            CREATE TABLE LOCALIDADE (
                id_localidade INTEGER PRIMARY KEY, cod_ibge TEXT, nome_localidade TEXT,
                tipo_localidade TEXT, sigla_uf TEXT, regiao TEXT);
            CREATE TABLE VACINACAO_ANUAL (
                id_localidade INTEGER, ano INTEGER, cobertura_d1 REAL,
                cobertura_d2 REAL, periodo_parcial INTEGER);
        """)
        con.execute("INSERT INTO LOCALIDADE VALUES (1, '43', ?, 'UF', 'RS', 'Sul')", (nome,))
        con.execute("INSERT INTO VACINACAO_ANUAL VALUES (1, 2025, ?, 80, 0)", (cobertura,))


@pytest.mark.parametrize("substituir", [False, True], ids=["atualizacao", "substituicao_etl"])
def test_cache_renova_consultas_catalogo_e_conexao(tmp_path, monkeypatch, substituir):
    caminho = tmp_path / "dados.db"
    criar_banco(caminho, "Nome anterior", 90)
    monkeypatch.setattr(c.config, "CAMINHO_DB", caminho)
    c.q.clear()
    c.mapa_localidades.clear()
    c._conexao.clear()
    conexoes = []
    try:
        versao_antiga = c.db_versao()
        conexoes.append(c.get_con())
        assert c.dados("cb1_serie_cobertura", cods=["43"]).cobertura_d1.iloc[0] == 90
        assert c.localidades().nome_localidade.iloc[0] == "Nome anterior"
        if substituir:
            novo = tmp_path / "novo.db"
            criar_banco(novo, "Nome renovado", 98)
            # Mantém tamanho e mtime: a troca do arquivo também deve invalidar o cache.
            os.utime(novo, ns=(caminho.stat().st_atime_ns, caminho.stat().st_mtime_ns))
            os.replace(novo, caminho)
        else:
            with sqlite3.connect(caminho) as con:
                con.execute("UPDATE LOCALIDADE SET nome_localidade = 'Nome renovado'")
                con.execute("UPDATE VACINACAO_ANUAL SET cobertura_d1 = 98")
            info = caminho.stat()
            os.utime(caminho, ns=(info.st_atime_ns, versao_antiga[2] + 1_000_000))
        assert c.db_versao() != versao_antiga
        assert c.dados("cb1_serie_cobertura", cods=["43"]).cobertura_d1.iloc[0] == 98
        assert c.localidades().nome_localidade.iloc[0] == "Nome renovado"
        conexoes.append(c.get_con())
        assert conexoes[0] is not conexoes[1]
    finally:
        for con in conexoes:
            con.close()
        c.q.clear()
        c.mapa_localidades.clear()
        c._conexao.clear()
