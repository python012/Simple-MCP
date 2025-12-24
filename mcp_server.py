"""
MCP 服务器 - 使用官方 mcp 库实现
提供用户数据库查询工具
"""

import json
from typing import Dict, Any, List, Optional, TypedDict
from pydantic import BaseModel, Field
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

    name: Optional[str] = Field(None, description="按姓名模糊查询")
    min_age: Optional[int] = Field(None, description="最小年龄")
    max_age: Optional[int] = Field(None, description="最大年龄")
    email_contains: Optional[str] = Field(None, description="邮箱包含的字符串")


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
async def query_users(params: QueryUsersParams, ctx: Context[ServerSession, None]) -> QueryUsersResult:
    """
    根据多种条件灵活查询用户信息。支持按姓名、年龄范围、邮箱等进行过滤，可组合多个条件进行高级查询。

    Args:
        params (QueryUsersParams): 查询参数对象
            - name (Optional[str]): 按姓名模糊查询，不区分大小写
            - min_age (Optional[int]): 最小年龄（包含），用于年龄范围查询的下界
            - max_age (Optional[int]): 最大年龄（包含），用于年龄范围查询的上界
            - email_contains (Optional[str]): 邮箱包含的字符串，模糊匹配，不区分大小写
        ctx (Context): MCP 上下文，用于日志记录和错误处理

    Returns:
        QueryUsersResult: 查询结果对象
            - status (str): 查询状态，成功返回 "success"
            - count (int): 匹配的用户数量
            - users (List[UserResult]): 符合条件的用户列表

    Examples:
        # 示例1: 按姓名查询
        >>> params = QueryUsersParams(name="Alice")
        >>> result = await query_users(params, ctx)
        # 返回所有包含 "Alice" 的用户

        # 示例2: 按年龄范围查询
        >>> params = QueryUsersParams(min_age=25, max_age=30)
        >>> result = await query_users(params, ctx)
        # 返回年龄在 25-30 之间的所有用户

        # 示例3: 组合条件查询（姓名 + 年龄范围）
        >>> params = QueryUsersParams(name="David", min_age=27, max_age=32)
        >>> result = await query_users(params, ctx)
        # 返回名字包含 "David" 且年龄在 27-32 之间的用户

        # 示例4: 按邮箱域名查询
        >>> params = QueryUsersParams(email_contains="@example.com")
        >>> result = await query_users(params, ctx)
        # 返回所有邮箱包含 "@example.com" 的用户

        # 示例5: 查询所有用户
        >>> params = QueryUsersParams()
        >>> result = await query_users(params, ctx)
        # 返回所有用户
    """
    try:
        await ctx.info(f"🔍 收到查询请求: {params.model_dump_json()}")

        results = []

        for user_id, user in USERS.items():
            match = True

            # 按姓名查询
            if params.name and params.name.lower() not in user["name"].lower():
                match = False

            # 按年龄范围查询
            if params.min_age is not None and user["age"] < params.min_age:
                match = False
            if params.max_age is not None and user["age"] > params.max_age:
                match = False

            # 按邮箱查询
            if params.email_contains and params.email_contains.lower() not in user["email"].lower():
                match = False

            if match:
                results.append(
                    {"id": user["id"], "name": user["name"], "email": user["email"], "age": user["age"]}
                )

        result = QueryUsersResult(status="success", count=len(results), users=results)

        await ctx.info(f"✅ 查询成功，找到 {len(results)} 个用户")
        return result

    except Exception as e:
        await ctx.error(f"❌ 查询失败: {str(e)}")
        raise


# 6. 添加一个简单的测试工具
@mcp.tool()
async def get_user_by_id(user_id: int, ctx: Context[ServerSession, None]) -> dict:
    """根据ID获取单个用户信息"""
    user = USERS.get(user_id)
    if user:
        await ctx.info(f"✅ 找到用户 ID: {user_id}")
        return user
    else:
        await ctx.warning(f"⚠️ 未找到用户 ID: {user_id}")
        return {"error": f"未找到用户 ID: {user_id}"}


# 7. 启动服务器
if __name__ == "__main__":
    # 使用 stdio 传输启动 MCP 服务器
    mcp.run()
