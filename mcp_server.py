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
    根据条件查询用户信息

    Args:
        params: 查询参数，包括 name, min_age, max_age, email_contains
        ctx: MCP 上下文，用于日志和错误处理

    Returns:
        QueryUsersResult: 包含查询结果的对象
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
