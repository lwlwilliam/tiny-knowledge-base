import requests
import config
import sys

def test_api():
    base_url = f"http://{config.FLASK_HOST}:{config.FLASK_PORT}"
    
    print("测试知识库问答系统 API...")
    print("=" * 50)
    
    # 测试首页
    print("1. 测试首页...")
    try:
        response = requests.get(base_url)
        if response.status_code == 200:
            print("   ✓ 首页访问成功")
        else:
            print(f"   ✗ 首页访问失败: {response.status_code}")
    except Exception as e:
        print(f"   ✗ 首页访问异常: {e}")
        return False
    
    # 测试普通问答 API
    print("\n2. 测试普通问答 API...")
    try:
        response = requests.post(
            f"{base_url}/api/ask",
            json={"question": "我想退款，怎么操作？"},
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ 普通问答 API 成功")
            print(f"   问题: {data.get('question')}")
            print(f"   回答长度: {len(data.get('answer', ''))} 字符")
        else:
            print(f"   ✗ 普通问答 API 失败: {response.status_code}")
            print(f"   响应: {response.text}")
    except Exception as e:
        print(f"   ✗ 普通问答 API 异常: {e}")
    
    # 测试流式问答 API
    print("\n3. 测试流式问答 API...")
    try:
        response = requests.post(
            f"{base_url}/api/ask/stream",
            json={"question": "发货时间是多少？"},
            headers={"Content-Type": "application/json"},
            stream=True
        )
        if response.status_code == 200:
            print("   ✓ 流式问答 API 连接成功")
            print("   流式响应内容:")
            content = ""
            for chunk in response.iter_content(chunk_size=1024, decode_unicode=True):
                if chunk:
                    content += chunk
                    sys.stdout.write(chunk)
                    sys.stdout.flush()
            print(f"\n   总响应长度: {len(content)} 字符")
        else:
            print(f"   ✗ 流式问答 API 失败: {response.status_code}")
            print(f"   响应: {response.text}")
    except Exception as e:
        print(f"   ✗ 流式问答 API 异常: {e}")
    
    # 测试搜索 API
    print("\n4. 测试搜索 API...")
    try:
        response = requests.post(
            f"{base_url}/api/search",
            json={"question": "保修政策", "limit": 3},
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ 搜索 API 成功")
            print(f"   问题: {data.get('question')}")
            print(f"   找到 {len(data.get('docs', []))} 个相关文档:")
            for i, doc in enumerate(data.get('docs', [])):
                if doc.get("payload"):
                    print(f"     {i+1}. {doc['payload']['text'][:50]}...")
                else:
                    print(f"     {i+1}. {doc[:50]}...")
        else:
            print(f"   ✗ 搜索 API 失败: {response.status_code}")
    except Exception as e:
        print(f"   ✗ 搜索 API 异常: {e}")
    
    print("\n" + "=" * 50)
    print("测试完成!")
    return True

if __name__ == "__main__":
    test_api()
