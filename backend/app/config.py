import os

REGION = os.environ.get("AWS_REGION", "ap-south-1")
PRODUCTS_TABLE = os.environ.get("PRODUCTS_TABLE", "dropstock-products")
RESERVATIONS_TABLE = os.environ.get("RESERVATIONS_TABLE", "dropstock-reservations")
