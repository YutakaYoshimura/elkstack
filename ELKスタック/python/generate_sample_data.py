"""
ELKスタック学習用のサンプルセンサーデータを生成する。

3ヶ月分のデータを10分間隔で生成。
- 正常時: 各センサー値がベースライン付近でランダムに変動
- 故障前兆: 故障日の7日前から徐々にセンサー値が悪化
- 故障モード: ベアリング劣化（振動上昇）、モーター過熱（温度上昇）

使い方（ローカルで実行）:
  pip install pandas numpy
  python generate_sample_data.py
"""

import os
import pandas as pd
import numpy as np

# 乱数シード固定（再現性のため）
np.random.seed(42)

# 出力先
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")


def generate_sensor_data():
    """3ヶ月分のセンサーデータを生成"""

    # 設備マスター
    devices = [
        {"device_id": "pump-01", "device_name": "ポンプA-01", "base_vibration": 3.0, "base_temp": 45.0, "base_current": 8.5},
        {"device_id": "pump-02", "device_name": "ポンプA-02", "base_vibration": 2.8, "base_temp": 43.0, "base_current": 8.0},
        {"device_id": "motor-01", "device_name": "モーターB-01", "base_vibration": 4.0, "base_temp": 55.0, "base_current": 12.0},
    ]

    # 故障イベント定義
    failures = [
        {"device_id": "pump-01", "failure_date": "2026-01-20", "failure_mode": "ベアリング劣化",
         "description": "異音発生により停止・ベアリング交換", "affect": "vibration", "severity": 3.0},
        {"device_id": "pump-01", "failure_date": "2026-02-15", "failure_mode": "モーター過熱",
         "description": "温度上昇により保護停止", "affect": "temperature", "severity": 25.0},
        {"device_id": "motor-01", "failure_date": "2026-02-05", "failure_mode": "ベアリング劣化",
         "description": "振動値上昇・計画停止で交換", "affect": "vibration", "severity": 4.0},
    ]

    # 期間: 2026-01-01 ~ 2026-03-31（10分間隔）
    timestamps = pd.date_range("2026-01-01", "2026-03-31 23:50:00", freq="10min")
    print(f"生成期間: {timestamps[0]} ～ {timestamps[-1]}")
    print(f"タイムスタンプ数: {len(timestamps)} × {len(devices)} 台 = {len(timestamps) * len(devices)} 行")

    rows = []
    for device in devices:
        for ts in timestamps:
            # ベースラインからのランダム変動（正常状態）
            vibration = device["base_vibration"] + np.random.normal(0, 0.3)
            temperature = device["base_temp"] + np.random.normal(0, 1.5)
            current = device["base_current"] + np.random.normal(0, 0.5)
            pressure = 2.0 + np.random.normal(0, 0.1)
            flow_rate = 15.0 + np.random.normal(0, 0.5)

            # 日内変動（昼間は少し高め）
            hour = ts.hour
            if 8 <= hour <= 18:
                temperature += 2.0
                current += 0.5

            # 故障前兆の付与（故障日の7日前から徐々に悪化）
            for f in failures:
                if f["device_id"] != device["device_id"]:
                    continue
                failure_dt = pd.Timestamp(f["failure_date"])
                pre_failure_start = failure_dt - pd.Timedelta(days=7)

                if pre_failure_start <= ts <= failure_dt:
                    # 故障までの進行度（0.0 → 1.0）
                    progress = (ts - pre_failure_start).total_seconds() / (7 * 24 * 3600)
                    # 二次関数的に悪化（最初はゆっくり、直前に急激に）
                    degradation = progress ** 2 * f["severity"]

                    if f["affect"] == "vibration":
                        vibration += degradation
                        # 振動が上がると電流も少し上がる（相関）
                        current += degradation * 0.3
                    elif f["affect"] == "temperature":
                        temperature += degradation
                        # 温度が上がると電流も上がる（相関）
                        current += degradation * 0.15

            # 値のクリップ（物理的にありえない値を除外）
            vibration = max(0.5, vibration)
            temperature = max(20.0, temperature)
            current = max(2.0, current)
            pressure = max(0.5, pressure)
            flow_rate = max(5.0, flow_rate)

            rows.append({
                "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
                "device_id": device["device_id"],
                "device_name": device["device_name"],
                "vibration": round(vibration, 2),
                "temperature": round(temperature, 2),
                "current": round(current, 2),
                "pressure": round(pressure, 2),
                "flow_rate": round(flow_rate, 2),
            })

    df = pd.DataFrame(rows)
    return df, devices, failures


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=== サンプルセンサーデータを生成中 ===")
    sensor_df, devices, failures = generate_sensor_data()

    # sensor_data.csv
    sensor_path = os.path.join(OUTPUT_DIR, "sensor_data.csv")
    sensor_df.to_csv(sensor_path, index=False)
    print(f"\nsensor_data.csv: {len(sensor_df)} rows -> {sensor_path}")

    # failure_history.csv
    failure_rows = []
    for f in failures:
        failure_rows.append({
            "device_id": f["device_id"],
            "failure_date": f["failure_date"],
            "failure_mode": f["failure_mode"],
            "description": f["description"],
        })
    failure_df = pd.DataFrame(failure_rows)
    failure_path = os.path.join(OUTPUT_DIR, "failure_history.csv")
    failure_df.to_csv(failure_path, index=False)
    print(f"failure_history.csv: {len(failure_df)} rows -> {failure_path}")

    # equipment_master.csv
    equip_rows = []
    for d in devices:
        equip_rows.append({
            "device_id": d["device_id"],
            "device_name": d["device_name"],
            "type": "ポンプ" if "pump" in d["device_id"] else "モーター",
            "location": "A棟1F" if "pump" in d["device_id"] else "B棟2F",
        })
    equip_df = pd.DataFrame(equip_rows)
    equip_path = os.path.join(OUTPUT_DIR, "equipment_master.csv")
    equip_df.to_csv(equip_path, index=False)
    print(f"equipment_master.csv: {len(equip_df)} rows -> {equip_path}")

    # threshold_settings.csv
    threshold_rows = [
        {"device_id": "pump-01", "sensor": "vibration", "lower_limit": 1.0, "upper_limit": 8.0, "unit": "mm/s"},
        {"device_id": "pump-01", "sensor": "temperature", "lower_limit": 20.0, "upper_limit": 75.0, "unit": "°C"},
        {"device_id": "pump-01", "sensor": "current", "lower_limit": 3.0, "upper_limit": 14.0, "unit": "A"},
        {"device_id": "pump-02", "sensor": "vibration", "lower_limit": 1.0, "upper_limit": 8.0, "unit": "mm/s"},
        {"device_id": "pump-02", "sensor": "temperature", "lower_limit": 20.0, "upper_limit": 75.0, "unit": "°C"},
        {"device_id": "pump-02", "sensor": "current", "lower_limit": 3.0, "upper_limit": 14.0, "unit": "A"},
        {"device_id": "motor-01", "sensor": "vibration", "lower_limit": 1.5, "upper_limit": 10.0, "unit": "mm/s"},
        {"device_id": "motor-01", "sensor": "temperature", "lower_limit": 25.0, "upper_limit": 85.0, "unit": "°C"},
        {"device_id": "motor-01", "sensor": "current", "lower_limit": 5.0, "upper_limit": 18.0, "unit": "A"},
    ]
    threshold_df = pd.DataFrame(threshold_rows)
    threshold_path = os.path.join(OUTPUT_DIR, "threshold_settings.csv")
    threshold_df.to_csv(threshold_path, index=False)
    print(f"threshold_settings.csv: {len(threshold_df)} rows -> {threshold_path}")

    # サマリー
    print("\n=== 生成データのサマリー ===")
    print(f"期間: 2026-01-01 ～ 2026-03-31")
    print(f"設備数: {len(devices)} 台")
    print(f"故障イベント数: {len(failures)} 件")
    for f in failures:
        print(f"  - {f['device_id']}: {f['failure_date']} ({f['failure_mode']})")
    print(f"\nセンサーデータ統計:")
    for col in ["vibration", "temperature", "current"]:
        print(f"  {col}: mean={sensor_df[col].mean():.2f}, "
              f"min={sensor_df[col].min():.2f}, max={sensor_df[col].max():.2f}")


if __name__ == "__main__":
    main()
