import api from "./api";

export const fileUrl = (url) => (url ? `${process.env.REACT_APP_BACKEND_URL}${url}` : "");

export async function uploadFile(file, kind = "attachment") {
  const fd = new FormData();
  fd.append("file", file);
  fd.append("kind", kind);
  const { data } = await api.post("/uploads", fd, { headers: { "Content-Type": "multipart/form-data" } });
  return data;
}
