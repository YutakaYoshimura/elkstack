# ELKスタック 予知保全PoC

工場設備（ポンプ・モーター）のセンサーデータを ELK スタックに取り込み、**異常検知 → 可視化 → アラート通知**の一連の流れを体験する学習・検証環境。

## 構成図

```
センサーデータ(CSV)
        │
        ▼
   ┌──────────┐     ┌───────────────┐     ┌──────────┐
   │ Logstash │────▶│ Elasticsearch │◀────│ Python   │
   │ (取込み) │     │ (蓄積・検索)  │     │ (ML推論) │
   └──────────┘     └───────┬───────┘     └──────────┘
                            │
                    ┌───────┴───────┐
                    ▼               ▼
              ┌──────────┐   ┌─────────────┐
              │  Kibana  │   │ ElastAlert2 │
              │ (可視化) │   │  (アラート) │
              └──────────┘   └─────────────┘
```

## 技術スタック

| コンポーネント | バージョン | 役割 |
|---|---|---|
| Elasticsearch | 8.17 | データ蓄積・検索・ML 異常検知 |
| Kibana | 8.17 | 可視化・ダッシュボード・ML 管理 |
| Logstash | 8.17 | CSV データの取り込み・変換 |
| ElastAlert2 | latest | 閾値ベースのアラート通知 |
| Python 3.11 | - | scikit-learn + LightGBM による ML 学習・推論 |

## 前提条件

- Docker Desktop がインストール済み
- ホスト PC のメモリ **8GB 以上**（推奨 16GB）
- ディスク空き容量 20GB 以上

> **メモリ 8GB の PC でも動作可能**。ただし `.env` のメモリ設定を下げる必要がある。詳しくは [.env.sample](.env.sample) のコメントを参照。

> Docker Desktop がない場合は、[GitHub Codespaces でブラウザだけで学習](docs/03_GitHub_Codespacesでの学習.md)することもできる。

## クイックスタート

```bash
# 1. リポジトリをクローン
git clone https://github.com/mizuta0711/learn_elk_stack.git
cd learn_elk_stack

# 2. 環境変数ファイルを準備
copy .env.sample .env

# 3. コンテナを起動（初回はイメージダウンロードに数分かかる）
docker compose up -d

# 4. Elasticsearch の稼働確認
curl -u elastic:changeme http://localhost:9200/_cluster/health?pretty

# 5. kibana_system ユーザーのパスワードを設定（初回のみ）
docker exec -it elasticsearch bin/elasticsearch-reset-password -u kibana_system -i
# プロンプトが表示されたら "changeme" を入力

# 6. Kibana を再起動
docker compose restart kibana
```

起動後、ブラウザで http://localhost:5601 を開く（ユーザー: `elastic` / パスワード: `changeme`）。

## サンプルデータ

3台の設備 x 3ヶ月分（約38,880行）のセンサーデータを同梱。Logstash が起動時に自動で Elasticsearch に投入する。

| 設備ID | 設備名 | 種別 |
|---|---|---|
| pump-01 | ポンプA-01 | ポンプ |
| pump-02 | ポンプA-02 | ポンプ |
| motor-01 | モーターB-01 | モーター |

データには **故障の7日前**から徐々にセンサー値が悪化するパターンが組み込まれており、異常検知の学習に最適。

## ディレクトリ構成

```
├── docker-compose.yml          # Docker Compose 定義
├── .env.sample                 # 環境変数のサンプル（.env にコピーして使用）
├── elasticsearch/config/       # Elasticsearch 設定
├── kibana/config/              # Kibana 設定（日本語化含む）
├── logstash/
│   ├── config/                 # Logstash 設定
│   └── pipeline/               # CSV 取り込みパイプライン
├── elastalert/
│   ├── config.yaml             # ElastAlert2 基本設定
│   └── rules/                  # アラートルール
├── python/
│   ├── Dockerfile              # Python ML コンテナ
│   ├── generate_sample_data.py # サンプルデータ生成
│   ├── train_model.py          # ML 学習
│   └── batch_inference.py      # バッチ推論
├── .devcontainer/              # GitHub Codespaces 設定
├── data/                       # センサーデータ（CSV）
└── docs/                       # ドキュメント
```

## 学習手順

詳細な手順は [docs/01_学習手順.md](docs/01_学習手順.md) を参照。

| Step | 内容 | 概要 |
|---|---|---|
| 1 | 環境起動 | Docker Compose でコンテナを起動し、Kibana にログイン |
| 2 | データ投入確認 | Logstash による CSV 取り込みを確認、Discover でデータ閲覧 |
| 3 | 異常検知（GUI） | Kibana ML で Anomaly Detection ジョブを作成・実行 |
| 4 | 異常検知（Python） | LightGBM で故障予兆スコアを算出（オプション） |
| 5 | ダッシュボード作成 | センサー推移・異常スコア・アラート一覧を可視化 |
| 6 | アラート通知 | ElastAlert2 による異常検知アラートを確認 |

## よく使うコマンド

```bash
# 起動 / 停止
docker compose up -d
docker compose down

# ログ確認
docker compose logs -f elasticsearch

# データ件数確認
curl -u elastic:changeme "http://localhost:9200/sensor-data-*/_count?pretty"

# ML 学習・推論（Python）
docker exec python-ml python train_model.py
docker exec python-ml python batch_inference.py

# 完全クリーンアップ（データも削除）
docker compose down -v
```

## 学習手順の完了後 — 次のステップ

学習手順（Step 1〜6）を一通り完了したら、以下のドキュメントで理解を深め、自分たちのデータでの実践に進む。

### 理解を深める

[02_より理解をすすめるために.md](docs/02_より理解をすすめるために.md) では、PoC で体験した内容の背景にある概念を解説している:

- **データの流れ** — 各コンポーネントが何をしているか、なぜその構成なのか
- **Elasticsearch の基本概念** — インデックス、マッピング、Data View の意味
- **異常検知の考え方** — 教師なし/教師あり学習の違いと使い分け
- **特徴量エンジニアリング** — なぜ生の数値ではなく「変化のパターン」が重要か
- **アラート設計** — 閾値ベース vs ML ベース、アラート疲れの防止

### 自分たちのデータで実践する

[03_今後の進め方.md](docs/03_今後の進め方.md) では、PoC から実運用に向けた具体的なアプローチを段階的に解説している:

- **Phase 1: データ準備** — 自社データの棚卸し、故障履歴の整理、データ品質の確認
- **Phase 2: 小規模検証** — PoC 環境に自社データを投入して ML を検証
- **Phase 3: 本番環境構築** — 環境選択、リアルタイムパイプライン、アラート運用設計
- **Phase 4: 拡張・改善** — モデル再学習、対象設備の拡大、高度な分析への発展

## ドキュメント

| ドキュメント | 内容 | 対象 |
|---|---|---|
| [概要と目的](docs/00_概要と目的.md) | プロジェクトの目的・ゴールイメージ・Azure 構成との対応 | 全員 |
| [学習手順](docs/01_学習手順.md) | ステップバイステップの操作手順（Step 1〜6） | 全員 |
| [より理解をすすめるために](docs/02_より理解をすすめるために.md) | 各コンポーネントの概念、異常検知の考え方 | 学習手順を完了した人 |
| [今後の進め方](docs/03_今後の進め方.md) | 自社データでの実践、本番化へのロードマップ | 実践に進む人 |
| [無料オンライン環境の調査](docs/90_無料オンライン環境の調査.md) | GitHub Codespaces 等の調査結果 | 参考資料 |
| [GitHub Codespaces での学習](docs/91_GitHub_Codespacesでの学習.md) | ブラウザだけで学習する方法 | Docker Desktop がない場合 |
| [Podman での構築](docs/92_podmanでの構築.md) | Windows 11 + Podman で構築する手順 | Docker Desktop を使わない場合 |

## 注意事項

- `.env` にパスワードが記載されているため、`.gitignore` で除外済み。`.env.sample` をコピーして使用すること
- Elasticsearch ML（X-Pack）は **Trial ライセンス（30日間）**。期限切れ後は `docker compose down -v` で再セットアップが必要
- ホスト PC のメモリは **8GB 以上**が必要（推奨 16GB）。8GB の場合は `.env` のメモリ設定を下げること

## 改訂履歴

| 日付 | 内容 |
|---|---|
| 2026-02-22 | 初回リリース（環境構築、サンプルデータ、学習手順 Step 1〜6） |
| 2026-02-22 | Kibana 日本語化対応、`.env.sample` 追加、無料オンライン環境の調査 |
| 2026-02-22 | README.md 追加、GitHub Codespaces 対応（devcontainer 設定） |
| 2026-02-23 | 学習手順を Kibana 実画面に合わせて修正（Step 3 ML ウィザード、Step 5 ダッシュボード） |
| 2026-02-23 | Step 6 アラート解説を充実、Python ML のバグ修正（Dockerfile / train_model.py） |
| 2026-02-23 | 理解を深めるドキュメント（02）、今後の進め方ドキュメント（03）を追加 |
| 2026-02-26 | Windows 11 + Podman での構築手順（92）を追加 |
