import { useState, useCallback } from "react";

export function useFileUpload() {
  const [uploading, setUploading] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<{ name: string; path: string }[]>([]);

  const upload = useCallback(async (file: File) => {
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append("files", file);
      const res = await fetch("/api/upload", { method: "POST", body: fd });
      if (res.ok) {
        const data = await res.json();
        setUploadedFiles((prev) => [...prev, ...data]);
      }
    } finally {
      setUploading(false);
    }
  }, []);

  const clearFiles = useCallback(() => setUploadedFiles([]), []);

  return { uploading, uploadedFiles, upload, clearFiles };
}
