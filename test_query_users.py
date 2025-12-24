"""
测试 query_users 函数的脚本
"""

import asyncio
from mcp_server import query_users, USERS


async def test_query_all_users():
    """测试1: 查询所有用户"""
    print("\n" + "="*50)
    print("测试1: 查询所有用户")
    print("="*50)
    
    result = await query_users()
    
    print(f"状态: {result.status}")
    print(f"找到 {result.count} 个用户")
    for user in result.users:
        print(f"  - {user['id']}: {user['name']} ({user['age']}) - {user['email']}")


async def test_query_by_name():
    """测试2: 按姓名查询"""
    print("\n" + "="*50)
    print("测试2: 按姓名查询 (name='Alice')")
    print("="*50)
    
    result = await query_users(name="Alice")
    
    print(f"状态: {result.status}")
    print(f"找到 {result.count} 个用户")
    for user in result.users:
        print(f"  - {user['name']} ({user['age']}) - {user['email']}")


async def test_query_by_age_range():
    """测试3: 按年龄范围查询（包含边界）"""
    print("\n" + "="*50)
    print("测试3: 按年龄范围查询 (min_age=27, max_age=30，包含边界)")
    print("="*50)
    
    result = await query_users(min_age=27, max_age=30)
    
    print(f"状态: {result.status}")
    print(f"找到 {result.count} 个用户")
    for user in result.users:
        print(f"  - {user['name']} (年龄: {user['age']}) - {user['email']}")


async def test_query_by_email():
    """测试4: 按邮箱查询"""
    print("\n" + "="*50)
    print("测试4: 按邮箱查询 (email_contains='smith')")
    print("="*50)
    
    result = await query_users(email_contains="smith")
    
    print(f"状态: {result.status}")
    print(f"找到 {result.count} 个用户")
    for user in result.users:
        print(f"  - {user['name']} - {user['email']}")


async def test_query_combined():
    """测试5: 组合条件查询"""
    print("\n" + "="*50)
    print("测试5: 组合条件查询 (name='David', min_age=25, max_age=30)")
    print("="*50)
    
    result = await query_users(name="David", min_age=25, max_age=30)
    
    print(f"状态: {result.status}")
    print(f"找到 {result.count} 个用户")
    for user in result.users:
        print(f"  - {user['name']} (年龄: {user['age']}) - {user['email']}")

async def test_query_age_greater_than():
    """测试6: 按年龄下界查询（不包含边界）"""
    print("\n" + "="*50)
    print("测试6: 按年龄下界查询 (age_greater_than=30，即 age > 30)")
    print("="*50)
    
    result = await query_users(age_greater_than=30)
    
    print(f"状态: {result.status}")
    print(f"找到 {result.count} 个用户")
    for user in result.users:
        print(f"  - {user['name']} (年龄: {user['age']}) - {user['email']}")


async def test_query_age_less_than():
    """测试7: 按年龄上界查询（不包含边界）"""
    print("\n" + "="*50)
    print("测试7: 按年龄上界查询 (age_less_than=25，即 age < 25)")
    print("="*50)
    
    result = await query_users(age_less_than=25)
    
    print(f"状态: {result.status}")
    print(f"找到 {result.count} 个用户")
    for user in result.users:
        print(f"  - {user['name']} (年龄: {user['age']}) - {user['email']}")


async def test_query_age_range_exclusive():
    """测试8: 按年龄区间查询（排他性边界）"""
    print("\n" + "="*50)
    print("测试8: 按年龄区间查询 (age_greater_than=25 AND age_less_than=35，即 25 < age < 35)")
    print("="*50)
    
    result = await query_users(age_greater_than=25, age_less_than=35)
    
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
    await test_query_age_greater_than()
    await test_query_age_less_than()
    await test_query_age_range_exclusive()
    
    print("\n" + "="*50)
    print("✅ 所有测试完成！")
    print("="*50 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
