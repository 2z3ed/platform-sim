"""
Odoo after-sale fetcher for official-sim-server.

Reads after-sale facts from Odoo account.move model.
Returns raw Odoo after-sale data.
"""
from typing import Dict, Any, Optional
import xmlrpc.client


class OdooAfterSaleFetcher:
    """Fetches after-sale/refund data from Odoo account.move via XML-RPC."""

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

    def fetch_aftersale_by_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch after-sale/refund by sale.order name.
        Returns raw Odoo account.move data or None if not found.
        
        Searches for out_refund linked to the order.
        """
        try:
            # First find sale.order id
            orders = self._execute(
                "sale.order",
                "search_read",
                domain=[("name", "=", order_id)],
                fields=["id", "name"],
                limit=1,
            )
            if not orders:
                return None
            
            order_db_id = orders[0]["id"]
            
            # Find account.move (out_refund) linked to this order via invoice_origin
            moves = self._execute(
                "account.move",
                "search_read",
                domain=[
                    ("move_type", "=", "out_refund"),
                    ("invoice_origin", "=", order_id),
                ],
                fields=[
                    "id", "name", "move_type", "state", "invoice_origin",
                    "amount_total", "amount_residual", "date", "create_date",
                    "ref", "narration",
                ],
                limit=1,
            )
            if moves:
                return moves[0]
            
            # Fallback: try to search by sale.order id in more complex way
            # Try via partner or other correlations
            return None
            
        except Exception as e:
            raise ConnectionError(f"Failed to fetch aftersale for order {order_id} from Odoo: {e}")
        return None

    def fetch_aftersale_by_refund_name(self, refund_name: str) -> Optional[Dict[str, Any]]:
        """Fetch a single account.move out_refund by name."""
        try:
            moves = self._execute(
                "account.move",
                "search_read",
                domain=[
                    ("name", "=", refund_name),
                    ("move_type", "=", "out_refund"),
                ],
                fields=[
                    "id", "name", "move_type", "state", "invoice_origin",
                    "amount_total", "amount_residual", "date", "create_date",
                    "ref", "narration",
                ],
                limit=1,
            )
            if moves:
                return moves[0]
        except Exception as e:
            raise ConnectionError(f"Failed to fetch aftersale {refund_name} from Odoo: {e}")
        return None

    def is_available(self) -> bool:
        """Check if Odoo connection is available."""
        try:
            if self._uid is None:
                self._authenticate()
            return self._uid is not None
        except Exception:
            return False