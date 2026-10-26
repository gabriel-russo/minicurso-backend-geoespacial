# Mapa Colaborativo — Minicurso de Geoinformática

Backend em **Python + FastAPI** para um mapa colaborativo em tempo real.
As geometrias são gravadas em um banco **SQLite + SpatiaLite** e sincronizadas
entre os navegadores por **WebSocket**.

O frontend (Leaflet + Leaflet.draw) já está pronto em `static/`: o foco do
minicurso é o backend, o banco espacial e a comunicação em tempo real.

## O que o sistema faz

- Desenha **pontos, linhas e polígonos** no mapa.
- Grava cada geometria em um banco espacial com SRID 4326.
- Sincroniza criação e exclusão entre todos os navegadores conectados.
- Envia um *snapshot* do mapa para quem entra depois.
- Mantém os dados após reiniciar o servidor.
- Expõe a API no Swagger em `/docs`.

## Arquitetura

```
Navegador (Leaflet + Leaflet.draw, JS puro)
   │
   │  HTTP  GET/POST/DELETE /api/features   (carregar, criar, excluir)
   │  WS    /ws                             (snapshot + eventos ao vivo)
   ▼
FastAPI (uvicorn, 1 worker)
   │
   │  sqlite3 + extensão mod_spatialite
   ▼
data/mapa.sqlite
   └── features(id, geom, criado_em) + índice espacial R-tree
```

Fluxo de uma criação:

1. O aluno desenha no mapa.
2. O JavaScript envia `POST /api/features` com um GeoJSON.
3. O FastAPI valida com Pydantic + Shapely e grava com `GeomFromText(wkt, 4326)`.
4. O servidor responde `201` e faz broadcast de `feature_added`.
5. Todos os navegadores (inclusive o autor) desenham a nova geometria.

## Estrutura do projeto

```
.
├── schema.sql               # estrutura declarativa do banco espacial
├── main.py                  # rotas REST, WebSocket e arquivos estáticos
├── db.py                    # conexão SpatiaLite e consultas SQL
├── pyproject.toml           # dependências gerenciadas pelo uv
├── uv.lock
├── requirements.txt         # alternativa para quem usa pip
├── README.md
├── static/
│   ├── index.html
│   ├── app.js
│   ├── style.css
│   └── vendor/              # Leaflet e Leaflet.draw locais (funciona sem CDN)
├── scripts/
│   ├── check_spatialite.py  # teste rápido do ambiente
│   └── consultas.sql        # consultas espaciais para a aula
└── data/
    └── mapa.sqlite          # gerado pelo schema.sql (não versionado)
```

## Requisitos

- Python 3.11 ou superior.
- [uv](https://docs.astral.sh/uv/) para gerenciar o projeto.
- Extensão SpatiaLite para Python:
  `libsqlite3-mod-spatialite`.
- CLI do SpatiaLite para criar e inspecionar o banco:
  `spatialite-bin`.

### Ubuntu / WSL

```bash
sudo apt update
sudo apt install -y libsqlite3-mod-spatialite spatialite-bin
```

Se o pacote `spatialite-bin` não for encontrado:

```bash
sudo add-apt-repository universe
sudo apt update
sudo apt install -y spatialite-bin
```

### uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# feche e abra o terminal, ou:
source "$HOME/.local/bin/env"
```

## 1. Criar o banco espacial (CLI)

O banco é criado **fora da aplicação**, com o arquivo `schema.sql`:

```bash
mkdir -p data
spatialite data/mapa.sqlite < schema.sql
```

> Em um banco novo, o CLI pode exibir
> `the SPATIAL_REF_SYS table already contains some row(s)`.
> É apenas um aviso da inicialização automática dos metadados espaciais pelo
> `spatialite`; o banco é criado corretamente e o aviso pode ser ignorado.

Confira a coluna e o índice espacial:

```bash
spatialite data/mapa.sqlite \
  "SELECT f_table_name, f_geometry_column, srid FROM geometry_columns
    WHERE f_table_name = 'features';"

spatialite data/mapa.sqlite \
  "SELECT CheckSpatialIndex('features', 'geom');"
```

Saída esperada:

```
features|geom|4326
1
```

O `1` confirma que o índice R-tree está ativo.

### Recriar o banco do zero

O `schema.sql` deve ser executado **somente em um banco novo** (a coluna `geom`
já existiria em um banco antigo). Para resetar:

```bash
rm -f data/mapa.sqlite data/mapa.sqlite-wal data/mapa.sqlite-shm
spatialite data/mapa.sqlite < schema.sql
```

### Inspecionar o banco

```bash
spatialite data/mapa.sqlite ".tables"
spatialite data/mapa.sqlite "SELECT COUNT(*) FROM features;"
```

## 2. Instalar dependências Python

```bash
uv sync
```

Isso cria/atualiza o `.venv` e instala as versões registradas no `uv.lock`.
Não é necessário ativar o ambiente: use `uv run ...`.

## 3. Rodar

```bash
uv run python scripts/check_spatialite.py
uv run uvicorn main:app --reload
```

Acesse:

- Aplicação: <http://localhost:8000>
- Swagger: <http://localhost:8000/docs>

Para testar com celulares na mesma rede:

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Use `http://IP-DA-MAQUINA:8000` nos outros dispositivos. Os *tiles* do mapa vêm
do OpenStreetMap e precisam de internet; sem rede, o mapa fica cinza, mas o
desenho e a sincronização continuam funcionando.

## 4. Como usar

1. Abra duas abas em `http://localhost:8000`.
2. Use as ferramentas no canto superior esquerdo:
   - marcador → **ponto**;
   - linha → **LineString**;
   - polígono → **Polygon**.
3. Desenhe em uma aba e observe a geometria aparecer na outra.
4. Clique em uma geometria para ver o popup e excluí-la.
5. Reinicie o servidor: as geometrias continuam no banco.

## API

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/features` | Todas as geometrias como `FeatureCollection` |
| `POST` | `/api/features` | Cria uma geometria a partir de um GeoJSON Feature |
| `DELETE` | `/api/features/{id}` | Exclui uma geometria (`204` ou `404`) |
| `WS` | `/ws` | Snapshot inicial + eventos em tempo real |
| `GET` | `/docs` | Documentação interativa (Swagger) |

### Exemplo de POST

```bash
curl -X POST http://localhost:8000/api/features \
  -H "Content-Type: application/json" \
  -d '{
    "type": "Feature",
    "geometry": { "type": "Point", "coordinates": [-63.9039, -8.7612] },
    "properties": {}
  }'
```

Resposta (`201`):

```json
{
  "type": "Feature",
  "id": 1,
  "geometry": { "type": "Point", "coordinates": [-63.9039, -8.7612] },
  "properties": { "id": 1, "criado_em": "2026-10-26 20:42:03" }
}
```

Tipos aceitos: `Point`, `LineString` e `Polygon`. Geometrias inválidas
(por exemplo, polígono com auto-interseção) retornam `422` com uma mensagem.

O campo `properties` é aceito no POST, mas o backend persiste apenas `id` e
`criado_em`. As propriedades GeoJSON são um bom exercício de extensão.

### Mensagens do WebSocket

Ao conectar, o servidor envia o estado atual:

```json
{ "type": "snapshot", "features": [ ... ] }
```

Depois, transmite os eventos para todos:

```json
{ "type": "feature_added", "feature": { ... } }
{ "type": "feature_removed", "id": 12 }
```

O canal é unidirecional na prática: o cliente **não** envia comandos pelo
WebSocket; as escritas passam pelo REST. Isso mantém um único caminho de
validação e persistência.

## Banco de dados

O `schema.sql` executa:

```sql
PRAGMA journal_mode = WAL;

SELECT InitSpatialMetadata(1);   -- com guarda para não repetir

CREATE TABLE features (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

SELECT AddGeometryColumn('features', 'geom', 4326, 'GEOMETRY', 'XY');
SELECT CreateSpatialIndex('features', 'geom');
```

- `InitSpatialMetadata` cria `spatial_ref_sys`, `geometry_columns` e demais
  tabelas de metadados.
- `AddGeometryColumn` cria a coluna `geom` e registra o SRID 4326.
- `GEOMETRY` aceita ponto, linha e polígono na mesma tabela.
- `CreateSpatialIndex` cria o índice R-tree.
- `WAL` permite ler o banco com a API rodando.

O banco fica em `data/mapa.sqlite` e **não** é versionado.

## Consultas espaciais

Com o servidor rodando e algumas geometrias no mapa:

```bash
spatialite data/mapa.sqlite < scripts/consultas.sql
```

O script calcula:

- quantidade por tipo de geometria;
- área dos polígonos em km²;
- comprimento das linhas em km;
- interseção com uma *bounding box*;
- distância até a UNIR, em metros.

Os cálculos usam o SRID **31980** (SIRGAS 2000 / UTM zona 20S), adequado para
Rondônia. Para outra região, ajuste o SRID no arquivo. O SRID 4326 usa graus e
**não** deve ser usado diretamente para calcular metros.

## Roteiro sugerido (4 horas)

| Tempo | Bloco | Conteúdo |
|---|---|---|
| 0:00–0:10 | Abertura + demo | Aplicação completa em duas abas |
| 0:10–1:05 | Teoria | Geometrias, GeoJSON/WKT, CRS/SRID, banco espacial, R-tree, `ST_*`, WebGIS, REST × WebSocket |
| 1:05–1:25 | Setup + banco | Dependências, `schema.sql` via CLI, verificação |
| 1:25–2:10 | Backend I | Conexão SpatiaLite, `GET /api/features`, Swagger |
| 2:10–2:25 | Intervalo | |
| 2:25–3:15 | Backend II | Shapely, POST, DELETE, WebSocket, snapshot e broadcast |
| 3:15–3:30 | Frontend | Como o `app.js` consome REST + WS; teste em duas abas |
| 3:30–3:45 | SQL espacial | `scripts/consultas.sql` ao vivo no terminal |
| 3:45–4:00 | Fechamento | Limitações, PostGIS, desafios, Q&A |

## Versões do repositório

- `main`: aplicação completa, pronta para rodar e para a demo inicial.
- `sala-de-aula`: esqueleto com pontos `TODO` para a turma completar durante o
  minicurso.

```bash
git checkout sala-de-aula   # começar a aula
git checkout main           # consultar a solução
```

## Limitações e próximos passos

- **Um worker apenas**: o estado dos WebSockets fica em memória. Não use
  `--workers 2` sem trocar o broadcast por um Pub/Sub (Redis, por exemplo).
- **Sem autenticação**: qualquer pessoa com acesso ao endereço pode criar e
  excluir geometrias.
- **Sem edição**: o escopo é criar, listar e excluir. Editar seria um `PUT`.
- **SQLite**: excelente para a sala de aula; para produção concorrente,
  considere PostGIS.
- **`properties`**: não são persistidas; apenas `id` e `criado_em`.
- **Projeções**: área/distância precisam de um SRID projetado (ex.: 31980).
- Ideias de extensão: editar geometria, exportar GeoJSON, filtrar por *bbox*,
  salas separadas, autenticação, PostGIS e GeoAlchemy2.

## Problemas comuns

**`sqlite3.OperationalError: no such table: features`**
O banco não foi criado ou está vazio. Rode:

```bash
spatialite data/mapa.sqlite < schema.sql
```

**`RuntimeError: Banco não encontrado`**
O arquivo `data/mapa.sqlite` não existe. Crie-o com o comando acima.

**`AttributeError: 'sqlite3.Connection' object has no attribute ...` / extensão não carrega**
Falta a biblioteca do sistema:

```bash
sudo apt install -y libsqlite3-mod-spatialite
```

**`spatialite: command not found`**

```bash
sudo apt install -y spatialite-bin
```

**`database is locked`**
Confirme que o banco foi criado com WAL e que existe apenas um worker do
uvicorn. Evite transações longas.

**Mapa cinza**
Os *tiles* do OpenStreetMap não carregaram (sem internet ou bloqueio de rede).
As geometrias e o WebSocket continuam funcionando.

**Status “reconectando…”**
O servidor foi reiniciado ou caiu. O frontend tenta reconectar a cada 2
segundos. Verifique o terminal do `uvicorn`.

**Porta 8000 ocupada**

```bash
uv run uvicorn main:app --reload --port 8001
```
