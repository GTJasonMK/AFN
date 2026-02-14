import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { BookCard } from '../../ui/BookCard';
import { BookButton } from '../../ui/BookButton';
import { BookInput, BookTextarea } from '../../ui/BookInput';
import { promptsApi, PromptRead } from '../../../api/prompts';
import { useToast } from '../../feedback/Toast';
import { confirmDialog } from '../../feedback/ConfirmDialog';
import { RefreshCw, Save, RotateCcw, Search, AlertTriangle } from 'lucide-react';
import { SettingsTabHeader } from './components/SettingsTabHeader';
import { isAdminUser, useAuthStore } from '../../../store/auth';

const normalizeKey = (value: any): string => {
  const s = String(value ?? '').trim();
  return s ? s : 'all';
};

const PROJECT_TYPE_LABELS: Record<string, string> = {
  all: '全部',
  novel: '小说项目',
  coding: 'Vibe Coding',
};

const CATEGORY_LABELS: Record<string, string> = {
  all: '全部',
  inspiration: '构思',
  blueprint: '蓝图',
  outline: '大纲',
  writing: '写作',
  analysis: '分析',
  manga: '漫画',
  protagonist: '主角',
  coding: '全部',
};

const formatLabel = (labels: Record<string, string>, key: string): string => {
  return labels[key] || key;
};

export const PromptsTab: React.FC = () => {
  const { addToast } = useToast();
  const { authEnabled, user } = useAuthStore();
  const isAdmin = isAdminUser(authEnabled, user);
  const [prompts, setPrompts] = useState<PromptRead[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedName, setSelectedName] = useState<string | null>(null);
  const [selected, setSelected] = useState<PromptRead | null>(null);

  const [query, setQuery] = useState('');
  const [contentDraft, setContentDraft] = useState('');
  const [saving, setSaving] = useState(false);
  const [resetting, setResetting] = useState(false);

  // 对齐桌面端：按 project_type / category 分层查看（Web 保留搜索能力）
  const [projectTypeFilter, setProjectTypeFilter] = useState<string>('all');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');

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

  const projectTypes = useMemo(() => {
    const set = new Set<string>();
    prompts.forEach((p) => set.add(normalizeKey(p.project_type)));

    const preferred = ['novel', 'coding'];
    const ordered: string[] = ['all'];
    preferred.forEach((k) => {
      if (set.has(k)) ordered.push(k);
    });

    const rest = Array.from(set)
      .filter((k) => k !== 'all' && !preferred.includes(k))
      .sort((a, b) => a.localeCompare(b));
    ordered.push(...rest);
    return ordered;
  }, [prompts]);

  const categories = useMemo(() => {
    const set = new Set<string>();
    prompts.forEach((p) => {
      const pt = normalizeKey(p.project_type);
      if (projectTypeFilter !== 'all' && pt !== projectTypeFilter) return;
      set.add(normalizeKey(p.category));
    });

    const preferredNovel = ['inspiration', 'blueprint', 'outline', 'writing', 'analysis', 'manga', 'protagonist'];
    const preferredCoding = ['coding'];
    const preferred = projectTypeFilter === 'coding' ? preferredCoding : preferredNovel;

    const ordered: string[] = ['all'];
    preferred.forEach((k) => {
      if (set.has(k)) ordered.push(k);
    });

    const rest = Array.from(set)
      .filter((k) => k !== 'all' && !preferred.includes(k))
      .sort((a, b) => a.localeCompare(b));
    ordered.push(...rest);
    return ordered;
  }, [projectTypeFilter, prompts]);

  useEffect(() => {
    if (categoryFilter === 'all') return;
    if (categories.includes(categoryFilter)) return;
    setCategoryFilter('all');
  }, [categories, categoryFilter]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return prompts.filter((p) => {
      const pt = normalizeKey(p.project_type);
      const cat = normalizeKey(p.category);
      if (projectTypeFilter !== 'all' && pt !== projectTypeFilter) return false;
      if (categoryFilter !== 'all' && cat !== categoryFilter) return false;
      if (!q) return true;
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
  }, [categoryFilter, projectTypeFilter, prompts, query]);

  useEffect(() => {
    if (!selectedName) {
      setSelectedName(filtered.length > 0 ? filtered[0].name : null);
      return;
    }
    if (filtered.some((p) => p.name === selectedName)) return;
    setSelectedName(filtered.length > 0 ? filtered[0].name : null);
  }, [filtered, selectedName]);

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
    if (!isAdmin) {
      addToast('需要管理员权限才能编辑提示词', 'error');
      return;
    }
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
    if (!isAdmin) {
      addToast('需要管理员权限才能恢复提示词', 'error');
      return;
    }
    if (!selected) return;
    const ok = await confirmDialog({
      title: '恢复默认提示词',
      message: `确定要将提示词「${selected.name}」恢复为默认值吗？`,
      confirmText: '恢复默认',
      dialogType: 'warning',
    });
    if (!ok) return;
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
    if (!isAdmin) {
      addToast('需要管理员权限才能恢复全部提示词', 'error');
      return;
    }
    const ok = await confirmDialog({
      title: '恢复全部提示词',
      message: '确定要恢复所有提示词为默认值吗？\n此操作会覆盖所有已修改内容。',
      confirmText: '恢复全部',
      dialogType: 'danger',
    });
    if (!ok) return;
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
          <BookButton variant="ghost" size="sm" onClick={handleResetAll} disabled={resetting || !isAdmin}>
            <RotateCcw size={14} className="mr-1" />
            恢复全部
          </BookButton>
        }
      />

      <div className="grid grid-cols-[280px_1fr] gap-4 min-h-[60vh]">
        <BookCard className="p-4">
          <div className="flex flex-wrap gap-2 mb-3">
            {projectTypes.map((pt) => {
              const isActive = projectTypeFilter === pt;
              return (
                <button
                  key={`pt-${pt}`}
                  type="button"
                  onClick={() => {
                    setProjectTypeFilter(pt);
                    setCategoryFilter('all');
                  }}
                  className={`px-2.5 py-1 rounded border text-[11px] font-bold transition-all ${
                    isActive
                      ? 'bg-book-primary/5 border-book-primary/30 text-book-primary'
                      : 'bg-book-bg border-book-border/40 text-book-text-main hover:border-book-primary/20'
                  }`}
                >
                  {formatLabel(PROJECT_TYPE_LABELS, pt)}
                </button>
              );
            })}
          </div>

          <div className="flex flex-wrap gap-2 mb-3">
            {categories.map((cat) => {
              const isActive = categoryFilter === cat;
              return (
                <button
                  key={`cat-${cat}`}
                  type="button"
                  onClick={() => setCategoryFilter(cat)}
                  className={`px-2.5 py-1 rounded border text-[11px] font-bold transition-all ${
                    isActive
                      ? 'bg-book-primary/5 border-book-primary/30 text-book-primary'
                      : 'bg-book-bg border-book-border/40 text-book-text-main hover:border-book-primary/20'
                  }`}
                >
                  {formatLabel(CATEGORY_LABELS, cat)}
                </button>
              );
            })}
          </div>

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
                  <BookButton variant="ghost" size="sm" onClick={handleReset} disabled={resetting || !isAdmin}>
                    <RotateCcw size={14} className="mr-1" />
                    恢复默认
                  </BookButton>
                  <BookButton variant="primary" size="sm" onClick={handleSave} disabled={!isDirty || saving || !isAdmin}>
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

              {!isAdmin && (
                <div className="text-xs text-book-text-muted bg-book-bg p-3 rounded-lg border border-book-border/50">
                  当前账号仅可查看提示词内容，编辑与恢复默认需要管理员权限。
                </div>
              )}

              <BookTextarea
                value={contentDraft}
                onChange={(e) => setContentDraft(e.target.value)}
                readOnly={!isAdmin}
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
