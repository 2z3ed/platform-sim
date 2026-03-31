import json
import re
from collections import defaultdict
from pathlib import Path

DATA_DIR = Path("/home/kkk/Project/platform-sim/data/ecommerce_dialogue_corpus/E-commerce dataset")
OUTPUT_DIR = Path("/home/kkk/Project/platform-sim/data/extracted_user_queries")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CATEGORIES = {
    "logistics": ["物流", "快递", "发货", "到货", "几天到", "什么时候到", "快递单", "单号", "运输"],
    "refund": ["退款", "退货", "退换", "不想要", "取消订单", "申请退款", "退款到账", "钱什么时候回来"],
    "invoice": ["发票", "增票", "普票", "开票", "发票抬头", "增值税"],
    "order_status": ["订单", "查一下", "帮我看看", "订单到哪", "收货", "还没收到", "订单状态"],
    "inventory": ["有没有货", "有货吗", "什么时候有货", "缺货", "库存", "还有货", "补货"],
    "price_discount": ["优惠", "便宜", "打折", "降价", "活动价", "能不能便宜", "便宜点"],
    "product_info": ["尺寸", "大小", "规格", "颜色", "款式", "材质", "是什么材质", "纯棉"],
    "shipping_addr": ["地址", "改地址", "收货地址", "寄到", "发到"],
}

def desegment(text):
    return text.replace(" ", "")

def extract_queries(filepath, max_samples=50000):
    categorized = defaultdict(list)

    with open(filepath, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= max_samples:
                break

            parts = line.strip().split("\t")
            if len(parts) < 4:
                continue

            query = desegment(parts[2])
            response = desegment(parts[3])

            for cat_name, keywords in CATEGORIES.items():
                for kw in keywords:
                    if kw in query or kw in response:
                        if len(query) >= 5 and len(query) <= 100:
                            categorized[cat_name].append({
                                "query": query,
                                "response": response,
                            })
                        break

    return categorized

def main():
    print("Extracting queries from ECD dataset...")

    all_categorized = defaultdict(list)

    for split in ["train.txt", "dev.txt", "test.txt"]:
        filepath = DATA_DIR / split
        if filepath.exists():
            print(f"Processing {split}...")
            categorized = extract_queries(filepath)
            for cat, items in categorized.items():
                all_categorized[cat].extend(items)

    print("\n=== Category Statistics ===")
    for cat, items in sorted(all_categorized.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"{cat}: {len(items)} samples")

    print(f"\nTotal unique categories: {len(all_categorized)}")

    output_file = OUTPUT_DIR / "user_queries_by_category.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_categorized, f, ensure_ascii=False, indent=2)

    print(f"\nSaved to: {output_file}")

    sample_file = OUTPUT_DIR / "sample_queries.txt"
    with open(sample_file, "w", encoding="utf-8") as f:
        for cat, items in sorted(all_categorized.items(), key=lambda x: len(x[1]), reverse=True):
            f.write(f"\n{'='*50}\n")
            f.write(f"Category: {cat} ({len(items)} samples)\n")
            f.write(f"{'='*50}\n")
            for item in items[:20]:
                f.write(f"User: {item['query']}\n")
                f.write(f"Agent: {item['response']}\n\n")

    print(f"Sample saved to: {sample_file}")

if __name__ == "__main__":
    main()
