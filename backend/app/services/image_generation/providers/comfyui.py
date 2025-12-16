"""
ComfyUI图片生成供应商

支持本地或远程ComfyUI服务的图片生成。

ComfyUI API工作流程：
1. POST /prompt 提交工作流JSON
2. 轮询 /history/{prompt_id} 获取执行状态
3. 从 /view 端点获取生成的图片

配置说明：
- api_base_url: ComfyUI服务地址，如 http://127.0.0.1:8188
- api_key: 可选，如果配置了API Key认证
- extra_params: 工作流相关参数
  - workflow_template: 自定义工作流模板（JSON字符串或dict）
  - checkpoint: 模型文件名，如 "v1-5-pruned.safetensors"
  - sampler_name: 采样器名称，如 "euler", "dpmpp_2m"
  - scheduler: 调度器，如 "normal", "karras"
  - steps: 采样步数
  - cfg_scale: CFG引导强度
  - width: 图片宽度
  - height: 图片高度
  - seed: 随机种子（-1为随机）
"""

import asyncio
import base64
import json
import logging
import random
import uuid
from typing import Any, Dict, List, Optional

import httpx

from .base import BaseImageProvider, ProviderTestResult, ProviderGenerateResult
from .factory import ImageProviderFactory
from ....models.image_config import ImageGenerationConfig
from ..schemas import ImageGenerationRequest

logger = logging.getLogger(__name__)

# ComfyUI轮询配置
COMFYUI_POLL_INTERVAL = 1.0  # 轮询间隔（秒）
COMFYUI_MAX_POLL_TIME = 300.0  # 最大轮询时间（秒）


@ImageProviderFactory.register("comfyui")
class ComfyUIProvider(BaseImageProvider):
    """ComfyUI供应商"""

    PROVIDER_TYPE = "comfyui"
    DISPLAY_NAME = "ComfyUI (本地/远程)"

    # 默认工作流模板 - 基础文生图流程
    DEFAULT_WORKFLOW = {
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "cfg": 7,
                "denoise": 1,
                "latent_image": ["5", 0],
                "model": ["4", 0],
                "negative": ["7", 0],
                "positive": ["6", 0],
                "sampler_name": "euler",
                "scheduler": "normal",
                "seed": -1,
                "steps": 20
            }
        },
        "4": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {
                "ckpt_name": "v1-5-pruned.safetensors"
            }
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "batch_size": 1,
                "height": 768,
                "width": 1024
            }
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "clip": ["4", 1],
                "text": ""
            }
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "clip": ["4", 1],
                "text": ""
            }
        },
        "8": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["3", 0],
                "vae": ["4", 2]
            }
        },
        "9": {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": "AFN",
                "images": ["8", 0]
            }
        }
    }

    def _get_base_url(self, config: ImageGenerationConfig) -> str:
        """获取ComfyUI服务基础URL"""
        return (config.api_base_url or "http://127.0.0.1:8188").rstrip("/")

    def get_auth_headers(
        self,
        config: ImageGenerationConfig,
        content_type: str = "application/json",
        accept: str = "application/json",
    ) -> Dict[str, str]:
        """
        获取请求头（ComfyUI通常不需要认证）

        重写父类方法，仅在配置了api_key时添加认证头。
        """
        headers = {}
        if content_type:
            headers["Content-Type"] = content_type
        if accept:
            headers["Accept"] = accept

        # ComfyUI可选认证
        if config.api_key:
            headers["Authorization"] = f"Bearer {config.api_key}"

        return headers

    async def test_connection(self, config: ImageGenerationConfig) -> ProviderTestResult:
        """测试ComfyUI连接"""
        base_url = self._get_base_url(config)

        try:
            async with self.create_http_client(config, for_test=True) as client:
                # 获取系统信息来验证连接
                response = await client.get(
                    f"{base_url}/system_stats",
                    headers=self.get_auth_headers(config, content_type=""),
                )

                if response.status_code == 200:
                    data = response.json()
                    system_info = data.get("system", {})
                    devices = data.get("devices", [])

                    # 提取GPU信息
                    gpu_info = ""
                    if devices:
                        for device in devices:
                            name = device.get("name", "Unknown")
                            vram = device.get("vram_total", 0)
                            vram_gb = round(vram / (1024**3), 1) if vram else 0
                            gpu_info = f"{name} ({vram_gb}GB)"
                            break

                    return ProviderTestResult(
                        success=True,
                        message=f"连接成功，GPU: {gpu_info}" if gpu_info else "连接成功",
                        extra_info={
                            "system": system_info,
                            "devices": devices,
                        }
                    )
                else:
                    return ProviderTestResult(
                        success=False,
                        message=f"连接失败: HTTP {response.status_code}"
                    )

        except httpx.ConnectError:
            return ProviderTestResult(
                success=False,
                message=f"无法连接到ComfyUI服务: {base_url}"
            )
        except httpx.TimeoutException:
            return ProviderTestResult(success=False, message="连接超时")
        except Exception as e:
            return ProviderTestResult(success=False, message=f"连接错误: {str(e)}")

    async def generate(
        self,
        config: ImageGenerationConfig,
        request: ImageGenerationRequest,
    ) -> ProviderGenerateResult:
        """
        使用ComfyUI生成图片

        流程：
        1. 构建工作流
        2. 提交到队列
        3. 轮询等待完成
        4. 获取生成的图片
        """
        try:
            urls = await self._generate_images(config, request)
            return ProviderGenerateResult(success=True, image_urls=urls)
        except asyncio.TimeoutError:
            logger.error("ComfyUI生成超时")
            return ProviderGenerateResult(
                success=False,
                error_message=f"生成超时（超过{COMFYUI_MAX_POLL_TIME}秒）"
            )
        except Exception as e:
            error_msg = str(e) if str(e) else f"{type(e).__name__}"
            logger.error("ComfyUI生成失败: %s", error_msg, exc_info=True)
            return ProviderGenerateResult(success=False, error_message=error_msg)

    async def _generate_images(
        self,
        config: ImageGenerationConfig,
        request: ImageGenerationRequest,
    ) -> List[str]:
        """执行图片生成流程"""
        base_url = self._get_base_url(config)
        extra_params = config.extra_params or {}

        # 构建工作流
        workflow = self._build_workflow(config, request)

        # 生成客户端ID（用于追踪任务）
        client_id = str(uuid.uuid4())

        async with self.create_http_client(config) as client:
            # 1. 提交工作流到队列
            prompt_id = await self._queue_prompt(
                client, base_url, workflow, client_id, config
            )
            logger.info("ComfyUI任务已提交: prompt_id=%s", prompt_id)

            # 2. 轮询等待完成
            outputs = await self._poll_for_completion(
                client, base_url, prompt_id, config
            )
            logger.info("ComfyUI任务完成: prompt_id=%s", prompt_id)

            # 3. 获取生成的图片
            image_urls = await self._fetch_images(
                client, base_url, outputs, config
            )

            return image_urls

    def _build_workflow(
        self,
        config: ImageGenerationConfig,
        request: ImageGenerationRequest,
    ) -> Dict[str, Any]:
        """
        构建ComfyUI工作流

        支持自定义工作流模板，或使用默认的基础文生图流程。
        """
        extra_params = config.extra_params or {}

        # 检查是否有自定义工作流模板
        custom_workflow = extra_params.get("workflow_template")
        if custom_workflow:
            if isinstance(custom_workflow, str):
                try:
                    workflow = json.loads(custom_workflow)
                except json.JSONDecodeError:
                    logger.warning("自定义工作流模板解析失败，使用默认模板")
                    workflow = self._get_default_workflow()
            else:
                workflow = custom_workflow.copy()
        else:
            workflow = self._get_default_workflow()

        # 构建提示词
        prompt = self.build_prompt(request, add_context=False)
        negative_prompt = request.negative_prompt or "low quality, blurry, distorted"

        # 获取参数
        seed = request.seed if request.seed is not None else random.randint(0, 2**32 - 1)
        steps = extra_params.get("steps", 20)
        cfg_scale = extra_params.get("cfg_scale", 7)
        sampler_name = extra_params.get("sampler_name", "euler")
        scheduler = extra_params.get("scheduler", "normal")
        checkpoint = extra_params.get("checkpoint", "v1-5-pruned.safetensors")

        # 确定图片尺寸
        width, height = self._get_dimensions(request, extra_params)

        # 更新工作流参数
        workflow = self._update_workflow_params(
            workflow,
            prompt=prompt,
            negative_prompt=negative_prompt,
            seed=seed,
            steps=steps,
            cfg_scale=cfg_scale,
            sampler_name=sampler_name,
            scheduler=scheduler,
            checkpoint=checkpoint,
            width=width,
            height=height,
            batch_size=request.count,
        )

        return workflow

    def _get_default_workflow(self) -> Dict[str, Any]:
        """获取默认工作流的深拷贝"""
        return json.loads(json.dumps(self.DEFAULT_WORKFLOW))

    def _update_workflow_params(
        self,
        workflow: Dict[str, Any],
        prompt: str,
        negative_prompt: str,
        seed: int,
        steps: int,
        cfg_scale: float,
        sampler_name: str,
        scheduler: str,
        checkpoint: str,
        width: int,
        height: int,
        batch_size: int,
    ) -> Dict[str, Any]:
        """
        更新工作流参数

        尝试智能匹配节点类型并更新参数。
        """
        for node_id, node in workflow.items():
            class_type = node.get("class_type", "")
            inputs = node.get("inputs", {})

            if class_type == "KSampler":
                inputs["seed"] = seed
                inputs["steps"] = steps
                inputs["cfg"] = cfg_scale
                inputs["sampler_name"] = sampler_name
                inputs["scheduler"] = scheduler

            elif class_type == "CheckpointLoaderSimple":
                inputs["ckpt_name"] = checkpoint

            elif class_type == "EmptyLatentImage":
                inputs["width"] = width
                inputs["height"] = height
                inputs["batch_size"] = batch_size

            elif class_type == "CLIPTextEncode":
                # 根据连接判断是正向还是负向提示词
                # 默认第一个找到的设为正向，第二个设为负向
                if not inputs.get("text") or inputs.get("text") == "":
                    # 检查是否被KSampler的negative引用
                    is_negative = self._is_negative_prompt_node(workflow, node_id)
                    inputs["text"] = negative_prompt if is_negative else prompt

        return workflow

    def _is_negative_prompt_node(self, workflow: Dict[str, Any], node_id: str) -> bool:
        """
        检查节点是否是负向提示词节点

        通过检查KSampler节点的negative输入来判断。
        """
        for node in workflow.values():
            if node.get("class_type") == "KSampler":
                negative_input = node.get("inputs", {}).get("negative", [])
                if isinstance(negative_input, list) and len(negative_input) > 0:
                    if negative_input[0] == node_id:
                        return True
        return False

    def _get_dimensions(
        self,
        request: ImageGenerationRequest,
        extra_params: Dict[str, Any],
    ) -> tuple:
        """
        获取图片尺寸

        优先级：extra_params > 基于ratio计算 > 默认值
        """
        # 检查直接指定的尺寸
        if "width" in extra_params and "height" in extra_params:
            return extra_params["width"], extra_params["height"]

        # 基于宽高比计算（默认基于1024的基础尺寸）
        base_size = extra_params.get("base_size", 1024)
        ratio = request.ratio or "16:9"

        ratio_dimensions = {
            "1:1": (base_size, base_size),
            "16:9": (base_size, int(base_size * 9 / 16)),
            "9:16": (int(base_size * 9 / 16), base_size),
            "4:3": (base_size, int(base_size * 3 / 4)),
            "3:4": (int(base_size * 3 / 4), base_size),
            "3:2": (base_size, int(base_size * 2 / 3)),
            "2:3": (int(base_size * 2 / 3), base_size),
            "21:9": (base_size, int(base_size * 9 / 21)),
        }

        width, height = ratio_dimensions.get(ratio, (1024, 576))

        # 确保是64的倍数（SD要求）
        width = (width // 64) * 64
        height = (height // 64) * 64

        return width, height

    async def _queue_prompt(
        self,
        client: httpx.AsyncClient,
        base_url: str,
        workflow: Dict[str, Any],
        client_id: str,
        config: ImageGenerationConfig,
    ) -> str:
        """提交工作流到ComfyUI队列"""
        payload = {
            "prompt": workflow,
            "client_id": client_id,
        }

        response = await client.post(
            f"{base_url}/prompt",
            headers=self.get_auth_headers(config),
            json=payload,
        )

        if response.status_code != 200:
            error_msg = f"提交工作流失败: HTTP {response.status_code}"
            try:
                error_data = response.json()
                if "error" in error_data:
                    error_msg = f"ComfyUI错误: {error_data['error']}"
                elif "node_errors" in error_data:
                    # 节点错误
                    node_errors = error_data["node_errors"]
                    error_details = []
                    for node_id, errors in node_errors.items():
                        for err in errors.get("errors", []):
                            error_details.append(f"节点{node_id}: {err.get('message', '未知错误')}")
                    if error_details:
                        error_msg = "工作流错误: " + "; ".join(error_details[:3])
            except Exception:
                pass
            raise Exception(error_msg)

        result = response.json()
        return result["prompt_id"]

    async def _poll_for_completion(
        self,
        client: httpx.AsyncClient,
        base_url: str,
        prompt_id: str,
        config: ImageGenerationConfig,
    ) -> Dict[str, Any]:
        """
        轮询等待任务完成

        Returns:
            输出节点的结果信息
        """
        start_time = asyncio.get_event_loop().time()

        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > COMFYUI_MAX_POLL_TIME:
                raise asyncio.TimeoutError()

            response = await client.get(
                f"{base_url}/history/{prompt_id}",
                headers=self.get_auth_headers(config, content_type=""),
            )

            if response.status_code == 200:
                history = response.json()
                if prompt_id in history:
                    task_info = history[prompt_id]

                    # 检查是否完成
                    status = task_info.get("status", {})
                    if status.get("completed", False):
                        outputs = task_info.get("outputs", {})
                        return outputs

                    # 检查是否出错
                    if status.get("status_str") == "error":
                        messages = status.get("messages", [])
                        error_msg = "生成失败"
                        if messages:
                            for msg in messages:
                                if len(msg) >= 2 and msg[0] == "execution_error":
                                    error_detail = msg[1]
                                    error_msg = error_detail.get("exception_message", error_msg)
                                    break
                        raise Exception(error_msg)

            await asyncio.sleep(COMFYUI_POLL_INTERVAL)

    async def _fetch_images(
        self,
        client: httpx.AsyncClient,
        base_url: str,
        outputs: Dict[str, Any],
        config: ImageGenerationConfig,
    ) -> List[str]:
        """
        从ComfyUI获取生成的图片

        将图片转换为base64 data URL返回。
        """
        image_urls = []

        for node_id, output in outputs.items():
            images = output.get("images", [])
            for image_info in images:
                filename = image_info.get("filename")
                subfolder = image_info.get("subfolder", "")
                img_type = image_info.get("type", "output")

                if not filename:
                    continue

                # 构建查看URL
                params = {
                    "filename": filename,
                    "type": img_type,
                }
                if subfolder:
                    params["subfolder"] = subfolder

                # 获取图片数据
                try:
                    response = await client.get(
                        f"{base_url}/view",
                        params=params,
                        headers=self.get_auth_headers(config, content_type="", accept="image/*"),
                    )

                    if response.status_code == 200:
                        # 转换为base64 data URL
                        content_type = response.headers.get("content-type", "image/png")
                        b64_data = base64.b64encode(response.content).decode("utf-8")
                        data_url = f"data:{content_type};base64,{b64_data}"
                        image_urls.append(data_url)
                    else:
                        logger.warning(
                            "获取图片失败: %s, HTTP %d",
                            filename,
                            response.status_code
                        )
                except Exception as e:
                    logger.warning("获取图片异常: %s - %s", filename, e)

        return image_urls

    def get_supported_features(self) -> dict:
        """获取ComfyUI支持的特性"""
        return {
            "negative_prompt": True,
            "style": True,
            "quality": False,  # 通过steps控制
            "resolution": True,
            "ratio": True,
            "cfg_scale": True,
            "steps": True,
            "sampler": True,
            "scheduler": True,
            "checkpoint": True,
            "custom_workflow": True,  # 支持自定义工作流
        }
