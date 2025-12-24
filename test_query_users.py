"""
测试 query_users 函数的脚本
"""

import asyncio
from mcp_server import query_users, QueryUsersParams, USERS
from mcp.server.session import ServerSession
from mcp.server.fastmcp import Context


# 创建一个模拟的 Context 对象用于测试
class MockContext:
    """模拟 MCP Context，用于测试"""
    
    async def info(self, message: str):
        print(f"ℹ️  INFO: {message}")
    
    async def warning(self, message: str):
        print(f"⚠️  WARNING: {message}")
    
    async def error(self, message: str):
        print(f"❌ ERROR: {message}")


async def test_query_all_users():
    """测试1: 查询所有用户"""
    print("\n" + "="*50)
    print("测试1: 查询所有用户")
    print("="*50)
    
    ctx = MockContext()
    params = QueryUsersParams(name=None, min_age=None, max_age=None, email_contains=None)
    result = await query_users(params, ctx)
    
    print(f"状态: {result.status}")
    print(f"找到 {result.count} 个用户")
    for user in result.users:
        print(f"  - {user['id']}: {user['name']} ({user['age']}) - {user['email']}")


async def test_query_by_name():
    """测试2: 按姓名查询"""
    print("\n" + "="*50)
    print("测试2: 按姓名查询 (name='Alice')")
    print("="*50)
    
    ctx = MockContext()
    params = QueryUsersParams(name="Alice", min_age=None, max_age=None, email_contains=None)
    result = await query_users(params, ctx)
    
    print(f"状态: {result.status}")
    print(f"找到 {result.count} 个用户")
    for user in result.users:
        print(f"  - {user['name']} ({user['age']}) - {user['email']}")


async def test_query_by_age_range():
    """测试3: 按年龄范围查询"""
    print("\n" + "="*50)
    print("测试3: 按年龄范围查询 (min_age=27, max_age=30)")
    print("="*50)
    
    ctx = MockContext()
    params = QueryUsersParams(name=None, min_age=27, max_age=30, email_contains=None)
    result = await query_users(params, ctx)
    
    print(f"状态: {result.status}")
    print(f"找到 {result.count} 个用户")
    for user in result.users:
        print(f"  - {user['name']} (年龄: {user['age']}) - {user['email']}")


async def test_query_by_email():
    """测试4: 按邮箱查询"""
    print("\n" + "="*50)
    print("测试4: 按邮箱查询 (email_contains='smith')")
    print("="*50)
    
    ctx = MockContext()
    params = QueryUsersParams(name=None, min_age=None, max_age=None, email_contains="smith")
    result = await query_users(params, ctx)
    
    print(f"状态: {result.status}")
    print(f"找到 {result.count} 个用户")
    for user in result.users:
        print(f"  - {user['name']} - {user['email']}")


async def test_query_combined():
    """测试5: 组合条件查询"""
    print("\n" + "="*50)
    print("测试5: 组合条件查询 (name='David', min_age=25, max_age=30)")
    print("="*50)
    
    ctx = MockContext()
    params = QueryUsersParams(name="David", min_age=25, max_age=30, email_contains=None)
    result = await query_users(params, ctx)
    
    print(f"状态: {result.status}")
    print(f"找到 {result.count} 个用户")
    for user in result.users:
        print(f"  - {user['name']} (年龄: {user['age']}) - {user['email']}")


async def main():
    """运行所有测试"""
    print("\n🧪 开始测试 query_users 函数\n")
    print(f"数据库中共有 {len(USERS)} 个用户\n")
    
    await test_query_all_users()
    await test_query_by_name()
    await test_query_by_age_range()
    await test_query_by_email()
    await test_query_combined()
    
    print("\n" + "="*50)
    print("✅ 所有测试完成！")
    print("="*50 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
