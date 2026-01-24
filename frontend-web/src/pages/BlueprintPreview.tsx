import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { novelsApi } from '../api/novels';
import { BookCard } from '../components/ui/BookCard';
import { BookButton } from '../components/ui/BookButton';
import { ArrowLeft, Map, Users, ScrollText, Play } from 'lucide-react';

// 蓝图数据类型定义
interface BlueprintData {
  title: string;
  one_sentence_summary: string;
  world_setting: string;
  characters: Array<{
    name: string;
    identity: string;
    personality: string;
    goal: string;
  }>;
  full_synopsis: string;
}

export const BlueprintPreview: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<BlueprintData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (id) {
      // 实际开发中，这里获取项目详情，其中包含 blueprint
      novelsApi.get(id).then((project: any) => {
        if (project.blueprint) {
          setData(project.blueprint);
        }
        setLoading(false);
      }).catch(() => setLoading(false));
    }
  }, [id]);

  const handleStartWriting = () => {
    navigate(`/write/${id}`);
  };

  if (loading) return <div className="p-20 text-center text-book-text-muted">加载蓝图设定中...</div>;
  if (!data) return <div className="p-20 text-center text-book-text-muted">未找到蓝图数据</div>;

  return (
    <div className="max-w-5xl mx-auto p-8 space-y-10 animate-in fade-in slide-in-from-bottom-4 duration-500">
      {/* 头部标题区 */}
      <div className="flex justify-between items-end border-b border-book-border pb-6">
        <div className="space-y-2">
          <button 
            onClick={() => navigate(`/inspiration/${id}`)}
            className="text-sm text-book-text-muted hover:text-book-primary flex items-center gap-1 transition-colors"
          >
            <ArrowLeft size={14} /> 返回对话
          </button>
          <h1 className="font-serif text-4xl font-bold text-book-text-main">{data.title}</h1>
          <p className="text-xl text-book-text-sub font-serif italic opacity-80">“{data.one_sentence_summary}”</p>
        </div>
        <BookButton size="lg" onClick={handleStartWriting} className="mb-1">
          <Play size={18} className="mr-2 fill-current" /> 开始执笔
        </BookButton>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {/* 左侧：世界观与故事大纲 */}
        <div className="md:col-span-2 space-y-10">
          <section className="space-y-4">
            <h2 className="font-serif text-2xl font-bold text-book-text-main flex items-center gap-2">
              <Map className="text-book-primary" /> 世界观设定
            </h2>
            <BookCard variant="flat" className="bg-book-bg-paper/50 leading-relaxed text-book-text-secondary whitespace-pre-wrap">
              {data.world_setting}
            </BookCard>
          </section>

          <section className="space-y-4">
            <h2 className="font-serif text-2xl font-bold text-book-text-main flex items-center gap-2">
              <ScrollText className="text-book-primary" /> 故事梗概
            </h2>
            <BookCard variant="flat" className="bg-book-bg-paper/50 leading-relaxed text-book-text-secondary whitespace-pre-wrap">
              {data.full_synopsis}
            </BookCard>
          </section>
        </div>

        {/* 右侧：角色卡片列表 */}
        <div className="space-y-4">
          <h2 className="font-serif text-2xl font-bold text-book-text-main flex items-center gap-2">
            <Users className="text-book-primary" /> 登场角色
          </h2>
          <div className="space-y-4">
            {data.characters.map((char, index) => (
              <BookCard key={index} className="hover:border-book-primary/30 transition-colors">
                <div className="font-bold text-book-text-main border-b border-book-border/30 pb-1 mb-2">
                  {char.name}
                </div>
                <div className="text-xs space-y-1 text-book-text-sub">
                  <p><span className="font-semibold text-book-text-muted">身份：</span>{char.identity}</p>
                  <p><span className="font-semibold text-book-text-muted">性格：</span>{char.personality}</p>
                  <p><span className="font-semibold text-book-text-muted">目标：</span>{char.goal}</p>
                </div>
              </BookCard>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};