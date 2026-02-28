import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

export type UsePdfPreviewUrlOptions = {
  resetKey: string | null | undefined;
  downloadUrl: string | null | undefined;
  resolveUrl?: (url: string) => string;
  onError?: (error: unknown) => void;
};

const safeRevokeObjectUrl = (url: string | null) => {
  if (!url) return;
  try {
    URL.revokeObjectURL(url);
  } catch {
    // ignore
  }
};

export const usePdfPreviewUrl = (opts: UsePdfPreviewUrlOptions) => {
  const { resetKey, downloadUrl, resolveUrl = (u) => u, onError } = opts;

  const [pdfPreviewOpen, setPdfPreviewOpen] = useState(false);
  const [pdfPreviewUrl, setPdfPreviewUrl] = useState<string | null>(null);
  const pdfPreviewUrlRef = useRef<string | null>(null);

  const clearPreviewUrl = useCallback(() => {
    setPdfPreviewUrl((prev) => {
      safeRevokeObjectUrl(prev);
      return null;
    });
  }, []);

  useEffect(() => {
    pdfPreviewUrlRef.current = pdfPreviewUrl;
  }, [pdfPreviewUrl]);

  useEffect(() => {
    return () => {
      safeRevokeObjectUrl(pdfPreviewUrlRef.current);
    };
  }, []);

  // 章节/项目切换时：关闭预览并释放 blob URL，避免自动触发下载/泄漏
  useEffect(() => {
    setPdfPreviewOpen(false);
    clearPreviewUrl();
  }, [clearPreviewUrl, resetKey]);

  // 当最新 PDF 发生变化时，关闭预览并释放旧 URL
  useEffect(() => {
    setPdfPreviewOpen(false);
    clearPreviewUrl();
  }, [clearPreviewUrl, downloadUrl]);

  // 用户关闭预览时释放 blob URL
  useEffect(() => {
    if (pdfPreviewOpen) return;
    clearPreviewUrl();
  }, [clearPreviewUrl, pdfPreviewOpen]);

  const resolvedDownloadUrl = useMemo(() => {
    const url = (downloadUrl || '').trim();
    if (!url) return '';
    return resolveUrl(url);
  }, [downloadUrl, resolveUrl]);

  useEffect(() => {
    if (!pdfPreviewOpen) return;
    if (!resolvedDownloadUrl) return;
    if (pdfPreviewUrl) return;

    const controller = new AbortController();
    void (async () => {
      try {
        const res = await fetch(resolvedDownloadUrl, { signal: controller.signal });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const blob = await res.blob();
        if (controller.signal.aborted) return;
        const objectUrl = URL.createObjectURL(blob);
        if (controller.signal.aborted) {
          safeRevokeObjectUrl(objectUrl);
          return;
        }
        setPdfPreviewUrl(objectUrl);
      } catch (e: any) {
        if (controller.signal.aborted) return;
        if (e?.name === 'AbortError') return;
        onError?.(e);
        setPdfPreviewOpen(false);
      }
    })();

    return () => {
      try {
        controller.abort();
      } catch {
        // ignore
      }
    };
  }, [onError, pdfPreviewOpen, pdfPreviewUrl, resolvedDownloadUrl]);

  return { pdfPreviewOpen, setPdfPreviewOpen, pdfPreviewUrl };
};

