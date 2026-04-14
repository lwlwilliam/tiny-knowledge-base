# AI 知识库问答系统

一个基于 Python 的 AI 知识库问答系统，使用 Flask 框架、Qdrant 向量数据库、BGE-M3 嵌入模型和 LLM 实现智能问答。

## 🚀 特性

- **智能问答**: 基于知识库的智能问答系统
- **流式输出**: 支持流式响应和普通响应两种模式
- **多格式导入**: 支持 JSON 和纯文本格式的知识库导入
- **RESTful API**: 提供完整的 RESTful API 接口
- **命令行工具**: 提供便捷的命令行管理工具
- **配置管理**: 集中化的配置管理系统
- **异常处理**: 完善的异常处理和错误提示
- **健康检查**: 系统健康状态监控

## 🏗️ 技术栈

### 后端

- **Python 3.12**: 主要编程语言
- **Flask**: Web 框架
- **Docker**: 提供向量数据库容器服务
- **Qdrant**: 向量数据库
- **Ollama**: 本地嵌入模型服务
- **BGE-M3**: 嵌入模型
- **DeepSeek API**: LLM 服务接口

## 📁 项目结构

```
knowledge_base/
├── app.py              # 主应用文件
├── cli.py              # 命令行工具
├── config.py           # 配置管理
├── test_api.py         # API 测试
├── requirements.txt    # 依赖包
├── README.md           # 项目说明
└── static/
    └── index.html      # 前端页面
```

## 🛠️ 安装运行

### 1. 环境准备

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 启动 Ollama 服务（用于文本嵌入）
ollama pull bge-m3
ollama serve

# 启动 Qdrant 向量数据库
docker run -d -ti --name=qdrant -p 6333:6333 qdrant/qdrant
```

### 2. 配置

详情查看 config.py。

### 3. 启动服务

```bash
# 启动 Flask 应用
python app.py
```

服务将在 http://localhost:5000 启动。

## 📚 使用指南

### 命令行工具

```bash
# 健康检查
python cli.py health

# 提问（普通模式）
python cli.py ask "我想退款，怎么操作？"

# 提问（流式模式）
python cli.py ask --stream "发货需要多长时间？"

# 初始化知识库
python cli.py init

# 导入知识库（从文件）
python cli.py ingest --file examples.json

# 导入知识库（从文本）
python cli.py ingest --text "第一行知识\n第二行知识"

# 搜索相关文档
python cli.py search "保修政策" --limit 3

# 获取配置信息
python cli.py config
```

### API 接口

#### 健康检查

```http
GET /api/health
```

#### 普通问答

```http
POST /api/ask
Content-Type: application/json

{
  "question": "我想退款，怎么操作？"
}
```

#### 流式问答

```http
POST /api/ask/stream
Content-Type: application/json

{
  "question": "发货需要多长时间？"
}
```

#### 初始化知识库

```http
POST /api/init
```

#### 导入知识库（JSON格式）

```http
POST /api/ingest
Content-Type: application/json

{
  "docs": [
    {
      "id": 1,
      "text": "退款流程：在订单页面点击申请退款，填写原因，3个工作日内处理完成。",
      "metadata": {"category": "售后"}
    }
  ]
}
```

#### 导入知识库（纯文本格式）

```http
POST /api/ingest/text
Content-Type: application/json

{
  "text": "第一行知识\n第二行知识"
}
```

#### 搜索相关文档

```http
POST /api/search
Content-Type: application/json

{
  "question": "保修政策",
  "limit": 5
}
```

#### 获取配置

```http
GET /api/config
```

## 🧪 测试

### API 测试

```bash
python test_api.py
```

## 🐛 故障排除

### 常见问题

1. **服务无法启动**
   - 检查 Ollama 是否运行：`curl http://localhost:11434`
   - 检查 Qdrant 是否运行：`curl http://localhost:6333`

2. **嵌入失败**
   - 确认 Ollama 已安装 bge-m3 模型：`ollama list`
   - 检查网络连接

3. **LLM 调用失败**
   - 确认 API 密钥已设置
   - 检查 API 密钥是否有余额

4. **导入失败**
   - 检查文档格式是否正确
   - 确认向量数据库服务正常

### 日志查看

应用会输出详细日志，包括：

- 配置信息
- 服务状态
- 请求处理
- 错误信息
