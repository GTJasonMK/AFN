import React, { useEffect, useMemo, useState, useCallback } from 'react';
import { novelsApi, CharacterPortrait } from '../../api/novels';
import { resolveAssetUrl } from '../../api/imageGeneration';
import { BookCard } from '../ui/BookCard';
import { BookButton } from '../ui/BookButton';
import { BookTextarea } from '../ui/BookInput';
import { Modal } from '../ui/Modal';
import { useToast } from '../feedback/Toast';
import { confirmDialog } from '../feedback/ConfirmDialog';
import { CheckCircle2, Image as ImageIcon, Plus, RefreshCw, Settings2, Trash2 } from 'lucide-react';

interface CharacterPortraitGalleryProps {
  projectId: string;
  characterNames?: string[];
  characterProfiles?: Record<string, string>;
}

type PortraitStyle = 'anime' | 'manga' | 'realistic';

const DEFAULT_STYLE_OPTIONS: Array<{ style: PortraitStyle; name: string; description: string }> = [
  { style: 'anime', name: '动漫', description: '日系动漫风格，色彩鲜艳' },
  { style: 'manga', name: '漫画', description: '黑白漫画风格，强调线条与阴影' },
  { style: 'realistic', name: '写实', description: '更接近真人照片效果' },
];

const normalizeName = (value: any) => String(value || '').trim();

export const CharacterPortraitGallery: React.FC<CharacterPortraitGalleryProps> = ({ projectId, characterNames, characterProfiles }) => {
  const { addToast } = useToast();
  const [portraits, setPortraits] = useState<CharacterPortrait[]>([]);
  const [loading, setLoading] = useState(true);
  const [styles, setStyles] = useState(DEFAULT_STYLE_OPTIONS);
  const [style, setStyle] = useState<PortraitStyle>('anime');

  const [busyKey, setBusyKey] = useState<string | null>(null);

  // 管理弹窗
  const [manageName, setManageName] = useState<string | null>(null);

  // 生成/重绘弹窗
  const [isGenOpen, setIsGenOpen] = useState(false);
  const [genMode, setGenMode] = useState<'generate' | 'regenerate'>('generate');
  const [genName, setGenName] = useState('');
  const [genPortraitId, setGenPortraitId] = useState<string | null>(null);
  const [genDescription, setGenDescription] = useState('');
  const [genStyle, setGenStyle] = useState<PortraitStyle>('anime');
  const [genCustomPrompt, setGenCustomPrompt] = useState('');

  const fetchPortraits = useCallback(async () => {
    try {
      const data = await novelsApi.getPortraits(projectId);
      setPortraits(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchPortraits();
  }, [fetchPortraits]);

  const fetchStyles = useCallback(async () => {
    try {
      const list = await novelsApi.getPortraitStyles();
      if (Array.isArray(list) && list.length) {
        const normalized = list
          .map((s) => ({
            style: String(s.style || '').trim() as PortraitStyle,
            name: String(s.name || '').trim(),
            description: String(s.description || '').trim(),
          }))
          .filter((s) => s.style === 'anime' || s.style === 'manga' || s.style === 'realistic');
        if (normalized.length) setStyles(normalized);
      }
    } catch (e) {
      console.error(e);
      // 不阻塞：回退到默认选项
    }
  }, []);

  useEffect(() => {
    fetchStyles();
  }, [fetchStyles]);

  const portraitsByName = useMemo(() => {
    const map = new Map<string, CharacterPortrait[]>();
    for (const p of portraits) {
      const name = normalizeName((p as any)?.character_name);
      if (!name) continue;
      const list = map.get(name) || [];
      list.push(p);
      map.set(name, list);
    }
    // 让激活的排前面、时间新的排前面（尽量稳定展示）
    for (const [name, list] of map.entries()) {
      list.sort((a, b) => {
        const aActive = Boolean((a as any)?.is_active);
        const bActive = Boolean((b as any)?.is_active);
        if (aActive !== bActive) return aActive ? -1 : 1;
        const aTime = Date.parse(String((a as any)?.updated_at || (a as any)?.created_at || '')) || 0;
        const bTime = Date.parse(String((b as any)?.updated_at || (b as any)?.created_at || '')) || 0;
        return bTime - aTime;
      });
      map.set(name, list);
    }
    return map;
  }, [portraits]);

  const activePortraitByName = useMemo(() => {
    const map = new Map<string, CharacterPortrait | null>();
    for (const [name, list] of portraitsByName.entries()) {
      const active = list.find((p) => Boolean((p as any)?.is_active)) || list[0] || null;
      map.set(name, active);
    }
    return map;
  }, [portraitsByName]);

  const allNames = useMemo(() => {
    const set = new Set<string>();
    (characterNames || []).forEach((n) => {
      const name = normalizeName(n);
      if (name) set.add(name);
    });
    portraits.forEach((p) => {
      const name = normalizeName((p as any)?.character_name);
      if (name) set.add(name);
    });
    return Array.from(set).sort((a, b) => a.localeCompare(b, 'zh-CN'));
  }, [characterNames, portraits]);

  const missingNames = useMemo(() => {
    if (!Array.isArray(characterNames) || characterNames.length === 0) return [];
    const miss: string[] = [];
    for (const n of characterNames) {
      const name = normalizeName(n);
      if (!name) continue;
      const hasAny = Boolean(portraitsByName.get(name)?.length);
      if (!hasAny) miss.push(name);
    }
    return miss;
  }, [characterNames, portraitsByName]);

  const openGenerateModal = useCallback((name: string) => {
    const safeName = normalizeName(name);
    if (!safeName) return;
    setGenMode('generate');
    setGenName(safeName);
    setGenPortraitId(null);
    setGenStyle(style);
    setGenCustomPrompt('');
    setGenDescription(normalizeName(characterProfiles?.[safeName] || ''));
    setIsGenOpen(true);
  }, [characterProfiles, style]);

  const openRegenerateModal = useCallback((name: string, portraitId: string) => {
    const safeName = normalizeName(name);
    const id = normalizeName(portraitId);
    if (!safeName || !id) return;
    setGenMode('regenerate');
    setGenName(safeName);
    setGenPortraitId(id);
    setGenStyle(style);
    setGenCustomPrompt('');
    setGenDescription('');
    setIsGenOpen(true);
  }, [style]);

  const runGenerateOrRegenerate = useCallback(async () => {
    const name = normalizeName(genName);
    if (!name) return;

    const key = genMode === 'generate' ? `gen:${name}` : `regen:${genPortraitId || 'unknown'}`;
    setBusyKey(key);
    try {
      if (genMode === 'generate') {
        await novelsApi.generatePortrait(projectId, name, genDescription, { style: genStyle, customPrompt: genCustomPrompt });
        addToast('立绘已生成', 'success');
      } else {
        if (!genPortraitId) {
          addToast('缺少 portrait_id，无法重绘', 'error');
          return;
        }
        await novelsApi.regeneratePortrait(projectId, genPortraitId, { style: genStyle, customPrompt: genCustomPrompt });
        addToast('立绘已重绘', 'success');
      }
      setIsGenOpen(false);
      await fetchPortraits();
    } catch (e) {
      console.error(e);
      addToast('操作失败（请查看后端日志）', 'error');
    } finally {
      setBusyKey(null);
    }
  }, [addToast, fetchPortraits, genCustomPrompt, genDescription, genMode, genName, genPortraitId, genStyle, projectId]);

	  const handleGenerateMissing = useCallback(async () => {
	    if (missingNames.length === 0) {
	      addToast('暂无需要生成的角色立绘', 'info');
	      return;
	    }
	    const ok = await confirmDialog({
	      title: '批量生成立绘',
	      message: `将为 ${missingNames.length} 个角色生成立绘，可能耗时较长。\n是否继续？`,
	      confirmText: '继续',
	      dialogType: 'warning',
	    });
	    if (!ok) return;

    setBusyKey('bulk');
    try {
      // 如果提供了角色外观描述，优先使用后端批量接口（更快，且会标记 auto_generated/is_secondary）
      if (characterProfiles && Object.keys(characterProfiles).length > 0) {
        const payload: Record<string, string> = {};
        for (const name of missingNames) {
          payload[name] = String(characterProfiles[name] || '').trim() || name;
        }
        const res = await novelsApi.autoGeneratePortraits(projectId, payload, { style, excludeExisting: true });
        const failedCount = Number(res?.failed_count || 0);
        if (failedCount > 0) {
          const failedNames = Array.isArray(res?.failed_characters) ? res.failed_characters.join('、') : '';
          addToast(`批量生成完成，但有 ${failedCount} 个失败：${failedNames || '请查看日志'}`, 'error');
        } else {
          addToast('批量生成完成', 'success');
        }
      } else {
        // 回退：逐个生成（会使用蓝图默认描述）
        for (const name of missingNames) {
          await novelsApi.generatePortrait(projectId, name, '', { style });
        }
        addToast('批量生成完成', 'success');
      }
      await fetchPortraits();
    } catch (e) {
      console.error(e);
      addToast('批量生成失败（请查看后端日志）', 'error');
    } finally {
      setBusyKey(null);
    }
  }, [addToast, characterProfiles, fetchPortraits, missingNames, projectId, style]);

  const handleSetActive = useCallback(async (portraitId: string) => {
    const id = normalizeName(portraitId);
    if (!id) return;
    setBusyKey(`active:${id}`);
    try {
      await novelsApi.setActivePortrait(projectId, id);
      addToast('已设为当前使用', 'success');
      await fetchPortraits();
    } catch (e) {
      console.error(e);
      addToast('设置失败（请查看后端日志）', 'error');
    } finally {
      setBusyKey(null);
    }
  }, [addToast, fetchPortraits, projectId]);

	  const handleDelete = useCallback(async (portraitId: string) => {
	    const id = normalizeName(portraitId);
	    if (!id) return;
	    const ok = await confirmDialog({
	      title: '删除立绘',
	      message: '确定要删除该立绘吗？此操作不可恢复。',
	      confirmText: '删除',
	      dialogType: 'danger',
	    });
	    if (!ok) return;
	    setBusyKey(`del:${id}`);
	    try {
	      await novelsApi.deletePortrait(projectId, id);
      addToast('立绘已删除', 'success');
      await fetchPortraits();
    } catch (e) {
      console.error(e);
      addToast('删除失败（请查看后端日志）', 'error');
    } finally {
      setBusyKey(null);
    }
  }, [addToast, fetchPortraits, projectId]);

  const closeManage = () => setManageName(null);

  const managedPortraits = useMemo(() => {
    const name = normalizeName(manageName);
    if (!name) return [];
    return portraitsByName.get(name) || [];
  }, [manageName, portraitsByName]);

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h3 className="font-serif text-lg font-bold text-book-text-main flex items-center gap-2">
          <ImageIcon size={20} className="text-book-accent" />
          角色画廊
        </h3>
        <div className="flex items-center gap-2">
          <div className="hidden sm:flex items-center gap-2 text-[11px] text-book-text-muted">
            <span className="font-bold">风格</span>
            <select
              value={style}
              onChange={(e) => setStyle(e.target.value as PortraitStyle)}
              className="px-2 py-1 rounded bg-book-bg border border-book-border/60 text-book-text-main outline-none focus:border-book-primary/60"
              disabled={Boolean(busyKey) || loading}
              title="生成/重绘时使用的默认立绘风格"
            >
              {styles.map((s) => (
                <option key={s.style} value={s.style}>
                  {s.name}
                </option>
              ))}
            </select>
          </div>

          {missingNames.length > 0 ? (
            <BookButton
              variant="ghost"
              size="sm"
              onClick={handleGenerateMissing}
              disabled={Boolean(busyKey) || loading}
              title="为蓝图中缺失立绘的角色一键生成（可能耗时较长）"
            >
              <Plus size={14} className="mr-1" />
              生成缺失（{missingNames.length}）
            </BookButton>
          ) : null}

          <BookButton variant="ghost" size="sm" onClick={fetchPortraits} disabled={loading || Boolean(busyKey)}>
            <RefreshCw size={14} className={`mr-1 ${busyKey === 'refresh' ? 'animate-spin' : ''}`} />
            刷新
          </BookButton>
        </div>
      </div>

      {loading ? (
        <div className="grid grid-cols-2 gap-4">
          {[1, 2].map(i => (
            <div key={i} className="aspect-[3/4] bg-book-bg-paper animate-pulse rounded-lg" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {allNames.map((name) => {
            const list = portraitsByName.get(name) || [];
            const portrait = activePortraitByName.get(name) || null;
            const active = Boolean(portrait?.is_active);
            const hasAny = list.length > 0;
            const busy = busyKey === `gen:${name}` || busyKey === `regen:${portrait?.id || ''}`;
            return (
            <BookCard key={name} className="p-2 flex flex-col gap-2 group">
              <div className="relative aspect-[3/4] overflow-hidden rounded-md bg-book-bg">
                {portrait?.image_url ? (
                  <img 
                    src={resolveAssetUrl(String(portrait.image_url))} 
                    alt={name}
                    loading="lazy"
                    decoding="async"
                    className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-book-text-muted">
                    未生成
                  </div>
                )}
                
                {/* Overlay actions */}
                <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                  <BookButton
                    variant="primary"
                    size="sm"
                    onClick={() => {
                      if (!hasAny) openGenerateModal(name);
                      else if (portrait?.id) openRegenerateModal(name, String(portrait.id));
                      else openGenerateModal(name);
                    }}
                    disabled={Boolean(busyKey) || busy}
                    title={hasAny ? '重绘当前立绘' : '生成立绘'}
                  >
                    <RefreshCw size={14} className={`mr-1 ${Boolean(busyKey) || busy ? 'animate-spin' : ''}`} />
                    {hasAny ? '重绘' : '生成'}
                  </BookButton>

                  {hasAny ? (
                    <BookButton
                      variant="secondary"
                      size="sm"
                      onClick={() => setManageName(name)}
                      disabled={Boolean(busyKey)}
                      title="管理该角色的所有立绘（设为当前/删除等）"
                    >
                      <Settings2 size={14} className="mr-1" />
                      管理
                    </BookButton>
                  ) : null}
                </div>
              </div>
              
              <div className="text-center">
                <div className="font-bold text-book-text-main text-sm flex items-center justify-center gap-1">
                  {name}
                  {active ? (
                    <span title="当前使用">
                      <CheckCircle2 size={14} className="text-book-primary" />
                    </span>
                  ) : null}
                </div>
                <div className="text-xs text-book-text-muted truncate">
                  {hasAny ? `${portrait?.style || ''}${list.length > 1 ? ` · ${list.length}张` : ''}` : '—'}
                </div>
              </div>
            </BookCard>
          );
          })}
          
          {allNames.length === 0 && (
            <div className="col-span-full py-8 text-center text-book-text-muted text-sm">
              暂无角色数据
            </div>
          )}
        </div>
      )}

      {/* 立绘管理弹窗 */}
      <Modal
        isOpen={Boolean(manageName)}
        onClose={closeManage}
        title={manageName ? `立绘管理 - ${manageName}` : '立绘管理'}
        maxWidthClassName="max-w-4xl"
        footer={
          <div className="flex justify-end gap-2">
            {manageName ? (
              <BookButton
                variant="primary"
                onClick={() => openGenerateModal(manageName)}
                disabled={Boolean(busyKey)}
              >
                <Plus size={16} className="mr-1" />
                新建一张
              </BookButton>
            ) : null}
            <BookButton variant="ghost" onClick={closeManage}>关闭</BookButton>
          </div>
        }
      >
        <div className="space-y-4">
          <div className="text-xs text-book-text-muted leading-relaxed bg-book-bg p-3 rounded-lg border border-book-border/50">
            提示：你可以在这里把某张立绘“设为当前使用”，或删除/重绘指定立绘。
          </div>

          {managedPortraits.length ? (
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {managedPortraits.map((p) => {
                const id = String((p as any)?.id || '');
                const isActive = Boolean((p as any)?.is_active);
                const isSecondary = Boolean((p as any)?.is_secondary);
                const autoGen = Boolean((p as any)?.auto_generated);
                const createdAt = String((p as any)?.created_at || '');
                const label = [
                  isActive ? '当前' : '',
                  isSecondary ? '次要' : '',
                  autoGen ? '自动' : '',
                ].filter(Boolean).join(' · ');

                return (
                  <BookCard key={id || `${manageName}-${createdAt}`} className="p-3 space-y-2">
                    <div className="relative aspect-[3/4] overflow-hidden rounded-md bg-book-bg">
                      {p?.image_url ? (
                        <img
                          src={resolveAssetUrl(String(p.image_url))}
                          alt={manageName || ''}
                          loading="lazy"
                          decoding="async"
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center text-book-text-muted">
                          无图片
                        </div>
                      )}
                      {label ? (
                        <div className="absolute top-2 left-2 text-[10px] px-2 py-0.5 rounded-full bg-black/60 text-white">
                          {label}
                        </div>
                      ) : null}
                    </div>

                    <div className="flex items-center justify-between gap-2">
                      <div className="text-xs text-book-text-muted truncate">
                        {String((p as any)?.style || '') || '—'}
                        {createdAt ? ` · ${createdAt.slice(0, 19).replace('T', ' ')}` : ''}
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <BookButton
                        variant="secondary"
                        size="sm"
                        onClick={() => handleSetActive(id)}
                        disabled={isActive || Boolean(busyKey)}
                        title={isActive ? '已是当前使用' : '设为当前使用'}
                      >
                        <CheckCircle2 size={14} className="mr-1" />
                        设为当前
                      </BookButton>
                      <BookButton
                        variant="ghost"
                        size="sm"
                        onClick={() => openRegenerateModal(manageName || '', id)}
                        disabled={Boolean(busyKey)}
                        title="重绘该立绘（不会新增条目）"
                      >
                        <RefreshCw size={14} className="mr-1" />
                        重绘
                      </BookButton>
                      <BookButton
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDelete(id)}
                        disabled={Boolean(busyKey)}
                        title="删除该立绘"
                      >
                        <Trash2 size={14} className="mr-1" />
                        删除
                      </BookButton>
                    </div>
                  </BookCard>
                );
              })}
            </div>
          ) : (
            <div className="py-10 text-center text-sm text-book-text-muted">
              暂无立绘数据
            </div>
          )}
        </div>
      </Modal>

      {/* 生成/重绘弹窗 */}
      <Modal
        isOpen={isGenOpen}
        onClose={() => {
          setIsGenOpen(false);
          setGenPortraitId(null);
        }}
        title={genMode === 'generate' ? `生成立绘 - ${genName}` : `重绘立绘 - ${genName}`}
        maxWidthClassName="max-w-2xl"
        footer={
          <div className="flex justify-end gap-2">
            <BookButton
              variant="ghost"
              onClick={() => setIsGenOpen(false)}
              disabled={Boolean(busyKey)}
            >
              取消
            </BookButton>
            <BookButton
              variant="primary"
              onClick={runGenerateOrRegenerate}
              disabled={Boolean(busyKey)}
            >
              确定
            </BookButton>
          </div>
        }
      >
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="space-y-1">
              <div className="text-xs text-book-text-muted font-bold">风格</div>
              <select
                value={genStyle}
                onChange={(e) => setGenStyle(e.target.value as PortraitStyle)}
                className="w-full px-3 py-2 rounded-lg bg-book-bg border border-book-border text-sm text-book-text-main outline-none focus:border-book-primary/60"
                disabled={Boolean(busyKey)}
              >
                {styles.map((s) => (
                  <option key={s.style} value={s.style}>{s.name}</option>
                ))}
              </select>
              <div className="text-[11px] text-book-text-muted">
                {styles.find((s) => s.style === genStyle)?.description || ''}
              </div>
            </div>
            <BookTextarea
              label="自定义提示词（可选）"
              value={genCustomPrompt}
              onChange={(e) => setGenCustomPrompt(e.target.value)}
              rows={4}
              placeholder="追加到系统提示词后，例如：更偏冷色调、加入特定服装细节…"
              disabled={Boolean(busyKey)}
            />
          </div>

          {genMode === 'generate' ? (
            <BookTextarea
              label="角色外貌描述（可选）"
              value={genDescription}
              onChange={(e) => setGenDescription(e.target.value)}
              rows={6}
              placeholder="留空则尝试从蓝图自动补全（身份/性格等）"
              disabled={Boolean(busyKey)}
            />
          ) : null}
        </div>
      </Modal>
    </div>
  );
};
