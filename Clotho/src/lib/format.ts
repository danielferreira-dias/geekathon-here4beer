export const formatInteger = (n: number) => new Intl.NumberFormat().format(n);
export const formatQty = (n: number) =>
  new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 }).format(n);
export const formatCurrency = (n: number, currency: string = "USD") =>
  new Intl.NumberFormat(undefined, { style: "currency", currency }).format(n);
export const formatDate = (iso: string) => new Date(iso).toLocaleDateString();
