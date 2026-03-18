"""
学習済みモデルでバッチ推論を実行し、予兆スコアをElasticsearchに書き戻す。

使い方:
  docker exec python-ml python batch_inference.py
"""

import os
import pickle

import pandas as pd
from elasticsearch import Elasticsearch, helpers
from train_model import fetch_sensor_data, generate_features


es = Elasticsearch(
    f"http://{os.environ['ES_HOST']}:{os.environ['ES_PORT']}",
    basic_auth=(os.environ["ES_USER"], os.environ["ES_PASSWORD"]),
)


def run_inference():
    print("=== モデルを読み込み中 ===")
    with open("/app/model.pkl", "rb") as f:
        model = pickle.load(f)

    print("=== センサーデータを取得中 ===")
    df = fetch_sensor_data()
    features = generate_features(df)

    feature_cols = [
        c for c in features.columns if c not in ["@timestamp", "device_id", "label"]
    ]

    print("=== 推論実行中 ===")
    scores = model.predict_proba(features[feature_cols])[:, 1]
    features["anomaly_score"] = scores

    # 閾値判定（比較用）
    features["threshold_alert"] = (
        (features["vibration"] > 10.0)
        | (features["temperature"] > 80.0)
        | (features["current"] > 15.0)
    ).astype(int)

    # Elasticsearch に書き戻し
    print("=== 推論結果を Elasticsearch に書き込み中 ===")
    actions = []
    for _, row in features.iterrows():
        doc = {
            "@timestamp": row["@timestamp"].isoformat(),
            "device_id": row["device_id"],
            "anomaly_score": float(row["anomaly_score"]),
            "threshold_alert": int(row["threshold_alert"]),
            "detection_method": "ml_lightgbm",
            "vibration": float(row["vibration"]),
            "temperature": float(row["temperature"]),
            "current": float(row["current"]),
        }

        # 異常レベル判定
        if row["anomaly_score"] > 0.95:
            doc["alert_level"] = "danger"
        elif row["anomaly_score"] > 0.85:
            doc["alert_level"] = "warning"
        elif row["anomaly_score"] > 0.7:
            doc["alert_level"] = "caution"
        else:
            doc["alert_level"] = "normal"

        actions.append({"_index": "prediction-results", "_source": doc})

    helpers.bulk(es, actions)
    print(f"書き込み完了: {len(actions)} 件")

    # サマリー表示
    alert_counts = features["anomaly_score"].apply(
        lambda s: "danger" if s > 0.95 else "warning" if s > 0.85 else "caution" if s > 0.7 else "normal"
    ).value_counts()
    print("\n=== 判定結果サマリー ===")
    for level, count in alert_counts.items():
        print(f"  {level}: {count} 件")


if __name__ == "__main__":
    run_inference()
