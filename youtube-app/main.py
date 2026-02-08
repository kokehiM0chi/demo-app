import os
import re
import json
import subprocess
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from youtube_transcript_api import YouTubeTranscriptApi

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class URLRequest(BaseModel):
    url: str

def extract_video_id(url):
    patterns = [r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", r"youtu\.be\/([0-9A-Za-z_-]{11})"]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match: return match.group(1)
    return url

def format_time(seconds):
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"[{h:02d}:{m:02d}:{s:02d}]"

@app.post("/get-transcript")
async def get_transcript_api(request: URLRequest):
    video_id = extract_video_id(request.url)
    if not video_id:
        raise HTTPException(status_code=400, detail="無効なYouTube URLです")

    try:
        # --- CLIで成功したロジックをそのまま移植 ---
        # 1. インスタンス化する（ここが重要！）
        ytt = YouTubeTranscriptApi()
        
        # 2. listメソッドで字幕リストを取得
        transcript_list = ytt.list(video_id)
        
        # 3. 言語の選択
        langs = ['ja', 'ja-JP', 'en']
        try:
            transcript = transcript_list.find_transcript(langs)
        except:
            transcript = next(iter(transcript_list))
        
        # 4. データの取得
        data = transcript.fetch()
        
        # 5. テキスト整形 (CLIと同じプロパティアクセス方式)
        formatted_text = ""
        for item in data:
            # CLI版に合わせて辞書ではなくオブジェクト属性(item['start']ではなくitem['start'])として扱う
            # もしエラーが出る場合は item['start'] に書き換えてください
            try:
                time_stamp = format_time(item['start'])
                text = item['text'].replace('\n', ' ')
            except (TypeError, KeyError):
                time_stamp = format_time(item.start)
                text = item.text.replace('\n', ' ')
                
            formatted_text += f"{time_stamp} {text}\n"

        return {
            "status": "success",
            "language": f"{transcript.language} ({transcript.language_code})",
            "transcript": formatted_text
        }
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/", response_class=HTMLResponse)
async def index():
    # 前回のHTMLコードをここに貼ってください（省略）
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>YouTube字幕取得</title>
        <script src="https://static.line-scdn.net/liff/edge/2/sdk.js"></script>
        <style>
            body { font-family: sans-serif; padding: 20px; background-color: #f8f9fa; }
            .container { max-width: 500px; margin: auto; }
            input { width: 100%; padding: 12px; box-sizing: border-box; margin-bottom: 10px; border: 1px solid #ccc; border-radius: 4px; }
            button { width: 100%; padding: 12px; background: #00b900; color: white; border: none; border-radius: 4px; font-weight: bold; cursor: pointer; }
            #status { margin-top: 10px; font-size: 0.9em; color: #666; }
            #result { white-space: pre-wrap; background: white; padding: 10px; margin-top: 20px; font-size: 13px; height: 350px; overflow-y: scroll; border: 1px solid #ddd; border-radius: 4px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h3>YouTube字幕抜き出し</h3>
            <input type="text" id="url" placeholder="YouTubeのURLをペースト">
            <button onclick="fetchTranscript()">取得開始</button>
            <div id="status"></div>
            <div id="result">ここに字幕が表示されます</div>
        </div>
        <script>
            const MY_LIFF_ID = "YOUR_LIFF_ID"; 
            liff.init({ liffId: MY_LIFF_ID }).catch(err => console.error(err));

            async function fetchTranscript() {
                const url = document.getElementById('url').value;
                const status = document.getElementById('status');
                const resultDiv = document.getElementById('result');
                if (!url) return;
                status.innerText = "取得中...";
                resultDiv.innerText = "";
                try {
                    const response = await fetch('/get-transcript', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ url: url })
                    });
                    const res = await response.json();
                    if (response.ok) {
                        status.innerText = "言語: " + res.language;
                        resultDiv.innerText = res.transcript;
                    } else {
                        status.innerText = "エラー: " + res.detail;
                    }
                } catch (e) {
                    status.innerText = "通信エラー";
                }
            }
        </script>
    </body>
    </html>
    """