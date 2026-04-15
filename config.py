# ollama 
OLLAMA_URL = "http://localhost:11434"
OLLAMA_EMBED_MODEL = "bge-m3"
OLLAMA_EMBED_MODEL_VECTOR_SIZE = 1024  # 嵌入模型的向量维度

# qdrant
QDRANT_URL = "http://localhost:6333"
QDRANT_COLLECTION = "product_kb"  # 知识库集合名称

# llm
LLM_BASE_URL = "https://api.deepseek.com/v1"
LLM_MODEL = "deepseek-chat"
LLM_API_KEY = ""

# flask
FLASK_HOST = "127.0.0.1"
FLASK_PORT = 5000

# knowledge base
KNOWLEDGE_BASE = [
    {"id": 1, "text": "退款流程：在订单页面点击申请退款，填写原因，3个工作日内处理完成。"},
    {"id": 2, "text": "发货时间：下单后24小时内发货，节假日顺延。"},
    {"id": 3, "text": "保修政策：产品自购买日起享有一年免费保修服务。"},
]
