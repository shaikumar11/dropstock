"""Table definitions shared by local dev and tests.

In AWS the same tables are created by template.yaml.
"""
import boto3

from . import config


def create_tables():
    ddb = boto3.client("dynamodb", region_name=config.REGION)
    for name in (config.PRODUCTS_TABLE, config.RESERVATIONS_TABLE):
        ddb.create_table(
            TableName=name,
            AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
            BillingMode="PAY_PER_REQUEST",
        )
