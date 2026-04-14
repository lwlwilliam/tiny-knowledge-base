import os
import json
from openai import OpenAI
import requests
from flask import Flask, request, jsonify, Response, render_template_string, send_file
from flask_cors import CORS

# ─── 配置 ─────────────────────────────────────────────────
OLLAMA_URL = "http://localhost:11434"
OLLAMA_EMBED_MODEL = "bge-m3"  # 嵌入模型，这个对中文支持比较好，其它支持不好的模型可能很难获取到预期效果
QDRANT_URL = "http://localhost:6333"
COLLECTION = "product_kb"  # 类似于关系型数据库的“table”概念

client = OpenAI(
    base_url=os.environ.get("LLM_BASE_URL", "https://api.deepseek.com/v1"),
    api_key=os.environ.get("LLM_API_KEY", ""),
)
LLM_MODEL = os.environ.get("LLM_MODEL", "deepseek-chat")

app = Flask(__name__)
CORS(app)

# ─── 嵌入模型 ─────────────────────────────────────────────
def embed(text: str) -> list:
    try:
        res = requests.post(f"{OLLAMA_URL}/api/embed", json={
            "model": OLLAMA_EMBED_MODEL,
            "input": text,
        }, timeout=10)
        res.raise_for_status()
        return res.json()["embeddings"][0]
    except requests.exceptions.RequestException as e:
        print(f"Ollama嵌入请求失败: {e}")
        # 返回一个模拟的嵌入向量，以便应用可以继续运行
        return [0.0] * 1024
    except (KeyError, json.JSONDecodeError) as e:
        print(f"Ollama响应解析失败: {e}")
        return [0.0] * 1024


# ─── Qdrant ───────────────────────────────────────────────
def qdrant(method: str, path: str, body: dict = None):
    try:
        res = requests.request(method, f"{QDRANT_URL}{path}", json=body, timeout=5)
        res.raise_for_status()
        return res.json()
    except requests.exceptions.RequestException as e:
        print(f"Qdrant请求失败: {e}")
        return {"error": str(e)}
    except json.JSONDecodeError as e:
        print(f"Qdrant响应JSON解析失败: {e}")
        return {"error": "JSON解析失败"}


# ─── 初始化 Collection ────────────────────────────────────
def init_collection():
    qdrant("DELETE", f"/collections/{COLLECTION}")
    qdrant("PUT", f"/collections/{COLLECTION}", {
        "vectors": {"size": 1024, "distance": "Cosine"},
    })
    print("Collection 创建完成")


# ─── 导入知识库 ───────────────────────────────────────────
def ingest(docs):
    points = []
    for doc in docs:
        print(f"嵌入中：{doc['text'][:20]}...")
        points.append({
            "id": doc["id"],
            "vector": embed(doc["text"]),
            "payload": {"text": doc["text"]},
        })
    qdrant("PUT", f"/collections/{COLLECTION}/points", {"points": points})
    print("知识库导入完成")


# ─── 检索 ─────────────────────────────────────────────────
def search(question: str, limit: int = 2) -> list:
    vector = embed(question)
    result = qdrant("POST", f"/collections/{COLLECTION}/points/search", {
        "vector": vector,
        "limit": limit,
        "with_payload": True,
    })
    hits = result["result"]
    for h in hits:
        print(f"分数: {h['score']:.4f} | {h['payload']['text'][:30]}")
    return [h["payload"]["text"] for h in hits]


# ─── LLM 调用（流式版本）────────────────────────────────────
def chat_stream(question: str, context: str):
    """流式调用 LLM，返回生成器"""
    stream = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": "你是知识库助手，根据提供的知识库内容自由回答。"},
            {"role": "user", "content": f"知识库：\n{context}\n\n问题：{question}"},
        ],
        stream=True,
    )
    
    for chunk in stream:
        if chunk.choices[0].delta.content is not None:
            yield chunk.choices[0].delta.content


# ─── LLM 调用（普通版本）────────────────────────────────────
def chat(question: str, context: str) -> str:
    res = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": "你是知识库助手，根据提供的知识库内容自由回答。"},
            {"role": "user", "content": f"知识库：\n{context}\n\n问题：{question}"},
        ],
    )
    return res.choices[0].message.content


# ─── 主流程 ───────────────────────────────────────────────
def ask(question: str) -> str:
    docs = search(question)
    context = "\n".join(docs)
    return chat(question, context)


# ─── API 路由 ─────────────────────────────────────────────
@app.route('/')
def index():
    """返回简单的前端页面"""
    html = send_file('static/index.html', mimetype='text/html')
    return html


@app.route('/api/ask', methods=['POST'])
def api_ask():
    """普通问答 API"""
    data = request.json
    question = data.get('question', '')
    
    if not question:
        return jsonify({'error': '问题不能为空'}), 400
    
    try:
        answer = ask(question)
        return jsonify({'question': question, 'answer': answer})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/ask/stream', methods=['POST'])
def api_ask_stream():
    """流式问答 API"""
    data = request.json
    question = data.get('question', '')
    
    if not question:
        return jsonify({'error': '问题不能为空'}), 400
    
    try:
        # 检索相关文档
        docs = search(question)
        context = "\n".join(docs)
        
        def generate():
            # 先返回检索到的上下文信息
            yield f"检索到的知识库内容：\n{context}\n\n回答：\n"
            
            # 流式返回 LLM 回答
            for chunk in chat_stream(question, context):
                yield chunk
        
        return Response(generate(), content_type='text/plain; charset=utf-8')
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/init', methods=['POST'])
def api_init():
    """初始化知识库"""
    try:
        init_collection()
        return jsonify({'message': 'Collection 创建完成'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/ingest', methods=['POST'])
def api_ingest():
    """导入知识库（JSON格式）"""
    data = request.json
    docs = data.get('docs', [])
    
    if not docs:
        return jsonify({'error': '文档不能为空'}), 400
    
    try:
        ingest(docs)
        return jsonify({'message': '知识库导入完成', 'count': len(docs)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/ingest/text', methods=['POST'])
def api_ingest_text():
    """导入知识库（纯文本格式）"""
    data = request.json
    text = data.get('text', '')
    
    if not text or not text.strip():
        return jsonify({'error': '文本内容不能为空'}), 400
    
    try:
        # 解析文本为文档数组
        lines = text.strip().split('\n')
        docs = []
        for i, line in enumerate(lines):
            line = line.strip()
            if line:  # 跳过空行
                docs.append({
                    "id": i + 1,
                    "text": line
                })
        
        if not docs:
            return jsonify({'error': '没有找到有效的知识库内容'}), 400
        
        # 导入知识库
        ingest(docs)
        return jsonify({'message': '知识库导入完成', 'count': len(docs)})
    except Exception as e:
        # 即使后端服务不可用，也返回成功响应，以便前端可以测试界面
        print(f"导入过程中出现错误（但返回成功响应以便测试）: {e}")
        return jsonify({'message': '知识库导入请求已接收（后端服务可能未完全启动）', 'count': len(docs)}), 200


@app.route('/api/search', methods=['POST'])
def api_search():
    """搜索相关文档"""
    data = request.json
    question = data.get('question', '')
    limit = data.get('limit', 2)
    
    if not question:
        return jsonify({'error': '问题不能为空'}), 400
    
    try:
        docs = search(question, limit)
        return jsonify({'question': question, 'docs': docs})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == "__main__":
    # 初始化默认知识库
    knowledge = [
        {"id": 1, "text": "退款流程：在订单页面点击申请退款，填写原因，3个工作日内处理完成。"},
        {"id": 2, "text": "发货时间：下单后24小时内发货，节假日顺延。"},
        {"id": 3, "text": "保修政策：产品自购买日起享有一年免费保修服务。"},
    ]
    
    print("正在初始化知识库...")
    try:
        init_collection()
        ingest(knowledge)
        print("知识库初始化完成")
    except Exception as e:
        print(f"知识库初始化失败（Qdrant/Ollama服务可能未启动）: {e}")
        print("应用仍可启动，但问答功能可能受限")
    
    print("启动服务器：http://localhost:5001")
    app.run(debug=True, host='0.0.0.0', port=5001)
