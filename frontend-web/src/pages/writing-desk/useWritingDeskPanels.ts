import { useCallback, useEffect, useRef, useState } from 'react';
import type { MouseEvent as ReactMouseEvent } from 'react';
import { usePersistedState } from '../../hooks/usePersistedState';
import { scheduleIdleTask } from '../../utils/scheduleIdleTask';

const clamp = (n: number, min: number, max: number) => Math.max(min, Math.min(max, n));

const getSidebarWidthKey = (projectId: string) => `afn:writing_sidebar_width:${projectId}`;
const getSidebarOpenKey = (projectId: string) => `afn:writing_sidebar_open:${projectId}`;
const getAssistantWidthKey = (projectId: string) => `afn:writing_assistant_width:${projectId}`;
const getAssistantOpenKey = (projectId: string) => `afn:writing_assistant_open:${projectId}`;

const parseSidebarWidth = (raw: string) => {
  const n = Number(raw);
  if (!Number.isFinite(n)) return 256;
  return clamp(Math.round(n), 220, 420);
};

const parseAssistantWidth = (raw: string) => {
  const n = Number(raw);
  if (!Number.isFinite(n)) return 384;
  return clamp(Math.round(n), 280, 720);
};

const serializeSidebarWidth = (value: number) => String(clamp(Math.round(value), 220, 420));
const serializeAssistantWidth = (value: number) => String(clamp(Math.round(value), 280, 720));
const parsePanelOpen = (raw: string) => raw !== '0';
const serializePanelOpen = (value: boolean) => (value ? '1' : '0');

export const useWritingDeskPanels = (projectId: string | undefined) => {
  const sidebarWidthKey = projectId ? getSidebarWidthKey(projectId) : null;
  const sidebarOpenKey = projectId ? getSidebarOpenKey(projectId) : null;
  const assistantWidthKey = projectId ? getAssistantWidthKey(projectId) : null;
  const assistantOpenKey = projectId ? getAssistantOpenKey(projectId) : null;

  const [sidebarWidth, setSidebarWidth] = usePersistedState<number>(sidebarWidthKey, 256, {
    parse: parseSidebarWidth,
    serialize: serializeSidebarWidth,
  });
  const [isSidebarOpen, setIsSidebarOpen] = usePersistedState<boolean>(sidebarOpenKey, true, {
    parse: parsePanelOpen,
    serialize: serializePanelOpen,
  });
  const [assistantWidth, setAssistantWidth] = usePersistedState<number>(assistantWidthKey, 384, {
    parse: parseAssistantWidth,
    serialize: serializeAssistantWidth,
  });
  const [isAssistantOpen, setIsAssistantOpen] = usePersistedState<boolean>(assistantOpenKey, true, {
    parse: parsePanelOpen,
    serialize: serializePanelOpen,
  });
  const [assistantMountReady, setAssistantMountReady] = useState(false);

  useEffect(() => {
    if (!isAssistantOpen) {
      setAssistantMountReady(false);
      return;
    }

    const cancel = scheduleIdleTask(() => {
      setAssistantMountReady(true);
    }, { delay: 420, timeout: 2400 });

    return cancel;
  }, [isAssistantOpen, projectId]);

  const clampAssistantWidth = useCallback((w: number) => {
    const minEditor = 420;
    const min = 280;
    const sidebar = isSidebarOpen ? sidebarWidth : 0;
    const maxByLayout = window.innerWidth - sidebar - minEditor - 20;
    const max = Math.max(min, Math.min(720, Math.floor(maxByLayout)));
    return clamp(Math.round(w), min, max);
  }, [isSidebarOpen, sidebarWidth]);

  const clampSidebarWidth = useCallback((w: number) => {
    const minEditor = 420;
    const min = 220;
    const hardMax = 420;
    const assistant = isAssistantOpen ? assistantWidth : 0;
    const maxByLayout = window.innerWidth - assistant - minEditor - 20;
    const max = Math.max(min, Math.min(hardMax, Math.floor(maxByLayout)));
    return clamp(Math.round(w), min, max);
  }, [assistantWidth, isAssistantOpen]);

  // 窗口尺寸 / 面板开关变化时：自动夹紧宽度，保证中间编辑区最小宽度
  useEffect(() => {
    const onResize = () => {
      if (isAssistantOpen) setAssistantWidth((w) => clampAssistantWidth(w));
      if (isSidebarOpen) setSidebarWidth((w) => clampSidebarWidth(w));
    };
    onResize();
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, [clampAssistantWidth, clampSidebarWidth, isAssistantOpen, isSidebarOpen]);

  const sidebarResizingRef = useRef(false);
  const sidebarResizeRafRef = useRef<number | null>(null);
  const sidebarResizeStartRef = useRef<{ x: number; w: number } | null>(null);

  const assistantResizingRef = useRef(false);
  const assistantResizeRafRef = useRef<number | null>(null);
  const assistantResizeStartRef = useRef<{ x: number; w: number } | null>(null);

  const stopSidebarResizing = useCallback(() => {
    sidebarResizingRef.current = false;
    sidebarResizeStartRef.current = null;
    if (sidebarResizeRafRef.current !== null) {
      window.cancelAnimationFrame(sidebarResizeRafRef.current);
      sidebarResizeRafRef.current = null;
    }
    try {
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    } catch {
      // ignore
    }
  }, []);

  const stopAssistantResizing = useCallback(() => {
    assistantResizingRef.current = false;
    assistantResizeStartRef.current = null;
    if (assistantResizeRafRef.current !== null) {
      window.cancelAnimationFrame(assistantResizeRafRef.current);
      assistantResizeRafRef.current = null;
    }
    try {
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    } catch {
      // ignore
    }
  }, []);

  const onSidebarResizeMove = useCallback((ev: MouseEvent) => {
    if (!sidebarResizingRef.current || !sidebarResizeStartRef.current) return;
    const { x, w } = sidebarResizeStartRef.current;
    const next = clampSidebarWidth(w + (ev.clientX - x));
    if (sidebarResizeRafRef.current !== null) window.cancelAnimationFrame(sidebarResizeRafRef.current);
    sidebarResizeRafRef.current = window.requestAnimationFrame(() => setSidebarWidth(next));
  }, [clampSidebarWidth]);

  const onAssistantResizeMove = useCallback((ev: MouseEvent) => {
    if (!assistantResizingRef.current || !assistantResizeStartRef.current) return;
    const { x, w } = assistantResizeStartRef.current;
    const next = clampAssistantWidth(w + (x - ev.clientX));
    if (assistantResizeRafRef.current !== null) window.cancelAnimationFrame(assistantResizeRafRef.current);
    assistantResizeRafRef.current = window.requestAnimationFrame(() => setAssistantWidth(next));
  }, [clampAssistantWidth]);

  const onSidebarResizeUp = useCallback(() => {
    window.removeEventListener('mousemove', onSidebarResizeMove);
    window.removeEventListener('mouseup', onSidebarResizeUp);
    stopSidebarResizing();
  }, [onSidebarResizeMove, stopSidebarResizing]);

  const onAssistantResizeUp = useCallback(() => {
    window.removeEventListener('mousemove', onAssistantResizeMove);
    window.removeEventListener('mouseup', onAssistantResizeUp);
    stopAssistantResizing();
  }, [onAssistantResizeMove, stopAssistantResizing]);

  const startSidebarResizing = useCallback((e: ReactMouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    sidebarResizingRef.current = true;
    sidebarResizeStartRef.current = { x: e.clientX, w: sidebarWidth };
    try {
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
    } catch {
      // ignore
    }
    window.addEventListener('mousemove', onSidebarResizeMove);
    window.addEventListener('mouseup', onSidebarResizeUp);
  }, [onSidebarResizeMove, onSidebarResizeUp, sidebarWidth]);

  const startAssistantResizing = useCallback((e: ReactMouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    assistantResizingRef.current = true;
    assistantResizeStartRef.current = { x: e.clientX, w: assistantWidth };
    try {
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
    } catch {
      // ignore
    }
    window.addEventListener('mousemove', onAssistantResizeMove);
    window.addEventListener('mouseup', onAssistantResizeUp);
  }, [assistantWidth, onAssistantResizeMove, onAssistantResizeUp]);

  useEffect(() => {
    return () => {
      window.removeEventListener('mousemove', onSidebarResizeMove);
      window.removeEventListener('mouseup', onSidebarResizeUp);
      stopSidebarResizing();
      window.removeEventListener('mousemove', onAssistantResizeMove);
      window.removeEventListener('mouseup', onAssistantResizeUp);
      stopAssistantResizing();
    };
  }, [
    onAssistantResizeMove,
    onAssistantResizeUp,
    onSidebarResizeMove,
    onSidebarResizeUp,
    stopAssistantResizing,
    stopSidebarResizing,
  ]);

  return {
    sidebarWidth,
    isSidebarOpen,
    setIsSidebarOpen,
    startSidebarResizing,
    assistantWidth,
    isAssistantOpen,
    setIsAssistantOpen,
    assistantMountReady,
    startAssistantResizing,
  };
};
