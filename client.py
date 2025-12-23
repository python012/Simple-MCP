"""
MCP 客户端 - 与阿里云 Qwen 和 MCP 服务器交互
使用自然语言查询用户数据库
"""

import asyncio
import json
import os
from typing import Dict, Any

from openai import OpenAI
import httpx
from dotenv import load_dotenv

# 导入 MCP 客户端库
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession
from mcp.types import TextContent

# 加载环境变量
load_dotenv()

# 1. 配置
QWEN_MODEL = "qwen-flash"

# 优先使用 ALIYUN_MODEL_API_KEY，其次兼容 OPENAI_API_KEY 环境变量
_api_key = os.getenv("ALIYUN_MODEL_API_KEY") or os.getenv("OPENAI_API_KEY")

# 使用自定义 httpx.Client 关闭系统代理，避免握手超时
_http_client = httpx.Client(
    trust_env=False,  # 忽略系统环境代理/证书设置
    timeout=httpx.Timeout(connect=30.0, read=60.0, write=30.0, pool=30.0),
)

client = OpenAI(
    api_key=_api_key,
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    max_retries=3,
    http_client=_http_client,
)


async def call_mcp_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    调用 MCP 服务器的工具

    Args:
        tool_name: 工具名称
        arguments: 工具参数

    Returns:
        工具执行结果
    """
    # 配置 MCP 服务器参数
    server_params = StdioServerParameters(
        command="python",
        args=["mcp_server.py"],
    )
    
    try:
        # 使用 async with 确保资源正确管理
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                # 初始化连接
                await session.initialize()
                
                # 调用工具
                result = await session.call_tool(tool_name, arguments)
                
                # 提取工具返回的内容
                if hasattr(result, 'content') and result.content:
                    # 获取第一个文本内容
                    for content_item in result.content:
                        if isinstance(content_item, TextContent):
                            content_text = content_item.text
                            # 尝试解析 JSON
                            try:
                                return json.loads(content_text)
                            except:
                                return {"result": content_text}
                    # 如果没有找到文本内容
                    return {"result": str(result)}
                else:
                    return {"result": str(result)}
                    
    except Exception as e:
        print(f"❌ 调用工具时出错: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


class NaturalLanguageQuery:
    """自然语言查询处理器"""

    def __init__(self):
        pass

    async def _get_tool_decision(self, question: str) -> str:
        """
        让 LLM 决定是否需要调用工具以及如何调用

        Args:
            question: 用户的自然语言问题

        Returns:
            包含工具调用决策的 JSON 字符串
        """
        system_prompt = """你是一个智能助手，可以帮助用户查询用户数据库。
        
可用的工具：
1. query_users - 根据条件查询多个用户
   参数：
   - name: 按姓名模糊查询（可选）
   - min_age: 最小年龄（可选）
   - max_age: 最大年龄（可选）
   - email_contains: 邮箱包含的字符串（可选）

2. get_user_by_id - 根据ID获取单个用户
   参数：
   - user_id: 用户ID（必需）

当用户询问用户信息时，你应该：
1. 分析用户的问题，判断需要哪个工具
2. 提取相关参数
3. 以严格的 JSON 格式返回工具调用信息

JSON 格式：
{
  "tool": "工具名称",
  "arguments": {
    "参数1": "值1",
    "参数2": "值2"
  }
}

如果问题不需要查询数据库，直接回答问题，不要返回 JSON。
"""

        response = client.chat.completions.create(
            model=QWEN_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question}
            ],
            # DashScope 兼容模式可能不支持 response_format，改为通过提示约束
            temperature=0,
        )

        return response.choices[0].message.content or ""

    async def query(self, question: str) -> str:
        """
        处理自然语言查询

        Args:
            question: 用户的自然语言问题

        Returns:
            AI 生成的回答
        """
        try:
            # 第一步：让 LLM 决定是否需要调用工具
            tool_decision_str = await self._get_tool_decision(question)
            print(f"🧠 LLM 决策: {tool_decision_str}")

            # 尝试解析 JSON
            try:
                tool_decision = json.loads(tool_decision_str)

                # 检查是否包含工具调用信息
                if "tool" in tool_decision and "arguments" in tool_decision:
                    tool_name = tool_decision["tool"]
                    arguments = tool_decision["arguments"]

                    print(f"🔧 调用工具: {tool_name}")
                    print(f"📊 工具参数: {arguments}")

                    # 调用 MCP 工具
                    tool_result = await call_mcp_tool(tool_name, arguments)
                    print(f"✅ 工具结果: {tool_result}")

                    # 第二步：让 LLM 根据工具结果生成最终回答
                    final_response = client.chat.completions.create(
                        model=QWEN_MODEL,
                        messages=[
                            {
                                "role": "system",
                                "content": "你是一个智能助手，根据工具返回的数据回答用户问题。使用中文回答，格式清晰。",
                            },
                            {
                                "role": "user",
                                "content": f"问题: {question}\n工具结果: {json.dumps(tool_result, ensure_ascii=False, indent=2)}",
                            },
                        ],
                        temperature=0.2,
                    )
                    return final_response.choices[0].message.content or ""

            except json.JSONDecodeError:
                # 不是有效的 JSON，直接返回 LLM 的回答
                pass

            # 如果没有工具调用，直接返回 LLM 的回答
            return tool_decision_str

        except Exception as e:
            return f"❌ 处理查询时出错: {str(e)}"


async def main():
    """主函数"""
    print("💬 智能用户查询助手 (MCP + 阿里云 Qwen)")
    print("✅ 已连接到阿里云 Qwen (qwen-flash)")
    print("❓ 输入你的问题，输入 'exit' 退出")
    print("-" * 50)

    # 创建查询处理器
    query_processor = NaturalLanguageQuery()

    while True:
        question = input("\n👤 你: ")
        if question.lower() == "exit":
            break

        print("🤖 AI 思考中...", end="", flush=True)

        try:
            # 处理查询
            answer = await query_processor.query(question)
            print(f"\n🤖 AI: {answer}")
        except Exception as e:
            print(f"\n❌ 错误: {str(e)}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
