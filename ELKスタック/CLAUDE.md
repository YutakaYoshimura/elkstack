# CLAUDE.md

すべて日本語で記述、回答してください。

## プロジェクト概要

ELKスタック（Elasticsearch + Logstash + Kibana）を使った予知保全PoCの学習・検証環境。
Docker Compose でローカルに構築し、サンプルセンサーデータで異常検知～可視化の一連の流れを体験する。

## ディレクトリ構成

```
D:\Develop\ELKスタック\
├── docker-compose.yml          # Docker Compose 定義
├── .env                        # 環境変数（パスワード等）
├── CLAUDE.md                   # このファイル
├── docs/                       # ドキュメント類
│   ├── 00_概要と目的.md        # プロジェクトの目的・実現したいこと
│   └── 01_学習手順.md          # ステップバイステップの学習手順
├── elasticsearch/
│   └── config/
│       └── elasticsearch.yml   # Elasticsearch 設定
├── logstash/
│   ├── config/
│   │   └── logstash.yml        # Logstash 設定
│   └── pipeline/
│       └── sensor-data.conf    # CSVデータ取り込みパイプライン
├── elastalert/
│   ├── config.yaml             # ElastAlert2 基本設定
│   └── rules/
│       └── anomaly-alert.yaml  # アラートルール
├── python/
│   ├── Dockerfile              # Python MLコンテナ
│   ├── requirements.txt        # Python パッケージ
│   ├── generate_sample_data.py # サンプルデータ生成（ローカル実行）
│   ├── train_model.py          # ML学習スクリプト（コンテナ内実行）
│   └── batch_inference.py      # バッチ推論スクリプト（コンテナ内実行）
└── data/
    ├── sensor_data.csv          # センサーデータ（38,880行 × 3台 × 3ヶ月）
    ├── failure_history.csv      # 故障履歴（3件）
    ├── equipment_master.csv     # 設備マスター（3台）
    └── threshold_settings.csv   # 閾値設定（9センサー分）
```

## 技術スタック

- **Elasticsearch 8.17**: データ蓄積・検索・ML異常検知
- **Kibana 8.17**: 可視化・ダッシュボード・ML管理
- **Logstash 8.17**: CSVデータの取り込み・変換
- **ElastAlert2**: 閾値ベースのアラート通知
- **Python 3.11 + scikit-learn + LightGBM**: ML学習・推論（高度なカスタマイズ用）

## よく使うコマンド

```bash
# 起動
docker compose up -d

# 停止
docker compose down

# ログ確認
docker compose logs -f elasticsearch
docker compose logs -f logstash
docker compose logs -f kibana

# Elasticsearch 疎通確認
curl -u elastic:changeme http://localhost:9200/_cluster/health?pretty

# データ件数確認
curl -u elastic:changeme "http://localhost:9200/sensor-data-*/_count?pretty"

# ML学習（Pythonコンテナ内で実行）
docker exec python-ml python train_model.py

# バッチ推論（Pythonコンテナ内で実行）
docker exec python-ml python batch_inference.py

# サンプルデータ再生成（ローカルで実行）
python python/generate_sample_data.py

# 完全クリーンアップ（データも削除）
docker compose down -v
```

## アクセス先

- **Kibana**: http://localhost:5601（elastic / changeme）
- **Elasticsearch**: http://localhost:9200

## 関連ドキュメント

- 設計資料: `D:\Documents\Obsidian\private\02_仕事用\03_Azureサービス\90_構成案\ELKスタック構成の場合.md`
- Azure 3案比較: `D:\Documents\Obsidian\private\02_仕事用\03_Azureサービス\90_構成案\3案構成検討.md`

## 注意事項

- `.env` にパスワードが記載されているため、Git に push する場合は `.gitignore` に追加すること
- Elasticsearch ML（X-Pack）は Trial ライセンス（30日間）。期限切れ後は再セットアップが必要
- Docker に最低 8GB のメモリを割り当てること（推奨 16GB）
