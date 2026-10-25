"""Lambda handlers for an API Gateway HTTP API (payload format 2.0)."""
import json
import logging

from . import validation
from .repository import IdempotencyConflict, OutOfStock, ProductNotFound, Repository

logger = logging.getLogger()
logger.setLevel(logging.INFO)

HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "content-type,idempotency-key",
}


def _response(status, body):
    return {"statusCode": status, "headers": HEADERS, "body": json.dumps(body)}


def _json_body(event):
    raw = event.get("body")
    if not raw:
        raise validation.ValidationError("Request body is required")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        raise validation.ValidationError("Body must be valid JSON")


def _safe(fn):
    """Turn known errors into clean HTTP responses, log the rest."""

    def wrapper(event, context=None):
        try:
            return fn(event, Repository())
        except validation.ValidationError as err:
            return _response(400, {"error": str(err)})
        except ProductNotFound:
            return _response(404, {"error": "Product not found"})
        except OutOfStock:
            return _response(409, {"error": "Not enough stock"})
        except IdempotencyConflict:
            return _response(422, {"error": "Idempotency-Key was already used for a different request"})
        except Exception:
            logger.exception("Unhandled error")
            return _response(500, {"error": "Internal server error"})

    return wrapper


@_safe
def list_products(event, repo):
    return _response(200, {"products": repo.list_products()})


@_safe
def create_product(event, repo):
    data = validation.parse_product(_json_body(event))
    return _response(201, repo.create_product(data))


@_safe
def get_product(event, repo):
    product = repo.get_product(event["pathParameters"]["id"])
    if product is None:
        raise ProductNotFound()
    return _response(200, product)


@_safe
def reserve(event, repo):
    key = (event.get("headers") or {}).get("idempotency-key", "").strip()
    if not key or len(key) > 64:
        raise validation.ValidationError("Idempotency-Key header is required (max 64 characters)")
    data = validation.parse_reservation(_json_body(event))
    reservation = repo.reserve(event["pathParameters"]["id"], key, data["quantity"], data["customer"])
    return _response(201, reservation)
