import { useCallback, useState } from 'react';
import type { Dispatch, SetStateAction } from 'react';
import { novelsApi } from '../../api/novels';
import { confirmDialog } from '../../components/feedback/ConfirmDialog';

type UseNovelDetailAvatarManagerParams = {
  id: string | undefined;
  projectHasBlueprint: boolean;
  hasAvatar: boolean;
  setBlueprintData: Dispatch<SetStateAction<any>>;
  addToast: (message: string, type?: string) => void;
};

export const useNovelDetailAvatarManager = ({
  id,
  projectHasBlueprint,
  hasAvatar,
  setBlueprintData,
  addToast,
}: UseNovelDetailAvatarManagerParams) => {
  const [avatarLoading, setAvatarLoading] = useState(false);

  const handleGenerateAvatar = useCallback(async () => {
    if (!id) return;
    setAvatarLoading(true);
    try {
      const result = await novelsApi.generateAvatar(id);
      setBlueprintData((prev: any) => ({
        ...prev,
        avatar_svg: result.avatar_svg,
        avatar_animal: result.animal,
      }));
      addToast('头像已生成', 'success');
    } catch (e) {
      console.error(e);
      addToast('头像生成失败（请检查 LLM 配置与后端日志）', 'error');
    } finally {
      setAvatarLoading(false);
    }
  }, [addToast, id, setBlueprintData]);

  const handleAvatarClick = useCallback(async () => {
    if (avatarLoading) return;
    if (!projectHasBlueprint) {
      addToast('请先生成蓝图后再生成头像', 'error');
      return;
    }
    if (hasAvatar) {
      const ok = await confirmDialog({
        title: '重新生成头像',
        message: '确定要重新生成头像吗？\n当前头像将被替换。',
        confirmText: '重新生成',
        dialogType: 'warning',
      });
      if (!ok) return;
    }
    await handleGenerateAvatar();
  }, [addToast, avatarLoading, handleGenerateAvatar, hasAvatar, projectHasBlueprint]);

  const handleDeleteAvatar = useCallback(async () => {
    if (!id) return;
    const ok = await confirmDialog({
      title: '删除头像',
      message: '确定要删除该小说头像吗？',
      confirmText: '删除',
      dialogType: 'danger',
    });
    if (!ok) return;
    setAvatarLoading(true);
    try {
      await novelsApi.deleteAvatar(id);
      setBlueprintData((prev: any) => ({
        ...prev,
        avatar_svg: null,
        avatar_animal: null,
      }));
      addToast('头像已删除', 'success');
    } catch (e) {
      console.error(e);
      addToast('头像删除失败', 'error');
    } finally {
      setAvatarLoading(false);
    }
  }, [addToast, id, setBlueprintData]);

  return {
    avatarLoading,
    handleAvatarClick,
    handleDeleteAvatar,
  };
};
