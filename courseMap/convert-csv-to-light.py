import pandas as pd

# 先ほど作った route.csv を読み込む
df = pd.read_csv('route.csv')

# データを思い切って間引く（例：全体の100点分だけ抽出）
step = max(1, len(df) // 50) 
df_light = df.iloc[::step]

# 保存
df_light.to_csv('test_route.csv', index=False)
print(f"✅ 50点に絞り込んだ test_route.csv を作成しました。")
