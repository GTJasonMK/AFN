import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { BookCard } from '../../ui/BookCard';
import { BookButton } from '../../ui/BookButton';
import { BookInput, BookTextarea } from '../../ui/BookInput';
import { promptsApi, PromptRead } from '../../../api/prompts';
import { useToast } from '../../feedback/Toast';
import { RefreshCw, Save, RotateCcw, Search, AlertTriangle } from 'lucide-react';
import { SettingsTabHeader } from './components/SettingsTabHeader';

export const PromptsTab: React.FC = () => {
  const { addToast } = useToast();
  const [prompts, setPrompts] = useState<PromptRead[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedName, setSelectedName] = useState<string | null>(null);
  const [selected, setSelected] = useState<PromptRead | null>(null);

  const [query, setQuery] = useState('');
  const [contentDraft, setContentDraft] = useState('');
  const [saving, setSaving] = useState(false);
  const [resetting, setResetting] = useState(false);

  const fetchList = useCallback(async () => {
    setLoading(true);
    try {
      const list = await promptsApi.list();
      setPrompts(list);
      setSelectedName((prev) => prev ?? (list.length > 0 ? list[0].name : null));
    } catch (e) {
      console.error(e);
      setPrompts([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchList();
  }, [fetchList]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return prompts;
    return prompts.filter((p) => {
      const hay = [
        p.name,
        p.title || '',
        p.description || '',
        p.category || '',
        p.status || '',
        (p.tags || []).join(','),
      ].join(' ').toLowerCase();
      return hay.includes(q);
    });
  }, [prompts, query]);

  useEffect(() => {
    if (!selectedName) return;
    const found = prompts.find((p) => p.name === selectedName);
    if (found) {
      setSelected(found);
      setContentDraft(found.content || '');
      return;
    }
    setSelected(null);
    setContentDraft('');
  }, [selectedName, prompts]);

  const refreshSelected = async () => {
    if (!selectedName) return;
    try {
      const fresh = await promptsApi.get(selectedName);
      setSelected(fresh);
      setContentDraft(fresh.content || '');
      await fetchList();
    } catch (e) {
      console.error(e);
    }
  };

  const isDirty = useMemo(() => {
    if (!selected) return false;
    return (selected.content || '') !== contentDraft;
  }, [selected, contentDraft]);

  const handleSave = async () => {
    if (!selected) return;
    setSaving(true);
    try {
      const updated = await promptsApi.update(selected.name, { content: contentDraft });
      setSelected(updated);
      addToast('提示词已保存', 'success');
      await fetchList();
    } catch (e) {
      console.error(e);
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    if (!selected) return;
    if (!confirm(`确定要将提示词「${selected.name}」恢复为默认值吗？`)) return;
    setResetting(true);
    try {
      const updated = await promptsApi.reset(selected.name);
      setSelected(updated);
      setContentDraft(updated.content || '');
      addToast('已恢复默认提示词', 'success');
      await fetchList();
    } catch (e) {
      console.error(e);
    } finally {
      setResetting(false);
    }
  };

  const handleResetAll = async () => {
    if (!confirm('确定要恢复所有提示词为默认值吗？此操作会覆盖所有已修改内容。')) return;
    setResetting(true);
    try {
      const res = await promptsApi.resetAll();
      addToast(res.message || '已恢复默认提示词', 'success');
      await fetchList();
      await refreshSelected();
    } catch (e) {
      console.error(e);
    } finally {
      setResetting(false);
    }
  };

  return (
    <div className="space-y-4">
      <SettingsTabHeader
        title="提示词"
        loading={loading}
        onRefresh={fetchList}
        showRefreshIcon
        extraActions={
          <BookButton variant="ghost" size="sm" onClick={handleResetAll} disabled={resetting}>
            <RotateCcw size={14} className="mr-1" />
            恢复全部
          </BookButton>
        }
      />

      <div className="grid grid-cols-[280px_1fr] gap-4 min-h-[60vh]">
        <BookCard className="p-4">
          <div className="relative mb-3">
            <BookInput
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="搜索提示词…"
              className="pl-9"
            />
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-book-text-muted" />
          </div>

          <div className="space-y-1 max-h-[52vh] overflow-auto custom-scrollbar pr-1">
            {filtered.map((p) => (
              <button
                key={p.name}
                onClick={() => setSelectedName(p.name)}
                className={`w-full text-left px-3 py-2 rounded-lg border transition-all ${
                  selectedName === p.name
                    ? 'bg-book-primary/5 border-book-primary/30 text-book-primary'
                    : 'bg-book-bg border-book-border/40 text-book-text-main hover:border-book-primary/20'
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="text-xs font-bold truncate">{p.title || p.name}</div>
                  {p.is_modified && (
                    <span className="text-[10px] px-2 py-0.5 rounded bg-book-accent/10 text-book-accent font-bold">已修改</span>
                  )}
                </div>
                <div className="mt-1 text-[10px] text-book-text-muted truncate">
                  {p.category || 'uncategorized'} · {p.status || 'active'} · {p.project_type || 'all'}
                </div>
              </button>
            ))}

            {filtered.length === 0 && !loading && (
              <div className="py-10 text-center text-book-text-muted text-sm">未找到</div>
            )}
          </div>
        </BookCard>

        <BookCard className="p-4">
          {!selected ? (
            <div className="h-full flex items-center justify-center text-book-text-muted">请选择一个提示词</div>
          ) : (
            <div className="space-y-3">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="font-bold text-book-text-main truncate">{selected.title || selected.name}</div>
                  {selected.description && (
                    <div className="mt-1 text-xs text-book-text-muted leading-relaxed">{selected.description}</div>
                  )}
                  <div className="mt-2 text-[10px] text-book-text-muted">
                    <span className="mr-2">名称：{selected.name}</span>
                    <span className="mr-2">分类：{selected.category || '—'}</span>
                    <span className="mr-2">状态：{selected.status || '—'}</span>
                    <span>类型：{selected.project_type || '—'}</span>
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <BookButton variant="ghost" size="sm" onClick={refreshSelected}>
                    <RefreshCw size={14} className="mr-1" />
                    重新加载
                  </BookButton>
                  <BookButton variant="ghost" size="sm" onClick={handleReset} disabled={resetting}>
                    <RotateCcw size={14} className="mr-1" />
                    恢复默认
                  </BookButton>
                  <BookButton variant="primary" size="sm" onClick={handleSave} disabled={!isDirty || saving}>
                    <Save size={14} className="mr-1" />
                    {saving ? '保存中…' : '保存'}
                  </BookButton>
                </div>
              </div>

              {isDirty && (
                <div className="text-xs text-book-text-muted bg-book-bg p-3 rounded-lg border border-book-border/50 flex items-start gap-2">
                  <AlertTriangle size={14} className="text-book-accent mt-0.5" />
                  当前内容未保存
                </div>
              )}

              <BookTextarea
                value={contentDraft}
                onChange={(e) => setContentDraft(e.target.value)}
                className="min-h-[45vh] font-mono text-xs leading-relaxed"
                placeholder="在此编辑提示词内容…"
              />
            </div>
          )}
        </BookCard>
      </div>
    </div>
  );
};
