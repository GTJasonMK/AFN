export const downloadBlob = (blob: Blob, filename: string) => {
  const safeName = String(filename || '').trim() || 'download';
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  try {
    link.href = url;
    link.setAttribute('download', safeName);
    document.body.appendChild(link);
    link.click();
  } finally {
    try {
      link.remove();
    } catch {
      // ignore
    }
    try {
      window.URL.revokeObjectURL(url);
    } catch {
      // ignore
    }
  }
};

export const downloadText = (text: string, filename: string, mimeType = 'text/plain;charset=utf-8') => {
  downloadBlob(new Blob([text], { type: mimeType }), filename);
};

export const downloadJson = (data: unknown, filename: string) => {
  const text = JSON.stringify(data, null, 2);
  downloadText(text, filename, 'application/json;charset=utf-8');
};

