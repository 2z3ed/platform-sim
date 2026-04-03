"""
Odoo shipment fetcher for official-sim-server.

Reads shipment facts from Odoo stock.picking model.
Returns raw Odoo shipment data.
"""
from typing import Dict, Any, Optional, List
import xmlrpc.client


class OdooShipmentFetcher:
    """Fetches shipment data from Odoo stock.picking via XML-RPC."""

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

    def fetch_shipment_by_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch shipment by sale.order name.
        Returns raw Odoo stock.picking data or None if not found.
        
        Note: origin field may not be reliable, so we search by picking move's sale line.
        """
        try:
            # Try to find picking via origin (sale order name)
            pickings = self._execute(
                "stock.picking",
                "search_read",
                domain=[("origin", "=", order_id)],
                fields=[
                    "id", "name", "origin", "state", "scheduled_date",
                    "date_done", "carrier_id", "carrier_tracking_ref",
                    "location_id", "location_dest_id",
                ],
                limit=1,
            )
            if pickings:
                picking = pickings[0]
                # Fetch carrier details if available
                carrier_id = picking.get("carrier_id")
                if carrier_id and isinstance(carrier_id, list) and len(carrier_id) > 1:
                    carriers = self._execute(
                        "delivery.carrier",
                        "search_read",
                        domain=[("id", "=", carrier_id[0])],
                        fields=["name", "tracking_url"],
                        limit=1,
                    )
                    if carriers:
                        picking["carrier_data"] = carriers[0]
                return picking
            
            # Fallback: search by sale order reference in moves
            orders = self._execute(
                "sale.order",
                "search_read",
                domain=[("name", "=", order_id)],
                fields=["id"],
                limit=1,
            )
            if not orders:
                return None
            
            order_db_id = orders[0]["id"]
            # Find pickings linked to this order via moves
            moves = self._execute(
                "stock.move",
                "search_read",
                domain=[("sale_line_id.order_id", "=", order_db_id)],
                fields=["picking_id"],
                limit=10,
            )
            if moves:
                picking_ids = list(set(m.get("picking_id", [None])[0] for m in moves if m.get("picking_id")))
                if picking_ids and picking_ids[0]:
                    pickings = self._execute(
                        "stock.picking",
                        "search_read",
                        domain=[("id", "=", picking_ids[0])],
                        fields=[
                            "id", "name", "origin", "state", "scheduled_date",
                            "date_done", "carrier_id", "carrier_tracking_ref",
                            "location_id", "location_dest_id",
                        ],
                        limit=1,
                    )
                    if pickings:
                        picking = pickings[0]
                        carrier_id = picking.get("carrier_id")
                        if carrier_id and isinstance(carrier_id, list) and len(carrier_id) > 1:
                            carriers = self._execute(
                                "delivery.carrier",
                                "search_read",
                                domain=[("id", "=", carrier_id[0])],
                                fields=["name", "tracking_url"],
                                limit=1,
                            )
                            if carriers:
                                picking["carrier_data"] = carriers[0]
                        return picking
                        
        except Exception as e:
            raise ConnectionError(f"Failed to fetch shipment for order {order_id} from Odoo: {e}")
        return None

    def fetch_shipment_by_picking_name(self, picking_name: str) -> Optional[Dict[str, Any]]:
        """Fetch a single stock.picking by name."""
        try:
            pickings = self._execute(
                "stock.picking",
                "search_read",
                domain=[("name", "=", picking_name)],
                fields=[
                    "id", "name", "origin", "state", "scheduled_date",
                    "date_done", "carrier_id", "carrier_tracking_ref",
                    "location_id", "location_dest_id",
                ],
                limit=1,
            )
            if pickings:
                picking = pickings[0]
                carrier_id = picking.get("carrier_id", [None, None])[0]
                if carrier_id:
                    carriers = self._execute(
                        "delivery.carrier",
                        "search_read",
                        domain=[("id", "=", carrier_id)],
                        fields=["name", "tracking_url"],
                        limit=1,
                    )
                    if carriers:
                        picking["carrier_data"] = carriers[0]
                return picking
        except Exception as e:
            raise ConnectionError(f"Failed to fetch shipment {picking_name} from Odoo: {e}")
        return None

    def is_available(self) -> bool:
        """Check if Odoo connection is available."""
        try:
            if self._uid is None:
                self._authenticate()
            return self._uid is not None
        except Exception:
            return False