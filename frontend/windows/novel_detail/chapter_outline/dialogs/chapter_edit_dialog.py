"""
章节大纲编辑对话框

复用写作台 OutlineEditDialog，保留新增/编辑模式文案与校验。
"""

from windows.writing_desk.dialogs import OutlineEditDialog


class ChapterOutlineEditDialog(OutlineEditDialog):
    """章节大纲编辑对话框（复用写作台对话框）"""

    def __init__(
        self,
        chapter_number: int,
        title: str = "",
        summary: str = "",
        is_new: bool = False,
        parent=None
    ):
        header_text = f"{'新增' if is_new else '编辑'}第 {chapter_number} 章大纲"
        confirm_text = "新增" if is_new else "保存"
        dialog_title = f"{'新增章节大纲' if is_new else '编辑章节大纲'} - 第{chapter_number}章"
        super().__init__(
            parent=parent,
            chapter_number=chapter_number,
            title=title,
            summary=summary,
            header_text=header_text,
            confirm_text=confirm_text,
            require_title=True,
            dialog_title=dialog_title,
            style_variant="book"
        )

    def get_values(self) -> tuple:
        """获取编辑后的值"""
        return self.getValues()
