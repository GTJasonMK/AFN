import React, { useMemo, useState, useEffect, useCallback } from 'react';
import { BookCard } from '../ui/BookCard';
import { BookButton } from '../ui/BookButton';
import { BadgeCheck, RefreshCw, Star, Loader2 } from 'lucide-react';
import { InsightCard } from './chapter/components/InsightCard';
import { writerApi } from '../../api/writer';
import { useToast } from '../feedback/Toast';

type EvaluationJson = {
  best_choice?: number;
  reason_for_choice?: string;
  evaluation?: Record<
    string,
    {
      pros?: string[];
      cons?: string[];
      overall_review?: string;
    }
  >;
  error?: string;
  details?: string;
};

const Chip: React.FC<{ children: React.ReactNode; className?: string }> = ({ children, className = '' }) => (
  <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] border border-book-border/50 bg-book-bg ${className}`}>
    {children}
  </span>
);

interface ChapterReviewViewProps {
  projectId: string;
  chapterNumber: number;
  onEvaluate?: () => void | Promise<void>;
}

export const ChapterReviewView: React.FC<ChapterReviewViewProps> = ({
  projectId,
  chapterNumber,
  onEvaluate,
}) => {
  const { addToast } = useToast();
  const [evaluation, setEvaluation] = useState<string | null>(null);
  const [versionCount, setVersionCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [isEvaluating, setIsEvaluating] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const chapter = await writerApi.getChapter(projectId, chapterNumber);
      const vs = Array.isArray(chapter.versions) ? chapter.versions : [];
      setVersionCount(vs.length);
      setEvaluation(chapter.evaluation || null);
    } catch (e) {
      console.error(e);
      addToast('获取评审数据失败', 'error');
    } finally {
      setLoading(false);
    }
  }, [addToast, chapterNumber, projectId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleEvaluate = async () => {
    if (onEvaluate) {
      setIsEvaluating(true);
      try {
        await onEvaluate();
        await fetchData();
      } finally {
        setIsEvaluating(false);
      }
    } else {
      setIsEvaluating(true);
      try {
        await writerApi.evaluateChapter(projectId, chapterNumber);
        addToast('评审完成', 'success');
        await fetchData();
      } catch (e) {
        console.error(e);
        addToast('评审失败', 'error');
      } finally {
        setIsEvaluating(false);
      }
    }
  };

  const handleSelectVersion = async (index: number) => {
    try {
      await writerApi.selectVersion(projectId, chapterNumber, index);
      addToast('版本已选择', 'success');
    } catch (e) {
      console.error(e);
      addToast('选择版本失败', 'error');
    }
  };

  const parsed = useMemo<EvaluationJson | null>(() => {
    if (!evaluation) return null;
    try {
      return JSON.parse(evaluation) as EvaluationJson;
    } catch {
      return null;
    }
  }, [evaluation]);

  const bestChoice = typeof parsed?.best_choice === 'number' ? parsed?.best_choice : null;
  const bestIndex = bestChoice ? bestChoice - 1 : null;

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 size={24} className="animate-spin text-book-primary" />
      </div>
    );
  }

  if (!evaluation) {
    const canEvaluate = versionCount >= 2;
    return (
      <div className="space-y-4">
        <InsightCard
          icon={<BadgeCheck size={16} className="text-book-primary" />}
          title={canEvaluate ? '暂无评审结果' : '无需评审'}
          description={
            canEvaluate
              ? '评审用于对比多个候选版本并推荐最佳版本。'
              : '评审需要至少 2 个版本；当前章节版本数不足。'
          }
          actions={
            canEvaluate ? (
              <BookButton variant="primary" size="sm" onClick={handleEvaluate} disabled={Boolean(isEvaluating)}>
                <RefreshCw size={14} className={`mr-1 ${isEvaluating ? 'animate-spin' : ''}`} />
                {isEvaluating ? '评审中...' : '开始评审'}
              </BookButton>
            ) : null
          }
        />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <InsightCard
        icon={<BadgeCheck size={16} className="text-book-primary" />}
        title={
          <>
            评审结果
            {bestChoice ? <Chip className="text-book-primary">推荐：版本 {bestChoice}</Chip> : null}
          </>
        }
        description={
          parsed?.reason_for_choice ||
          (parsed?.error ? `${parsed.error}${parsed.details ? `：${parsed.details}` : ''}` : '（无推荐理由）')
        }
        actions={
          <>
            {bestIndex !== null && bestIndex >= 0 && (
              <BookButton variant="secondary" size="sm" onClick={() => handleSelectVersion(bestIndex)} title="选择推荐版本">
                <Star size={14} className="mr-1" />
                选择推荐
              </BookButton>
            )}
            <BookButton variant="ghost" size="sm" onClick={handleEvaluate} disabled={Boolean(isEvaluating)}>
              <RefreshCw size={14} className={`mr-1 ${isEvaluating ? 'animate-spin' : ''}`} />
              {isEvaluating ? '评审中...' : '重新评审'}
            </BookButton>
          </>
        }
        actionsClassName="flex items-center gap-2"
      />

      {parsed?.evaluation ? (
        <div className="space-y-4">
          {Object.entries(parsed.evaluation).map(([key, value]) => {
            const versionNo = key.replace('version', '');
            const pros = Array.isArray(value.pros) ? value.pros : [];
            const cons = Array.isArray(value.cons) ? value.cons : [];
            return (
              <BookCard key={key} className="p-4">
                <div className="flex items-center justify-between gap-2 mb-2">
                  <div className="font-bold text-book-primary">版本 {versionNo}</div>
                  {bestChoice && Number(versionNo) === bestChoice ? (
                    <Chip className="text-book-primary">推荐</Chip>
                  ) : null}
                </div>

                {pros.length > 0 && (
                  <div className="mt-2">
                    <div className="text-xs font-bold text-book-text-sub mb-1">优点</div>
                    <ul className="list-disc list-inside text-sm text-book-text-main space-y-1">
                      {pros.map((p, idx) => (
                        <li key={`${key}-p-${idx}`}>{p}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {cons.length > 0 && (
                  <div className="mt-3">
                    <div className="text-xs font-bold text-book-text-sub mb-1">缺点</div>
                    <ul className="list-disc list-inside text-sm text-book-text-main space-y-1">
                      {cons.map((c, idx) => (
                        <li key={`${key}-c-${idx}`}>{c}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {value.overall_review ? (
                  <div className="mt-3 text-sm text-book-text-main leading-relaxed whitespace-pre-wrap">
                    <span className="font-bold text-book-text-sub mr-2">总结</span>
                    {value.overall_review}
                  </div>
                ) : null}
              </BookCard>
            );
          })}
        </div>
      ) : (
        <BookCard className="p-4">
          <div className="text-xs text-book-text-muted mb-2">原始数据</div>
          <pre className="text-xs text-book-text-main whitespace-pre-wrap font-mono leading-relaxed">{evaluation}</pre>
        </BookCard>
      )}
    </div>
  );
};
