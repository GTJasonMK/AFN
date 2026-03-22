import React, { useEffect, useMemo, useState } from 'react';
import { Modal } from '../../../ui/Modal';
import { BookButton } from '../../../ui/BookButton';
import { useSSE } from '../../../../hooks/useSSE';
import { useToast } from '../../../feedback/Toast';
import {
  NovelDialogIntro,
  NovelDialogSection,
  NovelDialogStack,
  NovelDialogSurface,
} from '../../novel/NovelDialogPrimitives';

type DownloadStatus = 'idle' | 'running' | 'success' | 'error' | 'stopped';

interface LocalEmbeddingModelDownloadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onDownloaded?: (result: { repoId: string; configId?: number; activated?: boolean }) => void | Promise<void>;
  repoId?: string;
  activateAfterDownload?: boolean;
}

const formatBytes = (value?: number | null): string => {
  const n = typeof value === 'number' ? value : 0;
  if (!Number.isFinite(n) || n <= 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let size = n;
  let idx = 0;
  while (size >= 1024 && idx < units.length - 1) {
    size /= 1024;
    idx += 1;
  }
  return `${size.toFixed(idx >= 2 ? 2 : 0)} ${units[idx]}`;
};

export const LocalEmbeddingModelDownloadModal: React.FC<LocalEmbeddingModelDownloadModalProps> = ({
  isOpen,
  onClose,
  onDownloaded,
  repoId,
  activateAfterDownload = true,
}) => {
  const { addToast } = useToast();
  const [status, setStatus] = useState<DownloadStatus>('idle');
  const [progressPercent, setProgressPercent] = useState<number | null>(null);
  const [message, setMessage] = useState<string>('');
  const [currentFile, setCurrentFile] = useState<string>('');
  const [bytes, setBytes] = useState<{ downloaded: number; total: number } | null>(null);
  const [files, setFiles] = useState<{ done: number; total: number } | null>(null);
  const [result, setResult] = useState<{ repoId: string; configId?: number; activated?: boolean } | null>(null);

  const allowClose = status === 'success' || status === 'error' || status === 'stopped';

  const endpoint = useMemo(() => '/embedding-configs/local-models/download-default-stream', []);
  const payload = useMemo(() => {
    return {
      repo_id: repoId ?? null,
      activate_after_download: activateAfterDownload,
    };
  }, [repoId, activateAfterDownload]);

  const { connect, disconnect, isConnected } = useSSE((event, data) => {
    if (event === 'progress') {
      const msg = typeof data?.message === 'string' ? data.message : '';
      const percentRaw = typeof data?.progress_percent === 'number' ? data.progress_percent : null;
      const percent = percentRaw === null ? null : Math.min(100, Math.max(0, percentRaw));

      setStatus('running');
      setMessage(msg || '下载中…');
      setProgressPercent(percent);

      const cf = typeof data?.current_file === 'string' ? data.current_file : '';
      setCurrentFile(cf);

      const downloadedBytes = Number(data?.downloaded_bytes ?? 0);
      const totalBytes = Number(data?.total_bytes ?? 0);
      if (Number.isFinite(downloadedBytes) && Number.isFinite(totalBytes) && totalBytes > 0) {
        setBytes({ downloaded: Math.max(0, downloadedBytes), total: Math.max(0, totalBytes) });
      } else {
        setBytes(null);
      }

      const done = Number(data?.completed_files ?? 0);
      const total = Number(data?.total_files ?? 0);
      if (Number.isFinite(done) && Number.isFinite(total) && total > 0) {
        setFiles({ done: Math.max(0, done), total: Math.max(1, total) });
      } else {
        setFiles(null);
      }
      return;
    }

    if (event === 'complete') {
      const repo = typeof data?.repo_id === 'string' ? data.repo_id : String(repoId || '本地嵌入模型').trim();
      const configId = typeof data?.config_id === 'number' ? data.config_id : undefined;
      const activated = typeof data?.activated === 'boolean' ? data.activated : undefined;
      setResult({ repoId: repo, configId, activated });

      setStatus('success');
      setProgressPercent(100);
      setMessage(typeof data?.message === 'string' ? data.message : '下载完成');

      addToast(activated ? '模型下载完成，已创建并启用嵌入配置' : '模型下载完成，已创建嵌入配置', 'success');
      Promise.resolve(onDownloaded?.({ repoId: repo, configId, activated })).catch((e) => console.error(e));
      return;
    }

    if (event === 'error') {
      const msg =
        typeof data?.message === 'string'
          ? data.message
          : (data instanceof Error ? data.message : '下载失败');
      setStatus('error');
      setMessage(msg);
      setProgressPercent(null);
      addToast(msg, 'error');
      return;
    }
  });

  useEffect(() => {
    if (!isOpen) {
      disconnect();
      setStatus('idle');
      setProgressPercent(null);
      setMessage('');
      setCurrentFile('');
      setBytes(null);
      setFiles(null);
      setResult(null);
      return;
    }

    // 打开即开始下载（避免多一步“开始”按钮）
    setStatus('running');
    setProgressPercent(0);
    setMessage('准备下载…');
    setCurrentFile('');
    setBytes(null);
    setFiles(null);
    setResult(null);

    void connect(endpoint, payload);
    return () => disconnect();
  }, [connect, disconnect, endpoint, isOpen, payload]);

  const handleRequestClose = () => {
    if (!allowClose) return;
    onClose();
  };

  const handleStop = () => {
    if (!isConnected) {
      setStatus('stopped');
      setMessage('已停止');
      return;
    }
    // 断开 SSE 连接即可触发后端停止并清理临时目录
    disconnect();
    setStatus('stopped');
    setMessage('已停止下载（临时文件将被清理）');
  };

  const percentText = typeof progressPercent === 'number' ? `${Math.round(progressPercent)}%` : '—';
  const bytesText = bytes ? `${formatBytes(bytes.downloaded)} / ${formatBytes(bytes.total)}` : '';
  const filesText = files ? `${files.done} / ${files.total}` : '';

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleRequestClose}
      title="下载默认本地嵌入模型"
      maxWidthClassName="max-w-2xl"
      closeOnBackdrop={false}
      showCloseButton={allowClose}
      footer={
        <div className="flex w-full flex-wrap items-center justify-between gap-2">
          <div className="text-xs text-book-text-muted">
            {result?.repoId ? `模型：${result.repoId}` : (repoId ? `模型：${repoId}` : '模型：默认')}
            {result?.configId ? ` · 配置ID：${result.configId}` : ''}
          </div>
          <div className="flex items-center gap-2">
            {status === 'running' ? (
              <BookButton variant="danger" onClick={handleStop}>
                停止
              </BookButton>
            ) : (
              <BookButton variant="primary" onClick={handleRequestClose}>
                关闭
              </BookButton>
            )}
          </div>
        </div>
      }
    >
      <NovelDialogStack>
        <NovelDialogIntro
          eyebrow="Local Embedding Model"
          title="下载与安装"
          description="下载过程会写入 storage/models，并在完成后自动创建（可选激活）对应的嵌入配置。下载中不可关闭弹窗，可随时停止。"
        />

        <NovelDialogSection
          eyebrow="Progress"
          title="下载进度"
          description="以文件与字节进度展示下载状态。"
        >
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div className="rounded-lg border border-book-border/50 bg-book-bg px-4 py-3">
              <div className="text-xs font-bold text-book-text-muted">进度</div>
              <div className="mt-1 text-sm font-semibold text-book-text-main">{percentText}</div>
            </div>
            <div className="rounded-lg border border-book-border/50 bg-book-bg px-4 py-3">
              <div className="text-xs font-bold text-book-text-muted">文件</div>
              <div className="mt-1 text-sm font-semibold text-book-text-main">{filesText || '—'}</div>
            </div>
            <div className="rounded-lg border border-book-border/50 bg-book-bg px-4 py-3">
              <div className="text-xs font-bold text-book-text-muted">流量</div>
              <div className="mt-1 text-sm font-semibold text-book-text-main">{bytesText || '—'}</div>
            </div>
          </div>

          {typeof progressPercent === 'number' ? (
            <div className="mt-4 h-2 w-full overflow-hidden rounded-full bg-book-bg border border-book-border/40">
              <div className="h-2 bg-book-primary transition-all duration-500" style={{ width: `${progressPercent}%` }} />
            </div>
          ) : null}

          <div className="mt-4 min-h-[2.25rem] text-sm font-semibold text-book-primary">
            {message || '—'}
          </div>
          {currentFile ? (
            <div className="mt-1 text-xs text-book-text-muted truncate" title={currentFile}>
              当前文件：{currentFile}
            </div>
          ) : null}
        </NovelDialogSection>

        {status === 'error' ? (
          <NovelDialogSurface className="text-sm text-book-accent">
            下载失败：{message || '未知错误'}（已尝试清理临时目录，请检查网络或 HF 镜像配置）
          </NovelDialogSurface>
        ) : null}

        {status === 'stopped' ? (
          <NovelDialogSurface className="text-sm text-book-text-muted">
            已停止下载。你可以重新点击“下载默认模型”再次开始。
          </NovelDialogSurface>
        ) : null}

        {status === 'success' ? (
          <NovelDialogSurface className="text-sm text-book-text-muted">
            下载完成。{result?.activated ? '已自动启用该嵌入配置。' : '已创建嵌入配置，你可以在列表中手动启用。'}
          </NovelDialogSurface>
        ) : null}
      </NovelDialogStack>
    </Modal>
  );
};

