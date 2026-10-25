class ValidationError(Exception):
    """Raised when a request body is invalid. Maps to HTTP 400."""


def parse_product(body):
    if not isinstance(body, dict):
        raise ValidationError("Body must be a JSON object")
    name = body.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValidationError("name is required")
    if len(name.strip()) > 80:
        raise ValidationError("name must be at most 80 characters")
    price = body.get("price_cents")
    if not _is_int(price) or price < 0:
        raise ValidationError("price_cents must be a non negative integer")
    stock = body.get("stock")
    if not _is_int(stock) or stock < 0:
        raise ValidationError("stock must be a non negative integer")
    return {"name": name.strip(), "price_cents": price, "stock": stock}


def parse_reservation(body):
    if not isinstance(body, dict):
        raise ValidationError("Body must be a JSON object")
    quantity = body.get("quantity")
    if not _is_int(quantity) or not 1 <= quantity <= 5:
        raise ValidationError("quantity must be an integer between 1 and 5")
    customer = body.get("customer")
    if not isinstance(customer, str) or not customer.strip():
        raise ValidationError("customer is required")
    return {"quantity": quantity, "customer": customer.strip()}


def _is_int(value):
    # bool is a subclass of int, so reject it explicitly
    return isinstance(value, int) and not isinstance(value, bool)
