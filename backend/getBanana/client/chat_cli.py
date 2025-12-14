"""
增强版交互式命令行客户端

功能：
- 加载并显示所有本地会话记录
- 交互式选择会话继续对话
- 显示会话历史消息
- 支持创建新会话
- 支持流式输出
- 支持模型切换
"""
import sys
import os
import json
import argparse
import textwrap
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

import httpx


# 颜色代码
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    BG_BLUE = "\033[44m"
    BG_GREEN = "\033[42m"


def colorize(text: str, *codes: str) -> str:
    """添加颜色代码"""
    return "".join(codes) + text + Colors.RESET


class ConversationData:
    """会话数据结构"""

    def __init__(self, data: dict, filepath: Path):
        self.id = data.get("id", "")
        self.name = data.get("name", "")
        self.model = data.get("model", "gemini-2.5-flash")
        self.messages = data.get("messages", [])
        self.binding = data.get("binding", {})
        self.created_at = data.get("created_at", 0)
        self.updated_at = data.get("updated_at", 0)
        self.filepath = filepath
        self._raw_data = data

    @property
    def display_name(self) -> str:
        """获取显示名称（优先使用第一条用户消息）"""
        # 如果已有自定义名称且不是默认值
        if self.name and self.name != self.id and not self.name.startswith("conv_"):
            if len(self.name) > 30:
                return self.name[:30] + "..."
            return self.name

        # 尝试从第一条用户消息生成名称
        for msg in self.messages:
            if msg.get("role") == "user":
                content = msg.get("content", "").strip()
                if content:
                    if len(content) > 30:
                        return content[:30] + "..."
                    return content

        # 回退到 ID 的缩写
        return self.id[:20] + "..."

    @property
    def message_count(self) -> int:
        return len(self.messages)

    @property
    def last_message(self) -> Optional[dict]:
        if self.messages:
            return self.messages[-1]
        return None

    @property
    def created_time(self) -> str:
        if self.created_at:
            return datetime.fromtimestamp(self.created_at).strftime("%Y-%m-%d %H:%M")
        return "未知"

    @property
    def updated_time(self) -> str:
        if self.updated_at:
            return datetime.fromtimestamp(self.updated_at).strftime("%Y-%m-%d %H:%M")
        return "未知"

    def get_preview(self, max_len: int = 50) -> str:
        """获取最后一条消息的预览"""
        if not self.last_message:
            return "(空会话)"

        content = self.last_message.get("content", "")
        role = self.last_message.get("role", "")

        # 清理内容
        content = content.replace("\n", " ").strip()
        if len(content) > max_len:
            content = content[:max_len] + "..."

        prefix = "You: " if role == "user" else "AI: "
        return prefix + content

    @classmethod
    def load(cls, filepath: Path) -> Optional["ConversationData"]:
        """从文件加载会话"""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            return cls(data, filepath)
        except Exception as e:
            return None


class ChatCLI:
    """增强版聊天CLI"""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        data_dir: Path,
        proxy: Optional[str] = None
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.data_dir = data_dir
        self.conversations_dir = data_dir / "conversations"
        self.proxy = proxy

        # 状态
        self.conversations: List[ConversationData] = []
        self.current_conversation: Optional[ConversationData] = None
        self.current_model = "gemini-2.5-flash"
        self.use_stream = True
        self.available_models: List[str] = []

        # HTTP客户端
        client_kwargs = {
            "timeout": 120.0,
            "verify": False,
        }
        if proxy:
            client_kwargs["proxy"] = proxy

        self.client = httpx.Client(**client_kwargs)

    def _headers(self) -> dict:
        """获取请求头"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Client-Type": "cli"
        }

    def load_conversations(self):
        """从本地加载所有会话"""
        self.conversations = []

        if not self.conversations_dir.exists():
            return

        for conv_dir in self.conversations_dir.iterdir():
            if conv_dir.is_dir():
                json_file = conv_dir / f"{conv_dir.name}.json"
                if json_file.exists():
                    conv = ConversationData.load(json_file)
                    if conv:
                        self.conversations.append(conv)

        # 按更新时间排序（最近的在前）
        self.conversations.sort(key=lambda c: c.updated_at, reverse=True)

    def load_models(self):
        """从服务器加载可用模型列表"""
        try:
            url = f"{self.base_url}/v1/models"
            response = self.client.get(url, headers=self._headers())
            if response.status_code == 200:
                data = response.json()
                self.available_models = [m["id"] for m in data.get("data", [])]
        except Exception as e:
            self.available_models = ["gemini-2.5-flash", "gemini-2.5-pro"]

    def print_header(self):
        """打印头部"""
        print()
        print(colorize("=" * 60, Colors.CYAN))
        print(colorize("  Gemini Business API - 增强版命令行客户端", Colors.CYAN, Colors.BOLD))
        print(colorize("=" * 60, Colors.CYAN))
        print(f"  服务地址: {colorize(self.base_url, Colors.GREEN)}")
        print(f"  会话目录: {colorize(str(self.conversations_dir), Colors.DIM)}")
        print(colorize("-" * 60, Colors.DIM))
        print()

    def print_conversation_list(self):
        """打印会话列表"""
        if not self.conversations:
            print(colorize("  (没有找到任何会话)", Colors.DIM))
            print()
            return

        print(colorize(f"  找到 {len(self.conversations)} 个会话:\n", Colors.BOLD))

        for i, conv in enumerate(self.conversations):
            # 当前会话标记
            marker = colorize(" * ", Colors.GREEN, Colors.BOLD) if conv == self.current_conversation else "   "

            # 序号
            num = colorize(f"[{i + 1}]", Colors.YELLOW)

            # 名称（使用 display_name 属性）
            name = colorize(conv.display_name, Colors.BOLD)

            # 消息数
            msg_count = colorize(f"{conv.message_count} 条消息", Colors.CYAN)

            # 时间
            time_str = colorize(conv.updated_time, Colors.DIM)

            # 第一行：序号、名称、消息数
            print(f"{marker}{num} {name}")
            print(f"       {msg_count} | {time_str}")

            # 预览
            preview = conv.get_preview(60)
            print(f"       {colorize(preview, Colors.DIM)}")
            print()

    def print_history(self, conversation: ConversationData, limit: int = 10):
        """打印会话历史"""
        messages = conversation.messages

        if not messages:
            print(colorize("  (没有消息历史)", Colors.DIM))
            return

        # 显示最后 limit 条消息
        start_idx = max(0, len(messages) - limit)
        if start_idx > 0:
            print(colorize(f"  ... 还有 {start_idx} 条更早的消息 ...\n", Colors.DIM))

        for msg in messages[start_idx:]:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role == "user":
                print(colorize("You:", Colors.GREEN, Colors.BOLD))
            else:
                print(colorize("Assistant:", Colors.BLUE, Colors.BOLD))

            # 包装长文本
            lines = content.split("\n")
            for line in lines:
                if len(line) > 80:
                    wrapped = textwrap.wrap(line, width=80)
                    for w in wrapped:
                        print(f"  {w}")
                else:
                    print(f"  {line}")
            print()

    def select_conversation(self, index: int) -> bool:
        """选择会话"""
        if 1 <= index <= len(self.conversations):
            self.current_conversation = self.conversations[index - 1]
            self.current_model = self.current_conversation.model
            return True
        return False

    def chat(self, message: str) -> str:
        """发送聊天消息"""
        url = f"{self.base_url}/v1/chat/completions"

        body = {
            "model": self.current_model,
            "messages": [{"role": "user", "content": message}],
            "stream": self.use_stream
        }

        # 如果有当前会话，添加会话ID
        if self.current_conversation:
            body["conversation_id"] = self.current_conversation.id

        if self.use_stream:
            return self._stream_chat(url, body)
        else:
            return self._sync_chat(url, body)

    def _sync_chat(self, url: str, body: dict) -> str:
        """同步聊天"""
        try:
            response = self.client.post(url, headers=self._headers(), json=body)

            if response.status_code != 200:
                print(colorize(f"\n[错误] {response.status_code}: {response.text}", Colors.RED))
                return ""

            data = response.json()

            # 更新会话ID
            if "conversation_id" in data and not self.current_conversation:
                self._refresh_current_conversation(data["conversation_id"])

            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return content
        except Exception as e:
            print(colorize(f"\n[错误] {e}", Colors.RED))
            return ""

    def _stream_chat(self, url: str, body: dict) -> str:
        """流式聊天"""
        full_response = ""
        conversation_id = None

        try:
            with self.client.stream("POST", url, headers=self._headers(), json=body) as response:
                if response.status_code != 200:
                    print(colorize(f"\n[错误] {response.status_code}", Colors.RED))
                    return ""

                for line in response.iter_lines():
                    if not line:
                        continue

                    if line.startswith("data: "):
                        data_str = line[6:]

                        if data_str == "[DONE]":
                            break

                        try:
                            data = json.loads(data_str)

                            # 检查错误
                            if "error" in data:
                                print(colorize(f"\n[错误] {data['error'].get('message', '未知错误')}", Colors.RED))
                                break

                            # 获取会话ID
                            if "conversation_id" in data and not conversation_id:
                                conversation_id = data["conversation_id"]

                            # 提取内容
                            delta = data.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")

                            if content:
                                print(content, end="", flush=True)
                                full_response += content

                        except json.JSONDecodeError:
                            continue

            print()  # 换行

            # 刷新当前会话
            if conversation_id and not self.current_conversation:
                self._refresh_current_conversation(conversation_id)
            elif self.current_conversation:
                self._refresh_current_conversation(self.current_conversation.id)

            return full_response

        except Exception as e:
            print(colorize(f"\n[错误] {e}", Colors.RED))
            return ""

    def _refresh_current_conversation(self, conv_id: str):
        """刷新当前会话数据"""
        json_file = self.conversations_dir / conv_id / f"{conv_id}.json"
        if json_file.exists():
            conv = ConversationData.load(json_file)
            if conv:
                # 更新或添加到列表
                found = False
                for i, c in enumerate(self.conversations):
                    if c.id == conv_id:
                        self.conversations[i] = conv
                        found = True
                        break
                if not found:
                    self.conversations.insert(0, conv)

                self.current_conversation = conv

    def create_new_conversation(self, name: str = "") -> bool:
        """创建新会话"""
        try:
            url = f"{self.base_url}/api/conversations"
            body = {"name": name, "model": self.current_model}

            response = self.client.post(url, headers=self._headers(), json=body)

            if response.status_code == 200:
                data = response.json()
                conv_id = data.get("id")
                if conv_id:
                    # 清除当前会话，等待第一条消息后刷新
                    self.current_conversation = None
                    print(colorize(f"[新会话] {conv_id}", Colors.GREEN))
                    return True
            else:
                print(colorize(f"[错误] {response.status_code}: {response.text}", Colors.RED))
        except Exception as e:
            print(colorize(f"[错误] {e}", Colors.RED))
        return False

    def delete_conversation(self, conv_id: str) -> bool:
        """删除会话"""
        try:
            url = f"{self.base_url}/api/conversations/{conv_id}"
            response = self.client.delete(url, headers=self._headers())

            if response.status_code == 200:
                # 从本地列表移除
                self.conversations = [c for c in self.conversations if c.id != conv_id]
                if self.current_conversation and self.current_conversation.id == conv_id:
                    self.current_conversation = None
                return True
        except Exception as e:
            print(colorize(f"[错误] {e}", Colors.RED))
        return False

    def print_help(self):
        """打印帮助信息"""
        help_text = """
命令:
  /list           刷新并显示会话列表
  /select <n>     选择第 n 个会话（也可直接输入数字）
  /history [n]    显示当前会话的历史消息（默认10条）
  /new [name]     创建新会话
  /delete <id>    删除指定会话
  /model [name]   查看或切换模型
  /stream         切换流式输出开关
  /status         查看系统状态
  /clear          清屏
  /help           显示帮助
  /quit           退出

交互:
  直接输入数字选择会话
  输入消息内容发送对话
"""
        print(colorize(help_text, Colors.CYAN))

    def print_status(self):
        """打印系统状态"""
        try:
            url = f"{self.base_url}/health"
            response = self.client.get(url)

            if response.status_code == 200:
                data = response.json()
                accounts = data.get("accounts", {})

                print()
                print(colorize("系统状态:", Colors.BOLD))
                print(f"  状态: {colorize(data.get('status', 'unknown'), Colors.GREEN)}")
                print(f"  账号: {accounts.get('available', 0)}/{accounts.get('total', 0)} 可用")
                print(f"  本地会话: {len(self.conversations)} 个")
                print(f"  当前模型: {colorize(self.current_model, Colors.CYAN)}")
                print(f"  流式输出: {colorize('开启' if self.use_stream else '关闭', Colors.YELLOW)}")
                print()
        except Exception as e:
            print(colorize(f"[错误] 无法获取状态: {e}", Colors.RED))

    def run(self):
        """运行主循环"""
        self.print_header()

        # 加载会话和模型
        print("正在加载会话...")
        self.load_conversations()
        self.load_models()

        # 显示会话列表
        self.print_conversation_list()

        print(colorize("提示: 输入数字选择会话，或输入 /help 查看帮助\n", Colors.DIM))

        try:
            while True:
                # 构建提示符
                if self.current_conversation:
                    conv_name = self.current_conversation.display_name[:15]
                    prompt = f"{colorize(f'[{conv_name}]', Colors.GREEN)} You: "
                else:
                    prompt = f"{colorize('[新会话]', Colors.YELLOW)} You: "

                try:
                    user_input = input(prompt).strip()
                except EOFError:
                    break

                if not user_input:
                    continue

                # 检查是否是纯数字（选择会话）
                if user_input.isdigit():
                    index = int(user_input)
                    if self.select_conversation(index):
                        conv = self.current_conversation
                        print(colorize(f"\n已选择会话: {conv.display_name}", Colors.GREEN))
                        print(colorize(f"模型: {conv.model} | 消息数: {conv.message_count}\n", Colors.DIM))
                        self.print_history(conv, limit=5)
                    else:
                        print(colorize(f"[错误] 无效的会话编号: {index}", Colors.RED))
                    continue

                # 处理命令
                if user_input.startswith("/"):
                    parts = user_input.split(maxsplit=1)
                    cmd = parts[0].lower()
                    arg = parts[1] if len(parts) > 1 else ""

                    if cmd in ("/quit", "/exit", "/q"):
                        print("再见!")
                        break

                    elif cmd == "/help":
                        self.print_help()

                    elif cmd == "/clear":
                        os.system("cls" if os.name == "nt" else "clear")
                        self.print_header()

                    elif cmd == "/list":
                        print("正在刷新会话列表...")
                        self.load_conversations()
                        self.print_conversation_list()

                    elif cmd == "/select":
                        if arg.isdigit():
                            index = int(arg)
                            if self.select_conversation(index):
                                conv = self.current_conversation
                                print(colorize(f"\n已选择会话: {conv.display_name}", Colors.GREEN))
                                self.print_history(conv, limit=5)
                            else:
                                print(colorize(f"[错误] 无效的会话编号: {index}", Colors.RED))
                        else:
                            print(colorize("[错误] 请指定会话编号", Colors.RED))

                    elif cmd == "/history":
                        if not self.current_conversation:
                            print(colorize("[错误] 请先选择一个会话", Colors.RED))
                        else:
                            limit = int(arg) if arg.isdigit() else 10
                            print(colorize(f"\n会话历史 ({self.current_conversation.display_name}):\n", Colors.BOLD))
                            self.print_history(self.current_conversation, limit=limit)

                    elif cmd == "/new":
                        self.current_conversation = None
                        print(colorize(f"\n已切换到新会话模式，发送消息将创建新会话", Colors.GREEN))
                        if arg:
                            print(colorize(f"会话名称: {arg}", Colors.DIM))

                    elif cmd == "/delete":
                        if arg:
                            # 支持通过编号删除
                            if arg.isdigit():
                                index = int(arg)
                                if 1 <= index <= len(self.conversations):
                                    conv_id = self.conversations[index - 1].id
                                else:
                                    print(colorize(f"[错误] 无效的会话编号: {index}", Colors.RED))
                                    continue
                            else:
                                conv_id = arg

                            confirm = input(f"确认删除会话 {conv_id}? (y/N): ").strip().lower()
                            if confirm == "y":
                                if self.delete_conversation(conv_id):
                                    print(colorize(f"[已删除] {conv_id}", Colors.GREEN))
                                else:
                                    print(colorize("[错误] 删除失败", Colors.RED))
                        else:
                            print(colorize("[错误] 请指定会话ID或编号", Colors.RED))

                    elif cmd == "/model":
                        if arg:
                            if arg in self.available_models or not self.available_models:
                                self.current_model = arg
                                print(colorize(f"[模型] 已切换到: {arg}", Colors.GREEN))
                            else:
                                print(colorize(f"[错误] 未知模型: {arg}", Colors.RED))
                                print(f"可用模型: {', '.join(self.available_models)}")
                        else:
                            print(f"当前模型: {colorize(self.current_model, Colors.CYAN)}")
                            if self.available_models:
                                print(f"可用模型: {', '.join(self.available_models)}")

                    elif cmd == "/stream":
                        self.use_stream = not self.use_stream
                        status = "开启" if self.use_stream else "关闭"
                        print(colorize(f"[流式输出] {status}", Colors.GREEN))

                    elif cmd == "/status":
                        self.print_status()

                    else:
                        print(colorize(f"[未知命令] {cmd}", Colors.RED))
                        print("输入 /help 查看帮助")

                else:
                    # 发送聊天消息
                    if self.current_conversation:
                        print(colorize(f"[会话: {self.current_conversation.id[:12]}...]", Colors.DIM))
                    else:
                        print(colorize("[创建新会话...]", Colors.DIM))

                    print(colorize("Assistant: ", Colors.BLUE, Colors.BOLD), end="", flush=True)
                    self.chat(user_input)

        except KeyboardInterrupt:
            print("\n再见!")

        finally:
            self.client.close()


def main():
    parser = argparse.ArgumentParser(
        description="Gemini Business API 增强版命令行客户端",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python chat_cli.py
  python chat_cli.py --url http://localhost:8080
  python chat_cli.py --key your-api-key
  python chat_cli.py --data-dir /path/to/data
"""
    )
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8000",
        help="API服务地址 (默认: http://127.0.0.1:8000)"
    )
    parser.add_argument(
        "--key",
        default="88888888",
        help="API密钥 (默认: 88888888)"
    )
    parser.add_argument(
        "--data-dir",
        default=None,
        help="数据目录路径 (默认: 自动检测)"
    )
    parser.add_argument(
        "--proxy",
        default=None,
        help="HTTP代理地址"
    )
    parser.add_argument(
        "--no-stream",
        action="store_true",
        help="禁用流式输出"
    )

    args = parser.parse_args()

    # 确定数据目录
    if args.data_dir:
        data_dir = Path(args.data_dir)
    else:
        # 自动检测：当前目录或父目录
        current = Path(__file__).parent.parent
        data_dir = current / "data"
        if not data_dir.exists():
            data_dir = Path.cwd() / "data"

    if not data_dir.exists():
        print(f"警告: 数据目录不存在: {data_dir}")
        print("将在发送消息时创建会话")

    # 创建CLI并运行
    cli = ChatCLI(
        base_url=args.url,
        api_key=args.key,
        data_dir=data_dir,
        proxy=args.proxy
    )

    if args.no_stream:
        cli.use_stream = False

    cli.run()


if __name__ == "__main__":
    main()
