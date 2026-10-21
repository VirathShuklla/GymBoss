import { useEffect, useState } from "react";
import api from "./api";
import { isNative } from "./inApp";
import { downloadBlob } from "./files";

export const fileUrl = (url) => (url ? `${process.env.REACT_APP_BACKEND_URL}${url}` : "");

export const MAX_UPLOAD_BYTES = 5 * 1024 * 1024;

export async function uploadFile(file, kind = "attachment") {
  if (file.size > MAX_UPLOAD_BYTES) throw new Error("File too large (max 5 MB)");
  const fd = new FormData();
  fd.append("file", file);
  fd.append("kind", kind);
  const { data } = await api.post("/uploads", fd, { headers: { "Content-Type": "multipart/form-data" } });
  return data;
}

const apiPath = (url) => url.replace(/^\/api/, "");

// Protected files (/api/files/...) need auth. Web sends cookies with <img>; native apps have no cookies,
// so the file is fetched through the authenticated client and shown from a local object URL.
export function useProtectedUrl(url) {
  const [src, setSrc] = useState(url && !isNative() ? fileUrl(url) : "");
  useEffect(() => {
    if (!url) { setSrc(""); return undefined; }
    if (!isNative()) { setSrc(fileUrl(url)); return undefined; }
    let objectUrl = "";
    let alive = true;
    api.get(apiPath(url), { responseType: "blob" }).then(({ data }) => {
      objectUrl = URL.createObjectURL(data);
      if (alive) setSrc(objectUrl);
    }).catch(() => setSrc(""));
    return () => { alive = false; if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [url]);
  return src;
}

export function ProtectedImg({ url, ...props }) {
  const src = useProtectedUrl(url);
  return src ? <img src={src} {...props} /> : <span className={props.className} data-testid={props["data-testid"]} />;
}

export async function openProtectedFile(url, filename = "attachment") {
  if (!isNative()) { window.open(fileUrl(url), "_blank", "noopener,noreferrer"); return; }
  const { data } = await api.get(apiPath(url), { responseType: "blob" });
  await downloadBlob(data, filename);
}
