"""
訂單對話會話管理器 (Order Session Manager)
------------------------------------------
管理每位 LINE 使用者的訂購對話狀態，支援多輪對話流程：
  EXTRACT_ORDER → CHECK_INVENTORY → COLLECT_INFO → CONFIRM_ORDER → 完成
"""

import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ── 狀態常數 ──────────────────────────────────────────────
STATE_EXTRACT_ORDER = "EXTRACT_ORDER"
STATE_CHECK_INVENTORY = "CHECK_INVENTORY"
STATE_COLLECT_INFO = "COLLECT_INFO"
STATE_CONFIRM_ORDER = "CONFIRM_ORDER"

# ── 收件與訂購人資訊收集步驟 ────────────────────────────────
INFO_STEPS = ["name", "phone", "company", "address", "note"]

INFO_PROMPTS = {
    "name":    "請問您的聯絡人姓名是？",
    "phone":   "請提供聯絡電話：",
    "company": "請問您的公司名稱是？（如無請填「個人」）",
    "address": "請提供送貨地址：",
    "note":    "是否有其他訂單備註或特殊要求？（如無請回覆「無」）",
}

INFO_LABELS = {
    "name":    "聯絡人姓名",
    "phone":   "聯絡電話",
    "company": "公司名稱",
    "address": "送貨地址",
    "note":    "訂單備註",
}

# ── 會話超時 ──────────────────────────────────────────────
SESSION_TIMEOUT_MINUTES = 30


@dataclass
class OrderItem:
    """單一訂購品項"""
    product_name: str       # 產品名稱 (e.g. "Basic Fuse Box - Black")
    quantity: int           # 訂購數量
    unit_price: int = 0     # 單價
    stock: int = 0          # 當前庫存


@dataclass
class OrderSession:
    """
    單一使用者的訂購會話。
    追蹤目前的對話狀態、已萃取的品項、以及已收集的收件與聯絡人資訊。
    """
    user_id: str
    state: str = STATE_EXTRACT_ORDER
    items: List[OrderItem] = field(default_factory=list)
    contact_info: Dict[str, str] = field(default_factory=dict)
    info_step_index: int = 0           # 目前收集到第幾個 INFO_STEPS
    created_at: datetime.datetime = field(default_factory=datetime.datetime.now)

    @property
    def is_expired(self) -> bool:
        elapsed = datetime.datetime.now() - self.created_at
        return elapsed > datetime.timedelta(minutes=SESSION_TIMEOUT_MINUTES)

    @property
    def current_info_step(self) -> Optional[str]:
        """目前要收集的資訊欄位名稱，若已收集完畢回傳 None"""
        if self.info_step_index < len(INFO_STEPS):
            return INFO_STEPS[self.info_step_index]
        return None

    @property
    def total_price(self) -> int:
        return sum(item.unit_price * item.quantity for item in self.items)

    def format_order_summary(self) -> str:
        """產生訂單摘要文字"""
        lines = ["📋 訂單摘要：", ""]
        lines.append("【訂購品項】")
        for i, item in enumerate(self.items, 1):
            lines.append(
                f"  {i}. {item.product_name} × {item.quantity}"
                f"（單價 NT${item.unit_price}，小計 NT${item.unit_price * item.quantity}）"
            )
        lines.append(f"\n💰 總金額：NT${self.total_price}")
        lines.append("")
        lines.append("【收件與聯絡人資訊】")
        for key in INFO_STEPS:
            label = INFO_LABELS.get(key, key)
            value = self.contact_info.get(key, "—")
            lines.append(f"  {label}：{value}")
        lines.append("")
        lines.append("請確認以上資訊是否正確：")
        lines.append("  ✅ 輸入「確認」送出訂單")
        lines.append("  ❌ 輸入「取消」放棄訂單")
        return "\n".join(lines)


class OrderSessionManager:
    """
    管理所有使用者的訂購會話。
    以 dict 儲存在記憶體中（未來可換成 Redis 等持久化方案）。
    """

    def __init__(self):
        self._sessions: Dict[str, OrderSession] = {}

    def get_session(self, user_id: str) -> Optional[OrderSession]:
        """取得使用者的會話，若已過期則自動清除"""
        session = self._sessions.get(user_id)
        if session and session.is_expired:
            print(f"⏰ [會話管理] 使用者 {user_id[-5:]} 的訂單會話已過期，自動清除")
            self.clear_session(user_id)
            return None
        return session

    def create_session(self, user_id: str) -> OrderSession:
        """為使用者建立新的訂購會話"""
        session = OrderSession(user_id=user_id)
        self._sessions[user_id] = session
        print(f"🆕 [會話管理] 為使用者 {user_id[-5:]} 建立訂單會話")
        return session

    def clear_session(self, user_id: str):
        """清除使用者的訂購會話"""
        if user_id in self._sessions:
            del self._sessions[user_id]
            print(f"🗑️ [會話管理] 清除使用者 {user_id[-5:]} 的訂單會話")

    def has_active_session(self, user_id: str) -> bool:
        """檢查使用者是否有進行中的訂購會話"""
        return self.get_session(user_id) is not None
