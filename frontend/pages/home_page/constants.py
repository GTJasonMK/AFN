"""
首页常量和工具函数

包含创作箴言集和排序工具函数。
"""


# 创作箴言集 - 富有文学气息的启发性标语
# 格式：(中文主标语, 英文副标语/出处)
CREATIVE_QUOTES = [
    # ========== 原创箴言 ==========
    ("落笔成章，灵感无疆", "Let words flow, let imagination soar"),
    ("一念成世界，字里藏山河", "A thought becomes a world"),
    ("以墨为舟，载梦远航", "Sail your dreams with ink"),
    ("每个故事，都值得被讲述", "Every story deserves to be told"),
    ("笔墨之间，万千世界", "Infinite worlds between the lines"),
    ("让灵感落地，让想象生长", "Ground your inspiration, grow your vision"),
    ("文字有灵，故事不朽", "Words have soul, stories live forever"),

    # ========== 中国古典诗词 ==========
    ("文章千古事，得失寸心知", "— 杜甫《偶题》"),
    ("文章本天成，妙手偶得之", "— 陆游《文章》"),
    ("看似寻常最奇崛，成如容易却艰辛", "— 王安石"),
    ("我手写我口，古岂能拘牵", "— 黄遵宪《杂感》"),
    ("须教自我胸中出，切忌随人脚后行", "— 戴复古《论诗》"),
    ("天籁自鸣天趣足，好诗不过近人情", "— 张问陶"),
    ("山重水复疑无路，柳暗花明又一村", "— 陆游《游山西村》"),
    ("落红不是无情物，化作春泥更护花", "— 龚自珍《己亥杂诗》"),

    # ========== 中国现当代作家 ==========
    ("有一分热，发一分光", "— 鲁迅"),
    ("我之所以写作，不是我有才华，而是我有感情", "— 巴金"),
    ("世事犹如书籍，一页页被翻过去", "— 莫言"),
    ("文学最大的用处，也许就是它没有用处", "— 莫言"),

    # ========== 西方文学名言 ==========
    ("心中若有未讲的故事，便是最大的痛苦", "There is no greater agony than bearing an untold story — Maya Angelou"),
    ("想读却还未被写出的书，你必须亲自去写", "If there's a book you want to read but hasn't been written yet, write it — Toni Morrison"),
    ("初稿不过是你讲给自己听的故事", "The first draft is just you telling yourself the story — Terry Pratchett"),
    ("一个词接着一个词，便是力量", "A word after a word after a word is power — Margaret Atwood"),
    ("故事是我们除了食物与栖身之外最需要的东西", "After nourishment and shelter, stories are what we need most — Philip Pullman"),
    ("小说是一种谎言，却能道出真实", "Fiction is a lie that tells us true things — Neil Gaiman"),
    ("童话不只告诉我们恶龙存在，更告诉我们恶龙可以被打败", "Fairy tales tell us dragons can be beaten — Neil Gaiman"),
    ("故事不是被创造的，而是被发现的", "Stories are found things — Stephen King"),
    ("好作家与常人的区别：每天走过千种故事，作家能看见其中五六种", "Good writers see five or six story ideas where others see none — Orson Scott Card"),
    ("信任你的梦，信任你的心，信任你的故事", "Trust dreams. Trust your heart. Trust your story — Neil Gaiman"),

    # ========== 关于想象力与创造 ==========
    ("想象力比知识更重要", "Imagination is more important than knowledge — Einstein"),
    ("精神的浩瀚、想象的活跃、心灵的勤奋：这便是天才", "— 狄德罗"),
    ("世界对于有想象力的人来说，只是一块画布", "The world is but a canvas to imagination — Thoreau"),
    ("只要我们能梦想，我们就能实现", "If we can dream it, we can do it"),
]


def get_title_sort_key(title: str) -> str:
    """
    获取标题的排序键（用于首字母分组）

    规则：
    - 英文字母开头：返回大写字母（A-Z）
    - 数字开头：返回 "#"
    - 中文或其他字符：返回该字符本身
    """
    if not title:
        return "#"
    first_char = title[0].upper()
    if first_char.isascii() and first_char.isalpha():
        return first_char
    elif first_char.isdigit():
        return "#"
    else:
        # 中文或其他字符，返回字符本身作为分组键
        return first_char
