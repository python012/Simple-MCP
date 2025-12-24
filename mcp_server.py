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
    1: {"id": 1, "name": "Alice", "email": "alice@example.com", "age": 39, "gender": "female"},
    2: {"id": 2, "name": "Bob", "email": "bob@example.com", "age": 40, "gender": "male"},
    3: {"id": 3, "name": "Charlie", "email": "charlie@example.com", "age": 19, "gender": "male"},
    4: {"id": 4, "name": "David", "email": "david.wilson@example.com", "age": 41, "gender": "male"},
    5: {"id": 5, "name": "Emma", "email": "emma.johnson@example.com", "age": 37, "gender": "female"},
    6: {"id": 6, "name": "Frank", "email": "frank.smith@example.com", "age": 20, "gender": "male"},
    7: {"id": 7, "name": "Grace", "email": "grace.lee@example.com", "age": 17, "gender": "female"},
    8: {"id": 8, "name": "Henry", "email": "henry.brown@example.com", "age": 35, "gender": "male"},
    9: {"id": 9, "name": "Ivy", "email": "ivy.martinez@example.com", "age": 29, "gender": "female"},
    10: {"id": 10, "name": "Jack", "email": "jack.taylor@example.com", "age": 18, "gender": "male"},
    11: {"id": 11, "name": "Karen", "email": "karen.anderson@example.com", "age": 28, "gender": "female"},
    12: {"id": 12, "name": "Leo", "email": "leo.thompson@example.com", "age": 22, "gender": "male"},
    13: {"id": 13, "name": "Mia", "email": "mia.garcia@example.com", "age": 18, "gender": "female"},
}


# 2. 定义用户之间的关系网络（图结构 - 边列表）
RELATIONSHIPS = [
    # 家庭1：Alice & Bob 的家庭（ID: 1, 2, 3, 13）
    {"user1": 1, "user2": 2, "relation": "夫妻", "user1_name": "Alice", "user2_name": "Bob"},
    {"user1": 1, "user2": 3, "relation": "母子", "user1_name": "Alice", "user2_name": "Charlie"},
    {"user1": 2, "user2": 3, "relation": "父子", "user1_name": "Bob", "user2_name": "Charlie"},
    {"user1": 1, "user2": 13, "relation": "母女", "user1_name": "Alice", "user2_name": "Mia"},
    {"user1": 2, "user2": 13, "relation": "父女", "user1_name": "Bob", "user2_name": "Mia"},
    {"user1": 3, "user2": 13, "relation": "兄妹", "user1_name": "Charlie", "user2_name": "Mia"},
    # 家庭2：David & Emma 的家庭（ID: 4, 5, 6, 7）
    {"user1": 4, "user2": 5, "relation": "夫妻", "user1_name": "David", "user2_name": "Emma"},
    {"user1": 4, "user2": 6, "relation": "父子", "user1_name": "David", "user2_name": "Frank"},
    {"user1": 5, "user2": 6, "relation": "母子", "user1_name": "Emma", "user2_name": "Frank"},
    {"user1": 4, "user2": 7, "relation": "父女", "user1_name": "David", "user2_name": "Grace"},
    {"user1": 5, "user2": 7, "relation": "母女", "user1_name": "Emma", "user2_name": "Grace"},
    {"user1": 6, "user2": 7, "relation": "兄妹", "user1_name": "Frank", "user2_name": "Grace"},
    # 家庭3：Henry & Ivy 的家庭（ID: 8, 9, 10）
    {"user1": 8, "user2": 9, "relation": "夫妻", "user1_name": "Henry", "user2_name": "Ivy"},
    {"user1": 8, "user2": 10, "relation": "父子", "user1_name": "Henry", "user2_name": "Jack"},
    {"user1": 9, "user2": 10, "relation": "母子", "user1_name": "Ivy", "user2_name": "Jack"},
    # Karen & Leo 姐弟（ID: 11, 12）
    {"user1": 11, "user2": 12, "relation": "姐弟", "user1_name": "Karen", "user2_name": "Leo"},
    # 跨家庭关系（让家庭之间有连接）
    {"user1": 3, "user2": 6, "relation": "表兄弟", "user1_name": "Charlie", "user2_name": "Frank"},
    {"user1": 13, "user2": 7, "relation": "朋友", "user1_name": "Mia", "user2_name": "Grace"},
    {"user1": 10, "user2": 11, "relation": "朋友", "user1_name": "Jack", "user2_name": "Karen"},
]


# 3. 构建邻接表（方便快速查询某个用户的所有关系）
def build_adjacency_list():
    """构建邻接表，用于快速查询用户关系"""
    adj_list = {user_id: [] for user_id in USERS.keys()}

    for rel in RELATIONSHIPS:
        # 添加双向关系
        adj_list[rel["user1"]].append(
            {
                "related_user_id": rel["user2"],
                "related_user_name": rel["user2_name"],
                "relation": rel["relation"],
            }
        )
        adj_list[rel["user2"]].append(
            {
                "related_user_id": rel["user1"],
                "related_user_name": rel["user1_name"],
                "relation": get_reverse_relation(rel["relation"]),
            }
        )

    return adj_list


def get_reverse_relation(relation: str) -> str:
    """获取反向关系"""
    reverse_map = {
        "夫妻": "夫妻",
        "父子": "子父",
        "母子": "子母",
        "父女": "女父",
        "母女": "女母",
        "兄妹": "妹兄",
        "姐弟": "弟姐",
        "表兄弟": "表兄弟",
        "表姐妹": "表姐妹",
        "朋友": "朋友",
    }
    return reverse_map.get(relation, relation)


# 构建邻接表
USER_ADJACENCY_LIST = build_adjacency_list()


# 2. 定义查询参数的结构
class QueryUsersParams(BaseModel):
    """查询用户的参数"""

    model_config = ConfigDict(extra="ignore")

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


# 6. 添加查询工具
@mcp.tool()
async def get_user_by_id(user_id: int) -> dict:
    """
    根据ID获取单个用户信息

    Args:
        user_id (int): 用户ID

    Returns:
        dict: 用户信息，包含 id, name, email, age, gender
    """
    user = USERS.get(user_id)
    if user:
        return user
    else:
        return {"error": f"未找到用户 ID: {user_id}"}


@mcp.tool()
async def get_user_relationships(user_id: int) -> dict:
    """
    查询某个用户的所有关系

    Args:
        user_id (int): 用户ID

    Returns:
        dict: 包含用户基本信息和所有关系列表

    Examples:
        >>> await get_user_relationships(1)
        # 返回 Alice 的所有关系（配偶Bob、儿子Charlie、女儿Mia等）
    """
    user = USERS.get(user_id)
    if not user:
        return {"error": f"未找到用户 ID: {user_id}"}

    relationships = USER_ADJACENCY_LIST.get(user_id, [])

    return {"user": user, "relationships_count": len(relationships), "relationships": relationships}


@mcp.tool()
async def get_relationship_between_users(user1_id: int, user2_id: int) -> dict:
    """
    查询两个用户之间是否有关系

    Args:
        user1_id (int): 第一个用户的ID
        user2_id (int): 第二个用户的ID

    Returns:
        dict: 两个用户之间的关系信息

    Examples:
        >>> await get_relationship_between_users(1, 2)
        # 返回 Alice 和 Bob 的关系：夫妻

        >>> await get_relationship_between_users(1, 10)
        # 返回 Alice 和 Jack 没有直接关系
    """
    user1 = USERS.get(user1_id)
    user2 = USERS.get(user2_id)

    if not user1:
        return {"error": f"未找到用户 ID: {user1_id}"}
    if not user2:
        return {"error": f"未找到用户 ID: {user2_id}"}

    # 查找 user1 到 user2 的关系
    relationships = USER_ADJACENCY_LIST.get(user1_id, [])
    for rel in relationships:
        if rel["related_user_id"] == user2_id:
            return {"has_relationship": True, "user1": user1, "user2": user2, "relation": rel["relation"]}

    return {
        "has_relationship": False,
        "user1": user1,
        "user2": user2,
        "message": f"{user1['name']} 和 {user2['name']} 没有直接关系",
    }


@mcp.tool()
async def get_spouse(user_id: int) -> dict:
    """
    查询某个用户的配偶（丈夫或妻子）

    Args:
        user_id (int): 用户ID

    Returns:
        dict: 配偶的完整信息，包括 id, name, email, age, gender

    Examples:
        >>> await get_spouse(1)
        # 返回 Alice 的配偶 Bob 的完整信息

        >>> await get_spouse(3)
        # 返回 Charlie 没有配偶（未婚）
    """
    user = USERS.get(user_id)
    if not user:
        return {"error": f"未找到用户 ID: {user_id}"}

    relationships = USER_ADJACENCY_LIST.get(user_id, [])
    for rel in relationships:
        if rel["relation"] == "夫妻":
            spouse_id = rel["related_user_id"]
            spouse = USERS.get(spouse_id)
            return {"user": user, "has_spouse": True, "spouse": spouse}

    return {"user": user, "has_spouse": False, "message": f"{user['name']} 没有配偶"}


@mcp.tool()
async def get_relatives_by_relation(user_id: int, relation_type: Optional[str] = None) -> dict:
    """
    查询某个用户的特定类型亲戚或所有亲戚

    Args:
        user_id (int): 用户ID
        relation_type (Optional[str]): 关系类型，如 "父子", "母女", "兄妹" 等
            如果不指定，返回所有关系

    Returns:
        dict: 符合条件的亲戚列表，包含完整用户信息

    Examples:
        >>> await get_relatives_by_relation(1, "母子")
        # 返回 Alice 的儿子 Charlie

        >>> await get_relatives_by_relation(1, "母女")
        # 返回 Alice 的女儿 Mia

        >>> await get_relatives_by_relation(3)
        # 返回 Charlie 的所有亲戚
    """
    user = USERS.get(user_id)
    if not user:
        return {"error": f"未找到用户 ID: {user_id}"}

    relationships = USER_ADJACENCY_LIST.get(user_id, [])

    # 如果指定了关系类型，进行过滤
    if relation_type:
        filtered_relationships = [rel for rel in relationships if rel["relation"] == relation_type]
    else:
        filtered_relationships = relationships

    # 获取完整的用户信息
    relatives = []
    for rel in filtered_relationships:
        relative_id = rel["related_user_id"]
        relative = USERS.get(relative_id)
        if relative:
            relatives.append({"relation": rel["relation"], "relative": relative})

    return {
        "user": user,
        "relation_type": relation_type if relation_type else "所有关系",
        "count": len(relatives),
        "relatives": relatives,
    }


@mcp.tool()
async def get_children(user_id: int) -> dict:
    """
    查询某个用户的所有子女

    Args:
        user_id (int): 用户ID

    Returns:
        dict: 所有子女的完整信息列表

    Examples:
        >>> await get_children(1)
        # 返回 Alice 的子女：Charlie 和 Mia
    """
    user = USERS.get(user_id)
    if not user:
        return {"error": f"未找到用户 ID: {user_id}"}

    relationships = USER_ADJACENCY_LIST.get(user_id, [])

    # 筛选父子、父女、母子、母女关系
    child_relations = ["父子", "父女", "母子", "母女"]
    children = []

    for rel in relationships:
        if rel["relation"] in child_relations:
            child_id = rel["related_user_id"]
            child = USERS.get(child_id)
            if child:
                children.append({"relation": rel["relation"], "child": child})

    return {"user": user, "children_count": len(children), "children": children}


@mcp.tool()
async def get_parents(user_id: int) -> dict:
    """
    查询某个用户的父母

    Args:
        user_id (int): 用户ID

    Returns:
        dict: 父母的完整信息列表

    Examples:
        >>> await get_parents(3)
        # 返回 Charlie 的父母：Alice 和 Bob
    """
    user = USERS.get(user_id)
    if not user:
        return {"error": f"未找到用户 ID: {user_id}"}

    relationships = USER_ADJACENCY_LIST.get(user_id, [])

    # 筛选子父、子母、女父、女母关系
    parent_relations = ["子父", "子母", "女父", "女母"]
    parents = []

    for rel in relationships:
        if rel["relation"] in parent_relations:
            parent_id = rel["related_user_id"]
            parent = USERS.get(parent_id)
            if parent:
                parents.append({"relation": rel["relation"], "parent": parent})

    return {"user": user, "parents_count": len(parents), "parents": parents}


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
    print("  • get_user_relationships - 查询用户的所有关系", file=sys.stderr, flush=True)
    print("  • get_relationship_between_users - 查询两人之间的关系", file=sys.stderr, flush=True)
    print("  • get_spouse - 查询配偶信息", file=sys.stderr, flush=True)
    print("  • get_relatives_by_relation - 按关系类型查询亲戚", file=sys.stderr, flush=True)
    print("  • get_children - 查询子女信息", file=sys.stderr, flush=True)
    print("  • get_parents - 查询父母信息", file=sys.stderr, flush=True)
    print(file=sys.stderr, flush=True)
    print("MCP 服务器就绪，等待客户端连接...".center(terminal_width - 4), file=sys.stderr, flush=True)
    print(separator, file=sys.stderr, flush=True)
    print(file=sys.stderr, flush=True)

    # 使用 stdio 传输启动 MCP 服务器
    mcp.run()
