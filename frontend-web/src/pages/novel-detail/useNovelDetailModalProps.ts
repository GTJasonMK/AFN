import { useMemo } from 'react';
import {
  useLazyBusinessModalProps,
} from './modal-props/useLazyBusinessModalProps';
import {
  useLatestPartOutlineModalProps,
} from './modal-props/useLatestPartOutlineModalProps';
import {
  useLatestChapterOutlineModalProps,
} from './modal-props/useLatestChapterOutlineModalProps';
import type {
  UseNovelDetailModalPropsParams,
  UseNovelDetailModalPropsResult,
} from './modal-props/types';

export const useNovelDetailModalProps = ({
  business,
  latestPart,
  latestChapter,
}: UseNovelDetailModalPropsParams): UseNovelDetailModalPropsResult => {
  const lazyBusinessModalProps = useLazyBusinessModalProps(business);
  const latestPartOutlineModalProps = useLatestPartOutlineModalProps(latestPart);
  const latestChapterOutlineModalProps = useLatestChapterOutlineModalProps(latestChapter);

  return useMemo(() => ({
    lazyBusinessModalProps,
    latestPartOutlineModalProps,
    latestChapterOutlineModalProps,
  }), [
    lazyBusinessModalProps,
    latestChapterOutlineModalProps,
    latestPartOutlineModalProps,
  ]);
};
