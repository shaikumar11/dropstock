const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const response = await fetch(`${BASE}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(data.error || `Request failed with ${response.status}`);
    error.status = response.status;
    throw error;
  }
  return data;
}

export function fetchProducts() {
  return request("/products").then((data) => data.products);
}

export function reserveProduct(productId, { quantity, customer }, idempotencyKey) {
  return request(`/products/${productId}/reserve`, {
    method: "POST",
    headers: { "Idempotency-Key": idempotencyKey },
    body: JSON.stringify({ quantity, customer }),
  });
}
