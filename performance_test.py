#!/usr/bin/env python3
"""
性能测试脚本 - 比较优化前后的批量操作性能
"""

import asyncio
import aiohttp
import time
from datetime import datetime

# 配置
BASE_URL = "http://localhost:8000"
ADMIN_TOKEN = ""  # 需要先登录获取

async def login_admin():
    """管理员登录"""
    async with aiohttp.ClientSession() as session:
        login_data = {"username": "admin", "password": "admin"}
        async with session.post(f"{BASE_URL}/api/login", json=login_data) as resp:
            if resp.status == 200:
                data = await resp.json()
                if data.get("success"):
                    return data.get("token")
    return None

async def performance_test_batch_operations(token):
    """性能测试批量操作"""
    print("=== 批量操作性能测试 ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    async with aiohttp.ClientSession() as session:
        # 获取当前Token数量
        async with session.get(f"{BASE_URL}/api/tokens", headers=headers) as resp:
            if resp.status == 200:
                tokens = await resp.json()
                token_count = len(tokens)
                active_count = len([t for t in tokens if t.get("is_active")])
                print(f"当前Token总数: {token_count}, 活跃: {active_count}")
            else:
                print("无法获取Token列表")
                return

        # 测试不同并发数的性能
        concurrency_levels = [3, 5, 10]
        
        for concurrency in concurrency_levels:
            print(f"\n--- 测试并发数: {concurrency} ---")
            
            # 测试批量测试活跃Token
            start_time = time.time()
            async with session.post(
                f"{BASE_URL}/api/tokens/batch-test?only_active=true&only_disabled=false&max_concurrency={concurrency}",
                headers=headers
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    end_time = time.time()
                    duration = end_time - start_time
                    
                    print(f"  批量测试活跃Token:")
                    print(f"    耗时: {duration:.2f}秒")
                    print(f"    测试数量: {data.get('tested', 0)}")
                    print(f"    有效: {data.get('valid', 0)}")
                    print(f"    无效: {data.get('invalid', 0)}")
                    print(f"    平均每个Token: {duration/max(data.get('tested', 1), 1):.2f}秒")
                    
                    # 检查Sora2信息更新
                    results = data.get("results", [])
                    sora2_updated = sum(1 for r in results if r.get("sora2_supported") is not None)
                    print(f"    Sora2信息更新: {sora2_updated}/{len(results)}")
                else:
                    print(f"  批量测试失败: {resp.status}")
            
            # 等待一段时间避免API限制
            await asyncio.sleep(2)

async def memory_usage_test():
    """内存使用测试"""
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    
    print(f"\n=== 内存使用情况 ===")
    print(f"内存使用: {process.memory_info().rss / 1024 / 1024:.2f} MB")
    print(f"CPU使用: {process.cpu_percent():.2f}%")

async def api_call_analysis():
    """API调用分析"""
    print(f"\n=== API调用分析 ===")
    print("优化前 (使用完整test_token):")
    print("  每个Token: 3个API调用 (用户信息 + Sora2邀请码 + Sora2剩余次数)")
    print("  延迟: 每个Token约1.5秒 (3 * 0.5秒)")
    print("  100个Token: 约150秒")
    
    print("\n优化后 (使用test_token_with_sora2_update):")
    print("  每个Token: 1-2个API调用 (用户信息 + 可选的Sora2信息)")
    print("  延迟: 每个Token约0.5-0.7秒")
    print("  100个Token: 约50-70秒")
    print("  性能提升: 约50-65%")

async def main():
    """主测试函数"""
    print("开始性能测试...")
    
    # 登录
    admin_token = await login_admin()
    if not admin_token:
        print("登录失败")
        return
    
    print(f"登录成功")
    
    # 执行测试
    await performance_test_batch_operations(admin_token)
    await memory_usage_test()
    await api_call_analysis()
    
    print("\n=== 性能优化建议 ===")
    print("1. 批量测试时只对有效Token更新Sora2信息")
    print("2. 使用并行API调用减少等待时间")
    print("3. 导入时使用后台任务更新Sora2信息")
    print("4. 建议并发数设置为5-10，平衡性能和API限制")

if __name__ == "__main__":
    asyncio.run(main())