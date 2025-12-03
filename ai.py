import os
import json
import tornado.web
from openai import OpenAI

# Load config to get AI settings
CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.json')

def load_ai_config():
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('ai_config', {})
    except Exception:
        return {}

class ChatAIStreamHandler(tornado.web.RequestHandler):
    async def get(self):
        # SSE headers
        self.set_header("Content-Type", "text/event-stream")
        self.set_header("Cache-Control", "no-cache")
        self.set_header("Connection", "keep-alive")

        prompt = (self.get_argument("prompt", "") or "").strip()
        
        config = load_ai_config()
        api_key = config.get("api_key")
        base_url = config.get("base_url")
        model = self.get_argument("model", "") or config.get("model_name", "Qwen/Qwen2.5-7B-Instruct")

        if not api_key:
            # self.write("event: error\n")
            self.write("data: [Error] 未配置 API Key，请检查 config.json\n\n")
            await self.flush()
            return

        # 初始化 OpenAI Client
        client = OpenAI(api_key=api_key, base_url=base_url)

        try:
            stream = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是成小理，一位友好的中文智能助手，请用简洁自然的中文回答。"},
                    {"role": "user", "content": prompt or "你好"},
                ],
                stream=True,
            )

            for event in stream:
                try:
                    delta = event.choices[0].delta
                    content = delta.content or ""
                except Exception:
                    content = ""
                if content:
                    # 正确的 SSE 格式：data: <content>\n\n
                    # 处理换行符，确保 SSE 格式正确
                    content = content.replace('\n', '\\n')  # 转义换行符
                    self.write(f"data: {content}\n\n")
                    await self.flush()

            # 结束事件
            self.write("data: [DONE]\n\n")
            await self.flush()
        except Exception as e:
            # self.write("event: error\n")
            self.write(f"data: [Error] {str(e)}\n\n")
            await self.flush()

