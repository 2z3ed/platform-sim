import json
import random
from pathlib import Path

DATA_DIR = Path("/home/kkk/Project/platform-sim/data/ecommerce_dialogue_corpus/E-commerce dataset")
OUTPUT_DIR = Path("/home/kkk/Project/platform-sim/data/extracted_user_queries")

def desegment(text):
    return text.replace(" ", "")

def load_category_data():
    with open(OUTPUT_DIR / "user_queries_by_category.json", "r", encoding="utf-8") as f:
        return json.load(f)

def build_prompt_templates():
    """从ECD数据中提取的用户消息模板，用于User Simulator"""
    templates = {
        "logistics": [
            "我的快递到哪了？单号是{tracking_no}",
            "帮我查一下物流，显示到哪了？",
            "快递怎么还没到啊，都好几天了",
            "帮我看看这个订单的发货情况",
            "发货了吗？快递单号多少？",
            "这个快递还要几天能到？",
            "快递一直没更新，帮我看看",
            "能帮我查下快递到哪了吗？",
        ],
        "refund": [
            "我要退款，帮我申请一下",
            "不想要了，能退款吗？",
            "什么时候能退款到账？",
            "退款申请通过了吗？",
            "我的退款到哪了？",
            "申请退款多久能处理？",
            "帮我取消订单退款",
        ],
        "order_status": [
            "帮我查下订单{order_id}的状态",
            "我的订单还没收到货",
            "订单什么时候能到？",
            "确认收货了，但是没收到货",
            "帮我看看这个订单",
        ],
        "invoice": [
            "能开发票吗？",
            "开一张增值税发票",
            "发票什么时候能开好？",
            "发票抬头是公司名称",
            "帮我开一下发票",
        ],
        "inventory": [
            "这个商品有货吗？",
            "什么时候能补货？",
            "我要买的商品缺货了",
            "帮我看看有没有库存",
        ],
        "shipping_addr": [
            "帮我改一下收货地址",
            "地址写错了，能改一下吗？",
            "新地址是xxxxxx",
        ],
    }
    return templates

def extract_clean_user_queries():
    """提取更干净的用户查询"""
    categorized = load_category_data()

    clean_queries = {}

    for cat, samples in categorized.items():
        queries = []
        for sample in samples:
            query = sample["query"]
            response = sample["response"]

            if len(query) >= 5 and len(query) <= 80:
                keywords_map = {
                    "logistics": ["快递", "发货", "物流", "单号"],
                    "refund": ["退款", "退", "取消"],
                    "invoice": ["发票", "开票"],
                }
                keywords = keywords_map.get(cat, [])
                if keywords:
                    if any(kw in response for kw in keywords):
                        queries.append(query)
                else:
                    queries.append(query)

        unique_queries = list(set(queries))
        random.shuffle(unique_queries)
        clean_queries[cat] = unique_queries[:500]

    return clean_queries

def main():
    print("Building prompt templates from ECD data...")

    templates = build_prompt_templates()

    output = {
        "prompt_templates": templates,
        "total_categories": len(templates),
    }

    with open(OUTPUT_DIR / "user_prompt_templates.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Saved prompt templates to: {OUTPUT_DIR / 'user_prompt_templates.json'}")

    clean_queries = extract_clean_user_queries()

    with open(OUTPUT_DIR / "clean_user_queries.json", "w", encoding="utf-8") as f:
        json.dump(clean_queries, f, ensure_ascii=False, indent=2)

    print(f"Saved clean queries to: {OUTPUT_DIR / 'clean_user_queries.json'}")

    print("\n=== Prompt Templates Summary ===")
    for cat, tmpls in templates.items():
        print(f"{cat}: {len(tmpls)} templates")

    print("\n=== Clean User Queries Summary ===")
    for cat, qs in clean_queries.items():
        print(f"{cat}: {len(qs)} unique queries")

if __name__ == "__main__":
    main()
