export const sanitizeFilenamePart = (raw: string) => {
  // Windows 不允许的文件名字符：<>:"/\\|?* + 控制字符
  return String(raw || '')
    .replace(/[<>:"/\\|?*\u0000-\u001F]/g, '')
    .replace(/\s+/g, ' ')
    .trim();
};

