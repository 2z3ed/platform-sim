import sys
from pathlib import Path

_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(_root))
sys.path.insert(0, str(_root / "apps" / "ai-orchestrator"))

from nodes.user_simulator import UserSimulator

def main():
    print("=" * 60)
    print("User Simulator 测试 (ECD模板已整合)")
    print("=" * 60)

    platforms = ["jd", "taobao", "douyin_shop"]

    for platform in platforms:
        print(f"\n{'='*60}")
        print(f"测试平台: {platform}")
        print("="*60)

        try:
            simulator = UserSimulator()
            result = simulator.generate(platform=platform)

            print(f"\n用户ID: {result.decision.selected_user_id}")
            print(f"订单ID: {result.decision.selected_order_id}")
            print(f"意图: {result.decision.intent.value}")
            print(f"情绪: {result.decision.emotion.value}")
            print(f"\n生成的用户消息:")
            print(f"  {result.user_message}")
            print(f"\n决策原因: {result.decision.reason}")

            if result.decision.tool_calls_used:
                print(f"\n调用的工具:")
                for tc in result.decision.tool_calls_used:
                    print(f"  - {tc.name}: {tc.arguments}")

        except Exception as e:
            print(f"  ❌ 错误: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
