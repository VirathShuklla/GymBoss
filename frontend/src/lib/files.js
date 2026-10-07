import api from "./api";

export function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 3000);
}

const fetchReceiptPdf = async (paymentId) =>
  (await api.get(`/payments/${paymentId}/receipt.pdf`, { responseType: "blob" })).data;

export async function downloadReceiptPdf(paymentId, receiptNo) {
  downloadBlob(await fetchReceiptPdf(paymentId), `Receipt-${receiptNo || paymentId.slice(0, 8)}.pdf`);
}

// Shares the PDF file via the OS share sheet (WhatsApp etc.) when supported; returns false otherwise.
export async function shareReceiptPdf(paymentId, receiptNo, text) {
  const blob = await fetchReceiptPdf(paymentId);
  const file = new File([blob], `Receipt-${receiptNo || "payment"}.pdf`, { type: "application/pdf" });
  if (navigator.canShare && navigator.canShare({ files: [file] })) {
    await navigator.share({ files: [file], text });
    return true;
  }
  downloadBlob(blob, file.name);
  return false;
}
