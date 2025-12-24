"""
MCP 服务器 - 使用官方 mcp 库实现
提供用户数据库查询工具
"""

import json
import sys
import shutil
from typing import Dict, Any, List, Optional, TypedDict
from pydantic import BaseModel, Field, ConfigDict
from mcp.server.fastmcp import FastMCP, Context
from mcp.server.session import ServerSession
from mcp.types import TextContent, CallToolResult


# 1. 定义我们的用户数据
USERS = {
    1: {"id": 1, "name": "Alice", "email": "alice@example.com", "age": 30},
    2: {"id": 2, "name": "Bob", "email": "bob@example.com", "age": 25},
    3: {"id": 3, "name": "Charlie", "email": "charlie@example.com", "age": 35},
    4: {"id": 4, "name": "David", "email": "david.wilson@example.com", "age": 28},
    5: {"id": 5, "name": "Emma", "email": "emma.johnson@example.com", "age": 32},
    6: {"id": 6, "name": "Frank", "email": "frank.smith@example.com", "age": 27},
    7: {"id": 7, "name": "Grace", "email": "grace.lee@example.com", "age": 31},
    8: {"id": 8, "name": "Henry", "email": "henry.brown@example.com", "age": 29},
    9: {"id": 9, "name": "Ivy", "email": "ivy.martinez@example.com", "age": 26},
    10: {"id": 10, "name": "Jack", "email": "jack.taylor@example.com", "age": 33},
    11: {"id": 11, "name": "Karen", "email": "karen.anderson@example.com", "age": 28},
    12: {"id": 12, "name": "Leo", "email": "leo.thompson@example.com", "age": 30},
    13: {"id": 13, "name": "Mia", "email": "mia.garcia@example.com", "age": 25},
}


# 2. 定义查询参数的结构
class QueryUsersParams(BaseModel):
    """查询用户的参数"""
    
    model_config = ConfigDict(extra='ignore')

    name: Optional[str] = None
    min_age: Optional[int] = None
    max_age: Optional[int] = None
    age_greater_than: Optional[int] = None
    age_less_than: Optional[int] = None
    email_contains: Optional[str] = None


# 3. 定义返回结果的结构
class UserResult(TypedDict):
    """单个用户结果"""

    id: int
    name: str
    email: str
    age: int


class QueryUsersResult(BaseModel):
    """查询结果"""

    status: str = "success"
    count: int
    users: List[UserResult]


# 4. 创建 MCP 服务器
mcp = FastMCP("UserDatabaseServer", instructions="提供用户数据库查询服务")


# 5. 定义查询工具
@mcp.tool()
async def query_users(
    name: Optional[str] = None,
    min_age: Optional[int] = None,
    max_age: Optional[int] = None,
    age_greater_than: Optional[int] = None,
    age_less_than: Optional[int] = None,
    email_contains: Optional[str] = None,
) -> QueryUsersResult:
    """
    根据多种条件灵活查询用户信息。支持按姓名、年龄范围、邮箱等进行过滤，可组合多个条件进行高级查询。

    Args:
        name (Optional[str]): 按姓名模糊查询，不区分大小写
        min_age (Optional[int]): 最小年龄（包含），用于年龄范围查询的下界，即 >= min_age
        max_age (Optional[int]): 最大年龄（包含），用于年龄范围查询的上界，即 <= max_age
        age_greater_than (Optional[int]): 年龄大于指定值（不包含），即 > age_greater_than
        age_less_than (Optional[int]): 年龄小于指定值（不包含），即 < age_less_than
        email_contains (Optional[str]): 邮箱包含的字符串，模糊匹配，不区分大小写

    Returns:
        QueryUsersResult: 查询结果对象
            - status (str): 查询状态，成功返回 "success"
            - count (int): 匹配的用户数量
            - users (List[UserResult]): 符合条件的用户列表

    Examples:
        # 示例1: 按姓名查询
        >>> await query_users(name="Alice")
        # 返回所有包含 "Alice" 的用户

        # 示例2: 按年龄范围查询
        >>> await query_users(min_age=25, max_age=30)
        # 返回年龄在 25-30 之间的所有用户

        # 示例3: 组合条件查询（姓名 + 年龄范围）
        >>> await query_users(name="David", min_age=27, max_age=32)
        # 返回名字包含 "David" 且年龄在 27-32 之间的用户

        # 示例4: 按邮箱域名查询
        >>> await query_users(email_contains="@example.com")
        # 返回所有邮箱包含 "@example.com" 的用户

        # 示例5: 查询所有用户
        >>> await query_users()
        # 返回所有用户

        # 示例6: 按年龄下界查询（不包含边界）
        >>> await query_users(age_greater_than=30)
        # 返回所有年龄大于30的用户（即 age > 30）

        # 示例7: 按年龄上界查询（不包含边界）
        >>> await query_users(age_less_than=25)
        # 返回所有年龄小于25的用户（即 age < 25）
    """
    try:
        results = []

        for user_id, user in USERS.items():
            match = True

            # 按姓名查询
            if name and name.lower() not in user["name"].lower():
                match = False

            # 按年龄范围查询（包含边界）
            if min_age is not None and user["age"] < min_age:
                match = False
            if max_age is not None and user["age"] > max_age:
                match = False

            # 按年龄查询（不包含边界）
            if age_greater_than is not None and user["age"] <= age_greater_than:
                match = False
            if age_less_than is not None and user["age"] >= age_less_than:
                match = False

            # 按邮箱查询
            if email_contains and email_contains.lower() not in user["email"].lower():
                match = False

            if match:
                results.append(
                    {"id": user["id"], "name": user["name"], "email": user["email"], "age": user["age"]}
                )

        result = QueryUsersResult(status="success", count=len(results), users=results)
        return result

    except Exception as e:
        raise


# 6. 添加一个简单的测试工具
@mcp.tool()
async def get_user_by_id(user_id: int) -> dict:
    """根据ID获取单个用户信息"""
    user = USERS.get(user_id)
    if user:
        return user
    else:
        return {"error": f"未找到用户 ID: {user_id}"}


# 7. 启动服务器
if __name__ == "__main__":
    # 获取终端窗口宽度，如果无法获取则默认 60
    terminal_width = shutil.get_terminal_size().columns
    separator = "=" * terminal_width
    
    # 所有启动信息输出到 stderr，避免干扰 stdio 协议通信
    print(separator, file=sys.stderr, flush=True)
    print("MCP 服务器启动".center(terminal_width), file=sys.stderr, flush=True)
    print(separator, file=sys.stderr, flush=True)
    print(file=sys.stderr, flush=True)
    print(f"已加载 {len(USERS)} 个用户数据", file=sys.stderr, flush=True)
    print(file=sys.stderr, flush=True)
    print("工作原理:", file=sys.stderr, flush=True)
    print("  1. 服务器使用 stdio (标准输入输出) 协议通信", file=sys.stderr, flush=True)
    print("  2. 保持运行状态，等待客户端通过 stdin 发送请求", file=sys.stderr, flush=True)
    print("  3. 每次客户端调用工具时，解析请求参数并执行查询", file=sys.stderr, flush=True)
    print("  4. 执行完毕后返回 JSON 格式结果", file=sys.stderr, flush=True)
    print(file=sys.stderr, flush=True)
    print("可用工具:", file=sys.stderr, flush=True)
    print("  • query_users - 根据多条件查询用户", file=sys.stderr, flush=True)
    print("  • get_user_by_id - 根据ID获取单个用户", file=sys.stderr, flush=True)
    print(file=sys.stderr, flush=True)
    print("MCP 服务器就绪，等待客户端连接...".center(terminal_width - 4), file=sys.stderr, flush=True)
    print(separator, file=sys.stderr, flush=True)
    print(file=sys.stderr, flush=True)
    
    # 使用 stdio 传输启动 MCP 服务器
    mcp.run()
