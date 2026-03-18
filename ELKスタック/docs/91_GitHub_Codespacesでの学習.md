# GitHub Codespaces での学習

ローカルに Docker Desktop がない環境でも、GitHub Codespaces を使えばブラウザだけで ELK スタックの学習ができる。

## 概要

GitHub Codespaces は、GitHub が提供するクラウド開発環境。リポジトリに `.devcontainer/devcontainer.json` を配置することで、ELK スタックが自動的に起動する環境を構築できる。

### メリット

- ブラウザだけで学習できる（Docker Desktop のインストール不要）
- 環境構築が自動化されている（Codespace を開くだけで ELK スタックが起動）
- どの PC からでもアクセス可能

### 制約

- **無料枠**: 月120コア時間（4コアマシンの場合、月30時間まで）
- **ストレージ**: 15GB まで
- **使わないときは必ず停止**すること（コア時間を消費し続けるため）

| マシンタイプ | メモリ | 月の利用可能時間 | ELK の快適さ |
|---|---|---|---|
| 4コア | 16GB | 30時間 | 快適 |
| 2コア | 8GB | 60時間 | やや制約あり |

## 利用手順

### 1. Codespace を作成する

1. GitHub でリポジトリページを開く
2. 緑色の **Code** ボタンをクリック
3. **Codespaces** タブを選択
4. **Create codespace on master** をクリック
5. マシンタイプの選択画面が表示されたら **4-core (16 GB RAM)** を選択

> 初回作成時は、Docker イメージのダウンロードと ELK スタックの起動に **5〜10分**程度かかる。

### 2. 自動的に実行される初期化処理

Codespace の作成時に、以下の処理が自動実行される（手動操作は不要）:

1. `.env.sample` → `.env` のコピー
2. `docker compose up -d` で全コンテナを起動
3. Elasticsearch の起動待機
4. `kibana_system` ユーザーのパスワード設定
5. Kibana の起動待機

ターミナルに `=== ELK Stack 初期化完了 ===` と表示されたら準備完了。

### 3. Kibana にアクセスする

初期化完了後、Kibana のポート（5601）が自動的にフォワードされる。

- **ポート** タブに `Kibana (5601)` が表示される
- 地球アイコンをクリックするとブラウザで Kibana が開く
- ユーザー名: `elastic` / パスワード: `changeme`

> Codespace 内のポートは自動的に HTTPS URL に変換される（例: `https://xxx-5601.app.github.dev`）。

### 4. 学習を進める

Kibana にログインできたら、[01_学習手順.md](01_学習手順.md) の **Step 2** 以降をそのまま進められる。

コマンド操作は Codespace のターミナルで実行する:

```bash
# データ件数確認
curl -u elastic:changeme "http://localhost:9200/sensor-data-*/_count?pretty"

# ML 学習（Python）
docker exec python-ml python train_model.py

# バッチ推論
docker exec python-ml python batch_inference.py
```

### 5. Codespace を停止する

**学習を中断するときは必ず停止すること**（停止しないと無料枠を消費し続ける）。

1. 左下の **Codespaces** をクリック
2. **Stop Current Codespace** を選択

または GitHub のリポジトリページから:

1. **Code** → **Codespaces** タブ
2. 対象の Codespace の **...** メニュー → **Stop codespace**

### 6. Codespace を再開する

停止した Codespace は、次回アクセス時に自動的に再開される。`postStartCommand` により `docker compose up -d` が自動実行されるため、ELK スタックも自動的に起動する。

## 設定ファイルの説明

### `.devcontainer/devcontainer.json`

Codespace の構成を定義するファイル。主な設定:

| 設定 | 値 | 説明 |
|---|---|---|
| `image` | `mcr.microsoft.com/devcontainers/base:ubuntu` | ベースイメージ |
| `features` | `docker-in-docker`, `python` | Docker と Python 3.11 を追加 |
| `hostRequirements.memory` | `8gb` | 最低 8GB メモリを要求 |
| `forwardPorts` | `[9200, 5601]` | ES と Kibana のポートを自動転送 |
| `postCreateCommand` | `post-create.sh` | 初回作成時の初期化スクリプト |
| `postStartCommand` | `docker compose up -d` | 起動のたびに ELK を自動起動 |

### `.devcontainer/post-create.sh`

Codespace 初回作成時に実行される初期化スクリプト。以下を自動化している:

1. `.env` ファイルの作成
2. Docker Compose による全コンテナの起動
3. Elasticsearch の起動待機
4. `kibana_system` パスワードの設定
5. Kibana の起動待機

## トラブルシューティング

### Codespace の作成に失敗する

- **マシンタイプが選択できない**: `hostRequirements` で 8GB を要求しているため、2コア（4GB）マシンは選択できない。無料枠の残りが十分か確認する

### Kibana にアクセスできない

- ポートタブで 5601 が表示されているか確認
- `docker compose ps` で全コンテナが running か確認
- `docker compose logs kibana` でエラーを確認

### コンテナが起動しない（メモリ不足）

- 2コアマシン（8GB）で起動した場合、メモリが不足することがある
- `.env` の `ES_MEM_LIMIT` を `1g` に下げて `docker compose up -d` を再実行

### 無料枠を使い切った

- 翌月にリセットされるまで待つ
- または、ローカル環境（Docker Desktop）での学習に切り替える
