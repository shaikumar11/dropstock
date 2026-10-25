import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App.jsx";
import { formatPrice } from "./ProductCard.jsx";

const PRODUCTS = [
  { id: "p1", name: "Air Zoom", price_cents: 11995, stock: 3 },
  { id: "p2", name: "Dunk Retro", price_cents: 9995, stock: 0 },
];

function jsonResponse(status, body) {
  return Promise.resolve({ ok: status < 400, status, json: () => Promise.resolve(body) });
}

describe("DropStock App", () => {
  let fetchMock;

  beforeEach(() => {
    fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shows products with stock and a sold out state", async () => {
    fetchMock.mockReturnValueOnce(jsonResponse(200, { products: PRODUCTS }));
    render(<App />);

    expect(await screen.findByText("Air Zoom")).toBeInTheDocument();
    expect(screen.getByText("3 left")).toBeInTheDocument();
    expect(screen.getByText("Sold out")).toBeInTheDocument();
    const buttons = screen.getAllByRole("button", { name: "Reserve" });
    expect(buttons[1]).toBeDisabled();
  });

  it("shows an error with retry when the API is down", async () => {
    fetchMock.mockReturnValueOnce(Promise.reject(new Error("network")));
    render(<App />);

    expect(await screen.findByRole("alert")).toHaveTextContent("Could not load products");

    fetchMock.mockReturnValueOnce(jsonResponse(200, { products: PRODUCTS }));
    await userEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByText("Air Zoom")).toBeInTheDocument();
  });

  it("blocks reserving without a name and does not call the API", async () => {
    fetchMock.mockReturnValueOnce(jsonResponse(200, { products: PRODUCTS }));
    render(<App />);
    await screen.findByText("Air Zoom");

    await userEvent.click(screen.getAllByRole("button", { name: "Reserve" })[0]);

    expect(screen.getByRole("alert")).toHaveTextContent("Enter your name");
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("reserves with an Idempotency-Key header and refreshes stock", async () => {
    fetchMock
      .mockReturnValueOnce(jsonResponse(200, { products: PRODUCTS }))
      .mockReturnValueOnce(jsonResponse(201, { id: "p1:k", quantity: 2 }))
      .mockReturnValueOnce(
        jsonResponse(200, { products: [{ ...PRODUCTS[0], stock: 1 }, PRODUCTS[1]] })
      );
    render(<App />);
    await screen.findByText("Air Zoom");

    await userEvent.type(screen.getAllByLabelText("Your name")[0], "Asha");
    await userEvent.selectOptions(screen.getAllByLabelText("Quantity")[0], "2");
    await userEvent.click(screen.getAllByRole("button", { name: "Reserve" })[0]);

    expect(await screen.findByRole("status")).toHaveTextContent("Reserved 2 for Asha.");
    const [url, options] = fetchMock.mock.calls[1];
    expect(url).toMatch(/\/products\/p1\/reserve$/);
    expect(options.headers["Idempotency-Key"]).toBeTruthy();
    expect(JSON.parse(options.body)).toEqual({ quantity: 2, customer: "Asha" });
    expect(await screen.findByText("1 left")).toBeInTheDocument();
  });

  it("shows the server message when stock runs out and reuses the key on retry", async () => {
    fetchMock
      .mockReturnValueOnce(jsonResponse(200, { products: PRODUCTS }))
      .mockReturnValueOnce(jsonResponse(409, { error: "Not enough stock" }))
      .mockReturnValueOnce(jsonResponse(409, { error: "Not enough stock" }));
    render(<App />);
    await screen.findByText("Air Zoom");

    await userEvent.type(screen.getAllByLabelText("Your name")[0], "Asha");
    const button = screen.getAllByRole("button", { name: "Reserve" })[0];
    await userEvent.click(button);
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Not enough stock"));
    await userEvent.click(button);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3));

    const firstKey = fetchMock.mock.calls[1][1].headers["Idempotency-Key"];
    const secondKey = fetchMock.mock.calls[2][1].headers["Idempotency-Key"];
    expect(secondKey).toBe(firstKey);
  });
});

describe("formatPrice", () => {
  it("formats cents as rupees", () => {
    expect(formatPrice(11995)).toBe("₹119.95");
  });
});
