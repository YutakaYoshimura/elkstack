"""
センサーデータからMLモデルを学習し、予兆スコアを算出する。

使い方:
  docker exec python-ml python train_model.py
"""

import os
import pickle

import pandas as pd
import numpy as np
from elasticsearch import Elasticsearch
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from lightgbm import LGBMClassifier


es = Elasticsearch(
    f"http://{os.environ['ES_HOST']}:{os.environ['ES_PORT']}",
    basic_auth=(os.environ["ES_USER"], os.environ["ES_PASSWORD"]),
)


def fetch_sensor_data():
    """Elasticsearch からセンサーデータを取得"""
    resp = es.search(
        index="sensor-data-*",
        body={"query": {"match_all": {}}, "size": 10000, "sort": [{"@timestamp": "asc"}]},
    )
    records = [hit["_source"] for hit in resp["hits"]["hits"]]
    df = pd.DataFrame(records)
    df["@timestamp"] = pd.to_datetime(df["@timestamp"])
    return df.sort_values("@timestamp")


def generate_features(df):
    """時系列特徴量を生成"""
    features = pd.DataFrame()
    features["@timestamp"] = df["@timestamp"]
    features["device_id"] = df["device_id"]

    for col in ["vibration", "temperature", "current"]:
        # 移動平均・標準偏差
        features[f"{col}_mean_1h"] = df[col].rolling(window=6, min_periods=1).mean()
        features[f"{col}_std_1h"] = df[col].rolling(window=6, min_periods=1).std().fillna(0)
        features[f"{col}_mean_24h"] = df[col].rolling(window=144, min_periods=1).mean()
        # 変化率
        features[f"{col}_change_rate"] = df[col].pct_change().fillna(0)
        # 現在値
        features[col] = df[col]

    # センサー間相関（直近1時間）
    features["corr_current_temp"] = (
        df["current"].rolling(window=6, min_periods=2).corr(df["temperature"]).fillna(0)
    )
    return features.dropna()


def train():
    """モデルを学習"""
    print("=== センサーデータを取得中 ===")
    df = fetch_sensor_data()
    print(f"取得件数: {len(df)}")

    # 故障履歴を読み込んでラベル付与
    failure_df = pd.read_csv("/data/failure_history.csv")
    failure_df["failure_date"] = pd.to_datetime(failure_df["failure_date"], utc=True)

    print("=== 特徴量を生成中 ===")
    features = generate_features(df)

    # ラベル付与（故障の7日前以内 = 1, それ以外 = 0）
    features["label"] = 0
    for _, row in failure_df.iterrows():
        mask = (
            (features["device_id"] == row["device_id"])
            & (features["@timestamp"] >= row["failure_date"] - pd.Timedelta(days=7))
            & (features["@timestamp"] <= row["failure_date"])
        )
        features.loc[mask, "label"] = 1

    feature_cols = [c for c in features.columns if c not in ["@timestamp", "device_id", "label"]]
    X = features[feature_cols]
    y = features["label"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    print("=== モデルを学習中 ===")
    model = LGBMClassifier(n_estimators=100, random_state=42, verbose=-1)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    print("\n=== 精度評価 ===")
    print(classification_report(y_test, y_pred, target_names=["正常", "異常"]))

    # 特徴量重要度
    importance = sorted(zip(feature_cols, model.feature_importances_), key=lambda x: -x[1])
    print("\n=== 特徴量重要度 TOP5 ===")
    for name, score in importance[:5]:
        print(f"  {name}: {score:.4f}")

    # モデル保存
    with open("/app/model.pkl", "wb") as f:
        pickle.dump(model, f)
    print("\nモデルを保存しました: /app/model.pkl")


if __name__ == "__main__":
    train()
