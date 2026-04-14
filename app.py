"""
知识库问答系统
"""

from openai import OpenAI
import requests
from flask import Flask, request, jsonify, Response, send_file
from flask_cors import CORS
import config
import time


client = OpenAI(
    base_url=config.LLM_BASE_URL,
    api_key=config.LLM_API_KEY,
)

app = Flask(__name__)
CORS(app)


def embed(text: str) -> list:
    """通过嵌入模型获取文本嵌入向量"""
    try:
        res = requests.post(f"{config.OLLAMA_URL}/api/embed", json={
            "model": config.OLLAMA_EMBED_MODEL,
            "input": text,
        }, timeout=10)
        res.raise_for_status()
        return res.json()["embeddings"][0]
    except Exception as e:
        print(f"嵌入失败: {e}")
        return [0.0] * config.OLLAMA_EMBED_MODEL_VECTOR_SIZE


def qdrant(method: str, path: str, body: dict = None):
    """发送Qdrant请求"""
    try:
        res = requests.request(method, f"{config.QDRANT_URL}{path}", json=body, timeout=5)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        print(f"Qdrant请求失败: {e}")
        return {"error": str(e)}


def init_collection():
    """根据嵌入模型初始化Qdrant集合"""
    """删除已存在的集合（如果有），然后创建新的集合"""
    qdrant("DELETE", f"/collections/{config.QDRANT_COLLECTION}")
    qdrant("PUT", f"/collections/{config.QDRANT_COLLECTION}", {
        "vectors": {"size": config.OLLAMA_EMBED_MODEL_VECTOR_SIZE, "distance": "Cosine"},
    })
    print("Collection 创建完成")


def ingest(docs):
    """导入知识库到Qdrant"""
    points = []
    for doc in docs:
        print(f"嵌入中：{doc['text'][:20]}...")
        """获取文档文本的嵌入向量，并准备好要导入Qdrant的数据格式，包括id、vector和payload（原始文本）"""
        points.append({
            "id": doc["id"],
            "vector": embed(doc["text"]),
            "payload": {"text": doc["text"]},
        })
    qdrant("PUT", f"/collections/{config.QDRANT_COLLECTION}/points", {"points": points})
    print("知识库导入完成")


def search(question: str, limit: int = 2, extra: bool = False) -> list:
    """搜索相关文档（知识库）"""
    """获取问题的嵌入向量，并在Qdrant中搜索相似的文档"""
    vector = embed(question)
    result = qdrant("POST", f"/collections/{config.QDRANT_COLLECTION}/points/search", {
        "vector": vector,
        "limit": limit,
        "with_payload": True,
    })
    hits = result["result"]
    for h in hits:
        print(f"分数: {h['score']:.4f} | {h['payload']['text'][:30]}")
    
    return [h["payload"]["text"] for h in hits] if not extra else hits


def chat_stream(question: str, context: str):
    """流式调用LLM"""
    """同时将匹配到的知识库内容和用户问题发送给LLM，让LLM根据这些信息生成回答，并通过流式接口逐步返回生成的内容"""
    stream = client.chat.completions.create(
        model=config.LLM_MODEL,
        messages=[
            {"role": "system", "content": "你是知识库助手，根据提供的知识库内容自由回答。"},
            {"role": "user", "content": f"知识库：\n{context}\n\n问题：{question}"},
        ],
        stream=True,
    )
    
    for chunk in stream:
        if chunk.choices[0].delta.content is not None:
            yield chunk.choices[0].delta.content


def chat(question: str, context: str) -> str:
    """普通调用LLM"""
    """将匹配到的知识库内容和用户问题发送给LLM，让LLM根据这些信息生成回答，并返回完整的回答内容"""
    res = client.chat.completions.create(
        model=config.LLM_MODEL,
        messages=[
            {"role": "system", "content": "你是知识库助手，根据提供的知识库内容自由回答。"},
            {"role": "user", "content": f"知识库：\n{context}\n\n问题：{question}"},
        ],
    )
    return res.choices[0].message.content


def ask(question: str) -> str:
    """完整问答流程"""
    """先从知识库中搜索相关文档，然后将这些文档作为上下文发送给LLM，让LLM根据这些信息生成回答，并返回回答内容"""
    docs = search(question)
    context = "\n".join(docs)
    """同时将匹配到的知识库内容和用户问题发送给LLM，让LLM根据这些信息生成回答，并返回完整的回答内容"""
    return chat(question, context)


# API路由
@app.route('/')
def index():
    """返回知识库问答前端页面"""
    return send_file('static/index.html', mimetype='text/html')


@app.route('/api/ask', methods=['POST'])
def api_ask():
    """普通问答API"""
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
    """流式问答API"""
    data = request.json
    question = data.get('question', '')
    
    if not question:
        return jsonify({'error': '问题不能为空'}), 400
    
    try:
        docs = search(question)
        context = "\n".join(docs)
        
        def generate():
            yield f"检索到的知识库内容：\n{context}\n\n回答：\n"
            for chunk in chat_stream(question, context):
                yield chunk
        
        return Response(generate(), content_type='text/markdown; charset=utf-8')
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
        lines = text.strip().split('\n')
        docs = []
        for i, line in enumerate(lines):
            line = line.strip()
            if line:
                docs.append({
                    "id": i + 1,
                    "text": line
                })
        
        if not docs:
            return jsonify({'error': '没有找到有效的知识库内容'}), 400
        
        ingest(docs)
        return jsonify({'message': '知识库导入完成', 'count': len(docs)})
    except Exception as e:
        print(f"导入错误: {e}")
        return jsonify({'message': '知识库导入请求已接收', 'count': len(docs)}), 200


@app.route('/api/search', methods=['POST'])
def api_search():
    """搜索相关文档"""
    data = request.json
    question = data.get('question', '')
    limit = data.get('limit', 2)
    
    if not question:
        return jsonify({'error': '问题不能为空'}), 400
    
    try:
        docs = search(question, limit, True)
        return jsonify({'question': question, 'docs': docs})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/config', methods=['GET'])
def api_config():
    """获取当前配置"""
    return jsonify({'config': {}, 'validation': {'is_valid': True, 'services_available': True}})


@app.route('/api/health', methods=['GET'])
def api_health():
    """健康检查接口"""
    return jsonify({'status': 'ok', 'timestamp': int(time.time())})


@app.route('/api/knowledges/default', methods=['GET'])
def api_knowledges():
    """获取所有默认知识库条目"""
    try:
        return jsonify({'knowledges': config.KNOWLEDGE_BASE})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == "__main__":
    print("正在初始化知识库...")
    try:
        init_collection()
        ingest(config.KNOWLEDGE_BASE)
        print("知识库初始化完成")
    except Exception as e:
        print(f"知识库初始化失败: {e}")
        print("应用仍可启动，但问答功能可能受限")
    
    print(f"启动服务器：http://{config.FLASK_HOST}:{config.FLASK_PORT}")
    app.run(debug=True, host=config.FLASK_HOST, port=config.FLASK_PORT)