# talent_graph 詳細設計図

## 1. 文書概要

### 1.1 文書の目的

本書は、`talent_graph` プロジェクトの詳細設計を定義するための文書である。  
対象は、**卓越した人材を、知識グラフ・埋め込み・ランキング・説明生成を用いて発見する探索基盤**であり、初期ユースケースは **Talent Discovery** に絞る。

本書では以下を定義する。

- システム全体アーキテクチャ
- コンポーネント構成
- データモデル
- グラフスキーマ
- ETL / ingestion 設計
- 埋め込み・ランキング・異常値検出
- API設計
- UI/UX設計
- バッチ / 更新設計
- 非機能要件
- セキュリティ / 法務 / 運用
- MVPスコープと将来拡張

---

## 2. システム目的

`talent_graph` は、以下の問いに答えるためのシステムである。

1. あるテーマ・人物・論文・repoに関連する有望人材は誰か  
2. まだ有名ではないが、卓越の兆候を持つ人物は誰か  
3. その人物がなぜ重要かを、証拠とともに説明できるか  
4. 1人を起点に、関連人物を芋づる式に探索できるか  
5. 人間の手探索に比べて、探索速度と発見品質を改善できるか

---

## 3. 対象ユースケース

### 3.1 MVP対象

#### Talent Discovery
- CTO / CEO / Founder室が、特定テーマの卓越人材を探す
- 採用市場に出ていない候補を深掘りする
- 社内向けに候補者ブリーフを作る

### 3.2 想定入力

- 技術キーワード（例: multimodal dialogue, RLHF, computer vision for cooking）
- 人物名
- 論文タイトル
- GitHub repository
- 組織名

### 3.3 想定出力

- 関連候補者の ranked list
- 候補者の要約
- 候補者と seed の関係説明
- 候補者の証拠一覧（論文、repo、artifact、共著など）
- 類似人材 / 隣接分野人材の候補

---

## 4. 設計方針

### 4.1 基本思想

- **Graph first**：人材はプロフィールではなく、関係構造で見る
- **Evidence based**：評価は肩書きではなく、成果物と痕跡に基づく
- **Explainable**：結果には必ず理由と根拠を添える
- **Human-in-the-loop**：完全自動ではなく、人間の判断を支援する
- **MVP first**：最初は Talent Discovery のみ最適化し、他用途は設計上の拡張性だけ確保する

### 4.2 初期制約

- なるべく無料 / 低コストスタックで構築
- 公開データから開始
- まずは OpenAlex + GitHub を主要ソースにする
- UIは過剰にグラフ可視化へ寄せず、発見導線を重視する

---

## 5. 全体アーキテクチャ

### 5.1 論理構成

```text
[Data Sources]
  ├ OpenAlex API
  ├ GitHub API
  └ Optional future sources
       ├ arXiv
       ├ Semantic Scholar
       ├ Kaggle
       ├ personal uploads
       └ company internal data

        ↓

[Ingestion / ETL Layer]
  ├ raw fetch
  ├ normalize
  ├ entity resolution
  ├ graph transformation
  └ feature generation

        ↓

[Storage Layer]
  ├ Postgres (normalized relational data)
  ├ Neo4j (graph)
  ├ pgvector / Qdrant (embeddings)
  └ File storage (raw JSON)

        ↓

[Intelligence Layer]
  ├ graph traversal
  ├ ranking
  ├ anomaly detection
  ├ clustering
  └ explanation generation

        ↓

[Application Layer]
  ├ Search API
  ├ Discovery API
  ├ Candidate Brief API
  ├ Shortlist API
  └ Admin API

        ↓

[UI]
  ├ Search page
  ├ Discovery page
  ├ Candidate page
  ├ Shortlist page
  └ Admin / debug page
```

### 5.2 物理構成（MVP）

```text
Frontend: Next.js
Backend API: FastAPI
Batch / ETL: Python scripts + cron / Prefect
Relational DB: PostgreSQL
Vector: pgvector
Graph DB: Neo4j Community
Modeling: Python (scikit-learn, sentence-transformers)
LLM: optional external API or local OSS model
Storage: local disk / S3 compatible future
```

---

## 6. コンポーネント設計

### 6.1 data_ingest

**役割**
- 外部ソースから raw data を取得する

**サブモジュール**
- `openalex_client.py`
- `github_client.py`
- `fetch_jobs.py`

**主な責務**
- API request
- pagination
- retry
- rate limiting
- raw response の保存

### 6.2 normalizer

**役割**
- raw JSON を内部共通スキーマへ変換する

**サブモジュール**
- `normalize_openalex.py`
- `normalize_github.py`
- `common_schema.py`

**主な責務**
- canonical field mapping
- null handling
- text cleanup
- datetime normalization

### 6.3 entity_resolver

**役割**
- 同一人物 / 組織 / 作品の名寄せ

**主な責務**
- OpenAlex author と GitHub user のリンク候補生成
- name similarity
- org similarity
- concept overlap
- confidence scoring

### 6.4 graph_builder

**役割**
- 正規化データから graph node / edge を生成し Neo4j に反映する

### 6.5 embedding_engine

**役割**
- Person / Paper / Repo / Concept の埋め込みを生成する

### 6.6 ranking_engine

**役割**
- relevance, novelty, growth, evidence quality を統合して候補者順位を返す

### 6.7 anomaly_detector

**役割**
- hidden expert 候補を検出する

### 6.8 explanation_engine

**役割**
- 候補者の重要性を根拠付きで説明する

### 6.9 api_server

**役割**
- UIおよび外部連携向けに REST API を提供する

### 6.10 frontend

**役割**
- seed 入力、探索、ランキング閲覧、shortlist 管理を提供する

---

## 7. データソース設計

## 7.1 OpenAlex

### 取得対象
- works
- authors
- institutions
- concepts
- authorships
- cited_by_count
- referenced_works

### 利用目的
- 論文ベースの専門性把握
- 共著ネットワーク構築
- 所属と研究テーマの把握

### 主な内部マッピング
- work → Paper
- author → Person
- institution → Org
- concept → Concept

## 7.2 GitHub

### 取得対象
- user
- repository
- contributor
- topics
- README
- issues
- pull requests
- comments
- stargazers_count
- forks_count
- pushed_at

### 利用目的
- 実装力・継続性・技術スタイルの把握
- 実務寄りの貢献シグナル取得
- Artifact層の充実

### 主な内部マッピング
- user → Person
- repository → Repo
- issue/pr/comment → Artifact
- topic → Concept

---

## 8. データモデル

### 8.1 基本方針

データは以下の4層で保持する。

1. **Raw layer**：APIレスポンスそのまま保存  
2. **Normalized layer**：共通スキーマ化したテーブル  
3. **Graph layer**：Neo4j 上の node / edge  
4. **Feature layer**：ranking や anomaly 用の特徴量

---

## 9. 正規化スキーマ（Postgres）

### 9.1 persons

| column | type | description |
|---|---|---|
| person_id | text pk | 内部ID |
| canonical_name | text | 標準名 |
| openalex_author_id | text nullable | OpenAlex ID |
| github_login | text nullable | GitHub login |
| primary_org_id | text nullable | 主要所属 |
| headline | text nullable | 要約 |
| created_at | timestamp | 作成時刻 |
| updated_at | timestamp | 更新時刻 |

### 9.2 orgs

| column | type | description |
|---|---|---|
| org_id | text pk | 内部ID |
| canonical_name | text | 組織名 |
| org_type | text | university/company/lab/etc |
| openalex_institution_id | text nullable | OpenAlex institution id |
| github_org_login | text nullable | GitHub org |

### 9.3 papers

| column | type | description |
|---|---|---|
| paper_id | text pk | 内部ID |
| openalex_work_id | text unique | OpenAlex work id |
| title | text | タイトル |
| abstract | text nullable | 要約 |
| publication_year | int | 年 |
| cited_by_count | int | 被引用数 |
| venue_name | text nullable | venue |
| doi | text nullable | DOI |

### 9.4 repos

| column | type | description |
|---|---|---|
| repo_id | text pk | 内部ID |
| github_repo_full_name | text unique | owner/name |
| repo_name | text | repo名 |
| description | text nullable | 説明 |
| stars | int | stars |
| forks | int | forks |
| language | text nullable | 主言語 |
| pushed_at | timestamp nullable | 最終更新 |
| archived | boolean | archive 여부 |

### 9.5 concepts

| column | type | description |
|---|---|---|
| concept_id | text pk | 内部ID |
| canonical_name | text | 概念名 |
| source | text | openalex/github/manual |
| concept_type | text | skill/domain/problem/topic |

### 9.6 artifacts

| column | type | description |
|---|---|---|
| artifact_id | text pk | 内部ID |
| artifact_type | text | issue/pr/comment/article/talk |
| source | text | github/openalex/manual |
| title | text nullable | タイトル |
| body_text | text nullable | 本文 |
| created_at | timestamp nullable | 作成日時 |
| source_url | text nullable | 元URL |

### 9.7 entity_links

| column | type | description |
|---|---|---|
| entity_link_id | text pk | 内部ID |
| left_entity_type | text | Person etc |
| left_entity_id | text | 内部ID |
| right_entity_type | text | Person etc |
| right_entity_id | text | 内部ID |
| link_type | text | same_as/candidate_match |
| confidence | float | 信頼度 |
| method | text | rule/model/manual |

---

## 10. Graph Schema（Neo4j）

### 10.1 Core Node Labels

- `Person`
- `Org`
- `Paper`
- `Repo`
- `Concept`
- `Artifact`

### 10.2 Node Properties

#### Person
- `person_id`
- `name`
- `headline`
- `primary_org_name`
- `novelty_score`
- `growth_score`
- `credibility_score`
- `style_cluster_id`

#### Paper
- `paper_id`
- `title`
- `year`
- `cited_by_count`

#### Repo
- `repo_id`
- `full_name`
- `stars`
- `language`
- `pushed_at`

#### Concept
- `concept_id`
- `name`
- `concept_type`

#### Artifact
- `artifact_id`
- `artifact_type`
- `title`
- `source`

#### Org
- `org_id`
- `name`
- `org_type`

### 10.3 Core Relationships

- `(Person)-[:AUTHORED]->(Paper)`
- `(Person)-[:CONTRIBUTED_TO]->(Repo)`
- `(Person)-[:AFFILIATED_WITH]->(Org)`
- `(Paper)-[:ABOUT]->(Concept)`
- `(Repo)-[:ABOUT]->(Concept)`
- `(Artifact)-[:ABOUT]->(Concept)`
- `(Person)-[:CREATED]->(Artifact)`
- `(Paper)-[:CITES]->(Paper)`
- `(Person)-[:COAUTHORED_WITH]->(Person)`
- `(Person)-[:SIMILAR_TO {source: "inferred", score: float}]->(Person)`
- `(Person)-[:LIKELY_EXPERT_IN {source: "inferred", score: float}]->(Concept)`

### 10.4 関係生成ルール

#### COAUTHORED_WITH
- 同一 Paper に著者として含まれる Person 間で生成
- `count_shared_papers` を property に持たせてもよい

#### SIMILAR_TO
- 埋め込み類似度 + concept overlap + graph proximity で算出
- 推論関係として別管理

#### LIKELY_EXPERT_IN
- Paper / Repo / Artifact の concept 集約により推定

---

## 11. 名寄せ（Entity Resolution）設計

### 11.1 課題

OpenAlex と GitHub では、同一人物が別IDとして存在する。これを解かないと、研究実績とOSS実績が分断される。

### 11.2 初期アプローチ

**段階的名寄せ**を採用する。

#### Level 1: deterministic
- exact GitHub URL mention
- ORCID 等の明示ID
- 同一メール / profile link（取れる場合のみ）

#### Level 2: heuristic
- 名前類似度
- 所属類似度
- topic / concept overlap
- README / homepage / personal site matching

#### Level 3: model-based
- ペア特徴量から match probability 推定

### 11.3 出力
- auto-merge は high confidence のみ
- medium confidence は `entity_links` に候補として保持
- UIで human review 可能にする

---

## 12. Embedding設計

### 12.1 埋め込み対象

#### Person embedding
以下を連結した Person Text を生成する。
- 主要論文 title + abstract
- 主な repo description + README要約
- 重要な issue / PR コメント要約
- 所属・概念タグ

#### Paper embedding
- title + abstract + concepts

#### Repo embedding
- repo description + README + topics

#### Concept embedding
- 概念名 + 親概念 + 関連概念

### 12.2 実装方針

初期は `sentence-transformers` を使う。
候補：
- `BAAI/bge-small-en-v1.5`
- `sentence-transformers/all-MiniLM-L6-v2`

### 12.3 保存方針

- Postgres + pgvector に保存
- entity type ごとにテーブル分離可

### 12.4 更新タイミング

- person, repo, paper 更新時に再計算
- バッチ再計算も可能

---

## 13. Feature Engineering 設計

### 13.1 Person features

#### Graph系
- degree_centrality
- pagerank
- betweenness
- num_coauthors
- num_org_connections

#### Research系
- num_papers
- total_citations
- recent_paper_count
- concept_diversity

#### OSS系
- num_repos
- total_repo_stars
- recent_repo_activity
- num_artifacts
- issue_comment_depth_score

#### Growth系
- papers_last_12m
- citations_last_12m proxy
- repo_activity_last_6m

#### Evidence系
- evidence_count
- evidence_diversity
- evidence_recency

#### Similarity系
- seed_cosine_similarity
- shared_concept_count
- shared_graph_neighbors

### 13.2 Repo features
- stars
- forks
- contributors_count
- recency score
- readme richness

### 13.3 Paper features
- cited_by_count
- recency score
- concept specificity

---

## 14. Ranking設計

### 14.1 ranking の目的

特定 seed に対して、「関連しつつ、面白く、深掘る価値がある人材」を上位に返す。

### 14.2 score の分解

MVPでは以下の線形結合から開始する。

```text
final_score =
  0.30 * semantic_similarity
+ 0.20 * graph_proximity
+ 0.15 * novelty_score
+ 0.15 * growth_score
+ 0.10 * evidence_quality
+ 0.10 * credibility_score
```

### 14.3 各スコア定義

#### semantic_similarity
- seed embedding と candidate person embedding の cosine similarity

#### graph_proximity
- shortest path inverse
- shared concepts
- shared neighbors

#### novelty_score
- popularity が高すぎないこと
- ただし evidence は十分あること

例：
- citation や stars が極端に大きい人だけを優遇しない

#### growth_score
- 最近の活動増加
- recent papers / recent repo pushes / recent comments

#### evidence_quality
- 高品質な repo, paper, artifact をどれだけ持つか

#### credibility_score
- 研究・実装の双方に偏りすぎていないか
- 低品質ノイズが多くないか

### 14.4 mode 切替

#### standard mode
バランス型

#### hidden expert mode
novelty / evidence quality / anomaly を重視

#### emerging mode
growth / recency を重視

---

## 15. Hidden Expert 検出

### 15.1 狙い

有名人ランキングではなく、「まだ目立っていないが本質的に強い人」を拾う。

### 15.2 特徴量候補

- citation percentile
- repo popularity percentile
- evidence quality percentile
- strong-neighbor connectivity
- concept specificity
- activity recency

### 15.3 実装

初期は `IsolationForest` を採用する。

入力例：
- log_total_citations
- log_total_stars
- pagerank
- evidence_quality
- growth_score
- concept_specificity

出力：
- anomaly_score
- hidden_expert_score

### 15.4 注意点

異常値 = 優秀とは限らない。  
したがって hidden expert score は **優先深掘り用**として扱い、絶対評価にしない。

---

## 16. クラスタリング設計

### 16.1 目的

人物を思想・技術スタイル・関心テーマでクラスタ化し、「似た人」を精度良く出す。

### 16.2 手法

- embedding generation
- UMAP で次元圧縮
- HDBSCAN でクラスタリング

### 16.3 出力

- `style_cluster_id`
- cluster summary
- cluster representative concepts

### 16.4 LLM活用

各クラスタについて以下を生成する。
- 1文要約
- 主要概念
- 代表人物
- どんな設計思想が見えるか

---

## 17. Explanation設計

### 17.1 目的

候補者に対して「なぜこの人が出てきたのか」を短く、納得感のある形で返す。

### 17.2 原則

- 説明は必ず **根拠データ** に紐づく
- hallucination を避ける
- free-form より structured generation を優先

### 17.3 入力

- seed metadata
- candidate metadata
- shared concepts
- shortest path / graph relation
- top evidence items
- ranking feature breakdown

### 17.4 出力形式

```json
{
  "summary": "...",
  "why_relevant": [
    "shared concept: multimodal dialogue",
    "contributed to repo X",
    "coauthored with Y"
  ],
  "evidence": [
    {"type": "paper", "title": "..."},
    {"type": "repo", "title": "..."}
  ],
  "style_hint": "..."
}
```

### 17.5 表示文例

- この候補者は、seed と同じ **multimodal dialogue** 領域で活動しており、関連する主要論文2本と実装repo 1件が確認されています。
- 被引用数は突出していない一方で、近接領域の強い研究者との共著が多く、hidden expert 候補として優先度が高いです。

---

## 18. API設計

### 18.1 API方針

- REST ベース
- フロントエンド用に coarse-grained endpoint を用意
- 将来 GraphQL 化は任意

### 18.2 主なエンドポイント

#### `GET /health`
ヘルスチェック

#### `POST /search`
seed 検索

**request**
```json
{
  "query": "multimodal dialogue",
  "entity_types": ["concept", "person", "paper", "repo"]
}
```

**response**
```json
{
  "results": [
    {"entity_type": "concept", "entity_id": "concept_1", "label": "multimodal dialogue"}
  ]
}
```

#### `GET /discovery/{entity_type}/{entity_id}`
seed を起点とした候補取得

**query params**
- `mode=standard|hidden|emerging`
- `limit=20`
- `filters=...`

#### `GET /person/{person_id}`
人物詳細

#### `GET /person/{person_id}/brief`
候補者ブリーフ取得

#### `POST /shortlists`
shortlist 作成

#### `POST /shortlists/{id}/items`
候補追加

#### `GET /graph/neighborhood/{entity_type}/{entity_id}`
近傍グラフ取得（軽量）

#### `POST /admin/ingest/openalex`
OpenAlex ingestion 開始

#### `POST /admin/ingest/github`
GitHub ingestion 開始

---

## 19. Candidate Brief設計

### 19.1 目的

候補者を社内共有・比較しやすい形で1ページ化する。

### 19.2 セクション

1. 基本情報
2. なぜ重要か
3. 主要概念
4. 証拠（papers/repos/artifacts）
5. 関係図
6. hidden expert / emerging 判定
7. 類似候補
8. 注意点 / 不確実性

### 19.3 出力形式
- UI表示
- Markdown export
- JSON export

---

## 20. UI/UX設計

### 20.1 画面一覧

#### Search Page
- query input
- entity type suggestion
- recent searches

#### Discovery Page
- seed summary
- candidate list
- mode switch
- filters
- explanation panel
- mini graph view

#### Person Detail Page
- profile summary
- concepts
- papers
- repos
- artifacts
- graph relations
- similar people

#### Shortlist Page
- saved candidates
- compare view
- notes
- export

#### Admin Page
- ingestion status
- feature refresh status
- entity resolution review

### 20.2 重要なUX原則

- グラフ可視化は補助。主役は ranked list + explanation
- 関連候補へ次々掘れる rabbit hole を用意
- hidden / emerging を1クリックで切り替えられる
- shortlist を自然に作れる導線にする

### 20.3 Discovery Page レイアウト

```text
-------------------------------------------------
Search bar / mode / filters
-------------------------------------------------
Seed summary
-------------------------------------------------
Candidate list        | Explanation / mini graph
Candidate list        | Evidence panel
Candidate list        | Similar concepts
-------------------------------------------------
```

---

## 21. ETL / バッチ設計

### 21.1 ジョブ種別

#### full_seed_ingest
- seed query から関連 papers / persons / repos を一括取得

#### incremental_refresh
- 既存 entity の更新差分を取得

#### feature_refresh
- ranking features 再計算

#### embedding_refresh
- 再埋め込み

#### graph_projection_refresh
- Neo4j projection / derived edges 更新

### 21.2 ETLステップ

1. fetch raw JSON
2. raw save
3. normalize
4. upsert relational tables
5. entity resolution
6. graph upsert
7. embedding compute
8. feature compute
9. inferred relation refresh

### 21.3 エラー処理

- source 単位に retry
- raw 保存が成功した時点で fetch 完了扱い
- normalize / graph / embedding は idempotent に設計

---

## 22. モジュール構成（Python package想定）

```text
talent_graph/
├── api/
│   ├── main.py
│   ├── routes/
│   └── schemas/
├── config/
├── ingestion/
│   ├── openalex_client.py
│   ├── github_client.py
│   └── jobs/
├── normalize/
├── entity_resolution/
├── graph/
│   ├── neo4j_client.py
│   ├── graph_builder.py
│   └── queries/
├── embeddings/
├── features/
├── ranking/
├── anomaly/
├── explain/
├── storage/
│   ├── postgres.py
│   ├── vector_store.py
│   └── raw_store.py
├── ui_contracts/
├── tests/
└── scripts/
```

---

## 23. Neo4j クエリ例

### 23.1 seed から関連人物取得

```cypher
MATCH (c:Concept {concept_id: $concept_id})
MATCH (p:Person)-[:AUTHORED|CONTRIBUTED_TO|CREATED]->(:Paper|:Repo|:Artifact)-[:ABOUT]->(c)
RETURN p
LIMIT 50
```

### 23.2 共著ネットワーク取得

```cypher
MATCH (p1:Person {person_id: $person_id})-[:AUTHORED]->(:Paper)<-[:AUTHORED]-(p2:Person)
WHERE p1 <> p2
RETURN p2, count(*) AS shared_papers
ORDER BY shared_papers DESC
LIMIT 20
```

### 23.3 類似概念人材取得

```cypher
MATCH (seed:Person {person_id: $person_id})-[:LIKELY_EXPERT_IN]->(c:Concept)
MATCH (other:Person)-[:LIKELY_EXPERT_IN]->(c)
WHERE seed <> other
RETURN other, count(c) AS shared_concepts
ORDER BY shared_concepts DESC
LIMIT 50
```

---

## 24. FastAPI スキーマ例

### 24.1 Discovery response

```json
{
  "seed": {
    "entity_type": "concept",
    "entity_id": "concept_123",
    "label": "multimodal dialogue"
  },
  "mode": "hidden",
  "candidates": [
    {
      "person_id": "person_1",
      "name": "Alice",
      "score": 0.82,
      "headline": "Research engineer in multimodal dialogue",
      "scores": {
        "semantic_similarity": 0.91,
        "graph_proximity": 0.65,
        "novelty_score": 0.74,
        "growth_score": 0.80,
        "evidence_quality": 0.76,
        "credibility_score": 0.72
      },
      "explanation": {
        "summary": "...",
        "why_relevant": ["..."],
        "evidence": [{"type": "paper", "title": "..."}]
      }
    }
  ]
}
```

---

## 25. 非機能要件

### 25.1 性能

MVP目標
- discovery API: 2〜5秒以内
- person detail: 1〜3秒以内
- shortlist操作: 1秒以内

### 25.2 可用性

- MVPでは高可用性不要
- 単一インスタンス + バックアップで十分

### 25.3 スケーラビリティ

- ingestion と API を分離
- embedding はバッチで回す
- graph query の重い処理は前計算を検討

### 25.4 観測可能性

- request logs
- batch job logs
- failure alerts
- ingestion counts
- node / edge counts
- entity resolution review queue size

---

## 26. セキュリティ・法務・倫理

### 26.1 初期方針

- 公開データのみ利用
- API規約に従う
- 不必要な個人情報は保持しない
- センシティブ推論を避ける

### 26.2 リスク

- 名寄せ誤りによる誤認
- 公開情報の過剰統合による違和感
- hidden expert としての誤評価

### 26.3 対策

- confidence 表示
- 推論と観測事実を分離
- export 時に source を明示
- 人間レビューの導線確保

---

## 27. テスト戦略

### 27.1 単体テスト
- normalizer
- entity resolution rules
- ranking functions
- feature calculation

### 27.2 結合テスト
- ingestion → normalize → graph build
- search → discovery → explanation

### 27.3 品質テスト
- known experts が上位に来るか
- hidden expert 候補に納得感があるか
- explanation が根拠から逸脱していないか

### 27.4 オフライン評価
- curated query set を作成
- expected candidate list / expected relation を持つ
- precision@k, MRR, explanation usefulness を測る

---

## 28. MVPスコープ

### 28.1 含めるもの

- OpenAlex ingestion
- GitHub ingestion
- basic entity resolution
- Neo4j graph build
- Person / Paper / Repo / Concept / Org / Artifact
- ranking
- hidden expert mode
- explanation generation
- Search / Discovery / Person / Shortlist UI

### 28.2 含めないもの

- 完全自律エージェント
- 高度な collaborative features
- enterprise private data integration
- multi-tenant permissions
- advanced graph visualization
- customer discovery 固有機能

---

## 29. 今後の拡張

### 29.1 Phase 2
- saved search
- alerts
- manual curation tools
- entity resolution review UI
- export to markdown / PDF

### 29.2 Phase 3
- semi-autonomous discovery agent
- interview / outreach memo generation
- team collaboration
- internal data sources

### 29.3 Phase 4
- research_graph への展開
- market_graph への展開
- unified discovery platform

---

## 30. 開発ロードマップ（技術観点）

### Sprint 1
- project scaffold
- Postgres / Neo4j setup
- OpenAlex client
- normalize_openalex
- initial graph import

### Sprint 2
- GitHub client
- normalize_github
- repo / artifact model
- person merge candidate logic

### Sprint 3
- embedding pipeline
- ranking engine
- discovery endpoint
- simple frontend search/discovery

### Sprint 4
- hidden expert detection
- explanation engine
- shortlist feature
- person brief page

### Sprint 5
- offline eval set
- performance tuning
- admin/debug page

---

## 31. 主要な設計上の判断まとめ

1. **内部プロジェクト名は talent_graph とする**  
2. **MVPは Talent Discovery に限定する**  
3. **OpenAlex + GitHub を初期主要ソースとする**  
4. **Graph DB は Neo4j Community を採用する**  
5. **Vector は pgvector で十分**  
6. **LLMは説明生成を中心に使い、判定の主役にはしない**  
7. **Graph visualization より ranking + explanation を重視する**  
8. **事実と推論を必ず分離する**  
9. **hidden expert は絶対評価ではなく優先深掘り用とする**  
10. **将来の汎用化を見据えつつ、UI/UXは Talent 専用で作る**

---

## 32. 一文まとめ

`talent_graph` は、論文・オープンソース・組織・概念の関係構造を統合し、ランキングと説明生成を通じて、履歴書検索では見つからない卓越人材を発見するための Talent Discovery 基盤である。

