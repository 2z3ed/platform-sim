"""
Odoo order fetcher for official-sim-server.

Reads order facts from Odoo via XML-RPC.
Returns raw Odoo sale.order data.
"""
from typing import Dict, Any, Optional
import xmlrpc.client


class OdooOrderFetcher:
    """Fetches order data from Odoo via XML-RPC."""

    def __init__(
        self,
        base_url: str,
        db: str,
        username: str,
        api_key: str,
        timeout: int = 30,
    ):
        self._base_url = base_url.rstrip("/")
        self._db = db
        self._username = username
        self._api_key = api_key
        self._timeout = timeout
        self._uid: Optional[int] = None
        self._models: Optional[xmlrpc.client.ServerProxy] = None

    def _authenticate(self) -> int:
        """Authenticate and return UID."""
        common = xmlrpc.client.ServerProxy(
            f"{self._base_url}/xmlrpc/2/common",
            allow_none=True,
        )
        uid = common.authenticate(self._db, self._username, self._api_key, {})
        if not uid:
            raise ConnectionError(f"Odoo authentication failed for {self._username}")
        self._uid = uid
        self._models = xmlrpc.client.ServerProxy(
            f"{self._base_url}/xmlrpc/2/object",
            allow_none=True,
        )
        return uid

    def _execute(self, model: str, method: str, *args, **kwargs) -> Any:
        """Execute a method on an Odoo model."""
        if self._models is None:
            self._authenticate()
        return self._models.execute_kw(
            self._db, self._uid, self._api_key, model, method, args, kwargs
        )

    def fetch_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a single sale.order by name (order number).
        Returns raw Odoo fields or None if not found.
        """
        try:
            orders = self._execute(
                "sale.order",
                "search_read",
                domain=[("name", "=", order_id)],
                fields=[
                    "id", "name", "state", "amount_total", "amount_untaxed",
                    "amount_tax", "currency_id", "create_date", "date_order",
                    "partner_id", "partner_shipping_id", "partner_invoice_id",
                    "note", "client_order_ref",
                ],
                limit=1,
            )
            if orders:
                order = orders[0]
                
                # Fetch order lines
                lines = self._execute(
                    "sale.order.line",
                    "search_read",
                    domain=[("order_id", "=", order["id"])],
                    fields=["name", "product_uom_qty", "price_unit"],
                )
                order["order_line"] = lines
                
                # Fetch shipping partner details
                shipping_id = order.get("partner_shipping_id", [None, None])[0]
                if shipping_id:
                    partners = self._execute(
                        "res.partner",
                        "search_read",
                        domain=[("id", "=", shipping_id)],
                        fields=["name", "street", "street2", "city", "state_id", "zip", "phone", "mobile"],
                        limit=1,
                    )
                    if partners:
                        order["partner_shipping_data"] = partners[0]
                
                return order
        except Exception as e:
            raise ConnectionError(f"Failed to fetch order {order_id} from Odoo: {e}")
        return None

    def fetch_orders(self, limit: int = 100) -> list:
        """Fetch a list of sale.orders."""
        try:
            return self._execute(
                "sale.order",
                "search_read",
                domain=[],
                fields=[
                    "id", "name", "state", "amount_total",
                    "currency_id", "create_date", "date_order",
                    "partner_id",
                ],
                limit=limit,
            )
        except Exception as e:
            raise ConnectionError(f"Failed to fetch orders from Odoo: {e}")

    def is_available(self) -> bool:
        """Check if Odoo connection is available."""
        try:
            if self._uid is None:
                self._authenticate()
            return self._uid is not None
        except Exception:
            return False
