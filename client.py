"""
MCP 客户端 - 与 Ollama 本地大模型和 MCP 服务器交互
使用自然语言查询用户数据库
"""

import asyncio
import json
from typing import Dict, Any, Optional
from datetime import datetime
import os
from pathlib import Path

from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

# 导入 MCP 客户端库
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession
from mcp.types import TextContent

# 1. 配置
OLLAMA_MODEL = "qwen3:14b"
OLLAMA_BASE_URL = "http://localhost:11434/v1"

# 创建 Ollama OpenAI 兼容客户端
client = OpenAI(
    api_key="ollama",  # Ollama 不需要真实的 API KEY
    base_url=OLLAMA_BASE_URL,
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
    import subprocess
    
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
                if hasattr(result, "content") and result.content:
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
        print(f"调用工具时出错: {e}")
        import traceback

        traceback.print_exc()
        return {"error": str(e)}


class NaturalLanguageQuery:
    """自然语言查询处理器"""

    def __init__(self):
        self.last_log_position = 0  # 记录上次读取日志文件的位置

    def _read_and_display_server_logs(self):
        """读取并显示 MCP 服务器日志文件中的新内容"""
        log_file = Path("mcp_server.log")
        
        if not log_file.exists():
            return
        
        try:
            file_size = log_file.stat().st_size
            
            # 如果文件有新内容，读取新增部分
            if file_size > self.last_log_position:
                with open(log_file, "r", encoding="utf-8") as f:
                    f.seek(self.last_log_position)
                    new_content = f.read()
                    
                    if new_content.strip():
                        print(f"\n[MCP 服务器日志]:")
                        print(new_content, end="")
                
                self.last_log_position = file_size
        except Exception as e:
            pass  # 静默处理读取失败

    def _convert_arguments(self, tool_name: str, arguments: dict) -> dict:
        """
        转换和验证工具参数的类型

        Args:
            tool_name: 工具名称
            arguments: 原始参数字典

        Returns:
            转换后的参数字典
        """
        converted = {}

        if tool_name == "query_users":
            # 移除 None 值和不存在的参数
            for key in ["name", "min_age", "max_age", "age_greater_than", "age_less_than", "email_contains"]:
                if key in arguments and arguments[key] is not None:
                    if key in ["min_age", "max_age", "age_greater_than", "age_less_than"]:
                        # 转换为整数
                        try:
                            converted[key] = int(arguments[key])
                        except (ValueError, TypeError):
                            print(f"[警告] {key} 无法转换为整数，跳过该参数")
                    else:
                        # name 和 email_contains 保持为字符串
                        converted[key] = str(arguments[key])

        elif tool_name in ["get_user_by_id", "get_user_relationships", "get_spouse", 
                           "get_relatives_by_relation", "get_children", "get_parents"]:
            # user_id 必须是整数
            if "user_id" in arguments:
                try:
                    converted["user_id"] = int(arguments["user_id"])
                except (ValueError, TypeError):
                    print(f"[警告] user_id 无法转换为整数")
                    converted["user_id"] = arguments["user_id"]
            
            # relation_type 保持为字符串（用于 get_relatives_by_relation）
            if "relation_type" in arguments and arguments["relation_type"] is not None:
                converted["relation_type"] = str(arguments["relation_type"])

        elif tool_name == "get_relationship_between_users":
            # user1_id 和 user2_id 必须是整数
            for key in ["user1_id", "user2_id"]:
                if key in arguments:
                    try:
                        converted[key] = int(arguments[key])
                    except (ValueError, TypeError):
                        print(f"[警告] {key} 无法转换为整数")
                        converted[key] = arguments[key]

        return converted if converted else arguments

    async def _get_tool_decision(self, question: str, conversation_history: Optional[list] = None) -> str:
        """
        让 LLM 决定是否需要调用工具以及如何调用

        Args:
            question: 用户的自然语言问题
            conversation_history: 之前的工具调用历史

        Returns:
            包含工具调用决策的 JSON 字符串，或者最终答案
        """
        system_prompt = """你是一个智能助手，可以帮助用户查询用户数据库和用户关系网络。

重要：你可以进行多次工具调用来收集信息，逐步回答用户问题。

可用的工具：

1. query_users - 根据条件查询多个用户
   参数：
   - name: 按姓名模糊查询（可选，字符串类型）
   - min_age: 最小年龄，包含边界，即 >= min_age（可选，整数类型）
   - max_age: 最大年龄，包含边界，即 <= max_age（可选，整数类型）
   - age_greater_than: 年龄大于，不包含边界，即 > age_greater_than（可选，整数类型）
   - age_less_than: 年龄小于，不包含边界，即 < age_less_than（可选，整数类型）
   - email_contains: 邮箱包含的字符串（可选，字符串类型）

2. get_user_by_id - 根据ID获取单个用户信息
   参数：
   - user_id: 用户ID（必需，整数类型）

3. get_user_relationships - 查询某个用户的所有关系
   参数：
   - user_id: 用户ID（必需，整数类型）

4. get_relationship_between_users - 查询两个用户之间的关系
   参数：
   - user1_id: 第一个用户ID（必需，整数类型）
   - user2_id: 第二个用户ID（必需，整数类型）

5. get_spouse - 查询某个用户的配偶（丈夫或妻子）
   参数：
   - user_id: 用户ID（必需，整数类型）

6. get_relatives_by_relation - 查询某个用户的特定类型亲戚
   参数：
   - user_id: 用户ID（必需，整数类型）
   - relation_type: 关系类型（可选，字符串类型，如"父子"、"母女"、"兄妹"等）

7. get_children - 查询某个用户的所有子女
   参数：
   - user_id: 用户ID（必需，整数类型）

8. get_parents - 查询某个用户的父母
   参数：
   - user_id: 用户ID（必需，整数类型）

工作流程：
1. 如果需要调用工具，返回 JSON 格式：{"tool": "工具名称", "arguments": {...}}
2. 如果已经有足够信息回答问题，直接返回答案文本（不要返回 JSON）
3. 你可以根据需要多次调用工具，每次调用后会收到结果，然后决定下一步

JSON 格式示例：
{
  "tool": "工具名称",
  "arguments": {
    "参数名": 参数值
  }
}

重要提示：
- 整数参数（如 user_id、min_age、max_age 等）必须是数字，不要加引号
- 字符串参数（如 name、email_contains、relation_type）要加引号
- 不需要的参数省略即可
- 如果已经有足够信息，直接输出答案，不要返回 JSON
- 问题不需要查询数据库时，直接回答，不要返回 JSON
"""

        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": system_prompt},
        ]
        
        # 构建用户消息，包含历史工具调用信息
        if conversation_history and len(conversation_history) > 0:
            # 有历史调用，构建完整上下文
            user_message = f"用户问题: {question}\n\n"
            user_message += "已执行的工具调用历史:\n"
            for idx, h in enumerate(conversation_history, 1):
                user_message += f"\n第 {idx} 次调用:\n"
                user_message += f"  工具: {h['tool']}\n"
                user_message += f"  参数: {json.dumps(h['arguments'], ensure_ascii=False)}\n"
                user_message += f"  结果: {json.dumps(h['result'], ensure_ascii=False, indent=2)}\n"
            user_message += "\n基于以上信息，你需要继续调用工具还是可以给出最终答案？"
            messages.append({"role": "user", "content": user_message})
        else:
            # 第一次调用
            messages.append({"role": "user", "content": question})

        # 打印完整的提示词
        print(f"\n" + "=" * 70)
        iteration_num = len(conversation_history) + 1 if conversation_history else 1
        print(f"[发给 LLM 的原始请求文本 - 第 {iteration_num} 轮]")
        print(f"=" * 70)
        print(f"System: {system_prompt}")
        print(f"\nUser: {messages[-1].get('content', '')}")
        print(f"=" * 70)

        response = client.chat.completions.create(
            model=OLLAMA_MODEL,
            messages=messages,
            temperature=0,
        )

        llm_response = response.choices[0].message.content or ""

        # 打印 LLM 的原始回答
        iteration_num = len(conversation_history) + 1 if conversation_history else 1
        print(f"\n🤖 [来自 LLM 的原始响应文本 - 第 {iteration_num} 轮]:")
        print(f"{llm_response}")
        print(f"=" * 70)

        return llm_response

    async def query(self, question: str) -> str:
        """
        处理自然语言查询，支持多轮工具调用

        Args:
            question: 用户的自然语言问题

        Returns:
            AI 生成的回答
        """
        try:
            start_time = datetime.now()
            print(f"[{start_time.strftime('%H:%M:%S')}] 开始处理问题")

            # 保存工具调用历史
            conversation_history = []
            max_iterations = 10  # 最大迭代次数，防止无限循环
            iteration = 0

            while iteration < max_iterations:
                iteration += 1
                print(f"\n{'='*70}")
                print(f"[第 {iteration} 轮工具决策]")
                print(f"{'='*70}")

                # 让 LLM 决定是否需要调用工具
                decision_start = datetime.now()
                print(f"[{decision_start.strftime('%H:%M:%S')}] 向 LLM 发送请求")

                tool_decision_str = await self._get_tool_decision(question, conversation_history)

                decision_end = datetime.now()
                decision_time = (decision_end - decision_start).total_seconds()
                print(f"[{decision_end.strftime('%H:%M:%S')}] LLM 响应完成 (耗时: {decision_time:.2f}秒)")

                # 尝试解析 JSON
                try:
                    tool_decision = json.loads(tool_decision_str)

                    # 检查是否包含工具调用信息
                    if "tool" in tool_decision and "arguments" in tool_decision:
                        tool_name = tool_decision["tool"]
                        arguments = tool_decision["arguments"]

                        # 转换参数类型
                        arguments = self._convert_arguments(tool_name, arguments)

                        print(f"\n[工具调用] {tool_name}")
                        print(f"[工具参数] {arguments}")

                        # 调用 MCP 工具
                        tool_start = datetime.now()
                        print(f"[{tool_start.strftime('%H:%M:%S')}] 开始调用 MCP 工具")

                        tool_result = await call_mcp_tool(tool_name, arguments)

                        tool_end = datetime.now()
                        tool_time = (tool_end - tool_start).total_seconds()
                        print(f"[{tool_end.strftime('%H:%M:%S')}] 工具调用完成 (耗时: {tool_time:.2f}秒)")
                        print(f"[工具结果] {json.dumps(tool_result, ensure_ascii=False, indent=2)}")

                        # 显示 MCP 服务器的日志
                        self._read_and_display_server_logs()

                        # 保存到历史记录
                        conversation_history.append({
                            "tool": tool_name,
                            "arguments": arguments,
                            "result": tool_result
                        })

                        # 继续下一轮
                        continue

                except json.JSONDecodeError:
                    # 不是有效的 JSON，说明 LLM 给出了最终答案
                    pass

                # LLM 没有返回工具调用，而是返回了最终答案
                if conversation_history:
                    # 有工具调用历史，LLM 的回答是基于这些信息的最终答案
                    total_time = (datetime.now() - start_time).total_seconds()
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] LLM 给出最终答案")
                    print(f"[总耗时] {total_time:.2f}秒")
                    print(f"[工具调用次数] {len(conversation_history)}")
                    return tool_decision_str
                else:
                    # 没有工具调用历史，直接返回 LLM 的回答
                    total_time = (datetime.now() - start_time).total_seconds()
                    print(f"[总耗时] {total_time:.2f}秒")
                    return tool_decision_str

            # 达到最大迭代次数
            print(f"\n[警告] 达到最大迭代次数 ({max_iterations})")
            if conversation_history:
                return f"抱歉，经过 {len(conversation_history)} 次工具调用后，问题仍然过于复杂。已收集的信息可能不足以完整回答您的问题，请尝试简化问题或分步询问。"
            else:
                return "抱歉，无法处理您的问题。"

        except Exception as e:
            return f"处理查询时出错: {str(e)}"


async def main():
    """主函数"""
    print("智能用户查询助手 (MCP + Ollama 本地大模型)")
    print(f"已连接到 Ollama 本地模型 ({OLLAMA_MODEL})")
    print("输入问题开始查询，输入 'exit' 退出")
    print("-" * 70)

    # 创建查询处理器
    query_processor = NaturalLanguageQuery()

    while True:
        question = input("\n👤 你: ")
        if question.lower() == "exit":
            break

        question_time = datetime.now()
        print(f"[{question_time.strftime('%H:%M:%S')}] 收到问题")

        try:
            # 处理查询
            answer = await query_processor.query(question)
            print(f"\n🤖 AI 发给用户的回答: {answer}")
        except Exception as e:
            print(f"\n错误: {str(e)}")
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
