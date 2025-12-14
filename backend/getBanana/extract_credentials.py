"""
Gemini Business 凭据提取工具

从已登录的浏览器中提取凭据并保存到 config.json。

使用方法：
1. 确保已安装依赖: pip install playwright
2. 安装浏览器: playwright install chromium
3. 运行脚本: python extract_credentials.py

选项：
  --no-save    不保存登录状态（每次都需要重新登录）
  --clear      清除已保存的登录状态
  --replace    替换而不是添加账号（默认是添加新账号）
  --note NAME  账号备注名称
  --auto       自动模式：检测过期账号并自动刷新（无需手动操作）
  --refresh-all  强制刷新所有账号
  --headless   无头模式运行（不显示浏览器窗口）
  --check      仅检查账号状态，不进行刷新

脚本会打开一个浏览器窗口，你需要：
1. 登录 Google 账号（如果还没登录）
2. 进入 business.gemini.google 的聊天页面
3. 脚本会自动提取所需的值并更新 config.json

自动刷新模式：
  如果浏览器会话仍然有效（保存在 .browser_data 中），
  脚本可以在不需要手动登录的情况下自动刷新Cookie。

  python extract_credentials.py --auto           # 自动刷新过期账号
  python extract_credentials.py --refresh-all   # 强制刷新所有账号
  python extract_credentials.py --check          # 仅检查状态
"""

import asyncio
import re
import os
import sys
import json
import shutil
import time
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from datetime import datetime

# 配置文件路径
CONFIG_FILE = Path(__file__).parent / "config.json"


def parse_args():
    """解析命令行参数"""
    args = {
        "save_session": True,
        "clear_session": False,
        "replace_mode": False,
        "note": "",
        "auto_mode": False,
        "refresh_all": False,
        "headless": False,
        "check_only": False,
    }

    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg in ("--no-save", "-n"):
            args["save_session"] = False
        elif arg in ("--clear", "-c"):
            args["clear_session"] = True
        elif arg in ("--replace", "-r"):
            args["replace_mode"] = True
        elif arg in ("--auto", "-a"):
            args["auto_mode"] = True
        elif arg in ("--refresh-all",):
            args["refresh_all"] = True
        elif arg in ("--headless", "-H"):
            args["headless"] = True
        elif arg in ("--check",):
            args["check_only"] = True
        elif arg in ("--note",) and i + 1 < len(sys.argv):
            i += 1
            args["note"] = sys.argv[i]
        elif arg in ("--help", "-h"):
            print(__doc__)
            print("选项:")
            print("  --no-save, -n     不保存登录状态（使用临时浏览器）")
            print("  --clear, -c       清除已保存的登录状态后再运行")
            print("  --replace, -r     替换现有账号（默认是添加新账号）")
            print("  --note NAME       账号备注名称")
            print("  --auto, -a        自动模式：检测过期账号并自动刷新")
            print("  --refresh-all     强制刷新所有账号")
            print("  --headless, -H    无头模式运行（不显示浏览器窗口）")
            print("  --check           仅检查账号状态，不进行刷新")
            print("  --help, -h        显示此帮助信息")
            sys.exit(0)
        i += 1

    return args


def load_config():
    """加载现有配置"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    # 默认配置
    return {
        "host": "127.0.0.1",
        "port": 8000,
        "proxy": "http://127.0.0.1:7897",
        "admin_password": "admin123",
        "admin_secret_key": "",
        "api_tokens": ["88888888"],
        "cooldown": {
            "auth_error_seconds": 900,
            "rate_limit_seconds": 300,
            "generic_error_seconds": 120
        },
        "models": [
            {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash", "owned_by": "google"},
            {"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro", "owned_by": "google"},
            {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash", "owned_by": "google"}
        ],
        "accounts": []
    }


def save_config(config):
    """保存配置"""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def find_account_by_csesidx(config, csesidx):
    """根据 csesidx 查找账号索引"""
    for i, acc in enumerate(config.get("accounts", [])):
        if acc.get("csesidx") == csesidx:
            return i
    return -1


async def check_session_valid(context, allow_login: bool = False, headless: bool = False) -> bool:
    """
    检查浏览器会话是否仍然有效（不需要重新登录）

    Args:
        context: Playwright browser context
        allow_login: 如果会话无效，是否等待用户手动登录
        headless: 是否无头模式

    Returns:
        True 如果会话有效或用户成功登录，False 否则
    """
    page = await context.new_page()
    try:
        # 访问 Gemini Business 首页
        await page.goto("https://business.gemini.google/", wait_until="networkidle", timeout=30000)
        await asyncio.sleep(2)

        current_url = page.url

        # 如果跳转到登录页面，说明会话无效
        if "accounts.google.com" in current_url or "signin" in current_url.lower():
            if allow_login and not headless:
                print("\n[!] 浏览器会话已过期，需要重新登录")
                print("请在浏览器中完成 Google 登录...")
                print("提示: 登录后请进入 Gemini Business 页面")
                print("-" * 60)

                # 等待用户登录，最多5分钟
                for i in range(300):
                    await asyncio.sleep(1)
                    current_url = page.url

                    if "business.gemini.google" in current_url:
                        print(f"\n登录成功! (第 {i+1} 秒)")
                        return True

                    if i > 0 and i % 30 == 0:
                        print(f"等待登录中... ({i} 秒)")

                print("\n[!] 登录超时（5分钟）")
                return False
            else:
                return False

        # 如果能访问到 business.gemini.google，说明会话有效
        if "business.gemini.google" in current_url:
            return True

        return False
    except Exception as e:
        print(f"[DEBUG] 检查会话时出错: {e}")
        return False
    finally:
        await page.close()


async def auto_refresh_credentials(context, account: dict, proxy: str = None, headless: bool = False) -> dict:
    """
    自动刷新单个账号的凭据

    Args:
        context: Playwright browser context
        account: 账号配置字典
        proxy: 代理地址（用于验证凭据）
        headless: 是否无头模式

    Returns:
        更新后的凭据字典，失败返回 None
    """
    page = await context.new_page()
    credentials = {}

    try:
        team_id = account.get("team_id", "")
        csesidx = account.get("csesidx", "")

        if not team_id:
            print(f"  [!] 账号缺少 team_id，跳过")
            return None

        # 构造目标URL - 直接访问聊天页面
        target_url = f"https://business.gemini.google/home/cid/{team_id}"
        if csesidx:
            target_url += f"?csesidx={csesidx}"

        print(f"  正在访问: {target_url[:60]}...")
        await page.goto(target_url, wait_until="networkidle", timeout=60000)

        # 等待页面完全加载
        await asyncio.sleep(3)

        current_url = page.url

        # 检查是否需要登录
        if "accounts.google.com" in current_url or "signin" in current_url.lower():
            print(f"  [!] 需要重新登录 Google 账号")
            if headless:
                print(f"  [!] 无头模式下无法手动登录，请先使用交互模式登录一次")
                return None

            # 等待用户手动登录
            print(f"  请在浏览器中完成登录...")
            for _ in range(180):  # 最多等待3分钟
                await asyncio.sleep(1)
                current_url = page.url
                if "business.gemini.google" in current_url:
                    break
            else:
                print(f"  [!] 登录超时")
                return None

        # 等待页面完全加载并可能发生重定向
        await asyncio.sleep(2)
        current_url = page.url

        # 提取凭据
        if "business.gemini.google" in current_url:
            # 提取 CONFIG_ID (team_id)
            cid_match = re.search(r'/cid/([^/?#]+)', current_url)
            if cid_match:
                credentials["team_id"] = cid_match.group(1)
            else:
                credentials["team_id"] = team_id  # 保持原有的

            # 提取 CSESIDX
            parsed = urlparse(current_url)
            params = parse_qs(parsed.query)
            if "csesidx" in params:
                credentials["csesidx"] = params["csesidx"][0]
            else:
                credentials["csesidx"] = csesidx  # 保持原有的

            # 提取 Cookies - 这是最重要的部分
            cookies = await context.cookies("https://business.gemini.google")
            for cookie in cookies:
                if cookie["name"] == "__Secure-C_SES":
                    credentials["secure_c_ses"] = cookie["value"]
                elif cookie["name"] == "__Host-C_OSES":
                    credentials["host_c_oses"] = cookie["value"]

            # 验证是否获取到必需的 cookie
            if credentials.get("secure_c_ses"):
                credentials["refresh_time"] = datetime.now().isoformat()

                # 验证凭据是否真正有效
                print(f"  正在验证凭据...")
                test_account = {
                    "secure_c_ses": credentials["secure_c_ses"],
                    "host_c_oses": credentials.get("host_c_oses", ""),
                    "csesidx": credentials["csesidx"],
                    "user_agent": account.get("user_agent", "Mozilla/5.0"),
                }
                is_valid, error_msg = await verify_single_account(test_account, proxy, silent=True)

                if is_valid:
                    print(f"  凭据验证通过")
                    return credentials
                else:
                    print(f"  [!] 凭据验证失败: {error_msg}")
                    print(f"  [!] 可能需要清除浏览器数据重新登录")
                    return None
            else:
                print(f"  [!] 未能获取 secure_c_ses cookie")
                return None
        else:
            print(f"  [!] 未能访问 Gemini Business 页面")
            return None

    except Exception as e:
        print(f"  [!] 刷新凭据时出错: {e}")
        return None
    finally:
        await page.close()


async def verify_single_account(account: dict, proxy: str = None, silent: bool = False) -> tuple:
    """
    验证单个账号的凭据是否有效

    Args:
        account: 账号配置字典
        proxy: 代理地址
        silent: 是否静默模式（不打印信息）

    Returns:
        (is_valid: bool, error_message: str)
    """
    import httpx

    secure_c_ses = account.get("secure_c_ses", "")
    host_c_oses = account.get("host_c_oses", "")
    csesidx = account.get("csesidx", "")

    if not secure_c_ses or not csesidx:
        return False, "缺少必要凭据 (secure_c_ses 或 csesidx)"

    try:
        # 请求 getoxsrf 来验证 Cookie
        url = f"https://business.gemini.google/auth/getoxsrf?csesidx={csesidx}"
        headers = {
            "accept": "*/*",
            "user-agent": account.get("user_agent", "Mozilla/5.0"),
            "cookie": f"__Secure-C_SES={secure_c_ses}; __Host-C_OSES={host_c_oses}",
        }

        async with httpx.AsyncClient(
            proxy=proxy,
            verify=False,
            timeout=30.0
        ) as client:
            resp = await client.get(url, headers=headers)

            if resp.status_code == 200:
                # 检查响应内容
                text = resp.text
                if text.startswith(")]}'"):
                    text = text[4:].strip()

                try:
                    data = json.loads(text)
                    if data.get("keyId") and data.get("xsrfToken"):
                        return True, ""
                    else:
                        return False, "响应中缺少 keyId 或 xsrfToken"
                except json.JSONDecodeError:
                    return False, "无法解析响应 JSON"
            elif resp.status_code == 401:
                return False, "认证失败 (401) - Cookie 已过期"
            elif resp.status_code == 403:
                return False, "访问被拒绝 (403) - 可能需要重新登录"
            else:
                return False, f"HTTP 错误 ({resp.status_code})"

    except httpx.TimeoutException:
        return False, "请求超时 - 检查网络或代理设置"
    except httpx.ProxyError as e:
        return False, f"代理错误 - {e}"
    except Exception as e:
        return False, f"验证失败: {e}"


async def check_account_validity(config: dict, proxy: str = None) -> list:
    """
    检查所有账号的有效性

    Returns:
        无效账号的索引列表
    """
    invalid_accounts = []
    accounts = config.get("accounts", [])

    print("\n检查账号有效性...")
    print("-" * 60)

    for i, acc in enumerate(accounts):
        note = acc.get("note", f"账号{i}")

        is_valid, error_msg = await verify_single_account(acc, proxy)

        if is_valid:
            print(f"  [{i}] {note}: 有效")
        else:
            print(f"  [{i}] {note}: 无效 - {error_msg}")
            invalid_accounts.append(i)

    return invalid_accounts


async def manual_refresh_single_account(context, account: dict, proxy: str = None) -> dict:
    """
    手动刷新单个账号的凭据（等待用户操作）

    Args:
        context: Playwright browser context
        account: 账号配置字典
        proxy: 代理地址

    Returns:
        更新后的凭据字典，失败返回 None
    """
    page = await context.new_page()
    credentials = {}

    try:
        team_id = account.get("team_id", "")
        csesidx = account.get("csesidx", "")

        if not team_id:
            print(f"  [!] 账号缺少 team_id，跳过")
            return None

        # 构造目标URL
        target_url = f"https://business.gemini.google/home/cid/{team_id}"
        if csesidx:
            target_url += f"?csesidx={csesidx}"

        print(f"  正在访问: {target_url[:60]}...")
        await page.goto(target_url, wait_until="networkidle", timeout=60000)

        # 等待用户操作
        print(f"  请在浏览器中完成以下操作:")
        print(f"    1. 如果需要登录，请完成 Google 登录")
        print(f"    2. 确保进入了 Gemini Business 聊天页面")
        print(f"  [重要] 请确保登录的是与此账号配置相同的 Google 账号!")
        print(f"  等待中... (最多3分钟)")

        # 等待用户操作，最多3分钟
        for i in range(180):
            await asyncio.sleep(1)
            current_url = page.url

            # 检查是否进入了正确的页面
            if "business.gemini.google" in current_url and "/cid/" in current_url:
                # 提取凭据
                cid_match = re.search(r'/cid/([^/?#]+)', current_url)
                if cid_match:
                    credentials["team_id"] = cid_match.group(1)
                else:
                    credentials["team_id"] = team_id

                parsed = urlparse(current_url)
                params = parse_qs(parsed.query)
                if "csesidx" in params:
                    credentials["csesidx"] = params["csesidx"][0]
                else:
                    credentials["csesidx"] = csesidx

                # 检查是否登录了不同的账号
                if credentials["csesidx"] != csesidx:
                    print(f"\n  [!] 警告: 检测到不同的账号!")
                    print(f"      原 csesidx: {csesidx[:20]}...")
                    print(f"      新 csesidx: {credentials['csesidx'][:20]}...")
                    print(f"  [!] 你可能登录了不同的 Google 账号")

                    try:
                        response = input("  是否用新账号替换原账号配置? (y/N): ").strip().lower()
                        if response != 'y':
                            print("  已取消，请用正确的账号重新登录")
                            return None
                        print("  将使用新账号的凭据...")
                    except EOFError:
                        return None

                # 提取 Cookies
                cookies = await context.cookies("https://business.gemini.google")
                for cookie in cookies:
                    if cookie["name"] == "__Secure-C_SES":
                        credentials["secure_c_ses"] = cookie["value"]
                    elif cookie["name"] == "__Host-C_OSES":
                        credentials["host_c_oses"] = cookie["value"]

                if credentials.get("secure_c_ses"):
                    # 验证凭据
                    print(f"  正在验证凭据...")
                    test_account = {
                        "secure_c_ses": credentials["secure_c_ses"],
                        "host_c_oses": credentials.get("host_c_oses", ""),
                        "csesidx": credentials["csesidx"],
                        "user_agent": account.get("user_agent", "Mozilla/5.0"),
                    }
                    is_valid, error_msg = await verify_single_account(test_account, proxy, silent=True)

                    if is_valid:
                        credentials["refresh_time"] = datetime.now().isoformat()
                        print(f"  凭据验证通过")
                        return credentials
                    else:
                        print(f"  [!] 凭据验证失败: {error_msg}")
                        # 继续等待，可能用户需要重新登录

            if i > 0 and i % 30 == 0:
                print(f"  等待中... ({i} 秒)")

        print(f"  [!] 等待超时")
        return None

    except Exception as e:
        print(f"  [!] 手动刷新时出错: {e}")
        return None
    finally:
        await page.close()


async def auto_mode(args: dict):
    """自动模式：检测并刷新过期账号"""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("请先安装 playwright: pip install playwright")
        print("然后安装浏览器: playwright install chromium")
        return

    config = load_config()
    accounts = config.get("accounts", [])

    if not accounts:
        print("配置中没有账号，请先手动添加账号")
        print("  python extract_credentials.py")
        return

    print("=" * 60)
    print("Gemini Business 凭据自动刷新工具")
    print(f"配置文件: {CONFIG_FILE}")
    print(f"账号总数: {len(accounts)}")
    print("=" * 60)

    # 首先检查哪些账号需要刷新
    proxy = config.get("proxy")

    if args["check_only"]:
        # 仅检查模式
        invalid = await check_account_validity(config, proxy)
        print("\n" + "=" * 60)
        if invalid:
            print(f"发现 {len(invalid)} 个无效账号: {invalid}")
            print("运行以下命令刷新这些账号:")
            print("  python extract_credentials.py --auto")
        else:
            print("所有账号均有效")
        return

    if args["refresh_all"]:
        # 强制刷新所有账号
        accounts_to_refresh = list(range(len(accounts)))
        print(f"\n强制刷新所有 {len(accounts_to_refresh)} 个账号")
    else:
        # 只刷新无效账号
        accounts_to_refresh = await check_account_validity(config, proxy)
        if not accounts_to_refresh:
            print("\n所有账号均有效，无需刷新")
            return
        print(f"\n需要刷新 {len(accounts_to_refresh)} 个账号: {accounts_to_refresh}")

    print("-" * 60)

    # 使用持久化浏览器上下文
    user_data_dir = os.path.join(os.path.dirname(__file__), ".browser_data")

    async with async_playwright() as p:
        print(f"\n浏览器数据目录: {user_data_dir}")

        context = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=args["headless"],
            viewport={"width": 1280, "height": 800},
            args=["--disable-blink-features=AutomationControlled"]
        )

        # 检查浏览器会话是否有效，如果无效且非 headless 则等待用户登录
        session_valid = await check_session_valid(
            context,
            allow_login=not args["headless"],
            headless=args["headless"]
        )

        if not session_valid:
            if args["headless"]:
                print("\n[!] 浏览器会话已过期，无头模式下无法手动登录")
                print("[!] 请先运行交互模式登录: python extract_credentials.py")
                await context.close()
                return
            else:
                print("\n[!] 无法完成登录，请重试")
                await context.close()
                return

        print("浏览器会话有效，可以自动刷新")

        # 逐个刷新账号
        refreshed_count = 0
        failed_count = 0
        failed_accounts = []  # 记录失败的账号索引

        for idx in accounts_to_refresh:
            acc = accounts[idx]
            note = acc.get("note", f"账号{idx}")
            print(f"\n正在刷新 [{idx}] {note}...")

            new_credentials = await auto_refresh_credentials(context, acc, proxy, args["headless"])

            if new_credentials:
                # 更新账号凭据
                acc["secure_c_ses"] = new_credentials.get("secure_c_ses", acc.get("secure_c_ses", ""))
                acc["host_c_oses"] = new_credentials.get("host_c_oses", acc.get("host_c_oses", ""))
                acc["refresh_time"] = new_credentials.get("refresh_time", "")
                acc["available"] = True

                # 清除之前的错误状态
                acc.pop("unavailable_reason", None)
                acc.pop("cooldown_until", None)

                print(f"  [OK] 刷新成功")
                refreshed_count += 1
            else:
                print(f"  [FAIL] 刷新失败")
                failed_count += 1
                failed_accounts.append(idx)

            # 短暂延迟避免请求过快
            await asyncio.sleep(1)

        # 如果有失败的账号且非 headless 模式，提示用户手动登录重试
        if failed_accounts and not args["headless"]:
            print("\n" + "-" * 60)
            print(f"有 {len(failed_accounts)} 个账号刷新失败")
            try:
                response = input("是否尝试手动登录来刷新这些账号? (Y/n): ").strip().lower()
                if response != 'n':
                    print("\n开始手动刷新失败的账号...")

                    for idx in failed_accounts:
                        acc = accounts[idx]
                        note = acc.get("note", f"账号{idx}")
                        print(f"\n正在手动刷新 [{idx}] {note}...")
                        print("请在浏览器中操作，确保已登录并进入正确的页面")

                        # 手动模式刷新，允许等待用户登录
                        new_credentials = await manual_refresh_single_account(
                            context, acc, proxy
                        )

                        if new_credentials:
                            acc["secure_c_ses"] = new_credentials.get("secure_c_ses", acc.get("secure_c_ses", ""))
                            acc["host_c_oses"] = new_credentials.get("host_c_oses", acc.get("host_c_oses", ""))
                            acc["refresh_time"] = new_credentials.get("refresh_time", "")
                            acc["available"] = True
                            acc.pop("unavailable_reason", None)
                            acc.pop("cooldown_until", None)

                            print(f"  [OK] 手动刷新成功")
                            refreshed_count += 1
                            failed_count -= 1
                        else:
                            print(f"  [FAIL] 手动刷新也失败了")

                        await asyncio.sleep(1)
            except EOFError:
                pass

        await context.close()

    # 保存更新后的配置
    save_config(config)

    print("\n" + "=" * 60)
    print(f"刷新完成！成功: {refreshed_count}, 失败: {failed_count}")
    print(f"配置已保存到: {CONFIG_FILE}")
    print("=" * 60)


async def extract_credentials():
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("请先安装 playwright: pip install playwright")
        print("然后安装浏览器: playwright install chromium")
        return

    args = parse_args()

    # 自动模式或检查模式
    if args["auto_mode"] or args["refresh_all"] or args["check_only"]:
        await auto_mode(args)
        return

    user_data_dir = os.path.join(os.path.dirname(__file__), ".browser_data")

    # 清除登录状态
    if args["clear_session"] and os.path.exists(user_data_dir):
        print(f"正在清除已保存的登录状态: {user_data_dir}")
        shutil.rmtree(user_data_dir)
        print("已清除\n")

    print("=" * 60)
    print("Gemini Business 凭据提取工具")
    print(f"配置文件: {CONFIG_FILE}")
    print("=" * 60)

    async with async_playwright() as p:
        if args["save_session"]:
            print(f"\n浏览器数据目录: {user_data_dir}")
            print("登录状态会被保存，下次运行可自动使用\n")

            context = await p.chromium.launch_persistent_context(
                user_data_dir,
                headless=args["headless"],
                viewport={"width": 1280, "height": 800},
                args=["--disable-blink-features=AutomationControlled"]
            )
        else:
            print("\n使用临时浏览器（登录状态不会保存）\n")

            browser = await p.chromium.launch(
                headless=args["headless"],
                args=["--disable-blink-features=AutomationControlled"]
            )
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800}
            )

        page = await context.new_page()

        print("正在打开 Gemini Business...")
        print("-" * 60)

        await page.goto("https://business.gemini.google/")

        print("\n请操作浏览器：")
        print("1. 如果需要登录，请完成 Google 登录")
        print("2. 进入任意一个 Gemini 聊天会话")
        print("3. 确保 URL 类似: https://business.gemini.google/home/cid/xxx/r/session/xxx?csesidx=xxx")
        print("\n等待你进入聊天页面...")
        print("-" * 60)

        credentials = {}
        max_wait = 300  # 最多等待 5 分钟

        for i in range(max_wait):
            await asyncio.sleep(1)

            try:
                current_url = page.url

                if "business.gemini.google" in current_url and "/cid/" in current_url:
                    # 提取 CONFIG_ID (team_id)
                    cid_match = re.search(r'/cid/([^/?#]+)', current_url)
                    if cid_match:
                        credentials["team_id"] = cid_match.group(1)

                    # 提取 CSESIDX
                    parsed = urlparse(current_url)
                    params = parse_qs(parsed.query)
                    if "csesidx" in params:
                        credentials["csesidx"] = params["csesidx"][0]

                    # 提取 Cookies
                    cookies = await context.cookies("https://business.gemini.google")
                    for cookie in cookies:
                        if cookie["name"] == "__Secure-C_SES":
                            credentials["secure_c_ses"] = cookie["value"]
                        elif cookie["name"] == "__Host-C_OSES":
                            credentials["host_c_oses"] = cookie["value"]

                    # 检查是否获取到所有必需的值
                    required = ["secure_c_ses", "csesidx", "team_id"]
                    if all(k in credentials for k in required):
                        print(f"\n已检测到有效的配置！ (第 {i+1} 秒)")
                        break

                if i > 0 and i % 10 == 0:
                    print(f"等待中... ({i} 秒) 当前URL: {current_url[:80]}...")

            except Exception as e:
                pass

        await context.close()

        # 检查结果
        if not credentials.get("secure_c_ses"):
            print("\n错误: 未能获取 secure_c_ses cookie")
            print("请确保已登录 Google 账号并进入 Gemini Business 聊天页面")
            return

        if not credentials.get("csesidx"):
            print("\n错误: 未能获取 csesidx")
            print("请确保 URL 中包含 csesidx 参数")
            return

        if not credentials.get("team_id"):
            print("\n错误: 未能获取 team_id")
            print("请确保进入了聊天会话页面")
            return

        # 打印提取到的值
        print("\n" + "=" * 60)
        print("提取到的配置值:")
        print("=" * 60)

        for key, value in credentials.items():
            display_value = value[:50] + "..." if len(value) > 50 else value
            print(f"{key}={display_value}")

        # 加载现有配置
        config = load_config()
        proxy = config.get("proxy")

        # 构建账号对象
        new_account = {
            "team_id": credentials["team_id"],
            "csesidx": credentials["csesidx"],
            "secure_c_ses": credentials["secure_c_ses"],
            "host_c_oses": credentials.get("host_c_oses", ""),
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "note": args["note"] or f"账号{len(config.get('accounts', [])) + 1}",
            "available": True,
            "refresh_time": datetime.now().isoformat()
        }

        # 验证凭据是否有效
        print("\n正在验证凭据...")
        is_valid, error_msg = await verify_single_account(new_account, proxy)

        if is_valid:
            print("凭据验证通过!")
        else:
            print(f"\n[!] 凭据验证失败: {error_msg}")
            print("[!] 这可能是因为:")
            print("    1. Cookie 刚获取还未生效，请稍后重试")
            print("    2. 需要清除浏览器数据重新登录")
            print("    3. 网络或代理问题")

            # 询问用户是否仍然保存
            try:
                response = input("\n是否仍然保存这些凭据? (y/N): ").strip().lower()
                if response != 'y':
                    print("已取消保存")
                    return
                print("继续保存凭据（可能无法正常使用）...")
            except EOFError:
                print("已取消保存")
                return

        # 检查是否已存在相同 csesidx 的账号
        existing_idx = find_account_by_csesidx(config, credentials["csesidx"])

        if existing_idx >= 0:
            # 更新现有账号
            print(f"\n发现已存在的账号 (索引: {existing_idx})，正在更新...")
            old_note = config["accounts"][existing_idx].get("note", "")
            new_account["note"] = old_note or new_account["note"]
            config["accounts"][existing_idx] = new_account
            action = "更新"
        elif args["replace_mode"] and config.get("accounts"):
            # 替换模式：替换第一个账号
            print("\n替换模式：正在替换第一个账号...")
            config["accounts"][0] = new_account
            action = "替换"
        else:
            # 添加新账号
            if "accounts" not in config:
                config["accounts"] = []
            config["accounts"].append(new_account)
            action = "添加"

        # 保存配置
        save_config(config)

        print("\n" + "=" * 60)
        print(f"账号已{action}到配置文件: {CONFIG_FILE}")
        print(f"当前账号总数: {len(config['accounts'])}")
        print("=" * 60)

        # 显示所有账号
        print("\n当前账号列表:")
        for i, acc in enumerate(config["accounts"]):
            note = acc.get("note", "")
            team_id = acc.get("team_id", "")[:8] + "..."
            print(f"  [{i}] {note} (team_id: {team_id})")

        print("\n现在可以启动服务器了:")
        print("  python run.py")
        print("\n或使用 GUI 客户端:")
        print("  python gui.py")

        print("\n自动刷新凭据（无需手动登录）:")
        print("  python extract_credentials.py --auto        # 自动刷新过期账号")
        print("  python extract_credentials.py --refresh-all # 强制刷新所有账号")
        print("  python extract_credentials.py --check       # 仅检查账号状态")


def main():
    asyncio.run(extract_credentials())


if __name__ == "__main__":
    main()
