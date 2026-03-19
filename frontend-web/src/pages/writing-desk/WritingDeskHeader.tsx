import React from 'react';
import {
  ArrowLeft,
  Download,
  Eye,
  FileText,
  PanelLeft,
  PanelRight,
  ScrollText,
  Upload,
} from 'lucide-react';
import { Dropdown } from '../../components/ui/Dropdown';
import { BookButton } from '../../components/ui/BookButton';

export const WritingDeskHeader: React.FC<{
  projectTitle: string;
  currentChapterNumber?: number | null;
  onBack: () => void;
  isSidebarOpen: boolean;
  onToggleSidebar: () => void;
  onOpenImportChapter: () => void;
  onExportTxt: () => void;
  onExportMarkdown: () => void;
  onOpenWritingNotes: () => void;
  onOpenPromptPreview: () => void;
  onOpenProjectDetail: () => void;
  isAssistantOpen: boolean;
  onToggleAssistant: () => void;
}> = ({
  projectTitle,
  currentChapterNumber,
  onBack,
  isSidebarOpen,
  onToggleSidebar,
  onOpenImportChapter,
  onExportTxt,
  onExportMarkdown,
  onOpenWritingNotes,
  onOpenPromptPreview,
  onOpenProjectDetail,
  isAssistantOpen,
  onToggleAssistant,
}) => {
  return (
    <section className="dramatic-surface rounded-[28px] px-4 py-2 sm:px-5 sm:py-3">
      <div className="relative z-[1]">
        <div className="flex items-center justify-between gap-3">
          <div className="flex min-w-0 flex-1 items-center gap-3">
            <BookButton variant="ghost" size="sm" onClick={onBack} title="返回项目列表">
              <ArrowLeft size={16} />
              返回
            </BookButton>

            <div className="min-w-0 flex-1">
              <div className="flex min-w-0 items-center gap-2 overflow-hidden">
                <div className="hidden xl:inline-flex eyebrow">Writing Desk</div>
                <h1 className="min-w-0 flex-1 truncate font-serif text-xl font-bold leading-tight tracking-[-0.03em] text-book-text-main">
                  {projectTitle || '写作台'}
                </h1>
                {currentChapterNumber ? (
                  <span className="story-pill-compact hidden md:inline-flex">第 {currentChapterNumber} 章</span>
                ) : null}
              </div>
            </div>
          </div>

          <div className="flex shrink-0 items-center gap-2">
            <BookButton
              variant={isSidebarOpen ? 'secondary' : 'ghost'}
              size="sm"
              onClick={onToggleSidebar}
              title={isSidebarOpen ? '隐藏章节导航' : '显示章节导航'}
            >
              <PanelLeft size={16} />
              章节
            </BookButton>

            <BookButton
              variant={isAssistantOpen ? 'secondary' : 'ghost'}
              size="sm"
              onClick={onToggleAssistant}
              title={isAssistantOpen ? '隐藏写作助手' : '显示写作助手'}
            >
              <PanelRight size={16} />
              助手
            </BookButton>

            <BookButton variant="ghost" size="sm" onClick={onOpenProjectDetail} title="项目详情（Story Control）">
              <FileText size={16} />
              项目详情
            </BookButton>

            <Dropdown
              label="导入导出"
              items={[
                { label: '导入章节', icon: <Upload size={14} />, onClick: onOpenImportChapter },
                { label: '导出 TXT', icon: <Download size={14} />, onClick: onExportTxt },
                { label: '导出 Markdown', icon: <Download size={14} />, onClick: onExportMarkdown },
              ]}
            />

            <Dropdown
              label="工具"
              items={[
                { label: '写作指导', icon: <ScrollText size={14} />, onClick: onOpenWritingNotes },
                { label: '提示词预览', icon: <Eye size={14} />, onClick: onOpenPromptPreview },
              ]}
            />
          </div>
        </div>
      </div>
    </section>
  );
};
