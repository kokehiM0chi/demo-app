import os
import csv
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
# from google import genai # ここを修正
import google.generativeai as genai

# .env の読み込み
env_path = Path(__file__).parent / '.env'
res=load_dotenv(dotenv_path=env_path, override=True)
print("!!!! res=", res)
# APIキーの設定
api_key = os.getenv("GEMINI_API_KEY")

# クライアントの初期化
client = genai.Client(api_key=api_key)

def extract_recipe_data(text):
    # 'gemini-1.5-flash-latest' または 'gemini-1.5-flash' を試します
    # v1beta ではなく v1 を使うように明示的な設定でモデルを初期化
    model = genai.GenerativeModel(model_name='gemini-1.5-flash')

    prompt = f"""
    以下のYouTube動画の文字起こしテキストから、料理の情報を抽出してJSON形式で出力してください。

    必ず以下のJSONキーを持つオブジェクトを1つだけ返してください。
    {{
        "料理名": "",
        "カテゴリ": "",
        "材料": "",
        "工程": "",
        "コンテキスト": "",
        "URL": "",
        "Video_ID": ""
    }}

    【対象テキスト】
    {text}
    """

    # 生成リクエスト
    response = model.generate_content(
        prompt,
        generation_config={"response_mime_type": "application/json"}
    )

    return json.loads(response.text)

def _extract_recipe_data(text):
    prompt = f"""
    以下のYouTube動画の文字起こしテキストから、料理の情報を抽出してJSON形式で出力してください。

    【出力項目】
    - 料理名
    - カテゴリ
    - 材料
    - 工程
    - コンテキスト
    - URL
    - Video_ID

    【対象テキスト】
    {text}
    """

    # モデル名に 'models/' プレフィックスを付けず、新しいSDK形式で呼び出し
    response = client.models.generate_content(
        model='gemini-1.5-flash',
        contents=prompt,
        config={
            'response_mime_type': 'application/json',
        }
    )

    return json.loads(response.text)

def main():
    input_text = """
    タイトル: 【ダイエット】モデルの朝ごはん
    動画URL: https://www.youtube.com/watch?v=f_tQoDbJO98
    [00:00:00] 昼食べる時間なさそうな時にこれ食べてる...
    朝ごはんとして。めっちゃお腹にたまるから長持ちする。
    大津(オートミール)とチアシードを蜂蜜にかけてで豆乳で混ぜて少なくとも4時間置いて、
    できたらティラミスみたいにヨーグルトとココアパウダー以上。
    """

    try:
        recipe_data = extract_recipe_data(input_text)

        fieldnames = ["料理名", "カテゴリ", "材料", "工程", "コンテキスト", "URL", "Video_ID"]
        writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)

        writer.writeheader()
        writer.writerow(recipe_data)

    except Exception as e:
        print(f"Error occurred: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
