import React, { useEffect, useState } from 'react';
import { apiClient } from '../api/client';
import { BookCard } from '../components/ui/BookCard';
import { BookButton } from '../components/ui/BookButton';

interface Novel {
  id: string;
  title: string;
  description?: string;
  cover_image?: string;
  updated_at: string;
}

export const NovelList: React.FC = () => {
  const [novels, setNovels] = useState<Novel[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchNovels = async () => {
      try {
        const res = await apiClient.get('/novels');
        setNovels(res.data);
      } catch (err) {
        console.error("Failed to fetch novels", err);
      } finally {
        setLoading(false);
      }
    };
    fetchNovels();
  }, []);

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="font-serif text-3xl font-bold text-book-text-main mb-2">
            我的书桌
          </h1>
          <p className="text-book-text-sub text-sm">
            Writing Desk / 项目列表
          </p>
        </div>
        <BookButton variant="primary" size="lg">
          + 新建小说
        </BookButton>
      </div>

      {loading ? (
        <div className="text-book-text-muted">加载中...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {novels.map((novel) => (
            <BookCard key={novel.id} hover className="flex flex-col h-full group">
              <div className="flex-1">
                <div className="flex justify-between items-start">
                  <h3 className="font-serif text-xl font-bold text-book-text-main mb-2 group-hover:text-book-primary transition-colors">
                    {novel.title}
                  </h3>
                  {/* 可以在这里放一个SVG Icon */}
                </div>
                <p className="text-book-text-sub text-sm line-clamp-3">
                  {novel.description || "暂无描述..."}
                </p>
              </div>
              
              <div className="mt-4 pt-4 border-t border-book-border/50 flex justify-between items-center text-xs text-book-text-muted">
                <span>{new Date(novel.updated_at).toLocaleDateString()}</span>
                <span className="bg-book-bg px-2 py-1 rounded">连载中</span>
              </div>
            </BookCard>
          ))}
          
          {/* 空状态下的占位卡片 */}
          {novels.length === 0 && (
            <BookCard variant="flat" className="border-dashed border-2 border-book-border flex items-center justify-center min-h-[200px]">
              <div className="text-center">
                <p className="text-book-text-muted mb-4">还没有项目</p>
                <BookButton variant="secondary" size="sm">创建第一个项目</BookButton>
              </div>
            </BookCard>
          )}
        </div>
      )}
    </div>
  );
};