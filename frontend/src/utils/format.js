export function compactNumber(value) {
  return new Intl.NumberFormat("en", { notation: "compact" }).format(value);
}

export function percentage(value) {
  return `${value}%`;
}

export function currency(value) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}
