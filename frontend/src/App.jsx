import { useCallback, useEffect, useState } from "react";
import { fetchProducts } from "./api.js";
import ProductCard from "./ProductCard.jsx";

export default function App() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      setProducts(await fetchProducts());
      setError("");
    } catch (err) {
      setError("Could not load products. Is the API running?");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <main>
      <h1>DropStock</h1>
      <p className="subtitle">Reserve limited drops. Stock is held atomically, so no oversell.</p>
      {loading && <p>Loading products...</p>}
      {error && (
        <p role="alert" className="message error">
          {error} <button onClick={load}>Retry</button>
        </p>
      )}
      <ul className="grid">
        {products.map((product) => (
          <ProductCard key={product.id} product={product} onReserved={load} />
        ))}
      </ul>
    </main>
  );
}
