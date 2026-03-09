# Graph Discovery Engine 企画設計書

## 1. プロダクト名（仮）

**Graph Discovery Engine**  
副題：**人・研究・企業・関心の関係構造から、次の重要な出会いを発見する探索基盤**

---

## 2. エグゼクティブサマリー

本プロダクトは、論文、GitHub、組織、人物、概念、嗜好、課題といった多様な情報源をグラフとして統合し、AIとグラフ探索を用いて「まだ顕在化していない有望な人・研究・顧客・協業候補」を発見するための探索サービスである。

従来の検索サービスは、キーワード一致や静的プロフィール検索に強い一方で、以下の課題を抱える。

- 肩書きや履歴書に現れない卓越性を見つけにくい
- 隣接領域に潜む有望候補へたどり着きにくい
- なぜその候補が重要かを説明しにくい
- 単なる検索結果の羅列で、発見体験が弱い

本プロダクトは、これらを以下で解決する。

1. **Graph**：人・研究・成果物・概念・組織の関係構造を明示的に保持する  
2. **Embedding**：思想・技術スタイル・関心の近さをベクトルで扱う  
3. **Ranking**：中心性、新規性、成長性、類似性、外れ値性を組み合わせて順位付けする  
4. **LLM Explainability**：なぜその候補が重要かを自然言語で説明する  
5. **Actionability**：保存、共有、比較、接触など次の行動に直接つなげる

短期的には、**Talent Discovery / Research Discovery** のユースケースでMVPを立ち上げる。中長期的には、**潜在顧客探索、共同研究候補探索、マッチング、VC向けDeal Sourcing、コミュニティ形成**へと拡張可能である。

---

## 3. 背景と問題意識

### 3.1 現状の探索の限界

既存の探索は、主に以下のいずれかに偏っている。

- **プロフィール検索型**：LinkedInのように肩書き・職歴・スキルで探す
- **企業データベース型**：Crunchbaseのように企業・資金調達情報を調べる
- **知識グラフ型**：DiffbotのようにWebから構造化データを抽出する
- **ATS型**：採用プロセスの管理に強いが、発見そのものには弱い

しかし実際に見つけたいのは、次のような存在である。

- まだ有名ではないが、重要な分野で異常なこだわりを持つ人
- 既存の肩書きでは表現できない思想・設計スタイルを持つ人
- 潜在顧客として極めて強い反応を示しそうなコミュニティや集団
- 一見遠い分野に見えて、本質的に同じ課題を解いている人たち

### 3.2 解くべき本質的課題

本プロダクトが解くべき課題は、単なる検索精度の問題ではなく、以下である。

1. **構造理解の欠如**  
   人・成果物・概念・組織の関係が見えないため、探索が浅くなる。

2. **卓越性の定義の難しさ**  
   有名さや肩書きではなく、実際の執着・実装・議論・継続性を見たい。

3. **探索ループの非効率性**  
   人間が毎回ゼロから検索をやり直しており、発見の再現性がない。

4. **説明責任の欠如**  
   候補が出ても「なぜこの人か」「なぜこの研究か」を説明しづらい。

5. **行動への接続不足**  
   結果を見ても、その後の接触・共有・比較・追跡が弱い。

---

## 4. ビジョン

### 4.1 長期ビジョン

**世界中の人・研究・技術・関心・課題の関係構造を探索可能にし、次の重要な出会いを加速する。**

### 4.2 プロダクト哲学

- 検索ではなく**発見**を支援する
- 静的なプロフィールではなく**行動の痕跡**を見る
- 有名さではなく**解像度の高さと執着**を拾う
- 単なる可視化ではなく**次の行動**につなげる
- AIを魔法扱いせず、**説明可能な探索支援**として使う

---

## 5. 想定ユースケース

### 5.1 第一優先：Talent Discovery

**想定ユーザー**
- CEO
- Founder室
- R&D責任者
- 採用責任者
- 技術ソーサー / エグゼクティブサーチ担当

**課題**
- 普通の採用市場に出てこない卓越人材を探したい
- 隣接分野から本質的に適した人を見つけたい
- なぜその人が必要かを社内に説明したい

**価値**
- hidden expert の発見
- 候補者ブリーフの自動生成
- 似た思想・スタイルの人の連鎖探索

### 5.2 第二優先：Research Discovery

**想定ユーザー**
- 研究者
- 企業R&D
- 共同研究担当
- 技術戦略担当

**課題**
- 特定テーマで本当に面白い研究者・研究室を知りたい
- 論文単体ではなく、人物・テーマ・コード・コミュニティまで広げて見たい

**価値**
- emerging researcher の発見
- 論文→著者→コード→組織→関連テーマの連続探索
- 説明付き推薦

### 5.3 将来拡張：Potential Customer Discovery

**想定ユーザー**
- PMF探索中のスタートアップ
- B2B SaaS
- 新規事業責任者

**課題**
- 潜在顧客がどこにいて、どの課題を持っているのか分からない
- 類似嗜好・類似課題を持つ集団を発見したい

**価値**
- 類似関心集団の発見
- コミュニティ・発信・使用ツール・話題から顧客仮説を立てられる

### 5.4 将来拡張：Matching / Community Discovery

- 嗜好が近い人の発見
- 共同創業候補の発見
- 専門性が補完し合う人の発見
- コミュニティ形成の支援

---

## 6. ターゲット市場と初期セグメント

### 6.1 最初の市場（PMF候補）

優先順位は以下を推奨する。

1. **AI/Research人材探索**
2. **研究者・共同研究先探索**
3. **エグゼクティブサーチ / Deep Tech採用**

### 6.2 なぜこの順か

- OpenAlex や GitHub など公開データが豊富
- 人物・研究・成果物の関係が比較的取りやすい
- 成果指標を定義しやすい
- 探索の価値が高く、導入メリットが明確

### 6.3 初期顧客候補

- AIスタートアップ
- 研究開発型企業
- Deep Tech採用チーム
- CTO/CEO直下の探索チーム
- VC/CVCのTech Sourcingチーム

---

## 7. ユーザーのジョブ（JTBD）

### 7.1 Talent Discovery JTBD

- 「肩書きでは見つからない、本当に強い人を見つけたい」
- 「その人がなぜ強いのか、社内に説明したい」
- 「1人見つけたら、その周辺も芋づる式に掘りたい」

### 7.2 Research Discovery JTBD

- 「このテーマで、次に重要になる人と研究室を知りたい」
- 「論文だけでなく、実装・思想・コミュニティまで見たい」

### 7.3 Potential Customer Discovery JTBD

- 「このプロダクトが刺さりそうな人たちを見つけたい」
- 「似た課題・嗜好を持つ人たちの集まりを知りたい」

---

## 8. 競争環境と差別化

### 8.1 既存カテゴリ

#### LinkedIn Recruiter
- 強み：大規模プロフィール検索
- 弱み：肩書き依存、行動の痕跡が弱い

#### Crunchbase / PitchBook
- 強み：企業・資金調達の把握
- 弱み：人材や思想の発見には弱い

#### Diffbot
- 強み：Webの構造化データ収集
- 弱み：探索UXが弱い、アクション導線が弱い

#### ATS
- 強み：採用プロセス管理
- 弱み：発見そのものには弱い

### 8.2 本プロダクトの差別化

1. **人だけでなく概念・成果物・証拠を中心に見る**  
2. **Graph + Embedding + LLM Explanation を一体化**  
3. **Rabbit hole型の探索UXを提供**  
4. **推論結果と観測事実を分離し、説明可能性を担保**  
5. **Talent / Research / Customer Discovery に横展開可能**

---

## 9. プロダクトコンセプト

### 9.1 一言でいうと

**「検索」ではなく「関係構造に沿って掘り進める発見エンジン」**

### 9.2 コア体験

ユーザーがある seed（人物、論文、repo、概念、会社、課題）を起点にすると、システムが以下を返す。

- 近い候補
- 意外だが重要な候補
- その理由
- 次に掘るべき方向
- 保存・共有・接触の導線

### 9.3 UXの骨格

```text
Seed → Expand → Rank → Explain → Action
```

---

## 10. MVPの定義

### 10.1 MVPで解く問い

**「ある技術テーマや人物を起点に、関連する有望人物を発見し、その理由を説明できるか」**

### 10.2 MVP対象データ

- OpenAlex（論文、著者、所属、概念、引用）
- GitHub（repos、contributors、issues、PR、README）

### 10.3 MVP対象ユーザー

- AI/Research人材を探す採用責任者
- 研究者探索をしたいR&D担当

### 10.4 MVP機能

#### 必須
1. Seed検索
   - 人物名
   - 論文タイトル
   - GitHub repo
   - 技術キーワード

2. グラフ展開
   - 関連人物
   - 共著者
   - 関連repo
   - 関連概念

3. ランキング
   - 類似性
   - 新規性
   - 成長性
   - 中心性

4. 候補の説明
   - LLMによる「なぜこの候補か」説明

5. 保存・比較・共有
   - shortlist
   - candidate brief
   - 共有リンク

#### あると強い
6. hidden expert モード
7. emerging researcher モード
8. 類似思想クラスタ表示

---

## 11. システム要件

### 11.1 非機能要件

- 低コストでプロトタイプ可能
- 公開データ中心で立ち上げられる
- データソース追加が容易
- 推論と事実が分離されている
- 結果に説明可能性がある

### 11.2 初期技術方針（無料寄り）

- Backend: Python + FastAPI
- Graph DB: Neo4j Community Edition
- Vector: pgvector or Qdrant local
- Embedding: sentence-transformers
- LLM: 小型OSSモデル + 必要に応じて外部API
- ETL: Python scripts + cron / Prefect軽量運用
- Frontend: Next.js or React

---

## 12. データモデル / Graph Schema

### 12.1 設計思想

本プロダクトは「人物そのもの」ではなく、**人物・概念・成果物・証拠・組織の多層構造**を扱う。

### 12.2 Core Nodes

- `Person`
- `Paper`
- `Repo`
- `Org`
- `Concept`
- `Artifact`
  - PR
  - IssueComment
  - Talk
  - Article

### 12.3 Core Edges

- `(:Person)-[:AUTHORED]->(:Paper)`
- `(:Person)-[:CONTRIBUTED_TO]->(:Repo)`
- `(:Person)-[:AFFILIATED_WITH]->(:Org)`
- `(:Paper)-[:ABOUT]->(:Concept)`
- `(:Repo)-[:ABOUT]->(:Concept)`
- `(:Artifact)-[:ABOUT]->(:Concept)`
- `(:Person)-[:CREATED]->(:Artifact)`
- `(:Person)-[:COAUTHORED_WITH]->(:Person)`
- `(:Person)-[:SIMILAR_TO]->(:Person)` ※推論層

### 12.4 Scores / Attributes

- relevance_score
- novelty_score
- style_similarity
- growth_score
- credibility_score
- centrality_score

### 12.5 推論層の扱い

AIによる推定は生データと混ぜない。`source=inferred` を付与するか、別管理層に保存する。

---

## 13. コアアルゴリズム

### 13.1 グラフ展開

- 1-hop / 2-hop / 3-hop探索
- 共著ネットワーク
- 共同コントリビューションネットワーク
- 概念共有ネットワーク

### 13.2 類似性推定

- Embedding cosine similarity
- 共通概念数
- 共著 / 共創造距離
- 技術スタイル近接度

### 13.3 ランキング

候補スコアの例：

```text
score =
  0.30 * semantic_similarity
+ 0.20 * graph_centrality
+ 0.20 * novelty_score
+ 0.15 * growth_score
+ 0.15 * evidence_quality
```

### 13.4 hidden expert 検出

- 低知名度だが高品質な証拠を持つ
- 強い人との接続密度が高い
- GitHubや議論ログの質が高い
- 急成長している

### 13.5 外れ値検出

Isolation Forest を用いて「注目すべき外れ値」を検出する。

例：
- citationは低いが、ネットワーク接続が強い
- starsは少ないが、設計品質・議論品質が高い

### 13.6 思想クラスタリング

- Person Text（主要論文、README、Issue、PR等）を統合
- Embedding
- UMAP + HDBSCAN でクラスタ化
- LLMでクラスタ名・特徴を要約

---

## 14. LLM / 自律エージェント設計

### 14.1 LLMの役割

LLMは判定器というより、以下に使う。

1. 候補の説明
2. クラスタ要約
3. 技術スタイル要約
4. 次の探索仮説提案

### 14.2 自律探索エージェント（将来）

#### Explorer
- 新しい論文・repo・人物を取得

#### Evaluator
- 候補の質を数値とテキストで評価

#### Strategist
- どの方向へ探索を広げるか決める

#### Curator
- 社内向けブリーフを生成

### 14.3 初期MVPではどう扱うか

MVPでは完全自律ではなく、**半自律**が望ましい。

- 人間が seed を与える
- システムが候補と説明を返す
- 人間が shortlist を作る
- システムが次の探索候補を提案する

---

## 15. 画面設計 / UX設計

### 15.1 基本画面

#### 1. Search / Seed画面
- キーワード
- 人物名
- 論文名
- repo名
- 会社名

#### 2. Discovery画面
- 中央：seed
- 周囲：関連ノード
- 右：説明パネル
- 上：フィルタ
- 下：候補リスト

#### 3. Candidate Brief画面
- なぜ重要か
- 何に強いか
- どの証拠があるか
- 類似人物
- 関連成果物

#### 4. Collection / Shortlist画面
- 保存候補
- 比較
- 共有
- コメント

### 15.2 UX原則

- グラフは主役ではなく、**発見の補助**
- 視覚化だけで終わらせず、**related / similar / hidden / emerging** の行動導線を優先
- 「なぜこの候補か」が1クリックで分かる
- Rabbit hole を自然に掘れる

### 15.3 UXの成功パターン

```text
Search → Result → Related → Related of Related → Save / Share / Act
```

---

## 16. データ収集とETL

### 16.1 初期データソース

#### OpenAlex
取得対象：
- works
- authors
- institutions
- concepts
- citations

#### GitHub API
取得対象：
- repos
- contributors
- issues
- pull requests
- README
- topics

### 16.2 ETLの流れ

1. source から raw JSON取得
2. normalize / cleaning
3. entity resolution（名寄せ）
4. graph nodes / edges 生成
5. embeddings生成
6. scores更新
7. UI用の派生ビュー生成

### 16.3 名寄せ方針

- OpenAlex Author ID
- GitHub login
- ORCID（可能なら）
- 名前類似 + 組織 + トピックで補助判定

### 16.4 生データ保存方針

- raw JSON を object storage か filesystem に保存
- 正規化後データを Postgres に保存
- グラフ構造を Neo4j に保存

---

## 17. 主要指標（Product Metrics）

### 17.1 探索品質指標

- 保存率（save rate）
- shortlist 作成率
- 候補の説明閲覧率
- 関連候補への連続クリック率
- hidden expert モード利用率

### 17.2 成果指標

#### Talent Discovery
- 面談化率
- 採用化率
- 1件の有望候補に到達するまでの時間短縮

#### Research Discovery
- 共同研究打診率
- 引用 / コラボ候補化率
- 調査時間短縮

#### Potential Customer Discovery
- インタビュー化率
- 反応率
- 仮説検証速度

### 17.3 モデル品質指標

- ranking precision@k
- explanation usefulness score
- hidden expert 検出の満足度
- cluster coherence

---

## 18. Go-To-Market（初期販売戦略）

### 18.1 初期提供形態

最初はSaaSよりも、**半プロダクト・半サービス**が向いている。

- 特定テーマでの探索支援
- 候補者ブリーフ作成
- エグゼクティブ向け調査レポート
- リサーチ探索支援

### 18.2 なぜそうするか

- 顧客ごとに「卓越」の定義が違う
- 探索ロジックの調整が必要
- UX要件の学習が必要

### 18.3 初期販売チャネル

- AIスタートアップへの直接提案
- VC/CVCへの紹介
- CEO/CTO直下の技術採用課題を持つ企業
- 研究開発型企業のR&D責任者

### 18.4 導入提案の切り口

- 一般採用市場にいない卓越人材の発見
- 共同研究相手・外部アドバイザー候補の発見
- 潜在顧客コミュニティの探索

---

## 19. ビジネスモデル案

### 19.1 初期

- 調査 / 探索プロジェクト単位の受託
- 月額レポーティング
- 探索テーマごとの分析提供

### 19.2 中期

- Seat課金 + 使用量課金
- 保存候補数 / クエリ数 / レポート数課金
- team collaboration 機能の上位プラン

### 19.3 長期

- Discovery API
- 自社データ接続オプション
- Enterprise向け private graph

---

## 20. ロードマップ

### Phase 0：問題検証
- 5〜10社にヒアリング
- 既存探索の痛みを定量化
- Talent / Research のどちらが刺さるか検証

### Phase 1：MVP
- OpenAlex + GitHub ingestion
- seed → related people の探索
- ranking + explanation
- shortlist 保存

### Phase 2：実戦投入
- 3社程度で実案件に使う
- 候補の質・説明の有用性を改善
- hidden expert ロジック改善

### Phase 3：プロダクト化
- マルチユーザー
- 共有・比較・コメント
- dashboard / saved search / alerts

### Phase 4：横展開
- 潜在顧客探索
- matching
- community graph
- enterprise private data ingestion

---

## 21. リスクと対策

### 21.1 データ品質

**リスク**
- 名寄せミス
- 欠損
- ソースごとの偏り

**対策**
- 事実と推論の分離
- confidence score の保持
- human-in-the-loop

### 21.2 説明の信頼性

**リスク**
- LLMがもっともらしいが誤った説明をする

**対策**
- 根拠となる edge / evidence を必ず明示
- free-formではなく structured explanation 生成

### 21.3 グラフ可視化への過剰依存

**リスク**
- きれいだが使われない

**対策**
- 保存・共有・比較・接触導線を優先
- グラフは補助UIとする

### 21.4 PMFの散漫化

**リスク**
- Talent、Research、Customer Discovery を一気にやって焦点がぼける

**対策**
- 初期は Talent / Research のどちらかに集中
- 共通基盤だけ汎用化する

### 21.5 法務・倫理

**リスク**
- 人物データの扱い
- スクレイピングや規約違反

**対策**
- 公開データ・規約準拠ソースから開始
- enterprise展開時に法務レビュー
- 不適切推論の抑制

---

## 22. 成功条件

本プロダクトが成功している状態は、以下である。

1. ユーザーが「普通には見つからない有望候補」を見つけられる  
2. 候補の理由説明が納得感を持つ  
3. 一度の検索で終わらず、連続探索が自然に起こる  
4. 保存・共有・比較・接触に進む  
5. 人力探索よりも速く、しかも面白い発見がある  

---

## 23. 初期仮説まとめ

### 仮説1
優れた探索体験は、検索結果の羅列ではなく、**seedから芋づる式に関連を掘る構造**から生まれる。

### 仮説2
卓越性は肩書きではなく、**成果物・議論・継続的な執着の証拠**に現れる。

### 仮説3
LLMは万能判定器ではなく、**理由説明と探索補助**として最も価値が高い。

### 仮説4
最初のPMFは、汎用グラフ探索ではなく、**高単価で痛みが強い探索業務（Talent / Research）**から出る。

### 仮説5
Graph Discoveryの勝敗は、データ量よりも**探索UXと説明可能性**で決まる。

---

## 24. MVP開発タスク（実装観点）

### Backend
- FastAPI scaffold
- OpenAlex client
- GitHub client
- ETL pipeline
- ranking service
- explanation service

### Database
- Neo4j schema
- Postgres / pgvector schema
- raw storage strategy

### Modeling
- embedding generation
- similarity search
- hidden expert scoring
- cluster generation

### Frontend
- search page
- discovery page
- candidate brief page
- shortlist page

### Ops
- cron updates
- monitoring
- data validation

---

## 25. 今後の検討論点

- 初期は Talent と Research のどちらに絞るか
- OpenAlex と GitHub の人物名寄せ精度をどう担保するか
- hidden expert の定義を顧客ごとにどの程度調整するか
- UIはグラフ中心かリスト中心か
- LLM explanation をどこまで自動化するか
- 商用化時のデータライセンス方針

---

## 26. 付録：プロダクトの一文ピッチ案

### パターンA
**Graph Discovery Engine は、論文・GitHub・組織・概念の関係構造から、まだ見つかっていない有望人物や研究を発見し、その理由まで説明する探索基盤です。**

### パターンB
**履歴書検索では見つからない卓越性を、グラフ探索とAIで掘り当てる。**

### パターンC
**人・研究・企業・関心のつながりを辿り、次の重要な出会いを見つけるためのDiscovery OS。**

---

## 27. 最後に

本プロダクトは、単なるグラフ可視化サービスでも、単なる人材検索サービスでもない。  
本質は、**世界の知的・技術的・嗜好的な構造を探索可能にし、重要な出会いを再現可能にすること**にある。

成功の鍵は、

- データ量の多さだけではなく
- どの構造を表現し
- どう順位付けし
- なぜ重要かを説明し
- 次の行動につなげるか

にある。

したがって、MVPでは機能を広げすぎず、まずは **Talent Discovery / Research Discovery の高価値ユースケースで、発見の質と説明の納得感を磨き込む** べきである。

