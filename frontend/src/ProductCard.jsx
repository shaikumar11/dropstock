import { useRef, useState } from "react";
import { reserveProduct } from "./api.js";

export function formatPrice(cents) {
  return `₹${(cents / 100).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;
}

export default function ProductCard({ product, onReserved }) {
  const [quantity, setQuantity] = useState(1);
  const [customer, setCustomer] = useState("");
  const [status, setStatus] = useState({ type: "idle", text: "" });
  // One key per attempt: a retry after a network error reuses it, so the
  // server never reserves twice. A new key is made only after success.
  const keyRef = useRef(crypto.randomUUID());

  const soldOut = product.stock === 0;
  const maxQuantity = Math.max(1, Math.min(5, product.stock));

  async function handleSubmit(event) {
    event.preventDefault();
    if (!customer.trim()) {
      setStatus({ type: "error", text: "Enter your name to reserve." });
      return;
    }
    setStatus({ type: "loading", text: "Reserving..." });
    try {
      await reserveProduct(product.id, { quantity, customer: customer.trim() }, keyRef.current);
      keyRef.current = crypto.randomUUID();
      setStatus({ type: "success", text: `Reserved ${quantity} for ${customer.trim()}.` });
      setQuantity(1);
      onReserved();
    } catch (error) {
      setStatus({ type: "error", text: error.message });
    }
  }

  return (
    <li className="card">
      <div className="card-head">
        <h2>{product.name}</h2>
        <span className="price">{formatPrice(product.price_cents)}</span>
      </div>
      <p className={soldOut ? "stock sold-out" : "stock"}>
        {soldOut ? "Sold out" : `${product.stock} left`}
      </p>
      <form onSubmit={handleSubmit}>
        <label>
          Your name
          <input value={customer} onChange={(e) => setCustomer(e.target.value)} disabled={soldOut} />
        </label>
        <label>
          Quantity
          <select
            value={quantity}
            onChange={(e) => setQuantity(Number(e.target.value))}
            disabled={soldOut}
          >
            {Array.from({ length: maxQuantity }, (_, i) => i + 1).map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </label>
        <button type="submit" disabled={soldOut || status.type === "loading"}>
          {status.type === "loading" ? "Reserving..." : "Reserve"}
        </button>
      </form>
      {status.text && status.type !== "loading" && (
        <p role={status.type === "error" ? "alert" : "status"} className={`message ${status.type}`}>
          {status.text}
        </p>
      )}
    </li>
  );
}
