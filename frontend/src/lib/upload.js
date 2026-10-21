import api from "./api";

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
