"""
知识库命令行工具
提供命令行界面来管理知识库
"""

import argparse
import sys
import json
import requests
import config


class KnowledgeBaseCLI:
    """知识库命令行工具类"""
    
    def __init__(self, base_url: str = f"http://{config.FLASK_HOST}:{config.FLASK_PORT}"):
        self.base_url = base_url
    
    def health_check(self) -> bool:
        """健康检查"""
        try:
            response = requests.get(f"{self.base_url}/api/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print("✅ 服务健康状态:")
                print(f"   状态: {data.get('status')}")
                print(f"   时间: {data.get('timestamp')}")
                
                services = data.get('services', [])
                for service in services:
                    status_icon = "✅" if service.get('status') == 'healthy' else "❌"
                    print(f"   {status_icon} {service.get('service')}: {service.get('message')}")
                
                return True
            else:
                print(f"❌ 服务不可用: HTTP {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ 连接失败: {e}")
            return False
    
    def ask_question(self, question: str, stream: bool = False) -> None:
        """提问"""
        if not question:
            print("❌ 问题不能为空")
            return
        
        try:
            if stream:
                print("🔍 正在流式回答...")
                response = requests.post(
                    f"{self.base_url}/api/ask/stream",
                    json={"question": question},
                    stream=True,
                    timeout=30
                )
                
                if response.status_code == 200:
                    for chunk in response.iter_content(chunk_size=1024, decode_unicode=True):
                        if chunk:
                            sys.stdout.write(chunk)
                            sys.stdout.flush()
                    print()
                else:
                    print(f"❌ 请求失败: HTTP {response.status_code}")
            else:
                print("🔍 正在获取回答...")
                response = requests.post(
                    f"{self.base_url}/api/ask",
                    json={"question": question},
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"\n📝 问题: {data.get('question')}")
                    print(f"💡 回答: {data.get('answer')}")
                else:
                    print(f"❌ 请求失败: HTTP {response.status_code}")
                    print(f"   错误: {response.text}")
        
        except requests.exceptions.Timeout:
            print("❌ 请求超时，请稍后重试")
        except requests.exceptions.RequestException as e:
            print(f"❌ 请求失败: {e}")
    
    def init_knowledge_base(self) -> None:
        """初始化知识库"""
        try:
            print("🔄 正在初始化知识库...")
            response = requests.post(f"{self.base_url}/api/init", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ {data.get('message')}")
            else:
                print(f"❌ 初始化失败: HTTP {response.status_code}")
                print(f"   错误: {response.text}")
        
        except requests.exceptions.RequestException as e:
            print(f"❌ 请求失败: {e}")
    
    def ingest_documents(self, file_path: str = None, text: str = None) -> None:
        """导入文档"""
        try:
            if file_path:
                print(f"📄 正在从文件导入: {file_path}")
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 尝试解析为JSON
                try:
                    data = json.loads(content)
                    if isinstance(data, list):
                        docs = data
                        endpoint = "/api/ingest"
                        payload = {"docs": docs}
                    else:
                        raise ValueError("文件内容不是有效的文档列表")
                except json.JSONDecodeError:
                    # 如果不是JSON，当作纯文本处理
                    endpoint = "/api/ingest/text"
                    payload = {"text": content}
            
            elif text:
                print("📝 正在导入文本...")
                endpoint = "/api/ingest/text"
                payload = {"text": text}
            else:
                print("❌ 请提供文件路径或文本内容")
                return
            
            response = requests.post(
                f"{self.base_url}{endpoint}",
                json=payload,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                print(f"✅ {data.get('message')}")
                
                if 'total_received' in data:
                    print(f"   接收文档: {data.get('total_received')}")
                    print(f"   验证通过: {data.get('validated')}")
                    print(f"   成功导入: {data.get('ingested')}")
                elif 'lines_received' in data:
                    print(f"   接收行数: {data.get('lines_received')}")
                    print(f"   创建文档: {data.get('documents_created')}")
                    print(f"   成功导入: {data.get('documents_ingested')}")
                elif 'count' in data:
                    print(f"   导入文档: {data.get('count')}")
                
                if 'warning' in data:
                    print(f"   ⚠️ 警告: {data.get('warning')}")
            
            else:
                print(f"❌ 导入失败: HTTP {response.status_code}")
                print(f"   错误: {response.text}")
        
        except FileNotFoundError:
            print(f"❌ 文件不存在: {file_path}")
        except Exception as e:
            print(f"❌ 导入失败: {e}")
    
    def search_documents(self, question: str, limit: int = 5) -> None:
        """搜索文档"""
        try:
            print(f"🔍 正在搜索: {question}")
            response = requests.post(
                f"{self.base_url}/api/search",
                json={"question": question, "limit": limit},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"📊 搜索结果 (共 {len(data.get('docs'))} 个):")
                
                docs = data.get('docs', [])
                for i, doc in enumerate(docs, 1):
                    print(f"\n  {i}. 相关度: {doc.get('score', 0):.4f}")

                    payload = doc.get('payload', {})
                    if payload:
                        print(f"     内容: {payload.get('text', '')[:100]}...")
                    else:
                        print(f"     内容: ")
                    
                    metadata = doc.get('metadata', {})
                    if metadata:
                        print(f"     元数据: {metadata}")
            else:
                print(f"❌ 搜索失败: HTTP {response.status_code}")
                print(f"   错误: {response.text}")
        
        except requests.exceptions.RequestException as e:
            print(f"❌ 请求失败: {e}")
    
    def get_config(self) -> None:
        """获取配置"""
        try:
            print("⚙️ 正在获取配置...")
            response = requests.get(f"{self.base_url}/api/config", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                config_data = data.get('config', {})
                validation = data.get('validation', {})
                
                print("📋 配置信息:")
                for key, value in config_data.items():
                    print(f"   {key}: {value}")
                
                print(f"\n✅ 配置验证: {'通过' if validation.get('is_valid') else '失败'}")
                print(f"   🔧 服务可用性: {'可用' if validation.get('services_available') else '不可用'}")
            
            else:
                print(f"❌ 获取配置失败: HTTP {response.status_code}")
        
        except requests.exceptions.RequestException as e:
            print(f"❌ 请求失败: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="知识库命令行工具")
    parser.add_argument("--url", default=f"http://{config.FLASK_HOST}:{config.FLASK_PORT}", help="API服务器地址")
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # 健康检查命令
    subparsers.add_parser("health", help="健康检查")
    
    # 提问命令
    ask_parser = subparsers.add_parser("ask", help="提问")
    ask_parser.add_argument("question", help="问题内容")
    ask_parser.add_argument("--stream", action="store_true", help="使用流式响应")
    
    # 初始化命令
    subparsers.add_parser("init", help="初始化知识库")
    
    # 导入命令
    ingest_parser = subparsers.add_parser("ingest", help="导入文档")
    ingest_group = ingest_parser.add_mutually_exclusive_group(required=True)
    ingest_group.add_argument("--file", help="文件路径")
    ingest_group.add_argument("--text", help="文本内容")
    
    # 搜索命令
    search_parser = subparsers.add_parser("search", help="搜索文档")
    search_parser.add_argument("question", help="搜索问题")
    search_parser.add_argument("--limit", type=int, default=5, help="结果数量限制")
    
    # 配置命令
    subparsers.add_parser("config", help="获取配置")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    cli = KnowledgeBaseCLI(args.url)
    
    try:
        if args.command == "health":
            cli.health_check()
        
        elif args.command == "ask":
            cli.ask_question(args.question, args.stream)
        
        elif args.command == "init":
            cli.init_knowledge_base()
        
        elif args.command == "ingest":
            cli.ingest_documents(args.file, args.text)
        
        elif args.command == "search":
            cli.search_documents(args.question, args.limit)
        
        elif args.command == "config":
            cli.get_config()
    
    except KeyboardInterrupt:
        print("\n\n⏹️ 操作已取消")
    except Exception as e:
        print(f"❌ 发生错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()