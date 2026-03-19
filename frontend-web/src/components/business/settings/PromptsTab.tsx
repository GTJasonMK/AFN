import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { BookButton } from '../../ui/BookButton';
import { BookInput } from '../../ui/BookInput';
import { promptsApi, PromptRead } from '../../../api/prompts';
import { useToast } from '../../feedback/Toast';
import { confirmDialog } from '../../feedback/ConfirmDialog';
import { RefreshCw, Save, RotateCcw, Search } from 'lucide-react';
import { SettingsTabPanel } from './components/SettingsTabPanel';
import { isAdminUser, useAuthStore } from '../../../store/auth';
import { useSettingsModalFooter } from './components/SettingsModalFooterContext';

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
  const { setFooter } = useSettingsModalFooter();
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
  const selectedRef = useRef<PromptRead | null>(null);
  selectedRef.current = selected;
  const contentDraftRef = useRef(contentDraft);
  contentDraftRef.current = contentDraft;
  const isAdminRef = useRef(isAdmin);
  isAdminRef.current = isAdmin;

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

  const isDirty = useMemo(() => {
    if (!selected) return false;
    return (selected.content || '') !== contentDraft;
  }, [selected, contentDraft]);

  useEffect(() => {
    if (!selectedName) {
      setSelectedName(filtered.length > 0 ? filtered[0].name : null);
      return;
    }
    if (filtered.some((p) => p.name === selectedName)) return;
    if (isDirty) return;
    setSelectedName(filtered.length > 0 ? filtered[0].name : null);
  }, [filtered, selectedName, isDirty]);

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

  const groupedFiltered = useMemo(() => {
    if (categoryFilter !== 'all') {
      const key = normalizeKey(categoryFilter);
      const label = key === 'all' ? '通用' : formatLabel(CATEGORY_LABELS, key);
      return [{ key, label, items: filtered }];
    }

    const order = categories.filter((k) => k !== 'all');
    const map = new Map<string, PromptRead[]>();
    filtered.forEach((p) => {
      const key = normalizeKey(p.category);
      const arr = map.get(key);
      if (arr) {
        arr.push(p);
      } else {
        map.set(key, [p]);
      }
    });

    const known = new Set(order);
    const unknown = Array.from(map.keys())
      .filter((k) => !known.has(k))
      .sort((a, b) => a.localeCompare(b));
    const allKeys = [...order, ...unknown];

    return allKeys
      .map((key) => ({
        key,
        label: key === 'all' ? '通用' : formatLabel(CATEGORY_LABELS, key),
        items: map.get(key) || [],
      }))
      .filter((g) => g.items.length > 0);
  }, [categories, categoryFilter, filtered]);

  const handleSelectPrompt = useCallback(
    async (name: string) => {
      if (name === selectedName) return;
      if (isDirty) {
        const ok = await confirmDialog({
          title: '切换提示词',
          message: '当前提示词还未应用。\n切换会丢失未保存内容，是否继续？',
          confirmText: '继续切换',
          dialogType: 'warning',
        });
        if (!ok) return;
      }
      setSelectedName(name);
    },
    [isDirty, selectedName],
  );

  const selectedHiddenByFilter = useMemo(() => {
    if (!selectedName) return false;
    if (filtered.some((p) => p.name === selectedName)) return false;
    return Boolean(query.trim() || projectTypeFilter !== 'all' || categoryFilter !== 'all');
  }, [categoryFilter, filtered, projectTypeFilter, query, selectedName]);

  const clearFilters = useCallback(() => {
    setQuery('');
    setProjectTypeFilter('all');
    setCategoryFilter('all');
  }, []);

  const handleSave = useCallback(async () => {
    if (!isAdminRef.current) {
      addToast('需要管理员权限才能编辑提示词', 'error');
      return;
    }
    const current = selectedRef.current;
    if (!current) return;
    setSaving(true);
    try {
      const updated = await promptsApi.update(current.name, { content: contentDraftRef.current });
      setSelected(updated);
      addToast('提示词已保存', 'success');
      await fetchList();
    } catch (e) {
      console.error(e);
    } finally {
      setSaving(false);
    }
  }, [addToast, fetchList]);

  const footer = useMemo(() => {
    if (!selected) return null;
    return (
      <BookButton variant="primary" size="sm" onClick={handleSave} disabled={!isDirty || saving || !isAdmin}>
        <Save size={14} className="mr-1" />
        {saving ? '应用中…' : '应用'}
      </BookButton>
    );
  }, [handleSave, isAdmin, isDirty, saving, selected]);

  useEffect(() => {
    setFooter(footer);
    return () => setFooter(null);
  }, [footer, setFooter]);

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
    <SettingsTabPanel className="h-full min-h-0" bodyClassName="h-full min-h-0">
      <div className="flex h-full min-h-0 flex-col gap-4">
        <div className="min-h-0 flex-1 overflow-hidden rounded-[28px] border border-book-border/55 bg-book-bg-paper/70 shadow-surface backdrop-blur-xl">
          <div className="grid h-full min-h-0 lg:grid-cols-[minmax(300px,360px)_minmax(0,1fr)]">
            <aside className="min-h-0 flex flex-col border-b border-book-border/45 lg:border-b-0 lg:border-r lg:border-book-border/45">
              <div className="shrink-0 border-b border-book-border/45 bg-book-bg/40 p-4">
                <div className="flex flex-col gap-3">
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2 text-sm font-bold text-book-text-main">
                      <Search size={16} className="text-book-primary" />
                      提示词库
                    </div>
                    <div className="flex flex-wrap items-center justify-end gap-2">
                      <BookButton variant="ghost" size="sm" onClick={fetchList} disabled={loading}>
                        <RefreshCw size={14} className={`mr-1 ${loading ? 'animate-spin' : ''}`} />
                        刷新
                      </BookButton>
                      <BookButton
                        variant="ghost"
                        size="sm"
                        onClick={handleResetAll}
                        disabled={resetting || !isAdmin}
                        className="text-book-accent"
                      >
                        <RotateCcw size={14} className="mr-1" />
                        {resetting ? '恢复中…' : '恢复全部'}
                      </BookButton>
                    </div>
                  </div>

                  <div className="grid gap-3">
                    <div className="grid gap-2 sm:grid-cols-2">
                      <label className="text-[11px] font-bold text-book-text-sub">
                        项目类型
                        <select
                          className="book-control book-select mt-1 w-full rounded-2xl border px-3 py-2 text-xs text-book-text-main outline-none focus:border-book-primary/50"
                          value={projectTypeFilter}
                          onChange={(e) => {
                            const next = e.target.value;
                            setProjectTypeFilter(next);
                            setCategoryFilter('all');
                          }}
                        >
                          {projectTypes.map((pt) => (
                            <option key={`pt-${pt}`} value={pt}>
                              {formatLabel(PROJECT_TYPE_LABELS, pt)}
                            </option>
                          ))}
                        </select>
                      </label>

                      <label className="text-[11px] font-bold text-book-text-sub">
                        分类
                        <select
                          className="book-control book-select mt-1 w-full rounded-2xl border px-3 py-2 text-xs text-book-text-main outline-none focus:border-book-primary/50"
                          value={categoryFilter}
                          onChange={(e) => setCategoryFilter(e.target.value)}
                        >
                          {categories.map((cat) => (
                            <option key={`cat-${cat}`} value={cat}>
                              {formatLabel(CATEGORY_LABELS, cat)}
                            </option>
                          ))}
                        </select>
                      </label>
                    </div>

                    <div className="relative">
                      <BookInput
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="搜索提示词…"
                        className="py-2 pl-9 text-xs"
                      />
                      <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-book-text-muted" />
                    </div>

                    <div className="flex items-center justify-between text-[10px] text-book-text-muted">
                      <div>
                        显示 <span className="font-mono">{filtered.length}</span> /{' '}
                        <span className="font-mono">{prompts.length}</span>
                      </div>
                      {(query.trim() || projectTypeFilter !== 'all' || categoryFilter !== 'all') ? (
                        <button
                          type="button"
                          className="font-bold text-book-primary hover:underline"
                          onClick={clearFilters}
                        >
                          清除筛选
                        </button>
                      ) : null}
                    </div>
                  </div>
                </div>
              </div>

              <div className="min-h-0 flex-1 overflow-y-auto p-3 pr-1 custom-scrollbar">
                {loading ? (
                  <div className="py-10 text-center text-book-text-muted text-sm">加载中…</div>
                ) : groupedFiltered.length === 0 ? (
                  <div className="py-10 text-center text-book-text-muted text-sm">未找到</div>
                ) : (
                  <div className="space-y-4">
                    {groupedFiltered.map((group) => (
                      <div key={`group-${group.key}`} className="space-y-2">
                        <div className="sticky top-0 z-10 -mx-1 rounded-2xl border border-book-border/45 bg-book-bg-paper/80 backdrop-blur-md px-3 py-2 text-[10px] font-bold text-book-text-muted">
                          {group.label}
                          <span className="ml-1 font-mono text-book-text-main">{group.items.length}</span>
                        </div>
                        <div className="space-y-1">
                          {group.items.map((p) => {
                            const isSelected = selectedName === p.name;
                            return (
                              <button
                                key={p.name}
                                type="button"
                                onClick={() => void handleSelectPrompt(p.name)}
                                className={`w-full rounded-[22px] border px-3 py-2 text-left transition-all ${
                                  isSelected
                                    ? 'border-book-primary/30 bg-book-primary/10'
                                    : 'border-book-border/40 bg-book-bg-paper/40 hover:border-book-primary/20 hover:bg-book-bg-paper/55'
                                }`}
                              >
                                <div className="flex items-center justify-between gap-2">
                                  <div className="min-w-0">
                                    <div className="truncate text-xs font-bold text-book-text-main">{p.title || p.name}</div>
                                    <div className="mt-1 truncate text-[10px] text-book-text-muted">
                                      {p.status || 'active'} · {formatLabel(PROJECT_TYPE_LABELS, normalizeKey(p.project_type))}
                                    </div>
                                  </div>
                                  {p.is_modified ? (
                                    <span className="shrink-0 text-[10px] rounded-full border border-book-primary/25 bg-book-primary/10 px-2 py-0.5 font-bold text-book-primary">
                                      已修改
                                    </span>
                                  ) : null}
                                </div>
                              </button>
                            );
                          })}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </aside>

            <section className="min-h-0 flex flex-col">
              <div className="shrink-0 border-b border-book-border/45 bg-book-bg/40 p-4">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <div className="max-w-full truncate text-sm font-bold text-book-text-main">
                        {selected ? (selected.title || selected.name) : '提示词编辑器'}
                      </div>
                      {!isAdmin ? (
                        <span className="inline-flex rounded-full border border-book-border/55 bg-book-bg-paper/70 px-2.5 py-1 text-[10px] font-bold text-book-text-muted">
                          只读
                        </span>
                      ) : null}
                      {selected?.is_modified ? (
                        <span className="inline-flex rounded-full border border-book-primary/25 bg-book-primary/10 px-2.5 py-1 text-[10px] font-bold text-book-primary">
                          已修改
                        </span>
                      ) : null}
                      {isDirty ? (
                        <span className="inline-flex rounded-full border border-book-primary/25 bg-book-primary/10 px-2.5 py-1 text-[10px] font-bold text-book-primary">
                          未应用
                        </span>
                      ) : null}
                      {selected && isAdmin ? (
                        <span className="inline-flex items-center rounded-full border border-book-border/55 bg-book-bg-paper/70 px-2.5 py-1 text-[10px] font-semibold text-book-text-muted">
                          Ctrl/⌘ + S
                        </span>
                      ) : null}
                    </div>

                    {selected?.description ? (
                      <div className="mt-1 text-[11px] leading-relaxed text-book-text-muted line-clamp-2">
                        {selected.description}
                      </div>
                    ) : (
                      <div className="mt-1 text-[11px] text-book-text-muted">从左侧选择一个提示词后开始编辑。</div>
                    )}

                    {selectedHiddenByFilter ? (
                      <div className="mt-2 text-[11px] text-book-accent">
                        当前提示词不在筛选结果中，
                        <button type="button" className="ml-1 font-bold hover:underline" onClick={clearFilters}>
                          清除筛选
                        </button>
                      </div>
                    ) : null}

                    {selected ? (
                      <div className="mt-2 flex flex-wrap items-center gap-2 text-[10px] text-book-text-muted">
                        <span className="inline-flex rounded-full border border-book-border/55 bg-book-bg-paper/70 px-2.5 py-1 font-semibold">
                          {formatLabel(PROJECT_TYPE_LABELS, normalizeKey(selected.project_type))}
                        </span>
                        <span className="inline-flex rounded-full border border-book-border/55 bg-book-bg-paper/70 px-2.5 py-1 font-semibold">
                          {formatLabel(CATEGORY_LABELS, normalizeKey(selected.category))}
                        </span>
                        <span className="inline-flex rounded-full border border-book-border/55 bg-book-bg-paper/70 px-2.5 py-1 font-semibold">
                          <span className="font-mono text-book-text-main">{selected.status || '—'}</span>
                        </span>
                      </div>
                    ) : null}
                  </div>

                  <div className="flex flex-wrap items-center justify-end gap-2">
                    <BookButton variant="ghost" size="sm" onClick={refreshSelected} disabled={!selectedName}>
                      <RefreshCw size={14} className="mr-1" />
                      重新加载
                    </BookButton>
                    <BookButton variant="ghost" size="sm" onClick={handleReset} disabled={resetting || !isAdmin || !selected}>
                      <RotateCcw size={14} className="mr-1" />
                      恢复默认
                    </BookButton>
                  </div>
                </div>
              </div>

              <div className="min-h-0 flex-1 overflow-hidden p-4">
                {!selected ? (
                  <div className="h-full flex items-center justify-center text-book-text-muted">请选择一个提示词</div>
                ) : (
                  <div className="flex h-full min-h-0 flex-col">
                    <textarea
                      value={contentDraft}
                      onChange={(e) => setContentDraft(e.target.value)}
                      readOnly={!isAdmin}
                      placeholder="在此编辑提示词内容…"
                      onKeyDown={(e) => {
                        if (!(e.ctrlKey || e.metaKey)) return;
                        if (e.key !== 's' && e.key !== 'S') return;
                        e.preventDefault();
                        if (!isAdmin || saving || !isDirty) return;
                        void handleSave();
                      }}
                      className="book-control custom-scrollbar flex-1 min-h-0 w-full rounded-[24px] border px-4 py-3 text-xs font-mono leading-relaxed text-book-text-main outline-none focus:border-book-primary/45 focus:ring-2 focus:ring-book-primary/18 transition-all duration-200 resize-none"
                    />
                  </div>
                )}
              </div>
            </section>
          </div>
        </div>
      </div>
    </SettingsTabPanel>
  );
};
