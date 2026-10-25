# DropStock

A small full stack app for reserving limited product drops without overselling.
React frontend, serverless style Python backend (AWS Lambda handlers) and DynamoDB.

## Why it exists

When many people try to buy the last pairs of a limited drop, a normal read then
write can sell the same stock twice. DropStock uses one DynamoDB transaction that
decrements stock only if enough remains and writes the reservation only if the
`Idempotency-Key` is new. A retry with the same key returns the same reservation
and never takes stock twice.

## Structure

- `backend/app/handlers.py` Lambda handlers for API Gateway HTTP API
- `backend/app/repository.py` all DynamoDB access, including the transaction
- `backend/app/validation.py` request validation
- `backend/local_server.py` runs the handlers over HTTP with in-memory DynamoDB (moto)
- `template.yaml` AWS SAM template with 4 functions, 2 tables and an HTTP API
- `frontend/` React and Vite app with Vitest tests
- `.github/workflows/ci.yml` runs backend and frontend tests and the build

## API

| Method | Path | Notes |
| --- | --- | --- |
| GET | /products | List products sorted by name |
| POST | /products | Body: name, price_cents, stock |
| GET | /products/{id} | 404 if unknown |
| POST | /products/{id}/reserve | Needs `Idempotency-Key` header. Body: quantity 1 to 5, customer. 201 ok, 409 out of stock, 422 key reused with a different request |

## Run locally

```bash
# terminal 1: API on http://localhost:8000
cd backend
pip install -r requirements-dev.txt
python local_server.py

# terminal 2: UI on http://localhost:5173
cd frontend
npm install
npm run dev
```

## Tests

```bash
cd backend && python -m unittest discover -s . -t . -v   # 22 tests
cd frontend && npm test                                  # 6 tests
```

Backend tests run against moto's in-memory DynamoDB, including a test with 8 parallel
requests that proves 10 attempts on 3 items give exactly 3 successes and stock 0.

## Deploying to AWS

`template.yaml` defines the functions, tables and API. Deploy with
`sam build && sam deploy --guided`, then set `VITE_API_URL` to the `ApiUrl` output.
The template has not been deployed yet; tests use moto, not a real AWS account.

## Decisions I would revisit

- Products use a table scan. A real catalogue would need a query pattern or a GSI.
- Reservations never expire. A TTL attribute and a release job would free stock.
- No authentication. Cognito or an authoriser would protect the create endpoint.
