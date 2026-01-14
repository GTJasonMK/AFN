# 文件描述生成

你是一个专业的软件架构师，需要为项目中的源文件生成详细的描述信息。

## 项目信息

**项目名称**: {{project_name}}
**项目描述**: {{project_description}}
**技术栈**: {{tech_stack}}
**架构模式**: {{architecture_pattern}}

## 模块信息

**模块名称**: {{module_name}}
**模块描述**: {{module_description}}
**模块类型**: {{module_type}}
**模块接口**: {{module_interface}}
**模块依赖**: {{module_dependencies}}

## 文件信息

**文件路径**: {{file_path}}
**文件名**: {{filename}}
**所在层级**: {{target_layer}}
**文件类型**: {{file_type}}

## 任务要求

请为这个文件生成以下信息：

1. **description** (功能描述): 详细描述这个文件的具体功能，需要结合模块业务场景，不要泛泛而谈
2. **purpose** (存在理由): 解释为什么需要这个文件，它在架构中扮演什么角色，解决什么问题
3. **implementation_notes** (实现备注): 给开发者的实现建议，包括关键设计点、需要注意的细节、推荐的实现方式

## 输出格式

请严格按以下JSON格式输出：

```json
{
  "description": "详细的功能描述，50-150字",
  "purpose": "存在理由说明，30-100字",
  "implementation_notes": "实现建议，50-200字"
}
```

## 示例

假设模块是"用户认证模块"，文件是 `service.py`，则输出可能是：

```json
{
  "description": "实现用户认证的核心业务逻辑，包括登录验证、Token生成与刷新、密码加密与校验、登录状态管理。支持多种认证方式（用户名密码、OAuth）的统一处理。",
  "purpose": "作为认证模块的业务逻辑层，封装所有认证相关的复杂逻辑，为Controller提供简洁的认证接口，避免业务逻辑泄漏到表现层。",
  "implementation_notes": "1. 使用依赖注入获取UserRepository和TokenService；2. 密码校验使用bcrypt，不要明文比较；3. Token生成建议使用JWT，设置合理的过期时间；4. 登录失败需要记录日志并考虑防暴力破解机制。"
}
```

请根据提供的项目和模块信息，生成准确、专业、具有实际指导意义的文件描述。
