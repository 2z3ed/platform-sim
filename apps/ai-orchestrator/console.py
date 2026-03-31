"""
终端控制台 - 多轮对话仿真
支持选择平台、情绪，返回官方真实API格式
"""

import os
import sys
import json
import time
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from providers.utils.fixture_loader import FixtureLoader

API_BASE = os.getenv("API_BASE", "http://localhost:8000")

PLATFORMS = {
    "1": "taobao",
    "2": "jd",
    "3": "douyin_shop",
    "4": "xhs",
    "5": "kuaishou",
    "6": "wecom_kf"
}

PLATFORM_NAMES = {
    "taobao": "淘宝",
    "jd": "京东",
    "douyin_shop": "抖音小店",
    "xhs": "小红书",
    "kuaishou": "快手",
    "wecom_kf": "企微客服"
}

EMOTIONS = {
    "1": "calm",
    "2": "impatient",
    "3": "angry"
}

EMOTION_NAMES = {
    "calm": "平静",
    "impatient": "不耐烦",
    "angry": "生气"
}

INTENTS = {
    "1": "ask_order_status",
    "2": "ask_shipment",
    "3": "ask_refund",
    "4": "complain",
    "5": "escalate_to_human",
    "0": "auto"
}


def clear_screen():
    os.system('clear' if os.name == 'posix' else 'cls')


def print_header():
    print("\033[36m" + "="*60 + "\033[0m")
    print("\033[36m" + "     Platform-Sim 终端控制台" + "\033[0m")
    print("\033[36m" + "="*60 + "\033[0m\n")


def print_menu():
    print("\033[33m平台选择:\033[0m")
    for k, v in PLATFORMS.items():
        print(f"  [{k}] {PLATFORM_NAMES.get(v, v)}")
    
    print("\n\033[33m情绪选择:\033[0m")
    for k, v in EMOTIONS.items():
        print(f"  [{k}] {EMOTION_NAMES.get(v, v)}")
    
    print("\n\033[33m意图选择:\033[0m")
    for k, v in INTENTS.items():
        print(f"  [{k}] {v}")
    
    print("\n\033[33m其他命令:\033[0m")
    print("  [q] 退出")
    print("  [r] 查看原始API返回")
    print("  [f] 查看Fixture列表")
    print("  [u] 查看用户列表")
    print("")


def select_platform():
    while True:
        choice = input("\033[32m选择平台 [1-6]: \033[0m").strip()
        if choice in PLATFORMS:
            return PLATFORMS[choice]
        print("\033[31m无效选择，请重新输入\033[0m")


def select_emotion():
    while True:
        choice = input("\033[32m选择情绪 [1-3]: \033[0m").strip()
        if choice in EMOTIONS:
            return EMOTIONS[choice]
        print("\033[31m无效选择，请重新输入\033[0m")


def select_intent():
    choice = input("\033[32m选择意图 [0-5, 默认0自动]: \033[0m").strip() or "0"
    return INTENTS.get(choice, "auto")


def run_simulation(platform: str, emotion: str, intent: str = None, max_turns: int = 1):
    print(f"\n\033[36m{'='*60}\033[0m")
    print(f"\033[36m  平台: {PLATFORM_NAMES.get(platform, platform)} | 情绪: {EMOTION_NAMES.get(emotion, emotion)}\033[0m")
    print(f"\033[36m{'='*60}\033[0m\n")
    
    try:
        payload = {
            "platform": platform,
            "emotion": emotion,
            "max_turns": max_turns
        }
        
        print("\033[33m创建对话...\033[0m")
        resp = requests.post(f"{API_BASE}/conversation-studio/runs", json=payload, timeout=10)
        
        if resp.status_code != 200:
            print(f"\033[31m创建失败: {resp.text}\033[0m")
            return None
        
        data = resp.json()
        run_id = data["run_id"]
        print(f"\033[32m对话已创建: {run_id}\033[0m")
        
        print(f"\n\033[33m生成用户消息 (LLM调用中)...\033[0m")
        start_time = time.time()
        
        next_payload = {}
        if intent and intent != "auto":
            next_payload["override_intent"] = intent
        
        resp = requests.post(f"{API_BASE}/conversation-studio/runs/{run_id}/next", json=next_payload, timeout=30)
        elapsed = time.time() - start_time
        
        if resp.status_code != 200:
            print(f"\033[31m获取回复失败: {resp.text}\033[0m")
            return None
        
        data = resp.json()
        
        print(f"\033[32m完成 ({elapsed*1000:.0f}ms)\033[0m\n")
        
        print(f"\033[34m{'═'*60}\033[0m")
        print(f"\033[34m  用户消息:\033[0m")
        print(f"\033[37m     {data['user_message']}\033[0m")
        print(f"\033[90m     意图: {data['intent']} | 情绪: {data['emotion']}\033[0m")
        
        if data.get('tool_calls'):
            print(f"\n\033[33m{'═'*60}\033[0m")
            print(f"\033[33m  官方API返回 (Fixture原始数据):\033[0m")
            
            for tc in data['tool_calls']:
                tool_name = tc['name']
                args = tc.get('arguments', {})
                
                order_id = args.get('order_id') if isinstance(args, dict) else None
                
                if order_id:
                    print(f"\n\033[36m{'─'*60}\033[0m")
                    print(f"\033[36m  工具: {tool_name}\033[0m")
                    print(f"\033[36m  参数: {json.dumps(args, ensure_ascii=False)}\033[0m")
                    
                    fixture_data = FixtureLoader.get_order(platform, order_id)
                    if fixture_data:
                        print(f"\n\033[32m  订单官方API格式:\033[0m")
                        print(json.dumps(fixture_data, indent=2, ensure_ascii=False))
                    
                    shipment_data = FixtureLoader.get_shipment(platform, order_id)
                    if shipment_data:
                        print(f"\n\033[32m  物流官方API格式:\033[0m")
                        print(json.dumps(shipment_data, indent=2, ensure_ascii=False))
                    
                    refund_data = FixtureLoader.get_refund(platform, order_id)
                    if refund_data:
                        print(f"\n\033[32m  退款官方API格式:\033[0m")
                        print(json.dumps(refund_data, indent=2, ensure_ascii=False))
        
        print(f"\n\033[34m{'═'*60}\033[0m\n")
        
        return data
        
    except requests.exceptions.Timeout:
        print("\033[31m请求超时\033[0m")
        return None
    except requests.exceptions.ConnectionError:
        print("\033[31m连接失败，请确认服务器已启动\033[0m")
        return None
    except Exception as e:
        print(f"\033[31m错误: {e}\033[0m")
        return None


def show_raw_api(platform: str, order_id: str = None):
    print(f"\n\033[36m{'='*60}\033[0m")
    print(f"\033[36m  官方API原始返回 - {PLATFORM_NAMES.get(platform, platform)}\033[0m")
    print(f"\033[36m{'='*60}\033[0m\n")
    
    if not order_id:
        orders = FixtureLoader.list_orders(platform)
        if orders:
            order_id = orders[0]
    
    if not order_id:
        print("\033[31m未找到订单\033[0m")
        return
    
    print(f"\033[33m订单ID: {order_id}\033[0m\n")
    
    try:
        resp = requests.get(f"{API_BASE}/official-sim/query/orders/{order_id}", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            print("\033[32m订单信息:\033[0m")
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print(f"\033[31m订单查询失败: {resp.status_code}\033[0m")
    except Exception as e:
        print(f"\033[31m错误: {e}\033[0m")
    
    try:
        resp = requests.get(f"{API_BASE}/official-sim/query/orders/{order_id}/shipment", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            print("\n\033[32m物流信息:\033[0m")
            print(json.dumps(data, indent=2, ensure_ascii=False))
    except:
        pass
    
    try:
        resp = requests.get(f"{API_BASE}/official-sim/query/orders/{order_id}/refund", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            print("\n\033[32m退款信息:\033[0m")
            print(json.dumps(data, indent=2, ensure_ascii=False))
    except:
        pass


def show_fixtures(platform: str):
    print(f"\n\033[36m{'='*60}\033[0m")
    print(f"\033[36m  Fixture列表 - {PLATFORM_NAMES.get(platform, platform)}\033[0m")
    print(f"\033[36m{'='*60}\033[0m\n")
    
    for category in ["success", "edge_case", "error_case"]:
        fixtures = FixtureLoader.list_fixtures(platform, category)
        if fixtures:
            print(f"\033[33m{category}:\033[0m")
            for f in fixtures[:10]:
                print(f"  - {f}")
            if len(fixtures) > 10:
                print(f"  ... 共 {len(fixtures)} 个")


def show_users(platform: str):
    print(f"\n\033[36m{'='*60}\033[0m")
    print(f"\033[36m  用户列表 - {PLATFORM_NAMES.get(platform, platform)}\033[0m")
    print(f"\033[36m{'='*60}\033[0m\n")
    
    users = FixtureLoader.list_users(platform)
    if users:
        for user_id in users[:10]:
            orders = FixtureLoader.list_orders(platform, user_id)
            print(f"\033[33m  {user_id}\033[0m - {len(orders)} 个订单")
    else:
        print("\033[31m未找到用户\033[0m")


def interactive_mode():
    current_platform = "taobao"
    current_emotion = "calm"
    
    while True:
        clear_screen()
        print_header()
        print(f"\033[90m当前: 平台={PLATFORM_NAMES.get(current_platform)} | 情绪={EMOTION_NAMES.get(current_emotion)}\033[0m\n")
        print_menu()
        
        cmd = input("\033[32m输入命令: \033[0m").strip().lower()
        
        if cmd == 'q':
            print("\n\033[33m再见!\033[0m\n")
            break
        elif cmd == 'r':
            show_raw_api(current_platform)
            input("\n\033[90m按回车继续...\033[0m")
        elif cmd == 'f':
            show_fixtures(current_platform)
            input("\n\033[90m按回车继续...\033[0m")
        elif cmd == 'u':
            show_users(current_platform)
            input("\n\033[90m按回车继续...\033[0m")
        elif cmd == 'p':
            current_platform = select_platform()
        elif cmd == 'e':
            current_emotion = select_emotion()
        elif cmd == 's' or cmd == '':
            intent = select_intent()
            run_simulation(current_platform, current_emotion, intent)
            input("\n\033[90m按回车继续...\033[0m")
        elif cmd in PLATFORMS:
            current_platform = PLATFORMS[cmd]
        elif cmd in EMOTIONS:
            current_emotion = EMOTIONS[cmd]
        else:
            print("\033[31m无效命令\033[0m")
            time.sleep(1)


def quick_mode(platform: str = None, emotion: str = None, intent: str = None):
    if not platform:
        platform = select_platform()
    if not emotion:
        emotion = select_emotion()
    
    run_simulation(platform, emotion, intent)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Platform-Sim 终端控制台")
    parser.add_argument("-p", "--platform", choices=list(PLATFORMS.values()), help="平台")
    parser.add_argument("-e", "--emotion", choices=list(EMOTIONS.values()), help="情绪")
    parser.add_argument("-i", "--intent", help="意图")
    parser.add_argument("-r", "--raw", action="store_true", help="显示原始API返回")
    parser.add_argument("--non-interactive", action="store_true", help="非交互模式")
    
    args = parser.parse_args()
    
    if args.raw:
        show_raw_api(args.platform or "taobao")
    elif args.non_interactive:
        quick_mode(args.platform, args.emotion, args.intent)
    else:
        interactive_mode()
