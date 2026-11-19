-- Esquema relacional (3FN) do banco projeto_sarampo_vacina.db
-- Baseado no modelo do artigo anteprojeto (Figura 1 / Tabela 2), com extensões
-- marcadas como [EXT] para rastreabilidade das fontes e sinalização de limitações.

PRAGMA foreign_keys = ON;

CREATE TABLE LOCALIDADE (
    id_localidade   INTEGER PRIMARY KEY AUTOINCREMENT,
    cod_ibge        TEXT    NOT NULL UNIQUE,   -- '00' Brasil | 2 dígitos UF | 6 dígitos município
    nome_localidade TEXT    NOT NULL,
    tipo_localidade TEXT    NOT NULL CHECK (tipo_localidade IN ('PAIS', 'UF', 'MUNICIPIO')),
    sigla_uf        TEXT    NOT NULL,          -- 'BR' para o país
    regiao          TEXT                       -- [EXT] região do país (filtros da interface)
);

CREATE TABLE VACINACAO_ANUAL (
    id_vac_anual       INTEGER PRIMARY KEY AUTOINCREMENT,
    id_localidade      INTEGER NOT NULL REFERENCES LOCALIDADE (id_localidade),
    ano                INTEGER NOT NULL CHECK (ano BETWEEN 2015 AND 2026),
    cobertura_d1       REAL    CHECK (cobertura_d1 IS NULL OR cobertura_d1 >= 0.0),
    cobertura_d2       REAL    CHECK (cobertura_d2 IS NULL OR cobertura_d2 >= 0.0),
    -- [EXT] Método alternativo (2023-2026): soma(doses)/soma(população-alvo) em vez da
    -- média simples das coberturas mensais. Em 2015-2022 é igual a cobertura_d*.
    cobertura_d1_pond  REAL,
    cobertura_d2_pond  REAL,
    doses_d1           INTEGER,                -- NULL de 2015 a 2022 (fonte só traz a taxa)
    doses_d2           INTEGER,
    -- [EXT] D1 e D2 têm denominadores distintos nas planilhas do SEIDIGI; por isso
    -- o artigo ("populacao_alvo") foi desdobrado em dois atributos.
    populacao_alvo_d1  INTEGER,
    populacao_alvo_d2  INTEGER,
    atingiu_meta_d1    INTEGER CHECK (atingiu_meta_d1 IN (0, 1)),
    atingiu_meta_d2    INTEGER CHECK (atingiu_meta_d2 IN (0, 1)),
    meses_cobertos     INTEGER NOT NULL DEFAULT 12,  -- [EXT] meses com dado no ano
    periodo_parcial    INTEGER NOT NULL DEFAULT 0 CHECK (periodo_parcial IN (0, 1)),  -- [EXT]
    fonte              TEXT    NOT NULL,       -- [EXT] 'TABNET/SI-PNI' ou 'SEIDIGI/DEMAS'
    UNIQUE (id_localidade, ano)
);

CREATE TABLE VACINACAO_MENSAL (
    id_vac_mensal   INTEGER PRIMARY KEY AUTOINCREMENT,
    id_localidade   INTEGER NOT NULL REFERENCES LOCALIDADE (id_localidade),
    ano             INTEGER NOT NULL CHECK (ano BETWEEN 2023 AND 2026),
    mes             INTEGER NOT NULL CHECK (mes BETWEEN 1 AND 12),
    dose            TEXT    NOT NULL CHECK (dose IN ('D1', 'D2')),
    doses_aplicadas INTEGER NOT NULL DEFAULT 0,  -- todas as doses aplicadas no mês (qualquer idade)
    cobertura_mensal REAL,                       -- [EXT] cobertura (%) do mês segundo o painel SEIDIGI
    doses_pop_alvo  INTEGER,                     -- [EXT] doses na população-alvo (numerador da cobertura)
    pop_alvo        INTEGER,                     -- [EXT] população-alvo do mês (denominador)
    UNIQUE (id_localidade, ano, mes, dose)
);

CREATE TABLE NOTIFICACAO_SARAMPO (
    id_notificacao         INTEGER PRIMARY KEY AUTOINCREMENT,
    id_localidade          INTEGER NOT NULL REFERENCES LOCALIDADE (id_localidade),
    ano                    INTEGER NOT NULL CHECK (ano BETWEEN 2015 AND 2026),  -- ano de INÍCIO DO EXANTEMA
    casos_inicio_exantema  INTEGER NOT NULL DEFAULT 0,
    populacao_ibge         INTEGER NOT NULL,
    incidencia_100k        REAL    NOT NULL DEFAULT 0.0,
    populacao_estimada     INTEGER NOT NULL DEFAULT 0 CHECK (populacao_estimada IN (0, 1)),  -- [EXT] 1 = população replicada de 2025
    periodo_parcial        INTEGER NOT NULL DEFAULT 0 CHECK (periodo_parcial IN (0, 1)),     -- [EXT] ano ainda em curso
    UNIQUE (id_localidade, ano)
);

-- [EXT] Casos por ANO DE NOTIFICAÇÃO (cortes preliminares not_sarampo_*.csv).
-- Permite comparar com o critério "ano de início do exantema" e discutir atraso de registro.
CREATE TABLE NOTIFICACAO_ANO_NOTIF (
    id_localidade  INTEGER NOT NULL REFERENCES LOCALIDADE (id_localidade),
    ano_notificacao INTEGER NOT NULL,
    casos_notificados INTEGER NOT NULL,
    PRIMARY KEY (id_localidade, ano_notificacao)
);

-- [EXT] Manifesto dos arquivos lidos (reprodutibilidade e data de extração).
CREATE TABLE FONTE_ARQUIVO (
    id_arquivo      INTEGER PRIMARY KEY AUTOINCREMENT,
    fonte           TEXT    NOT NULL,   -- TABNET/SI-PNI | SEIDIGI/DEMAS | SINAN | IBGE
    arquivo         TEXT    NOT NULL UNIQUE,
    conteudo        TEXT    NOT NULL,
    linhas_lidas    INTEGER NOT NULL,
    data_extracao   TEXT,               -- quando a própria fonte informa (ISO 8601)
    modificado_em   TEXT    NOT NULL,   -- data de modificação do arquivo local
    sha256          TEXT    NOT NULL
);

-- [EXT] Ocorrências de qualidade registradas pelo ETL (linhas descartadas, colunas ignoradas...).
CREATE TABLE LOG_QUALIDADE (
    id_log     INTEGER PRIMARY KEY AUTOINCREMENT,
    etapa      TEXT NOT NULL,
    descricao  TEXT NOT NULL,
    valor      REAL
);

CREATE INDEX idx_vac_anual_ano  ON VACINACAO_ANUAL (ano);
CREATE INDEX idx_vac_mensal_loc ON VACINACAO_MENSAL (id_localidade, ano, mes);
CREATE INDEX idx_notif_ano      ON NOTIFICACAO_SARAMPO (ano);
CREATE INDEX idx_loc_tipo       ON LOCALIDADE (tipo_localidade, sigla_uf);

-- [EXT] Visão que cruza cobertura anual, casos por início do exantema e incidência.
CREATE VIEW VW_CRUZAMENTO AS
SELECT l.id_localidade, l.cod_ibge, l.nome_localidade, l.tipo_localidade, l.sigla_uf, l.regiao,
       v.ano,
       v.cobertura_d1, v.cobertura_d2, v.cobertura_d1_pond, v.cobertura_d2_pond, v.doses_d1, v.doses_d2,
       v.populacao_alvo_d1, v.populacao_alvo_d2,
       v.atingiu_meta_d1, v.atingiu_meta_d2,
       v.periodo_parcial AS vac_parcial,
       n.casos_inicio_exantema AS casos, n.populacao_ibge, n.incidencia_100k,
       n.populacao_estimada, n.periodo_parcial AS notif_parcial
FROM LOCALIDADE l
JOIN VACINACAO_ANUAL v      ON v.id_localidade = l.id_localidade
LEFT JOIN NOTIFICACAO_SARAMPO n ON n.id_localidade = l.id_localidade AND n.ano = v.ano;
