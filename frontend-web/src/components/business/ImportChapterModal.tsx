import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Modal } from '../ui/Modal';
import { BookButton } from '../ui/BookButton';
import { BookInput, BookTextarea } from '../ui/BookInput';
import { useToast } from '../feedback/Toast';
import { writerApi } from '../../api/writer';
import { sanitizeFilenamePart } from '../../utils/sanitizeFilename';

type Encoding = 'utf-8' | 'gb18030';

export const ImportChapterModal: React.FC<{
  projectId: string;
  isOpen: boolean;
  onClose: () => void;
  suggestedChapterNumber: number;
  onImported: (chapterNumber: number) => void | Promise<void>;
}> = ({ projectId, isOpen, onClose, suggestedChapterNumber, onImported }) => {
  const { addToast } = useToast();
  const wasOpenRef = useRef(false);

  const [chapterNumber, setChapterNumber] = useState<number>(1);
  const [chapterTitle, setChapterTitle] = useState('');
  const [titleTouched, setTitleTouched] = useState(false);
  const [chapterContent, setChapterContent] = useState('');
  const [encoding, setEncoding] = useState<Encoding>('utf-8');
  const [fileName, setFileName] = useState('');
  const [fileBuffer, setFileBuffer] = useState<ArrayBuffer | null>(null);
  const [importing, setImporting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const resetForm = useCallback(() => {
    const n = Math.max(1, Number(suggestedChapterNumber) || 1);
    setChapterNumber(n);
    setChapterTitle(`第${n}章`);
    setTitleTouched(false);
    setChapterContent('');
    setEncoding('utf-8');
    setFileName('');
    setFileBuffer(null);
  }, [suggestedChapterNumber]);

  useEffect(() => {
    if (isOpen && !wasOpenRef.current) {
      resetForm();
    }
    wasOpenRef.current = isOpen;
  }, [isOpen, resetForm]);

  const pickFile = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const onFileChange = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] || null;
    e.target.value = '';
    if (!file) return;

    try {
      const buf = await file.arrayBuffer();
      setFileName(file.name);
      setFileBuffer(buf);

      const defaultTitle = sanitizeFilenamePart(file.name.replace(/\.[^.]+$/, ''));
      if (!titleTouched && defaultTitle) {
        setChapterTitle(defaultTitle);
      }
    } catch (err) {
      console.error(err);
      addToast('读取文件失败', 'error');
    }
  }, [addToast, titleTouched]);

  // 按编码解码文件内容（避免 Windows TXT 因编码不同出现乱码）
  useEffect(() => {
    if (!fileBuffer) return;
    try {
      const decoder = new TextDecoder(encoding);
      const text = decoder.decode(new Uint8Array(fileBuffer));
      setChapterContent(text);
    } catch (e) {
      console.error(e);
      if (encoding !== 'utf-8') {
        addToast('当前浏览器不支持该编码，已回退为 UTF-8', 'info');
        setEncoding('utf-8');
      } else {
        addToast('文件解码失败，请尝试重新选择文件或更换编码', 'error');
      }
    }
  }, [addToast, encoding, fileBuffer]);

  const handleImport = useCallback(async () => {
    const chapterNo = Math.max(1, Number(chapterNumber) || 1);
    const title = (chapterTitle || '').trim() || `第${chapterNo}章`;
    const text = String(chapterContent || '');

    setImporting(true);
    try {
      await writerApi.importChapter(projectId, chapterNo, title, text, { timeout: 0 });
      addToast('章节已导入', 'success');
      onClose();
      setFileName('');
      setFileBuffer(null);
      await onImported(chapterNo);
    } catch (e) {
      console.error(e);
      addToast('导入失败', 'error');
    } finally {
      setImporting(false);
    }
  }, [addToast, chapterContent, chapterNumber, chapterTitle, onClose, onImported, projectId]);

  return (
    <>
      <input
        ref={fileInputRef}
        type="file"
        accept=".txt,.md,text/plain,text/markdown"
        style={{ display: 'none' }}
        onChange={onFileChange}
      />

      <Modal
        isOpen={isOpen}
        onClose={() => {
          if (importing) return;
          onClose();
        }}
        title="导入章节"
        maxWidthClassName="max-w-2xl"
        footer={
          <div className="flex justify-end gap-2">
            <BookButton variant="ghost" onClick={onClose} disabled={importing}>
              取消
            </BookButton>
            <BookButton variant="primary" onClick={handleImport} disabled={importing}>
              {importing ? '导入中…' : '导入'}
            </BookButton>
          </div>
        }
      >
        <div className="space-y-4">
          <div className="text-xs text-book-text-muted leading-relaxed bg-book-bg p-3 rounded-lg border border-book-border/50">
            说明：导入会创建（或更新）指定章节，并生成一个新的版本。支持直接粘贴正文，或选择 TXT/MD 文件自动填充内容。
          </div>

          <div className="flex items-end gap-3 flex-wrap">
            <BookButton variant="secondary" size="sm" onClick={pickFile} disabled={importing}>
              选择文件
            </BookButton>
            <div className="text-xs text-book-text-muted">
              {fileName ? `已选择：${fileName}` : '未选择文件（可直接粘贴内容）'}
            </div>
            <div className="ml-auto flex items-center gap-2">
              <span className="text-xs text-book-text-muted">编码</span>
              <select
                value={encoding}
                onChange={(e) => setEncoding(e.target.value === 'gb18030' ? 'gb18030' : 'utf-8')}
                disabled={importing}
                className="text-xs bg-book-bg-paper border border-book-border/50 rounded-md px-2 py-1 outline-none focus:border-book-primary/50"
                title="若文件乱码，请切换为 GB18030（部分浏览器可能不支持）"
              >
                <option value="utf-8">UTF-8</option>
                <option value="gb18030">GB18030（Win 常见）</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <BookInput
              label="章节号"
              type="number"
              min={1}
              value={chapterNumber}
              onChange={(e) => setChapterNumber(parseInt(e.target.value, 10) || 1)}
              disabled={importing}
            />
            <BookInput
              label="章节标题"
              value={chapterTitle}
              onChange={(e) => {
                setTitleTouched(true);
                setChapterTitle(e.target.value);
              }}
              disabled={importing}
            />
          </div>

          <BookTextarea
            label="章节内容"
            rows={12}
            value={chapterContent}
            onChange={(e) => setChapterContent(e.target.value)}
            placeholder="可直接粘贴；或选择 TXT/MD 文件自动填充"
            disabled={importing}
          />
        </div>
      </Modal>
    </>
  );
};
