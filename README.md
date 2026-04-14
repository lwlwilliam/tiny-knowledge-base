# 小型 AI 知识库

用于理解`AI`知识库的实现原理。

## 技术栈

* flask 框架
* qdrant 向量数据库
* ollama 运行的 bge-m3 嵌入模型
* deepseek api

## 特性

* 支持流式输出和普通输出
* 支持导入纯文本知识

## 安装运行

```bash
ollama pull bge-m3
ollama serve
docker run -d -ti --name=qdrant -p 6333:6333 qdrant/qdran
pip3 install -r requirements.txt
export LLM_API_KEY=   # 将 deepseek 的 api key 填到 LLM_API_KEY 中
python3 app.py
```

