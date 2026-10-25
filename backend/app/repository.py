"""All DynamoDB access lives here, so handlers stay small and testable."""
import uuid
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError

from . import config


class OutOfStock(Exception):
    pass


class ProductNotFound(Exception):
    pass


class IdempotencyConflict(Exception):
    """Same Idempotency-Key reused with a different request."""


def _plain(item):
    """DynamoDB returns Decimal for numbers; convert to int for JSON."""
    return {k: int(v) if isinstance(v, Decimal) else v for k, v in item.items()}


class Repository:
    def __init__(self):
        self.client = boto3.client("dynamodb", region_name=config.REGION)
        resource = boto3.resource("dynamodb", region_name=config.REGION)
        self.products = resource.Table(config.PRODUCTS_TABLE)
        self.reservations = resource.Table(config.RESERVATIONS_TABLE)

    def create_product(self, data):
        item = {"id": str(uuid.uuid4()), **data}
        self.products.put_item(Item=item, ConditionExpression="attribute_not_exists(id)")
        return item

    def get_product(self, product_id):
        item = self.products.get_item(Key={"id": product_id}).get("Item")
        return _plain(item) if item else None

    def list_products(self):
        items, kwargs = [], {}
        while True:
            page = self.products.scan(**kwargs)
            items.extend(page["Items"])
            if "LastEvaluatedKey" not in page:
                break
            kwargs["ExclusiveStartKey"] = page["LastEvaluatedKey"]
        return sorted((_plain(i) for i in items), key=lambda i: i["name"].lower())

    def get_reservation(self, reservation_id):
        item = self.reservations.get_item(Key={"id": reservation_id}).get("Item")
        return _plain(item) if item else None

    def reserve(self, product_id, idempotency_key, quantity, customer):
        """Reserve stock atomically.

        One transaction decrements stock only if enough remains AND writes the
        reservation only if this Idempotency-Key was not used before. Either
        both happen or neither does, so stock can never be oversold.
        """
        reservation_id = f"{product_id}:{idempotency_key}"
        existing = self.get_reservation(reservation_id)
        if existing:
            return self._replay(existing, quantity, customer)

        if self.get_product(product_id) is None:
            raise ProductNotFound(product_id)

        try:
            self.client.transact_write_items(
                TransactItems=[
                    {
                        "Update": {
                            "TableName": config.PRODUCTS_TABLE,
                            "Key": {"id": {"S": product_id}},
                            "UpdateExpression": "SET stock = stock - :q",
                            "ConditionExpression": "stock >= :q",
                            "ExpressionAttributeValues": {":q": {"N": str(quantity)}},
                        }
                    },
                    {
                        "Put": {
                            "TableName": config.RESERVATIONS_TABLE,
                            "Item": {
                                "id": {"S": reservation_id},
                                "product_id": {"S": product_id},
                                "quantity": {"N": str(quantity)},
                                "customer": {"S": customer},
                            },
                            "ConditionExpression": "attribute_not_exists(id)",
                        }
                    },
                ]
            )
        except ClientError as err:
            if err.response["Error"]["Code"] != "TransactionCanceledException":
                raise
            # Another request with the same key may have won the race.
            existing = self.get_reservation(reservation_id)
            if existing:
                return self._replay(existing, quantity, customer)
            raise OutOfStock(product_id)

        return self.get_reservation(reservation_id)

    @staticmethod
    def _replay(existing, quantity, customer):
        if existing["quantity"] != quantity or existing["customer"] != customer:
            raise IdempotencyConflict(existing["id"])
        return existing
