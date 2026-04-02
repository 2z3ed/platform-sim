import sys
import logging
from pathlib import Path

_root = Path(__file__).parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

_platform_sim_root = _root.parent.parent
if str(_platform_sim_root) not in sys.path:
    sys.path.insert(0, str(_platform_sim_root))

import uvicorn
from fastapi import FastAPI, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from api.routes.conversation_studio import router as conversation_studio_router

logger = logging.getLogger("ai-orchestrator")

app = FastAPI(
    title="AI Orchestrator",
    description="AI Orchestrator for Customer Service Simulation",
    version="0.1.0",
)

app.include_router(conversation_studio_router)


class SuggestReplyRequest(BaseModel):
    conversation_id: str
    platform: str
    user_message: str
    conversation_history: Optional[List[dict]] = []


class SuggestReplyResponse(BaseModel):
    suggestions: List[str]


ORDER_STATUS_SUGGESTIONS: Dict[str, Dict[str, List[str]]] = {
    "jd": {
        "WAIT_BUYER_PAY": [
            "您的订单已创建，请尽快完成付款",
            "付款后我们将立即为您安排发货",
        ],
        "WAIT_SELLER_STOCK": [
            "您的订单已付款，正在准备发货中",
            "商品正在打包，预计24小时内发货",
        ],
        "WAIT_BUYER_CONFIRM": [
            "您的包裹已发货，正在运送途中",
            "包裹正在配送中，请注意查收",
        ],
        "FINISHED": [
            "交易已完成，感谢您的购买！",
            "欢迎再次光临京东～",
        ],
    },
    "taobao": {
        "WAIT_BUYER_PAY": [
            "亲爱的买家，您的订单已创建，请尽快完成付款哦～",
            "您的订单等待付款中，付款后可立即发货",
        ],
        "WAIT_SELLER_SEND_GOODS": [
            "您的订单已付款，商家正在准备发货中",
            "商家正在打包商品，预计24小时内发货",
        ],
        "WAIT_BUYER_CONFIRM_GOODS": [
            "您的包裹已发货，正在运送途中",
            "包裹已发出，预计3-5天送达",
        ],
        "TRADE_FINISHED": [
            "交易已完成，感谢您的购买！",
            "欢迎再次光临本店～",
        ],
    },
}


def _get_suggestions(platform: str, user_message: str) -> List[str]:
    suggestions = []
    
    if "退款" in user_message or "退货" in user_message:
        suggestions = [
            "您希望申请退款，请问是什么原因呢？",
            "了解您的退款需求，请问方便说明一下原因吗？",
        ]
    elif "物流" in user_message or "发货" in user_message or "到哪" in user_message:
        suggestions = [
            "我来帮您查询一下物流信息",
            "正在为您查看包裹位置",
        ]
    elif "取消" in user_message:
        suggestions = [
            "了解您想取消订单，请问是有什么问题吗？",
            "如需取消订单，请确认是否已付款",
        ]
    else:
        platform_suggestions = ORDER_STATUS_SUGGESTIONS.get(platform, {})
        if platform_suggestions:
            for status_suggestions in platform_suggestions.values():
                suggestions.extend(status_suggestions[:1])
        
        if not suggestions:
            suggestions = [
                "您好，请问有什么可以帮助您的？",
                "请问您想了解订单的什么信息？",
            ]
    
    return suggestions[:3]


@app.post("/api/ai/suggest-reply", response_model=SuggestReplyResponse)
async def suggest_reply(request: SuggestReplyRequest):
    suggestions = _get_suggestions(request.platform, request.user_message)
    return SuggestReplyResponse(suggestions=suggestions)


DEPRECATION_MESSAGE = {
    "code": "410",
    "message": "This endpoint has been retired. Use official-sim-server at http://localhost:9001/official-sim/query/* instead.",
    "data": None,
}


@app.get("/official-sim/query/orders/{order_id}")
async def get_order(order_id: str, platform: str = Query(...)):
    logger.warning("RETIRED: /official-sim/query/orders/%s called on ai-orchestrator. Migrate to official-sim-server:9001", order_id)
    raise HTTPException(status_code=410, detail=DEPRECATION_MESSAGE)


@app.get("/official-sim/query/orders/{order_id}/shipment")
async def get_shipment(order_id: str, platform: str = Query(...)):
    logger.warning("RETIRED: /official-sim/query/orders/%s/shipment called on ai-orchestrator. Migrate to official-sim-server:9001", order_id)
    raise HTTPException(status_code=410, detail=DEPRECATION_MESSAGE)


@app.get("/official-sim/query/orders/{order_id}/refund")
async def get_refund(order_id: str, platform: str = Query(...)):
    logger.warning("RETIRED: /official-sim/query/orders/%s/refund called on ai-orchestrator. Migrate to official-sim-server:9001", order_id)
    raise HTTPException(status_code=410, detail=DEPRECATION_MESSAGE)


@app.get("/official-sim/query/users")
async def list_users(platform: str = Query(...)):
    logger.warning("RETIRED: /official-sim/query/users called on ai-orchestrator. Migrate to official-sim-server:9001")
    raise HTTPException(status_code=410, detail=DEPRECATION_MESSAGE)


static_dir = _root / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
async def index():
    return FileResponse(str(static_dir / "conversation_studio.html"))


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "service": "ai-orchestrator"}


if __name__ == "__main__":
    import socket
    config = uvicorn.Config(app, host="0.0.0.0", port=9000)
    server = uvicorn.Server(config)
    server.run()
