# 官方API文档汇总

本文档记录各平台官方API字段定义，作为 fixtures/ 目录的参考依据。

**重要说明**：
- fixtures/ 目录下的 JSON 文件是官方API的真实payload
- fixtures 必须与本文档字段保持一致
- official-sim-server 必须从 fixtures/ 加载，而非硬编码函数
- LLM 不可用于定义"官方真相"，真相来源只能是 fixtures

---

## 淘宝 taobao.trade.fullinfo.get

**官方文档**: https://jaq-doc.alibaba.com/doc2/apiDetail.htm?apiId=54

### 订单状态 status
- TRADE_NO_CREATE_PAY: 没有创建支付宝交易
- WAIT_BUYER_PAY: 等待买家付款
- WAIT_SELLER_SEND_GOODS: 等待卖家发货
- WAIT_BUYER_CONFIRM_GOODS: 等待买家确认收货
- TRADE_BUYER_SIGNED: 买家已签收
- TRADE_FINISHED: 交易成功
- TRADE_CLOSED: 交易关闭
- TRADE_CLOSED_BY_TAOBAO: 由淘宝关闭交易

### 退款状态 refund_status
- NO_REFUND: 没有退款
- WAIT_SELLER_AGREE: 等待卖家同意
- WAIT_BUYER_RETURN_GOODS: 卖家已同意，等待买家退货
- WAIT_SELLER_CONFIRM_GOODS: 买家已退货，等待卖家确认收货
- CLOSED: 退款关闭
- SUCCESS: 退款成功
- SELLER_REFUSE_BUYER: 卖家拒绝退款

### 核心字段
| 字段 | 类型 | 说明 |
|------|------|------|
| tid | Number | 交易编号 |
| status | String | 交易状态 |
| type | String | 交易类型 |
| buyer_open_uid | String | 买家open_uid |
| seller_nick | String | 卖家昵称 |
| buyer_nick | String | 买家昵称 |
| created | Date | 交易创建时间 |
| modified | Date | 交易修改时间 |
| pay_time | Date | 支付时间 |
| consign_time | Date | 发货时间 |
| end_time | Date | 交易结束时间 |
| total_fee | String | 商品总价 |
| payment | String | 实际支付金额 |
| post_fee | String | 邮费 |
| discount_fee | String | 优惠金额 |
| adjust_fee | String | 调整金额 |
| coupon_fee | String | 红包金额 |
| point_fee | String | 积分抵扣金额 |
| tmall_coupon_fee | String | 天猫红包金额 |
| has_yfx | Boolean | 是否有订单熔断 |
| yfx_fee | String | 订单熔断金额 |
| yfx_id | String | 订单熔断ID |
| logistics_type | Number | 物流类型 |
| step_trade_status | String | 分阶段状态 |
| step_paid_fee | String | 分阶段已付金额 |
| buyer_message | String | 买家留言 |
| seller_memo | String | 卖家备注 |
| receiver_name | String | 收货人姓名 |
| receiver_mobile | String | 收货人手机号 |
| receiver_phone | String | 收货人固定电话 |
| receiver_state | String | 收货人省份 |
| receiver_city | String | 收货人城市 |
| receiver_district | String | 收货人区/县 |
| receiver_address | String | 收货人详细地址 |
| receiver_zip | String | 收货人邮编 |
| orders.order[] | Array | 子订单列表 |
| orders.order[].oid | Number | 子订单编号 |
| orders.order[].num_iid | Number | 商品数字ID |
| orders.order[].title | String | 商品标题 |
| orders.order[].price | String | 商品价格 |
| orders.order[].num | Number | 购买数量 |
| orders.order[].sku_id | String | SKU ID |
| orders.order[].sku_properties_name | String | SKU属性 |
| orders.order[].item_meal_name | String | 套餐名称 |
| orders.order[].pic_path | String | 图片路径 |
| orders.order[].pic_url | String | 图片URL |
| orders.order[].refund_status | String | 退款状态 |
| orders.order[].status | String | 子订单状态 |
| orders.order[].payment | String | 子订单实付金额 |
| orders.order[].discount_fee | String | 子订单优惠金额 |
| orders.order[]. adjust_fee | String | 子订单调整金额 |
| orders.order[].coupon_fee | String | 子订单优惠券金额 |
| orders.order[].point_fee | String | 子订单积分抵扣金额 |
| orders.order[].logistics_company | String | 物流公司 |
| orders.order[].invoice_no | String | 物流单号 |
| orders.order[].is_oversold | Boolean | 是否超卖 |

## 京东 jingdong.order.get

**官方文档**: https://opendj.jd.com/staticnew/widgets/theGinseng/esOrderQuery.html

### 订单状态 orderStatus (实物类)
- 20010: 锁定
- 20020: 用户取消
- 20040: 系统取消
- 31000: 等待付款
- 31010: 等待付款确认
- 32000: 等待出库
- 32010: 已出库
- 33030: 站点收货
- 33040: 配送中
- 33050: 待自提
- 33060: 已妥投
- 34000: 京东已收款
- 34010: 商家已收款
- 90000: 完成

### 核心字段
| 字段 | 类型 | 说明 |
|------|------|------|
| orderId | Long | 订单号 |
| srcOrderId | String | 来源订单号 |
| srcPlatId | Long | 来源平台id |
| srcOrderType | Integer | 来源订单类型 |
| srcInnerType | Integer | 内部订单来源类型 |
| srcInnerOrderId | Long | 内部订单来源订单号 |
| orderType | Integer | 订单类型 |
| orderStockOwner | Integer | 订单库存归属 |
| orderSkuType | Integer | 订单商品类型 |
| orderStatus | Integer | 订单状态 |
| orderStatusTime | Date | 订单状态最新更改时间 |
| orderStartTime | Date | 下单时间 |
| orderPurchaseTime | Date | 订单成交时间 |
| orderAgingType | Integer | 订单时效类型 |
| orderPreDeliveryTime | Date | 预计送达时间 |
| orderPreStartDeliveryTime | Date | 预计送达开始时间 |
| orderPreEndDeliveryTime | Date | 预计送达结束时间 |
| orderCancelTime | Date | 订单取消时间 |
| orderCancelRemark | String | 订单取消备注 |
| orderDeleteTime | Date | 订单删除时间 |
| orderIsClosed | tinyint | 订单是否关闭 |
| orderCloseTime | Date | 订单关闭时间 |
| orgCode | String | 组织编号 |
| popVenderId | String | pop商家编号 |
| buyerPinType | Integer | 买家账号类型 |
| buyerPin | String | 买家账号 |
| buyerNickName | String | 买家昵称(已停用) |
| buyerFullName | String | 收货人名称 |
| buyerFullAddress | String | 收货人详细地址 |
| buyerTelephone | String | 收货人电话 |
| buyerMobile | String | 收货人手机号 |
| buyerProvince | String | 省Id |
| buyerCity | String | 市Id |
| buyerCountry | String | 县Id |
| buyerTown | String | 镇Id |
| buyerProvinceName | String | 买家省名称 |
| buyerCityName | String | 买家市名称 |
| buyerCountryName | String | 买家县名称 |
| buyerTownName | String | 买家镇名称 |
| buyerIp | Integer | 买家ip |
| buyerCoordType | Integer | 收货人地址坐标类型 |
| buyerLng | double | 收货人地址坐标经度 |
| buyerLat | double | 收货人地址坐标纬度 |
| produceStationNo | String | 京东门店编号 |
| produceStationName | String | 京东门店名称 |
| produceStationNoIsv | String | 商家门店编号 |
| deliveryStationNo | String | 到家配送门店编号 |
| deliveryStationName | String | 配送门店名称 |
| deliveryStationNoIsv | String | 外部配送门店编号 |
| deliveryType | Integer | 配送类型 |
| deliveryCarrierNo | String | 承运商编号 |
| deliveryCarrierName | String | 承运商名称 |
| deliveryBillNo | String | 承运单号 |
| deliveryPackageWeight | double | 包裹重量 |
| deliveryPackageVolume | double | 包裹体积 |
| deliveryManNo | String | 配送员编号 |
| deliveryManName | String | 配送员姓名 |
| deliveryManPhone | String | 配送员电话 |
| deliveryConfirmTime | Date | 妥投时间 |
| orderPayType | Integer | 订单支付类型 |
| orderTakeSelfCode | String | 订单自提码 |
| orderTotalMoney | Long | 订单总金额 |
| orderDiscountMoney | Long | 订单优惠总金额 |
| orderFreightMoney | Long | 订单运费总金额 |
| orderGoodsMoney | Long | 订单货款总金额 |
| orderBuyerPayableMoney | Long | 用户应付金额 |
| orderVenderChargeMoney | Long | 商家再收金额 |
| packagingMoney | Long | 包装金额 |
| orderBalanceUsed | Long | 余额支付金额 |
| orderInvoiceOpenMark | Integer | 订单开发票标识 |
| orderFinanceOrgCode | Integer | 订单结算财务机构号 |
| isJDGetcash | tinyint | 是否京东收款 |
| adjustIsExists | tinyint | 是否存在调整单 |
| adjustCount | Integer | 调整次数记录 |
| adjustId | Long | 最新确认单id |
| orderJingdouMoney | Long | 京豆金额 |
| payChannel | Integer | 支付渠道 |
| isDeleted | Boolean | 用户删除 |
| isGroupon | Boolean | 是否拼团订单 |
| preTransmissionTime | Date | 预计下发时间 |
| hasTransferred | Boolean | 下发标识 |
| orderInvoiceType | String | 发票类型 |
| orderInvoiceTitle | String | 发票抬头 |
| orderInvoiceContent | String | 发票内容 |
| orderBuyerRemark | String | 订单买家备注 |
| orderVenderRemark | String | 订单商家备注 |
| orderDeliveryRemark | String | 订单配送备注 |
| orderCustomerServiceRemark | String | 订单客服备注 |
| businessTag | String | 业务标识 |
| specialServiceTag | String | 特殊服务标签 |
| cartId | String | 购物车id |
| equipmentId | String | 设备id |
| buyerPoi | String | 用户poi |
| businessTagId | Integer | 行业标签id |
| ordererName | String | 订购人姓名 |
| ordererMobile | String | 订购人电话 |
| appVersion | String | app版本号 |
| artificerPortraitUrl | String | 技师头像URL |
| grouponId | Long | 拼团团Id |
| product[] | List | 商品列表 |
| discount[] | List | 优惠列表 |

## 小红书 order.getOrderDetail

**官方文档**: https://xiaohongshu.apifox.cn/api-24201582

### 订单状态 orderStatus
- 1: 已下单待付款
- 2: 已支付处理中
- 3: 清关中
- 4: 待发货
- 5: 部分发货
- 6: 待收货
- 7: 已完成
- 8: 已关闭
- 9: 已取消
- 10: 换货申请中

### 售后状态 orderAfterSalesStatus
- 1: 无售后
- 2: 售后处理中
- 3: 售后完成
- 4: 售后关闭

### 核心字段
| 字段 | 类型 | 说明 |
|------|------|------|
| orderId | String | 订单ID |
| outOrderId | String | 外部订单ID |
| orderType | Integer | 订单类型 |
| orderTypeDesc | String | 订单类型描述 |
| orderStatus | Integer | 订单状态 |
| statusDesc | String | 状态描述 |
| orderAfterSalesStatus | Integer | 售后状态 |
| totalAmount | Integer | 订单总金额(分) |
| payAmount | Integer | 支付金额(分) |
| postAmount | Integer | 运费(分) |
| discountAmount | Integer | 优惠金额(分) |
| taxAmount | Integer | 税金(分) |
| actuallyPayAmount | Integer | 实付金额(分) |
| buyerNick | String | 买家昵称 |
| zoneCodes | Array | 区域编码列表 |
| transferExtendInfo | Object | 转单扩展信息 |
| internationalExpressNo | String | 国际快递单号 |
| orderDeclaredAmount | String | 订单申报金额 |
| paintMarker | String | 涂鸦标记 |
| collectionPlace | String | 集货地 |
| threeSegmentCode | String | 三段码 |
| openAddressId | String | 开放地址ID |
| totalTaxAmount | Integer | 总税金 |
| totalNetWeight | Integer | 总净重 |
| itemTag | String | 商品标签 |
| channel | String | 渠道 |
| originalPackageId | String | 原包裹ID |
| totalPayAmount | Integer | 总支付金额 |
| unpack | Boolean | 是否拆包 |
| expressTrackingNo | String | 快递追踪号 |
| expressCompanyCode | String | 快递公司编码 |
| productValue | Integer | 订单价值 |
| shippingFee | Integer | 运费 |
| receiverName | String | 收件人姓名 |
| receiverPhone | String | 收件人手机 |
| receiverAddress | String | 收件人地址 |
| productItems[] | Array | 商品列表 |
| productItems[].itemId | String | 商品ID |
| productItems[].outItemId | String | 外部商品ID |
| productItems[].skuId | String | SKU ID |
| productItems[].outSkuId | String | 外部SKU ID |
| productItems[].itemName | String | 商品名称 |
| productItems[].skuName | String | SKU名称 |
| productItems[].itemCount | Integer | 商品数量 |
| productItems[].price | Integer | 商品价格(分) |
| productItems[].discountAmount | Integer | 优惠金额(分) |
| productItems[].taxAmount | Integer | 税金(分) |
| productItems[].actuallyPayAmount | Integer | 实付金额(分) |
| productItems[].picUrl | String | 图片URL |
| logistics | Object | 物流信息 |
| logistics.logisticsCompany | String | 物流公司 |
| logistics.trackingNo | String | 追踪号 |
| logistics.status | String | 物流状态 |
| logistics.deliveryStatus | Integer | 配送状态 |
| createTime | Integer | 创建时间(时间戳) |
| payTime | Integer | 支付时间(时间戳) |
| confirmTime | Integer | 确认时间(时间戳) |
| deliveryTime | Integer | 发货时间(时间戳) |
| cancelTime | Integer | 取消时间(时间戳) |
| cancelReason | String | 取消原因 |

## 抖店 /order/orderDetail

**官方文档**: https://op.jinritemai.com/docs/api-docs/172/1738

### 订单状态 order_status
- 10: 待付款
- 20: 已付款
- 30: 已付款(待发货)
- 100: 已发货
- 110: 已履约
- 120: 已完成
- 130: 取消中
- 140: 已取消
- 150: 退款中
- 160: 退款完成
- 170: 退款拒绝

### 核心字段
| 字段 | 类型 | 说明 |
|------|------|------|
| order_id | String | 订单ID |
| out_order_id | String | 外部订单ID |
| shop_id | Integer | 店铺ID |
| shop_name | String | 店铺名称 |
| order_status | Integer | 订单状态 |
| order_status_desc | String | 订单状态描述 |
| create_time | Integer | 创建时间(秒时间戳) |
| update_time | Integer | 更新时间(秒时间戳) |
| pay_time | Integer | 支付时间(秒时间戳) |
| confirm_time | Integer | 确认时间(秒时间戳) |
| consign_time | Integer | 发货时间(秒时间戳) |
| finish_time | Integer | 完成时间(秒时间戳) |
| cancel_time | Integer | 取消时间(秒时间戳) |
| cancel_reason | String | 取消原因 |
| order_amount | Object | 订单金额信息 |
| order_amount.total_amount | Integer | 订单总金额(分) |
| order_amount.pay_amount | Integer | 支付金额(分) |
| order_amount.freight_amount | Integer | 运费金额(分) |
| order_amount.discount_amount | Integer | 优惠金额(分) |
| order_amount.tax_amount | Integer | 税金金额(分) |
| order_amount.actually_pay_amount | Integer | 实付金额(分) |
| order_amount.platform_cost_amount | Integer | 平台承担金额(分) |
| order_amount.seller_cost_amount | Integer | 商家承担金额(分) |
| receiver | Object | 收货人信息 |
| receiver.name | String | 收货人姓名 |
| receiver.phone | String | 收货人手机号 |
| receiver.mobile | String | 备用联系方式 |
| receiver.province | String | 省份 |
| receiver.city | String | 城市 |
| receiver.district | String | 区县 |
| receiver.address | String | 详细地址 |
| receiver.zip_code | String | 邮编 |
| product_items[] | Array | 商品列表 |
| product_items[].product_id | String | 商品ID |
| product_items[].out_product_id | String | 外部商品ID |
| product_items[].sku_id | String | SKU ID |
| product_items[].out_sku_id | String | 外部SKU ID |
| product_items[].product_name | String | 商品名称 |
| product_items[].sku_name | String | SKU名称 |
| product_items[].product_count | Integer | 商品数量 |
| product_items[].product_price | Integer | 商品价格(分) |
| product_items[].sku_price | Integer | SKU价格(分) |
| product_items[].discount_amount | Integer | 优惠金额(分) |
| product_items[].tax_amount | Integer | 税金(分) |
| product_items[].actually_pay_amount | Integer | 实付金额(分) |
| product_items[].pic_url | String | 商品图片 |
| delivery_info | Object | 物流信息 |
| delivery_info.company_name | String | 物流公司名称 |
| delivery_info.tracking_no | String | 物流单号 |
| delivery_info.delivery_status | Integer | 配送状态 |
| delivery_info.delivery_status_desc | String | 配送状态描述 |
| after_sale_status | Integer | 售后状态 |
| buyer_message | String | 买家留言 |
| seller_memo | String | 卖家备注 |
| order_tag | Object | 订单标签 |

## 快手 open.order.detail

**官方文档**: https://open.kwaixiaodian.com/docs/api?apiName=open.order.detail&version=1

### 订单状态 orderStatus
- 1: 待付款
- 2: 已付款(待发货)
- 3: 已发货(配送中)
- 4: 已发货(待收货)
- 5: 已完成
- 6: 已取消
- 7: 退款中
- 8: 退款完成
- 9: 退款拒绝

### 核心字段
| 字段 | 类型 | 说明 |
|------|------|------|
| orderId | String | 订单ID |
| orderNo | String | 订单编号 |
| orderStatus | Integer | 订单状态 |
| statusDesc | String | 状态描述 |
| totalAmount | Integer | 订单总金额(分) |
| payAmount | Integer | 支付金额(分) |
| freightAmount | Integer | 运费(分) |
| discountAmount | Integer | 优惠金额(分) |
| buyerNick | String | 买家昵称 |
| receiver | Object | 收货人信息 |
| receiver.name | String | 收货人姓名 |
| receiver.phone | String | 收货人手机号 |
| receiver.province | String | 省份 |
| receiver.city | String | 城市 |
| receiver.district | String | 区县 |
| receiver.address | String | 详细地址 |
| productItems[] | Array | 商品列表 |
| productItems[].itemId | String | 商品ID |
| productItems[].itemName | String | 商品名称 |
| productItems[].itemCount | Integer | 商品数量 |
| productItems[].price | Integer | 价格(分) |
| productItems[].skuId | String | SKU ID |
| productItems[].skuName | String | SKU名称 |
| productItems[].itemType | Integer | 商品类型 |
| productItems[].itemPrevInfo | Object | 商品预信息 |
| productItems[].goodsCode | String | 商品编码 |
| productItems[].warehouseCode | String | 仓库编码 |
| logistics | Object | 物流信息 |
| logistics.company | String | 物流公司 |
| logistics.companyCode | String | 物流公司编码 |
| logistics.trackingNo | String | 物流单号 |
| logistics.status | String | 物流状态 |
| createTime | Integer | 创建时间(时间戳) |
| payTime | Integer | 支付时间(时间戳) |
| deliveryTime | Integer | 发货时间(时间戳) |
| confirmTime | Integer | 确认时间(时间戳) |
| finishTime | Integer | 完成时间(时间戳) |
| cancelTime | Integer | 取消时间(时间戳) |
| deliveryStatus | Integer | 配送状态 |
| refundStatus | Integer | 退款状态 |
| cpsInfo | Object | CPS信息(已停用) |
| enablePromotion | Boolean | 是否参与分销 |
| promotionAmount | Integer | 预计分销金额(分) |
| openId | String | 用户open id |

## 企微客服 wecom.kf.customer_msg.list

**官方文档**: https://kf.weixin.qq.com/api/doc/path/94745

### 消息来源 origin
- 3: 微信客户发送的消息
- 4: 系统推送的事件消息
- 5: 接待人员在企业微信客户端发送的消息

### 核心字段
| 字段 | 类型 | 说明 |
|------|------|------|
| msg_list | Array | 消息列表 |
| msg_list[].msgid | String | 消息ID |
| msg_list[].action | String | 动作 |
| msg_list[].msg_type | String | 消息类型 |
| msg_list[].content | String | 消息内容 |
| msg_list[].from_userid | String | 发送者userid |
| msg_list[].origin | Integer | 消息来源 |
| msg_list[].create_time | Integer | 创建时间 |
| msg_list[].conversation_id | String | 会话ID |
| msg_list[].scene | String | 场景 |

### 会话字段
| 字段 | 类型 | 说明 |
|------|------|------|
| conversation_id | String | 会话ID |
| open_kfid | String | 客服账号ID |
| external_userid | String | 微信客户userid |
| status | String | 会话状态 |
| welcome_code | String | 欢迎码 |
| scene | String | 场景 |
| customer | Object | 客户信息 |
| customer.external_userid | String | 客户userid |
| customer.nickname | String | 客户昵称 |
| customer.avatar | String | 客户头像 |
| servicer | Object | 客服信息 |
| servicer.userid | String | 客服userid |
| servicer.name | String | 客服姓名 |
| welcome_msg | String | 欢迎语 |
| create_time | Integer | 创建时间 |
| update_time | Integer | 更新时间 |
| latest_msg | Object | 最新消息 |
| latest_msg.msgid | String | 消息ID |
| latest_msg.msg_type | String | 消息类型 |
| latest_msg.content | String | 消息内容 |
| latest_msg.send_time | Integer | 发送时间 |
