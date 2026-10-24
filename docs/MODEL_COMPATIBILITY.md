# 模型与格式兼容表

核对日期：2026-10-23。该表是已核实的兼容快照，不是所有厂商、地区、账户可用型号的完整清单。型号、计费、地区权限、预览资格及下架时间以服务商为准。本次验证使用离线请求合同测试，未使用用户密钥调用付费模型。

## 先区分三种模型

1. **文本／视觉理解模型**：本地加载，或通过 API 读取 Skill 底稿并生成提示词正文。API 面板的模型名属于这一类。
2. **图像提示词目标模型**：控制给下游生图模型使用的文字组织方式，不在这里加载扩散模型，也不调用图片生成接口。
3. **视频提示词目标模型**：输出自然语言分镜及机器可读的分镜 JSON，不在这里生成或上传视频。参考图、参考视频、音频等素材仍需交给下游生成节点。

不要把 `qwen-image-3.0-pro`、`wan3.0-video` 等媒体生成型号填进文本润色 API 模型框。

## API 型号与协议

| 服务商 | 新选择服务商时的默认型号 | 本次新增／核实的候选 |
| --- | --- | --- |
| 通义千问 DashScope | `qwen3.8-max` | `qwen3.8-flash`、`qwen3.7-plus`、`qwen3.8-omni-flash`，以及百炼目录中的 DeepSeek、Kimi、GLM、MiniMax 文本型号 |
| DeepSeek | `deepseek-flash` | `deepseek-v4-pro`；旧 `deepseek-v4-flash` 别名保留输入兼容，官方已将其路由到新版 Flash |
| Claude Anthropic | `claude-haiku-5-5` | `claude-sonnet-5-5`、`claude-opus-5-5`、`claude-fable-5-1`、`claude-mythos-5-1`；SDK 中列出不等于当前账户一定有权限 |
| Gemini 原生／OpenAI 兼容 | `gemini-flash-latest` | `gemini-3.1-pro-preview`；`latest` 是服务商浮动别名，需要复现时应自填账户可用的固定版本 |
| OpenAI／其他服务商 | 保留原值 | OpenAI 官方文档本次返回 403，未依据推测或内置快照强行升级；其他未核实的服务商同样保留原预设 |

模型框新增按服务商分类的候选提示，不是允许列表。私有部署名、旧快照、微调型号都可以自填。重新选择服务商按钮仍会应用该服务商预设；单纯打开工作流、刷新候选或升级插件不会覆盖已填模型名。

继续支持六条协议路线：OpenAI Chat Completions、Responses、Anthropic Messages、Gemini `generateContent`、DashScope Generation／MultiModalConversation、Ollama Chat。可填写 Base URL 或完整端点；协议与路径必须匹配。OpenAI 兼容不等于支持 OpenAI 的全部参数。

本次请求格式调整：

- DeepSeek 的 `deepseek-flash`、V4／V4.1 Flash／Pro 及日期快照统一识别。Chat Completions 发送 `thinking.type=disabled`，Responses 发送 `reasoning.effort=none`，避免把同一字段跨协议混用。该规则只应用于 DeepSeek 服务商或精确官方主机，不污染无关网关。
- Qwen3.8 原生调用维持现有思考路线，但思考预算不超过 1024 token，并按输出预算缩小；显式 `preserve_thinking=false`。不同时发送 `reasoning_effort` 与 `thinking_budget`。这些内部思考参数不进入最终图片／视频正文。
- Claude 5 型号按当前官方 SDK 请求类型省略旧 `temperature`、`top_p`、`top_k` 字段；显式选择旧 Claude 型号时保留原采样设置。
- 已有可选参数兼容重试、密钥来源保护、代理诊断、取消和 Skill 回退继续生效。不能用重试解决无权限、错误型号、配额不足、网络封锁或缺失运行时。

## 图像提示词格式

| 新 Profile | 已核实的模型名称 | 输出约定 |
| --- | --- | --- |
| `FLUX.2` | FLUX.2 [dev]、[klein] 4B／9B／Base／KV 系列 | 主体、动作、场景、镜头、光线与材质关系优先；不把平台参数混进正文 |
| `FLUX.3` | `flux-3-image`（官方托管接口） | 媒介、主体位置与空间关系优先；画面文字原文加引号。该接口没有独立 `negative_prompt` 字段，不把负面标签混进正向正文 |
| `FLUX.3 Klein` | `black-forest-labs/flux-3-image-klein`、`-base` | 复用 FLUX.3 的可见画面描述；本地生成仍应保留官方 prompt upsampler，本节点正文不是已验证的替代品 |
| `MOSS Image` | `OpenMOSS-Team/MOSS-Image-Base`、`MOSS-Image-SFT` | 构图、主体位置、物体关系、动作与光影的详细自然语言；保留用户指定文字、位置与换行，不擅自写字。官方偏好英文但不强制覆盖所选语言 |
| `Qwen Image 2.1` | `Qwen/Qwen-Image-2.1`、`qwen-image-2.1-pro` | 生成、编辑与最多 10 张参考图；明确参考顺序及保留／变更内容。RGBA 仅在用户请求且下游支持时启用 |
| `Qwen Image 2.1 Turbo` | `Qwen/Qwen-Image-2.1-Turbo`、`qwen-image-2.1-turbo` | 同一自然语言格式；8 步调度属于下游模型配置，不写进正文，也不套用于其他模型 |
| `Qwen Image 2512` | `Qwen/Qwen-Image-2512` | 完整自然语言与明确空间关系，保留人物、材质和构图事实 |
| `Qwen Image Edit 2511` | `Qwen/Qwen-Image-Edit-2511` | 记录编辑／多参考用途；引用素材必须由下游实际提供 |
| `Qwen Image 3.0` | `qwen-image-3.0-pro` | 继承 Qwen Image 的关系描述顺序，保留已选设计硬锚点 |
| `Wan 2.7 Image` | `wan2.7-image-pro` | 通用自然语言图像格式，不虚构平台参数 |
| `Gemini Image` | `gemini-3.1-flash-lite-image` | 通用自然语言生成／编辑描述，平台请求体由下游处理 |

原来的通用、Flux、SDXL、Qwen Image、Krea 2、Midjourney、自定义均保留。不同版本共用相同语言规则时会明确复用家族逻辑，不伪造版本专用语法。图像 Profile 返回独立数据，修改本次 `prompt_order`、型号列表不会污染后续运行。

三视图仍将 `layout_contract` 放在首位：同一角色、同一比例与光照，等宽正面／90 度侧面／背面，不混入视频剧情。JSON 的 `image_prompt_contract` 新增家族、参考型号、用途、参考保留约定和核对日期。`negative_prompt` 仍是独立输出；是否把它交给生成接口由下游决定，不能假设所有图片 API 都有负面词参数。

MOSS-Image 的官方 Layout 使用 `summary/items` 与居中像素 `yxyx` 坐标；FLUX.3 的版式使用其自身 schema，二者不可串用。本轮采用自然语言位置描述，只在合同中记录下游版式能力，**不自动虚构框坐标或提交 Layout JSON**。MOSS 发布版的 Base/SFT 记录为 T2I／Layout，不据此宣称原生多参考编辑。其 4096 token 上限是下游文本编码限制，不是 4096 个汉字；本节点不按字符数截断用户正文，使用者仍需核对下游 tokenizer。

图像合同新增 `max_reference_images`、`transparency_contract`、`prompt_expansion_policy`、`prompt_token_limit` 等型号适用字段，以及 `weight_format_policy`。GGUF、BF16、FP8 等权重形态通常不改变自然语言格式，但需要匹配下游实际架构与加载器。

人物三视图继续使用清晰正脸、正面／90 度侧面／背面的等宽等高合同；非人物三视图单独描述同一器物、机械或建筑的完整轮廓、结构、部件、表面与材质，不再注入人物五官、发型、服装或站姿。Skill、智能文本和本地／API 润色共享此区分；非人物模式仍校验视图角度与均分布局，不因去除人脸要求而放松版式。自动补齐标签同样使用主体整体、顶底基准线和一致结构状态；用户明确选择的原始标签不做全局替换。

设定图入口和参考图反推同样保留显式的非人物主体类型，并使用结构化实体特征与兼容的历史避重方向。`仅反推描述` 不启用设定图，会将可见环境与实体事实送入普通智能文本流程。

## 视频提示词格式

| 新 Profile | 已核实的型号 | 本 Profile 确认的输入模式 |
| --- | --- | --- |
| `FLUX.3 Video` | `flux-3-video`（官方托管接口） | T2V、I2V、FL2V；支持同步音频及多镜头。视频续写／编辑与带时间戳关键帧仍由下游对应接口处理 |
| `Wan 3.0` | `wan3.0-video`、`wan3.0-video-prime` | T2V、I2V、FL2V、Ref2V |
| `Wan 2.7` | `wan2.7-t2v`、`wan2.7-i2v`、`wan2.7-r2v-2026-06-12` | T2V、I2V、FL2V、Ref2V；具体模式需选对应下游型号 |
| `LTX 2.5` | `Lightricks/LTX-2.5` | T2V、I2V；JSON 标记 `submission_unit=per_shot`，每段可分别交给下游生成后剪辑 |
| `HappyHorse 1.1` | `happyhorse-1.1-t2v`／`i2v`／`r2v` | T2V、I2V、Ref2V |
| `Veo 3.1` | `veo-3.1-generate-preview` | T2V、I2V；预览权限和其他输入能力请另查下游实际版本 |

这是一组保守的已确认子集，不是完整能力矩阵。原有 H3、Wan、LTX、Seedance、通用、自定义保持兼容。未确认的输入组合仍保留用户选择，并在 `compatibility_notes` 和运行诊断中提示，`input_mode_supported=false` 不表示厂商所有版本永远不支持该模式。

每段保持完整自然语言分镜，所有段落组成同一个故事。`video_prompt_profile` 与逐镜头 `video_storyboard` 新增 `input_contract`、`submission_unit`、`input_mode_supported`，用于约束首帧事实、首尾帧过渡与参考一致性。`native_audio=true` 只表示已核实的下游模型有音频能力，不表示本节点已传入音轨。

参考素材约束在镜头数量调整后绑定到实际首镜与末镜，覆盖单镜头、短动作、标准剧情与长剧情，以及中英文／双语输出。I2V／FL2V 开场优先沿用输入首帧的景别、机位和主体位置，不再同时强加模板的中心站位；FL2V／L2V 最后收束到输入尾帧，不用原有构图覆盖尾帧。单镜头正文独立交代主体、服装、场景、道具、动作与可见结果，不引用并不存在的上一分镜。这些是提示词约束，不代表节点读取、验证或传输了参考帧。

本地／API 模型采纳、定向修复与增量融合共享镜头数量和参考素材边界检查，接受中英文同义描述，不要求逐字复述底稿。候选丢失首尾帧约束、擅自改变镜头数或明确要求忽略输入参考时，不会直接覆盖 Skill 结果。单镜头 JSON 也使用独立连续拍摄说明，不要求交接给不存在的前后镜头。

最终历史避重仍在原镜头内部补充兼容变化，不追加第六镜或改变末镜；后处理后再次检查镜头数量和参考素材边界。双语正文的 JSON 分镜从独立中文段提取，镜头数量与 Profile 及实际正文保持一致。

非人物视频用既有结构状态、接触关系和表面变化组织分镜；通用剧情池中的人物专属反馈不会机械套到器物上，音效也不默认追加脚步、呼吸或衣料声。该处理只作用于自动剧情措辞，不删除用户明确选择的主体部件或视觉事实。

时间轴默认关闭；启用后现有 8 秒轴只作为节点的编排参考，不代表任一服务商固定只支持 8 秒。真实时长、分辨率、帧率、参考素材和生成参数在下游配置。

## 本地权重格式与新模型

当前内置路线保持两类：

| 格式 | 加载方式与边界 |
| --- | --- |
| `.gguf` | 依赖当前 `llama-cpp-python` 实际支持的架构和量化类型；视觉任务还需匹配版本的 mmproj 与 chat handler |
| 原始模型目录 | `config.json`、tokenizer／processor 及 `.safetensors`／`.bin`／`.pt`／`.pth`／`.ckpt` 权重，交给 Transformers；权重扩展名相同不代表架构一定兼容 |

Qwen3.8 的 27B、2.4T-A95B，以及 Qwen3.6 27B／35B-A3B 已在官方仓库核实。节点已有 Qwen3.8 自动识别，主模型与 mmproj 的精确版本校验继续生效。大型模型不等于本机显存可运行；新架构需要更新运行时后再尝试加载，本次不自动下载权重或升级依赖。

AWQ、GPTQ 等量化仓库只有在当前 Transformers 及其可选依赖支持时才可能走原始目录路线，不能仅凭扩展名保证成功。EXL2、MLX／MLX-VLM 等专用运行时未新增为 Windows 内置后端；可以由对应运行时提供 OpenAI 兼容服务后，通过节点的 API 路线连接。Ollama、LM Studio、vLLM、SGLang、Transformers Serve 的模型名以实际部署名为准，不自动猜测或拉取。

原始模型的 GPU 层数设为数值 `0` 时按 CPU 路线处理，不会因默认值判断误变成自动 GPU；高级 JSON 的显式 `device_map` 仍优先。视觉输入在完整编码后检查上下文，不单独截断图像占位 token；预算不足时在 `generate()` 前报出所需 token 与调整建议，纯文本截断和动态输出预算保持原逻辑。

原始模型优先使用自身 `generation_config` 的完整 EOS 列表，随后才回退到模型配置或 tokenizer；显式调用覆盖仍有效。Seq2Seq 的编码器／解码器窗口分别受各自元数据和节点上下文约束，tokenizer 的输入长度限制不占用解码器输出预算；解码器起始 token 与已有前缀仍占用输出侧窗口。

取消异常在图片、视频、批量与定向修复入口保持抛出，普通错误仍回退 Skill。批量逐条重试按最终实际回退输出计数，正文校验不合格不能算作恢复成功。对于签名不可反射的 Python 后端，参数绑定失败仍可兼容重试，但已进入后端内部的 `TypeError` 不再导致重复调用；C 扩展的内部执行状态未必可由 Python 调用栈判断。

图片反推入口同样传播显式取消，即使后端已经复位全局中断标记；空正文在共享结果发布前判为失败，并发等待方使用一致的失败诊断，空结果不缓存。API 响应体的真实缓冲 socket 使用非阻塞探测与协作等待，避免短读取超时损坏缓冲流；仍保留总时限、取消、大小限制和原 socket 状态。流式原生增量保留重复片段，累计消息快照继续按快照合并。

Anthropic Messages SSE 按内容块索引组合可见 `text_delta`，不把 thinking 或工具输入并进正文；Responses SSE 仅接收 output-text 事件，保留完成／不完整状态，服务端失败事件不会作为成功的空响应或部分结果返回。SSE 以空行划分事件，同一事件的多条 `data:` 行先合并再解析，避免丢失跨行正文或失败信息；明确的 `error`／`response.failed` 事件即使正文损坏也会报错，普通心跳继续忽略。继续兼容单行事件与 NDJSON。以上协议归一只作用于识别出的流式事件，非流式 JSON 响应形状不变。

本轮 GGUF 更新：

- 保留 `.gguf` 全量文件扫描，不按 Q／IQ／TQ／MXFP4／NVFP4 后缀过滤；新量化类型是否能运行取决于实际二进制与设备，不能仅凭后缀保证。
- 标准 `-00001-of-000NN.gguf` 分片只显示首片；旧工作流选中后续分片时自动归一，加载前检查同组全部分片。缺片不卸载已托管模型。
- 最多读取 256 KiB 头部，尽力识别 GGUF v2/v3 的名称、架构等信息。未知版本、截断或超出预算的元数据交给运行时处理，不据此宣称文件完整或支持新架构；明确的扩散模型／投影元数据会提示不要充当文本主模型。
- KV 缓存新增 q4_0、q4_1、q5_0、q5_1、bf16，先检查已安装运行时是否导出对应常量；具体内核仍可能受硬件、架构和 Flash Attention 限制。模型权重量化与 KV 精度是两个独立参数，旧默认 F16 不变。
- 同时兼容旧版平铺 `GGML_TYPE_*` 常量和新版 `_ggml.GGMLType` 枚举位置；本机只读检查确认安装版本为 `llama-cpp-python 0.3.34`，新枚举下的 q4/q5/bf16 类型可识别。这不代表已经完成相应权重的 GPU 推理验证。
- 模型自动识别的诊断文字不再参与加载参数缓存比较，避免相同权重被重复卸载、重载。文件与可预检配置错误尽量在卸载现有模型前报告；实际分配显存或加载权重阶段的失败仍不能保证保留旧实例。
- API、仅 Skill 或外接模型模式不再被闲置内置模型／mmproj 的旧文件选择阻止；实际使用内置模型时仍校验文件选项与分片。前端保留旧工作流当前选项的显示，并同步刷新后的文件候选，不擅自换成另一份权重。
- 没有自动安装／升级 `llama-cpp-python`、CUDA 或 DLL，也没有下载权重。本轮 GGUF 验证使用合成头部和模拟后端，不是实机权重推理测试。

## 官方核对来源

- [阿里云百炼模型目录](https://help.aliyun.com/zh/model-studio/models)
- [DashScope 原生请求与 Qwen3.8 参数](https://help.aliyun.com/zh/model-studio/qwen-api-via-dashscope)
- [DeepSeek 当前模型](https://api-docs.deepseek.com/quick_start/pricing)、[思考模式](https://api-docs.deepseek.com/guides/thinking_mode)、[Responses](https://api-docs.deepseek.com/guides/responses_api)
- [Anthropic 官方 SDK 型号定义](https://github.com/anthropics/anthropic-sdk-python/blob/main/src/anthropic/types/model.py)、[Messages 请求定义](https://github.com/anthropics/anthropic-sdk-python/blob/main/src/anthropic/types/message_create_params.py)
- [Google Gen AI 官方 SDK：当前型号与图像／视频示例](https://github.com/googleapis/python-genai)
- [Qwen3.8／3.6 官方仓库](https://github.com/QwenLM/Qwen3.5)
- [FLUX.2 官方仓库](https://github.com/black-forest-labs/flux2)、[Qwen Image 官方仓库](https://github.com/QwenLM/Qwen-Image)
- [Qwen Image 2.1／Turbo 官方仓库与提示词增强说明](https://github.com/QwenLM/Qwen-Image-2.1)
- [MOSS-Image 官方仓库](https://github.com/OpenMOSS/MOSS-Image)、[用户指南](https://github.com/OpenMOSS/MOSS-Image/blob/main/USERGUIDE.md)
- [FLUX.3 Image 官方提示词说明](https://docs.bfl.ai/guides/prompting_unified_basics)、[FLUX.3 Klein 官方仓库](https://github.com/black-forest-labs/flux-3-image-klein)、[FLUX.3 视频](https://docs.bfl.ai/flux_3/flux3_video)
- [GGUF 类型与量化定义](https://github.com/ggml-org/llama.cpp/blob/master/gguf-py/gguf/constants.py)、[llama-cpp-python 构造参数](https://github.com/abetlen/llama-cpp-python/blob/main/llama_cpp/llama.py)
- [LTX-2.5 官方仓库](https://github.com/Lightricks/LTX-2)
- [万相／HappyHorse 视频模型目录](https://help.aliyun.com/zh/model-studio/video-generation)

上游 `main`、浮动别名和在线目录会继续变化。发现新型号时可以先自填，不必等待插件枚举更新；不要因候选列表没有某个名字就判定它不受支持。
