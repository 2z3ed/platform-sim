import random
from typing import Dict, Any
from .base import ReplyAdapter, ReplySource


STUB_REPLIES = {
    "ask_order_status": [
        "您好，已经为您查询，订单正在处理中。",
        "亲，订单这边已经收到了，正在尽快为您备货哦。",
        "订单已确认，我们会尽快为您发货。",
    ],
    "ask_shipment": [
        "您好，快递已经发出，预计3-5天到达。",
        "亲，您的宝贝已经出发啦，路上大约需要3-5天哦。",
        "快递已发货，单号为{tracking_no}，请留意查收。",
    ],
    "ask_refund": [
        "您好，退款申请已收到，我们尽快为您处理。",
        "亲，退款这边已经在办理中了，预计1-3个工作日到账。",
        "退款申请已通过，款项会在1-7个工作日内退回原支付账户。",
    ],
    "refund_progress": [
        "您好，已为您查询，退款正在处理中，请耐心等待。",
        "亲，退款已经在银行处理阶段了，预计很快到账哦。",
    ],
    "complain": [
        "非常抱歉给您带来不便，我们会尽快为您处理。",
        "亲，真的很抱歉，我们这就去催一下。",
    ],
    "product_question": [
        "您好，这款产品是{product_info}，有什么可以帮您了解的？",
        "亲，这款的具体信息是...，请放心购买哦。",
    ],
    "escalate_to_human": [
        "好的，我为您转接人工客服，请稍等。",
        "亲，稍等，我这边帮您联系专业客服人员。",
    ],
    "default": [
        "您好，有什么可以帮您的？",
        "亲，请说～",
        "收到，我帮您看看。",
    ],
}

PLATFORM_STUB_REPLIES = {
    "taobao": STUB_REPLIES,
    "jd": {
        "ask_order_status": [
            "您好，订单已收到，正在为您处理中。",
            "京东订单已确认，我们会尽快为您发货。",
            "您的订单正在配送准备中，请耐心等待。",
        ],
        "ask_shipment": [
            "您好，商品已从京东仓库发出，预计1-3天送达。",
            "快递已出发，京东物流预计1-3天为您送达。",
            "订单已发货，请关注京东APP查看物流进度。",
        ],
        "ask_refund": [
            "您好，退款申请已受理，京东退款处理中。",
            "退款申请已通过，款项将退回原支付方式。",
            "京东退款预计1-7个工作日到账，请留意。",
        ],
        "refund_progress": [
            "已为您查询，退款正在处理中。",
            "退款已进入银行处理阶段，请耐心等待。",
        ],
        "complain": [
            "非常抱歉给您带来不便，京东会尽快为您处理。",
            "对不起，我们马上为您核实处理。",
        ],
        "product_question": [
            "您好，这款京东自营商品信息是{product_info}。",
            "这是京东自营商品，品质有保障哦。",
        ],
        "escalate_to_human": [
            "好的，为您转接京东人工客服。",
            "请稍等，正在为您连接人工服务。",
        ],
        "default": [
            "您好，京东客服为您服务。",
            "有什么可以帮您？",
            "收到，立即为您处理。",
        ],
    },
    "douyin_shop": {
        "ask_order_status": [
            "亲，订单已收到，正在为您准备发货哦～",
            "抖音小店订单已确认，小店正在加急处理中！",
            "您的订单已下单，我们会尽快发出～",
        ],
        "ask_shipment": [
            "快递已从抖音小店发出，预计3-5天到达～",
            "包裹已出发，路上大约3-5天，还请耐心等待哦～",
            "小店已发货，还请关注物流信息～",
        ],
        "ask_refund": [
            "退款申请已收到，小店会尽快为您处理～",
            "亲，退款办理中，预计1-3个工作日到账哦～",
            "退款申请已通过，款项会原路返回的～",
        ],
        "refund_progress": [
            "已为您查询，退款正在处理中哦～",
            "退款在银行处理阶段了，很快到账～",
        ],
        "complain": [
            "非常抱歉让您不开心，小店会马上处理～",
            "对不起亲，我们这就去帮您催一下～",
        ],
        "product_question": [
            "这款抖音小店的商品是{product_info}，小店承诺品质保障～",
            "亲，商品详情是{product_info}，有任何问题随时问小店哦～",
        ],
        "escalate_to_human": [
            "好的，为亲转接小店人工客服～",
            "请稍等，小店人工客服马上为您服务～",
        ],
        "default": [
            "亲，有什么可以帮到您的呢～",
            "小店客服为您服务哦～",
            "收到，小店马上为您处理～",
        ],
    },
    "wecom_kf": {
        "ask_order_status": [
            "您好，已为您查询，订单状态如下。",
            "订单已确认，我们正在处理中。",
            "会话已记录，订单查询结果如下。",
        ],
        "ask_shipment": [
            "您好，货物已发出，请留意查收。",
            "快递已安排，预计送达时间已通知您。",
            "发货信息已更新，请确认收货地址。",
        ],
        "ask_refund": [
            "退款申请已受理，我们会尽快处理。",
            "退款流程已启动，请等待到账通知。",
            "退款申请已通过，款项将原路返回。",
        ],
        "refund_progress": [
            "退款正在处理中，请耐心等待。",
            "退款已进入财务审核阶段。",
        ],
        "complain": [
            "非常抱歉给您带来困扰，我们会立即处理。",
            "感谢您的反馈，我们会尽快核实并解决。",
        ],
        "product_question": [
            "关于产品{product_info}，请问有什么想了解的？",
            "产品信息如下，请查阅。",
        ],
        "escalate_to_human": [
            "好的，正在为您转接人工客服。",
            "请稍候，人工客服将直接为您服务。",
        ],
        "default": [
            "您好，企业微信客服为您服务。",
            "请问有什么可以帮您？",
            "已收到，正在为您处理。",
        ],
    },
}


class StubReplyAdapter(ReplyAdapter):
    def __init__(self, custom_replies: Dict[str, list] = None, platform: str = "taobao"):
        self.platform = platform
        self.custom_replies = custom_replies or PLATFORM_STUB_REPLIES.get(platform, STUB_REPLIES)

    def get_reply(
        self,
        run_id: str,
        user_message: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        intent = context.get("intent", "default")
        tracking_no = context.get("tracking_no", "")
        product_info = context.get("product_info", "")

        reply_key = intent if intent in self.custom_replies else "default"
        reply_text = random.choice(self.custom_replies[reply_key])

        reply_text = reply_text.format(
            tracking_no=tracking_no,
            product_info=product_info
        )

        return {
            "text": reply_text,
            "source": ReplySource.STUB.value,
            "run_id": run_id,
            "intent": intent,
            "platform": self.platform,
            "timestamp": self._get_timestamp(),
        }

    def get_source(self) -> ReplySource:
        return ReplySource.STUB

    def _get_timestamp(self) -> str:
        from datetime import datetime
        return datetime.now().isoformat()
