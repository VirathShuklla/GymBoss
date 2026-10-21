import { Filesystem, Directory } from "@capacitor/filesystem";
import { Share } from "@capacitor/share";
import api, { apiError } from "./api";
import { isNative } from "./inApp";

const toBase64 = (blob) => new Promise((resolve, reject) => {
  const r = new FileReader();
  r.onload = () => resolve(String(r.result).split(",")[1]);
  r.onerror = reject;
  r.readAsDataURL(blob);
});

// Native apps: write the file to the app cache and open the OS share/save sheet (Files, Drive, WhatsApp...).
async function nativeShare(blob, filename, text) {
  const { uri } = await Filesystem.writeFile({ path: filename, data: await toBase64(blob), directory: Directory.Cache });
  await Share.share({ title: filename, text, files: [uri], dialogTitle: filename });
}

export async function downloadBlob(blob, filename) {
  if (isNative()) return nativeShare(blob, filename);
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
  await downloadBlob(await fetchReceiptPdf(paymentId), `Receipt-${receiptNo || paymentId.slice(0, 8)}.pdf`);
}

// Shares the PDF via the OS share sheet (WhatsApp etc.) when supported; returns false if it fell back to a download.
export async function shareReceiptPdf(paymentId, receiptNo, text) {
  const blob = await fetchReceiptPdf(paymentId);
  const name = `Receipt-${receiptNo || "payment"}.pdf`;
  if (isNative()) {
    await nativeShare(blob, name, text);
    return true;
  }
  const file = new File([blob], name, { type: "application/pdf" });
  if (navigator.canShare && navigator.canShare({ files: [file] })) {
    await navigator.share({ files: [file], text });
    return true;
  }
  await downloadBlob(blob, file.name);
  return false;
}

// CSV exports go through the authenticated API client (works with cookies on web and Bearer tokens in apps).
export async function downloadExport(dataset, params = {}) {
  const res = await api.get(`/export/${dataset}`, { params, responseType: "blob" });
  const istDay = new Date(Date.now() + 5.5 * 3600 * 1000).toISOString().slice(0, 10);
  await downloadBlob(res.data, `gymboss_${dataset}_${istDay}.csv`);
}

// Blob responses hide the server's JSON error; read it back so the real message is shown.
export async function blobError(err, fallback) {
  const data = err?.response?.data;
  if (data instanceof Blob) {
    try { return apiError({ response: { data: JSON.parse(await data.text()) } }, fallback); } catch (e) { return fallback; }
  }
  return apiError(err, fallback);
}
