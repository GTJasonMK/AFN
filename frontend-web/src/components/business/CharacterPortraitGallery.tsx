import React, { useState, useEffect } from 'react';
import { novelsApi, CharacterPortrait } from '../../api/novels';
import { BookCard } from '../ui/BookCard';
import { BookButton } from '../ui/BookButton';
import { API_BASE_URL } from '../../api/client';
import { RefreshCw, Image as ImageIcon } from 'lucide-react';

interface CharacterPortraitGalleryProps {
  projectId: string;
}

export const CharacterPortraitGallery: React.FC<CharacterPortraitGalleryProps> = ({ projectId }) => {
  const [portraits, setPortraits] = useState<CharacterPortrait[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState<string | null>(null);

  useEffect(() => {
    fetchPortraits();
  }, [projectId]);

  const fetchPortraits = async () => {
    try {
      const data = await novelsApi.getPortraits(projectId);
      setPortraits(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async (charName: string) => {
    setGenerating(charName);
    try {
      await novelsApi.generatePortrait(projectId, charName, ""); // Empty desc to use blueprint default
      await fetchPortraits();
    } catch (e) {
      console.error(e);
    } finally {
      setGenerating(null);
    }
  };

  // Helper to construct full image URL
  // Backend returns relative path or full URL. If relative, prepend base.
  // Note: The backend 'CharacterPortraitResponse' usually returns a full URL if configured, 
  // or we need to handle the serving path.
  // Assuming backend returns something like '/api/image-generation/files/...' or just path.
  const getImageUrl = (url: string) => {
    if (url.startsWith('http')) return url;
    // Remove /api prefix from base if present to avoid double api
    const baseUrl = API_BASE_URL.replace(/\/api$/, ''); 
    return `${baseUrl}${url}`;
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h3 className="font-serif text-lg font-bold text-book-text-main flex items-center gap-2">
          <ImageIcon size={20} className="text-book-accent" />
          角色画廊
        </h3>
        <BookButton variant="ghost" size="sm" onClick={fetchPortraits}>
          刷新
        </BookButton>
      </div>

      {loading ? (
        <div className="grid grid-cols-2 gap-4">
          {[1, 2].map(i => (
            <div key={i} className="aspect-[3/4] bg-book-bg-paper animate-pulse rounded-lg" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {portraits.map((portrait) => (
            <BookCard key={portrait.id} className="p-2 flex flex-col gap-2 group">
              <div className="relative aspect-[3/4] overflow-hidden rounded-md bg-book-bg">
                {portrait.image_url ? (
                  <img 
                    src={getImageUrl(portrait.image_url)} 
                    alt={portrait.character_name}
                    className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-book-text-muted">
                    无图片
                  </div>
                )}
                
                {/* Overlay actions */}
                <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                  <BookButton 
                    variant="primary" 
                    size="sm"
                    onClick={() => handleGenerate(portrait.character_name)}
                    disabled={generating === portrait.character_name}
                  >
                    <RefreshCw size={14} className={`mr-1 ${generating === portrait.character_name ? 'animate-spin' : ''}`} />
                    重绘
                  </BookButton>
                </div>
              </div>
              
              <div className="text-center">
                <div className="font-bold text-book-text-main text-sm">{portrait.character_name}</div>
                <div className="text-xs text-book-text-muted truncate">{portrait.style}</div>
              </div>
            </BookCard>
          ))}
          
          {portraits.length === 0 && (
            <div className="col-span-full py-8 text-center text-book-text-muted text-sm">
              暂无角色立绘
            </div>
          )}
        </div>
      )}
    </div>
  );
};