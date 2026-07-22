import { app } from "/scripts/app.js";

window.__QWEN_TE_STAGE_MAIN_UI_LOADED__ = true;
window.__QWEN_TE_STAGE_MAIN_UI__ = true;

const EXTENSION_NAME = "QwenTE.StagePromptGeneratorUI";
const TARGET_NODE_CLASSES = new Set(["QwenTE_StagePromptGenerator", "QwenTE_UniversalStagePromptGenerator"]);
const TARGET_NODE_CLASS = "QwenTE_StagePromptGenerator";
const STAGE_DISPLAY_NAME_MARKERS = ["阶段式提示词生成器", "真男人提示词阶段生成器"];
const STAGE_WIDGET_SIGNATURE_NAMES = ["qwen模型", "模板风格", "首条正向提示词"];
const STAGE_OUTPUT_SIGNATURE_GROUPS = new Map([
	["结果全文", "full"], ["全文", "full"],
	["首条正向提示词", "positive"], ["正向", "positive"],
	["已选标签", "tags"], ["标签", "tags"],
	["JSON结果", "json"], ["JSON", "json"],
	["推荐负面词", "negative"], ["负面", "negative"],
	["正向提示词合集", "collection"], ["合集", "collection"],
	["智能文本", "smart"], ["智能", "smart"],
]);
const PANEL_KEY = Symbol.for("qwen_te.stage_prompt.panel");
const PANEL_READY_KEY = Symbol.for("qwen_te.stage_prompt.panel_ready");
const MODEL_LOADER_PANEL_KEY = Symbol.for("qwen_te.model_loader.panel");
const HIDDEN_KEY = Symbol("qwen_te_hidden");
const NAMED_STATE_KEY = "qwen_te_named_widget_state_v1";
const NODE_CACHE_NAMESPACE_KEY = "qwen_te_cache_namespace_v1";
const NODE_CACHE_NAMESPACE_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._:-]{7,127}$/u;
const NODE_HISTORY_KEY = "qwen_te_history_v1";
const NODE_CONTINUOUS_REPORT_KEY = "qwen_te_continuous_report_v1";
const NODE_CONTINUOUS_LOG_KEY = "qwen_te_continuous_log_v1";
const NODE_PRESET_BATCH_STATE_KEY = "qwen_te_preset_batch_state_v1";
const NODE_RANDOM_CORE_STATE_KEY = "qwen_te_random_core_state_v1";
const NODE_RANDOM_CORE_SIGNATURE_KEY = "qwen_te_random_core_signature_v1";
const NODE_RANDOM_LAST_STATE_KEY = "qwen_te_random_last_state_v1";
const NODE_RANDOM_COMBO_HISTORY_KEY = "qwen_te_random_combo_history_v1";
const NODE_RANDOM_COMBO_PREVIEW_KEY = "qwen_te_random_combo_preview_v1";
const NODE_AUTO_NEGATIVE_SYNC_KEY = "qwen_te_auto_negative_sync_v1";
const NODE_QUALITY_AUDIT_KEY = "qwen_te_quality_audit_v1";
const NODE_WORKFLOW_OUTPUT_KEY = "qwen_te_workflow_output_v1";
const NODE_MODEL_API_RUNTIME_SIGNATURE_KEY = "qwen_te_model_api_runtime_signature_v1";
const NODE_NSFW_PROFILE_RESTORE_KEY = "qwen_te_nsfw_profile_restore_v1";
const NODE_CHARACTER_SHEET_RESTORE_KEY = "qwen_te_character_sheet_restore_v1";
const NODE_SMART_TEXT_AUTO_EXTRA_KEY = "qwen_te_smart_text_auto_extra_v1";
const NODE_STATE_MUTATION_REVISION_KEY = Symbol("qwen_te_state_mutation_revision");
const NODE_LIBRARY_REFRESH_REVISION_KEY = Symbol("qwen_te_library_refresh_revision");
const NODE_QUALITY_AUDIT_REVISION_KEY = Symbol("qwen_te_quality_audit_revision");
const NODE_PROGRAMMATIC_WIDGET_WRITE_DEPTH_KEY = Symbol("qwen_te_programmatic_widget_write_depth");
const WIDGET_SUMMARY_REFRESH_BOUND_KEY = Symbol("qwen_te_summary_refresh_bound");
const SLOT_PANEL_LIBRARY_SIGNATURE_KEY = Symbol("qwen_te_slot_panel_library_signature");
const SLOT_PANEL_POPULATED_KEY = Symbol("qwen_te_slot_panel_populated");
const SLOT_PANEL_LIBRARY_SIGNATURE_CACHE = new WeakMap();
let slotPanelListSequence = 0;
const NODE_REMOVED_KEY = Symbol.for("qwen_te.node.removed");
const NODE_ENHANCE_RETRY_STATE_KEY = Symbol.for("qwen_te.stage_prompt.enhance_retry_state");
const STAGE_NODE_LIFECYCLE_PATCH_KEY = Symbol.for("qwen_te.stage_prompt.lifecycle_patch");
const GRAPH_NODE_ADDED_PATCH_KEY = Symbol.for("qwen_te.graph.node_added_patch");
const RANDOM_DEDUPE_CACHE_WIDGET_NAME = "随机补充避重缓存";
const PROMPT_DEDUPE_CACHE_WIDGET_NAME = "连续生成避重缓存";
const RUNTIME_RANDOM_PROTECTED_TAGS_WIDGET_NAME = "运行时随机保护标签";
const RUNTIME_RANDOM_PREVIEW_TOKEN_WIDGET_NAME = "运行时随机预览令牌";
const GLOBAL_STAGE_QUEUE_CAPTURE_FLAG = "__qwenTeStagePromptQueueCaptureInstalled";
const NODE_HISTORY_LIMIT = 50;
const USER_PRESET_LIMIT = 30;
const NODE_HISTORY_ITEM_MAX_BYTES = 160 * 1024;
const NODE_HISTORY_TOTAL_MAX_BYTES = 1024 * 1024;
const NODE_HISTORY_IMPORT_MAX_BYTES = 2 * 1024 * 1024;
const USER_PRESET_ITEM_MAX_BYTES = 160 * 1024;
const USER_PRESET_TOTAL_MAX_BYTES = 1024 * 1024;
const USER_PRESET_IMPORT_MAX_BYTES = 2 * 1024 * 1024;
const USER_PRESET_NAME_MAX_CHARS = 128;
const NSFW_CUSTOM_FIELD_ENTRY_LIMIT = 80;
const NSFW_CUSTOM_FIELD_ENTRY_MAX_CHARS = 256;
const NSFW_CUSTOM_FIELD_LIBRARY_MAX_BYTES = 128 * 1024;
const NSFW_WORKSPACE_MAX_JSON_BYTES = 128 * 1024;
const NSFW_WORKSPACE_MAX_LIST_ITEMS = 128;
const NSFW_WORKSPACE_MAX_TERM_CHARS = 512;
const NSFW_WORKSPACE_MAX_SCALAR_CHARS = 2048;
const NSFW_WORKSPACE_MAX_CUSTOM_TEXT_CHARS = 512;
const NSFW_WORKSPACE_MAX_NEGATIVE_CHARS = 32768;
const NSFW_WORKSPACE_MAX_SCANNED_LIST_VALUES = 4 * NSFW_WORKSPACE_MAX_LIST_ITEMS;
const NSFW_WORKSPACE_MAX_LIST_SCAN_CHARS = 4 * NSFW_WORKSPACE_MAX_LIST_ITEMS * NSFW_WORKSPACE_MAX_TERM_CHARS;
const NSFW_WORKSPACE_MAX_PROVENANCE_GROUPS = 64;
const NSFW_WORKSPACE_MAX_PROVENANCE_TERMS = 256;
const NSFW_WORKSPACE_MAX_PROVENANCE_GROUP_CHARS = 128;
const UI_FETCH_DEFAULT_TIMEOUT_MS = 30000;
const RANDOM_COMBO_HISTORY_LIMIT = 8;
const USER_PRESET_STORAGE_KEY = "QwenTE.StagePromptGenerator.UserPresets";
const NSFW_CUSTOM_FIELD_LIBRARY_STORAGE_KEY = "QwenTE.StagePromptGenerator.NsfwFieldLibrary";
const USER_PRESET_SOURCE_LABELS = {
	manual: "手存预设",
	"arrange-preview": "整理预设",
	"single-preset": "单预设快照",
	"history-aggregate": "历史聚合快照",
};
const USER_PRESET_FILTER_LABELS = {
	all: "全部",
	favorites: "置顶",
	...USER_PRESET_SOURCE_LABELS,
};
const NSFW_WORKSPACE_DEFAULTS = {
	enabled: false,
	trigger_words: [],
	workspace_custom_tags: [],
	selector_character: "——",
	selector_outfit: "——",
	selector_action: "——",
	selector_scene: "——",
	selector_expression: "——",
	selector_prop: "——",
	scene: "——",
	action: "——",
	outfit: "——",
	mood: "——",
	anatomy_terms: "——",
	explicit_terms: "——",
	adult_action_style: "——",
	camera_movement: "——",
	camera_angle: "——",
	light_source: "——",
	light_type: "——",
	lens_type: "——",
	focal_length: "——",
	color_tone: "——",
	visual_style: "——",
	effect: "——",
	filter: "——",
	random_mode: "关闭",
	random_nonce: "",
	preset: "——",
	quality_tier: "高质量",
	negative_preset: "标准负面提示词",
	negative_apply_mode: "preview",
	custom_negative: "",
	custom_prefix: "",
	custom_suffix: "",
};
const NSFW_WORKSPACE_FIELD_ALIASES = {
	triggerWords: "trigger_words",
	workspaceCustomTags: "workspace_custom_tags",
	selectorCharacter: "selector_character",
	selectorOutfit: "selector_outfit",
	selectorAction: "selector_action",
	selectorScene: "selector_scene",
	selectorExpression: "selector_expression",
	selectorProp: "selector_prop",
	anatomyTerms: "anatomy_terms",
	explicitTerms: "explicit_terms",
	adultActionStyle: "adult_action_style",
	cameraMovement: "camera_movement",
	cameraAngle: "camera_angle",
	lightSource: "light_source",
	lightType: "light_type",
	lensType: "lens_type",
	focalLength: "focal_length",
	colorTone: "color_tone",
	visualStyle: "visual_style",
	randomMode: "random_mode",
	randomNonce: "random_nonce",
	qualityTier: "quality_tier",
	negativePreset: "negative_preset",
	negativeApplyMode: "negative_apply_mode",
	customNegative: "custom_negative",
	customPrefix: "custom_prefix",
	customSuffix: "custom_suffix",
	appliedCustomTags: "applied_custom_tags",
	appliedSelectedTags: "applied_selected_tags",
	manualCustomTags: "manual_custom_tags",
	userCustomTags: "manual_custom_tags",
	user_custom_tags: "manual_custom_tags",
	generationProfileRestore: "generation_profile_restore",
};
const NSFW_RANDOM_SEED_FIELDS = new Set(["trigger_words", "preset", "quality_tier", "negative_preset", "random_mode"]);
const NSFW_NEGATIVE_PRESETS = {
	"标准负面提示词": "low quality, blurry, bad anatomy",
	"WAN视频负面提示词": "色调艳丽，过曝，静态，细节模糊不清，字幕",
	"文生图负面提示词": "low quality, text, watermark, logo",
	"高质量负面提示词": "worst quality, low quality, blurry, bad anatomy",
	"自定义负面提示词": "",
};
const NSFW_WORKSPACE_OPTIONS = {
	selector_character: ["——", "单女性", "男女配对", "双女性", "多女性", "办公室女士", "女仆", "护士", "秘书", "警察", "军人", "偶像", "公主", "女王", "女神", "猫女", "兔女郎", "精灵", "魅魔", "吸血鬼", "女巫", "机器人", "仿生人", "半机械人"],
	selector_outfit: ["——", "比基尼", "内衣", "透明薄纱", "湿衣服", "破损衣服", "微型比基尼", "绳结比基尼", "丁字裤", "渔网装", "乳胶装", "皮革装", "太空服", "束缚造型", "项圈", "手铐", "眼罩", "高跟鞋"],
	selector_action: ["——", "接吻", "法式接吻", "颈部亲吻", "亲密拥抱", "身体贴近", "手部抚摸", "腿部打开姿态", "摩擦姿态", "女上位姿态", "站姿亲密", "脱衣舞", "钢管舞", "膝上舞"],
	selector_scene: ["——", "酒店套房", "情人酒店", "温泉", "淋浴场景", "浴缸场景", "车内", "办公室", "户外", "海滩", "按摩场景", "夜店", "私人泳池", "更衣室", "桑拿", "科幻舱室"],
	selector_expression: ["——", "脸红", "害羞", "诱惑视线", "微醺情绪", "出汗", "喘息感", "湿润质感", "心形眼睛", "微张嘴唇", "伸出舌尖", "眼泪"],
	selector_prop: ["——", "项圈", "牵引绳", "手铐", "绳索", "口塞", "眼罩", "鞭子", "成人道具", "纹身", "穿孔", "镜面道具", "玻璃反光"],
	scene: ["——", "豪华卧室，红色丝绒床单，镜面天花板", "精品酒店套房，暖色壁灯，落地窗夜景", "卧室落地窗夜景，柔纱窗帘，城市灯火", "浴后蒸汽浴室，雾化玻璃，温暖顶光", "私人温泉，岩石池沿，月色水汽", "复古化妆间，镜前灯泡，丝绒座椅", "暗调酒吧，吧台反光，低饱和霓虹", "影棚纯色背景，柔光箱，干净地台", "城市天台，晚风栏杆，远处灯海", "雨夜车窗，皮质座椅，玻璃水痕", "赛博街区，霓虹雨夜，潮湿路面", "古典月下庭院，回廊灯笼，石阶留白"],
	action: ["——", "男女深吻，镜前亲密拥抱，眼神交流", "倚靠窗边回眸，肩颈放松，指尖扶帘", "镜前整理妆发，视线避开镜头，姿态自然", "轻抚发丝，侧身站立，身体线条舒展", "整理肩带与衣领，表情克制，动作含蓄", "浴后擦发，水汽环绕，身体重心稳定", "扶栏远望，侧脸受光，衣摆被风带起", "端起酒杯轻靠吧台，眼神微醺，肩线清晰", "慢步转身，衣料有动态，脚步落点清楚", "托腮凝视，肘部支撑合理，眼神有情绪", "强成人氛围姿态，身体贴近，表情成熟克制", "私密姿态，动作含蓄但张力明确，镜头保持完整构图"],
	outfit: ["——", "蕾丝内衣套装，轮廓精致，材质层次清楚", "真丝吊带裙，柔软垂坠，边缘高光细腻", "丝质睡袍，腰带松弛，袖口自然垂落", "湿身薄纱罩衫，半透明层次，水汽贴合面料", "浴巾裹身，湿发贴肩，柔光皮肤质感", "黑色缎面礼服，低调光泽，高级剪裁", "细跟高跟鞋，脚踝线条清楚，落脚稳定", "透明高跟凉鞋，反光材质，脚部完整", "Lookbook贴身套装，版型明确，商业成片感", "汉服薄纱外搭，内外层次分明，衣摆流动", "低遮挡内衣风，贴身材质，轮廓关系清楚", "镂空蕾丝内衣，遮挡结构明确，材质层次清楚", "透明黑色纱裙，半透层次，身体轮廓清楚", "短款皮质热裤，搭配项圈，造型张力明确", "紧身乳胶装，光泽贴合身体轮廓", "蕾丝饰带缠绕，装饰性覆盖，轮廓关系清楚", "渔网连体装，低遮挡结构，主体完整入镜", "半裸湿透衬衫，贴合身体线条，水汽质感明确", "情趣吊带袜，搭配高跟鞋，腿部线条完整", "透明睡袍，薄纱层次，边缘高光细腻", "装饰性饰带缠绕，覆盖关系清楚，避免局部抢镜", "情趣制服，短裙摆与敞开扣子，版型清楚", "皮质束缚装，金属铆钉装饰，结构感明确", "成熟私房造型，薄纱与蕾丝层次明确，主体完整入镜"],
	mood: ["——", "克制诱惑，眼神清醒，情绪含蓄", "私密微醺，嘴角微扬，氛围松弛", "慵懒松弛，呼吸感明显，姿态自然", "冷艳自持，视线稳定，表情锋利", "温柔暧昧，面部柔和，情绪细腻", "自信注视，身体打开，镜头感强", "清冷疏离，低饱和情绪，动作克制", "高级性感，商业大片质感，主体完成度高", "高强度成人氛围，成熟诱惑，镜头克制不直白", "露骨感收敛表达，强调私密张力和成熟气质", "欲念张力，身体微颤，眼神迷离", "禁忌诱惑，嘴角微翘，情绪克制", "支配感，掌控姿态，人物关系清楚", "情绪迷醉，呼吸急促，表情集中", "强烈感官氛围，动作张力明确，画面不贴脸"],
	anatomy_terms: ["——", "乳房", "乳头", "外阴", "阴道", "阴蒂", "阴唇", "阴茎", "龟头", "睾丸", "臀部", "肛门", "私密部位细节"],
	explicit_terms: ["——", "性交", "插入", "自慰", "潮吹"],
	adult_action_style: ["——", "单人私密姿态，动作含蓄，表情张力明确", "单人挑逗动作，身体线条舒展，镜头保持完整构图", "脱衣动作，节奏缓慢，镜头保持全身关系", "舔唇表情，视线集中，面部情绪明确", "弯腰姿态，重心稳定，身体线条可读", "手部抚摸动作，动作连续，避免局部抢镜", "身体扭动，湿身滴水，动态自然", "胸部抚摸动作，表情迷离，镜头克制", "臀部慢摇，曲线突出，姿态不变形", "倚墙伸展姿态，手臂上举，身体比例稳定", "双手高举，身体拉伸，肩颈线条清楚", "低姿爬行动作，回头视线，空间透视稳定", "侧躺私房姿态，腿部交叠，曲线自然可读", "跪姿私房构图，背部拱起，发丝自然垂落", "微张嘴唇，呼吸感明显，表情张力集中", "湿身浴室动作，水汽与泡沫作为氛围遮挡", "道具氛围点缀，保留成人张力但避免局部特写", "成人道具参与，动作关系清楚，避免局部特写", "双人亲密拥抱，肢体靠近，主体关系清楚", "双人亲密互动，动作连续，镜头克制不直白", "站姿双人互动，重心稳定，身体关系明确", "跨坐互动，腰部距离清楚，人物关系稳定", "从后拥抱，颈部贴近，情绪亲密", "口部亲密互动，镜头克制，人物关系清楚", "轻拍臀部互动，动作提示明确，镜头不贴脸", "推拉节奏互动，肢体缠绕，人物关系不混乱", "侧躺双人互动，动作柔和，空间关系稳定", "亲密低语，头发触碰，眼神对视", "浴室双人亲密氛围，泡沫与水汽包裹主体", "车内亲密氛围，狭窄空间与玻璃反光增强张力", "腿部打开姿态，手部位置清楚，构图保持全身", "主从感互动，束缚元素作为造型叙事，避免暴力表达", "主从感跪姿互动，服从姿态作为叙事，避免暴力羞辱", "多人亲密氛围，主体优先，人物关系不混乱"],
	camera_movement: ["——", "静态封面肖像，主体稳定，背景干净", "缓慢推近面部，焦点停在眼睛和唇部妆感", "从全身到半身，先交代服装轮廓再收束表情", "拉远保留全身，脚部和衣摆完整入镜", "环绕式展示服装轮廓，保持单一主体比例", "镜前反射切换，主体与镜像关系清楚", "快速推进至局部细节，随后回到全身关系", "360度环绕，捕捉全身轮廓与服装材质", "低角度慢扫，从脚踝到腰线，节奏渐强", "柔焦跟随，锁定亲密动作关系", "动态放大后拉远，强调身体曲线与空间", "晃动镜头，营造紧张挑逗氛围", "快速变焦，强调情绪峰值"],
	camera_angle: ["——", "眼平视角，人物关系稳定", "轻微俯拍，面部与肩线清楚", "低角度全身，腿部比例自然", "过肩镜中视角，镜像不制造多人错觉", "侧面三分之二，脸部仍可读", "背面回头，发丝和衣摆完整", "窗边侧逆光视角，轮廓光分离主体", "低角度，突出臀部与腿部线条", "高角度，俯视亲密姿态，身体关系清楚", "过肩视角，聚焦亲密互动，主体关系稳定", "平视角度，强调表情与动作连续性"],
	light_source: ["——", "窗边自然光，柔纱漫射", "暖色台灯，局部照亮面部", "霓虹侧光，湿润反光", "红色烛光，摇曳氛围", "月光洒落，银色反光", "柔光箱，商业棚拍质感", "冷暖混合光，背景与主体分层", "粉紫霓虹光，循环闪烁", "低调私密灯光，晕染肌肤", "彩色渐变光，流动氛围", "闪烁氛围光，节奏同步"],
	light_type: ["——", "柔光，肤质过渡自然", "强烈背光，轮廓清楚", "侧逆光，勾出发丝和肩线", "边缘轮廓光，主体从背景分离", "低调光，保留暗部细节", "水汽散射，背景柔化", "低对比私密光，营造禁忌感", "彩色光晕，环绕身体轮廓", "闪烁节奏光，强化动作连续感", "低角度光，强调身体曲线"],
	lens_type: ["——", "全景全身，人物完整入镜", "近景半身，脸部和服装上半身清楚", "50mm标准镜头，透视自然", "85mm人像镜头，背景压缩柔和", "35mm环境人像，人物与场景关系清楚", "中画幅棚拍，层次细腻", "双人亲密接触，人物关系稳定", "动态局部镜头，随后回到主体整体", "快速场景切换，挑逗氛围定场", "多人镜头，主体优先，关系不混乱"],
	focal_length: ["——", "广角，展现场景与身体全貌", "标准焦段，人物比例自然", "中长焦，人像压缩稳定", "长焦，背景柔化，主体突出", "微距材质，服装纹理与皮肤高光清楚", "超广角，强化空间感但控制身体变形", "鱼眼镜头，梦幻扭曲效果"],
	color_tone: ["——", "低饱和冷灰，情绪克制", "黑金商业调，质感高级", "酒红暗调，复古私密", "青橙电影色调，冷暖对比", "玫瑰粉调，柔和但不过度单色", "奶油暖白，肤色干净", "冷蓝霓虹，夜景湿润", "炽热红色调，感官主导", "冷艳紫色调，私密氛围", "高饱和感官色调，鲜艳对比", "暗调禁忌感，深色渲染", "粉红柔情色调，柔和渐变", "深红挑逗调，浓烈感官", "金色调，奢华私密感"],
	visual_style: ["——", "高端时尚编辑肖像", "时尚编辑商业广告", "私房写真", "商业摄影", "电影剧照感", "写实真人质感", "港式武侠胶片", "港风胶片", "日韩影像", "日系电影感", "东方赛博武侠朋克", "古风电影氛围", "复古禁忌风，柔和颗粒感", "时尚挑逗风，杂志质感", "超现实私密，梦幻扭曲", "艺术情欲风，抽象光影"],
	effect: ["——", "水汽雾化，柔化背景边缘", "镜面反射，扩展空间但不复制主体", "皮肤高光，真实油润但不过曝", "背景虚化，主体第一视觉中心", "光晕绽放，边缘柔和", "胶片颗粒，复古质感", "雨滴玻璃，前景有层次但不遮脸", "快速模糊转场，节奏峰值", "色彩渐变，色调动态过渡", "水滴效果，强调湿润氛围", "烟雾弥漫，增添神秘氛围"],
	filter: ["——", "柔光滤镜，肌肤光滑细腻", "高对比滤镜，强化光影", "暖色胶片滤镜，肤色温润", "冷色电影滤镜，夜景清透", "颗粒滤镜，复古质感", "黑金商业滤镜，质感统一", "青橙电影滤镜，冷暖分层", "暖色滤镜，增强私密氛围", "冷色滤镜，营造禁忌感", "模糊边缘滤镜，突出主体关系"],
	random_mode: ["关闭", "场景随机", "动作随机", "全部随机"],
	preset: ["——", "经典情色", "野外激情", "浴室诱惑", "办公室秘密", "车内激情", "落地窗微醺", "黑金棚拍", "古风薄纱", "赛博夜色", "温泉雾气", "高强度成人氛围"],
	quality_tier: ["标准", "高质量", "超高质量", "大师级", "商业成片", "电影精修", "成人氛围增强"],
};
const NSFW_WORKSPACE_PRESETS = {
	经典情色: { scene: "豪华卧室，红色丝绒床单，镜面天花板", action: "男女深吻，镜前亲密拥抱，眼神交流", outfit: "蕾丝内衣套装，轮廓精致，材质层次清楚", mood: "克制诱惑，眼神清醒，情绪含蓄", lens_type: "全景全身，人物完整入镜", visual_style: "高端时尚编辑肖像" },
	野外激情: { scene: "湖畔夜雾，冷色月光，远处树影", action: "扶栏远望，侧脸受光，衣摆被风带起", outfit: "透明薄纱披肩，轻薄覆盖，肩颈线条可读", mood: "浪漫沉浸，柔光包裹，人物安静", visual_style: "电影剧照感" },
	浴室诱惑: { scene: "浴后蒸汽浴室，雾化玻璃，温暖顶光", action: "浴后擦发，水汽环绕，身体重心稳定", outfit: "浴巾裹身，湿发贴肩，柔光皮肤质感", mood: "私密微醺，嘴角微扬，氛围松弛", visual_style: "私房写真" },
	办公室秘密: { scene: "高层办公室，玻璃幕墙，城市夜景", action: "整理肩带与衣领，表情克制，动作含蓄", outfit: "衬衫半解领口，布料褶皱真实，身体轮廓自然", mood: "危险感，暗调对比，姿态紧绷但自然", visual_style: "商业摄影" },
	车内激情: { scene: "雨夜车窗，皮质座椅，玻璃水痕", action: "端起酒杯轻靠吧台，眼神微醺，肩线清晰", outfit: "黑色缎面礼服，低调光泽，高级剪裁", mood: "雨夜孤独，反光湿润，情绪内收", visual_style: "港风胶片" },
	落地窗微醺: { scene: "卧室落地窗夜景，柔纱窗帘，城市灯火", action: "倚靠窗边回眸，肩颈放松，指尖扶帘", outfit: "丝质睡袍，腰带松弛，袖口自然垂落", mood: "私密微醺，嘴角微扬，氛围松弛", visual_style: "私房写真" },
	黑金棚拍: { scene: "影棚纯色背景，柔光箱，干净地台", action: "镜头前轻转身体，服装轮廓和材质完整展示", outfit: "皮质束腰，金属扣件，结构感明确", mood: "高级性感，商业大片质感，主体完成度高", visual_style: "时尚编辑商业广告" },
	古风薄纱: { scene: "古典月下庭院，回廊灯笼，石阶留白", action: "慢步转身，衣料有动态，脚步落点清楚", outfit: "汉服薄纱外搭，内外层次分明，衣摆流动", mood: "清冷疏离，低饱和情绪，动作克制", visual_style: "古风电影氛围" },
	赛博夜色: { scene: "赛博街区，霓虹雨夜，潮湿路面", action: "手持外套搭在肩上，姿态自信，视线看向镜头", outfit: "Lookbook贴身套装，版型明确，商业成片感", mood: "冷艳自持，视线稳定，表情锋利", visual_style: "东方赛博武侠朋克" },
	温泉雾气: { scene: "私人温泉，岩石池沿，月色水汽", action: "侧卧回望，前景不过度遮挡，脸部清晰", outfit: "浴巾裹身，湿发贴肩，柔光皮肤质感", mood: "温柔暧昧，面部柔和，情绪细腻", visual_style: "日系电影感" },
	高强度成人氛围: { scene: "精品酒店套房，暖色壁灯，落地窗夜景", action: "强成人氛围姿态，身体贴近，表情成熟克制", outfit: "低遮挡内衣风，贴身材质，轮廓关系清楚", mood: "高强度成人氛围，成熟诱惑，镜头克制不直白", anatomy_terms: "乳房、乳头、外阴、阴道、阴蒂", explicit_terms: "性交、插入、自慰、潮吹", adult_action_style: "双人亲密互动，动作连续，镜头克制不直白", camera_angle: "眼平视角，人物关系稳定", light_source: "暖色台灯，局部照亮面部", light_type: "低调光，保留暗部细节", lens_type: "全景全身，人物完整入镜", visual_style: "私房写真", effect: "皮肤高光，真实油润但不过曝", filter: "暖色胶片滤镜，肤色温润" },
};
const NSFW_QUALITY_TAGS = {
	标准: ["detailed", "high quality", "clean composition"],
	高质量: ["masterpiece", "best quality", "ultra-detailed", "high resolution", "clean focus hierarchy", "人物完成度高"],
	超高质量: ["masterpiece", "best quality", "ultra-detailed", "extremely detailed", "8k", "photorealistic", "广告成片质感", "皮肤与材质纹理真实"],
	大师级: ["masterpiece", "best quality", "ultra-detailed", "extremely detailed", "8k", "4k", "photorealistic", "professional photography", "studio lighting", "perfect anatomy", "高光过渡柔和", "手部结构自然", "主体边缘干净"],
	商业成片: ["commercial editorial finish", "professional photography", "clean skin texture", "controlled background detail", "fashion campaign lighting", "人物视觉重心清晰", "服装材质层次清楚"],
	电影精修: ["cinematic color grading", "controlled contrast", "soft edge light", "realistic skin texture", "coherent spatial depth", "电影剧照完成度", "前中后景层次清楚"],
	成人氛围增强: ["mature boudoir atmosphere", "intimate editorial lighting", "controlled sensual mood", "clean full-body framing", "stable anatomy", "mature subject clarity", "低遮挡但构图完整", "成熟私密氛围", "脸部与身体关系清晰"],
};
const NSFW_WORKSPACE_FIELD_SECTIONS = [
	{
		key: "structure",
		label: "结构",
		description: "触发词、场景、动作、服装、情绪、器官词、露骨词和成人动作先定下来。",
		fields: ["trigger_words", "scene", "action", "outfit", "mood", "anatomy_terms", "explicit_terms", "adult_action_style", "preset", "quality_tier", "random_mode"],
	},
	{
		key: "selector",
		label: "选择器",
		description: "内嵌外部 PromptSelector 的常用入口，写回后会进入全局标签、Skill 和模型上下文。",
		fields: ["selector_character", "selector_outfit", "selector_action", "selector_scene", "selector_expression", "selector_prop"],
	},
	{
		key: "camera",
		label: "镜头",
		description: "镜头、景别、光源、风格与滤镜分开调。",
		fields: ["camera_movement", "camera_angle", "light_source", "light_type", "lens_type", "focal_length", "color_tone", "visual_style", "effect", "filter"],
	},
	{
		key: "negative",
		label: "负面",
		description: "负面预设与自定义负面词在这里显式切换。",
		fields: ["negative_preset", "negative_apply_mode", "custom_negative", "custom_prefix", "custom_suffix"],
	},
];
const NSFW_WORKSPACE_FIELD_LABELS = {
	trigger_words: "触发词",
	selector_character: "角色/数量",
	selector_outfit: "服饰状态",
	selector_action: "动作关系",
	selector_scene: "场景入口",
	selector_expression: "表情状态",
	selector_prop: "道具元素",
	scene: "场景",
	action: "动作",
	outfit: "服饰",
	mood: "情绪",
	anatomy_terms: "器官词",
	explicit_terms: "露骨词",
	adult_action_style: "成人动作",
	camera_movement: "运镜",
	camera_angle: "机位",
	light_source: "光源",
	light_type: "光型",
	lens_type: "镜头类型",
	focal_length: "焦段",
	color_tone: "色调",
	visual_style: "视觉风格",
	effect: "效果",
	filter: "滤镜",
	random_mode: "随机模式",
	preset: "预设",
	quality_tier: "质量档位",
	negative_preset: "负面预设",
	negative_apply_mode: "应用方式",
	custom_negative: "自定义负面词",
	custom_prefix: "额外前缀",
	custom_suffix: "额外后缀",
};
const NSFW_CUSTOM_FIELD_LIBRARY_FIELDS = [
	"selector_character",
	"selector_outfit",
	"selector_action",
	"selector_scene",
	"selector_expression",
	"selector_prop",
	"scene",
	"action",
	"outfit",
	"mood",
	"anatomy_terms",
	"explicit_terms",
	"adult_action_style",
	"camera_movement",
	"camera_angle",
	"light_source",
	"light_type",
	"lens_type",
	"focal_length",
	"color_tone",
	"visual_style",
	"effect",
	"filter",
];
const SAFE_PROFILE_WIDE_TAGS = new Set(["大全景", "大远景", "远景", "全景", "全景全身", "全身"]);
const SAFE_PROFILE_LENS_TAGS = new Set(["长焦", "标准镜头", "50mm标准镜头", "85mm人像镜头", "定焦"]);
const SAFE_PROFILE_SOFT_LIGHT_TAGS = new Set(["柔光", "自然光", "漫射光", "侧光", "柔和逆光"]);
const SAFE_PROFILE_TEXT_SUPPRESSION_TAGS = ["无文字", "无水印", "无logo", "无边框"];
const SAFE_PROFILE_TECH_TAG = "高光过渡柔和";
const SAFE_PROFILE_PORTRAIT_TAG = "面部聚焦";
const RANDOM_OPTIMIZE_GUARD_TAGS = ["面部聚焦", "高光过渡柔和", "无文字", "无水印", "无logo", "主体突出"];
const RANDOM_OPTIMIZE_EXCLUDE_TAGS = ["双人", "少女", "儿童", "Q版"];
const RANDOM_COMBO_IDENTITY_GROUP_NAME = "主体";
const RANDOM_COMBO_SCENE_GROUP_NAME = "场景背景";
const RANDOM_COMBO_IDENTITY_SECTION_NAMES = ["特殊身份", "奇幻角色", "现代人物"];
const RANDOM_COMBO_SCENE_EXCLUDE_TAGS = new Set(["白色背景", "纯色背景"]);
const STAGE_EMBEDDED_LOCAL_MODEL_WIDGET_NAMES = ["内置模型系列", "内置主模型", "内置视觉投影mmproj", "内置启用思考", "内置上下文长度", "内置GPU层数", "内置KV缓存K类型", "内置KV缓存V类型"];
const STAGE_EMBEDDED_API_MODEL_WIDGET_NAMES = ["API服务商", "API地址", "API密钥", "API模型", "API超时秒", "API额外请求头"];
const STAGE_EMBEDDED_MODEL_WIDGET_NAMES = ["模型来源", ...STAGE_EMBEDDED_LOCAL_MODEL_WIDGET_NAMES, ...STAGE_EMBEDDED_API_MODEL_WIDGET_NAMES];
const STAGE_EMBEDDED_MODEL_WIDGET_COUNT = STAGE_EMBEDDED_MODEL_WIDGET_NAMES.length;
const MODEL_WIDGET_ALIASES = {
	"模型来源": ["模型来源"],
	"模型系列": ["模型系列", "内置模型系列"],
	"主模型": ["主模型", "内置主模型"],
	"视觉投影mmproj": ["视觉投影mmproj", "内置视觉投影mmproj"],
	"启用思考": ["启用思考", "内置启用思考"],
	"上下文长度": ["上下文长度", "内置上下文长度"],
	"GPU层数": ["GPU层数", "内置GPU层数"],
	"KV缓存K类型": ["KV缓存K类型", "内置KV缓存K类型"],
	"KV缓存V类型": ["KV缓存V类型", "内置KV缓存V类型"],
	"API服务商": ["API服务商"],
	"API地址": ["API地址"],
	"API密钥": ["API密钥"],
	"API模型": ["API模型"],
	"API超时秒": ["API超时秒"],
	"API额外请求头": ["API额外请求头"],
};
const TAG_BLOCK_COMPOSER_ENABLED_WIDGET_NAME = "标签块编排启用";
const TAG_BLOCK_COMPOSER_JSON_WIDGET_NAME = "标签块编排JSON";
const FIX_UI_WIDGET_NAMES = new Set(["标签", "随机", "随机跑", "匹配", "身景随", "身景跑", "连测轮", "连测随", "停连测", "连测报", "质检", "复制", "负面", "同步负", "诊断", "预设", "联机", "历史", "回退", "槽位", "高级", "自负", "稳妥", "柔肤", "抑字", "清空", "示例", "状态", "摘要"]);
const STAGE_TOP_STATUS_WIDGET_NAMES = new Set(["状态", "摘要"]);
const ALWAYS_HIDDEN_WIDGET_NAMES = [RANDOM_DEDUPE_CACHE_WIDGET_NAME, PROMPT_DEDUPE_CACHE_WIDGET_NAME, RUNTIME_RANDOM_PROTECTED_TAGS_WIDGET_NAME, RUNTIME_RANDOM_PREVIEW_TOKEN_WIDGET_NAME, "智能文本匹配", "智能文本输入", TAG_BLOCK_COMPOSER_ENABLED_WIDGET_NAME, TAG_BLOCK_COMPOSER_JSON_WIDGET_NAME, "图片反推生成", "图片反推模式", "图片反推最大边长", ...STAGE_EMBEDDED_MODEL_WIDGET_NAMES];
const LEGACY_REVERSE_MODE_ALIASES = {
	商业摄影: "自动平衡",
	高密度站点: "自动平衡",
};
const LEGACY_WIDGET_BATCHES = [
	["成人向表达标签1", "成人向表达标签2", "成人向表达标签3"],
	["运行时随机标签", "运行时随机模式"],
	["核心标签锁定数量", "运行时随机强度"],
	["锁定标签白名单", "随机排除标签"],
	[RUNTIME_RANDOM_PROTECTED_TAGS_WIDGET_NAME, RUNTIME_RANDOM_PREVIEW_TOKEN_WIDGET_NAME],
];

const CONTROL_WIDGET_NAMES = [
	"模板风格",
	"运行时随机标签",
	"运行时随机模式",
	"核心标签锁定数量",
	"运行时随机强度",
	"随机主题池",
	"生成数量",
	"提示词语言",
	"详细度",
	"标签反推模式",
	"优先柔和肤质",
	"抑制文字伪影",
];

const ADVANCED_WIDGET_NAMES = [
	"主体类型",
	"案例输出结构",
	"风格隔离策略",
	"输出模式",
	"额外要求",
	"智能文本匹配",
	"智能文本输入",
	"智能文本风格优先",
	"图片反推生成",
	"图片反推模式",
	"图片反推最大边长",
	"锁定标签白名单",
	"随机排除标签",
	"系统提示词覆盖",
	"最大生成token",
	"温度",
	"top_p",
	"top_k",
	"重复惩罚",
	"频率惩罚",
	"存在惩罚",
	"seed",
	"输出think块",
];

const CONTROL_WIDGET_OPTIONS = {
	"模板风格": [
		{ value: "自动", label: "自动" },
		{ value: "真实感", label: "真实" },
		{ value: "商业摄影", label: "商业" },
		{ value: "时尚编辑", label: "时尚" },
		{ value: "电影写实", label: "电影" },
		{ value: "私房写实", label: "私房" },
		{ value: "插画感", label: "插画" },
		{ value: "复古动画", label: "复古" },
		{ value: "CG感", label: "CG" },
		{ value: "东方赛博", label: "东方赛博" },
		{ value: "硬表面科幻", label: "科幻" },
		{ value: "古风", label: "古风" },
		{ value: "国风电影", label: "国风电影" },
		{ value: "武侠电影", label: "武侠" },
		{ value: "神话感", label: "神话" },
		{ value: "暗黑奇幻", label: "暗黑" },
	],
	"运行时随机标签": [
		{ value: false, label: "关" },
		{ value: true, label: "开" },
	],
	"运行时随机模式": [
		{ value: "自动判断", label: "自动判断" },
		{ value: "全随机", label: "全随机" },
		{ value: "保留已选核心标签", label: "保留核心" },
		{ value: "重写主体与场景", label: "重写主线" },
	],
	"运行时随机强度": [
		{ value: "弱", label: "弱" },
		{ value: "中", label: "中" },
		{ value: "强", label: "强" },
		{ value: "强 / 极限拉开", label: "极限拉开", hint: "批量输出时扩大主体、场景、服装、动作和光影差异。" },
	],
	"随机主题池": ["自动", "写实生活", "商业摄影", "时尚大片", "糖水写真", "旅行街拍", "海岸假日", "森林自然", "都市职场", "夜场电影感", "私房写实", "运动机能", "古风园林", "武侠江湖", "洛可可宫廷", "神话史诗", "暗黑哥特", "赛博工业", "东方赛博", "机甲科幻", "废土荒原", "复古插画"],
	"生成数量": [1, 2, 3, 4, 5, 8, 12],
	"提示词语言": [
		{ value: "纯中文", label: "中文" },
		{ value: "英文提示词+中文说明", label: "英+中" },
		{ value: "纯英文", label: "英文" },
	],
	"详细度": ["简洁", "标准", "详细"],
	"输出模式": ["完整结果", "仅提示词优先"],
	"标签反推模式": [
		{ value: "自动平衡", label: "平衡", hint: "普通标签收敛：按当前风格和主题自动整理，不主动进入 NSFW 策略。" },
		{ value: "成人向成熟", label: "成人策略", hint: "开启成人向策略：联动 NSFW 标签识别、成熟主体锚点、负面词与模型上下文。" },
	],
	"核心标签锁定数量": [0, 5, 10, 20, 30, 50, 75, 100, 150, 200, 300, 500],
	"优先柔和肤质": [
		{ value: false, label: "柔肤关" },
		{ value: true, label: "柔肤开" },
	],
	"抑制文字伪影": [
		{ value: false, label: "抑字关" },
		{ value: true, label: "抑字开" },
	],
	"智能文本匹配": [
		{ value: false, label: "关闭" },
		{ value: true, label: "启用" },
	],
	"智能文本风格优先": [
		{ value: "自动判断", label: "自动判断" },
		{ value: "节点优先", label: "节点优先" },
		{ value: "文本优先", label: "文本优先" },
	],
	"风格隔离策略": [
		{ value: "平衡收敛", label: "平衡收敛", hint: "保留当前风格主线，同时清理明显冲突的媒介标签。" },
		{ value: "严格风格隔离", label: "严格隔离", hint: "优先清除跨媒介、跨时代和跨风格污染。" },
		{ value: "允许风格漂移", label: "允许漂移", hint: "保留更多混合风格素材，适合实验性输出。" },
	],
	"图片反推生成": [
		{ value: false, label: "关闭" },
		{ value: true, label: "启用" },
	],
	"图片反推模式": ["角色设定图", "仅反推描述"],
	"图片反推最大边长": [640, 768, 960, 1280],
	"输出think块": [
		{ value: false, label: "关闭" },
		{ value: true, label: "输出" },
	],
	"最大生成token": [1280, 1800, 2200, 3072],
	"温度": [0.45, 0.62, 0.8, 1.0],
	"top_p": [0.85, 0.9, 0.95, 1.0],
	"top_k": [20, 40, 80, 120],
	"重复惩罚": [1.0, 1.08, 1.15, 1.25],
};
const ADVANCED_PANEL_SECTIONS = [
	{
		title: "生成策略",
		desc: "决定输出风格、语言和反推方式。",
		rows: ["模板风格", "主体类型", "案例输出结构", "风格隔离策略", "提示词语言", "详细度", "输出模式", "标签反推模式", "生成数量", "优先柔和肤质", "抑制文字伪影"],
	},
	{
		title: "随机控制",
		desc: "控制随机标签、主题池和锁定策略。",
		rows: ["运行时随机标签", "运行时随机模式", "核心标签锁定数量", "运行时随机强度", "随机主题池", "锁定标签白名单", "随机排除标签"],
	},
	{
		title: "智能文本",
		desc: "把用户描述或参考图反推送入匹配与模型润色链路。",
		rows: ["智能文本匹配", "智能文本输入", "智能文本风格优先", "图片反推生成", "图片反推模式", "图片反推最大边长", "额外要求"],
	},
	{
		title: "模型采样",
		desc: "少量保留专家采样参数，默认不用频繁调整。",
		rows: ["最大生成token", "温度", "top_p", "top_k", "重复惩罚", "频率惩罚", "存在惩罚", "seed", "输出think块", "系统提示词覆盖"],
	},
];
const MODEL_FAMILY_BUTTONS = [
	{ value: "Qwen3.5-VL", label: "Qwen3.5", hint: "Qwen VL 主力" },
	{ value: "Qwen3-VL", label: "Qwen3", hint: "Qwen3 视觉" },
	{ value: "Gemma4", label: "Gemma4", hint: "Gemma 多模态/文本" },
	{ value: "Llama", label: "Llama", hint: "通用 Llama GGUF" },
	{ value: "Mistral", label: "Mistral", hint: "Mistral Instruct" },
	{ value: "DeepSeek", label: "DeepSeek", hint: "DeepSeek GGUF" },
	{ value: "通用GGUF", label: "通用", hint: "自动推断格式" },
];
const MODEL_CONTEXT_BUTTONS = [4096, 8192, 16384, 32768];
const MODEL_GPU_BUTTONS = [
	{ value: -1, label: "自动GPU" },
	{ value: 0, label: "CPU" },
	{ value: 99, label: "99层" },
];
const MODEL_KV_BUTTONS = [
	{ value: "默认(F16)", label: "F16" },
	{ value: "q8_0", label: "Q8" },
];
const MODEL_SOURCE_BUTTONS = [
	{ value: "仅Skill", label: "Skill", hint: "离线规则模式：只用节点内 Skill、标签库和模板，不联网、不调用模型。" },
	{ value: "本地模型", label: "本地", hint: "本地模型模式：可连接任意兼容模型对象；未连接时从 ComfyUI/models/LLM 加载内置 GGUF。" },
	{ value: "API接口", label: "API", hint: "API 模式：用下方服务商、Key 和模型名调用云端、Ollama、LM Studio 或其他兼容接口。" },
];

function normalizeModelSourceValue(value) {
	const source = String(value ?? "").trim() || "仅Skill";
	return source === "本地GGUF" ? "本地模型" : source;
}
const MODEL_API_PROVIDER_BUTTONS = [
	{ value: "OpenAI兼容", label: "兼容", baseUrl: "", model: "", keyRef: "", hint: "自定义 OpenAI 兼容接口：填写 Base URL、Key 和模型名。" },
	{ value: "OpenAI", label: "OpenAI", baseUrl: "https://api.openai.com/v1", model: "gpt-4o-mini", keyRef: "env:OPENAI_API_KEY" },
	{ value: "OpenRouter", label: "Router", baseUrl: "https://openrouter.ai/api/v1", model: "openai/gpt-4o-mini", keyRef: "env:OPENROUTER_API_KEY" },
	{ value: "DeepSeek", label: "DeepSeek", baseUrl: "https://api.deepseek.com", model: "deepseek-v4-flash", keyRef: "env:DEEPSEEK_API_KEY" },
	{ value: "通义千问DashScope", label: "通义", baseUrl: "https://dashscope.aliyuncs.com/compatible-mode/v1", model: "qwen-plus", keyRef: "env:DASHSCOPE_API_KEY" },
	{ value: "Kimi", label: "Kimi", baseUrl: "https://api.moonshot.cn/v1", model: "moonshot-v1-8k", keyRef: "env:MOONSHOT_API_KEY" },
	{ value: "SiliconFlow", label: "硅基", baseUrl: "https://api.siliconflow.cn/v1", model: "", keyRef: "env:SILICONFLOW_API_KEY" },
	{ value: "火山方舟", label: "方舟", baseUrl: "https://ark.cn-beijing.volces.com/api/v3", model: "", keyRef: "env:ARK_API_KEY" },
	{ value: "智谱GLM", label: "智谱", baseUrl: "https://open.bigmodel.cn/api/paas/v4", model: "glm-4.5", keyRef: "env:ZHIPUAI_API_KEY" },
	{ value: "Groq", label: "Groq", baseUrl: "https://api.groq.com/openai/v1", model: "openai/gpt-oss-20b", keyRef: "env:GROQ_API_KEY" },
	{ value: "Together", label: "Together", baseUrl: "https://api.together.xyz/v1", model: "", keyRef: "env:TOGETHER_API_KEY" },
	{ value: "Fireworks", label: "Fireworks", baseUrl: "https://api.fireworks.ai/inference/v1", model: "", keyRef: "env:FIREWORKS_API_KEY" },
	{ value: "Mistral", label: "Mistral", baseUrl: "https://api.mistral.ai/v1", model: "mistral-small-latest", keyRef: "env:MISTRAL_API_KEY" },
	{ value: "Perplexity", label: "PPLX", baseUrl: "https://api.perplexity.ai", model: "sonar", keyRef: "env:PPLX_API_KEY" },
	{ value: "Gemini OpenAI兼容", label: "Gemini兼容", baseUrl: "https://generativelanguage.googleapis.com/v1beta/openai", model: "gemini-2.5-flash", keyRef: "env:GEMINI_API_KEY" },
	{ value: "Claude Anthropic", label: "Claude", baseUrl: "https://api.anthropic.com/v1/messages", model: "claude-haiku-4-5", keyRef: "env:ANTHROPIC_API_KEY" },
	{ value: "Gemini 原生", label: "Gemini", baseUrl: "https://generativelanguage.googleapis.com/v1beta", model: "gemini-2.5-flash", keyRef: "env:GEMINI_API_KEY" },
	{ value: "Ollama本地", label: "Ollama", baseUrl: "http://127.0.0.1:11434/v1", model: "qwen2.5", keyRef: "" },
	{ value: "LM Studio本地", label: "LMStudio", baseUrl: "http://127.0.0.1:1234/v1", model: "", keyRef: "" },
	{ value: "自定义", label: "自定义", baseUrl: "", model: "", keyRef: "", hint: "完全自定义：手动填写兼容接口地址、Key、模型名和额外请求头。" },
];
const MODEL_API_PROVIDER_VALUES = new Set(MODEL_API_PROVIDER_BUTTONS.map((item) => item.value));
const MODEL_API_PROVIDER_HOST_HINTS = [
	{ token: "api.openai.com", label: "OpenAI" },
	{ token: "openrouter.ai", label: "OpenRouter" },
	{ token: "api.deepseek.com", label: "DeepSeek" },
	{ token: "dashscope.aliyuncs.com", label: "通义千问DashScope" },
	{ token: "api.moonshot.cn", label: "Kimi" },
	{ token: "api.siliconflow.cn", label: "SiliconFlow" },
	{ token: "volces.com", label: "火山方舟" },
	{ token: "open.bigmodel.cn", label: "智谱GLM" },
	{ token: "api.groq.com", label: "Groq" },
	{ token: "api.together.xyz", label: "Together" },
	{ token: "api.fireworks.ai", label: "Fireworks" },
	{ token: "api.mistral.ai", label: "Mistral" },
	{ token: "api.perplexity.ai", label: "Perplexity" },
	{ token: "generativelanguage.googleapis.com/v1beta/openai", label: "Gemini OpenAI兼容" },
	{ token: "anthropic.com", label: "Claude Anthropic" },
	{ token: "generativelanguage.googleapis.com", label: "Gemini 原生" },
	{ token: "127.0.0.1:11434", label: "Ollama本地" },
	{ token: "localhost:11434", label: "Ollama本地" },
	{ token: "127.0.0.1:1234", label: "LM Studio本地" },
	{ token: "localhost:1234", label: "LM Studio本地" },
];
const MODEL_API_STALE_MODEL_VALUES = new Set([
	"自动",
	"人物角色",
	"非人物主体",
	"案例长段版",
	"案例分段版",
	"全随机",
	"保留已选核心标签",
	"重写主体与场景",
	"纯中文",
	"英文提示词+中文说明",
	"纯英文",
	"简洁",
	"标准",
	"详细",
	"完整结果",
	"正向提示词",
	"标签集合",
	"JSON",
	"自动平衡",
	"成人向成熟",
	"平衡收敛",
	"严格隔离",
	"允许漂移",
	"节点优先",
	"文本优先",
	"角色设定图",
	"单图反推",
	"仅提示词",
]);

const PRESET_SETTING_NAMES = [
	"模板风格",
	"主体类型",
	"案例输出结构",
	"运行时随机标签",
	"运行时随机模式",
	"核心标签锁定数量",
	"运行时随机强度",
	"随机主题池",
	"锁定标签白名单",
	"随机排除标签",
	"生成数量",
	"提示词语言",
	"详细度",
	"输出模式",
	"标签反推模式",
	"风格隔离策略",
	"优先柔和肤质",
	"抑制文字伪影",
	"智能文本匹配",
	"智能文本输入",
	"智能文本风格优先",
	TAG_BLOCK_COMPOSER_ENABLED_WIDGET_NAME,
	TAG_BLOCK_COMPOSER_JSON_WIDGET_NAME,
	"图片反推生成",
	"图片反推模式",
	"图片反推最大边长",
	"模型来源",
	"内置模型系列",
	"内置主模型",
	"内置视觉投影mmproj",
	"内置启用思考",
	"内置上下文长度",
	"内置GPU层数",
	"内置KV缓存K类型",
	"内置KV缓存V类型",
	"API服务商",
	"API地址",
	"API模型",
	"API超时秒",
	"额外要求",
	"系统提示词覆盖",
	"最大生成token",
	"温度",
	"top_p",
	"top_k",
	"重复惩罚",
	"频率惩罚",
	"存在惩罚",
	"seed",
	"输出think块",
	RUNTIME_RANDOM_PROTECTED_TAGS_WIDGET_NAME,
];

const PRESET_SETTING_DEFAULTS = {
	"模板风格": "自动",
	"主体类型": "自动",
	"案例输出结构": "自动",
	"运行时随机标签": false,
	"运行时随机模式": "自动判断",
	"核心标签锁定数量": 10,
	"运行时随机强度": "中",
	"随机主题池": "自动",
	"锁定标签白名单": "",
	"随机排除标签": "",
	"生成数量": 3,
	"提示词语言": "纯中文",
	"详细度": "标准",
	"输出模式": "完整结果",
	"标签反推模式": "自动平衡",
	"风格隔离策略": "平衡收敛",
	"优先柔和肤质": false,
	"抑制文字伪影": false,
	"智能文本匹配": false,
	"智能文本输入": "",
	"智能文本风格优先": "自动判断",
	[TAG_BLOCK_COMPOSER_ENABLED_WIDGET_NAME]: false,
	[TAG_BLOCK_COMPOSER_JSON_WIDGET_NAME]: "",
	"图片反推生成": false,
	"图片反推模式": "角色设定图",
	"图片反推最大边长": 960,
	"模型来源": "仅Skill",
	"内置模型系列": "Qwen3.5-VL",
	"内置主模型": "",
	"内置视觉投影mmproj": "无",
	"内置启用思考": false,
	"内置上下文长度": 8192,
	"内置GPU层数": -1,
	"内置KV缓存K类型": "默认(F16)",
	"内置KV缓存V类型": "默认(F16)",
	"API服务商": "OpenAI兼容",
	"API地址": "",
	"API模型": "",
	"API超时秒": 120,
	"额外要求": "",
	"系统提示词覆盖": "",
	"最大生成token": 1800,
	"温度": 0.62,
	"top_p": 0.9,
	"top_k": 40,
	"重复惩罚": 1.08,
	"频率惩罚": 0,
	"存在惩罚": 0,
	"seed": 0,
	"输出think块": false,
	[RUNTIME_RANDOM_PROTECTED_TAGS_WIDGET_NAME]: "",
};
const CLEAR_PROMPT_INPUT_WIDGET_NAMES = ["额外要求", "智能文本输入", TAG_BLOCK_COMPOSER_JSON_WIDGET_NAME];

const QUICK_THEME_POOL_CARDS = [
	{ value: "自动", label: "自动", caption: "跟随当前标签", glow: "rgba(123,161,210,.18)", border: "rgba(96,122,158,.72)", hint: "回到自动主题池，让现有标签和随机逻辑自己决定发散方向。" },
	{ value: "商业摄影", label: "商业", caption: "白棚品牌片", glow: "rgba(218,186,124,.20)", border: "rgba(182,145,84,.74)", hint: "偏向白棚、品牌大片、Lookbook 和商业广告质感。" },
	{ value: "时尚大片", label: "时尚", caption: "杂志封面", glow: "rgba(211,141,150,.20)", border: "rgba(179,104,116,.74)", hint: "偏向杂志编辑摄影、封面肖像、高定礼服和时装片。" },
	{ value: "糖水写真", label: "糖水", caption: "奶油柔光", glow: "rgba(226,161,183,.22)", border: "rgba(196,137,160,.74)", hint: "偏向樱花、柔光、奶油和糖水写真语义。" },
	{ value: "海岸假日", label: "海岸", caption: "海风日落", glow: "rgba(101,173,202,.19)", border: "rgba(81,139,166,.74)", hint: "偏向海边、栈道、礁石、日落逆光和度假广告。" },
	{ value: "神话史诗", label: "神话", caption: "云海神殿", glow: "rgba(214,180,108,.22)", border: "rgba(182,144,85,.74)", hint: "偏向云海、神殿、祭坛和史诗神性方向。" },
	{ value: "赛博工业", label: "赛博", caption: "机库金属", glow: "rgba(92,194,214,.20)", border: "rgba(74,147,162,.74)", hint: "偏向机库、工业结构、金属和未来都市方向。" },
	{ value: "机甲科幻", label: "机甲", caption: "整备机库", glow: "rgba(104,154,221,.20)", border: "rgba(81,122,181,.74)", hint: "偏向机甲设定、实验室、飞船走廊和硬表面科幻。" },
	{ value: "古风园林", label: "古风", caption: "园林月洞门", glow: "rgba(115,171,128,.19)", border: "rgba(88,142,102,.74)", hint: "偏向园林仕女、月洞门、园林借景和古风柔光。" },
	{ value: "武侠江湖", label: "武侠", caption: "竹林客栈", glow: "rgba(131,176,137,.19)", border: "rgba(97,145,104,.74)", hint: "偏向竹林、客栈、雨夜屋檐、长剑和江湖电影感。" },
	{ value: "都市职场", label: "都市", caption: "杂志职场", glow: "rgba(150,164,214,.20)", border: "rgba(112,127,180,.74)", hint: "偏向办公室、都市职场、杂志感和全身构图。" },
];
const QUICK_THEME_POOL_CARD_VALUES = new Set(QUICK_THEME_POOL_CARDS.map((item) => item.value));
const NSFW_GENERATION_PROFILE = {
	templateStyle: "真实感",
	subjectType: "人物角色",
	reverseMode: "成人向成熟",
};
const NSFW_GENERATION_PROFILE_SETTING_NAMES = ["模板风格", "主体类型", "标签反推模式", "优先柔和肤质", "抑制文字伪影"];

const CASE_PRESETS = [
	{ name: "糖水片成年写真", description: "参考糖水片模板，保留甜美、浅景深与梦幻光斑，但明确是成年写真，默认全身比例。", settings: { "模板风格": "真实感", "主体类型": "人物角色", "案例输出结构": "案例长段版", "提示词语言": "纯中文", "详细度": "详细", "输出模式": "完整结果" }, tags: ["成年女性", "东亚", "甜美", "灵动", "真实感", "糖水片", "CCD感", "奶油针织", "白衬衫", "樱花树下", "柔光", "暖色调", "治愈", "全景全身", "50mm标准镜头", "中心构图", "浅景深", "光斑", "冷白皮", "清透肌肤", "成年大学生气质", "无幼态感", "8K"] },
	{ name: "高质感时尚写真", description: "质感优先模板：强调自然皮肤纹理、干净背景、全身比例与电影级轮廓光。建议采样参数：DPM++ 2M Karras / 28-36 steps / CFG 4.5-6；二次放大 denoise 0.22-0.35。", settings: { "模板风格": "真实感", "主体类型": "人物角色", "案例输出结构": "案例长段版", "提示词语言": "纯中文", "详细度": "详细", "输出模式": "完整结果" }, tags: ["成年女性", "东亚", "优雅", "真实感", "时尚写真", "杂志感", "电影感", "自然光", "柔光", "轮廓光", "全景全身", "平视", "浅景深", "皮肤纹理", "清透肌肤", "景深层次自然", "主体突出", "材质细节丰富", "高细节", "8K"] },
	{ name: "在当前标签上优化", description: "原“图集收敛一键生”。给你这类随机图准备的一键收敛版：优先单人成人、全身比例、银白金属与宝石晶体饰品、高定礼装或轻科幻棚拍气质，默认压多人复制、裸露漂移、服装崩坏和背景乱跳。这个预设会保留当前已选标签和自定义标签，再叠加优化约束；如果运行时随机开启，会默认按“全随机 + 护栏白名单/排除集”工作。建议采样参数：DPM++ 2M Karras / 28-34 steps / CFG 4.5-6。", mergeWithCurrent: true, mergeExtraRequirement: true, preserveCustomTagsForRandom: true, randomWhitelistTags: RANDOM_OPTIMIZE_GUARD_TAGS, randomExcludeTags: RANDOM_OPTIMIZE_EXCLUDE_TAGS, settings: { "模板风格": "真实感", "主体类型": "人物角色", "案例输出结构": "案例长段版", "运行时随机标签": true, "运行时随机模式": "全随机", "运行时随机强度": "中", "提示词语言": "纯中文", "详细度": "详细", "输出模式": "完整结果", "优先柔和肤质": true, "抑制文字伪影": true, "额外要求": "默认保持单人成人全身写真，脸部清晰但不压过头身比例；优先银白金属、宝石、晶体、精致配饰与高定礼装质感；背景只允许都市街头、摄影棚或科幻室内三类干净场景之一，不要混入多个主场景；严格禁止多人复制、裸露漂移、服装结构崩坏、手部畸形、未成年感、二次元幼态和杂乱道具喧宾夺主。" }, tags: ["成年女性", "东亚", "优雅", "真实感", "时尚写真", "杂志感", "电影感", "全景全身", "平视", "50mm标准镜头", "浅景深", "人物完整入镜", "柔光", "轮廓光", "清透肌肤", "空气感奶油肌", "高光过渡柔和", "主体突出", "材质细节丰富", "高细节", "银白金属", "宝石配饰", "晶体装饰", "高定礼装", "轻科幻棚拍", "无文字", "无水印", "无logo"] },
	{ name: "中画幅通勤大片", description: "写实高价值小预设：直接走中画幅、品牌大片、Lookbook 和都市纪实轨道，默认就是高级通勤全身广告片逻辑。建议采样参数：DPM++ 2M Karras / 28-34 steps / CFG 4.5-6。", settings: { "模板风格": "真实感", "主体类型": "人物角色", "案例输出结构": "案例长段版", "提示词语言": "纯中文", "详细度": "详细", "输出模式": "完整结果", "优先柔和肤质": true, "抑制文字伪影": true }, tags: ["成年女性", "东亚", "真实感", "中画幅", "品牌大片", "Lookbook", "生活方式广告", "都市纪实", "白衬衫", "长款大衣", "街道", "阴天自然光", "全景全身", "50mm标准镜头", "电影调色", "肤色校正自然", "服装褶皱真实"] },
	{ name: "城市天台晚风纪实", description: "参考角色案例里的高完成度写实方向：城市天台、日落逆光、风吹发丝与侧脸留白，适合做自然纪实感年轻人像。", settings: { "模板风格": "真实感", "主体类型": "人物角色", "案例输出结构": "案例长段版", "提示词语言": "纯中文", "详细度": "详细", "输出模式": "完整结果", "优先柔和肤质": true, "抑制文字伪影": true }, tags: ["成年女性", "东亚", "真实感", "城市屋顶纪实", "晚风纪实", "城市天台", "屋顶晾衣架", "有线耳机", "黑长直", "日落逆光", "晚风感", "侧脸构图", "负空间留白", "背景轻微虚化", "发丝迎风清晰", "侧脸轮廓清晰", "生活电影感"] },
	{ name: "随机主题池·糖水写真", description: "给随机模式加一个明确偏向：更容易往樱花、柔光、奶油与糖水写真方向发散，同时默认保持全身比例。", settings: { "模板风格": "自动", "主体类型": "人物角色", "案例输出结构": "案例长段版", "运行时随机标签": true, "运行时随机模式": "全随机", "运行时随机强度": "中", "随机主题池": "糖水写真", "提示词语言": "纯中文", "详细度": "详细", "输出模式": "完整结果" }, tags: ["成年女性", "东亚", "全景全身", "人物完整入镜", "柔光"] },
	{ name: "随机主题池·神话史诗", description: "随机时优先云海、神殿、祭坛与神性服装语义，并默认保持全身史诗尺度。", settings: { "模板风格": "自动", "主体类型": "人物角色", "案例输出结构": "案例长段版", "运行时随机标签": true, "运行时随机模式": "全随机", "运行时随机强度": "中", "随机主题池": "神话史诗", "提示词语言": "纯中文", "详细度": "详细", "输出模式": "完整结果" }, tags: ["成年女性", "东亚", "史诗感", "体积光", "全景全身"] },
	{ name: "随机主题池·赛博工业", description: "随机时偏向机库、工业、未来都市与金属结构，避免一直在写实粉色职场里打转。", settings: { "模板风格": "自动", "主体类型": "人物角色", "案例输出结构": "案例长段版", "运行时随机标签": true, "运行时随机模式": "全随机", "运行时随机强度": "中", "随机主题池": "赛博工业", "提示词语言": "纯中文", "详细度": "详细", "输出模式": "完整结果" }, tags: ["成年女性", "东亚", "CG感", "低角度", "高细节"] },
	{ name: "海边轻熟写实", description: "推荐稳定版：轻熟女性写实海边全身写真，优先头身比例、发丝、礼服轮廓和海边留白。", settings: { "模板风格": "真实感", "主体类型": "人物角色", "案例输出结构": "案例长段版", "提示词语言": "纯中文", "详细度": "详细", "输出模式": "完整结果", "优先柔和肤质": true, "抑制文字伪影": true, "额外要求": "优先保持单一主场景为海边黄昏，不要再混入酒吧或卧室；默认全身入镜，脸部清晰但不压过头身比例，脚部和高跟鞋保持自然透视。" }, tags: ["成年女性", "东亚", "调酒师", "轻熟感", "真实感", "海边", "黄昏", "冷白皮", "清透肌肤", "空气感奶油肌", "黑长直", "银色耳饰", "深灰丝绒礼服", "全景全身", "50mm标准镜头", "三分法", "电影调色", "低饱和", "主体突出", "服装褶皱真实"] },
	{ name: "海边轻熟写实·近景", description: "海边轻熟写实的近景版：强化脸部、发丝、肩颈与丝绒礼服的杂志级肖像关系。", settings: { "模板风格": "真实感", "主体类型": "人物角色", "案例输出结构": "案例长段版", "提示词语言": "纯中文", "详细度": "详细", "输出模式": "完整结果", "优先柔和肤质": true, "抑制文字伪影": true, "额外要求": "优先保持海边黄昏近景女性肖像，脸部作为第一视觉中心，只保留肩颈与礼服上半身，不允许脚部或鞋跟进入前景。" }, tags: ["成年女性", "东亚", "调酒师", "轻熟感", "真实感", "海边", "黄昏", "冷白皮", "清透肌肤", "空气感奶油肌", "黑长直", "银色耳饰", "深灰丝绒礼服", "近景", "85mm人像镜头", "三分法", "电影调色", "低饱和", "主体突出"] },
	{ name: "海边轻熟写实·中景", description: "海边轻熟写实的中景版：保留脸部、肩颈、腰线和礼服轮廓，让海面退成干净背景。", settings: { "模板风格": "真实感", "主体类型": "人物角色", "案例输出结构": "案例长段版", "提示词语言": "纯中文", "详细度": "详细", "输出模式": "完整结果", "优先柔和肤质": true, "抑制文字伪影": true, "额外要求": "优先保持海边黄昏中景人像，保留腰线和礼服轮廓，但脚部、高跟鞋和腿部只能退到边缘，不允许前景畸变。" }, tags: ["成年女性", "东亚", "调酒师", "轻熟感", "真实感", "海边", "黄昏", "冷白皮", "清透肌肤", "空气感奶油肌", "黑长直", "银色耳饰", "深灰丝绒礼服", "中景半身", "85mm人像镜头", "三分法", "电影调色", "低饱和", "主体突出", "服装褶皱真实"] },
	{ name: "海边轻熟写实·全身", description: "海边轻熟写实的全身版：稳定全身比例、礼服轮廓和海边留白，不让局部身体顶前景。", settings: { "模板风格": "真实感", "主体类型": "人物角色", "案例输出结构": "案例长段版", "提示词语言": "纯中文", "详细度": "详细", "输出模式": "完整结果", "优先柔和肤质": true, "抑制文字伪影": true, "额外要求": "优先保持海边黄昏全身时尚写真，优先头身比例、站姿和礼服轮廓自然成立，不允许脚部、高跟鞋或腿线极端透视放大。" }, tags: ["成年女性", "东亚", "调酒师", "轻熟感", "真实感", "海边", "黄昏", "深灰丝绒礼服", "全景全身", "85mm人像镜头", "三分法", "电影调色", "低饱和", "主体突出", "服装褶皱真实"] },
	{ name: "林荫街头白衬衫", description: "白衬衫、针织披肩、林荫街道，偏杂志感城市全身人像。", settings: { "模板风格": "真实感", "主体类型": "人物角色", "案例输出结构": "案例长段版", "提示词语言": "纯中文", "详细度": "详细", "输出模式": "完整结果" }, tags: ["成年女性", "东亚", "清冷", "真实感", "时尚写真", "杂志感", "白衬衫", "奶油针织", "街道", "林荫大道", "自然光", "柔光", "全景全身", "平视", "浅景深", "冷白皮", "清透肌肤", "高细节", "8K"] },
	{ name: "海岸逆光白衬衫", description: "海边逆光、白衬衫、成熟冷白皮，偏高级商业全身写真。", settings: { "模板风格": "真实感", "主体类型": "人物角色", "案例输出结构": "案例长段版", "提示词语言": "纯中文", "详细度": "详细", "输出模式": "完整结果" }, tags: ["成年女性", "东亚", "成熟", "真实感", "时尚写真", "白衬衫", "海边", "海岸线", "逆光", "自然光", "暖金光斑", "全景全身", "自然透视", "低角度", "中心构图", "冷白皮", "清透肌肤", "高动态范围", "高细节", "8K"] },
	{ name: "古风玄幻半身", description: "参考古风玄幻半身写真模板，强调黑发发髻、花钿、苏绣与面部聚焦。", settings: { "模板风格": "古风", "主体类型": "人物角色", "案例输出结构": "案例长段版", "提示词语言": "纯中文", "详细度": "详细", "输出模式": "完整结果" }, tags: ["成年女性", "东亚", "清丽", "空灵", "古风", "玄幻古风", "汉服", "苏绣", "披帛", "步摇", "花钿", "鬓边帘", "发髻", "黑长直", "宫殿", "柔光", "光影斑驳", "浮光", "近景", "半身", "镜头近距离", "面部聚焦", "真实发丝", "冷白皮", "瓷肌", "8K"] },
	{ name: "宋韵园林仕女", description: "古风高价值小预设：用宋韵美学、园林仕女、纸窗天光和卷轴式构图，默认全身展示服装轮廓。", settings: { "模板风格": "古风", "主体类型": "人物角色", "案例输出结构": "案例长段版", "提示词语言": "纯中文", "详细度": "详细", "输出模式": "完整结果", "优先柔和肤质": true, "抑制文字伪影": true }, tags: ["成年女性", "东亚", "古风", "宋韵美学", "园林仕女", "褙子", "诃子裙", "云肩", "玉佩", "月洞门", "水榭", "纸窗天光", "卷轴式构图", "全景全身", "丝绸褶裥清晰", "发髻结构完整"] },
	{ name: "竹林月下仕女", description: "竹林、月光、古典女子，偏清冷静谧的古风半身。", settings: { "模板风格": "古风", "主体类型": "人物角色", "案例输出结构": "案例长段版", "提示词语言": "纯中文", "详细度": "详细", "输出模式": "完整结果" }, tags: ["成年女性", "东亚", "清丽", "空灵", "古风", "汉服", "披帛", "竹林", "月光", "自然光", "柔光", "近景", "半身", "侧面", "面部聚焦", "真实发丝", "冷白皮", "细腻肌理", "高细节", "8K"] },
	{ name: "清代仕女工笔", description: "清代仕女、深绿稳重、工笔重彩感。", settings: { "模板风格": "古风", "主体类型": "人物角色", "案例输出结构": "案例长段版", "提示词语言": "纯中文", "详细度": "详细", "输出模式": "完整结果" }, tags: ["成年女性", "东亚", "优雅", "古风", "宫廷", "工笔", "国风美学", "旗袍", "发饰", "深绿", "立领", "柔光", "中景", "平视", "中心构图", "细腻肌理", "高细节", "8K"] },
	{ name: "OVA复古动画", description: "参考 80-90 年代 OVA 提示词，强调手绘线条、低保真与怀旧颗粒。", settings: { "模板风格": "插画感", "主体类型": "人物角色", "案例输出结构": "案例长段版", "提示词语言": "纯中文", "详细度": "详细", "输出模式": "完整结果" }, tags: ["成年女性", "女冒险者", "神秘", "插画感", "OVA风", "手绘画风", "怀旧动画", "赛璐璐", "线条感", "中世纪哥特", "森林", "乡村小道", "梦幻", "中景", "45度角", "广角", "低保真", "印刷网点", "自然噪点", "高细节"] },
	{ name: "中世纪女骑士OVA", description: "女骑士、中世纪郊外、怀旧OVA感。", settings: { "模板风格": "插画感", "主体类型": "人物角色", "案例输出结构": "案例长段版", "提示词语言": "纯中文", "详细度": "详细", "输出模式": "完整结果" }, tags: ["成年女性", "女骑士", "神秘", "插画感", "OVA风", "手绘画风", "怀旧动画", "中世纪哥特", "郊外", "柔光", "中景", "低角度", "广角", "低保真", "印刷网点", "自然噪点", "大师构图", "高细节"] },
	{ name: "暗黑城镇女法师", description: "中世纪暗黑城镇、古典女法师、朦胧神秘。", settings: { "模板风格": "插画感", "主体类型": "人物角色", "案例输出结构": "案例长段版", "提示词语言": "纯中文", "详细度": "详细", "输出模式": "完整结果" }, tags: ["成年女性", "女法师", "神秘", "插画感", "OVA风", "手绘画风", "中世纪城镇", "午夜", "侧光", "中景", "平视", "线条感", "低保真", "印刷网点", "自然噪点", "朦胧感", "大师构图", "高细节"] },
	{ name: "新中式国潮", description: "参考国潮与新年服饰类提示词，强调中式盘扣、马面裙与杂志感。", settings: { "模板风格": "真实感", "主体类型": "人物角色", "案例输出结构": "案例长段版", "提示词语言": "纯中文", "详细度": "详细", "输出模式": "完整结果" }, tags: ["成年女性", "东亚", "优雅", "国潮", "杂志感", "时尚写真", "国潮新中式", "中式盘扣", "袄裙", "马面裙", "街道", "暖色调", "高对比", "中景", "平视", "中心构图", "8K", "高细节"] },
	{ name: "史诗战斗修女CG", description: "参考史诗大片与 OVA 哥特修女表达，强调体积光、神殿和尺度感。", settings: { "模板风格": "CG感", "主体类型": "人物角色", "案例输出结构": "案例长段版", "提示词语言": "纯中文", "详细度": "详细", "输出模式": "完整结果" }, tags: ["成年女性", "战斗修女", "神秘", "CG感", "3D渲染", "史诗感", "宗教核", "中世纪哥特", "体积光", "轮廓光", "低角度", "全身", "广角", "神殿", "战场", "盔甲", "斗篷", "金属", "8K", "电影感", "高细节"] },
	{ name: "赛博女警夜巡", description: "霓虹都市、未来制服、冷硬赛博夜巡。", settings: { "模板风格": "CG感", "主体类型": "人物角色", "案例输出结构": "案例长段版", "提示词语言": "纯中文", "详细度": "详细", "输出模式": "完整结果" }, tags: ["成年女性", "女警", "未来感", "CG感", "3D渲染", "赛博朋克", "霓虹都市", "制服", "金属", "夜晚", "轮廓光", "中景", "低角度", "广角", "高对比", "电影感", "高细节", "8K"] },
	{ name: "机能赛博雨夜", description: "赛博高价值小预设：优先使用机能赛博、义体美学、广告屏街谷和能量刀，默认更像完整赛博大片。", settings: { "模板风格": "CG感", "主体类型": "人物角色", "案例输出结构": "案例长段版", "提示词语言": "纯中文", "详细度": "详细", "输出模式": "完整结果", "抑制文字伪影": true }, tags: ["成年女性", "机能赛博", "义体美学", "全息界面", "能量刀", "广告屏街谷", "霓虹雨夜", "全息投影光", "广告屏反射光", "低角度", "变形宽银幕", "义体金属细节", "霓虹反射克制"] },
	{ name: "洛可可秋日时装", description: "秋日奢华穿搭、复古高端、洛可可曲线感。", settings: { "模板风格": "真实感", "主体类型": "人物角色", "案例输出结构": "案例长段版", "提示词语言": "纯中文", "详细度": "详细", "输出模式": "完整结果" }, tags: ["成年女性", "优雅", "时尚写真", "复古", "杂志感", "长裙", "围巾", "花园", "黄昏", "柔光", "中景", "平视", "中心构图", "梦幻", "高细节", "8K"] },
	{ name: "云海神女", description: "参考神话史诗与东方神性表达，强调云海、台座、丝绸层次与克制神光。", settings: { "模板风格": "神话感", "主体类型": "人物角色", "案例输出结构": "案例长段版", "提示词语言": "纯中文", "详细度": "详细", "输出模式": "完整结果" }, tags: ["成年女性", "神女", "神圣", "神话感", "丝绸", "披帛", "发冠", "宝石", "云海", "神殿", "神圣祭坛", "体积光", "柔光", "仰视", "广角", "史诗", "8K", "电影感"] },
	{ name: "敦煌神庙神女", description: "神话高价值小预设：用敦煌神性、神庙壁画感、天穹祭坛和日轮，默认就能拉开神性空间与材质完成度。", settings: { "模板风格": "神话感", "主体类型": "人物角色", "案例输出结构": "案例长段版", "提示词语言": "纯中文", "详细度": "详细", "输出模式": "完整结果", "优先柔和肤质": true, "抑制文字伪影": true }, tags: ["成年女性", "神女", "东方神话史诗", "敦煌神性", "神庙壁画感", "鎏金头冠", "日轮", "天穹祭坛", "圣辉逆光", "云隙光", "祭坛对称构图", "广角", "神性皮肤光泽", "宝石能量晕光", "神话壁画质感"] },
	{ name: "山谷圣城巨构", description: "参考场景案例里的史诗场景方向：山谷王城、巨构神殿、瀑布峡谷与远山雪峰，适合直接拉出电影级世界观全景。", settings: { "模板风格": "神话感", "主体类型": "非人物主体", "案例输出结构": "案例长段版", "提示词语言": "纯中文", "详细度": "详细", "输出模式": "完整结果", "抑制文字伪影": true }, tags: ["神话感", "巨构史诗奇观", "山谷圣城", "巨构神殿", "瀑布峡谷", "远山雪峰", "史诗城市中轴", "山体建筑一体化", "中轴对称巨构", "超广角全景", "云隙光", "体积光", "山体建筑细节密度"] },
	{ name: "落地窗轻私房", description: "推荐稳定版：女性成人向落地窗夜景，默认全身展示睡袍轮廓与室内空间。", settings: { "模板风格": "真实感", "主体类型": "人物角色", "案例输出结构": "案例长段版", "提示词语言": "纯中文", "详细度": "详细", "输出模式": "完整结果", "优先柔和肤质": true, "抑制文字伪影": true, "额外要求": "优先保持主场景为卧室落地窗夜景，窗外城市灯光只做虚化背景；不要再加入海边、纯色背景或酒吧主空间；默认全身入镜，脸部清晰但不压过头身比例。" }, tags: ["成年女性", "东亚", "调酒师", "真实感", "私房写真", "卧室", "落地窗夜景", "微醺感", "冷白皮", "空气感奶油肌", "湿发", "丝质睡袍", "露背礼服", "全景全身", "50mm标准镜头", "柔光", "电影调色", "胶片感", "主体突出"] },
	{ name: "落地窗轻私房·近景", description: "落地窗轻私房的近景版：脸部、湿发、锁骨和睡袍面料关系优先，避免身体局部夺走注意力。", settings: { "模板风格": "真实感", "主体类型": "人物角色", "案例输出结构": "案例长段版", "提示词语言": "纯中文", "详细度": "详细", "输出模式": "完整结果", "优先柔和肤质": true, "抑制文字伪影": true, "额外要求": "优先保持卧室落地窗夜景近景女性私房，窗外灯光只做虚化背景，脸部和肩颈作为第一视觉中心，不允许胸腰或脚部前景抢戏。" }, tags: ["成年女性", "东亚", "调酒师", "真实感", "私房写真", "卧室", "落地窗夜景", "微醺感", "湿发", "丝质睡袍", "露背礼服", "近景", "85mm人像镜头", "柔光", "电影调色", "胶片感", "主体突出"] },
	{ name: "落地窗轻私房·中景", description: "落地窗轻私房的中景版：适合保留脸部、肩颈、锁骨和上半身服装轮廓。", settings: { "模板风格": "真实感", "主体类型": "人物角色", "案例输出结构": "案例长段版", "提示词语言": "纯中文", "详细度": "详细", "输出模式": "完整结果", "优先柔和肤质": true, "抑制文字伪影": true, "额外要求": "优先保持卧室落地窗夜景中景私房，胸腰线可以辅助，但绝不能压过脸部与姿态；不加入海边、酒吧或纯色背景。" }, tags: ["成年女性", "东亚", "调酒师", "真实感", "私房写真", "卧室", "落地窗夜景", "微醺感", "冷白皮", "空气感奶油肌", "湿发", "丝质睡袍", "露背礼服", "中景半身", "85mm人像镜头", "柔光", "电影调色", "胶片感", "主体突出"] },
	{ name: "落地窗轻私房·全身", description: "落地窗轻私房的全身版：保留私密夜景氛围，同时优先全身比例和睡袍轮廓稳定。", settings: { "模板风格": "真实感", "主体类型": "人物角色", "案例输出结构": "案例长段版", "提示词语言": "纯中文", "详细度": "详细", "输出模式": "完整结果", "优先柔和肤质": true, "抑制文字伪影": true, "额外要求": "优先保持卧室落地窗夜景全身私房，优先头身比例、腿线和睡袍轮廓自然成立，不允许脚部、高跟鞋或身体局部近大远小。"}, tags: ["成年女性", "东亚", "调酒师", "真实感", "私房写真", "卧室", "落地窗夜景", "微醺感", "丝质睡袍", "露背礼服", "全景全身", "85mm人像镜头", "柔光", "电影调色", "主体突出"] },
	{ name: "浴缸蒸汽私房", description: "推荐稳定版：女性成人向浴缸蒸汽场景，默认全身展示浴室空间、姿态和睡袍轮廓。", settings: { "模板风格": "真实感", "主体类型": "人物角色", "案例输出结构": "案例长段版", "提示词语言": "纯中文", "详细度": "详细", "输出模式": "完整结果", "优先柔和肤质": true, "抑制文字伪影": true, "额外要求": "优先保持主场景为浴室浴缸蒸汽空间，不混入卧室或酒吧；默认全身入镜，局部身体只能辅助氛围，不能压过头身比例与姿态；保持蒸汽、湿发和暖灯关系自然克制。" }, tags: ["成年女性", "东亚", "调酒师", "真实感", "私房写真", "浴缸", "浴室", "温泉雾气", "湿发", "丝质睡袍", "冷白皮", "清透肌肤", "全景全身", "50mm标准镜头", "柔光", "暖色调", "电影调色", "主体突出"] },
	{ name: "浴缸蒸汽私房·近景", description: "浴缸蒸汽私房的近景版：保留脸部、湿发、锁骨和蒸汽关系，避免浴缸边缘抢镜。", settings: { "模板风格": "真实感", "主体类型": "人物角色", "案例输出结构": "案例长段版", "提示词语言": "纯中文", "详细度": "详细", "输出模式": "完整结果", "优先柔和肤质": true, "抑制文字伪影": true, "额外要求": "优先保持浴室浴缸蒸汽近景女性私房，蒸汽和暖灯服务脸部与肩颈，不允许浴缸边缘、胸腰或脚部压过主体。" }, tags: ["成年女性", "东亚", "调酒师", "真实感", "私房写真", "浴缸", "浴室", "温泉雾气", "湿发", "丝质睡袍", "近景", "85mm人像镜头", "柔光", "暖色调", "电影调色", "主体突出"] },
	{ name: "浴缸蒸汽私房·中景", description: "浴缸蒸汽私房的中景版：适合保留脸部、肩颈、锁骨和浴室蒸汽环境的平衡。", settings: { "模板风格": "真实感", "主体类型": "人物角色", "案例输出结构": "案例长段版", "提示词语言": "纯中文", "详细度": "详细", "输出模式": "完整结果", "优先柔和肤质": true, "抑制文字伪影": true, "额外要求": "优先保持浴室蒸汽中景私房，保留肩颈与上半身结构，局部身体只能辅助氛围，不允许前景畸变。" }, tags: ["成年女性", "东亚", "调酒师", "真实感", "私房写真", "浴缸", "浴室", "温泉雾气", "湿发", "丝质睡袍", "中景半身", "85mm人像镜头", "柔光", "暖色调", "电影调色", "主体突出"] },
	{ name: "浴缸蒸汽私房·全身", description: "浴缸蒸汽私房的全身版：保留蒸汽浴室环境，但优先全身比例和姿态自然。", settings: { "模板风格": "真实感", "主体类型": "人物角色", "案例输出结构": "案例长段版", "提示词语言": "纯中文", "详细度": "详细", "输出模式": "完整结果", "优先柔和肤质": true, "抑制文字伪影": true, "额外要求": "优先保持浴室蒸汽全身私房，优先头身比例、腿线和姿态自然，不允许极端俯拍、低角度或身体局部近大远小。"}, tags: ["成年女性", "东亚", "调酒师", "真实感", "私房写真", "浴缸", "浴室", "温泉雾气", "丝质睡袍", "全景全身", "85mm人像镜头", "柔光", "暖色调", "电影调色", "主体突出"] },
	{ name: "神话低皱纹人像", description: "神话感近脸优化模板：优先柔光、长焦、中近景与高光过渡柔和，降低法令纹/眼周硬纹理，同时维持云海神殿的神圣氛围。", settings: { "模板风格": "神话感", "主体类型": "人物角色", "案例输出结构": "案例长段版", "提示词语言": "纯中文", "详细度": "详细", "输出模式": "完整结果", "优先柔和肤质": true, "抑制文字伪影": true, "额外要求": "重点控制面部肤质：避免法令纹过深、眼周纹理过重、皮肤锐化过度；背景与服装不要出现任何可读铭文、符文、字母或数字。" }, tags: ["成年女性", "神女", "神圣", "空灵", "神话感", "CG感", "电影剧照", "丝绸", "发冠", "宝石", "云海", "神殿", "异世界", "柔光", "自然光", "暖色调", "中近景", "平视", "长焦", "冷白皮", "清透肌肤", "面部聚焦", "高光过渡柔和", "空气感奶油肌", "高细节", "无文字", "无水印", "无logo", "无边框"] },
	{ name: "白孔雀神女", description: "神女与白孔雀、祥云环绕，偏东方神圣叙事。", settings: { "模板风格": "神话感", "主体类型": "人物角色", "案例输出结构": "案例长段版", "提示词语言": "纯中文", "详细度": "详细", "输出模式": "完整结果" }, tags: ["成年女性", "神女", "神圣", "神话感", "工笔", "白孔雀", "云海", "祥云", "柔光", "体积光", "中景", "仰视", "史诗感", "高细节", "8K"] },
	{ name: "夜色男性私房", description: "推荐稳定版：男性私房夜景，默认全身展示肩线、站姿、手部与睡袍主线。", settings: { "模板风格": "真实感", "主体类型": "人物角色", "案例输出结构": "案例长段版", "提示词语言": "纯中文", "详细度": "详细", "输出模式": "完整结果", "优先柔和肤质": true, "抑制文字伪影": true, "额外要求": "明确保持成年男性主线，不要再写御姐或女性化服装语义；优先保持主场景为私密夜景房间，酒瓶与暖灯只做背景锚点；默认全身入镜，脸部、肩线和手部姿态清晰。" }, tags: ["成年男性", "东亚", "调酒师", "真实感", "私房写真", "卧室", "夜晚", "落地窗夜景", "微湿背头", "银色项链", "丝质睡袍", "全景全身", "50mm标准镜头", "侧光", "电影调色", "胶片感", "主体突出"] },
	{ name: "夜色男性私房·近景", description: "夜色男性私房的近景版：优先下颌、肩颈、手部和睡袍质感，不让局部身体越过脸部。", settings: { "模板风格": "真实感", "主体类型": "人物角色", "案例输出结构": "案例长段版", "提示词语言": "纯中文", "详细度": "详细", "输出模式": "完整结果", "优先柔和肤质": true, "抑制文字伪影": true, "额外要求": "优先保持男性私房近景夜景，脸部、下颌和肩颈作为第一视觉中心，局部身体与道具只能辅助，不允许女性化服装逻辑。" }, tags: ["成年男性", "东亚", "调酒师", "真实感", "私房写真", "卧室", "夜晚", "落地窗夜景", "微湿背头", "银色项链", "丝质睡袍", "近景", "85mm人像镜头", "侧光", "电影调色", "胶片感", "主体突出"] },
	{ name: "夜色男性私房·中景", description: "夜色男性私房的中景版：优先脸部、肩线、手部姿态和睡袍主轮廓。", settings: { "模板风格": "真实感", "主体类型": "人物角色", "案例输出结构": "案例长段版", "提示词语言": "纯中文", "详细度": "详细", "输出模式": "完整结果", "优先柔和肤质": true, "抑制文字伪影": true, "额外要求": "优先保持男性私房中景夜景，优先肩线、下颌、手部姿态和上半身主轮廓，不要让身体局部或酒瓶越过脸部主叙事。" }, tags: ["成年男性", "东亚", "调酒师", "真实感", "私房写真", "卧室", "夜晚", "落地窗夜景", "微湿背头", "银色项链", "丝质睡袍", "中景半身", "85mm人像镜头", "侧光", "电影调色", "胶片感", "主体突出"] },
	{ name: "夜色男性私房·全身", description: "夜色男性私房的全身版：保留私密夜景氛围，但优先男性站姿、肩线和全身比例自然。", settings: { "模板风格": "真实感", "主体类型": "人物角色", "案例输出结构": "案例长段版", "提示词语言": "纯中文", "详细度": "详细", "输出模式": "完整结果", "优先柔和肤质": true, "抑制文字伪影": true, "额外要求": "优先保持男性私房全身夜景，优先头身比例、肩线、站姿和睡袍轮廓自然成立，不允许脚部、腿部或局部身体被极端透视放大。" }, tags: ["成年男性", "东亚", "调酒师", "真实感", "私房写真", "卧室", "夜晚", "落地窗夜景", "微湿背头", "丝质睡袍", "全景全身", "85mm人像镜头", "侧光", "电影调色", "胶片感", "主体突出"] },
	{ name: "胡金铨武侠", description: "参考胡金铨式武侠美学，强调胶片、侧逆光、负空间与前景遮挡。", settings: { "模板风格": "古风", "主体类型": "人物角色", "案例输出结构": "案例长段版", "提示词语言": "纯中文", "详细度": "详细", "输出模式": "完整结果" }, tags: ["成年男性", "剑客", "古风", "胶片感", "负空间", "前景遮挡", "侧光", "逆光", "竹林", "山顶", "低角度", "广角", "斗篷", "电影感", "高对比", "8K"] },
	{ name: "成人私房", description: "成人向、私房、落地窗夜景。", settings: { "模板风格": "真实感", "主体类型": "人物角色", "案例输出结构": "案例长段版", "提示词语言": "纯中文", "详细度": "详细", "输出模式": "完整结果" }, tags: ["成年女性", "东亚", "成熟", "御姐", "私房写真", "成人向", "暧昧", "睡裙", "落地窗夜景", "柔光", "夜晚", "迷离", "近景", "半身", "平视", "中心构图", "8K", "电影感", "皮肤纹理", "景深"] },
	{ name: "暖厨柔焦私房", description: "暖灯厨房、近景凝视、柔焦肤感。", settings: { "模板风格": "真实感", "主体类型": "人物角色", "案例输出结构": "案例长段版", "提示词语言": "纯中文", "详细度": "详细", "输出模式": "完整结果" }, tags: ["成年女性", "东亚", "成熟", "暧昧", "私房写真", "柔光", "暖色调", "厨房", "近景", "低角度", "面部聚焦", "冷白皮", "清透肌肤", "景深", "电影感", "高细节", "8K"] },
	{ name: "机甲写实", description: "机甲、写实、工业感。", settings: { "模板风格": "真实感", "主体类型": "非人物主体", "案例输出结构": "案例分段版", "提示词语言": "纯中文", "详细度": "详细", "输出模式": "完整结果" }, tags: ["机甲", "战士", "未来感", "真实感", "照片级", "纪实", "自然光", "柔光", "侧光", "冷色调", "低饱和", "中景", "全身", "平视", "标准镜头", "中心构图", "金属", "训练场", "8K", "杰作", "最佳质量", "锐利焦点", "raw photo", "金属反光", "橡胶"] },
	{ name: "工业树灵巨像", description: "参考巨物妖兽案例里的混生质感：树灵巨像、朽木树皮、苔藓附生与工业舱室组合，适合做近景压迫型非人主体。", settings: { "模板风格": "CG感", "主体类型": "非人物主体", "案例输出结构": "案例长段版", "提示词语言": "纯中文", "详细度": "详细", "输出模式": "完整结果", "抑制文字伪影": true }, tags: ["CG感", "树灵巨像", "古木守卫", "朽木树皮纹理", "苔藓附生质感", "工业舱室", "巨物压迫近景", "冷色工业顶光", "风化木纹", "发光裂隙", "游戏CG质感", "材质细节丰富"] },
	{ name: "欧式贵族油画", description: "油画质感、宫廷贵族、古典华丽。", settings: { "模板风格": "神话感", "主体类型": "人物角色", "案例输出结构": "案例长段版", "提示词语言": "纯中文", "详细度": "详细", "输出模式": "完整结果" }, tags: ["成年女性", "贵族", "优雅", "油画", "复古", "华丽", "宫廷", "礼服", "柔光", "中景", "平视", "中心构图", "高细节", "8K"] },
	{ name: "纯欲夏日泳装", description: "夏日泳装、柔光、暧昧但偏轻私房。", settings: { "模板风格": "真实感", "主体类型": "人物角色", "案例输出结构": "案例长段版", "提示词语言": "纯中文", "详细度": "详细", "输出模式": "完整结果" }, tags: ["成年女性", "东亚", "纯欲风", "少女", "泳装", "海边", "柔光", "暖色调", "近景", "半身", "平视", "浅景深", "清透肌肤", "电影感", "高细节", "8K"] },
];

const DISABLED_CASE_PRESET_NAMES = new Set([
	"糖水片成年写真",
	"成人私房",
	"暖厨柔焦私房",
	"林荫街头白衬衫",
	"海岸逆光白衬衫",
	"欧式贵族油画",
	"纯欲夏日泳装",
]);
const EXAMPLE_ANCHOR_PRESET_NAMES = new Set([
	"中画幅通勤大片",
	"城市天台晚风纪实",
	"OVA复古动画",
	"宋韵园林仕女",
	"敦煌神庙神女",
	"山谷圣城巨构",
	"机能赛博雨夜",
	"工业树灵巨像",
	"胡金铨武侠",
	"机甲写实",
]);
const COLLAPSED_PRESET_FAMILIES = new Set([
	"海边轻熟写实",
	"落地窗轻私房",
	"浴缸蒸汽私房",
	"夜色男性私房",
]);

const EXAMPLE_PRESET_MAP = { "真实感": "中画幅通勤大片", "插画感": "OVA复古动画", "CG感": "机能赛博雨夜", "古风": "宋韵园林仕女", "神话感": "敦煌神庙神女", "自动": "中画幅通勤大片" };
const PRESET_TIER_ORDER = ["稳妥", "强风格", "高完成度"];
const PRESET_USE_CASE_ORDER = ["人像", "场景", "巨物", "成人", "古风", "神话", "CG科幻", "职业", "女性向", "男性向", "低遮挡", "电影感", "道具叙事", "测试"];
const PRESET_GROUP_USE_CASES = {
	"人像写真": ["人像"],
	"成人私房": ["成人"],
	"古风神话": ["古风", "神话"],
	"CG科幻": ["CG科幻"],
	"场景史诗": ["场景", "神话"],
	"巨物妖兽": ["巨物", "CG科幻"],
	"职业题材": ["职业"],
	"运行测试": ["测试"],
	"示例模板": ["人像"],
};
const PRESET_STRONG_STYLE_TAGS = new Set(["古风", "神话感", "CG感", "插画感", "OVA风", "赛博朋克", "巴洛克", "蒸汽都市", "霓虹都市", "未来都市", "异世界", "水墨", "油画", "神殿", "云海"]);
const PRESET_HIGH_FINISH_TAGS = new Set(["体积光", "商业广告大片", "电影剧照", "电影调色", "珠宝细节", "神圣祭坛", "云端阶梯", "法阵", "权杖", "法杖", "宝剑", "枪", "身体轮廓清晰", "遮挡最小化", "无遮挡感"]);
const PRESET_FEMALE_TAGS = new Set(["少女", "成年女性", "中年女性", "OL", "神女", "仙子", "魔女", "公主", "女王", "战斗修女", "女冒险者"]);
const PRESET_MALE_TAGS = new Set(["少年", "成年男性", "中年男性", "皇子", "帝王", "骑士", "剑客", "特工", "律师", "机修师", "机械师", "调酒师", "乐队主唱"]);
const PRESET_LOW_COVER_TAGS = new Set(["遮挡最小化", "无遮挡感", "少遮挡", "弱遮挡", "身体轮廓清晰"]);
const PRESET_CINEMATIC_TAGS = new Set(["电影剧照", "电影调色", "商业广告大片", "胶片感"]);
const PRESET_PROP_TAGS = new Set(["花束", "酒杯", "乐器", "卷轴", "灯笼", "面具", "扇", "伞", "武器", "剑", "宝剑", "刀", "枪", "弓", "盾", "长矛", "权杖", "法器", "法杖"]);
const PRESET_SCENE_TAGS = new Set(["山谷圣城", "巨构神殿", "瀑布峡谷", "远山雪峰", "史诗城市中轴", "山体建筑一体化", "城市天台", "屋顶晾衣架"]);
const PRESET_MONSTER_TAGS = new Set(["树灵巨像", "古木守卫", "藤蔓木妖", "朽木树皮纹理", "苔藓附生质感", "巨物压迫近景"]);
const PRESET_USE_CASE_ALIASES = {
	"人像": ["写真", "肖像", "portrait"],
	"场景": ["环境", "建筑", "landscape", "scene"],
	"巨物": ["怪兽", "妖兽", "巨像", "kaiju", "colossal", "beast"],
	"成人": ["私房", "adult", "nsfw"],
	"古风": ["国风", "武侠", "oriental"],
	"神话": ["史诗", "祭司", "myth"],
	"CG科幻": ["科幻", "赛博", "插画", "cg", "scifi"],
	"职业": ["职业角色", "纪实", "role"],
	"女性向": ["女生", "女像", "female"],
	"男性向": ["男像", "男性", "male"],
	"低遮挡": ["轮廓", "开放感", "low-cover"],
	"电影感": ["cinematic", "film", "movie"],
	"道具叙事": ["持物", "武器", "法器", "prop"],
	"测试": ["调试", "随机", "test"],
};
const CHARACTER_SHEET_MODE_OPTIONS = [
	{
		key: "reference",
		label: "参考单人图",
		desc: "接入单人参考图时使用：只约束同一角色一致性，不锁定风格、服装、颜色和背景。",
	},
	{
		key: "prompt",
		label: "纯提示词",
		desc: "不接图片参考时使用：按输入文字生成角色设定图，不额外固定题材。",
	},
];
const CHARACTER_SHEET_BASE_TAGS = [
	"角色设定图",
	"角色三视图",
	"正面视图",
	"侧面视图",
	"背面视图",
	"头像特写",
	"全身",
	"低遮挡",
	"身体轮廓清晰",
	"服装结构完整",
	"发型结构完整",
	"材质细节丰富",
	"无文字",
	"无水印",
	"无logo",
];
const CHARACTER_SHEET_STYLE_TAGS = ["高细节", "主体轮廓清晰", "人物完整入镜", "空间层次明确"];
const CHARACTER_SHEET_PROMPTS = {
	reference: "角色设定图模式：接入单人参考图作为角色来源，保持同一成年角色的脸型、发型、关键服装结构、主配色和材质逻辑一致；画面组织为角色设定展示，可包含头像特写、正面全身、侧面全身、背面全身等视角；背景、风格、服装和色彩跟随参考图与用户补充，不要自行锁定白底、古风、汉服或固定颜色；不要更换人物，不要生成多人故事场景，不要文字标注。",
	prompt: "角色设定图模式：根据当前文字生成角色设定展示，可包含头像特写、正面全身、侧面全身、背面全身等视角；角色身份、服装、风格、配色、背景和材质完全跟随用户输入与当前节点标签，不要额外锁定白底、古风、汉服、粉色或固定题材；重点表现服装结构、发型轮廓、材质层次和角色一致性，不要文字标注。",
};
const CHARACTER_SHEET_STRATEGY_PREFIX = "角色设定图策略：";
const CHARACTER_SHEET_MODE_TAGS = ["参考图一致性", "纯提示词角色设计"];
const CHARACTER_SHEET_AUTO_TAGS = new Set([...CHARACTER_SHEET_BASE_TAGS, ...CHARACTER_SHEET_STYLE_TAGS, ...CHARACTER_SHEET_MODE_TAGS]);
const CHARACTER_SHEET_LEGACY_CLEANUP_TAGS = new Set([
	"角色设定图",
	"角色三视图",
	"正面视图",
	"侧面视图",
	"背面视图",
	"头像特写",
	"服装结构完整",
	"发型结构完整",
	...CHARACTER_SHEET_MODE_TAGS,
]);
const CHARACTER_SHEET_SETTING_NAMES = [
	"主体类型",
	"案例输出结构",
	"详细度",
	"输出模式",
	"优先柔和肤质",
	"抑制文字伪影",
	"图片反推生成",
	"图片反推模式",
	"图片反推最大边长",
];

function uniqueTextList(items) {
	const seen = new Set();
	const result = [];
	for (const raw of items ?? []) {
		const text = String(raw ?? "").trim();
		if (!text || seen.has(text)) continue;
		seen.add(text);
		result.push(text);
	}
	return result;
}

function parseNsfwCustomFieldLibraryEntries(value) {
	return uniqueTextList(String(value ?? "")
		.replace(/\r/gu, "\n")
		.split(/\n+/u)
		.map((item) => String(item ?? "").trim())
		.filter((item) => item && item !== "——"));
}

function normalizeNsfwCustomFieldLibrary(library) {
	const normalized = {};
	const source = library && typeof library === "object" ? library : {};
	for (const field of NSFW_CUSTOM_FIELD_LIBRARY_FIELDS) {
		const items = Array.isArray(source[field]) ? source[field] : [];
		normalized[field] = [];
		for (const item of uniqueTextList(items)) {
			if (!item || item === "——" || item.length > NSFW_CUSTOM_FIELD_ENTRY_MAX_CHARS) continue;
			if (normalized[field].length >= NSFW_CUSTOM_FIELD_ENTRY_LIMIT) break;
			const candidate = { ...normalized, [field]: [...normalized[field], item] };
			if (utf8ByteLength(candidate) > NSFW_CUSTOM_FIELD_LIBRARY_MAX_BYTES) continue;
			normalized[field].push(item);
		}
	}
	return normalized;
}

function getNsfwCustomFieldLibrary() {
	try {
		const raw = globalThis.localStorage?.getItem?.(NSFW_CUSTOM_FIELD_LIBRARY_STORAGE_KEY);
		if (!raw) return normalizeNsfwCustomFieldLibrary(null);
		return normalizeNsfwCustomFieldLibrary(JSON.parse(raw));
	} catch {
		return normalizeNsfwCustomFieldLibrary(null);
	}
}

function persistNsfwCustomFieldLibrary(library) {
	const normalized = normalizeNsfwCustomFieldLibrary(library);
	try {
		if (typeof globalThis.localStorage?.setItem !== "function") throw new Error("localStorage unavailable");
		globalThis.localStorage.setItem(NSFW_CUSTOM_FIELD_LIBRARY_STORAGE_KEY, JSON.stringify(normalized));
		return { ok: true, library: normalized, error: null };
	} catch (error) {
		return { ok: false, library: getNsfwCustomFieldLibrary(), error };
	}
}

function setNsfwCustomFieldLibrary(library) {
	return persistNsfwCustomFieldLibrary(library).library;
}

function getNsfwCustomFieldOptions(field) {
	const key = String(field ?? "").trim();
	if (!NSFW_CUSTOM_FIELD_LIBRARY_FIELDS.includes(key)) return [];
	return [...(getNsfwCustomFieldLibrary()[key] ?? [])];
}

function addNsfwCustomFieldOptions(field, value) {
	const key = String(field ?? "").trim();
	const library = getNsfwCustomFieldLibrary();
	if (!NSFW_CUSTOM_FIELD_LIBRARY_FIELDS.includes(key)) return { ok: false, added: 0, skipped: 0, library };
	const entries = parseNsfwCustomFieldLibraryEntries(value);
	const existing = new Set(library[key] ?? []);
	let added = 0;
	let skipped = 0;
	for (const entry of entries) {
		if (existing.has(entry) || entry.length > NSFW_CUSTOM_FIELD_ENTRY_MAX_CHARS || library[key].length >= NSFW_CUSTOM_FIELD_ENTRY_LIMIT) {
			skipped += 1;
			continue;
		}
		library[key].push(entry);
		if (utf8ByteLength(library) > NSFW_CUSTOM_FIELD_LIBRARY_MAX_BYTES) {
			library[key].pop();
			skipped += 1;
			continue;
		}
		existing.add(entry);
		added += 1;
	}
	const persisted = persistNsfwCustomFieldLibrary(library);
	if (!persisted.ok) return { ok: false, added: 0, skipped: skipped + added, reason: "storage", error: persisted.error, library: persisted.library };
	return { ok: true, added, skipped, library: persisted.library };
}

function removeNsfwCustomFieldOption(field, optionValue) {
	const key = String(field ?? "").trim();
	const library = getNsfwCustomFieldLibrary();
	if (!NSFW_CUSTOM_FIELD_LIBRARY_FIELDS.includes(key)) return { ok: false, removed: false, library };
	const value = String(optionValue ?? "").trim();
	const before = library[key]?.length ?? 0;
	library[key] = (library[key] ?? []).filter((item) => item !== value);
	const removed = (library[key]?.length ?? 0) !== before;
	if (!removed) return { ok: true, removed: false, library };
	const persisted = persistNsfwCustomFieldLibrary(library);
	return persisted.ok
		? { ok: true, removed: true, library: persisted.library }
		: { ok: false, removed: false, reason: "storage", error: persisted.error, library: persisted.library };
}

function inferPresetGroup(preset) {
	const tags = new Set(preset?.tags ?? []);
	if (tags.has("成人向") || tags.has("私房写真") || tags.has("暧昧")) return "成人私房";
	if (tags.has("树灵巨像") || tags.has("古木守卫") || tags.has("藤蔓木妖") || tags.has("巨物压迫近景")) return "巨物妖兽";
	if (tags.has("山谷圣城") || tags.has("巨构神殿") || tags.has("瀑布峡谷") || tags.has("远山雪峰") || tags.has("史诗城市中轴")) return "场景史诗";
	if (tags.has("神话感") || tags.has("古风") || tags.has("汉服") || tags.has("武侠")) return "古风神话";
	if (tags.has("CG感") || tags.has("插画感") || tags.has("OVA风") || tags.has("赛博朋克") || tags.has("未来都市")) return "CG科幻";
	if ([...tags].some((tag) => PRESET_MALE_TAGS.has(tag) || ["机修师", "机械师", "律师", "调酒师", "乐队主唱", "摄影师"].includes(tag))) return "职业题材";
	if (String(preset?.name ?? "").includes("随机")) return "运行测试";
	return "示例模板";
}

function inferPresetTier(groupName, tags) {
	const tagSet = new Set(tags ?? []);
	if (groupName === "运行测试") return "稳妥";
	if ([...tagSet].some((tag) => PRESET_HIGH_FINISH_TAGS.has(tag))) return "高完成度";
	if (groupName === "CG科幻" || groupName === "古风神话") return "强风格";
	if ([...tagSet].some((tag) => PRESET_STRONG_STYLE_TAGS.has(tag))) return "强风格";
	return "稳妥";
}

function inferPresetUseCases(groupName, tags) {
	const tagSet = new Set(tags ?? []);
	const uses = new Set(PRESET_GROUP_USE_CASES[groupName] ?? []);
	if ([...tagSet].some((tag) => PRESET_SCENE_TAGS.has(tag))) uses.add("场景");
	if ([...tagSet].some((tag) => PRESET_MONSTER_TAGS.has(tag))) uses.add("巨物");
	if ([...tagSet].some((tag) => PRESET_FEMALE_TAGS.has(tag))) uses.add("女性向");
	if ([...tagSet].some((tag) => PRESET_MALE_TAGS.has(tag))) uses.add("男性向");
	if ([...tagSet].some((tag) => PRESET_LOW_COVER_TAGS.has(tag))) uses.add("低遮挡");
	if ([...tagSet].some((tag) => PRESET_CINEMATIC_TAGS.has(tag))) uses.add("电影感");
	if ([...tagSet].some((tag) => PRESET_PROP_TAGS.has(tag))) uses.add("道具叙事");
	if (tagSet.has("神话感")) uses.add("神话");
	if (tagSet.has("古风") || tagSet.has("汉服") || tagSet.has("武侠")) uses.add("古风");
	if (tagSet.has("成人向") || tagSet.has("私房写真")) uses.add("成人");
	if (tagSet.has("CG感") || tagSet.has("插画感") || tagSet.has("未来都市")) uses.add("CG科幻");
	if (groupName === "示例模板" && !uses.has("成人")) uses.add("人像");
	return PRESET_USE_CASE_ORDER.filter((label) => uses.has(label));
}

function buildPresetSearchKeywords(preset, meta) {
	const keywords = [
		preset?.name,
		preset?.description,
		meta?.group,
		meta?.tier,
		...(meta?.use_cases ?? []),
		...(preset?.tags ?? []),
		...(meta?.search_keywords ?? []),
	];
	for (const label of meta?.use_cases ?? []) keywords.push(...(PRESET_USE_CASE_ALIASES[label] ?? []));
	return uniqueTextList(keywords);
}

function hydratePreset(preset, libraryMeta = null) {
	const group = String(libraryMeta?.group ?? inferPresetGroup(preset));
	const tier = String(libraryMeta?.tier ?? inferPresetTier(group, preset?.tags ?? []));
	const useCases = uniqueTextList(Array.isArray(libraryMeta?.use_cases) ? libraryMeta.use_cases : inferPresetUseCases(group, preset?.tags ?? []));
	const meta = {
		group,
		tier,
		tag_count: Number(libraryMeta?.tag_count ?? (preset?.tags ?? []).length),
		use_cases: useCases,
		search_keywords: uniqueTextList(Array.isArray(libraryMeta?.search_keywords) ? libraryMeta.search_keywords : []),
	};
	meta.search_keywords = buildPresetSearchKeywords(preset, meta);
	return {
		...preset,
		description: preset?.description ?? "来自内置快速推荐组合。",
		meta,
	};
}

function isCollapsedPresetVariant(name) {
	const presetName = String(name ?? "").trim();
	if (!presetName.includes("·")) return false;
	const family = getPresetFamilyKey(presetName);
	const variant = getPresetVariantKey(presetName);
	return COLLAPSED_PRESET_FAMILIES.has(family) && ["标准", "近景", "中景", "全身"].includes(variant);
}

function buildDedupedPresets(library, options = {}) {
	const includeVariants = !!options.includeVariants;
	const collection = String(options.collection ?? "all");
	const merged = new Map();
	const metaMap = library?.quick_preset_meta ?? {};
	const casePresetMap = new Map(CASE_PRESETS.map((preset) => [String(preset.name), preset]));
	const shouldIncludePreset = (name) => {
		const presetName = String(name ?? "").trim();
		if (DISABLED_CASE_PRESET_NAMES.has(presetName)) return false;
		if (collection === "example") return EXAMPLE_ANCHOR_PRESET_NAMES.has(presetName);
		if (collection === "production") return !EXAMPLE_ANCHOR_PRESET_NAMES.has(presetName);
		return true;
	};
	for (const [name, tags] of Object.entries(library?.quick_presets ?? {})) {
		if (!shouldIncludePreset(name)) continue;
		if (!includeVariants && isCollapsedPresetVariant(name)) continue;
		const fallbackPreset = casePresetMap.get(String(name));
		merged.set(
			String(name),
			hydratePreset(
				{
					name,
					description: fallbackPreset?.description ?? "来自内置快速推荐组合。",
					tags,
					settings: fallbackPreset?.settings ?? {},
				},
				metaMap?.[String(name)],
			),
		);
	}
	for (const preset of CASE_PRESETS) {
		const name = String(preset.name);
		if (!shouldIncludePreset(name)) continue;
		if (!includeVariants && isCollapsedPresetVariant(name)) continue;
		if (merged.has(name)) continue;
		merged.set(name, hydratePreset(preset, metaMap?.[name]));
	}
	return [...merged.values()];
}

function inferBestExamplePreset(availablePresets, currentTemplate, currentState) {
	const presets = Array.isArray(availablePresets) ? availablePresets : [];
	if (!presets.length) return null;
	const selectedTags = new Set([
		...Object.values(currentState?.selected ?? {}).flat(),
		...(currentState?.customTags ?? []),
	]);
	const templateName = String(currentTemplate ?? "自动");
	const subjectType = String(currentState?.settings?.["主体类型"] ?? "自动").trim();
	const scored = presets
		.map((preset) => {
			let score = 0;
			const tags = new Set(preset?.tags ?? []);
			if (templateName !== "自动" && tags.has(templateName)) score += 12;
			if (templateName === "自动") score += 1;
			for (const tag of selectedTags) {
				if (tags.has(tag)) score += 3;
			}
			const useCases = new Set(preset?.meta?.use_cases ?? []);
			if (selectedTags.has("成人向") && useCases.has("成人")) score += 6;
			if ((selectedTags.has("古风") || selectedTags.has("汉服")) && useCases.has("古风")) score += 6;
			if (selectedTags.has("神话感") && useCases.has("神话")) score += 6;
			if (selectedTags.has("CG感") && useCases.has("CG科幻")) score += 6;
			if (selectedTags.has("成年男性") && useCases.has("男性向")) score += 4;
			if (selectedTags.has("成年女性") && useCases.has("女性向")) score += 4;
			const sceneTags = ["山谷圣城", "巨构神殿", "瀑布峡谷", "远山雪峰", "史诗城市中轴", "山体建筑一体化"];
			const colossusTags = ["树灵巨像", "古木守卫", "藤蔓木妖", "工业舱室", "巨物压迫近景", "朽木树皮纹理", "苔藓附生质感", "发光裂隙"];
			if (subjectType === "非人物主体") {
				if (useCases.has("场景")) score += 8;
				if (useCases.has("巨物")) score += 8;
				if (useCases.has("人像")) score -= 6;
				if (useCases.has("女性向") || useCases.has("男性向")) score -= 3;
			}
			if (sceneTags.some((tag) => selectedTags.has(tag)) && useCases.has("场景")) score += 12;
			if (colossusTags.some((tag) => selectedTags.has(tag)) && useCases.has("巨物")) score += 12;
			if (templateName === "神话感" && subjectType === "非人物主体" && useCases.has("场景")) score += 4;
			if (templateName === "CG感" && subjectType === "非人物主体" && useCases.has("巨物")) score += 4;
			return { preset, score };
		})
		.sort((left, right) => right.score - left.score || String(left.preset?.name ?? "").localeCompare(String(right.preset?.name ?? ""), "zh-CN"));
	return scored[0]?.preset ?? null;
}

function getPresetFamilyKey(presetName = "") {
	return String(presetName ?? "").split("·")[0].trim();
}

function getPresetVariantKey(presetName = "") {
	const parts = String(presetName ?? "").split("·");
	return parts.length > 1 ? parts.slice(1).join("·").trim() : "base";
}

function getPresetVariantLabel(presetName = "") {
	const key = getPresetVariantKey(presetName);
	if (key === "base") return "基础";
	return key;
}

function inferPresetRecommendation(preset) {
	const name = String(preset?.name ?? "");
	const tags = new Set(preset?.tags ?? []);
	const shotKey = name.includes("·近景")
		? "close"
		: name.includes("·全身")
			? "wide"
			: tags.has("近景") || tags.has("面部特写") || tags.has("头部写真")
				? "close"
				: tags.has("全景全身") || tags.has("全身") || tags.has("大全景")
					? "wide"
					: "mid";
	const family = getPresetFamilyKey(name);
	const shotLabel = shotKey === "close" ? "近景" : shotKey === "wide" ? "全身" : "中景";
	const byFamily = {
		"海边轻熟写实": { sampler: "DPM++ 2M Karras", steps: "28-34", cfg: "4.6-6.0", denoise: shotKey === "wide" ? "0.18-0.24" : "0.20-0.28", note: "优先压住海边留白和礼服轮廓，避免脚部前景放大。" },
		"落地窗轻私房": { sampler: "DPM++ 2M Karras", steps: "26-32", cfg: "4.2-5.6", denoise: shotKey === "close" ? "0.18-0.24" : "0.20-0.30", note: "优先保持卧室落地窗夜景，窗外灯光只做虚化背景。" },
		"浴缸蒸汽私房": { sampler: "DPM++ SDE Karras", steps: "26-32", cfg: "4.2-5.4", denoise: shotKey === "wide" ? "0.16-0.24" : "0.18-0.26", note: "蒸汽和暖灯辅助脸部与肩颈，不要让浴缸边缘抢镜。" },
		"夜色男性私房": { sampler: "DPM++ 2M Karras", steps: "26-32", cfg: "4.5-5.8", denoise: shotKey === "wide" ? "0.16-0.24" : "0.18-0.28", note: "优先男性肩线、下颌和手部姿态，不走女性私房构图逻辑。" },
		"中画幅通勤大片": { sampler: "DPM++ 2M Karras", steps: "28-34", cfg: "4.5-6.0", denoise: "0.18-0.28", note: "适合干净商业写实和中画幅成片质感。" },
		"机能赛博雨夜": { sampler: "DPM++ SDE Karras", steps: "28-36", cfg: "4.8-6.2", denoise: "0.18-0.28", note: "先保机能赛博结构，再放霓虹和广告屏反射。" },
		"宋韵园林仕女": { sampler: "DPM++ 2M Karras", steps: "28-34", cfg: "4.6-5.8", denoise: "0.18-0.26", note: "优先纸窗天光、园林借景和服饰层次。" },
		"敦煌神庙神女": { sampler: "DPM++ SDE Karras", steps: "30-36", cfg: "4.8-6.2", denoise: "0.18-0.28", note: "优先祭坛、天光与神性材质，不要让特效盖人。" },
		"山谷圣城巨构": { sampler: "DPM++ SDE Karras", steps: "32-40", cfg: "4.8-6.4", denoise: "0.18-0.30", note: "优先空间尺度、建筑层次和主光方向，避免误跑成人像小景。" },
		"工业树灵巨像": { sampler: "DPM++ SDE Karras", steps: "30-38", cfg: "4.8-6.4", denoise: "0.20-0.32", note: "优先巨物体量、树皮材质和工业舱室压迫感，角色只做尺度参考。" },
	};
	const fallback = { sampler: "DPM++ 2M Karras", steps: "28-34", cfg: "4.5-6.0", denoise: "0.18-0.28", note: "优先保证单一主场景、单一主镜头和结构稳定。" };
	const rule = byFamily[family] ?? fallback;
	return [
		{ label: "推荐采样", value: rule.sampler },
		{ label: "建议步数", value: rule.steps },
		{ label: "建议 CFG", value: rule.cfg },
		{ label: "建议 Denoise", value: rule.denoise },
		{ label: "适合景别", value: shotLabel },
		{ label: "稳定提醒", value: rule.note },
	];
}

function inferPresetNegativePreview(preset) {
	const tags = new Set(preset?.tags ?? []);
	const settings = preset?.settings ?? {};
	const family = getPresetFamilyKey(preset?.name ?? "");
	const shotKey = getPresetVariantKey(preset?.name ?? "") === "近景"
		? "close"
		: getPresetVariantKey(preset?.name ?? "") === "全身"
			? "wide"
			: inferPresetRecommendation(preset).find((item) => item.label === "适合景别")?.value === "全身"
				? "wide"
				: inferPresetRecommendation(preset).find((item) => item.label === "适合景别")?.value === "近景"
					? "close"
					: "mid";
	const negatives = [
		"多主体",
		"多场景拼贴",
		"多镜头冲突",
		"可读文字",
		"水印",
		"logo",
	];
	if (shotKey === "close") negatives.push("前景脚部放大", "局部身体压脸", "道具压脸", "微距皮肤锐化");
	if (shotKey === "mid") negatives.push("胸腰前景抢镜", "手脚比例异常", "半身躯干缺失");
	if (shotKey === "wide") negatives.push("截断脚部", "截断双腿", "头身比例异常", "关节弯折异常");
	if (family.includes("轻私房") || family.includes("蒸汽私房") || family.includes("男性私房") || tags.has("私房写真")) {
		negatives.push("高跟鞋压镜头", "臀腿前景抢戏", "极端低角度畸变");
	}
	if (family.includes("海边轻熟")) negatives.push("珠宝喧宾夺主", "礼服状态冲突");
	if (family.includes("男性私房")) negatives.push("御姐语义漂移", "女性化服装语义", "女性私房构图逻辑");
	if (settings["优先柔和肤质"]) negatives.push("过度皮肤锐化", "法令纹过深", "眼周纹理过重");
	if (settings["抑制文字伪影"]) negatives.push("屏幕字样", "铭文", "招牌字样");
	return uniqueTextList(negatives);
}

function inferPresetDisplayGroup(preset) {
	const family = getPresetFamilyKey(preset?.name ?? "");
	const useCases = new Set(preset?.meta?.use_cases ?? []);
	if (useCases.has("场景")) return "场景";
	if (useCases.has("巨物")) return "巨物";
	if (family.includes("男性")) return "男性";
	if (family.includes("私房") || useCases.has("成人")) return "私房";
	if (family.includes("写实") || useCases.has("人像")) return "写实";
	return "其他";
}

function inferProductionPresetGroup(preset) {
	const template = String(preset?.settings?.["模板风格"] ?? "").trim();
	const tags = new Set(preset?.tags ?? []);
	if (template === "古风" || tags.has("古风") || tags.has("汉服") || tags.has("武侠")) return "古风";
	if (template === "神话感" || tags.has("神话感") || tags.has("神女") || tags.has("神圣")) return "神话";
	if (template === "CG感" || template === "插画感" || tags.has("CG感") || tags.has("插画感") || tags.has("赛博朋克") || tags.has("OVA风")) return "CG";
	return "写实";
}

let styleInjected = false;
let promptLibraryPromise = null;
let promptLibraryPromiseEpoch = -1;
let promptLibrarySnapshot = null;
let promptLibrarySnapshotEpoch = -1;
let promptLibraryEpoch = 0;
let promptLibraryRequestGeneration = 0;
let promptLibraryNeedsRefresh = false;
const PROMPT_LIBRARY_REQUEST_OWNER = {};
const PROMPT_LIBRARY_MUTATION_ROUTES = new Set([
	"/qwen_te/tag_library/add_batch",
	"/qwen_te/tag_library/delete",
]);
const OWNED_FETCH_REQUESTS = new WeakMap();
const BOUNDED_NODE_HISTORY_ARRAYS = new WeakSet();

function isAbortLikeError(error) {
	const name = String(error?.name ?? "");
	const message = String(error?.message ?? error ?? "");
	return name === "AbortError" || /(?:signal is aborted|aborted without reason)/iu.test(message);
}

function utf8ByteLength(value) {
	const text = typeof value === "string" ? value : JSON.stringify(value ?? null);
	if (typeof TextEncoder === "function") return new TextEncoder().encode(text).byteLength;
	try { return unescape(encodeURIComponent(text)).length; } catch (_error) { return text.length * 2; }
}

function abortOwnedRequest(owner, key) {
	if (!owner || (typeof owner !== "object" && typeof owner !== "function")) return false;
	const requests = OWNED_FETCH_REQUESTS.get(owner);
	const requestKey = String(key ?? "default");
	const controller = requests?.get(requestKey);
	if (!controller) return false;
	requests.delete(requestKey);
	if (!requests.size) OWNED_FETCH_REQUESTS.delete(owner);
	try { controller.abort(); } catch (_error) {}
	return true;
}

function abortOwnedRequests(owner) {
	if (!owner || (typeof owner !== "object" && typeof owner !== "function")) return 0;
	const requests = OWNED_FETCH_REQUESTS.get(owner);
	if (!requests) return 0;
	OWNED_FETCH_REQUESTS.delete(owner);
	let aborted = 0;
	for (const controller of requests.values()) {
		try { controller.abort(); aborted += 1; } catch (_error) {}
	}
	return aborted;
}

async function runOwnedFetch(input, init = {}, options = {}, consume = async (response) => response) {
	const owner = options.owner;
	const key = String(options.key ?? input ?? "request");
	const timeoutMs = Math.max(250, Number(options.timeoutMs ?? UI_FETCH_DEFAULT_TIMEOUT_MS) || UI_FETCH_DEFAULT_TIMEOUT_MS);
	const Controller = globalThis.AbortController;
	if (typeof Controller !== "function") return await consume(await fetch(input, init));
	if (owner && options.replace !== false) abortOwnedRequest(owner, key);
	const controller = new Controller();
	const externalSignal = init?.signal;
	const abortFromExternal = () => controller.abort(externalSignal?.reason);
	if (externalSignal?.aborted) abortFromExternal();
	else externalSignal?.addEventListener?.("abort", abortFromExternal, { once: true });
	let requests = null;
	if (owner && (typeof owner === "object" || typeof owner === "function")) {
		requests = OWNED_FETCH_REQUESTS.get(owner);
		if (!requests) {
			requests = new Map();
			OWNED_FETCH_REQUESTS.set(owner, requests);
		}
		requests.set(key, controller);
	}
	let timedOut = false;
	const timeoutId = setTimeout(() => {
		timedOut = true;
		controller.abort();
	}, timeoutMs);
	timeoutId?.unref?.();
	try {
		const response = await fetch(input, { ...init, signal: controller.signal });
		return await consume(response);
	} catch (error) {
		if (timedOut && isAbortLikeError(error)) {
			const timeoutError = new Error(`请求超时（${Math.max(1, Math.round(timeoutMs / 1000))} 秒）。`);
			timeoutError.name = "TimeoutError";
			throw timeoutError;
		}
		throw error;
	} finally {
		clearTimeout(timeoutId);
		externalSignal?.removeEventListener?.("abort", abortFromExternal);
		if (requests?.get(key) === controller) {
			requests.delete(key);
			if (!requests.size) OWNED_FETCH_REQUESTS.delete(owner);
		}
	}
}

async function fetchWithTimeout(input, init = {}, options = {}) {
	return await runOwnedFetch(input, init, options);
}

async function fetchJsonWithTimeout(input, init = {}, options = {}) {
	return await runOwnedFetch(input, init, options, async (response) => ({
		response,
		data: await response.json(),
	}));
}

function isStagePromptNode(node) {
	if (!node) return false;
	if ([node.comfyClass, node.type].some((value) => TARGET_NODE_CLASSES.has(String(value ?? "")))) return true;
	if (typeof node.title === "string" && hasStagePromptDisplayName(node.title)) return true;
	const widgetNames = new Set((node.widgets ?? []).map((widget) => String(widget?.name ?? "")));
	if (STAGE_WIDGET_SIGNATURE_NAMES.every((name) => widgetNames.has(name))) return true;
	const outputSignatureGroups = new Set();
	for (const output of node.outputs ?? []) {
		const names = [output?.name, output?._qwenTeOriginalName].map((value) => String(value ?? ""));
		for (const name of names) {
			const group = STAGE_OUTPUT_SIGNATURE_GROUPS.get(name);
			if (group) outputSignatureGroups.add(group);
		}
	}
	return outputSignatureGroups.size >= 3;
}

function hasStagePromptDisplayName(value) {
	const text = String(value ?? "");
	return STAGE_DISPLAY_NAME_MARKERS.some((marker) => text.includes(marker));
}

function injectStyles() {
	if (styleInjected) return;
	styleInjected = true;
	const style = document.createElement("style");
	style.textContent = `
	.qwen-te-panel{display:flex;flex-direction:column;gap:10px;padding:7px 0 3px;width:100%;box-sizing:border-box;color:#edf4ff;font-family:"Segoe UI Variable Text","Microsoft YaHei UI","PingFang SC",sans-serif;--qwen-te-surface-0:#0f141b;--qwen-te-surface-1:#141b23;--qwen-te-surface-2:#1b2430;--qwen-te-surface-3:#233040;--qwen-te-border:#425268;--qwen-te-border-soft:rgba(96,118,148,.32);--qwen-te-cyan:#9fd4ff;--qwen-te-cyan-soft:#6d8aa8;--qwen-te-amber:#f0c784;--qwen-te-amber-soft:#987244;--qwen-te-text-soft:#a7b4c7;--qwen-te-text-dim:#7f91a8}
	.qwen-te-panel__hero{position:relative;overflow:hidden;display:flex;flex-direction:column;gap:8px;padding:14px 14px 12px;border:1px solid #465872;border-radius:16px;background:linear-gradient(135deg,rgba(120,168,225,.10),rgba(120,168,225,0) 32%),radial-gradient(120% 160% at 100% 0%,rgba(196,145,66,.12),rgba(196,145,66,0) 34%),linear-gradient(180deg,#1c2530,#10161d);box-shadow:inset 0 1px 0 rgba(255,255,255,.05),0 18px 36px rgba(0,0,0,.24)}
	.qwen-te-panel__hero::before{content:"";position:absolute;left:14px;right:14px;top:10px;height:1px;background:linear-gradient(90deg,rgba(159,212,255,.75),rgba(159,212,255,0));opacity:.78;pointer-events:none}
	.qwen-te-panel__hero::after{content:"";position:absolute;inset:0;pointer-events:none;background:repeating-linear-gradient(180deg,rgba(255,255,255,.02) 0 1px,transparent 1px 28px);opacity:.35}
	.qwen-te-panel__hero-top{display:grid;grid-template-columns:minmax(0,1fr) auto;align-items:flex-start;gap:12px}
	.qwen-te-panel__hero-rail{display:flex;flex-wrap:wrap;gap:6px;justify-content:flex-end;align-content:flex-start}
	.qwen-te-panel__eyebrow{font-size:10px;letter-spacing:.16em;text-transform:uppercase;color:#87a3c2;font-family:Consolas,"Cascadia Code","SFMono-Regular",monospace}
	.qwen-te-panel__hero-title{font-size:16px;font-weight:700;color:#f4f7fb;line-height:1.08;letter-spacing:.02em}
	.qwen-te-panel__hero-caption{font-size:10px;line-height:1.45;color:#a3b3c7;max-width:72ch}
	.qwen-te-panel__hero-badge{border:1px solid rgba(164,122,57,.62);background:linear-gradient(180deg,rgba(81,60,27,.96),rgba(51,37,16,.98));border-radius:11px;padding:4px 8px;font-size:10px;font-weight:700;color:#f6dba4;white-space:nowrap;box-shadow:inset 0 1px 0 rgba(255,255,255,.04)}
	.qwen-te-panel__hero-badge--secondary{border-color:rgba(98,123,156,.56);background:linear-gradient(180deg,rgba(36,50,67,.96),rgba(23,33,45,.98));color:#d7ebff}
	.qwen-te-panel__hero-badge.is-active{border-color:#d4aa62;background:linear-gradient(180deg,#62471d,#443114);color:#fff0ca;box-shadow:0 10px 18px rgba(0,0,0,.18),inset 0 0 0 1px rgba(255,226,170,.08)}
	.qwen-te-panel__hero-history{display:flex;flex-wrap:wrap;gap:6px}
	.qwen-te-panel__hero-history-pill{border:1px solid rgba(98,123,156,.54);background:linear-gradient(180deg,rgba(37,49,65,.94),rgba(24,33,44,.98));border-radius:10px;padding:3px 7px;font-size:9px;font-weight:600;color:#d7e8ff;white-space:nowrap}
	.qwen-te-panel__hero-runtime{display:flex;flex-wrap:wrap;gap:6px}
	.qwen-te-panel__hero-runtime-pill{border:1px solid rgba(164,122,57,.56);background:linear-gradient(180deg,rgba(79,57,23,.95),rgba(53,38,16,.98));border-radius:10px;padding:3px 7px;font-size:9px;font-weight:700;color:#f5d89a;white-space:nowrap}
	.qwen-te-panel__hero-runtime-pill--action{cursor:pointer;transition:transform .08s ease,box-shadow .12s ease,border-color .12s ease,background .12s ease}
	.qwen-te-panel__hero-runtime-pill--action:hover{transform:translateY(-1px);border-color:rgba(238,200,126,.82);box-shadow:0 8px 16px rgba(0,0,0,.18)}
	.qwen-te-panel__hero-runtime-pill--action:active{transform:translateY(1px)}
	.qwen-te-panel__hero-runtime-pill--action:disabled{cursor:not-allowed;opacity:.52;transform:none;box-shadow:none}
	.qwen-te-panel__workspace{display:grid;grid-template-columns:minmax(0,1fr);gap:9px;align-items:start}
	.qwen-te-panel__main{display:flex;flex-direction:column;gap:9px;min-width:0}
	.qwen-te-panel__rail{display:flex;flex-direction:column;gap:9px;min-width:0}
	.qwen-te-panel__signal-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
	.qwen-te-panel__meta{display:grid;grid-template-columns:minmax(0,1fr);gap:8px;align-items:stretch}
	.qwen-te-panel__meta-stack{display:flex;flex-direction:column;gap:8px;min-width:0;height:100%}
	.qwen-te-panel__meta-card{position:relative;overflow:hidden;border:1px solid rgba(84,104,131,.48);border-radius:14px;background:linear-gradient(180deg,rgba(24,32,42,.96),rgba(16,22,30,.98));padding:8px 9px;display:flex;flex-direction:column;gap:6px;min-height:42px;box-shadow:inset 0 1px 0 rgba(255,255,255,.03),0 8px 16px rgba(0,0,0,.10)}
	.qwen-te-panel__meta-card::before{content:"";position:absolute;left:0;right:0;top:0;height:1px;background:linear-gradient(90deg,rgba(159,212,255,.56),rgba(159,212,255,0));pointer-events:none}
	.qwen-te-panel__meta-card--summary{min-height:44px}
	.qwen-te-panel__meta-card--wide{grid-column:1 / -1;min-height:48px}
	.qwen-te-panel__meta-label{font-size:9px;letter-spacing:.14em;text-transform:uppercase;color:#8da7c7;font-family:Consolas,"Cascadia Code","SFMono-Regular",monospace}
	.qwen-te-panel__summary{display:flex;flex-direction:column;gap:4px;min-width:0}
	.qwen-te-panel__summary-line{font-size:11px;line-height:1.35;color:#e9f1ff;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
	.qwen-te-panel__summary-sub{font-size:9.5px;line-height:1.3;color:#92a4bb;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
	.qwen-te-panel__control{border:1px solid rgba(84,104,131,.52);border-radius:14px;background:linear-gradient(180deg,rgba(20,28,38,.98),rgba(13,19,27,.99));padding:9px;display:flex;flex-direction:column;gap:8px;box-shadow:inset 0 1px 0 rgba(255,255,255,.03),0 10px 20px rgba(0,0,0,.12)}
	.qwen-te-panel__control-head{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:0 1px}
	.qwen-te-panel__control-title{font-size:9px;letter-spacing:.14em;text-transform:uppercase;color:#8da7c7;font-family:Consolas,"Cascadia Code","SFMono-Regular",monospace}
	.qwen-te-panel__control-hint{font-size:10px;line-height:1.35;color:#91a4bd;text-align:right;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:72%}
	.qwen-te-panel__control-grid{display:flex;flex-direction:column;gap:8px}
	.qwen-te-panel__control-section{display:flex;flex-direction:column;gap:6px}
	.qwen-te-panel__control-section-title{font-size:9px;letter-spacing:.12em;text-transform:uppercase;color:#7f95ae;font-family:Consolas,"Cascadia Code","SFMono-Regular",monospace}
	.qwen-te-panel__control-row{display:flex;flex-direction:column;gap:5px;min-width:0}
	.qwen-te-panel__control-label{display:none}
	.qwen-te-panel__control-value{display:none}
	.qwen-te-panel__control-options{display:grid;grid-template-columns:repeat(var(--qwen-te-control-cols,3),minmax(0,1fr));gap:5px;min-width:0}
	.qwen-te-panel__control-chip{border:1px solid rgba(88,108,136,.72);border-radius:9px;background:linear-gradient(180deg,rgba(42,55,71,.94),rgba(26,36,48,.98));color:#dbe7f7;cursor:pointer;font-size:9.5px;line-height:1.12;min-height:25px;padding:5px 6px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;transition:background .12s ease,border-color .12s ease,box-shadow .12s ease,color .12s ease}
	.qwen-te-panel__control-chip:hover{border-color:#7f9abc;background:linear-gradient(180deg,rgba(53,69,88,.98),rgba(34,45,58,.99))}
	.qwen-te-panel__control-chip:active{transform:translateY(1px)}
	.qwen-te-panel__control-chip.is-active{border-color:#d3a75e;background:linear-gradient(180deg,#60471e,#423115);color:#fff0ca;box-shadow:0 0 0 1px rgba(255,214,140,.12)}
	.qwen-te-panel__control-chip--toggle{font-weight:700}
	.qwen-te-panel__control-chip--danger.is-active{border-color:#a66a75;background:linear-gradient(180deg,rgba(76,42,49,.98),rgba(48,27,33,.99));color:#ffdce2}
	.qwen-te-panel__advanced{display:flex;flex-direction:column;border:1px solid rgba(84,104,131,.54);border-radius:16px;background:linear-gradient(180deg,rgba(18,25,34,.98),rgba(11,16,23,.99));padding:10px;box-shadow:inset 0 1px 0 rgba(255,255,255,.03),0 12px 24px rgba(0,0,0,.16);max-height:clamp(260px,52vh,520px);min-height:0}
	.qwen-te-panel__advanced.qwen-te-hidden{display:none!important}
	.qwen-te-panel__advanced-scroll{display:flex;flex-direction:column;gap:9px;min-height:0;max-height:inherit;overflow-y:auto;overflow-x:hidden;overscroll-behavior:contain;scrollbar-width:thin;scrollbar-color:rgba(143,166,198,.48) rgba(8,13,20,.28);padding-right:4px;margin-right:-4px}
	.qwen-te-panel__advanced-scroll::-webkit-scrollbar{width:7px}
	.qwen-te-panel__advanced-scroll::-webkit-scrollbar-track{background:rgba(8,13,20,.28);border-radius:999px}
	.qwen-te-panel__advanced-scroll::-webkit-scrollbar-thumb{background:rgba(143,166,198,.48);border-radius:999px;border:2px solid rgba(8,13,20,.28)}
	.qwen-te-panel__advanced-card{border:1px solid rgba(83,103,130,.48);border-radius:14px;background:linear-gradient(180deg,rgba(25,35,47,.96),rgba(16,23,32,.98));padding:10px;display:flex;flex-direction:column;gap:9px;min-width:0;box-shadow:inset 0 1px 0 rgba(255,255,255,.03)}
	.qwen-te-panel__advanced-card--wide{grid-column:auto}
	.qwen-te-panel__advanced-card.is-collapsed{gap:0;padding:8px 10px}
	.qwen-te-panel__advanced-card.is-collapsed .qwen-te-panel__advanced-body{display:none}
	.qwen-te-panel__advanced-head{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:8px;align-items:center;border:0;background:transparent;padding:0;text-align:left;cursor:pointer;width:100%}
	.qwen-te-panel__advanced-title{font-size:10px;font-weight:800;letter-spacing:.12em;text-transform:uppercase;color:#9fd4ff;font-family:Consolas,"Cascadia Code","SFMono-Regular",monospace}
	.qwen-te-panel__advanced-meta{display:flex;align-items:center;gap:6px;min-width:0}
	.qwen-te-panel__advanced-desc{font-size:9.5px;line-height:1.35;color:#8fa2ba;text-align:right;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
	.qwen-te-panel__advanced-toggle{border:1px solid rgba(156,184,220,.26);border-radius:999px;background:rgba(8,13,20,.34);color:#cfe1f7;font-size:8.5px;line-height:1;padding:3px 6px;white-space:nowrap}
	.qwen-te-panel__advanced-body{display:grid;grid-template-columns:1fr;gap:8px}
	.qwen-te-panel__advanced-row{display:flex;flex-direction:column;gap:5px;min-width:0;border:1px solid rgba(74,92,116,.34);border-radius:11px;background:rgba(8,13,20,.18);padding:7px}
	.qwen-te-panel__advanced-label{font-size:10px;line-height:1.25;color:#b7c7dc;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
	.qwen-te-panel__advanced-value{min-width:0}
	.qwen-te-panel__advanced-options{display:grid;grid-template-columns:repeat(var(--qwen-te-advanced-cols,2),minmax(0,1fr));gap:5px}
	.qwen-te-panel__advanced-card--wide .qwen-te-panel__advanced-options{grid-template-columns:repeat(var(--qwen-te-advanced-cols,2),minmax(0,1fr))}
	.qwen-te-panel__advanced-chip{border:1px solid rgba(88,108,136,.72);border-radius:9px;background:linear-gradient(180deg,rgba(42,55,71,.94),rgba(26,36,48,.98));color:#dbe7f7;cursor:pointer;font-size:9.5px;line-height:1.18;min-height:28px;padding:6px 7px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;transition:background .12s ease,border-color .12s ease,box-shadow .12s ease,color .12s ease}
	.qwen-te-panel__advanced-chip:hover{border-color:#7f9abc;background:linear-gradient(180deg,rgba(53,69,88,.98),rgba(34,45,58,.99))}
	.qwen-te-panel__advanced-chip.is-active{border-color:#d3a75e;background:linear-gradient(180deg,#60471e,#423115);color:#fff0ca;box-shadow:0 0 0 1px rgba(255,214,140,.12)}
	.qwen-te-panel__advanced-input,.qwen-te-panel__advanced-select{width:100%;box-sizing:border-box;border:1px solid rgba(75,94,120,.82);border-radius:10px;background:rgba(7,11,16,.86);color:#e9f2ff;padding:7px 9px;font-size:10.5px;line-height:1.35;outline:none;min-height:30px}
	.qwen-te-panel__advanced-select{color-scheme:dark;cursor:pointer;text-overflow:ellipsis}
	.qwen-te-panel__advanced-select option{background:#111923;color:#e9f2ff}
	.qwen-te-panel__advanced-input:focus,.qwen-te-panel__advanced-select:focus{border-color:#d0a250;box-shadow:0 0 0 1px rgba(255,214,140,.14)}
	textarea.qwen-te-panel__advanced-input{min-height:58px;max-height:92px;resize:vertical;overflow:auto;overscroll-behavior:contain}
	.qwen-te-panel__advanced-note{font-size:9.5px;line-height:1.35;color:#8395ad}
	.qwen-te-panel__slots{display:flex;flex-direction:column;gap:7px;max-height:clamp(280px,52vh,480px);overflow-y:auto;overflow-x:hidden;overscroll-behavior:contain;scrollbar-gutter:stable;border:1px solid rgba(84,104,131,.54);border-radius:16px;background:linear-gradient(180deg,rgba(18,25,34,.98),rgba(11,16,23,.99));padding:9px 7px 9px 9px;box-shadow:inset 0 1px 0 rgba(255,255,255,.03),0 12px 24px rgba(0,0,0,.16)}
	.qwen-te-panel__slots.qwen-te-hidden{display:none!important}
	.qwen-te-panel__slots::-webkit-scrollbar{width:8px}
	.qwen-te-panel__slots::-webkit-scrollbar-thumb{border-radius:999px;background:rgba(112,137,170,.42);border:2px solid rgba(12,18,26,.92)}
	.qwen-te-panel__slot-card{border:1px solid rgba(83,103,130,.44);border-radius:12px;background:linear-gradient(180deg,rgba(25,35,47,.88),rgba(16,23,32,.94));padding:7px;display:flex;flex-direction:column;gap:6px;min-width:0;box-shadow:inset 0 1px 0 rgba(255,255,255,.025)}
	.qwen-te-panel__slot-card--custom{align-items:stretch;gap:7px}
	.qwen-te-panel__slot-head{display:flex;align-items:center;justify-content:space-between;gap:6px;min-width:0}
	.qwen-te-panel__slot-title{font-size:10px;font-weight:800;letter-spacing:.04em;color:#9fd4ff;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
	.qwen-te-panel__slot-count{border:1px solid rgba(156,184,220,.24);border-radius:999px;background:rgba(8,13,20,.32);color:#c9d8eb;font-size:8.5px;line-height:1;padding:3px 6px;white-space:nowrap}
	.qwen-te-panel__slot-body{display:grid;grid-template-columns:repeat(auto-fit,minmax(82px,1fr));gap:5px;min-width:0}
	.qwen-te-panel__slot-row{display:flex;min-width:0}
	.qwen-te-panel__slot-label{display:none}
	.qwen-te-panel__slot-select{width:100%;min-width:0;box-sizing:border-box;border:1px solid rgba(75,94,120,.78);border-radius:8px;background:#101923;color:#e6f0ff;padding:5px 6px;font-size:9.5px;line-height:1.15;outline:none;cursor:text}
	.qwen-te-panel__slot-select:focus{border-color:#d0a250;box-shadow:0 0 0 1px rgba(255,214,140,.14)}
	.qwen-te-panel__slot-select.is-filled{border-color:#b88a42;background:linear-gradient(180deg,#493819,#2c2518);color:#fff0ca}
	.qwen-te-panel__slot-select.is-invalid{border-color:#d85b65;background:#2a151a;color:#ffd9dc}
	.qwen-te-panel__slot-custom{width:100%;box-sizing:border-box;border:1px solid rgba(75,94,120,.82);border-radius:10px;background:rgba(7,11,16,.86);color:#e9f2ff;padding:7px 9px;font-size:10.5px;line-height:1.4;outline:none;min-height:52px;max-height:92px;resize:vertical;overflow:auto;overscroll-behavior:contain}
	.qwen-te-panel__slot-custom:focus{border-color:#d0a250;box-shadow:0 0 0 1px rgba(255,214,140,.14)}
	.qwen-te-panel__slot-empty{font-size:9.5px;line-height:1.35;color:#8395ad}
	.qwen-te-panel__quickbar{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:6px;padding:8px;border:1px solid rgba(84,104,131,.48);border-radius:14px;background:linear-gradient(180deg,#171f29,#10161d);box-shadow:inset 0 1px 0 rgba(255,255,255,.03),0 10px 18px rgba(0,0,0,.12)}
	.qwen-te-panel__quickbar .qwen-te-panel__button{min-height:30px;padding:6px 7px;border-radius:10px;font-size:10px;line-height:1.12;gap:0}
	.qwen-te-panel__quickbar .qwen-te-panel__button-icon{display:none}
	.qwen-te-panel__quickbar .qwen-te-panel__button--wide{grid-column:span 2}
	.qwen-te-panel__quickbar .qwen-te-panel__button--primary{grid-column:span 2}
	.qwen-te-panel__quickbar .qwen-te-panel__button--minor{opacity:.88}
	.qwen-te-panel__meta-card--theme{gap:8px}
	.qwen-te-panel__theme-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(98px,1fr));gap:8px}
	.qwen-te-panel__theme-card{position:relative;overflow:hidden;border:1px solid var(--qwen-te-theme-border,rgba(94,116,145,.72));border-radius:14px;padding:10px 11px;min-height:70px;background:radial-gradient(120% 120% at 0% 0%,var(--qwen-te-theme-glow,rgba(120,168,225,.16)),rgba(0,0,0,0) 60%),linear-gradient(180deg,rgba(34,45,59,.98),rgba(21,29,39,.99));display:flex;flex-direction:column;justify-content:space-between;gap:6px;text-align:left;cursor:pointer;box-shadow:inset 0 1px 0 rgba(255,255,255,.04),0 10px 20px rgba(0,0,0,.14);transition:transform .08s ease,border-color .12s ease,box-shadow .12s ease,filter .12s ease}
	.qwen-te-panel__theme-card:hover{transform:translateY(-1px);border-color:rgba(214,226,244,.48);box-shadow:0 12px 22px rgba(0,0,0,.18),inset 0 1px 0 rgba(255,255,255,.05)}
	.qwen-te-panel__theme-card:active{transform:translateY(1px)}
	.qwen-te-panel__theme-card:disabled{cursor:not-allowed;box-shadow:none}
	.qwen-te-panel__theme-card.is-active{border-color:#d7ae68;box-shadow:0 0 0 1px rgba(255,214,140,.18),0 14px 24px rgba(0,0,0,.22),inset 0 0 0 1px rgba(255,231,188,.08);background:radial-gradient(120% 120% at 0% 0%,var(--qwen-te-theme-glow,rgba(120,168,225,.16)),rgba(0,0,0,0) 58%),linear-gradient(180deg,rgba(87,66,28,.98),rgba(55,41,18,.99));color:#fff1cd}
	.qwen-te-panel__theme-card-title{font-size:12px;font-weight:700;letter-spacing:.04em;color:#eef4ff}
	.qwen-te-panel__theme-card-sub{font-size:10px;line-height:1.35;color:#9fb2ca}
	.qwen-te-panel__theme-card.is-active .qwen-te-panel__theme-card-title{color:#fff4dc}
	.qwen-te-panel__theme-card.is-active .qwen-te-panel__theme-card-sub{color:#f4deb0}
	.qwen-te-panel__theme-note{font-size:10px;line-height:1.45;color:#99abc1}
	.qwen-te-panel__display{border:1px solid rgba(84,104,131,.62);border-radius:14px;background:linear-gradient(180deg,rgba(23,31,41,.98),rgba(13,18,25,.99));padding:10px 12px;display:flex;flex-direction:column;gap:7px;height:clamp(170px,23vh,210px);min-height:170px;max-height:210px;flex:0 1 190px;overflow:hidden;box-shadow:inset 0 1px 0 rgba(255,255,255,.03),0 12px 24px rgba(0,0,0,.16)}
	.qwen-te-panel__display-top{display:flex;align-items:flex-start;justify-content:space-between;gap:8px}
	.qwen-te-panel__display-title{font-size:9px;letter-spacing:.14em;text-transform:uppercase;color:#8da7c7;font-family:Consolas,"Cascadia Code","SFMono-Regular",monospace}
	.qwen-te-panel__display-meta{display:flex;align-items:center;gap:6px;min-width:0;margin-left:auto}
	.qwen-te-panel__display-source{min-width:0;max-width:160px;overflow:hidden;text-overflow:ellipsis;border:1px solid rgba(94,116,145,.74);border-radius:10px;padding:3px 7px;background:linear-gradient(180deg,rgba(39,53,69,.96),rgba(25,35,46,.98));font-size:10px;line-height:1.2;color:#d9e5f8;white-space:nowrap}
	.qwen-te-panel__display-expand{border:1px solid rgba(94,116,145,.72);border-radius:10px;padding:3px 8px;background:linear-gradient(180deg,rgba(44,58,74,.96),rgba(29,38,49,.98));font-size:10px;line-height:1.2;color:#e5eefc;cursor:pointer;white-space:nowrap}
	.qwen-te-panel__display-expand:hover{border-color:#cfaa69;background:linear-gradient(180deg,#5c4520,#3f3117);color:#fff0ca}
	.qwen-te-panel__display-search{border-color:rgba(176,137,70,.82);color:#fff0ca}
	.qwen-te-panel__display-tabs{display:flex;flex-wrap:wrap;gap:5px}
	.qwen-te-panel__display-tab{border:1px solid rgba(87,107,133,.72);background:linear-gradient(180deg,rgba(42,55,71,.96),rgba(27,37,49,.98));color:#dfe8f7;border-radius:10px;padding:4px 8px;font-size:10px;line-height:1.1;cursor:pointer}
	.qwen-te-panel__display-tab:hover{background:linear-gradient(180deg,rgba(52,68,87,.98),rgba(34,45,58,.98));border-color:#7592b5}
	.qwen-te-panel__display-tab.is-active{border-color:#cfa864;background:linear-gradient(180deg,#5f4821,#423216);color:#fff0ca;box-shadow:inset 0 0 0 1px rgba(255,227,180,.08)}
	.qwen-te-panel__display-screen{flex:1 1 0;min-height:0;height:100%;overflow:auto;border:1px solid rgba(49,65,82,.92);border-radius:11px;background:linear-gradient(180deg,rgba(32,45,60,.16),rgba(0,0,0,0) 30%),repeating-linear-gradient(180deg,rgba(143,166,194,.05) 0 1px,transparent 1px 24px),#0a0e13;padding:9px 11px;font-size:10.5px;line-height:1.54;color:#d9e4f5;white-space:pre-wrap;word-break:break-word;scrollbar-gutter:stable both-edges;overscroll-behavior:contain;font-family:Consolas,'SFMono-Regular','Cascadia Code',monospace}
	.qwen-te-panel__display-screen.is-empty{color:#90a0b4}
	.qwen-te-panel__display-screen--smart{display:flex;flex-direction:column;gap:8px;font-family:"Segoe UI Variable Text","Microsoft YaHei UI","PingFang SC",sans-serif;white-space:normal}
	.qwen-te-panel__smart-input{width:100%;min-height:58px;max-height:88px;resize:none;box-sizing:border-box;border:1px solid rgba(75,94,120,.82);border-radius:10px;background:rgba(7,11,16,.88);color:#e9f2ff;padding:8px 10px;font-size:11px;line-height:1.45;outline:none;overflow:auto;overscroll-behavior:contain}
	.qwen-te-panel__smart-input:focus{border-color:#d0a250;box-shadow:0 0 0 1px rgba(255,214,140,.14)}
	.qwen-te-panel__smart-row{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:8px;align-items:center}
	.qwen-te-panel__smart-hint{min-width:0;font-size:10px;line-height:1.35;color:#91a4bd;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
	.qwen-te-panel__smart-button{border:1px solid #c79948;border-radius:10px;background:linear-gradient(180deg,#5f4821,#423216);color:#fff0ca;font-size:10.5px;font-weight:700;padding:7px 13px;cursor:pointer;white-space:nowrap}
	.qwen-te-panel__smart-button:hover{border-color:#e1b96f;background:linear-gradient(180deg,#705527,#4c3919)}
	.qwen-te-panel__smart-button:disabled{cursor:not-allowed;opacity:.72;filter:saturate(.78);box-shadow:none}
	.qwen-te-panel__smart-result{min-height:40px;border:1px solid rgba(49,65,82,.76);border-radius:10px;background:rgba(4,7,11,.42);padding:8px 10px;color:#d9e4f5;font:10.5px/1.54 Consolas,'SFMono-Regular','Cascadia Code',monospace;white-space:pre-wrap;word-break:break-word;display:flex;flex-direction:column;gap:4px}
	.qwen-te-panel__smart-result-lead{font-size:9px;letter-spacing:.12em;text-transform:uppercase;color:#91a4bd;font-family:Consolas,"Cascadia Code","SFMono-Regular",monospace}
	.qwen-te-panel__smart-result-body{display:flex;flex-direction:column;gap:4px;white-space:normal;word-break:break-word}
	.qwen-te-panel__smart-preview-line{min-width:0;line-height:1.55;color:#d9e4f5;white-space:pre-wrap;word-break:break-word}
	.qwen-te-panel__smart-preview-line--hero{color:#fff1ca}
	.qwen-te-panel__smart-preview-line--key{padding:4px 7px;border:1px solid rgba(111,136,168,.28);border-radius:9px;background:linear-gradient(180deg,rgba(44,56,72,.34),rgba(23,31,41,.22))}
	.qwen-te-panel__smart-preview-line[data-smart-key="subject"]{border-color:rgba(209,166,91,.38);background:linear-gradient(180deg,rgba(79,58,25,.28),rgba(31,26,18,.24))}
	.qwen-te-panel__smart-preview-line[data-smart-key="scene"]{border-color:rgba(86,167,177,.32);background:linear-gradient(180deg,rgba(24,67,76,.24),rgba(15,29,37,.22))}
	.qwen-te-panel__smart-preview-line[data-smart-key="lens"]{border-color:rgba(106,145,205,.34);background:linear-gradient(180deg,rgba(34,54,88,.26),rgba(18,28,43,.22))}
	.qwen-te-panel__smart-preview-line[data-smart-key="light"]{border-color:rgba(198,127,90,.34);background:linear-gradient(180deg,rgba(78,42,29,.25),rgba(31,22,18,.22))}
	.qwen-te-panel__smart-preview-label{color:#f1d396;font-weight:700;letter-spacing:.03em}
	.qwen-te-panel__smart-preview-value{display:inline-flex;flex-wrap:wrap;gap:4px 5px;color:#e6eef9}
	.qwen-te-panel__smart-preview-chip{display:inline-flex;align-items:center;max-width:100%;border:1px solid rgba(112,140,173,.42);border-radius:999px;background:linear-gradient(180deg,rgba(37,51,68,.68),rgba(18,25,34,.54));padding:1px 6px;color:#dce9fb;line-height:1.35;white-space:normal}
	.qwen-te-panel__smart-result.is-empty .qwen-te-panel__smart-result-lead{color:#93a0b2}
	.qwen-te-panel__smart-result.is-empty .qwen-te-panel__smart-result-body{color:#90a0b4}
	.qwen-te-panel__display-screen--blocks{display:flex;flex-direction:column;gap:7px;font-family:"Segoe UI Variable Text","Microsoft YaHei UI","PingFang SC",sans-serif;white-space:normal}
	.qwen-te-panel__block-toolbar{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px}
	.qwen-te-panel__block-button{border:1px solid rgba(91,114,144,.78);border-radius:9px;background:linear-gradient(180deg,rgba(42,55,71,.96),rgba(27,37,49,.98));color:#e8f2ff;font-size:10px;font-weight:700;line-height:1.1;min-height:28px;padding:6px 7px;cursor:pointer;transition:background .12s ease,border-color .12s ease,transform .08s ease}
	.qwen-te-panel__block-button:hover{border-color:#82a0c6;background:linear-gradient(180deg,rgba(54,71,91,.98),rgba(35,47,61,.99));transform:translateY(-1px)}
	.qwen-te-panel__block-button:active{transform:translateY(1px)}
	.qwen-te-panel__block-button--run{border-color:#d0a250;background:linear-gradient(180deg,#654b1f,#473415);color:#fff0ca}
	.qwen-te-panel__block-button--danger{border-color:#9d6670;background:linear-gradient(180deg,rgba(69,40,46,.98),rgba(42,24,29,.99));color:#f6dce2}
	.qwen-te-panel__block-status{font-size:10px;line-height:1.35;color:#91a4bd;white-space:normal}
	.qwen-te-panel__block-list{display:flex;flex-direction:column;gap:3px;min-height:0;border:1px solid rgba(49,65,82,.92);border-radius:11px;background:linear-gradient(180deg,rgba(32,45,60,.16),rgba(0,0,0,0) 30%),repeating-linear-gradient(180deg,rgba(143,166,194,.045) 0 1px,transparent 1px 24px),#0a0e13;padding:5px;overflow:auto;scrollbar-gutter:stable;overscroll-behavior:contain}
	.qwen-te-panel__block-card{border:1px solid rgba(82,105,135,.34);border-radius:8px;background:rgba(16,24,34,.62);padding:4px 5px;display:grid;grid-template-columns:minmax(70px,.34fr) minmax(0,1fr) auto;gap:6px;align-items:center;min-height:30px;cursor:grab;box-shadow:none}
	.qwen-te-panel__block-card--custom{grid-template-columns:minmax(0,1fr) auto;align-items:start;padding:6px;gap:6px;border-color:rgba(94,119,151,.46);background:linear-gradient(180deg,rgba(18,29,40,.72),rgba(9,14,20,.78))}
	.qwen-te-panel__block-card:active{cursor:grabbing}
	.qwen-te-panel__block-card.is-drag-over{border-color:#d0a250;background:rgba(38,32,17,.82);box-shadow:0 0 0 1px rgba(255,214,140,.12)}
	.qwen-te-panel__block-card.is-locked{border-color:rgba(187,142,64,.52);background:rgba(48,38,19,.72)}
	.qwen-te-panel__block-head{display:contents}
	.qwen-te-panel__block-head>div:first-child{grid-column:1;grid-row:1;min-width:0;display:flex;align-items:baseline;gap:5px}
	.qwen-te-panel__block-card--custom .qwen-te-panel__block-head>div:first-child{align-items:center}
	.qwen-te-panel__block-title{font-size:10.5px;font-weight:800;color:#f3f8ff;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
	.qwen-te-panel__block-sub{display:none}
	.qwen-te-panel__block-actions{grid-column:3;grid-row:1;display:flex;gap:3px;align-items:center;justify-content:flex-end}
	.qwen-te-panel__block-card--custom .qwen-te-panel__block-actions{grid-column:2}
	.qwen-te-panel__block-action{border:1px solid rgba(105,129,160,.48);border-radius:7px;background:rgba(8,13,20,.22);color:#d9e6f7;font-size:9px;font-weight:700;line-height:1;min-width:22px;min-height:20px;padding:0 5px;cursor:pointer}
	.qwen-te-panel__block-action:hover{border-color:#cfa864;color:#fff0ca}
	.qwen-te-panel__block-chip-list{grid-column:2;grid-row:1;display:flex;flex-wrap:wrap;gap:3px;min-width:0;align-items:center}
	.qwen-te-panel__block-card--custom .qwen-te-panel__block-chip-list{grid-column:1/-1;grid-row:2;display:grid;grid-template-columns:repeat(auto-fill,minmax(128px,1fr));gap:5px 6px;align-items:start;max-height:132px;overflow:auto;overscroll-behavior:contain;scrollbar-gutter:stable;padding:7px 8px;border:1px solid rgba(57,76,99,.78);border-radius:9px;background:linear-gradient(180deg,rgba(6,10,15,.82),rgba(7,11,16,.68))}
	.qwen-te-panel__block-chip{display:inline-flex;align-items:center;max-width:100%;border:1px solid rgba(112,140,173,.42);border-radius:999px;background:linear-gradient(180deg,rgba(37,51,68,.62),rgba(18,25,34,.50));padding:1px 6px;color:#dce9fb;font-size:9.5px;line-height:1.25;white-space:normal}
	.qwen-te-panel__block-card--custom .qwen-te-panel__block-chip{width:100%;max-width:100%;justify-content:space-between;padding:2px 7px;line-height:1.35;background:linear-gradient(180deg,rgba(35,49,66,.72),rgba(15,22,31,.62))}
	.qwen-te-panel__block-chip span:first-child{min-width:0;overflow:hidden;text-overflow:ellipsis;word-break:break-word;overflow-wrap:anywhere}
	button.qwen-te-panel__block-chip{gap:4px;font-family:inherit;cursor:pointer;text-align:left}
	button.qwen-te-panel__block-chip:hover{border-color:#cfa864;color:#fff0ca;background:linear-gradient(180deg,rgba(63,51,28,.76),rgba(31,25,18,.64))}
	.qwen-te-panel__block-chip-remove{font-size:10px;line-height:1;color:#d7a9b4;opacity:.82}
	button.qwen-te-panel__block-chip:hover .qwen-te-panel__block-chip-remove{color:#ffd6dd;opacity:1}
	.qwen-te-panel__block-text{grid-column:2;grid-row:1;width:100%;box-sizing:border-box;border:1px solid rgba(75,94,120,.72);border-radius:8px;background:rgba(7,11,16,.72);color:#e9f2ff;padding:6px 8px;font-size:10.5px;line-height:1.35;outline:none;min-height:34px;max-height:96px;resize:vertical;overflow:auto;overscroll-behavior:contain}
	.qwen-te-panel__block-text:focus{border-color:#d0a250;box-shadow:0 0 0 1px rgba(255,214,140,.14)}
	.qwen-te-panel__block-empty{border:1px dashed rgba(113,139,172,.42);border-radius:8px;padding:8px;color:#91a4bd;font-size:10.5px;line-height:1.4;text-align:center;background:rgba(7,11,16,.22)}
	.qwen-te-panel__actions-shell{display:none}
	.qwen-te-panel__actions-shell::before{content:"操作";position:absolute;top:-8px;left:14px;padding:0 6px;background:#10161d;color:#7f98b4;font-size:9px;letter-spacing:.16em;text-transform:uppercase;font-family:Consolas,"Cascadia Code","SFMono-Regular",monospace}
	.qwen-te-panel__actions-group{display:flex;flex-direction:column;gap:7px;padding:9px 9px 10px;border:1px solid rgba(83,98,120,.34);border-radius:13px;background:linear-gradient(180deg,rgba(29,40,53,.96),rgba(18,27,37,.98));box-shadow:inset 0 1px 0 rgba(255,255,255,.03)}
	.qwen-te-panel__actions-group--compact{padding:7px 8px 8px}
	.qwen-te-panel__actions-label{font-size:9px;letter-spacing:.14em;text-transform:uppercase;color:#9bb2cf;padding:0 1px;display:flex;align-items:center;justify-content:space-between;font-family:Consolas,"Cascadia Code","SFMono-Regular",monospace}
	.qwen-te-panel__actions-label::after{content:"";flex:1 1 auto;height:1px;margin-left:6px;background:linear-gradient(90deg,rgba(136,165,205,.3),rgba(136,165,205,0))}
	.qwen-te-panel__actions{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px}
	.qwen-te-panel__actions--triple{grid-template-columns:repeat(2,minmax(0,1fr))}
	.qwen-te-panel__actions--manager{grid-template-columns:repeat(2,minmax(0,1fr))}
	.qwen-te-panel__actions--double{grid-template-columns:repeat(2,minmax(0,1fr))}
	.qwen-te-panel__actions-tools{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px}
	.qwen-te-panel__button{border:1px solid rgba(92,114,142,.84);background:linear-gradient(180deg,rgba(47,61,77,.98),rgba(31,41,52,.99));color:#f4f7fb;border-radius:11px;padding:8px 7px 7px;cursor:pointer;font-size:10.5px;line-height:1.16;font-weight:600;width:100%;text-align:center;min-height:38px;transition:background .12s ease,border-color .12s ease,transform .08s ease,box-shadow .12s ease,filter .12s ease;display:flex;align-items:center;justify-content:center;gap:6px;box-shadow:inset 0 1px 0 rgba(255,255,255,.03)}
	.qwen-te-panel__button:hover{background:linear-gradient(180deg,rgba(57,74,93,.99),rgba(35,46,58,.99));border-color:#7a96ba;box-shadow:0 8px 16px rgba(0,0,0,.20),inset 0 1px 0 rgba(255,255,255,.05);transform:translateY(-1px)}
	.qwen-te-panel__button:active{transform:translateY(1px)}
	.qwen-te-panel__button:disabled{opacity:.68;cursor:wait;box-shadow:none}
	.qwen-te-panel__button--cool{background:linear-gradient(180deg,rgba(43,66,88,.98),rgba(28,48,67,.99));border-color:#6286ad}
	.qwen-te-panel__button--accent{background:linear-gradient(180deg,rgba(52,61,83,.98),rgba(34,42,58,.99));border-color:#7a8cba}
	.qwen-te-panel__button--warm{background:linear-gradient(180deg,rgba(80,60,28,.98),rgba(54,40,17,.99));border-color:#a27a3f;color:#f7dfac}
	.qwen-te-panel__button--run{background:linear-gradient(180deg,rgba(92,69,24,.99),rgba(64,46,15,.99));border-color:#d0a250;color:#fff0c6;box-shadow:0 10px 20px rgba(0,0,0,.22)}
	.qwen-te-panel__button--subtle{background:linear-gradient(180deg,rgba(40,47,58,.98),rgba(25,31,39,.99));color:#d8dde6}
	.qwen-te-panel__button--danger{background:linear-gradient(180deg,rgba(69,40,46,.98),rgba(42,24,29,.99));border-color:#9d6670;color:#f2d7dc}
	.qwen-te-panel__button--wide{grid-column:1 / -1}
	.qwen-te-panel__button.is-active{border-color:#d7ae68;background:linear-gradient(180deg,#654b1f,#473415);color:#fff1cc;box-shadow:0 0 0 1px rgba(255,214,140,.18),0 12px 20px rgba(0,0,0,.22)}
	.qwen-te-panel__button.is-busy{filter:saturate(.92);box-shadow:inset 0 0 0 1px rgba(255,255,255,.04)}
	.qwen-te-panel__button-icon{display:inline-flex;align-items:center;justify-content:center;min-width:22px;height:18px;border:1px solid rgba(136,163,200,.32);border-radius:7px;background:rgba(10,14,19,.24);font:700 9px/1 Consolas,"Cascadia Code","SFMono-Regular",monospace;letter-spacing:.04em;color:#d8e9ff;box-shadow:inset 0 1px 0 rgba(255,255,255,.03)}
	.qwen-te-panel__button-label{display:inline-block;overflow:hidden;text-overflow:ellipsis;white-space:normal;line-height:1.16}
	.qwen-te-model{display:flex;flex-direction:column;gap:8px;padding:8px 0 3px;width:100%;box-sizing:border-box;color:#edf4ff;font-family:"Segoe UI Variable Text","Microsoft YaHei UI","PingFang SC",sans-serif}
	.qwen-te-model--modal{padding:0;max-width:680px;margin:0 auto}
	.qwen-te-model--modal .qwen-te-model__card{padding:14px;gap:12px}
	.qwen-te-model--modal .qwen-te-model__button{min-height:34px;font-size:11px}
	.qwen-te-model--modal .qwen-te-model__select{font-size:11px;padding:8px 10px}
	.qwen-te-model__card{border:1px solid rgba(84,104,131,.62);border-radius:14px;background:linear-gradient(180deg,rgba(23,31,41,.98),rgba(13,18,25,.99));padding:9px;display:flex;flex-direction:column;gap:8px;box-shadow:inset 0 1px 0 rgba(255,255,255,.03),0 12px 24px rgba(0,0,0,.16)}
	.qwen-te-model__head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px}
	.qwen-te-model__title{font-size:10px;font-weight:800;letter-spacing:.12em;text-transform:uppercase;color:#9fd4ff;font-family:Consolas,"Cascadia Code","SFMono-Regular",monospace}
	.qwen-te-model__status{font-size:10px;line-height:1.35;color:#dce8f7;text-align:right;max-width:62%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
	.qwen-te-model__runtime-status{min-height:28px;display:flex;align-items:center;padding:6px 8px;border:1px solid #344250;border-radius:6px;background:#18212a;color:#c8d5e3;font-size:10px;line-height:1.45}
	.qwen-te-model__runtime-status[data-tone="ready"],.qwen-te-model__runtime-status[data-tone="success"]{border-color:#39735a;background:#14271f;color:#bce8d0}
	.qwen-te-model__runtime-status[data-tone="warn"]{border-color:#80642e;background:#2c2414;color:#f2d690}
	.qwen-te-model__runtime-status[data-tone="error"]{border-color:#83454a;background:#2d191c;color:#f2b9bd}
	.qwen-te-model__grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px}
	.qwen-te-model__grid--wide{grid-template-columns:repeat(4,minmax(0,1fr))}
	.qwen-te-model__button{border:1px solid rgba(92,114,142,.84);background:linear-gradient(180deg,rgba(47,61,77,.98),rgba(31,41,52,.99));color:#f4f7fb;border-radius:10px;padding:6px 6px;cursor:pointer;font-size:10px;line-height:1.15;font-weight:700;min-height:29px;text-align:center;transition:background .12s ease,border-color .12s ease,transform .08s ease,box-shadow .12s ease}
	.qwen-te-model__button:hover{background:linear-gradient(180deg,rgba(57,74,93,.99),rgba(35,46,58,.99));border-color:#7a96ba;box-shadow:0 8px 16px rgba(0,0,0,.20);transform:translateY(-1px)}
	.qwen-te-model__button:active{transform:translateY(1px)}
	.qwen-te-model__button:disabled{opacity:.46;cursor:not-allowed;transform:none;box-shadow:none}
	.qwen-te-model__button.is-active{border-color:#d7ae68;background:linear-gradient(180deg,#654b1f,#473415);color:#fff1cc;box-shadow:0 0 0 1px rgba(255,214,140,.18)}
	.qwen-te-model__section{display:flex;flex-direction:column;gap:5px}
	.qwen-te-model__section--card{border:1px solid rgba(77,96,121,.44);border-radius:13px;background:linear-gradient(180deg,rgba(20,28,38,.86),rgba(13,19,27,.94));padding:10px;gap:8px}
	.qwen-te-model__section-head{display:flex;align-items:center;justify-content:space-between;gap:10px}
	.qwen-te-model__section-title{font-size:9px;color:#8ea4bd;letter-spacing:.08em;text-transform:uppercase;font-family:Consolas,"Cascadia Code","SFMono-Regular",monospace}
	.qwen-te-model__section-value{font-size:10px;color:#f1d498;line-height:1.25;text-align:right;max-width:58%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
	.qwen-te-model__select-row{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:6px}
	.qwen-te-model__select{border:1px solid rgba(76,96,122,.78);border-radius:10px;background:linear-gradient(180deg,rgba(35,47,61,.96),rgba(21,30,40,.98));color:#eaf2ff;font-size:10px;line-height:1.2;padding:6px 8px;min-width:0}
	.qwen-te-panel__slot-select,.qwen-te-model__select{color-scheme:dark}
	.qwen-te-model__select option,.qwen-te-model__select optgroup{background-color:#101923!important;color:#e6f0ff!important}
	.qwen-te-model__select option:checked{background-color:#493819!important;color:#fff0ca!important}
	.qwen-te-model__select option:disabled{background-color:#101923!important;color:#78889b!important}
	.qwen-te-model__api-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px}
	.qwen-te-model__input{border:1px solid rgba(76,96,122,.78);border-radius:10px;background:linear-gradient(180deg,rgba(14,19,26,.98),rgba(9,13,18,.99));color:#eaf2ff;font-size:10px;line-height:1.3;padding:7px 9px;min-width:0;outline:none}
	textarea.qwen-te-model__input{min-height:58px;resize:vertical;font-family:Consolas,"Cascadia Code","SFMono-Regular",monospace}
	.qwen-te-model__input:focus{border-color:#d7ae68;box-shadow:0 0 0 1px rgba(255,214,140,.18)}
	.qwen-te-model__settings{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
	.qwen-te-model__quickbar{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px}
	.qwen-te-model__hint{font-size:9.5px;line-height:1.35;color:#91a3b9;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
	.qwen-te-panel__status{color:#d6e1f1;line-height:1.46;white-space:normal;overflow:hidden;display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:3}
	.qwen-te-modal{position:fixed;inset:0;background:rgba(0,0,0,.72);display:flex;align-items:center;justify-content:center;z-index:10001;padding:20px}
	.qwen-te-modal__dialog{width:min(1180px,96vw);max-height:92vh;background:#171717;border:1px solid #404040;border-radius:16px;box-shadow:0 24px 80px rgba(0,0,0,.45);display:flex;flex-direction:column;overflow:hidden;color:#f3f3f3}
	.qwen-te-modal__header{display:flex;align-items:center;justify-content:space-between;padding:18px 20px 14px;border-bottom:1px solid #303030;gap:12px}
	.qwen-te-modal__title{font-size:18px;font-weight:700}
	.qwen-te-modal__subtitle{font-size:12px;color:#b5b5b5;margin-top:4px}
	.qwen-te-modal__body{overflow:auto;padding:16px 20px 20px;display:flex;flex-direction:column;gap:16px}
	.qwen-te-modal__toolbar{display:flex;flex-wrap:wrap;gap:10px;align-items:center}
	.qwen-te-modal__details{border:1px solid rgba(84,102,128,.42);border-radius:14px;background:linear-gradient(180deg,rgba(24,31,42,.9),rgba(18,24,33,.96));padding:0;overflow:hidden}
	.qwen-te-modal__details[open]{padding-bottom:10px}
	.qwen-te-modal__details-summary{cursor:pointer;list-style:none;padding:10px 12px;font-size:11px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:#dbe8fb;display:flex;align-items:center;justify-content:space-between;gap:10px}
	.qwen-te-modal__details-summary::-webkit-details-marker{display:none}
	.qwen-te-modal__details-summary::after{content:"展开";font-size:10px;font-weight:600;letter-spacing:0;color:#9fb1c8;text-transform:none}
	.qwen-te-modal__details[open]>.qwen-te-modal__details-summary::after{content:"收起"}
	.qwen-te-modal__stage-output-body{display:flex;flex-direction:column;gap:12px;min-height:0}
	.qwen-te-modal__stage-output-toolbar{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:10px}
	.qwen-te-modal__stage-output-toolbar-main{display:flex;flex-wrap:wrap;align-items:center;gap:8px;min-width:0}
	.qwen-te-modal__stage-output-toolbar-side{display:flex;flex-wrap:wrap;align-items:center;justify-content:flex-end;gap:8px;min-width:0}
	.qwen-te-modal__stage-output-source{border:1px solid #536277;border-radius:999px;padding:3px 9px;background:linear-gradient(180deg,#273240,#1f2732);font-size:11px;line-height:1.2;color:#dbe6f8;white-space:nowrap}
	.qwen-te-modal__stage-output-tabs{display:flex;flex-wrap:wrap;gap:6px}
	.qwen-te-modal__stage-output-tab{border:1px solid #4b5668;background:linear-gradient(180deg,#2b3441,#222a35);color:#dfe8f7;border-radius:999px;padding:5px 10px;font-size:11px;line-height:1.1;cursor:pointer}
	.qwen-te-modal__stage-output-tab:hover{background:linear-gradient(180deg,#354151,#27303c);border-color:#60758f}
	.qwen-te-modal__stage-output-tab.is-active{border-color:#caa55b;background:linear-gradient(180deg,#5a4620,#3e3018);color:#fff0ca}
	.qwen-te-modal__nsfw-tabs{margin-bottom:2px}
	.qwen-te-modal[data-qwen-modal="nsfw-workspace"] .qwen-te-modal__workspace{display:grid;grid-template-columns:minmax(0,1.5fr) minmax(280px,.82fr);gap:12px;align-items:start;min-height:0}
	.qwen-te-modal[data-qwen-modal="nsfw-workspace"] .qwen-te-modal__workspace-main,
	.qwen-te-modal[data-qwen-modal="nsfw-workspace"] .qwen-te-modal__workspace-side{display:flex;flex-direction:column;gap:10px;min-width:0;min-height:0}
	.qwen-te-modal[data-qwen-modal="nsfw-workspace"] .qwen-te-modal__workspace-side{max-height:min(72vh,720px);overflow:auto;overscroll-behavior:contain;padding-right:4px;scrollbar-gutter:stable}
	.qwen-te-modal[data-qwen-modal="nsfw-workspace"] .qwen-te-modal__surface{display:flex;flex-direction:column;gap:10px;padding:12px 14px;border:1px solid rgba(74,89,110,.56);border-radius:14px;background:linear-gradient(180deg,rgba(24,30,39,.98),rgba(19,24,32,.98));box-shadow:inset 0 1px 0 rgba(255,255,255,.03),0 16px 32px rgba(0,0,0,.16);min-width:0}
	.qwen-te-modal[data-qwen-modal="nsfw-workspace"] .qwen-te-modal__surface-title{font-size:12px;font-weight:700;color:#f1f6ff;letter-spacing:.03em}
	.qwen-te-modal[data-qwen-modal="nsfw-workspace"] .qwen-te-modal__surface-desc{font-size:10.5px;line-height:1.45;color:#9fb1c8;margin-top:3px}
	.qwen-te-modal[data-qwen-modal="nsfw-workspace"] .qwen-te-modal__surface-meta{display:flex;flex-wrap:wrap;gap:6px}
	.qwen-te-modal[data-qwen-modal="nsfw-workspace"] .qwen-te-modal__surface-pill{border:1px solid rgba(92,113,139,.54);border-radius:999px;padding:4px 9px;background:linear-gradient(180deg,#253243,#1d2734);font-size:10px;line-height:1.2;color:#dbe8fb;white-space:nowrap}
	.qwen-te-modal[data-qwen-modal="nsfw-workspace"] .qwen-te-modal__surface-pill--accent{border-color:#b48a43;background:linear-gradient(180deg,#5d451c,#433113);color:#fff0cb}
	.qwen-te-modal[data-qwen-modal="nsfw-workspace"] .qwen-te-modal__toolbar-row{grid-template-columns:minmax(140px,220px) minmax(0,1fr);align-items:center;padding:0}
	.qwen-te-modal[data-qwen-modal="nsfw-workspace"] .qwen-te-modal__toolbar-section-title{padding:0}
	.qwen-te-modal[data-qwen-modal="nsfw-workspace"] .qwen-te-modal__search,
	.qwen-te-modal[data-qwen-modal="nsfw-workspace"] .qwen-te-modal__textarea{width:100%;min-width:0}
	.qwen-te-modal[data-qwen-modal="nsfw-workspace"] .qwen-te-modal__search{flex:0 0 auto;box-sizing:border-box;min-height:36px;height:auto;padding:8px 10px;font-size:12px;line-height:1.25}
	.qwen-te-modal[data-qwen-modal="nsfw-workspace"] .qwen-te-modal__textarea{background:#101010;border:1px solid #444;color:#fff;border-radius:10px;padding:10px 12px;font-size:13px;resize:vertical;line-height:1.45}
	.qwen-te-modal[data-qwen-modal="nsfw-workspace"] .qwen-te-modal__footer-button{border-color:#56657b;background:linear-gradient(180deg,#2d3a4b,#253141);color:#f1f6ff;transition:background .14s ease,border-color .14s ease,box-shadow .14s ease,transform .08s ease}
	.qwen-te-modal[data-qwen-modal="nsfw-workspace"] .qwen-te-modal__footer-button:hover{background:linear-gradient(180deg,#37475a,#2c3a4b);border-color:#6f89ad;box-shadow:0 8px 16px rgba(0,0,0,.16)}
	.qwen-te-modal[data-qwen-modal="nsfw-workspace"] .qwen-te-modal__footer-button--primary{background:#8a6730;border-color:#b48a43;color:#fff4df}
	.qwen-te-modal[data-qwen-modal="nsfw-workspace"] .qwen-te-modal__footer-button--accent{background:linear-gradient(180deg,#5c4520,#423116);border-color:#bd9243;color:#fff0cb}
	.qwen-te-modal[data-qwen-modal="nsfw-workspace"] .qwen-te-modal__status{padding:8px 10px;border:1px solid rgba(77,94,118,.4);border-radius:10px;background:linear-gradient(180deg,rgba(33,43,56,.92),rgba(25,32,42,.96))}
	.qwen-te-modal__stage-output-metrics{display:flex;flex-wrap:wrap;gap:6px}
	.qwen-te-modal__stage-output-metric{border:1px solid #48596f;border-radius:999px;padding:3px 8px;background:linear-gradient(180deg,#243040,#1b2430);font-size:10px;line-height:1.2;color:#cfe0f7;white-space:nowrap}
	.qwen-te-modal__stage-output-view-tabs{display:flex;flex-wrap:wrap;gap:6px}
	.qwen-te-modal__stage-output-view-tab{border:1px solid #4f6075;background:linear-gradient(180deg,#293340,#202833);color:#deebfb;border-radius:999px;padding:4px 9px;font-size:10px;line-height:1.15;cursor:pointer}
	.qwen-te-modal__stage-output-view-tab:hover{background:linear-gradient(180deg,#344051,#27313d);border-color:#6680a1}
	.qwen-te-modal__stage-output-view-tab.is-active{border-color:#caa55b;background:linear-gradient(180deg,#5a4620,#3e3018);color:#fff0ca}
	.qwen-te-modal__stage-output-actions{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
	.qwen-te-modal__stage-output-screen{flex:1 1 auto;min-height:min(62vh,460px);max-height:min(70vh,760px);overflow:auto;border:1px solid #314152;border-radius:12px;background:#0a0e13;padding:14px 16px;font-size:12px;line-height:1.6;color:#d9e4f5;white-space:pre-wrap;word-break:break-word;scrollbar-gutter:stable both-edges;overscroll-behavior:contain;font-family:Consolas,'SFMono-Regular','Cascadia Code',monospace}
	.qwen-te-modal[data-qwen-modal="stage-output"] .qwen-te-modal__stage-output-body{flex:1 1 auto;overflow:hidden}
	.qwen-te-modal__stage-output-screen.qwen-te-panel__display-screen--blocks{min-height:min(58vh,520px);max-height:min(72vh,760px);padding-bottom:42px;overflow:auto}
	.qwen-te-modal__stage-output-screen.qwen-te-panel__display-screen--blocks .qwen-te-panel__block-list{overflow:visible;min-height:auto;padding-bottom:42px}
	.qwen-te-modal__stage-output-screen.is-empty{color:#90a0b4}
	.qwen-te-modal__stage-output-footer{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:10px;padding-top:10px;border-top:1px solid rgba(83,98,120,.24)}
	.qwen-te-modal__stage-output-note{flex:1 1 280px;min-width:0;font-size:11px;line-height:1.45;color:#9fb1c8}
	.qwen-te-modal__toolbar--online-search{display:grid;grid-template-columns:minmax(0,1fr) auto;align-items:stretch}
	.qwen-te-modal__toolbar--online-actions{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));align-items:stretch}
	.qwen-te-modal__toolbar--online-search .qwen-te-modal__search{min-width:0}
	.qwen-te-modal__toolbar--online-search .qwen-te-modal__footer-button,
	.qwen-te-modal__toolbar--online-actions .qwen-te-modal__footer-button{width:100%;text-align:center;white-space:nowrap}
	.qwen-te-modal__toolbar--preset-save{display:grid;grid-template-columns:minmax(0,1fr) auto;align-items:stretch}
	.qwen-te-modal__toolbar--preset-save .qwen-te-modal__search{min-width:0}
	.qwen-te-modal__toolbar--preset-save .qwen-te-modal__footer-button{white-space:nowrap}
	.qwen-te-modal__toolbar--preset-batch{display:flex;flex-direction:column;gap:12px;align-items:stretch}
	.qwen-te-modal__batch-dashboard{display:grid;grid-template-columns:minmax(0,1.58fr) minmax(330px,.92fr);gap:12px;align-items:start}
	.qwen-te-modal__batch-dashboard-main,.qwen-te-modal__batch-dashboard-side{display:flex;flex-direction:column;gap:12px;min-width:0}
	.qwen-te-modal__batch-section{display:flex;flex-direction:column;gap:10px;padding:12px;border:1px solid #3e4f67;border-radius:14px;background:radial-gradient(120% 120% at 0% 0%,rgba(93,135,201,.16),rgba(93,135,201,0) 58%),linear-gradient(180deg,#1d2734,#161f2a);box-shadow:inset 0 1px 0 rgba(255,255,255,.04),0 12px 24px rgba(0,0,0,.18);min-width:0}
	.qwen-te-modal__batch-section--full,.qwen-te-modal__batch-section--wide{grid-column:auto}
	.qwen-te-modal__batch-section--meta{background:radial-gradient(120% 120% at 0% 0%,rgba(115,165,226,.18),rgba(115,165,226,0) 56%),linear-gradient(180deg,#1d2734,#161f2a)}
	.qwen-te-modal__batch-section--manage{background:linear-gradient(180deg,rgba(36,48,64,.9),rgba(26,36,48,.94))}
	.qwen-te-modal__batch-section--run{background:radial-gradient(120% 120% at 0% 0%,rgba(90,132,187,.16),rgba(90,132,187,0) 58%),linear-gradient(180deg,#1c2d40,#162331)}
	.qwen-te-modal__batch-section--continuous{background:radial-gradient(120% 120% at 0% 0%,rgba(170,132,68,.16),rgba(170,132,68,0) 58%),linear-gradient(180deg,#372b1f,#241d16);border-color:rgba(171,132,68,.36)}
	.qwen-te-modal__batch-section--export{background:linear-gradient(180deg,rgba(34,43,57,.92),rgba(24,31,43,.96))}
	.qwen-te-modal__batch-head{display:flex;flex-direction:column;gap:4px;min-width:0}
	.qwen-te-modal__batch-title{font-size:12px;line-height:1.2;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:#eef4ff}
	.qwen-te-modal__batch-desc{font-size:11px;line-height:1.45;color:#9fb1c8}
	.qwen-te-modal__toolbar-section-title{font-size:11px;line-height:1.2;letter-spacing:.08em;text-transform:uppercase;color:#9fb8dd;padding:0 2px}
	.qwen-te-modal__toolbar-row{display:grid;gap:8px;align-items:start;min-width:0}
	.qwen-te-modal__toolbar-row .qwen-te-modal__footer-button{width:100%;text-align:center;white-space:nowrap}
	.qwen-te-modal__toolbar-row--preset-meta{grid-template-columns:minmax(0,1fr) auto auto;align-items:center;padding:10px;border:1px solid rgba(98,123,161,.34);border-radius:12px;background:linear-gradient(180deg,rgba(33,46,64,.74),rgba(26,37,52,.92))}
	.qwen-te-modal__status--inline{margin:0;padding:8px 10px;border:1px solid #48576d;border-radius:10px;background:#202936;color:#dce6f7}
	.qwen-te-modal__status--panel{grid-column:1/-1;margin:0;padding:8px 10px;border:1px solid #445469;border-radius:10px;background:#1f2834}
	.qwen-te-modal__input-inline{display:flex;align-items:center;gap:8px;padding:6px 8px;border:1px solid #465468;border-radius:10px;background:#1d2530}
	.qwen-te-modal__input-label{font-size:11px;color:#adc1dc;white-space:nowrap}
	.qwen-te-modal__search--compact{flex:0 0 96px;min-width:96px;max-width:112px;text-align:center;padding:8px 10px}
	.qwen-te-modal__toolbar-row--preset-manage{grid-template-columns:repeat(auto-fit,minmax(132px,1fr))}
	.qwen-te-modal__toolbar-row--preset-run{grid-template-columns:repeat(3,minmax(0,1fr))}
	.qwen-te-modal__toolbar-row--preset-continuous{grid-template-columns:repeat(2,minmax(0,1fr))}
	.qwen-te-modal__toolbar-row--preset-export{grid-template-columns:repeat(4,minmax(0,1fr))}
	.qwen-te-modal__footer-button--span-full{grid-column:1 / -1}
	.qwen-te-modal__toolbar--preset-report{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));align-items:stretch}
	.qwen-te-modal__toolbar--preset-filter{display:grid;grid-template-columns:minmax(0,1fr) minmax(180px,280px);align-items:stretch}
	.qwen-te-modal__toolbar--preset-filter .qwen-te-modal__search{min-width:0}
	.qwen-te-modal__search{flex:1 1 260px;background:#101010;border:1px solid #444;color:#fff;border-radius:10px;padding:10px 12px;font-size:13px}
	.qwen-te-modal__pillbar{display:flex;flex-wrap:wrap;gap:8px;padding-bottom:4px}
	.qwen-te-modal__pillbar::-webkit-scrollbar{display:none}
	.qwen-te-modal__template-groups{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;padding-bottom:4px}
	.qwen-te-modal__template-group{display:flex;flex-direction:column;gap:8px;padding:10px 12px;border:1px solid rgba(73,89,112,.56);border-radius:14px;background:linear-gradient(180deg,rgba(25,32,42,.96),rgba(18,24,32,.98));box-shadow:inset 0 1px 0 rgba(255,255,255,.03),0 12px 24px rgba(0,0,0,.12);min-width:0}
	.qwen-te-modal__template-group-title{font-size:11px;line-height:1.2;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:#dbe8fb}
	.qwen-te-modal__template-group-bar{display:flex;flex-wrap:wrap;gap:8px}
	.qwen-te-modal__preset{border:1px solid #525252;background:#232323;color:#f7f7f7;border-radius:999px;padding:7px 12px;cursor:pointer;font-size:12px;flex:0 0 auto}
	.qwen-te-modal__preset:hover{background:#303030}
	.qwen-te-modal__status{font-size:12px;color:#d7c18a}
	.qwen-te-modal__split{display:grid;grid-template-columns:220px minmax(0,1fr);gap:16px;align-items:start;min-height:0}
	.qwen-te-modal__sidebar{border:1px solid #343434;background:#171b22;border-radius:14px;padding:12px;display:flex;flex-direction:column;gap:10px;max-height:min(62vh,720px);overflow:auto;box-shadow:inset 0 12px 16px -16px rgba(255,255,255,.06),inset 0 -14px 18px -18px rgba(0,0,0,.38)}
	.qwen-te-modal__sidebar-title{position:sticky;top:-12px;z-index:1;font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:#97a5b8;background:linear-gradient(180deg,#171b22 75%,rgba(23,27,34,.92));padding:0 0 8px;margin-bottom:2px;border-bottom:1px solid rgba(77,88,106,.28)}
	.qwen-te-modal__nav{display:flex;flex-direction:column;gap:8px}
	.qwen-te-modal__sidebar-section{display:flex;flex-direction:column;gap:8px;padding-top:8px;border-top:1px solid rgba(77,88,106,.22)}
	.qwen-te-modal__sidebar-section .qwen-te-modal__textarea{min-height:72px}
	.qwen-te-modal__nav-button{border:1px solid #404958;background:#222833;color:#e5ebf5;border-radius:10px;padding:9px 10px;display:flex;align-items:center;justify-content:space-between;gap:10px;cursor:pointer;font-size:12px;text-align:left}
	.qwen-te-modal__nav-button:hover{background:#29313d;border-color:#5f6f88}
	.qwen-te-modal__nav-button.is-active{border-color:#c6a464;background:linear-gradient(180deg,#5a4620,#3e3018);color:#fff0ca;box-shadow:0 10px 18px rgba(0,0,0,.18)}
	.qwen-te-modal__nav-button.is-match{box-shadow:0 0 0 1px rgba(112,160,232,.22),0 8px 18px rgba(0,0,0,.12);border-color:#6d88aa}
	.qwen-te-modal__nav-count{font-size:11px;color:#c9d3e0;border:1px solid #536277;border-radius:999px;padding:2px 8px}
	.qwen-te-modal__nav-button.is-active .qwen-te-modal__nav-count{border-color:#d0ad6c;color:#fff0ca}
	.qwen-te-modal__nav-meta{display:flex;align-items:center;gap:6px}
	.qwen-te-modal__nav-match{font-size:10px;color:#9fc4ff}
	.qwen-te-modal__content{display:flex;flex-direction:column;gap:14px;min-width:0;max-height:min(62vh,720px);overflow:auto;padding-right:4px;position:relative}
	.qwen-te-modal__content::before,.qwen-te-modal__content::after{content:"";position:sticky;left:0;right:4px;height:14px;display:block;pointer-events:none;z-index:3}
	.qwen-te-modal__content::before{top:0;margin-bottom:-14px;background:linear-gradient(180deg,rgba(23,27,34,.94),rgba(23,27,34,0))}
	.qwen-te-modal__content::after{bottom:0;margin-top:-14px;background:linear-gradient(0deg,rgba(23,27,34,.94),rgba(23,27,34,0))}
	.qwen-te-modal__content-header{position:sticky;top:0;z-index:2;border:1px solid #3a4452;border-radius:14px;padding:12px;background:linear-gradient(180deg,#1c232c,#171c22);box-shadow:0 8px 20px rgba(0,0,0,.18)}
	.qwen-te-modal__content-title{display:flex;align-items:center;justify-content:space-between;gap:10px}
	.qwen-te-modal__content-name{font-size:16px;font-weight:700;color:#f3f6fb}
	.qwen-te-modal__content-sub{font-size:12px;line-height:1.45;color:#a4b1c1;margin-top:6px}
	.qwen-te-modal__content-pills{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}
	.qwen-te-modal__content-pill{border:1px solid #536277;border-radius:999px;padding:4px 8px;background:linear-gradient(180deg,#2c3641,#232b35);font-size:11px;line-height:1.2;color:#edf4ff}
	.qwen-te-modal__content-pill--muted{border-color:#6c5935;background:linear-gradient(180deg,#3a2d1c,#2a2116);color:#f3ddb0}
	button.qwen-te-modal__content-pill{font-family:inherit;cursor:pointer}
	button.qwen-te-modal__content-pill:hover{border-color:#d0ad6c;color:#fff0ca}
	.qwen-te-modal__content-tools{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}
	.qwen-te-modal__mini-button{border:1px solid #4a5568;background:#232a33;color:#e5ecf6;border-radius:999px;padding:6px 10px;font-size:11px;line-height:1.2;cursor:pointer}
	.qwen-te-modal__mini-button.is-hidden{display:none}
	.qwen-te-modal__mini-button:hover{background:#2d3642;border-color:#6d7f99}
	.qwen-te-modal__empty{border:1px dashed #414b5a;border-radius:14px;padding:18px;color:#9eabbc;font-size:12px;line-height:1.5}
	.qwen-te-group{border:1px solid #313131;background:#1e1e1e;border-radius:14px;padding:14px;display:flex;flex-direction:column;gap:12px;min-height:280px;max-height:min(56vh,640px);overflow:auto}
	.qwen-te-group--content{min-height:0;max-height:none}
	.qwen-te-group--manager{min-height:0;max-height:none;overflow:hidden}
	.qwen-te-group--manager[open]{overflow:auto}
	.qwen-te-group>summary{list-style:none;cursor:pointer}
	.qwen-te-group>summary::-webkit-details-marker{display:none}
	.qwen-te-group__title{display:flex;align-items:center;justify-content:space-between;gap:10px;font-weight:700;font-size:14px;line-height:1.2}
	.qwen-te-group__count{font-size:11px;color:#bababa;border:1px solid #4c4c4c;border-radius:999px;padding:2px 8px}
	.qwen-te-group__sub{font-size:12px;color:#a8a8a8;margin-top:0;line-height:1.4}
	.qwen-te-group--manager .qwen-te-group__sub{padding-top:2px}
	.qwen-te-group__section-title{font-size:11px;color:#9c9c9c;text-transform:uppercase;letter-spacing:.04em;margin-bottom:6px}
	.qwen-te-group__chips{display:flex;flex-wrap:wrap;gap:8px}
	.qwen-te-group__section{border-top:1px solid #343434;padding-top:10px;display:flex;flex-direction:column;gap:8px}
	.qwen-te-group__section-toggle{display:flex;align-items:center;justify-content:space-between;gap:10px;background:transparent;border:none;color:inherit;padding:0;cursor:pointer;text-align:left}
	.qwen-te-group__section-toggle:hover .qwen-te-group__section-title{color:#d4dbe5}
	.qwen-te-group__section-meta{display:flex;align-items:center;gap:8px}
	.qwen-te-group__section-chevron{font-size:11px;color:#95a4ba;transition:transform .12s ease}
	.qwen-te-group__section.is-collapsed .qwen-te-group__section-chevron{transform:rotate(-90deg)}
	.qwen-te-group__section-tags{display:flex;flex-wrap:wrap;gap:8px}
	.qwen-te-chip{border:1px solid #4b4b4b;background:#262626;color:#efefef;border-radius:999px;padding:6px 10px;cursor:pointer;font-size:12px;line-height:1.15}
	.qwen-te-chip:hover{background:#333}
	.qwen-te-chip.is-selected{border-color:#d7b36a;background:linear-gradient(180deg,#6a5223,#4b3918);color:#fff0ca;box-shadow:0 0 0 1px rgba(255,223,155,.12),0 8px 16px rgba(0,0,0,.14)}
	.qwen-te-chip.is-capacity-blocked{opacity:.42;cursor:not-allowed}
	.qwen-te-hidden{display:none!important}
	.qwen-te-modal__textarea{width:100%;min-height:88px;background:#101010;border:1px solid #444;color:#fff;border-radius:10px;padding:10px 12px;font-size:13px;resize:vertical;box-sizing:border-box}
	.qwen-te-modal__footer{display:flex;justify-content:flex-end;gap:10px;padding:16px 20px 20px;border-top:1px solid #303030}
	.qwen-te-modal__footer-button{border:1px solid #555;border-radius:10px;padding:9px 16px;font-size:13px;cursor:pointer;background:#262626;color:#f2f2f2}
	.qwen-te-modal__footer-button--primary{background:#8a6730;border-color:#b48a43;color:#fff4df}
	.qwen-te-modal__footer-button--danger{background:linear-gradient(180deg,#4d2e36,#3a2228);border-color:#9f606d;color:#ffdce3}
	.qwen-te-modal__footer-button--danger:hover{background:linear-gradient(180deg,#613743,#482932);border-color:#bd7280}
	.qwen-te-modal[data-qwen-modal="online-search"]{padding:10px;background:rgba(0,0,0,.72)}
	.qwen-te-modal[data-qwen-modal="online-search"] .qwen-te-modal__dialog{width:min(1320px,97vw);height:min(860px,94vh);max-height:94vh;border-radius:8px;overflow:hidden;background:#11151a;border-color:#3b424c;display:flex;flex-direction:column}
	.qwen-te-modal[data-qwen-modal="online-search"] .qwen-te-online-search__tabstrip{min-height:44px;padding:7px 8px 0;background:#20242a;border-bottom:1px solid #30363f;align-items:flex-end;gap:8px}
	.qwen-te-online-search__tabs{display:flex;flex:1 1 auto;align-items:flex-end;gap:5px;min-width:0}
	.qwen-te-online-search__tab{appearance:none;display:flex;flex-direction:column;justify-content:center;min-width:180px;max-width:300px;height:37px;padding:5px 12px;border:1px solid #383f48;border-bottom:none;border-radius:7px 7px 0 0;background:#181d23;color:#aeb7c2;position:relative;min-height:0;text-align:left;cursor:pointer}
	.qwen-te-online-search__tab:hover{background:#20262d;color:#eef3f8}
	.qwen-te-online-search__tab.is-active{background:#11151a;border-color:#46515d;color:#f3f6fa;box-shadow:inset 0 2px 0 #b28843}
	.qwen-te-online-search__tab:focus-visible{outline:2px solid #83a9d3;outline-offset:-2px}
	.qwen-te-online-search__tab .qwen-te-modal__title{font-size:13px;line-height:1.15;letter-spacing:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
	.qwen-te-online-search__tab .qwen-te-modal__subtitle{font-size:9px;line-height:1.15;letter-spacing:0;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
	.qwen-te-online-search__window-button{width:34px;height:34px;flex:0 0 34px;margin:0 0 3px auto;border:1px solid transparent;border-radius:6px;background:transparent;color:#d8dde5;font-size:22px;line-height:1;cursor:pointer}
	.qwen-te-online-search__window-button:hover{background:#493038;border-color:#73515b;color:#ffe4e8}
	.qwen-te-modal[data-qwen-modal="online-search"] .qwen-te-online-search__body{flex:1 1 auto;min-height:0;padding:0;overflow:hidden}
	.qwen-te-online-search__stack{display:flex;flex-direction:column;min-height:0;height:100%;padding:0;background:#11151a}
	.qwen-te-online-search__topbar{display:flex;flex-direction:column;gap:7px;flex:0 0 auto;padding:9px 12px 8px;background:#171b20;border-bottom:1px solid #30363f}
	.qwen-te-online-search__browser-toolbar{display:grid;grid-template-columns:auto minmax(0,1fr) auto auto auto;align-items:center;gap:8px;padding:0}
	.qwen-te-online-search__nav{display:flex;align-items:center;gap:3px}
	.qwen-te-online-search__nav-button{width:34px;height:34px;display:inline-flex;align-items:center;justify-content:center;border:1px solid transparent;border-radius:50%;background:transparent;color:#d3d8df;font-size:18px;line-height:1;cursor:pointer}
	.qwen-te-online-search__nav-button:hover:not(:disabled){background:#2a3037;border-color:#3d4651}
	.qwen-te-online-search__nav-button:disabled{opacity:.34;cursor:not-allowed}
	.qwen-te-online-search__addressbar{min-width:0;height:38px;display:flex;align-items:center;gap:8px;border:1px solid #414954;border-radius:20px;padding:0 11px;background:#0b0f13;box-shadow:inset 0 1px 0 rgba(255,255,255,.03)}
	.qwen-te-online-search__addressbar:focus-within{border-color:#7e9bc0;box-shadow:0 0 0 2px rgba(101,143,197,.16)}
	.qwen-te-online-search__address-badge{flex:0 0 auto;max-width:92px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#9db4d2;font-size:10px;line-height:1}
	.qwen-te-modal[data-qwen-modal="online-search"] .qwen-te-online-search__address-input{min-width:0;flex:1 1 auto;padding:0;border:0;border-radius:0;background:transparent;color:#f2f5f9;font-size:13px;outline:none;box-shadow:none}
	.qwen-te-online-search__go-button{height:36px;min-width:74px;border:1px solid #a87d36;border-radius:7px;padding:0 14px;background:#76551f;color:#fff1ce;font-size:12px;font-weight:700;cursor:pointer}
	.qwen-te-online-search__go-button:hover:not(:disabled){background:#8b6627;border-color:#c3984d}
	.qwen-te-online-search__go-button:disabled{opacity:.48;cursor:not-allowed}
	.qwen-te-online-search__external-button{border-radius:6px;border-color:#3b4652;background:#20262d;font-size:16px}
	.qwen-te-online-search__companion-button{border-radius:6px;border-color:#7f6330;background:#4d3918;color:#ffe8b4;font-size:15px}
	.qwen-te-online-search__companion-button:hover:not(:disabled){background:#674b1c;border-color:#b58a42}
	.qwen-te-online-search__companion-button.is-busy{opacity:.62;cursor:wait}
	.qwen-te-online-search__bookmarks{display:flex;flex-wrap:nowrap;gap:5px;min-width:0;overflow-x:auto;padding:0 0 1px 111px;scrollbar-width:none}
	.qwen-te-online-search__bookmarks::-webkit-scrollbar{display:none}
	.qwen-te-modal[data-qwen-modal="online-search"] .qwen-te-online-search__bookmarks .qwen-te-modal__preset{flex:0 0 auto;border:0;border-radius:5px;padding:4px 8px;background:transparent;color:#b9c1cb;font-size:10.5px}
	.qwen-te-modal[data-qwen-modal="online-search"] .qwen-te-online-search__bookmarks .qwen-te-modal__preset:hover{background:#292f36;color:#f1f4f8}
	.qwen-te-online-search__status{min-height:16px;max-height:34px;padding-left:111px;color:#c9b47d;line-height:1.45;overflow:hidden;display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2}
	.qwen-te-online-search__grid{display:grid;grid-template-columns:210px minmax(400px,1fr) 320px;grid-template-rows:minmax(0,1fr);gap:0;align-items:stretch;flex:1 1 auto;min-height:0;overflow:hidden}
	.qwen-te-online-search__filter-rail{display:flex;flex-direction:column;gap:7px;min-width:0;min-height:0;padding:12px 10px;background:#14191f;border-right:1px solid #30363f;overflow:auto}
	.qwen-te-online-search__summary{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:5px;margin:0 0 6px}
	.qwen-te-modal[data-qwen-modal="online-search"] .qwen-te-online-search__summary .qwen-te-modal__content-pill{min-width:0;border:1px solid #343e49;border-radius:5px;padding:5px 6px;background:#1b222a;color:#cbd4df;font-size:10px;text-align:center;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
	.qwen-te-online-search__filter-label,.qwen-te-online-search__section-label{margin-top:5px;font-size:10px;font-weight:700;line-height:1.2;letter-spacing:0;color:#8795a7}
	.qwen-te-online-search__filter-list{display:flex;flex-direction:column;gap:4px;padding:0}
	.qwen-te-modal[data-qwen-modal="online-search"] .qwen-te-online-search__filter-list .qwen-te-modal__preset{width:100%;display:flex;align-items:center;justify-content:flex-start;border:1px solid transparent;border-radius:5px;padding:7px 8px;background:transparent;color:#c3ccd7;font-size:11px;text-align:left}
	.qwen-te-modal[data-qwen-modal="online-search"] .qwen-te-online-search__filter-list .qwen-te-modal__preset:hover:not(:disabled){background:#1e252d;border-color:#34404c}
	.qwen-te-modal[data-qwen-modal="online-search"] .qwen-te-online-search__filter-list .qwen-te-modal__preset.is-active{background:#2b2416;border-color:#9a783b;color:#ffe8b4}
	.qwen-te-online-search__panel{display:flex;flex-direction:column;gap:0;min-width:0;min-height:0;padding:0;border:0;border-radius:0;background:#11151a;overflow:hidden}
	.qwen-te-online-search__panel--results{border-right:1px solid #30363f}
	.qwen-te-online-search__panel--samples{padding:12px;background:#151a20;overflow:hidden}
	.qwen-te-online-search__panel-head{display:flex;align-items:flex-start;justify-content:space-between;gap:10px;flex:0 0 auto;padding:13px 15px 10px;border-bottom:1px solid #2c333b}
	.qwen-te-online-search__panel--samples .qwen-te-online-search__panel-head{padding:0 0 10px}
	.qwen-te-online-search__panel-title{font-size:13px;line-height:1.25;font-weight:700;letter-spacing:0;color:#edf2f8}
	.qwen-te-online-search__panel-sub{font-size:10.5px;line-height:1.4;color:#8f9dad;white-space:pre-wrap;margin-top:3px}
	.qwen-te-online-search__panel-head .qwen-te-modal__content-tools{display:flex;flex-wrap:wrap;justify-content:flex-end;gap:5px;margin:0}
	.qwen-te-online-search__panel-head .qwen-te-modal__mini-button{border-radius:5px;padding:5px 8px;background:#1b222a;font-size:10px}
	.qwen-te-online-search__cards{display:flex;flex-direction:column;gap:0;flex:1 1 auto;min-height:0;overflow:auto;align-content:stretch}
	.qwen-te-online-search__card{position:relative;width:100%;min-height:104px;display:flex;flex-direction:column;gap:5px;padding:12px 16px 12px 18px;border:0;border-bottom:1px solid #2b323a;border-radius:0;background:transparent;color:#dbe2eb;text-align:left;cursor:pointer;transition:background .12s ease,border-color .12s ease}
	.qwen-te-online-search__card:hover:not(:disabled){background:#171d23}
	.qwen-te-online-search__card:focus-visible{outline:2px solid #80a8d8;outline-offset:-3px}
	.qwen-te-online-search__card.is-selected{background:#211d14;box-shadow:inset 3px 0 0 #c59a4b}
	.qwen-te-online-search__card.is-existing{opacity:.78}
	.qwen-te-online-search__card.is-high:not(.is-selected){box-shadow:inset 3px 0 0 #557ba8}
	.qwen-te-online-search__card:disabled{cursor:not-allowed;opacity:.48}
	.qwen-te-online-search__result-route{font-size:10px;line-height:1.2;color:#78a889;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
	.qwen-te-online-search__card-head{display:flex;align-items:flex-start;justify-content:space-between;gap:10px}
	.qwen-te-online-search__card-name{min-width:0;font-size:13px;font-weight:600;line-height:1.45;letter-spacing:0;color:#8ab4f8;word-break:break-word;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
	.qwen-te-online-search__result-badges{flex:0 0 auto;margin:0}
	.qwen-te-online-search__result-badges .qwen-te-modal__content-pill{border-radius:4px;padding:3px 6px;font-size:9.5px}
	.qwen-te-online-search__card-summary{font-size:11px;line-height:1.45;color:#aab5c2;white-space:normal}
	.qwen-te-online-search__card-foot{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-top:auto}
	.qwen-te-online-search__card-empty{margin:18px;border:1px dashed #3e4853;border-radius:6px;padding:24px;color:#91a0b1;font-size:12px;line-height:1.5;background:#14191f}
	.qwen-te-online-search__selection-status{flex:0 0 auto;border:1px solid #38434f;border-radius:6px;padding:7px 8px;background:#11161c;color:#dbe4ef;font-size:11px}
	.qwen-te-online-search__selected-preview{display:flex;flex-wrap:wrap;gap:5px;flex:0 0 auto;max-height:108px;overflow:auto;padding:7px 0}
	.qwen-te-online-search__selected-chip{max-width:100%;border:1px solid #52677f;border-radius:5px;padding:4px 7px;background:#202b37;color:#d8e8fb;font-size:10px;line-height:1.25;white-space:normal;word-break:break-word;cursor:pointer}
	.qwen-te-online-search__selected-chip:hover:not(:disabled){border-color:#b08743;background:#342a19;color:#ffe9b8}
	.qwen-te-online-search__selected-empty,.qwen-te-online-search__selected-more{font-size:10px;line-height:1.4;color:#8897a8}
	.qwen-te-online-search__actions{display:grid;grid-template-columns:minmax(0,1fr);gap:6px;padding:0 0 8px;border-bottom:1px solid #303740}
	.qwen-te-modal[data-qwen-modal="online-search"] .qwen-te-online-search__actions .qwen-te-modal__footer-button{min-height:34px;border-radius:5px;padding:6px 8px;background:#222a33;font-size:11px;white-space:normal}
	.qwen-te-modal[data-qwen-modal="online-search"] .qwen-te-online-search__actions .qwen-te-modal__footer-button:first-child{border-color:#9d7938;background:#5f461d;color:#ffedc4}
	.qwen-te-online-search__sample-box{flex:1 1 auto;min-height:0;height:100%;resize:none;overflow:auto}
	.qwen-te-online-search__sample-list{display:flex;flex-direction:column;gap:0;flex:1 1 auto;min-height:0;overflow:auto;padding:0}
	.qwen-te-online-search__sample-item{border:0;border-bottom:1px solid #2d343d;border-radius:0;padding:9px 2px;background:transparent;font-size:10.5px;line-height:1.5;color:#cbd5e1;white-space:pre-wrap;word-break:break-word}
	.qwen-te-online-search__sample-item-index{display:inline-flex;align-items:center;justify-content:center;min-width:19px;height:19px;margin-right:6px;border-radius:4px;border:1px solid #52677e;background:#202936;font-size:9px;line-height:1;color:#dbe9fa;vertical-align:top}
	.qwen-te-online-search__hint{flex:0 0 auto;padding-top:7px;font-size:9.5px;line-height:1.4;color:#79899a}
	.qwen-te-modal[data-qwen-modal="online-search"] .qwen-te-modal__status{font-size:10.5px;line-height:1.4}
	.qwen-te-online-search__web-workspace{display:flex;flex:1 1 auto;min-width:0;min-height:0;position:relative;background:#0f1318;overflow:hidden}
	.qwen-te-online-search__web-home{display:flex;flex:1 1 auto;min-width:0;min-height:0;flex-direction:column;align-items:center;padding:clamp(24px,8vh,70px) 18px 24px;overflow:auto;background:#11151a}
	.qwen-te-online-search__web-home-title{width:min(720px,100%);margin-bottom:13px;color:#dce3eb;font-size:13px;font-weight:700}
	.qwen-te-online-search__web-home-grid{width:min(720px,100%);display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px}
	.qwen-te-online-search__site-button{appearance:none;display:flex;min-width:0;min-height:72px;flex-direction:column;align-items:center;justify-content:center;gap:7px;border:1px solid #323b45;border-radius:6px;padding:9px 7px;background:#171d23;color:#cdd5df;cursor:pointer}
	.qwen-te-online-search__site-button:hover{border-color:#647891;background:#202730;color:#f2f5f9}
	.qwen-te-online-search__site-button:focus-visible{outline:2px solid #83a9d3;outline-offset:2px}
	.qwen-te-online-search__site-icon{display:inline-flex;width:28px;height:28px;align-items:center;justify-content:center;border:1px solid #526478;border-radius:50%;background:#24303d;color:#dceafa;font-size:12px;font-weight:700}
	.qwen-te-online-search__site-label{max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:10.5px}
	.qwen-te-online-search__web-frame-shell{position:relative;display:flex;align-items:center;justify-content:center;flex:1 1 auto;min-width:0;min-height:0;background:#fff;overflow:hidden;isolation:isolate;contain:paint}
	.qwen-te-online-search__web-frame{position:relative;z-index:1;width:100%;height:100%;flex:1 1 auto;min-width:0;min-height:0;border:0;background:#fff;object-fit:contain;image-rendering:auto;pointer-events:auto;touch-action:none;user-select:none;-webkit-user-drag:none;outline:none;cursor:default}
	.qwen-te-online-search__web-frame:focus-visible{box-shadow:inset 0 0 0 2px #78a6df}
	.qwen-te-online-search__frame-overlay{position:absolute;inset:0;z-index:2;display:flex;align-items:center;justify-content:center;padding:24px;background:rgba(15,19,24,.82);color:#dbe5f1;font-size:12px;line-height:1.5;text-align:center;pointer-events:none}
	.qwen-te-online-search__frame-overlay.is-passive{background:rgba(15,19,24,.38);align-items:flex-end;justify-content:flex-start;text-align:left}
	.qwen-te-online-search__input-sink{position:fixed!important;left:-10000px!important;top:-10000px!important;width:1px!important;height:1px!important;min-width:1px!important;min-height:1px!important;opacity:0!important;pointer-events:none!important;resize:none!important}
	.qwen-te-online-search__frame-external{position:absolute;top:9px;right:10px;z-index:3;min-height:31px;border:1px solid #6f7f91;border-radius:6px;padding:5px 10px;background:rgba(19,25,32,.92);color:#eef4fb;font-size:10.5px;font-weight:700;box-shadow:0 3px 12px rgba(0,0,0,.28);cursor:pointer}
	.qwen-te-online-search__frame-external:hover:not(:disabled){background:#283543;border-color:#95abc2}
	.qwen-te-online-search__frame-external:disabled{opacity:.45;cursor:not-allowed}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__dialog{width:min(980px,95vw);max-height:90vh}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__header{padding:12px 16px 10px}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__body{padding:10px 16px 14px;gap:10px}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__footer{padding:10px 16px 12px;background:#151a20}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__title{font-size:16px}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__subtitle{font-size:11px;line-height:1.35;margin-top:3px}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__search{padding:8px 10px;font-size:12px;border-radius:9px}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__footer-button{padding:7px 12px;font-size:12px;border-radius:9px;min-height:38px}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__status{font-size:11px}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__preset-save-panel{display:flex;flex-direction:column;gap:8px;padding:12px 14px;border:1px solid rgba(87,105,131,.52);border-radius:14px;background:linear-gradient(180deg,rgba(28,36,48,.96),rgba(18,24,34,.98));box-shadow:inset 0 1px 0 rgba(255,255,255,.04),0 14px 28px rgba(0,0,0,.18)}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__preset-save-head{display:flex;align-items:flex-start;justify-content:space-between;gap:10px}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__preset-save-title{font-size:12px;font-weight:700;letter-spacing:.04em;color:#eef4ff}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__preset-save-desc{font-size:10.5px;line-height:1.45;color:#9fb1c8;margin-top:3px}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__toolbar--preset-batch{gap:10px}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__batch-dashboard{grid-template-columns:minmax(0,1.72fr) minmax(260px,.88fr);gap:10px}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__batch-dashboard-main,
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__batch-dashboard-side{gap:10px}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__batch-section{gap:8px;padding:10px 12px;border-radius:12px}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__batch-head{flex-direction:row;align-items:baseline;justify-content:space-between;gap:6px 10px}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__batch-title{font-size:11px}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__batch-desc{font-size:10px;line-height:1.35;flex:1 1 240px}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__batch-kicker{font-size:10px;letter-spacing:.08em;text-transform:uppercase;color:#8fb0d7}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__toolbar-row{gap:6px}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__toolbar-row--preset-meta{padding:8px;grid-template-columns:minmax(0,1fr) auto auto}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__status--inline,
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__status--panel{padding:6px 8px}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__status--inline{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__input-inline{padding:4px 6px;gap:6px;border-radius:9px}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__input-label{font-size:10px}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__search--compact{flex:0 0 72px;min-width:72px;max-width:84px;padding:6px 8px}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__toolbar-row--preset-manage{grid-template-columns:repeat(2,minmax(0,1fr))}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__toolbar-row--preset-run{grid-template-columns:repeat(4,minmax(0,1fr))}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__toolbar-row--preset-continuous{grid-template-columns:repeat(2,minmax(0,1fr))}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__toolbar-row--preset-export{grid-template-columns:repeat(4,minmax(0,1fr))}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__toolbar--preset-report{grid-template-columns:repeat(3,minmax(0,1fr));gap:6px}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-group__section-title{font-size:10px;margin-bottom:4px}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__workspace{display:grid;grid-template-columns:minmax(0,1fr);gap:12px;align-items:start;min-height:0}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__workspace-main,
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__workspace-side{display:flex;flex-direction:column;gap:10px;min-width:0;min-height:0}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__workspace-side{display:none}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__surface{display:flex;flex-direction:column;gap:10px;padding:12px 14px;border:1px solid rgba(74,89,110,.56);border-radius:14px;background:linear-gradient(180deg,rgba(24,30,39,.98),rgba(19,24,32,.98));box-shadow:inset 0 1px 0 rgba(255,255,255,.03),0 16px 32px rgba(0,0,0,.16);min-width:0}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__surface--filter{background:linear-gradient(180deg,rgba(22,28,38,.98),rgba(18,23,31,.98))}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__surface--list{padding:12px;min-height:260px}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__surface-head{display:flex;align-items:flex-start;justify-content:space-between;gap:10px}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__surface-title{font-size:12px;font-weight:700;color:#f1f6ff;letter-spacing:.03em}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__surface-desc{font-size:10.5px;line-height:1.45;color:#9fb1c8;margin-top:3px}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__surface-meta{display:flex;flex-wrap:wrap;gap:6px;justify-content:flex-end}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__surface-pill{border:1px solid rgba(92,113,139,.54);border-radius:999px;padding:4px 9px;background:linear-gradient(180deg,#253243,#1d2734);font-size:10px;line-height:1.2;color:#dbe8fb;white-space:nowrap}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__surface-pill--accent{border-color:#b48a43;background:linear-gradient(180deg,#5d451c,#433113);color:#fff0cb}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__filter-toolbar{display:grid;grid-template-columns:minmax(0,1fr) minmax(190px,260px);gap:10px;align-items:stretch}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__filter-guide{font-size:10.5px;line-height:1.45;color:#c7d3e5}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__list-scroll{display:flex;flex-direction:column;gap:8px;min-height:0;max-height:min(58vh,680px);overflow:auto;padding-right:2px}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__report-actions{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__report-stream{display:flex;flex-direction:column;gap:8px;min-height:0;max-height:min(58vh,700px);overflow:auto;padding-right:2px}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__empty-state{display:flex;align-items:center;justify-content:center;min-height:160px;border:1px dashed rgba(79,97,123,.5);border-radius:14px;background:rgba(18,24,33,.62);padding:18px;color:#b8c7dd;text-align:center;line-height:1.55}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-preset-list{gap:8px}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-preset-card{padding:10px;gap:6px}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-preset-card__summary{font-size:11px;line-height:1.4}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-preset-card__action-row{gap:6px}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-preset-card__action-row--primary{grid-template-columns:repeat(auto-fit,minmax(96px,1fr))}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-preset-card__action-row--danger{grid-template-columns:repeat(2,minmax(0,1fr))}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-preset-card__editor{display:flex;flex-direction:column;gap:9px;padding:10px;border:1px solid rgba(180,138,67,.58);border-radius:10px;background:linear-gradient(180deg,rgba(42,34,22,.9),rgba(24,27,33,.98))}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-preset-card__editor-grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:9px}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-preset-card__editor-field{display:flex;flex-direction:column;gap:5px;min-width:0}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-preset-card__editor-field--wide{grid-column:1/-1}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-preset-card__editor-label{font-size:10.5px;font-weight:700;color:#e8d4ab}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-preset-card__editor-help{font-size:10px;line-height:1.4;color:#9fb1c8}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-preset-card__editor-textarea{min-height:168px;font-family:Consolas,"Cascadia Code","SFMono-Regular",monospace;font-size:11px;line-height:1.45}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-preset-card__editor-actions{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-preset-card__header{align-items:flex-start}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-preset-card__select{min-width:84px}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-preset-card__name{font-size:13px}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-preset-card__time{white-space:nowrap}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-preset-card__summary{color:#d3dceb}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__footer-button{border-color:#56657b;background:linear-gradient(180deg,#2d3a4b,#253141);color:#f1f6ff;transition:background .14s ease,border-color .14s ease,box-shadow .14s ease,transform .08s ease}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__toolbar-row .qwen-te-modal__footer-button{min-height:36px;height:auto;padding:7px 10px;font-size:12px;font-weight:600;letter-spacing:.01em}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__footer-button:hover{background:linear-gradient(180deg,#37475a,#2c3a4b);border-color:#6f89ad;box-shadow:0 8px 16px rgba(0,0,0,.16)}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__footer-button:active{transform:translateY(1px)}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__footer-button:disabled{opacity:.62;cursor:not-allowed;box-shadow:none}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__footer-button--primary{background:#8a6730;border-color:#b48a43;color:#fff4df}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__footer-button--accent{background:linear-gradient(180deg,#5c4520,#423116);border-color:#bd9243;color:#fff0cb}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__footer-button--danger{background:linear-gradient(180deg,#4d2e36,#3a2228);border-color:#9f606d;color:#ffdce3}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__batch-section .qwen-te-modal__toolbar-row--preset-meta,
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__batch-section .qwen-te-modal__toolbar-row--preset-manage,
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__batch-section .qwen-te-modal__toolbar-row--preset-run,
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__batch-section .qwen-te-modal__toolbar-row--preset-continuous,
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__batch-section .qwen-te-modal__toolbar-row--preset-export{padding:0;border:0;background:transparent}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-group__section-title{margin-bottom:4px}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__toolbar--preset-report{padding:8px 10px;border:1px solid rgba(84,102,128,.34);border-radius:12px;background:linear-gradient(180deg,rgba(31,40,54,.78),rgba(24,31,43,.92))}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__status{line-height:1.45}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-preset-list{gap:8px}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__preset-report-panel{min-height:0;max-height:none;padding:8px 10px;gap:8px;border-radius:12px;background:linear-gradient(180deg,rgba(30,38,50,.94),rgba(22,28,38,.98))}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__preset-report-summary{list-style:none;display:flex;align-items:center;justify-content:space-between;gap:10px;cursor:pointer}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__preset-report-summary::-webkit-details-marker{display:none}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__preset-report-main{display:flex;flex-direction:column;gap:3px;min-width:0}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__preset-report-title{font-size:11px;font-weight:700;letter-spacing:.04em;color:#eef4ff}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__preset-report-meta{font-size:10px;line-height:1.3;color:#9fb1c8;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__preset-report-list{max-height:176px;overflow:auto;padding-right:2px}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__preset-report-list .qwen-te-preset-card{padding:8px}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__preset-report-list .qwen-te-preset-card__name{font-size:12px}
	.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__preset-report-list .qwen-te-preset-card__summary{font-size:10.5px;line-height:1.35}
	@media (max-width:1120px){
		.qwen-te-online-search__grid{grid-template-columns:190px minmax(0,1fr);grid-template-rows:minmax(300px,1fr) minmax(190px,220px)}
		.qwen-te-online-search__filter-rail{grid-column:1;grid-row:1/3}
		.qwen-te-online-search__panel--results{grid-column:2;grid-row:1;border-right:0}
		.qwen-te-online-search__panel--samples{grid-column:2;grid-row:2;border-top:1px solid #30363f;overflow:auto}
		.qwen-te-online-search__panel--samples .qwen-te-online-search__sample-list{flex:0 0 auto;min-height:82px;overflow:visible}
	}
	@media (max-width:920px){
		.qwen-te-modal[data-qwen-modal="online-search"] .qwen-te-modal__dialog{width:min(900px,98vw);height:min(900px,96vh);max-height:96vh}
		.qwen-te-online-search__bookmarks,.qwen-te-online-search__status{padding-left:0}
		.qwen-te-online-search__grid{grid-template-columns:minmax(0,1fr);grid-template-rows:140px minmax(260px,1fr) 210px}
		.qwen-te-online-search__filter-rail{grid-column:1;grid-row:1;padding:8px 10px;border-right:0;border-bottom:1px solid #30363f}
		.qwen-te-online-search__summary{grid-template-columns:repeat(4,minmax(0,1fr));margin-bottom:2px}
		.qwen-te-online-search__filter-list{flex-direction:row;flex-wrap:wrap}
		.qwen-te-modal[data-qwen-modal="online-search"] .qwen-te-online-search__filter-list .qwen-te-modal__preset{width:auto;padding:5px 8px}
		.qwen-te-online-search__panel--results{grid-column:1;grid-row:2;border-right:0}
		.qwen-te-online-search__panel--samples{grid-column:1;grid-row:3;min-height:0;border-top:1px solid #30363f}
		.qwen-te-modal__batch-dashboard{grid-template-columns:1fr}
		.qwen-te-modal__batch-dashboard-main,.qwen-te-modal__batch-dashboard-side{gap:10px}
		.qwen-te-modal__toolbar-row--preset-meta{grid-template-columns:minmax(0,1fr) auto}
		.qwen-te-modal__status--inline{grid-column:1/-1}
		.qwen-te-modal__toolbar-row--preset-run{grid-template-columns:repeat(2,minmax(0,1fr))}
		.qwen-te-modal__toolbar-row--preset-continuous{grid-template-columns:repeat(2,minmax(0,1fr))}
		.qwen-te-modal__toolbar-row--preset-export{grid-template-columns:repeat(3,minmax(0,1fr))}
	}
	@media (max-width:640px){
		.qwen-te-modal[data-qwen-modal="online-search"]{padding:4px}
		.qwen-te-modal[data-qwen-modal="online-search"] .qwen-te-modal__dialog{width:100vw;height:98vh;max-height:98vh}
		.qwen-te-modal[data-qwen-modal="online-search"] .qwen-te-online-search__tabstrip{min-height:40px;padding:5px 6px 0}
		.qwen-te-online-search__tab{min-width:0;max-width:none;flex:1 1 auto;height:35px;padding-left:9px}
		.qwen-te-online-search__topbar{gap:5px;padding:7px 8px}
		.qwen-te-online-search__browser-toolbar{grid-template-columns:minmax(0,1fr) auto auto auto;gap:6px}
		.qwen-te-online-search__nav{grid-column:1/-1}
		.qwen-te-online-search__addressbar{height:36px;padding:0 9px}
		.qwen-te-online-search__address-badge{max-width:58px}
		.qwen-te-online-search__go-button{height:34px;min-width:66px;padding:0 10px}
		.qwen-te-online-search__external-button{width:34px;height:34px}
		.qwen-te-online-search__companion-button{width:34px;height:34px}
		.qwen-te-online-search__web-home{padding:24px 12px}
		.qwen-te-online-search__web-home-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:7px}
		.qwen-te-online-search__site-button{min-height:64px}
		.qwen-te-online-search__grid{grid-template-rows:126px minmax(220px,1fr) 190px}
		.qwen-te-online-search__summary{grid-template-columns:repeat(2,minmax(0,1fr))}
		.qwen-te-online-search__panel-head{flex-direction:column;padding:10px 11px 8px}
		.qwen-te-online-search__panel-head .qwen-te-modal__content-tools{justify-content:flex-start}
		.qwen-te-online-search__card{min-height:0;padding:10px 12px 10px 14px}
		.qwen-te-online-search__card-name{font-size:14px}
		.qwen-te-online-search__panel--samples{padding:9px}
		.qwen-te-online-search__panel--samples .qwen-te-online-search__panel-head{padding-bottom:6px}
		.qwen-te-online-search__selected-preview{max-height:54px;padding:5px 0}
		.qwen-te-online-search__actions{grid-template-columns:repeat(3,minmax(0,1fr));gap:4px;padding-bottom:6px}
		.qwen-te-modal[data-qwen-modal="online-search"] .qwen-te-online-search__actions .qwen-te-modal__footer-button{min-width:0;min-height:32px;padding:5px 4px;font-size:10px}
		.qwen-te-modal__toolbar-row--preset-run{grid-template-columns:minmax(0,1fr)}
		.qwen-te-modal__toolbar-row--preset-continuous{grid-template-columns:minmax(0,1fr)}
		.qwen-te-modal__toolbar-row--preset-export{grid-template-columns:minmax(0,1fr)}
		.qwen-te-modal__toolbar--preset-save{grid-template-columns:minmax(0,1fr)}
		.qwen-te-modal__toolbar-row--preset-meta{grid-template-columns:minmax(0,1fr)}
		.qwen-te-modal__input-inline{justify-content:space-between}
		.qwen-te-modal__toolbar--preset-filter{grid-template-columns:minmax(0,1fr)}
	}
	@media (max-width:640px) and (max-height:720px){
		.qwen-te-modal[data-qwen-modal="online-search"] .qwen-te-online-search__body{overflow:auto}
		.qwen-te-online-search__stack{height:auto;min-height:670px}
		.qwen-te-online-search__topbar{position:sticky;top:0;z-index:3}
		.qwen-te-online-search__grid{flex:1 0 536px;min-height:536px}
		.qwen-te-online-search__web-workspace{flex:1 0 536px;min-height:536px}
	}
	.qwen-te-preset-list{display:flex;flex-direction:column;gap:10px}
		.qwen-te-preset-card{border:1px solid #343434;background:#1d1d1d;border-radius:12px;padding:12px;display:flex;flex-direction:column;gap:8px}
		.qwen-te-preset-card--success{border-color:#3f6a49;background:linear-gradient(180deg,#1c2a1f,#19221b)}
		.qwen-te-preset-card--warn{border-color:#7a6834;background:linear-gradient(180deg,#2b2417,#211c14)}
		.qwen-te-preset-card--danger{border-color:#7a4348;background:linear-gradient(180deg,#2a1d20,#211719)}
		.qwen-te-preset-card--info{border-color:#485c78;background:linear-gradient(180deg,#1b222b,#171d25)}
		.qwen-te-preset-card--clickable{cursor:pointer}
		.qwen-te-preset-card--expanded{box-shadow:0 0 0 1px rgba(255,255,255,.05),0 10px 18px rgba(0,0,0,.18)}
		.qwen-te-preset-card__header{display:flex;align-items:center;justify-content:space-between;gap:10px}
		.qwen-te-preset-card__head-main{display:flex;align-items:center;gap:8px;flex-wrap:wrap;min-width:0;flex:1 1 auto}
		.qwen-te-preset-card__select{min-width:78px;padding:7px 10px;font-size:12px}
		.qwen-te-preset-card__source{margin-top:0}
		.qwen-te-preset-card__name{font-size:14px;font-weight:700}
		.qwen-te-preset-card__time{font-size:11px;color:#a9a9a9}
		.qwen-te-preset-card__summary{font-size:12px;line-height:1.45;color:#ddd;white-space:pre-wrap}
		.qwen-te-preset-card__badges{display:flex;flex-wrap:wrap;gap:6px}
		.qwen-te-preset-card__actions{display:flex;flex-direction:column;gap:7px}
		.qwen-te-preset-card__action-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:8px}
		.qwen-te-preset-card__action-row .qwen-te-modal__footer-button{width:100%;text-align:center;white-space:nowrap}
		.qwen-te-preset-card__action-row--primary{grid-template-columns:repeat(auto-fit,minmax(132px,1fr))}
		.qwen-te-preset-card__action-row--danger{grid-template-columns:repeat(2,minmax(0,1fr))}
		.qwen-te-preset-card__badge{border:1px solid #536277;border-radius:999px;padding:3px 8px;background:linear-gradient(180deg,#2c3641,#232b35);font-size:11px;line-height:1.2;color:#edf4ff}
		.qwen-te-preset-card__badge--success{border-color:#4f8a5c;background:linear-gradient(180deg,#27402c,#1f3223);color:#dff6e3}
		.qwen-te-preset-card__badge--warn{border-color:#ab8b42;background:linear-gradient(180deg,#4a3a1e,#352915);color:#fde4a8}
		.qwen-te-preset-card__badge--danger{border-color:#b06470;background:linear-gradient(180deg,#4d2830,#351b21);color:#ffd9df}
		.qwen-te-preset-card__badge--info{border-color:#6886ad;background:linear-gradient(180deg,#2a3748,#1f2936);color:#d9ebff}
		.qwen-te-preset-card__detail{border-top:1px solid rgba(255,255,255,.08);padding-top:8px;display:flex;flex-direction:column;gap:6px}
		.qwen-te-preset-card__detail-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(168px,1fr));gap:8px}
		.qwen-te-preset-card__kv{border:1px solid rgba(96,116,146,.35);border-radius:10px;background:linear-gradient(180deg,#222b36,#1a212b);padding:8px 10px;display:flex;flex-direction:column;gap:4px}
		.qwen-te-preset-card__kv-label{font-size:10px;letter-spacing:.06em;text-transform:uppercase;color:#9fb5d4}
		.qwen-te-preset-card__kv-value{font-size:12px;line-height:1.35;color:#f1f6ff;word-break:break-word}
		.qwen-te-preset-card__detail-item{font-size:12px;line-height:1.45;color:#d7dde7;white-space:pre-wrap}
		.qwen-te-preset-card__detail-item--success{border-left:3px solid #4f8a5c;background:rgba(39,64,44,.22);padding:8px 10px;border-radius:10px}
		.qwen-te-preset-card__detail-item--warn{border-left:3px solid #ab8b42;background:rgba(74,58,30,.24);padding:8px 10px;border-radius:10px}
		.qwen-te-preset-card__detail-item--danger{border-left:3px solid #b06470;background:rgba(77,40,48,.24);padding:8px 10px;border-radius:10px}
		.qwen-te-preset-card__detail-item--info{border-left:3px solid #6886ad;background:rgba(42,55,72,.24);padding:8px 10px;border-radius:10px}
		.qwen-te-preset-card__detail-item strong{color:#fff4df}
	@media (max-width: 1180px){
		.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__batch-dashboard{grid-template-columns:minmax(0,1fr)}
		.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-preset-card__editor-grid{grid-template-columns:minmax(0,1fr)}
		.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-preset-card__editor-field--wide{grid-column:auto}
		.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__toolbar-row--preset-run{grid-template-columns:repeat(3,minmax(0,1fr))}
		.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__toolbar-row--preset-export{grid-template-columns:repeat(3,minmax(0,1fr))}
	}
	@media (max-width: 860px){
		.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__toolbar-row--preset-meta{grid-template-columns:1fr}
		.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__toolbar-row--preset-run,
		.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__toolbar-row--preset-export,
		.qwen-te-modal[data-qwen-modal="preset-manager"] .qwen-te-modal__toolbar--preset-report{grid-template-columns:repeat(2,minmax(0,1fr))}
	}
	@media (max-width: 560px){
		.qwen-te-panel__workspace{grid-template-columns:minmax(0,1fr)}
		.qwen-te-panel__hero-top{grid-template-columns:minmax(0,1fr)}
		.qwen-te-panel__hero-rail{justify-content:flex-start}
		.qwen-te-panel__signal-grid{grid-template-columns:1fr}
		.qwen-te-panel__meta{grid-template-columns:1fr}
		.qwen-te-panel__meta-card--summary{min-height:72px}
		.qwen-te-panel__actions-shell{grid-template-columns:minmax(0,1fr)}
		.qwen-te-panel__actions,
		.qwen-te-panel__actions--triple,
		.qwen-te-panel__actions--manager,
		.qwen-te-panel__actions--double,
		.qwen-te-panel__actions-tools{grid-template-columns:repeat(2,minmax(0,1fr))}
		.qwen-te-modal__split{grid-template-columns:1fr}
		.qwen-te-modal__sidebar{max-height:none}
		.qwen-te-modal__content{max-height:none}
		.qwen-te-preset-card__action-row--danger{grid-template-columns:minmax(0,1fr)}
	}
	`;
	document.head.appendChild(style);
}

function createEmptyPromptLibrary() {
	return { slot_config: [], tag_library: {}, custom_tag_library: {}, custom_tag_rules: {}, custom_tag_stats: {}, quick_presets: {} };
}

function buildNativePromptLibraryFallback(node) {
	const groupSlots = new Map();
	const groupTags = new Map();
	for (const widget of node?.widgets ?? []) {
		const match = /^(.+?)标签(\d+)$/u.exec(String(widget?.name ?? ""));
		if (!match) continue;
		const groupName = String(match[1] ?? "").trim();
		const slotIndex = Math.max(0, Number(match[2] ?? 0) || 0);
		if (!groupName || slotIndex <= 0) continue;
		groupSlots.set(groupName, Math.min(32, Math.max(groupSlots.get(groupName) ?? 0, slotIndex)));
		const tags = groupTags.get(groupName) ?? [];
		const optionValues = Array.isArray(widget?.options?.values) ? widget.options.values : [];
		for (const value of [...optionValues, widget?.value]) {
			const tag = String(value ?? "").trim();
			if (!tag || tag === "无" || tags.includes(tag)) continue;
			tags.push(tag);
		}
		groupTags.set(groupName, tags);
	}
	if (!groupSlots.size) return createEmptyPromptLibrary();
	return {
		slot_config: [...groupSlots].map(([name, slots]) => ({ name, slots })),
		tag_library: Object.fromEntries([...groupSlots.keys()].map((name) => [name, { "当前节点": groupTags.get(name) ?? [] }])),
		custom_tag_library: {},
		custom_tag_rules: {},
		custom_tag_stats: {},
		quick_presets: {},
		__native_fallback: true,
	};
}

function isUsablePromptLibrary(value) {
	return !!value
		&& typeof value === "object"
		&& !Array.isArray(value)
		&& Array.isArray(value.slot_config)
		&& value.tag_library
		&& typeof value.tag_library === "object"
		&& !Array.isArray(value.tag_library);
}

function hasPromptLibraryContent(value) {
	return isUsablePromptLibrary(value)
		&& value.slot_config.length > 0
		&& Object.keys(value.tag_library).length > 0;
}

async function getPromptLibrary(force = false) {
	const requestEpoch = promptLibraryEpoch;
	if (promptLibraryPromise && promptLibraryPromiseEpoch === requestEpoch) return await promptLibraryPromise;
	if (!force && !promptLibraryNeedsRefresh && promptLibrarySnapshot && promptLibrarySnapshotEpoch === requestEpoch) {
		return promptLibrarySnapshot;
	}
	const requestGeneration = promptLibraryRequestGeneration + 1;
	promptLibraryRequestGeneration = requestGeneration;
	let requestPromise = null;
	requestPromise = fetchJsonWithTimeout("/qwen_te/prompt_library", { cache: "no-cache" }, {
		owner: PROMPT_LIBRARY_REQUEST_OWNER,
		key: "prompt-library",
		replace: false,
		timeoutMs: 20000,
	})
		.then(({ response, data: library }) => {
			if (!response.ok) throw new Error(`HTTP ${response.status}`);
			if (!isUsablePromptLibrary(library)) throw new Error("invalid prompt library payload");
			const isLatestRequest = requestGeneration === promptLibraryRequestGeneration && requestEpoch === promptLibraryEpoch;
			if (isLatestRequest) {
				promptLibrarySnapshot = library;
				promptLibrarySnapshotEpoch = requestEpoch;
				promptLibraryNeedsRefresh = false;
				return library;
			}
			const currentPromise = promptLibraryPromise;
			if (currentPromise && currentPromise !== requestPromise) return currentPromise;
			if (promptLibrarySnapshot && promptLibrarySnapshotEpoch === promptLibraryEpoch) return promptLibrarySnapshot;
			return library;
		})
		.catch(() => {
			const isLatestRequest = requestGeneration === promptLibraryRequestGeneration && requestEpoch === promptLibraryEpoch;
			if (isLatestRequest) promptLibraryNeedsRefresh = true;
			const currentPromise = promptLibraryPromise;
			if (!isLatestRequest && currentPromise && currentPromise !== requestPromise) return currentPromise;
			return promptLibrarySnapshot ?? createEmptyPromptLibrary();
		})
		.finally(() => {
			if (promptLibraryPromise !== requestPromise) return;
			promptLibraryPromise = null;
			promptLibraryPromiseEpoch = -1;
		});
	promptLibraryPromise = requestPromise;
	promptLibraryPromiseEpoch = requestEpoch;
	return await requestPromise;
}

function invalidatePromptLibraryCache() {
	promptLibraryEpoch += 1;
	promptLibraryNeedsRefresh = true;
	return promptLibraryEpoch;
}

async function mutateTagLibrary(route, payload, options = {}) {
	const { response, data } = await fetchJsonWithTimeout(route, {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify(payload),
	}, {
		owner: options.owner,
		key: options.key ?? route,
		timeoutMs: options.timeoutMs ?? 30000,
	});
	if (!response.ok) {
		throw new Error(data.message || data.error || `HTTP ${response.status}`);
	}
	const normalizedRoute = String(route ?? "").split("?", 1)[0];
	if (PROMPT_LIBRARY_MUTATION_ROUTES.has(normalizedRoute)) invalidatePromptLibraryCache();
	return data;
}

async function suggestCustomTagGrouping(text, options = {}) {
	const tags = parseCustomTags(text);
	if (!tags.length) return { tags: [], summary: { total: 0, existing_count: 0, recommendable_count: 0, group_counts: {} } };
	const data = await mutateTagLibrary("/qwen_te/tag_library/suggest", { tag: text }, options);
	return data.detail ?? { tags: [], summary: { total: 0, existing_count: 0, recommendable_count: 0, group_counts: {} } };
}

function isOnlineNoiseTag(tagText) {
	const text = String(tagText ?? "").trim();
	if (!text) return true;
	const lowered = text.toLowerCase();
	if (/(duckduckgo|url\s*source|markdown\s*content|prompt\s*tags?|search\s*results?|at\s+duckduckgo|please\s*try\s*again|unexpected\s*error|please\s*shorten(?:\s+and)?\s*try\s*again|search\s*query\s*entered\s*was\s*too\s*long|cached\s*snapshot|caching\s*opt-?out|consider\s*retry\s*with\s*caching\s*opt-?out)/i.test(lowered)) return true;
	if (/^https?:\/\//i.test(lowered)) return true;
	const tokens = lowered.split(/\s+/u).filter(Boolean);
	if (tokens.length && tokens.every((token) => ["prompt", "tag", "tags", "search", "result", "results", "duckduckgo", "at", "please", "try", "again", "unexpected", "error", "warning"].includes(token))) return true;
	return false;
}

function getOnlineSearchCanonicalKey(value) {
	let text = String(value ?? "").trim();
	try { text = text.normalize("NFKC"); } catch (_error) {}
	return text.replace(/\s+/gu, " ").toLowerCase();
}

function normalizeOnlineSearchTagItems(rawItems, maxItems = 60) {
	const limit = Math.max(1, Math.min(60, Math.trunc(Number(maxItems) || 60)));
	const items = [];
	const byKey = new Map();
	for (const rawItem of rawItems ?? []) {
		const tag = String(rawItem?.tag ?? "").trim().replace(/\s+/gu, " ");
		const key = getOnlineSearchCanonicalKey(tag);
		if (!key || isOnlineNoiseTag(tag)) continue;
		const normalized = {
			tag,
			count: Math.max(1, Number(rawItem?.count ?? 1) || 1),
			confidence: Math.max(0, Math.min(1, Number(rawItem?.confidence ?? 0.5) || 0.5)),
			group: String(rawItem?.group ?? "").trim(),
			section: String(rawItem?.section ?? "").trim(),
			exists: !!rawItem?.exists,
			source: String(rawItem?.source ?? "").trim(),
		};
		const existing = byKey.get(key);
		if (!existing) {
			byKey.set(key, normalized);
			items.push(normalized);
			continue;
		}
		existing.count = Math.max(existing.count, normalized.count);
		existing.confidence = Math.max(existing.confidence, normalized.confidence);
		existing.exists = existing.exists || normalized.exists;
		if (!existing.group && normalized.group) existing.group = normalized.group;
		if (!existing.section && normalized.section) existing.section = normalized.section;
		if (!existing.source && normalized.source) existing.source = normalized.source;
	}
	return items.slice(0, limit);
}

function normalizeOnlineSearchSamples(rawSamples, maxItems = 6) {
	const limit = Math.max(1, Math.min(12, Math.trunc(Number(maxItems) || 6)));
	const samples = [];
	const seen = new Set();
	for (const rawSample of rawSamples ?? []) {
		const text = String(rawSample ?? "").trim().replace(/\s+/gu, " ").slice(0, 1200);
		const key = getOnlineSearchCanonicalKey(text);
		if (!key || seen.has(key)) continue;
		seen.add(key);
		samples.push(text);
		if (samples.length >= limit) break;
	}
	return samples;
}

function normalizeOnlinePromptItems(rawItems, rawSamples = [], maxItems = 16) {
    const limit = Math.max(1, Math.min(16, Math.trunc(Number(maxItems) || 16)));
    const sourceItems = Array.isArray(rawItems) && rawItems.length ? rawItems : Array.from(rawSamples ?? []);
    const items = [];
    const seen = new Set();
    for (const [index, rawItem] of sourceItems.entries()) {
        const rawPrompt = typeof rawItem === "string"
            ? rawItem
            : (rawItem?.prompt ?? rawItem?.text ?? rawItem?.sample ?? "");
        const prompt = String(rawPrompt ?? "").trim().replace(/\s+/gu, " ").slice(0, 1200);
        const key = getOnlineSearchCanonicalKey(prompt);
        if (!key || seen.has(key) || prompt.length < 8 || isOnlineNoiseTag(prompt)) continue;
        seen.add(key);
        const source = String(typeof rawItem === "object" ? rawItem?.source ?? "" : "").trim() || "unknown";
        const sourceLabel = String(typeof rawItem === "object" ? rawItem?.source_label ?? "" : "").trim()
            || (source.includes("local_fallback") ? "本地回退" : source);
        const confidence = Math.max(0, Math.min(1, Number(typeof rawItem === "object" ? rawItem?.confidence ?? 0.62 : 0.62) || 0.62));
        const segmentCount = Math.max(
            1,
            Number(typeof rawItem === "object" ? rawItem?.segment_count ?? 0 : 0)
                || parseCustomTags(prompt).length
                || 1,
        );
        items.push({
            id: String(typeof rawItem === "object" ? rawItem?.id ?? "" : "").trim() || key,
            prompt,
            tag: prompt,
            confidence,
            group: sourceLabel || "搜索结果",
            section: prompt.length >= 180 ? "详细提示词" : "精简提示词",
            exists: false,
            source,
            sourceLabel,
            count: segmentCount,
            length: Math.max(prompt.length, Number(typeof rawItem === "object" ? rawItem?.length ?? 0 : 0) || 0),
            rank: Math.max(1, Number(typeof rawItem === "object" ? rawItem?.rank ?? index + 1 : index + 1) || index + 1),
        });
        if (items.length >= limit) break;
    }
    return items;
}

function formatOnlineSearchWarning(rawWarning) {
	const providerNames = { searxng: "SearXNG", civitai: "Civitai", lexica: "Lexica", fetch: "检索", extract: "标签提取", policy: "策略" };
	const codeNames = {
		timeout: "超时",
		tls_error: "TLS 证书错误",
		invalid_json: "返回内容不是有效 JSON",
		invalid_schema: "返回结构不兼容",
		provider_error: "服务端拒绝请求",
		network_error: "网络不可用",
		request_failed: "请求失败",
		busy: "搜索任务繁忙",
		failed: "处理失败",
		public_sources_disabled: "已关闭公开来源回退",
		query_too_long_skip_online: "关键词较长，已跳过联网",
	};
	const messages = [];
	for (const rawPart of String(rawWarning ?? "").split(",")) {
		const part = rawPart.trim();
		if (!part) continue;
		const separator = part.indexOf(":");
		const provider = separator >= 0 ? part.slice(0, separator).trim() : "";
		const code = separator >= 0 ? part.slice(separator + 1).trim() : part;
		const httpMatch = /^http_(\d{3})$/u.exec(code);
		const codeText = httpMatch ? `HTTP ${httpMatch[1]}` : (codeNames[code] ?? "请求失败");
		const providerText = providerNames[provider] ?? provider;
		const message = providerText ? `${providerText}：${codeText}` : codeText;
		if (!messages.includes(message)) messages.push(message);
	}
	return messages.join("；");
}

function resolveOnlineSearchLibraryTags(rawTags, library) {
	const existingKeys = new Set(
		[...buildTagGroupIndex(library ?? createEmptyPromptLibrary()).keys()]
			.map((tag) => getOnlineSearchCanonicalKey(tag))
			.filter(Boolean),
	);
	const resolvedTags = [];
	const unresolvedTags = [];
	const seen = new Set();
	for (const rawTag of rawTags ?? []) {
		const tag = String(rawTag ?? "").trim();
		const key = getOnlineSearchCanonicalKey(tag);
		if (!key || seen.has(key)) continue;
		seen.add(key);
		if (existingKeys.has(key)) resolvedTags.push(tag);
		else unresolvedTags.push(tag);
	}
	return { existingKeys, resolvedTags, unresolvedTags };
}

function pushOnlineSearchBrowserHistory(rawItems, currentIndex, rawQuery, maxItems = 20) {
	const query = String(rawQuery ?? "").trim();
	const limit = Math.max(1, Math.min(50, Math.trunc(Number(maxItems) || 20)));
	const items = Array.from(rawItems ?? [], (item) => String(item ?? "").trim()).filter(Boolean);
	let index = Math.max(-1, Math.min(items.length - 1, Math.trunc(Number(currentIndex) || 0)));
	if (!query) return { items, index };
	if (index >= 0 && items[index] === query) return { items, index };
	const nextItems = items.slice(0, index + 1);
	nextItems.push(query);
	if (nextItems.length > limit) nextItems.splice(0, nextItems.length - limit);
	return { items: nextItems, index: nextItems.length - 1 };
}

function stepOnlineSearchBrowserHistory(rawItems, currentIndex, direction) {
	const items = Array.from(rawItems ?? [], (item) => String(item ?? "").trim()).filter(Boolean);
	if (!items.length) return { items, index: -1, query: "" };
	const current = Math.max(0, Math.min(items.length - 1, Math.trunc(Number(currentIndex) || 0)));
	const delta = Number(direction) < 0 ? -1 : 1;
	const index = Math.max(0, Math.min(items.length - 1, current + delta));
	return { items, index, query: items[index] ?? "" };
}

const PROMPT_BROWSER_HOME_ENTRY = "qwen-browser://home";
const PROMPT_BROWSER_SEARCH_BASE_URL = "https://www.google.com/search?igu=1&q=";
const PROMPT_BROWSER_EMBEDDED_RETRY_DELAY_MS = 2 * 60 * 1000;
let promptBrowserEmbeddedRetryAfter = 0;
const PROMPT_BROWSER_BLOCKED_SCHEMES = new Set([
	"about", "blob", "chrome", "data", "file", "ftp", "javascript", "mailto", "resource", "tel", "view-source", "ws", "wss",
]);

function parsePromptBrowserIpv4(hostname) {
	const match = /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/u.exec(String(hostname ?? ""));
	if (!match) return null;
	const parts = match.slice(1).map((part) => Number(part));
	return parts.every((part) => Number.isInteger(part) && part >= 0 && part <= 255) ? parts : null;
}

function isPromptBrowserNonPublicIpv4(parts) {
	if (!Array.isArray(parts) || parts.length !== 4) return true;
	const [a, b, c] = parts;
	if (a === 0 || a === 10 || a === 127 || a >= 224) return true;
	if (a === 100 && b >= 64 && b <= 127) return true;
	if (a === 169 && b === 254) return true;
	if (a === 172 && b >= 16 && b <= 31) return true;
	if (a === 192 && (b === 0 || b === 168)) return true;
	if (a === 198 && (b === 18 || b === 19 || (b === 51 && c === 100))) return true;
	if (a === 203 && b === 0 && c === 113) return true;
	return false;
}

function parsePromptBrowserIpv6(hostname) {
	let text = String(hostname ?? "").trim().toLowerCase();
	if (text.startsWith("[") && text.endsWith("]")) text = text.slice(1, -1);
	if (!text || text.includes("%")) return null;
	const halves = text.split("::");
	if (halves.length > 2) return null;
	const parseHalf = (half) => {
		if (!half) return [];
		const values = [];
		for (const token of half.split(":")) {
			if (!/^[0-9a-f]{1,4}$/u.test(token)) return null;
			values.push(Number.parseInt(token, 16));
		}
		return values;
	};
	const left = parseHalf(halves[0]);
	const right = parseHalf(halves[1] ?? "");
	if (!left || !right) return null;
	const missing = 8 - left.length - right.length;
	if ((halves.length === 1 && missing !== 0) || missing < 0) return null;
	const groups = halves.length === 2 ? [...left, ...Array(missing).fill(0), ...right] : left;
	return groups.length === 8 ? groups : null;
}

function isPromptBrowserNonPublicIpv6(groups) {
	if (!Array.isArray(groups) || groups.length !== 8) return true;
	const allZero = groups.every((group) => group === 0);
	const loopback = groups.slice(0, 7).every((group) => group === 0) && groups[7] === 1;
	if (allZero || loopback) return true;
	const first = groups[0];
	if ((first & 0xfe00) === 0xfc00) return true;
	if ((first & 0xffc0) === 0xfe80) return true;
	if ((first & 0xff00) === 0xff00) return true;
	if (first === 0x2001 && groups[1] === 0x0db8) return true;
	const isIpv4Mapped = groups.slice(0, 5).every((group) => group === 0) && (groups[5] === 0 || groups[5] === 0xffff);
	if (isIpv4Mapped) {
		return isPromptBrowserNonPublicIpv4([
			(groups[6] >> 8) & 0xff,
			groups[6] & 0xff,
			(groups[7] >> 8) & 0xff,
			groups[7] & 0xff,
		]);
	}
	return false;
}

function isPromptBrowserBlockedHostname(rawHostname) {
	let hostname = String(rawHostname ?? "").trim().toLowerCase().replace(/\.$/u, "");
	if (hostname.startsWith("[") && hostname.endsWith("]")) hostname = hostname.slice(1, -1);
	if (!hostname || hostname === "localhost" || !hostname.includes(".")) return true;
	if ([".localhost", ".local", ".lan", ".internal", ".home", ".home.arpa", ".test", ".invalid"].some((suffix) => hostname.endsWith(suffix))) return true;
	const ipv4 = parsePromptBrowserIpv4(hostname);
	if (ipv4) return isPromptBrowserNonPublicIpv4(ipv4);
	if (hostname.includes(":")) return isPromptBrowserNonPublicIpv6(parsePromptBrowserIpv6(hostname));
	return false;
}

function resolvePromptBrowserTarget(rawTarget, options = {}) {
	let input = String(rawTarget ?? "").trim();
	try { input = input.normalize("NFKC"); } catch (_error) {}
	const maxLength = Math.max(256, Math.min(4096, Math.trunc(Number(options.maxLength) || 2048)));
	const invalid = (reason, message) => ({ ok: false, kind: "invalid", url: "", input, reason, message });
	if (!input) return invalid("empty", "请输入网址或网页搜索词。");
	if (input.length > maxLength) return invalid("too_long", `网址或搜索词不能超过 ${maxLength} 个字符。`);
	if (/[\u0000-\u001f\u007f]/u.test(input)) return invalid("control_character", "网址不能包含控制字符。");
	if (input.startsWith("//")) return invalid("ambiguous_url", "请输入包含 http:// 或 https:// 的完整网址。");
	const schemeMatch = /^([a-z][a-z0-9+.-]*):/iu.exec(input);
	const scheme = String(schemeMatch?.[1] ?? "").toLowerCase();
	if (scheme && PROMPT_BROWSER_BLOCKED_SCHEMES.has(scheme)) return invalid("blocked_scheme", `不允许打开 ${scheme}: 地址。`);
	const explicitHttpUrl = scheme === "http" || scheme === "https";
	const hostLike = /^(?:localhost|\[[0-9a-f:.]+\]|(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63})(?::\d{1,5})?(?:[/?#]|$)/iu.test(input)
		|| /^(?:0x[0-9a-f]+|0[0-7]+|\d+(?:\.\d+){1,3})(?::\d{1,5})?(?:[/?#]|$)/iu.test(input);
	if (!explicitHttpUrl && !hostLike) {
		const query = input.replace(/\s+/gu, " ").trim();
		return {
			ok: true,
			kind: "search",
			url: `${PROMPT_BROWSER_SEARCH_BASE_URL}${encodeURIComponent(query)}`,
			input,
			query,
			display: query,
		};
	}
	const candidate = explicitHttpUrl ? input : `https://${input}`;
	let parsed;
	try {
		parsed = new URL(candidate);
	} catch (_error) {
		return invalid("invalid_url", "网址格式无效。");
	}
	if (!['http:', 'https:'].includes(parsed.protocol)) return invalid("blocked_scheme", "只允许打开 http 或 https 网站。");
	if (parsed.username || parsed.password) return invalid("credentials", "网址不能包含用户名或密码。");
	if (parsed.port === "0") return invalid("invalid_port", "网址端口不能为 0。");
	if (isPromptBrowserBlockedHostname(parsed.hostname)) return invalid("private_host", "不能打开本机、局域网或保留地址。");
	let currentOrigin = String(options.currentOrigin ?? "").trim();
	try { currentOrigin = currentOrigin ? new URL(currentOrigin).origin : ""; } catch (_error) { currentOrigin = ""; }
	if (currentOrigin && parsed.origin === currentOrigin) return invalid("same_origin", "不能在网页浏览器中嵌套当前 ComfyUI 页面。");
	if (parsed.href.length > maxLength) return invalid("too_long", `网址不能超过 ${maxLength} 个字符。`);
	return { ok: true, kind: "url", url: parsed.href, input, query: "", display: parsed.href };
}

function openPromptBrowserExternal(rawTarget, options = {}) {
	const target = resolvePromptBrowserTarget(rawTarget, options);
	if (!target.ok) return { ...target, opened: false };
	if (typeof options.openWindow !== "function") {
		const documentRef = options.document ?? globalThis.document;
		const parent = documentRef?.body ?? documentRef?.documentElement;
		if (typeof documentRef?.createElement === "function" && parent?.appendChild) {
			try {
				const link = documentRef.createElement("a");
				link.href = target.url;
				link.target = "_blank";
				link.rel = "noopener noreferrer";
				link.style.display = "none";
				parent.appendChild(link);
				link.click();
				link.remove?.();
				return { ...target, opened: true, reason: "" };
			} catch (_error) {}
		}
	}
	const openWindow = options.openWindow ?? globalThis.window?.open?.bind?.(globalThis.window);
	if (typeof openWindow !== "function") return { ...target, opened: false, reason: "unavailable", message: "当前环境不能打开新标签页。" };
	let child = null;
	try { child = openWindow(target.url, "_blank", "noopener,noreferrer"); } catch (_error) {}
	try { if (child) child.opener = null; } catch (_error) {}
	return child
		? { ...target, opened: true, reason: "" }
		: { ...target, opened: false, reason: "popup_blocked", message: "新标签页被浏览器拦截。" };
}

async function launchPromptCompanionBrowser(rawTarget, options = {}) {
	const target = resolvePromptBrowserTarget(rawTarget, options);
	if (!target.ok) return { ...target, launched: false };
	const requestJson = options.requestJson ?? fetchJsonWithTimeout;
	try {
		const { response, data } = await requestJson("/qwen_te/companion_browser/open", {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
				"X-Qwen-TE-Companion-Browser": "1",
			},
			body: JSON.stringify({ url: target.url }),
		}, {
			owner: options.owner,
			key: options.key ?? "companion-browser",
			timeoutMs: options.timeoutMs ?? 15000,
		});
		if (!response?.ok || !data?.ok) {
			return {
				...target,
				launched: false,
				reason: `http_${Number(response?.status ?? 0) || 0}`,
				message: String(data?.message ?? `完整浏览器启动失败：HTTP ${response?.status ?? 0}`),
			};
		}
		return {
			...target,
			launched: true,
			reason: "",
			browser: String(data?.browser ?? "完整浏览器"),
			message: String(data?.message ?? "完整浏览器已启动。"),
		};
	} catch (error) {
		return {
			...target,
			launched: false,
			reason: error?.name === "AbortError" ? "aborted" : "request_failed",
			message: error?.name === "AbortError" ? "完整浏览器启动请求已取消。" : `完整浏览器启动失败：${error?.message ?? error}`,
		};
	}
}

function resolveEmbeddedBrowserViewport(rect, options = {}) {
    const sourceWidth = Number(rect?.width);
    const sourceHeight = Number(rect?.height);
    const minWidth = Math.max(480, Math.trunc(Number(options.minWidth) || 640));
    const minHeight = Math.max(270, Math.trunc(Number(options.minHeight) || 360));
    const maxWidth = Math.max(minWidth, Math.trunc(Number(options.maxWidth) || 1920));
    const maxHeight = Math.max(minHeight, Math.trunc(Number(options.maxHeight) || 1080));
    const fallbackWidth = Math.max(minWidth, Math.min(maxWidth, Math.trunc(Number(options.fallbackWidth) || 1440)));
    const fallbackHeight = Math.max(minHeight, Math.min(maxHeight, Math.trunc(Number(options.fallbackHeight) || 810)));
    if (![sourceWidth, sourceHeight].every((value) => Number.isFinite(value) && value > 0)) {
        return { width: fallbackWidth, height: fallbackHeight };
    }
    const aspect = sourceWidth / sourceHeight;
    let width = Math.max(minWidth, Math.min(maxWidth, Math.round(sourceWidth)));
    let height = Math.round(width / aspect);
    if (height > maxHeight) {
        height = maxHeight;
        width = Math.round(height * aspect);
    }
    if (height < minHeight) {
        height = minHeight;
        width = Math.round(height * aspect);
    }
    if (width > maxWidth) {
        width = maxWidth;
        height = Math.round(width / aspect);
    }
    if (width < minWidth) {
        width = minWidth;
        height = Math.round(width / aspect);
    }
    return {
        width: Math.max(minWidth, Math.min(maxWidth, width)),
        height: Math.max(minHeight, Math.min(maxHeight, height)),
    };
}
function getEmbeddedBrowserFrameCaptureProfile(rect, options = {}) {
	const fast = !!options.fast;
	const hasFrame = !!options.hasFrame;
	const settled = !!options.pageReady && hasFrame && !fast;
	const viewport = resolveEmbeddedBrowserViewport(rect, {
		minWidth: 640,
		minHeight: 360,
		maxWidth: 1920,
		maxHeight: 1080,
		fallbackWidth: 1440,
		fallbackHeight: 810,
	});
	const requestedPixelRatio = Number(options.pixelRatio ?? globalThis.devicePixelRatio ?? 1);
	const pixelRatio = settled && Number.isFinite(requestedPixelRatio)
		? Math.max(1, Math.min(1.5, requestedPixelRatio))
		: 1;
	return {
		maxWidth: Math.min(2880, Math.round(viewport.width * pixelRatio)),
		maxHeight: Math.min(1620, Math.round(viewport.height * pixelRatio)),
		quality: settled ? 90 : (hasFrame ? 72 : 76),
		profile: settled ? "sharp" : "fast",
		pixelRatio,
	};
}
function mapEmbeddedBrowserPointerPoint(clientX, clientY, rect, frameWidth, frameHeight, viewportWidth, viewportHeight) {
	const box = rect ?? {};
	const rectWidth = Number(box.width);
	const rectHeight = Number(box.height);
	const sourceWidth = Number(frameWidth);
	const sourceHeight = Number(frameHeight);
	const targetWidth = Number(viewportWidth);
	const targetHeight = Number(viewportHeight);
	if (![rectWidth, rectHeight, sourceWidth, sourceHeight, targetWidth, targetHeight].every((value) => Number.isFinite(value) && value > 0)) return null;
	const scale = Math.min(rectWidth / sourceWidth, rectHeight / sourceHeight);
	if (!(scale > 0)) return null;
	const renderedWidth = sourceWidth * scale;
	const renderedHeight = sourceHeight * scale;
	const left = Number(box.left ?? box.x ?? 0) + (rectWidth - renderedWidth) / 2;
	const top = Number(box.top ?? box.y ?? 0) + (rectHeight - renderedHeight) / 2;
	const localX = Number(clientX) - left;
	const localY = Number(clientY) - top;
	if (![localX, localY].every(Number.isFinite)) return null;
	if (localX < 0 || localY < 0 || localX > renderedWidth || localY > renderedHeight) return null;
	return {
		x: (localX / renderedWidth) * targetWidth,
		y: (localY / renderedHeight) * targetHeight,
	};
}

async function requestEmbeddedPromptBrowser(route, payload, options = {}) {
	const requestJson = options.requestJson ?? fetchJsonWithTimeout;
	const { response, data } = await requestJson(`/qwen_te/embedded_browser/${route}`, {
		method: "POST",
		headers: {
			"Content-Type": "application/json",
			"X-Qwen-TE-Companion-Browser": "1",
		},
		body: JSON.stringify(payload ?? {}),
	}, {
		owner: options.owner,
		key: options.key ?? `embedded-browser-${route}`,
		replace: options.replace,
		timeoutMs: options.timeoutMs ?? 20000,
	});
	if (!response?.ok || !data?.ok) {
		const error = new Error(String(data?.message ?? `内嵌浏览器请求失败：HTTP ${response?.status ?? 0}`));
		error.status = Number(response?.status ?? 0) || 0;
		throw error;
	}
	return data;
}

async function fetchEmbeddedPromptBrowserFrame(sessionId, options = {}) {
	const request = options.request ?? fetchWithTimeout;
	const previousFrameId = String(options.previousFrameId ?? "").trim();
	const response = await request("/qwen_te/embedded_browser/frame", {
		method: "POST",
		headers: {
			"Content-Type": "application/json",
			"X-Qwen-TE-Companion-Browser": "1",
		},
		body: JSON.stringify({
			session_id: String(sessionId ?? ""),
			previous_frame_id: previousFrameId,
			max_width: Math.max(480, Math.min(2880, Math.trunc(Number(options.maxWidth) || 1440))),
			max_height: Math.max(270, Math.min(1620, Math.trunc(Number(options.maxHeight) || 810))),
			quality: Math.max(40, Math.min(92, Math.trunc(Number(options.quality) || 76))),
		}),
		cache: "no-store",
	}, {
		owner: options.owner,
		key: options.key ?? "embedded-browser-frame",
		replace: options.replace,
		timeoutMs: options.timeoutMs ?? 20000,
	});
	const frameId = String(response?.headers?.get?.("X-Qwen-TE-Frame-Id") ?? "").trim();
	if (Number(response?.status ?? 0) === 204) return { changed: false, frameId, blob: null };
	if (!response?.ok) {
		let message = `内嵌浏览器画面请求失败：HTTP ${response?.status ?? 0}`;
		try {
			const data = await response.clone().json();
			if (data?.message) message = String(data.message);
		} catch (_error) {}
		const error = new Error(message);
		error.status = Number(response?.status ?? 0) || 0;
		throw error;
	}
	const blob = await response.blob();
	if (!String(blob?.type ?? "").toLowerCase().startsWith("image/")) throw new Error("内嵌浏览器返回的画面格式无效。");
	return { changed: true, frameId, blob };
}

const ONLINE_QUERY_LOW_VALUE_TERMS = new Set([
	"8k",
	"4k",
	"高细节",
	"摄影质感",
	"无文字",
	"无水印",
	"无logo",
	"主体突出",
	"景深层次自然",
	"材质细节丰富",
	"写实肤感自然",
	"皮肤质感柔和",
	"布料褶皱自然",
]);
const ONLINE_QUERY_EXPANSION_RULES = [
	{ keys: ["成人", "私房", "adult", "nsfw"], terms: ["adult", "nsfw", "boudoir"] },
	{ keys: ["半身", "上半身", "中景半身", "waist up"], terms: ["half body", "waist up", "medium shot"] },
	{ keys: ["写真", "人像", "portrait"], terms: ["portrait", "editorial portrait"] },
];

function buildOnlineSearchQuery(rawQuery, maxTerms = 6) {
	const sourceText = String(rawQuery ?? "").trim();
	if (!sourceText) return { query: "", dropped: 0, normalized: false };
	const chunks = parseCustomTags(sourceText);
	const seeds = chunks.length ? chunks : sourceText.split(/\s+/u).filter(Boolean);
	const terms = [];
	const seen = new Set();
	let dropped = 0;
	for (const seed of seeds) {
		const normalized = String(seed ?? "").normalize("NFKC").replace(/\s+/gu, " ").trim();
		if (!normalized) continue;
		const pieces = /[\u4e00-\u9fff]/u.test(normalized) ? [normalized] : normalized.split(/\s+/u);
		for (const piece of pieces) {
			const term = String(piece ?? "").trim();
			if (!term) continue;
			const lowered = term.toLowerCase();
			if (ONLINE_QUERY_LOW_VALUE_TERMS.has(lowered)) {
				dropped += 1;
				continue;
			}
			if (term.length > 32) {
				dropped += 1;
				continue;
			}
			if (seen.has(lowered)) continue;
			seen.add(lowered);
			terms.push(term);
			if (terms.length >= maxTerms) break;
		}
		if (terms.length >= maxTerms) break;
	}
	const normalizedSource = sourceText.normalize("NFKC").toLowerCase();
	for (const rule of ONLINE_QUERY_EXPANSION_RULES) {
		const keys = Array.isArray(rule?.keys) ? rule.keys : [];
		const hit = keys.some((key) => normalizedSource.includes(String(key ?? "").toLowerCase()));
		if (!hit) continue;
		for (const termText of (Array.isArray(rule?.terms) ? rule.terms : [])) {
			const term = String(termText ?? "").trim();
			if (!term) continue;
			const lowered = term.toLowerCase();
			if (seen.has(lowered)) continue;
			seen.add(lowered);
			terms.push(term);
			if (terms.length >= maxTerms) break;
		}
		if (terms.length >= maxTerms) break;
	}
	if (!terms.length) {
		return {
			query: sourceText.slice(0, 64),
			dropped,
			normalized: sourceText.length > 64,
		};
	}
	const query = terms.join(" ");
	return {
		query,
		dropped,
		normalized: query !== sourceText,
	};
}

function chunkOnlineImportTags(rawTags, batchSize = 12) {
	const size = Math.max(1, Math.min(12, Math.trunc(Number(batchSize) || 12)));
	const tags = [];
	const seen = new Set();
	for (const rawTag of rawTags ?? []) {
		const tag = String(rawTag ?? "").trim();
		if (!tag || seen.has(tag)) continue;
		seen.add(tag);
		tags.push(tag);
	}
	const batches = [];
	for (let start = 0; start < tags.length; start += size) batches.push(tags.slice(start, start + size));
	return batches;
}

function resolveOnlineSearchSelectedTags(candidateItems, selectedTags, options = {}) {
	const selected = new Set();
	for (const rawTag of selectedTags ?? []) {
		const tag = String(rawTag ?? "").trim();
		if (tag) selected.add(tag);
	}
	if (!selected.size) return [];
	const onlyHigh = !!options.onlyHighConfidence;
	const requestedThreshold = Number(options.highConfidenceThreshold ?? 0.72);
	const highConfidenceThreshold = Number.isFinite(requestedThreshold) ? requestedThreshold : 0.72;
	const resolved = [];
	const seen = new Set();
	for (const item of candidateItems ?? []) {
		const tag = String(item?.tag ?? "").trim();
		if (!tag || !selected.has(tag) || seen.has(tag)) continue;
		const confidence = Number(item?.confidence ?? 0);
		if (onlyHigh && (!Number.isFinite(confidence) || confidence < highConfidenceThreshold)) continue;
		seen.add(tag);
		resolved.push(tag);
	}
	return resolved;
}

async function searchOnlinePromptTags(query, limit = 24, options = {}) {
    const normalized = String(query ?? "").trim();
    if (!normalized) return { prompts: [], promptItems: [], tags: [], tagItems: [], samples: [], source: "none", message: "请输入主题或提示词后再搜索。" };
    const data = await mutateTagLibrary("/qwen_te/tag_library/online_search", { query: normalized, limit }, {
        ...options,
        timeoutMs: options.timeoutMs ?? 90000,
    });
    const rawItems = Array.isArray(data?.tag_items) ? data.tag_items : [];
    const normalizedItems = normalizeOnlineSearchTagItems(rawItems, limit);
    const fallbackItems = normalizeOnlineSearchTagItems(
        parseCustomTags((data?.tags ?? []).join(", ")).map((tag, index) => ({
            tag,
            count: Math.max(1, normalizedItems.length - index),
            confidence: 0.55,
            group: "",
            section: "",
            exists: false,
            source: "legacy_tags",
        })),
        limit,
    );
    const tagItems = normalizedItems.length ? normalizedItems : fallbackItems;
    const tags = tagItems.map((item) => item.tag);
    const samples = normalizeOnlineSearchSamples(
        Array.isArray(data?.prompts) && data.prompts.length ? data.prompts : (Array.isArray(data?.samples) ? data.samples : []),
        12,
    );
    let promptItems = normalizeOnlinePromptItems(
        Array.isArray(data?.prompt_items) ? data.prompt_items : [],
        samples,
        Math.min(16, limit),
    );
    if (!promptItems.length && tags.length) {
        promptItems = normalizeOnlinePromptItems([], [tags.join(", ")], 1);
    }
    return {
        prompts: promptItems.map((item) => item.prompt),
        promptItems,
        tags,
        tagItems,
        samples: promptItems.map((item) => item.prompt),
        source: String(data?.source ?? "unknown"),
        message: String(data?.message ?? ""),
        warning: String(data?.warning ?? ""),
        cached: !!data?.cached,
    };
}
async function searchOnlinePrompts(query, limit = 24, options = {}) {
    return searchOnlinePromptTags(query, limit, options);
}
async function requestQualityAudit(payload = {}, options = {}) {
	const { response, data } = await fetchJsonWithTimeout("/qwen_te/quality_audit", {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify(payload),
	}, {
		owner: options.owner,
		key: options.key ?? "quality-audit",
		timeoutMs: options.timeoutMs ?? 180000,
	});
	if (!response.ok) {
		throw new Error(data.message || data.error || `HTTP ${response.status}`);
	}
	return data;
}

async function requestWorkflowHistory(maxItems = 24, options = {}) {
	const limit = Math.max(1, Math.min(120, Math.trunc(Number(maxItems) || 24)));
	const { response, data } = await fetchJsonWithTimeout(`/history?max_items=${encodeURIComponent(limit)}`, {}, {
		owner: options.owner,
		key: options.key ?? "workflow-history",
		timeoutMs: options.timeoutMs ?? 20000,
	});
	if (!response.ok) {
		throw new Error(data?.message || data?.error || `HTTP ${response.status}`);
	}
	return data && typeof data === "object" ? data : {};
}


function beginNodeLibraryRefresh(node) {
	if (!node || typeof node !== "object") return 0;
	const nextRevision = Math.max(0, Number(node[NODE_LIBRARY_REFRESH_REVISION_KEY] ?? 0) || 0) + 1;
	node[NODE_LIBRARY_REFRESH_REVISION_KEY] = nextRevision;
	return nextRevision;
}

function isNodeLibraryRefreshCurrent(node, revision) {
	const expected = Math.max(0, Number(revision ?? 0) || 0);
	return !!node && !node[NODE_REMOVED_KEY] && expected > 0 && Number(node[NODE_LIBRARY_REFRESH_REVISION_KEY] ?? 0) === expected;
}

async function refreshLibraryOnNode(node, options = {}) {
	const refreshRevision = beginNodeLibraryRefresh(node);
	const mutationRevision = Math.max(0, Number(options.mutationRevision ?? 0) || 0);
	const library = await getPromptLibrary(options.force === true);
	if (!isNodeLibraryRefreshCurrent(node, refreshRevision)) return node?.[PANEL_KEY]?.library ?? library;
	if (mutationRevision > 0 && !isNodeStateMutationCurrent(node, mutationRevision)) return node?.[PANEL_KEY]?.library ?? library;
	if (typeof options.commitGuard === "function" && !options.commitGuard()) return node?.[PANEL_KEY]?.library ?? library;
	if (node[PANEL_KEY]) {
		node[PANEL_KEY].library = library;
		node[PANEL_KEY].rawTagWidgetNames = getRawTagWidgetNames(library);
		bindSummaryRefresh(node, library);
	}
	syncRawWidgetOptions(node, library);
	if (node[PANEL_KEY]) {
		setWidgetGroupVisibility(node, node[PANEL_KEY].rawTagWidgetNames, false, "Raw");
		refreshSlotPanel(node);
	}
	refreshNodeSummary(node, library);
	return library;
}

function ensureNodeProperties(node) {
	node.properties = node.properties ?? {};
	return node.properties;
}

function createNodeCacheNamespace() {
	if (typeof globalThis.crypto?.randomUUID === "function") {
		try { return `node-${globalThis.crypto.randomUUID()}`; } catch (_error) {}
	}
	const randomPart = () => Math.random().toString(36).slice(2, 12);
	return `node-${Date.now().toString(36)}-${randomPart()}-${randomPart()}`;
}

function ensureNodeCacheNamespace(node) {
	const properties = ensureNodeProperties(node);
	let namespace = String(properties[NODE_CACHE_NAMESPACE_KEY] ?? "").trim();
	const graphNodes = Array.isArray(app?.graph?._nodes) ? app.graph._nodes : [];
	const duplicate = NODE_CACHE_NAMESPACE_PATTERN.test(namespace) && graphNodes.some((otherNode) => (
		otherNode !== node
		&& String(otherNode?.properties?.[NODE_CACHE_NAMESPACE_KEY] ?? "").trim() === namespace
	));
	if (!NODE_CACHE_NAMESPACE_PATTERN.test(namespace) || duplicate) {
		const occupied = new Set(graphNodes
			.filter((otherNode) => otherNode !== node)
			.map((otherNode) => String(otherNode?.properties?.[NODE_CACHE_NAMESPACE_KEY] ?? "").trim())
			.filter((value) => NODE_CACHE_NAMESPACE_PATTERN.test(value)));
		do { namespace = createNodeCacheNamespace(); } while (occupied.has(namespace));
		properties[NODE_CACHE_NAMESPACE_KEY] = namespace;
		if (duplicate) {
			delete properties[NODE_MODEL_API_RUNTIME_SIGNATURE_KEY];
			delete properties[NODE_WORKFLOW_OUTPUT_KEY];
			invalidateModelApiRuntimeStatus(node);
			if (node?.[PANEL_KEY]) {
				node[PANEL_KEY].lastExecutionOutputs = [];
				node[PANEL_KEY].directStageOutputCache = null;
				node[PANEL_KEY].hydratedExecutionOutputs = [];
				node[PANEL_KEY].previewExecutionOutputs = [];
			}
		}
	}
	return namespace;
}

function getNodeAutoNegativeSyncEnabled(node) {
	return !!ensureNodeProperties(node)[NODE_AUTO_NEGATIVE_SYNC_KEY];
}

function setNodeAutoNegativeSyncEnabled(node, enabled) {
	const nextValue = !!enabled;
	ensureNodeProperties(node)[NODE_AUTO_NEGATIVE_SYNC_KEY] = nextValue;
	if (node?.[PANEL_KEY]) node[PANEL_KEY].autoNegativeSync = nextValue;
}

function getNodeContinuousReportMeta(node) {
	const meta = ensureNodeProperties(node)[NODE_CONTINUOUS_REPORT_KEY];
	return meta && typeof meta === "object" ? meta : null;
}

function setNodeContinuousReportMeta(node, meta) {
	ensureNodeProperties(node)[NODE_CONTINUOUS_REPORT_KEY] = meta;
	if (node?.[PANEL_KEY]) node[PANEL_KEY].continuousReportMeta = meta;
}

function clearNodeContinuousReportMeta(node) {
	delete ensureNodeProperties(node)[NODE_CONTINUOUS_REPORT_KEY];
	if (node?.[PANEL_KEY]) delete node[PANEL_KEY].continuousReportMeta;
}

function normalizeContinuousRunReport(entries) {
	if (!Array.isArray(entries)) return [];
	return entries
		.filter((item) => item && typeof item === "object")
		.map((item) => ({
			at: Number(item.at ?? Date.now()),
			level: String(item.level ?? "记录"),
			message: String(item.message ?? ""),
			presetName: String(item.presetName ?? ""),
			origin: String(item.origin ?? "continuous"),
			round: Math.max(0, Math.trunc(Number(item.round ?? 0) || 0)),
			total: Math.max(0, Math.trunc(Number(item.total ?? 0) || 0)),
		}))
		.filter((item) => item.message)
		.slice(0, 50);
}

function getNodeContinuousRunReport(node) {
	return normalizeContinuousRunReport(ensureNodeProperties(node)[NODE_CONTINUOUS_LOG_KEY]);
}

function setNodeContinuousRunReport(node, report) {
	const nextReport = normalizeContinuousRunReport(report);
	ensureNodeProperties(node)[NODE_CONTINUOUS_LOG_KEY] = nextReport;
	if (node?.[PANEL_KEY]) node[PANEL_KEY].continuousRunReport = nextReport;
}

function clearNodeContinuousRunReport(node) {
	delete ensureNodeProperties(node)[NODE_CONTINUOUS_LOG_KEY];
	if (node?.[PANEL_KEY]) delete node[PANEL_KEY].continuousRunReport;
}

function normalizePresetBatchState(state) {
	const payload = state && typeof state === "object" ? state : {};
	const selectedIds = Array.isArray(payload.selectedIds)
		? [...new Set(payload.selectedIds.map((id) => String(id ?? "").trim()).filter(Boolean))]
		: [];
	const continuousCount = Math.max(1, Math.min(99, Math.trunc(Number(payload.continuousCount ?? 3) || 3)));
	return { selectedIds, continuousCount };
}

function getNodePresetBatchState(node) {
	return normalizePresetBatchState(ensureNodeProperties(node)[NODE_PRESET_BATCH_STATE_KEY]);
}

function setNodePresetBatchState(node, state) {
	const nextState = normalizePresetBatchState(state);
	ensureNodeProperties(node)[NODE_PRESET_BATCH_STATE_KEY] = nextState;
	if (node?.[PANEL_KEY]) node[PANEL_KEY].presetBatchState = nextState;
}

function addPresetToNodeBatchState(node, presetId) {
	const id = String(presetId ?? "").trim();
	if (!id) return { ok: false, changed: false, count: getNodePresetBatchState(node).selectedIds.length };
	const batchState = getNodePresetBatchState(node);
	if (batchState.selectedIds.includes(id)) {
		return { ok: true, changed: false, count: batchState.selectedIds.length };
	}
	const nextSelectedIds = [...batchState.selectedIds, id];
	setNodePresetBatchState(node, {
		...batchState,
		selectedIds: nextSelectedIds,
	});
	return { ok: true, changed: true, count: nextSelectedIds.length };
}

function setExclusivePresetBatchState(node, presetId) {
	const id = String(presetId ?? "").trim();
	if (!id) return { ok: false, changed: false, count: getNodePresetBatchState(node).selectedIds.length };
	const batchState = getNodePresetBatchState(node);
	const currentIds = batchState.selectedIds;
	const changed = currentIds.length !== 1 || currentIds[0] !== id;
	setNodePresetBatchState(node, {
		...batchState,
		selectedIds: [id],
	});
	return { ok: true, changed, count: 1 };
}

function normalizeRandomCoreState(state) {
	const payload = state && typeof state === "object" ? state : {};
	return cloneSelectionOnlyState(payload);
}

function getRandomCoreSignature(settings = {}) {
	return JSON.stringify({
		mode: String(settings["运行时随机模式"] ?? "全随机"),
		lockedCount: Math.max(0, Number(settings["核心标签锁定数量"] ?? 10)),
		whitelist: parseCustomTags(settings["锁定标签白名单"]).sort(),
		exclude: parseCustomTags(settings["随机排除标签"]).sort(),
	});
}

function getNodeRandomCoreState(node) {
	const state = ensureNodeProperties(node)[NODE_RANDOM_CORE_STATE_KEY];
	return state && typeof state === "object" ? normalizeRandomCoreState(state) : null;
}

function setNodeRandomCoreState(node, state) {
	ensureNodeProperties(node)[NODE_RANDOM_CORE_STATE_KEY] = normalizeRandomCoreState(state);
}

function clearNodeRandomCoreState(node) {
	delete ensureNodeProperties(node)[NODE_RANDOM_CORE_STATE_KEY];
}

function getNodeRandomCoreSignature(node) {
	return String(ensureNodeProperties(node)[NODE_RANDOM_CORE_SIGNATURE_KEY] ?? "");
}

function setNodeRandomCoreSignature(node, signature) {
	ensureNodeProperties(node)[NODE_RANDOM_CORE_SIGNATURE_KEY] = String(signature ?? "");
}

function clearNodeRandomCoreSignature(node) {
	delete ensureNodeProperties(node)[NODE_RANDOM_CORE_SIGNATURE_KEY];
}

function getNodeRandomLastState(node) {
	const state = ensureNodeProperties(node)[NODE_RANDOM_LAST_STATE_KEY];
	return state && typeof state === "object" ? normalizeRandomCoreState(state) : null;
}

function setNodeRandomLastState(node, state) {
	ensureNodeProperties(node)[NODE_RANDOM_LAST_STATE_KEY] = normalizeRandomCoreState(state);
}

function clearNodeRandomLastState(node) {
	delete ensureNodeProperties(node)[NODE_RANDOM_LAST_STATE_KEY];
}

function normalizeRandomComboHistory(entries) {
	if (!Array.isArray(entries)) return [];
	const seen = new Set();
	const normalized = [];
	for (const entry of entries) {
		if (!entry || typeof entry !== "object") continue;
		const identity = String(entry.identity ?? "").trim();
		const scene = String(entry.scene ?? "").trim();
		if (!identity || !scene) continue;
		const key = `${identity}__${scene}`;
		if (seen.has(key)) continue;
		seen.add(key);
		normalized.push({ identity, scene });
		if (normalized.length >= RANDOM_COMBO_HISTORY_LIMIT) break;
	}
	return normalized;
}

function getNodeRandomComboHistory(node) {
	return normalizeRandomComboHistory(ensureNodeProperties(node)[NODE_RANDOM_COMBO_HISTORY_KEY]);
}

function setNodeRandomComboHistory(node, entries) {
	ensureNodeProperties(node)[NODE_RANDOM_COMBO_HISTORY_KEY] = normalizeRandomComboHistory(entries);
}

function pushNodeRandomComboHistory(node, identity, scene) {
	const normalizedIdentity = String(identity ?? "").trim();
	const normalizedScene = String(scene ?? "").trim();
	if (!normalizedIdentity || !normalizedScene) return;
	const next = [{ identity: normalizedIdentity, scene: normalizedScene }, ...getNodeRandomComboHistory(node)];
	setNodeRandomComboHistory(node, next);
}

function getNodeRandomComboPreview(node) {
	const preview = ensureNodeProperties(node)[NODE_RANDOM_COMBO_PREVIEW_KEY];
	if (!preview || typeof preview !== "object") return null;
	const identity = String(preview.identity ?? "").trim();
	const scene = String(preview.scene ?? "").trim();
	if (!identity || !scene) return null;
	return { identity, scene };
}

function setNodeRandomComboPreview(node, preview) {
	const identity = String(preview?.identity ?? "").trim();
	const scene = String(preview?.scene ?? "").trim();
	if (!identity || !scene) {
		delete ensureNodeProperties(node)[NODE_RANDOM_COMBO_PREVIEW_KEY];
		return;
	}
	ensureNodeProperties(node)[NODE_RANDOM_COMBO_PREVIEW_KEY] = { identity, scene };
}

function getNodeQualityAuditMeta(node) {
	const meta = ensureNodeProperties(node)[NODE_QUALITY_AUDIT_KEY];
	return meta && typeof meta === "object" ? meta : null;
}

function setNodeQualityAuditMeta(node, meta) {
	ensureNodeProperties(node)[NODE_QUALITY_AUDIT_KEY] = meta;
	if (node?.[PANEL_KEY]) node[PANEL_KEY].qualityAuditMeta = meta;
}

function getNodeWorkflowOutputMeta(node) {
	const meta = ensureNodeProperties(node)[NODE_WORKFLOW_OUTPUT_KEY];
	return meta && typeof meta === "object" ? meta : null;
}

function setNodeWorkflowOutputMeta(node, meta) {
	ensureNodeProperties(node)[NODE_WORKFLOW_OUTPUT_KEY] = meta;
	if (node?.[PANEL_KEY]) node[PANEL_KEY].workflowOutputMeta = meta;
}

function normalizeHistoryPromptIds(items = []) {
	return [...new Set((items ?? []).map((item) => String(item ?? "").trim()).filter(Boolean))];
}

function getHistoryEntryPromptTuple(entry) {
	return Array.isArray(entry?.prompt) ? entry.prompt : null;
}

function getHistoryEntryPromptGraph(entry) {
	const promptTuple = getHistoryEntryPromptTuple(entry);
	const promptGraph = promptTuple?.[2];
	return promptGraph && typeof promptGraph === "object" ? promptGraph : null;
}

function getHistoryEntryCreateTime(entry) {
	const promptTuple = getHistoryEntryPromptTuple(entry);
	const extraData = promptTuple?.[3];
	const createdAt = Number(extraData?.create_time ?? 0);
	return Number.isFinite(createdAt) && createdAt > 0 ? createdAt : 0;
}

function historyEntryContainsNode(entry, node) {
	const promptGraph = getHistoryEntryPromptGraph(entry);
	return !!(promptGraph && Object.prototype.hasOwnProperty.call(promptGraph, String(node?.id ?? "")));
}

function collectHistoryEntryImageRecords(entry) {
	const outputs = entry?.outputs;
	if (!outputs || typeof outputs !== "object") return [];
	const preferOutput = [];
	const fallbackImages = [];
	const pushRecord = (bucket, image, ownerNodeId) => {
		const filename = String(image?.filename ?? "").trim();
		if (!filename) return;
		bucket.push({
			filename,
			subfolder: String(image?.subfolder ?? "").trim(),
			type: String(image?.type ?? "output").trim() || "output",
			ownerNodeId: String(ownerNodeId ?? ""),
		});
	};
	for (const [ownerNodeId, output] of Object.entries(outputs)) {
		const images = output?.images;
		if (!Array.isArray(images)) continue;
		for (const image of images) {
			const imageType = String(image?.type ?? "output").trim().toLowerCase();
			pushRecord(imageType === "output" ? preferOutput : fallbackImages, image, ownerNodeId);
		}
	}
	const records = preferOutput.length ? preferOutput : fallbackImages;
	const seen = new Set();
	return records.filter((record) => {
		const key = `${record.type}::${record.subfolder}::${record.filename}`;
		if (seen.has(key)) return false;
		seen.add(key);
		return true;
	});
}

function normalizeStageTextValue(value) {
	if (typeof value === "string") return value;
	if (value == null) return "";
	if (typeof value === "number" || typeof value === "boolean") return String(value);
	if (Array.isArray(value)) {
		const flattened = value
			.map((item) => normalizeStageTextValue(item))
			.filter((item) => item.trim());
		return flattened.join("\n");
	}
	if (typeof value === "object") {
		const direct = [
			value.text,
			value.string,
			value.value,
			value.content,
			value.prompt,
			value.prompt_text,
			value.positivePrompt,
			value.positive_prompt,
			value.result,
			value.output,
			value.display_text,
		]
			.map((item) => normalizeStageTextValue(item))
			.find((item) => item.trim());
		if (direct) return direct;
	}
	return "";
}

function iterInputReferences(value, callback) {
	if (Array.isArray(value)) {
		if (value.length >= 2 && (typeof value[0] === "string" || typeof value[0] === "number")) {
			callback(String(value[0]), Number(value[1]));
		}
		for (const item of value) iterInputReferences(item, callback);
		return;
	}
	if (!value || typeof value !== "object") return;
	for (const item of Object.values(value)) iterInputReferences(item, callback);
}

function extractStageOutputsFromHistoryEntry(entry, node) {
	const outputs = entry?.outputs;
	const stageId = String(node?.id ?? "");
	if (!stageId) return [];
	const stageOutputPayload = outputs?.[stageId];
	const result = Array.from({ length: STAGE_OUTPUT_FIELD_KEYS.length }, () => "");
	if (stageOutputPayload && typeof stageOutputPayload === "object") {
		const directValues = extractStageOutputSlotsFromPayload(stageOutputPayload);
		directValues.forEach((value, index) => {
			if (index < result.length && String(value ?? "").trim()) result[index] = String(value);
		});
	}
	const promptGraph = getHistoryEntryPromptGraph(entry);
	if (!promptGraph || typeof promptGraph !== "object") {
		return result.some((item) => item.trim()) ? result : [];
	}
	for (const [nodeId, nodeDef] of Object.entries(promptGraph)) {
		if (!nodeDef || typeof nodeDef !== "object") continue;
		const inputValues = Object.values(nodeDef.inputs ?? {});
		let matchedSlot = -1;
		for (const inputValue of inputValues) {
			iterInputReferences(inputValue, (sourceNodeId, slot) => {
				if (matchedSlot >= 0) return;
				if (sourceNodeId === stageId && Number.isFinite(slot) && slot >= 0 && slot < result.length) {
					matchedSlot = slot;
				}
			});
			if (matchedSlot >= 0) break;
		}
		if (matchedSlot < 0) continue;
		const linkedOutput = outputs?.[String(nodeId)];
		if (!linkedOutput || typeof linkedOutput !== "object") continue;
		const linkedValues = normalizeStageExecutionOutputs(linkedOutput);
		const textValue = linkedValues.find((item) => String(item ?? "").trim());
		if (textValue && !result[matchedSlot]) result[matchedSlot] = String(textValue);
	}
	return result.some((item) => item.trim()) ? result : [];
}

function buildWorkflowOutputMetaFromHistory(promptId, entry, node = null) {
	const imageRecords = collectHistoryEntryImageRecords(entry);
	const stageOutputs = node ? extractStageOutputsFromHistoryEntry(entry, node) : [];
	if (!imageRecords.length && !stageOutputs.length) return null;
	return {
		promptId: String(promptId ?? ""),
		createdAt: getHistoryEntryCreateTime(entry),
		capturedAt: Date.now(),
		imageCount: imageRecords.length,
		images: cloneJsonSafe(imageRecords, []),
		stageOutputs: cloneJsonSafe(stageOutputs, []),
	};
}

function getNodeWorkflowHistorySearchAfter(node, fallbackWindowMs = 120000) {
	const queuedAt = Number(node?.[PANEL_KEY]?.lastWorkflowQueueRequestedAt ?? 0);
	const executedAt = getNodeExecutionStamp(node);
	const executedWindowStart = executedAt > 0 ? Math.max(0, executedAt - fallbackWindowMs) : 0;
	return Math.max(Number.isFinite(queuedAt) && queuedAt > 0 ? queuedAt : 0, executedWindowStart);
}

function markNodeWorkflowQueueRequested(node, at = Date.now()) {
	if (!node?.[PANEL_KEY]) return;
	node[PANEL_KEY].lastWorkflowQueueRequestedAt = Number(at ?? Date.now()) || Date.now();
	const modelSource = normalizeModelSourceValue(getModelWidget(node, "模型来源")?.value);
	const apiConfig = modelSource === "API接口" ? getModelApiEffectiveConfig(node) : null;
	const apiReady = !!apiConfig?.baseUrl && !!apiConfig?.model && !getModelApiConfigValidationError(node);
	node[PANEL_KEY].pendingModelApiConfigSignature = apiReady ? buildModelApiConfigSignature(node) : "";
	node[PANEL_KEY].stageOutputPollIdleCount = 0;
	node[PANEL_KEY].stageOutputPollActiveCount = 0;
	ensureStageOutputPolling(node);
}

function getNodeWorkflowQueueRequestedAt(node, fallback = Date.now()) {
	const queuedAt = Number(node?.[PANEL_KEY]?.lastWorkflowQueueRequestedAt ?? 0) || 0;
	return queuedAt > 0 ? queuedAt : Math.max(0, Number(fallback ?? 0) || 0);
}

async function findLatestNodeWorkflowOutputFromHistory(node, options = {}) {
	if (!node) return null;
	const excludePromptIds = new Set(normalizeHistoryPromptIds(options.excludePromptIds));
	const createdAfter = Math.max(0, Number(options.createdAfter ?? 0) || 0);
	const maxItems = Math.max(
		12,
		Math.min(120, Math.trunc(Number(options.maxItems ?? (24 + excludePromptIds.size * 3))) || 24),
	);
	const history = await requestWorkflowHistory(maxItems, {
		owner: options.requestOwner ?? node,
		key: options.requestKey ?? "workflow-history",
		timeoutMs: options.requestTimeoutMs,
	});
	const entries = Object.entries(history ?? {});
	for (let index = entries.length - 1; index >= 0; index -= 1) {
		const [promptId, entry] = entries[index];
		if (!promptId || excludePromptIds.has(promptId)) continue;
		if (!historyEntryContainsNode(entry, node)) continue;
		const createdAt = getHistoryEntryCreateTime(entry);
		if (createdAfter > 0) {
			if (createdAt <= 0) continue;
			if (createdAt + 2000 < createdAfter) continue;
		}
		const meta = buildWorkflowOutputMetaFromHistory(promptId, entry, node);
		if (!meta) continue;
		return meta;
	}
	return null;
}

async function syncNodeWorkflowOutputMetaFromHistory(node, options = {}) {
	const meta = await findLatestNodeWorkflowOutputFromHistory(node, options);
	if (typeof options.shouldCommit === "function" && !options.shouldCommit()) return null;
	if (meta) {
		setNodeWorkflowOutputMeta(node, meta);
		if (node?.[PANEL_KEY]?.pendingModelApiConfigSignature) rememberModelApiRuntimeSignature(node, meta.stageOutputs);
	}
	return meta;
}

async function waitForNodeWorkflowOutput(node, options = {}) {
	const timeoutMs = Math.max(0, Number(options.timeoutMs ?? 0) || 0);
	const pollMs = Math.max(500, Number(options.pollMs ?? 1200) || 1200);
	const startedAt = Date.now();
	let lastError = null;
	do {
		if (typeof options.shouldCancel === "function" && options.shouldCancel()) return null;
		try {
			const meta = await syncNodeWorkflowOutputMetaFromHistory(node, options);
			if (meta) return meta;
			lastError = null;
		} catch (error) {
			lastError = error;
		}
		if (timeoutMs <= 0) break;
		await sleep(pollMs);
	} while (Date.now() - startedAt < timeoutMs);
	if (options.throwOnError && lastError) throw lastError;
	return null;
}

async function resolveNodeWorkflowAuditPromptIds(node, options = {}) {
	const explicitPromptIds = normalizeHistoryPromptIds([
		options.historyPromptId,
		...(Array.isArray(options.historyPromptIds) ? options.historyPromptIds : []),
	]);
	if (explicitPromptIds.length) return explicitPromptIds;
	const searchAfter = Math.max(0, Number(options.historyCreatedAfter ?? getNodeWorkflowHistorySearchAfter(node)) || 0);
	const cachedMeta = getNodeWorkflowOutputMeta(node);
	const cachedCreatedAt = Number(cachedMeta?.createdAt ?? 0) || 0;
	if (cachedMeta?.promptId && (!searchAfter || (cachedCreatedAt > 0 && cachedCreatedAt + 2000 >= searchAfter))) {
		return [String(cachedMeta.promptId)];
	}
	const meta = await waitForNodeWorkflowOutput(node, {
		createdAfter: searchAfter,
		maxItems: options.historyMaxItems,
		timeoutMs: searchAfter > 0 ? Number(options.historyWaitTimeoutMs ?? 12000) || 12000 : 0,
		pollMs: options.historyPollMs,
		shouldCancel: options.shouldCancel,
		shouldCommit: options.shouldCommit,
		requestOwner: options.requestOwner,
		requestKey: options.historyRequestKey ?? "quality-audit-history",
	});
	return meta?.promptId ? [String(meta.promptId)] : [];
}

async function waitForNodeContinuousWorkflowOutput(node, options = {}) {
	return await waitForNodeWorkflowOutput(node, {
		createdAfter: options.createdAfter,
		excludePromptIds: options.excludePromptIds,
		maxItems: options.maxItems,
		timeoutMs: Number(options.timeoutMs ?? 180000) || 180000,
		pollMs: options.pollMs,
		shouldCancel: options.shouldCancel,
		shouldCommit: options.shouldCommit,
		requestOwner: options.requestOwner,
		requestKey: options.requestKey ?? "continuous-workflow-history",
	});
}

function formatQualityAuditSummary(summary) {
	if (!summary || typeof summary !== "object") return "";
	return `OCR ${summary.ocr_risk_images ?? 0} | 皱纹 ${summary.wrinkle_risk_images ?? 0} | 磨皮 ${summary.oversmooth_risk_images ?? 0}`;
}

function buildQualityAuditHistoryMeta(node) {
	const meta = getNodeQualityAuditMeta(node);
	if (!meta?.summary) return null;
	return {
		at: Number(meta.at ?? Date.now()),
		summary: cloneJsonSafe(meta.summary, null),
		markdown: String(meta.markdown ?? ""),
	};
}

async function runNodeQualityAudit(node, options = {}) {
	const revision = Math.max(0, Number(node?.[NODE_QUALITY_AUDIT_REVISION_KEY] ?? 0) || 0) + 1;
	if (node) node[NODE_QUALITY_AUDIT_REVISION_KEY] = revision;
	const isCurrent = () => !node?.[NODE_REMOVED_KEY] && node?.[NODE_QUALITY_AUDIT_REVISION_KEY] === revision;
	const limit = Math.max(1, Math.min(24, Number(options.limit ?? 6) || 6));
	const payload = { limit };
	const historyPromptIds = await resolveNodeWorkflowAuditPromptIds(node, {
		...options,
		shouldCancel: () => !isCurrent() || options.shouldCancel?.(),
		shouldCommit: isCurrent,
	});
	if (!isCurrent()) return { ok: false, stale: true, result: null, markdown: "", summaryText: "" };
	if (historyPromptIds.length) payload.history_prompt_ids = historyPromptIds;
	else if (options.afterTimestamp != null) payload.after_timestamp = Number(options.afterTimestamp);
	const data = await requestQualityAudit(payload, {
		owner: options.requestOwner ?? node,
		key: options.requestKey ?? "quality-audit",
		timeoutMs: options.requestTimeoutMs,
	});
	if (!isCurrent()) return { ok: false, stale: true, result: null, markdown: "", summaryText: "" };
	const result = data?.result ?? { summary: { total_images: 0, ocr_risk_images: 0, wrinkle_risk_images: 0, oversmooth_risk_images: 0 }, images: [] };
	const summaryText = formatQualityAuditSummary(result.summary);
	setNodeQualityAuditMeta(node, { at: Date.now(), summary: result.summary ?? null, markdown: String(data?.markdown ?? "") });
	if (node?.[PANEL_KEY]?.library) refreshNodeSummary(node, node[PANEL_KEY].library);
	return {
		ok: !!data?.ok,
		message: String(data?.message ?? ""),
		result,
		markdown: String(data?.markdown ?? ""),
		summaryText,
	};
}

function readNodeRandomDedupeCache(node) {
	const widget = getWidget(node, RANDOM_DEDUPE_CACHE_WIDGET_NAME);
	return parseCustomTags(widget?.value ?? "");
}

function writeNodeRandomDedupeCache(node, tags) {
	const serialized = parseCustomTags((tags ?? []).join(", ")).join(", ");
	setWidgetValue(node, RANDOM_DEDUPE_CACHE_WIDGET_NAME, serialized);
}

function clearNodeRandomDedupeCache(node) {
	setWidgetValue(node, RANDOM_DEDUPE_CACHE_WIDGET_NAME, "");
}

function syncNodeRandomDedupeCacheFromResult(node, payload = null) {
	const data = payload && typeof payload === "object" ? payload : getStageJsonPayload(node);
	if (!data || typeof data !== "object") return;
	if (data.runtime_random_preview_marker_present) {
		setWidgetValue(node, RUNTIME_RANDOM_PREVIEW_TOKEN_WIDGET_NAME, "");
	}
	const generatedTags = data.runtime_random_enabled && Array.isArray(data.runtime_random_generated_tags)
		? data.runtime_random_generated_tags
		: [];
	const profileMarkers = Array.isArray(data.profile_rotation_markers) ? data.profile_rotation_markers : [];
	const cacheEntries = [...generatedTags, ...profileMarkers];
	if (!cacheEntries.length) {
		clearNodeRandomDedupeCache(node);
		return;
	}
	writeNodeRandomDedupeCache(node, cacheEntries);
}

function syncNodePromptDedupeCacheFromResult(node, payload = null) {
	const data = payload && typeof payload === "object" ? payload : getStageJsonPayload(node);
	if (!data || typeof data !== "object") return;
	const serialized = String(data.prompt_dedupe_cache ?? "").trim();
	if (!serialized) return;
	setWidgetValue(node, PROMPT_DEDUPE_CACHE_WIDGET_NAME, serialized);
}

function getNodeRandomRuntimeDiagnostics(node) {
	const data = getStageJsonPayload(node);
	if (!data || typeof data !== "object" || !data.runtime_random_enabled) return null;
	return {
		adultSubpool: String(data.runtime_random_adult_subpool ?? "").trim(),
		mainSceneGroup: String(data.runtime_random_main_scene_group ?? "").trim(),
		mainIdentity: String(data.runtime_random_main_identity ?? "").trim(),
		styleTrack: String(data.runtime_random_style_track ?? "").trim(),
	};
}

function formatRandomRuntimeDiagnostics(node) {
	const diag = getNodeRandomRuntimeDiagnostics(node);
	if (!diag) return "";
	const bits = [];
	if (diag.adultSubpool) bits.push(`成人池 ${diag.adultSubpool}`);
	if (diag.mainSceneGroup) bits.push(`片场组 ${diag.mainSceneGroup}`);
	if (diag.mainIdentity) bits.push(`主身份 ${diag.mainIdentity}`);
	if (diag.styleTrack) bits.push(`轨道 ${diag.styleTrack}`);
	return bits.join(" | ");
}

function getRandomTrackHistoryItems(node) {
	const data = getStageJsonPayload(node);
	if (!data || typeof data !== "object") return [];
	const current = String(data.runtime_random_style_track ?? "").trim();
	const merged = [];
	if (current) merged.push(current);
	if (Array.isArray(data.recent_style_tracks)) {
		for (const item of data.recent_style_tracks) {
			const text = String(item ?? "").trim();
			if (!text || merged.includes(text)) continue;
			merged.push(text);
			if (merged.length >= 3) break;
		}
	}
	return merged.slice(0, 3);
}

function refreshRandomTrackHistory(node) {
	const container = node?.[PANEL_KEY]?.randomTrackHistoryEl;
	if (!(container instanceof HTMLElement)) return;
	container.replaceChildren();
	const items = getRandomTrackHistoryItems(node);
	if (!items.length) return;
	for (const item of items) {
		const pill = document.createElement("div");
		pill.className = "qwen-te-panel__hero-history-pill";
		pill.textContent = item;
		container.appendChild(pill);
	}
}

function buildRandomTrackHistoryText(node) {
	const items = getRandomTrackHistoryItems(node);
	if (!items.length) return "";
	return `轨道历史 ${items.join(" / ")}`;
}

function refreshRandomRuntimePills(node) {
	const container = node?.[PANEL_KEY]?.randomRuntimePillsEl;
	if (!(container instanceof HTMLElement)) return;
	container.replaceChildren();
	const comboPreview = getNodeRandomComboPreview(node);
	const diag = getNodeRandomRuntimeDiagnostics(node);
	if (!diag && !comboPreview) return;
	const runtime = ensureNodeContinuousRuntime(node);
	const items = [
		{ text: comboPreview?.identity ? `本次身份 ${comboPreview.identity}` : "", interactive: false },
		{ text: comboPreview?.scene ? `本次场景 ${comboPreview.scene}` : "", interactive: false },
		{ text: diag?.adultSubpool ? `成人池 ${diag.adultSubpool}` : "", interactive: false },
		{ text: diag?.mainSceneGroup ? `片场组 ${diag.mainSceneGroup}` : "", interactive: false },
		{ text: diag?.mainIdentity ? `主身份 ${diag.mainIdentity}` : "", interactive: false },
		{ text: diag?.styleTrack ? `当前轨道 ${diag.styleTrack}` : "", interactive: false },
		{ text: comboPreview ? "换一组身景" : "", interactive: true },
	];
	for (const item of items) {
		const text = String(item?.text ?? "").trim();
		if (!text) continue;
		const pill = document.createElement(item?.interactive ? "button" : "div");
		if (item?.interactive) {
			pill.type = "button";
			pill.className = "qwen-te-panel__hero-runtime-pill qwen-te-panel__hero-runtime-pill--action";
			pill.disabled = !!runtime.running;
			pill.title = runtime.running ? "连续测试进行中，先停止后再换一组。" : "重新自动组合一组人物身份和场景。";
			pill.addEventListener("pointerdown", (event) => { event.stopPropagation(); });
			pill.addEventListener("mousedown", (event) => { event.stopPropagation(); });
			pill.addEventListener("click", async (event) => {
				event.stopPropagation();
				if (pill.disabled) return;
				const mutationRevision = beginNodeStateMutation(node);
				const nextLibrary = await getFreshLibraryForUi(node, node?.[PANEL_KEY]?.library ?? null, { mutationRevision });
				if (!isNodeStateMutationCurrent(node, mutationRevision)) return;
				await applyIdentitySceneComboRandom(node, nextLibrary, { queue: false, mutationRevision });
			});
		} else {
			pill.className = "qwen-te-panel__hero-runtime-pill";
		}
		pill.textContent = text;
		container.appendChild(pill);
	}
}

function clearNodeRandomRuntimeState(node) {
	clearNodeRandomCoreState(node);
	clearNodeRandomCoreSignature(node);
	clearNodeRandomLastState(node);
}

function getHistoryReportPayload(item) {
	const reportPayload = item?.meta?.reportPayload;
	if (reportPayload && typeof reportPayload === "object") return reportPayload;
	const aggregatePayload = item?.meta?.aggregatePayload;
	if (aggregatePayload && typeof aggregatePayload === "object") return aggregatePayload;
	return null;
}

function getHistoryReportAggregate(item) {
	const payload = getHistoryReportPayload(item);
	if (!payload || typeof payload !== "object") return null;
	return payload.aggregate ?? payload.latestAggregate ?? null;
}

function resolvePresetFromHistoryReport(item) {
	const reportPayload = getHistoryReportPayload(item);
	const reportAggregate = getHistoryReportAggregate(item);
	const presetId = String(item?.meta?.reportPresetId ?? reportPayload?.presetId ?? "").trim();
	const presetName = String(reportAggregate?.presetName ?? reportPayload?.presetName ?? "").trim();
	const presets = getUserPresets();
	if (presetId) {
		const matchedById = presets.find((preset) => String(preset.id ?? "").trim() === presetId);
		if (matchedById) return matchedById;
	}
	if (presetName) {
		const matchedByName = presets.find((preset) => String(preset.name ?? "").trim() === presetName);
		if (matchedByName) return matchedByName;
	}
	return null;
}

function ensurePresetForHistoryReport(item) {
	const existingPreset = resolvePresetFromHistoryReport(item);
	if (existingPreset) return { preset: existingPreset, created: false, snapshotName: "" };
	const reportPayload = getHistoryReportPayload(item);
	const reportAggregate = getHistoryReportAggregate(item);
	if (!reportPayload || !item?.state) return { preset: null, created: false, snapshotName: "" };
	const isAggregateHistoryReport = item?.source === "history-aggregate-report" || Array.isArray(reportPayload?.reportPayloads);
	const snapshotName = isAggregateHistoryReport
		? buildHistoryAggregateSnapshotName(reportPayload)
		: `单预设快照-${String(reportAggregate?.presetName ?? reportPayload?.presetName ?? "未标注预设").trim() || "未标注预设"}-${buildCompactTimestamp(item?.updatedAt ?? Date.now())}`;
	const snapshotSource = isAggregateHistoryReport ? "history-aggregate" : "single-preset";
	const snapshotMeta = isAggregateHistoryReport
		? buildHistoryAggregateSnapshotMeta(reportPayload)
		: {
			presetName: String(reportAggregate?.presetName ?? reportPayload?.presetName ?? ""),
			successRate: String(reportAggregate?.successRate ?? "待定"),
			outcomeTrail: String(reportAggregate?.outcomeTrail ?? "·"),
			risk: String(reportAggregate?.risk?.label ?? "未知"),
		};
	const saved = saveUserPreset(snapshotName, item.state, {
		source: snapshotSource,
		meta: snapshotMeta,
	});
	if (!saved) return { preset: null, created: false, snapshotName };
	const createdPreset = getUserPresets().find((preset) => String(preset.name ?? "").trim() === snapshotName) ?? null;
	return { preset: createdPreset, created: true, snapshotName };
}

function ensurePresetForHistoryAggregateItem(item) {
	const latestItem = item?.latestItem ?? null;
	const existingPreset = latestItem ? resolvePresetFromHistoryReport(latestItem) : null;
	if (existingPreset) return { preset: existingPreset, created: false, snapshotName: "" };
	const snapshotState = latestItem?.state ?? null;
	if (!snapshotState) return { preset: null, created: false, snapshotName: "" };
	const snapshotName = buildHistoryAggregateSnapshotName(item);
	const saved = saveUserPreset(snapshotName, snapshotState, {
		source: "history-aggregate",
		meta: buildHistoryAggregateSnapshotMeta(item),
	});
	if (!saved) return { preset: null, created: false, snapshotName };
	const createdPreset = getUserPresets().find((preset) => String(preset.name ?? "").trim() === snapshotName) ?? null;
	return { preset: createdPreset, created: true, snapshotName };
}

function formatContinuousReportSummary(meta) {
	if (!meta || typeof meta !== "object") return "";
	const level = String(meta.level ?? "").trim();
	const summary = String(meta.summary ?? "").trim();
	if (!summary) return "";
	return level ? `${level} | ${summary}` : summary;
}

function buildContinuousPanelBadgeState(node) {
	const runtime = node?.[PANEL_KEY]?.continuousRuntime;
	if (runtime?.running) {
		const modeText = runtime.mode === "random" ? "随机" : "轮流";
		return {
			text: `连测进行 ${runtime.step}/${runtime.total}`,
			title: `${modeText}连续测试进行中`,
			muted: false,
		};
	}
	const batchState = getNodePresetBatchState(node);
	const meta = getNodeContinuousReportMeta(node);
	const selectedCount = batchState.selectedIds.length;
	const runCount = batchState.continuousCount;
	if (meta?.summary) {
		return {
			text: `连测 ${String(meta.level ?? "记录").trim() || "记录"}`,
			title: `${meta.summary}${selectedCount ? ` | 已选 ${selectedCount} 预设` : ""}${runCount ? ` | ${runCount} 轮` : ""}`,
			muted: false,
		};
	}
	if (selectedCount) {
		return {
			text: `连测就绪 ${selectedCount}`,
			title: `已配置 ${selectedCount} 个预设，连续测试轮数 ${runCount}`,
			muted: false,
		};
	}
	return {
		text: "连测未配",
		title: "还没有配置连续测试预设。",
		muted: true,
	};
}

function normalizeUserPresetItem(item) {
	if (!item || typeof item !== "object" || !item.name || !item.state) return null;
	const source = String(item.source ?? "manual");
	const meta = item.meta && typeof item.meta === "object" ? { ...item.meta } : {};
	const name = String(item.name ?? "").trim().slice(0, USER_PRESET_NAME_MAX_CHARS);
	if (!name) return null;
	return {
		id: String(item.id ?? `preset_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`),
		name,
		updatedAt: Number(item.updatedAt ?? Date.now()),
		state: clonePresetState(item.state),
		source,
		meta,
		favorite: !!item.favorite,
	};
}

function boundUserPresets(presets) {
	const seen = new Set();
	const result = [];
	let totalBytes = 2;
	for (const item of presets ?? []) {
		if (result.length >= USER_PRESET_LIMIT) break;
		const normalized = normalizeUserPresetItem(item);
		if (!normalized) continue;
		const key = normalized.name.toLowerCase();
		if (seen.has(key)) continue;
		const itemBytes = utf8ByteLength(normalized);
		if (itemBytes > USER_PRESET_ITEM_MAX_BYTES || totalBytes + itemBytes > USER_PRESET_TOTAL_MAX_BYTES) continue;
		seen.add(key);
		result.push(normalized);
		totalBytes += itemBytes + 1;
	}
	return result;
}

function getUserPresets() {
	try {
		const raw = localStorage.getItem(USER_PRESET_STORAGE_KEY);
		const parsed = JSON.parse(raw ?? "[]");
		return Array.isArray(parsed) ? boundUserPresets(parsed) : [];
	} catch (_error) {
		return [];
	}
}

function setUserPresets(presets) {
	try {
		const bounded = boundUserPresets(presets);
		localStorage.setItem(USER_PRESET_STORAGE_KEY, JSON.stringify(bounded));
		return true;
	} catch (_error) {
		return false;
	}
}

function formatPresetTime(timestamp) {
	const value = Number(timestamp);
	if (!Number.isFinite(value) || value <= 0) return "未知时间";
	try {
		return new Date(value).toLocaleString("zh-CN", {
			year: "numeric",
			month: "2-digit",
			day: "2-digit",
			hour: "2-digit",
			minute: "2-digit",
		});
	} catch (_error) {
		return String(value);
	}
}

function buildCompactTimestamp(timestamp = Date.now()) {
	const value = Number(timestamp);
	if (!Number.isFinite(value) || value <= 0) return "unknown";
	const date = new Date(value);
	const parts = [
		date.getFullYear(),
		String(date.getMonth() + 1).padStart(2, "0"),
		String(date.getDate()).padStart(2, "0"),
		String(date.getHours()).padStart(2, "0"),
		String(date.getMinutes()).padStart(2, "0"),
	];
	return parts.join("");
}

function saveUserPreset(name, state, options = {}) {
	const presetName = String(name ?? "").trim();
	if (!presetName || presetName.length > USER_PRESET_NAME_MAX_CHARS) return false;
	const presets = getUserPresets();
	const now = Date.now();
	const nextPreset = {
		id: `preset_${now}_${Math.random().toString(36).slice(2, 8)}`,
		name: presetName,
		updatedAt: now,
		state: clonePresetState(state),
		source: String(options.source ?? "manual"),
		meta: options.meta && typeof options.meta === "object" ? { ...options.meta } : {},
		favorite: !!options.favorite,
	};
	if (utf8ByteLength(nextPreset) > USER_PRESET_ITEM_MAX_BYTES) return false;
	const existingIndex = presets.findIndex((item) => String(item.name ?? "").trim() === presetName);
	if (existingIndex >= 0) {
		const existing = presets[existingIndex];
		nextPreset.id = String(existing.id ?? nextPreset.id);
		if (!options.source) nextPreset.source = String(existing.source ?? nextPreset.source);
		nextPreset.meta = { ...(existing.meta ?? {}), ...(nextPreset.meta ?? {}) };
		if (options.favorite == null) nextPreset.favorite = !!existing.favorite;
		presets.splice(existingIndex, 1, nextPreset);
	} else {
		presets.unshift(nextPreset);
	}
	const bounded = boundUserPresets(presets);
	if (!bounded.some((item) => item.id === nextPreset.id)) return false;
	return setUserPresets(bounded);
}


function updateUserPreset(id, changes = {}) {
	const presetId = String(id ?? "").trim();
	if (!presetId) return { ok: false, reason: "missing-id" };
	const presets = getUserPresets();
	const index = presets.findIndex((item) => String(item.id ?? "") === presetId);
	if (index < 0) return { ok: false, reason: "not-found" };
	const existing = presets[index];
	const nextName = String(changes.name ?? existing.name ?? "").trim();
	if (!nextName || nextName.length > USER_PRESET_NAME_MAX_CHARS) return { ok: false, reason: "invalid-name" };
	const duplicate = presets.some((item, itemIndex) => (
		itemIndex !== index
		&& String(item.name ?? "").trim().toLowerCase() === nextName.toLowerCase()
	));
	if (duplicate) return { ok: false, reason: "duplicate-name" };
	const nextPreset = normalizeUserPresetItem({
		...existing,
		name: nextName,
		state: clonePresetState(changes.state ?? existing.state),
		updatedAt: Date.now(),
	});
	if (!nextPreset || utf8ByteLength(nextPreset) > USER_PRESET_ITEM_MAX_BYTES) {
		return { ok: false, reason: "too-large" };
	}
	const nextPresets = [...presets];
	nextPresets.splice(index, 1, nextPreset);
	const bounded = boundUserPresets(nextPresets);
	if (!bounded.some((item) => String(item.id ?? "") === presetId)) return { ok: false, reason: "capacity" };
	if (!setUserPresets(bounded)) return { ok: false, reason: "storage" };
	return { ok: true, preset: bounded.find((item) => String(item.id ?? "") === presetId) ?? nextPreset };
}

function formatPresetSelectionEditorText(state, library) {
	const lines = [];
	for (const group of library?.slot_config ?? []) {
		const groupName = String(group?.name ?? "").trim();
		if (!groupName) continue;
		const values = uniqueTextList(state?.selected?.[groupName] ?? []);
		lines.push(`${groupName}: ${values.join(", ")}`);
	}
	lines.push(`自定义补充标签: ${uniqueTextList(state?.customTags ?? []).join(", ")}`);
	return lines.join("\n");
}

function parsePresetSelectionEditorText(rawText, library) {
	const groups = (library?.slot_config ?? []).map((group) => String(group?.name ?? "").trim()).filter(Boolean);
	const groupSet = new Set(groups);
	const selected = Object.fromEntries(groups.map((groupName) => [groupName, []]));
	const customTags = [];
	const errors = [];
	const lines = String(rawText ?? "").split(/\r?\n/u);
	for (let index = 0; index < lines.length; index += 1) {
		const line = lines[index].trim();
		if (!line) continue;
		const separatorIndex = line.search(/[:：]/u);
		if (separatorIndex < 0) {
			for (const tag of parseCustomTags(line)) addUniqueTag(customTags, tag);
			continue;
		}
		const label = line.slice(0, separatorIndex).trim();
		const values = parseCustomTags(line.slice(separatorIndex + 1));
		if (label === "自定义补充标签" || label === "自定义标签") {
			for (const tag of values) addUniqueTag(customTags, tag);
			continue;
		}
		if (!groupSet.has(label)) {
			errors.push(`第 ${index + 1} 行包含未知分组：${label}`);
			continue;
		}
		for (const tag of values) addUniqueTag(selected[label], tag);
	}
	return errors.length ? { ok: false, error: errors.join("；") } : { ok: true, selected, customTags };
}

function formatPresetSettingsEditorText(state) {
	try { return JSON.stringify(state?.settings ?? {}, null, 2); } catch (_error) { return "{}"; }
}

function parsePresetSettingsEditorText(rawText) {
	let parsed;
	try {
		parsed = JSON.parse(String(rawText ?? "").trim() || "{}");
	} catch (error) {
		return { ok: false, error: `设置 JSON 格式错误：${error?.message ?? error}` };
	}
	if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
		return { ok: false, error: "设置 JSON 必须是对象。" };
	}
	const settings = {};
	for (const [rawKey, value] of Object.entries(parsed)) {
		const key = String(rawKey ?? "").trim();
		if (!key || key.length > 128 || ["__proto__", "prototype", "constructor"].includes(key)) continue;
		settings[key] = value;
	}
	return { ok: true, settings };
}

function buildEditedPresetState(baseState, library, selectionText, settingsText) {
	const selectionResult = parsePresetSelectionEditorText(selectionText, library);
	if (!selectionResult.ok) return selectionResult;
	const settingsResult = parsePresetSettingsEditorText(settingsText);
	if (!settingsResult.ok) return settingsResult;
	const nextState = clonePresetState(baseState ?? {});
	nextState.selected = selectionResult.selected;
	nextState.customTags = selectionResult.customTags;
	nextState.settings = settingsResult.settings;
	return { ok: true, state: nextState };
}

function parsePercentText(value) {
	const match = String(value ?? "").trim().match(/(\d+(?:\.\d+)?)\s*%/);
	return match ? Number(match[1] ?? -1) : -1;
}

function formatHistoryAggregateRate(value) {
	return Number.isFinite(Number(value)) && Number(value) >= 0 ? `${Math.round(Number(value))}%` : "待定";
}

function inferHistoryAggregatePresetTone(preset) {
	const meta = preset?.meta ?? {};
	const explicitTone = String(meta.latestRiskTone ?? "").trim();
	if (["success", "warn", "danger", "info"].includes(explicitTone)) return explicitTone;
	const risk = String(meta.latestRisk ?? "").trim();
	if (/正常|稳定/.test(risk)) return "success";
	if (/观察|波动/.test(risk)) return "warn";
	if (/超时|失败|异常|连/.test(risk)) return "danger";
	const rate = parsePercentText(meta.averageSuccessRate);
	if (rate >= 85) return "success";
	if (rate >= 50) return "warn";
	if (rate >= 0) return "danger";
	return "info";
}

function buildUserPresetSummaryText(preset) {
	if (String(preset?.source ?? "") === "history-aggregate") {
		const meta = preset?.meta ?? {};
		const targetName = String(meta.presetName ?? preset?.name ?? "").trim() || String(preset?.name ?? "");
		const average = String(meta.averageSuccessRate ?? "待定").trim() || "待定";
		const risk = String(meta.latestRisk ?? "未知").trim() || "未知";
		const trail = String(meta.latestOutcomeTrail ?? "·").trim() || "·";
		const reportCount = Number(meta.reportCount ?? 0);
		const trend = `${String(meta.latestTrendArrow ?? "").trim()} ${String(meta.latestTrendLabel ?? "").trim()}`.trim();
		const latestMessage = String(meta.latestMessage ?? "").trim();
		return `聚合快照 | 目标 ${targetName} | 报告 ${reportCount || "?"} | 平均成功率 ${average} | ${trend ? `趋势 ${trend} | ` : ""}风险 ${risk} | 结果 ${trail}${latestMessage ? `\n最近：${latestMessage}` : ""}`;
	}
	return String(preset?.meta?.summary ?? summarizeHistoryState(preset?.state));
}

function buildUserPresetSearchText(preset) {
	const sourceLabel = String(USER_PRESET_SOURCE_LABELS[preset?.source] ?? "用户预设");
	const summaryText = buildUserPresetSummaryText(preset);
	const meta = preset?.meta ?? {};
	return [
		preset?.name,
		sourceLabel,
		summaryText,
		meta.presetName,
		meta.reportCount,
		meta.averageSuccessRate,
		meta.latestTrendArrow,
		meta.latestTrendLabel,
		meta.latestRisk,
		meta.latestOutcomeTrail,
		meta.latestMessage,
	]
		.filter(Boolean)
		.join(" ")
		.toLowerCase();
}

function buildUserPresetMetaBadges(preset) {
	const badges = [];
	if (String(preset?.source ?? "") === "history-aggregate") {
		const meta = preset?.meta ?? {};
		const tone = inferHistoryAggregatePresetTone(preset);
		if (meta.reportCount) badges.push({ text: `报告 ${meta.reportCount}`, tone: "info" });
		if (meta.averageSuccessRate) badges.push({ text: `均值 ${meta.averageSuccessRate}`, tone });
		if (meta.latestTrendLabel) badges.push({ text: `趋势 ${String(meta.latestTrendArrow ?? "").trim()} ${meta.latestTrendLabel}`.trim(), tone: "info" });
		if (meta.latestRisk) badges.push({ text: `风险 ${meta.latestRisk}`, tone });
		if (meta.latestOutcomeTrail) badges.push({ text: `结果 ${meta.latestOutcomeTrail}`, tone: "info" });
	}
	return badges;
}

function buildHistoryAggregatePresetText(preset) {
	const payload = buildHistoryAggregatePresetExportPayload(preset);
	const targetName = String(payload?.presetName ?? preset?.name ?? "").trim() || String(preset?.name ?? "");
	const reportCount = Number(payload?.count ?? 0);
	const average = String(payload?.averageSuccessRate ?? "待定").trim() || "待定";
	const trend = `${String(payload?.latestAggregate?.trend?.arrow ?? "").trim()} ${String(payload?.latestAggregate?.trend?.label ?? "").trim()}`.trim() || "待观察";
	const risk = String(payload?.latestAggregate?.risk?.label ?? "未知").trim() || "未知";
	const trail = String(payload?.latestAggregate?.outcomeTrail ?? "·").trim() || "·";
	const latestMessage = String(payload?.latestAggregate?.lastMessage ?? "").trim();
	const lines = [
		`${preset?.name ?? "历史聚合快照"}`,
		`目标预设 ${targetName} | 报告 ${reportCount || "?"} | 平均成功率 ${average}`,
		`趋势 ${trend} | 风险 ${risk} | 结果 ${trail}`,
	];
	if (latestMessage) lines.push(`最近事件：${latestMessage}`);
	return lines.join("\n");
}

function buildHistoryAggregatePresetMarkdown(preset) {
	const payload = buildHistoryAggregatePresetExportPayload(preset);
	const targetName = String(payload?.presetName ?? preset?.name ?? "").trim() || String(preset?.name ?? "");
	const reportCount = Number(payload?.count ?? 0);
	const average = String(payload?.averageSuccessRate ?? "待定").trim() || "待定";
	const trend = `${String(payload?.latestAggregate?.trend?.arrow ?? "").trim()} ${String(payload?.latestAggregate?.trend?.label ?? "").trim()}`.trim() || "待观察";
	const risk = String(payload?.latestAggregate?.risk?.label ?? "未知").trim() || "未知";
	const trail = String(payload?.latestAggregate?.outcomeTrail ?? "·").trim() || "·";
	const latestMessage = String(payload?.latestAggregate?.lastMessage ?? "").trim();
	const lines = [
		"# 历史聚合快照",
		"",
		`- 快照名：${preset?.name ?? "未命名快照"}`,
		`- 目标预设：${targetName}`,
		`- 报告数：${reportCount || "?"}`,
		`- 平均成功率：${average}`,
		`- 趋势：${trend}`,
		`- 风险：${risk}`,
		`- 最近结果：${trail}`,
	];
	if (latestMessage) {
		lines.push("", `最近事件：${latestMessage}`);
	}
	return lines.join("\n");
}

function buildHistoryAggregatePresetCsv(preset) {
	const payload = buildHistoryAggregatePresetExportPayload(preset);
	if (!payload?.presetName) return "";
	const escapeCsv = (value) => `"${String(value ?? "").replace(/"/g, '""')}"`;
	const rows = [["预设", "报告数", "平均成功率", "趋势", "风险", "最近结果", "最近事件"]];
	rows.push([
		payload.presetName,
		payload.count ?? 0,
		payload.averageSuccessRate ?? "待定",
		`${payload?.latestAggregate?.trend?.arrow ?? "→"} ${payload?.latestAggregate?.trend?.label ?? "待观察"}`,
		payload?.latestAggregate?.risk?.label ?? "未知",
		payload?.latestAggregate?.outcomeTrail ?? "·",
		payload?.latestAggregate?.lastMessage ?? "",
	]);
	for (const report of payload.reportPayloads ?? []) {
		const aggregate = report?.aggregate ?? {};
		rows.push([
			aggregate?.presetName ?? payload.presetName,
			"单条",
			aggregate?.successRate ?? "待定",
			`${aggregate?.trend?.arrow ?? "→"} ${aggregate?.trend?.label ?? "待观察"}`,
			aggregate?.risk?.label ?? "未知",
			aggregate?.outcomeTrail ?? "·",
			aggregate?.lastMessage ?? "",
		]);
	}
	return rows.map((row) => row.map(escapeCsv).join(",")).join("\n");
}

function cloneJsonSafe(value, fallback = {}) {
	try {
		return JSON.parse(JSON.stringify(value ?? fallback));
	} catch {
		return fallback;
	}
}

function exportTextFile(content, filename, mimeType = "text/plain;charset=utf-8") {
	if (!content) return false;
	const blob = new Blob([content], { type: mimeType });
	const url = URL.createObjectURL(blob);
	const a = document.createElement("a");
	a.href = url;
	a.download = filename;
	document.body.appendChild(a);
	a.click();
	document.body.removeChild(a);
	URL.revokeObjectURL(url);
	return true;
}

function toggleUserPresetFavorite(id) {
	const presetId = String(id ?? "").trim();
	if (!presetId) return false;
	const presets = getUserPresets();
	let changed = false;
	const nextPresets = presets.map((item) => {
		if (String(item.id ?? "") !== presetId) return item;
		changed = true;
		return { ...item, favorite: !item.favorite, updatedAt: Date.now() };
	});
	if (!changed) return false;
	return setUserPresets(nextPresets);
}

function setUserPresetFavorite(id, favorite) {
	const presetId = String(id ?? "").trim();
	if (!presetId) return false;
	const targetFavorite = !!favorite;
	const presets = getUserPresets();
	let changed = false;
	const nextPresets = presets.map((item) => {
		if (String(item.id ?? "") !== presetId) return item;
		if (!!item.favorite === targetFavorite) return item;
		changed = true;
		return { ...item, favorite: targetFavorite, updatedAt: Date.now() };
	});
	if (!changed) return false;
	return setUserPresets(nextPresets);
}

function deleteUserPresets(ids) {
	const idSet = new Set((ids ?? []).map((id) => String(id ?? "").trim()).filter(Boolean));
	if (!idSet.size) return 0;
	const presets = getUserPresets();
	const nextPresets = presets.filter((item) => !idSet.has(String(item.id ?? "")));
	const deletedCount = presets.length - nextPresets.length;
	if (deletedCount <= 0) return 0;
	return setUserPresets(nextPresets) ? deletedCount : 0;
}

function normalizeUserPresetItems(items) {
	const seen = new Set();
	const result = [];
	for (const item of items ?? []) {
		const normalized = normalizeUserPresetItem(item);
		if (!normalized) continue;
		const key = String(normalized.name ?? "").trim().toLowerCase();
		if (!key || seen.has(key)) continue;
		seen.add(key);
		result.push(normalized);
	}
	return result;
}

function exportUserPresets(items = null) {
	const presets = normalizeUserPresetItems(items ?? getUserPresets());
	if (!presets.length) return false;
	const payload = {
		version: 1,
		exportedAt: Date.now(),
		source: "qwen-te-user-presets",
		presets,
	};
	const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
	const url = URL.createObjectURL(blob);
	const a = document.createElement("a");
	a.href = url;
	a.download = `qwen-te-user-presets-${buildCompactTimestamp()}.json`;
	document.body.appendChild(a);
	a.click();
	document.body.removeChild(a);
	URL.revokeObjectURL(url);
	return true;
}

async function importUserPresetFile(file) {
	if (Number(file?.size ?? 0) > USER_PRESET_IMPORT_MAX_BYTES) throw new Error("预设文件超过 2 MiB 导入上限。");
	const text = await file.text();
	if (utf8ByteLength(text) > USER_PRESET_IMPORT_MAX_BYTES) throw new Error("预设文件超过 2 MiB 导入上限。");
	const payload = JSON.parse(text);
	const normalizedImported = normalizeUserPresetItems(payload?.presets);
	const imported = boundUserPresets(normalizedImported);
	let skippedCount = Math.max(0, normalizedImported.length - imported.length);
	if (!imported.length) {
		return {
			ok: false,
			message: normalizedImported.length ? "预设内容超过单项或总存储上限，未导入任何预设。" : "文件里没有可导入的预设。",
			imported: 0,
			merged: 0,
		};
	}
	let working = getUserPresets();
	let importedCount = 0;
	let mergedCount = 0;
	for (const item of imported) {
		const key = String(item.name ?? "").trim().toLowerCase();
		const existingIndex = working.findIndex((entry) => String(entry.name ?? "").trim().toLowerCase() === key);
		const candidate = existingIndex >= 0
			? working.map((entry, index) => index === existingIndex ? item : entry)
			: [item, ...working];
		candidate.sort((left, right) => Number(!!right.favorite) - Number(!!left.favorite) || Number(right.updatedAt ?? 0) - Number(left.updatedAt ?? 0));
		const boundedCandidate = boundUserPresets(candidate);
		const retainedKeys = new Set(boundedCandidate.map((entry) => String(entry.name ?? "").trim().toLowerCase()));
		const preservesExisting = working.every((entry) => {
			const existingKey = String(entry.name ?? "").trim().toLowerCase();
			return existingKey === key || retainedKeys.has(existingKey);
		});
		if (!retainedKeys.has(key) || !preservesExisting) {
			skippedCount += 1;
			continue;
		}
		working = boundedCandidate;
		importedCount += 1;
		if (existingIndex >= 0) mergedCount += 1;
	}
	if (!importedCount) {
		return { ok: false, message: "预设库已达数量或容量上限，未导入新预设；现有预设保持不变。", imported: 0, merged: 0 };
	}
	if (!setUserPresets(working)) {
		return { ok: false, message: "预设写入失败：浏览器本地存储空间不足。", imported: 0, merged: 0 };
	}
	return {
		ok: true,
		message: `已导入 ${importedCount} 个预设，其中覆盖 ${mergedCount} 个同名预设${skippedCount ? `，另有 ${skippedCount} 个因容量限制跳过` : ""}。`,
		imported: importedCount,
		merged: mergedCount,
	};
}

function deleteUserPreset(id) {
	const presetId = String(id ?? "").trim();
	if (!presetId) return false;
	const presets = getUserPresets();
	const nextPresets = presets.filter((item) => String(item.id ?? "") !== presetId);
	if (nextPresets.length === presets.length) return false;
	return setUserPresets(nextPresets);
}

function getWidget(node, name) {
	return node.widgets?.find((widget) => widget.name === name) ?? null;
}

function getWidgetOptions(node, name) {
	const widget = getWidget(node, name);
	if (Array.isArray(widget?.options?.values)) return widget.options.values.map((value) => String(value));
	if (Array.isArray(widget?.options)) return widget.options.map((value) => String(value));
	return [];
}

function getSerializableWidgets(node) {
	return (node.widgets ?? []).filter((widget) => widget?.name !== "qwen_te_tag_panel" && widget?.serialize !== false);
}

function removeNodeWidgetSafely(node, widget) {
	if (!Array.isArray(node?.widgets) || !node.widgets.includes(widget)) return false;
	if (widget && typeof node.removeWidget === "function") {
		try {
			node.removeWidget(widget);
			if (!node.widgets.includes(widget)) return true;
		} catch (_error) {}
	}
	const index = node.widgets.indexOf(widget);
	if (index < 0) return false;
	node.widgets.splice(index, 1);
	try { widget?.onRemove?.(); } catch (_error) {}
	return true;
}

function disableFixUiRuntime() {
	if (window.__qwenFixTimer) {
		clearInterval(window.__qwenFixTimer);
		window.__qwenFixTimer = null;
	}
	window.__QWEN_TE_DISABLE_FIX_UI__ = true;
}

function cleanupFixUiArtifacts(node, options = {}) {
	disableFixUiRuntime();
	if (!node) return;
	const preserveMiniToolbar = options.preserveMiniToolbar === true;
	const hadLegacyTitleArtifacts = !!(
		node.__qwenFixLoaded ||
		node.__qwenFixToolbarButtons ||
		(node.widgets ?? []).some((widget) => (
			widget?.name === "qwen_fix_toolbar" ||
			(widget?.__qwenStageFallbackWidget && !STAGE_TOP_STATUS_WIDGET_NAMES.has(String(widget.name ?? "")))
		))
	);
	if (!preserveMiniToolbar) {
		try { window.__QWEN_TE_STAGE_CLEANUP_MINI_TOOLBAR__?.(node, { scheduleLayout: false }); } catch (_error) {}
	}
	let changed = false;
	if (Array.isArray(node.widgets)) {
		const keptTopStatusNames = new Set();
		const widgetsToRemove = [];
		for (const widget of [...node.widgets]) {
			let remove = false;
			if (!widget) remove = true;
			if (widget?.__qwenStageFallbackWidget) {
				const name = String(widget.name ?? "");
				if (!STAGE_TOP_STATUS_WIDGET_NAMES.has(name) || keptTopStatusNames.has(name)) remove = true;
				else keptTopStatusNames.add(name);
			}
			if (widget?.name === "qwen_fix_toolbar") remove = true;
			if (!preserveMiniToolbar && (widget?.name === "qwen_te_mini_toolbar_dom" || widget?.__qwenStageMiniWidget)) remove = true;
			if (!node[PANEL_KEY] && widget?.name === "qwen_te_tag_panel") remove = true;
			if (widget?.serialize === false && FIX_UI_WIDGET_NAMES.has(widget?.name) && !widget?.__qwenStageFallbackWidget) remove = true;
			if (remove) widgetsToRemove.push(widget);
		}
		for (const widget of widgetsToRemove) changed = removeNodeWidgetSafely(node, widget) || changed;
	}
	if (hadLegacyTitleArtifacts && typeof node.title === "string") {
		const nextTitle = node.title.replace(/\s+\[(?:UI|FIX OK|FIX UI)\]$/u, "");
		changed = changed || nextTitle !== node.title;
		node.title = nextTitle;
	}
	delete node.__qwenFixLoaded;
	delete node.__qwenFixToolbarButtons;
	delete node.__qwenFixStatusWidget;
	delete node.__qwenFixSummaryWidget;
	delete node.__qwenFixSummaryElement;
	delete node.__qwenFixStatusElement;
	delete node.__qwenFixExecutedHooked;
	if (changed) scheduleNodeLayoutUpdate(node);
}

async function getFreshLibraryForUi(node, fallbackLibrary, options = {}) {
	try {
		return await refreshLibraryOnNode(node, options);
	} catch (_error) {
		return node?.[PANEL_KEY]?.library ?? fallbackLibrary;
	}
}

function wrapPanelAction(node, statusEl, label, action, buttonEl = null) {
	return async () => {
		const mutationRevision = beginNodeStateMutation(node);
		const previousStatus = node?.[PANEL_KEY]?.lastPanelMessage ?? statusEl?.textContent ?? "";
		const processingText = `${label}处理中...`;
		const previousDisabled = !!buttonEl?.disabled;
		try {
			setNodeStatusText(node, processingText);
			if (buttonEl) {
				buttonEl.disabled = true;
				buttonEl.classList.add("is-busy");
			}
			await action(mutationRevision);
		} catch (error) {
			const message = `${label}失败：${error?.message ?? error}`;
			setNodeStatusText(node, message);
			console.error(`[QwenTE UI] ${label} failed`, error);
			scheduleNodeLayoutUpdate(node);
		} finally {
			if ((node?.[PANEL_KEY]?.lastPanelMessage ?? statusEl?.textContent) === processingText) {
				setNodeStatusText(node, previousStatus || `${label}完成。`);
			}
			if (buttonEl) {
				buttonEl.disabled = previousDisabled;
				buttonEl.classList.remove("is-busy");
			}
			refreshNodeActionButtons(node);
		}
	};
}

function renderSummaryPills(container, summaryText) {
	if (!(container instanceof HTMLElement)) return;
	container.replaceChildren();
	const lines = String(summaryText ?? "").split("\n").map((line) => line.trim()).filter(Boolean);
	if (!lines.length) return;
	const primary = document.createElement("div");
	primary.className = "qwen-te-panel__summary-line";
	primary.textContent = lines[0].replace(/\s*\|\s*/gu, " / ");
	primary.title = lines[0];
	container.appendChild(primary);
	const secondaryText = lines.slice(1).join(" / ");
	if (secondaryText) {
		const secondary = document.createElement("div");
		secondary.className = "qwen-te-panel__summary-sub";
		secondary.textContent = secondaryText;
		secondary.title = secondaryText;
		container.appendChild(secondary);
	}
}

function captureNamedWidgetState(node) {
	const state = {};
	for (const widget of getSerializableWidgets(node)) state[widget.name] = widget.value;
	return state;
}

function persistNamedWidgetState(node) {
	ensureNodeProperties(node)[NAMED_STATE_KEY] = captureNamedWidgetState(node);
}

function applyNamedWidgetState(node, state) {
	if (!state || typeof state !== "object") return false;
	let applied = false;
	for (const widget of getSerializableWidgets(node)) {
		if (!(widget.name in state)) continue;
		if (!Object.is(widget.value, state[widget.name])) setWidgetValue(node, widget.name, state[widget.name]);
		applied = true;
	}
	return applied;
}

function getDefaultWidgetValue(widget) {
	if (!widget) return undefined;
	if ([
		"自定义补充标签",
		"额外要求",
		"系统提示词覆盖",
		"锁定标签白名单",
		"随机排除标签",
		RANDOM_DEDUPE_CACHE_WIDGET_NAME,
		PROMPT_DEDUPE_CACHE_WIDGET_NAME,
		RUNTIME_RANDOM_PROTECTED_TAGS_WIDGET_NAME,
		RUNTIME_RANDOM_PREVIEW_TOKEN_WIDGET_NAME,
	].includes(widget.name)) return "";
	if (/标签\d+$/u.test(String(widget.name ?? ""))) return "无";
	return widget.value;
}

function normalizeLegacyWidgetValues(node, widgetValues) {
	if (!Array.isArray(widgetValues) || !node.widgets?.length) return widgetValues;
	const widgets = getSerializableWidgets(node);
	const currentLength = widgets.length;
	let values = [...widgetValues];
	if (values.length === currentLength) return values;
	if (values.length > currentLength) values = values.slice(values.length - currentLength);
	if (values.length === currentLength) return values;
	const embeddedModelIndex = widgets.findIndex((widget) => widget.name === STAGE_EMBEDDED_MODEL_WIDGET_NAMES[0]);
	const legacyMissingEmbeddedModelWidgets =
		embeddedModelIndex >= 0 &&
		values.length <= currentLength - STAGE_EMBEDDED_MODEL_WIDGET_COUNT &&
		STAGE_EMBEDDED_MODEL_WIDGET_NAMES.every((name, index) => widgets[embeddedModelIndex + index]?.name === name);
	if (legacyMissingEmbeddedModelWidgets) {
		const defaults = STAGE_EMBEDDED_MODEL_WIDGET_NAMES.map((name) => getDefaultWidgetValue(widgets.find((widget) => widget.name === name)));
		values = [...values.slice(0, embeddedModelIndex), ...defaults, ...values.slice(embeddedModelIndex)];
		if (values.length === currentLength) return values;
	}
	const expandedTagWidgets = widgets.filter((widget) => {
		const match = String(widget?.name ?? "").match(/标签(\d+)$/u);
		return match && Number(match[1]) > 10;
	});
	if (expandedTagWidgets.length && values.length === currentLength - expandedTagWidgets.length) {
		const expandedSet = new Set(expandedTagWidgets);
		const migrated = [];
		let legacyIndex = 0;
		for (const widget of widgets) {
			if (expandedSet.has(widget)) migrated.push(getDefaultWidgetValue(widget));
			else migrated.push(values[legacyIndex++]);
		}
		return migrated;
	}
	for (const batch of LEGACY_WIDGET_BATCHES) {
		const unresolved = currentLength - values.length;
		if (unresolved <= 0) break;
		if (unresolved < batch.length) continue;
		const batchIndex = widgets.findIndex((widget) => widget.name === batch[0]);
		if (batchIndex < 0) continue;
		const defaults = batch.map((name) => getDefaultWidgetValue(widgets.find((widget) => widget.name === name)));
		values = [...values.slice(0, batchIndex), ...defaults, ...values.slice(batchIndex)];
		if (values.length >= currentLength) break;
	}
	while (values.length < currentLength) values.push(getDefaultWidgetValue(widgets[values.length]));
	return values.slice(0, currentLength);
}

function serializePersistedWidgetValue(widget) {
	return cloneJsonSafe(widget?.value, null);
}

function normalizeConfiguredWidgetValues(node, config) {
	if (!Array.isArray(config?.widgets_values)) return config?.widgets_values;
	const positionalValues = normalizeLegacyWidgetValues(node, config.widgets_values);
	const namedState = config?.properties?.[NAMED_STATE_KEY];
	if (!namedState || typeof namedState !== "object") return positionalValues;
	return getSerializableWidgets(node).map((widget, index) => (
		Object.prototype.hasOwnProperty.call(namedState, widget.name)
			? cloneJsonSafe(namedState[widget.name], null)
			: positionalValues[index]
	));
}

function normalizeSerializedNodePayload(node, serialized) {
	serialized.properties = serialized.properties ?? {};
	serialized.properties[NODE_CACHE_NAMESPACE_KEY] = ensureNodeCacheNamespace(node);
	serialized.properties[NAMED_STATE_KEY] = cloneJsonSafe(captureNamedWidgetState(node), {});
	serialized.widgets_values = getSerializableWidgets(node).map((widget) => serializePersistedWidgetValue(widget, node));
	return serialized;
}

function parseCustomTags(text) {
	const normalized = String(text ?? "")
		.normalize("NFKC")
		.replace(/\u3000/gu, " ");
	const seen = new Set();
	const results = [];
	for (const raw of normalized.split(/[,\n\r\t;；，、]+/u)) {
		const tag = raw.replace(/\s+/gu, " ").trim();
		if (!tag || seen.has(tag)) continue;
		seen.add(tag);
		results.push(tag);
	}
	return results;
}

function mergeTagSettingText(baseText, extraTags = []) {
	return parseCustomTags([String(baseText ?? ""), ...(extraTags ?? [])].join(", ")).join(", ");
}

function mergeRequirementText(baseText, extraText) {
	const base = String(baseText ?? "").trim();
	const extra = String(extraText ?? "").trim();
	if (!base) return extra;
	if (!extra) return base;
	if (base === extra) return base;
	return `${base}\n${extra}`;
}

function flattenUniqueTags(groupData) {
	const seen = new Set();
	const flat = [];
	for (const tags of Object.values(groupData ?? {})) {
		for (const tag of tags ?? []) {
			if (seen.has(tag)) continue;
			seen.add(tag);
			flat.push(tag);
		}
	}
	return flat;
}

function flattenSectionTags(groupData, sectionNames = []) {
	const sections = Array.isArray(sectionNames) && sectionNames.length ? sectionNames : Object.keys(groupData ?? {});
	const seen = new Set();
	const flat = [];
	for (const sectionName of sections) {
		for (const tag of groupData?.[sectionName] ?? []) {
			const normalizedTag = String(tag ?? "").trim();
			if (!normalizedTag || seen.has(normalizedTag)) continue;
			seen.add(normalizedTag);
			flat.push(normalizedTag);
		}
	}
	return flat;
}

function cloneSelection(selection) {
	return Object.fromEntries(Object.entries(selection).map(([key, value]) => [key, [...value]]));
}

const TAG_GROUP_SLOT_HARD_LIMIT = 32;
const TAG_SELECTION_PILL_PREVIEW_LIMIT = 12;
const RUNTIME_RANDOM_AUTO_SLOT_BUDGET = 10;

function normalizeTagGroupSlotLimit(value, fallback = 0) {
	let numeric = Number(value);
	if (!Number.isFinite(numeric) || numeric <= 0) numeric = Number(fallback);
	if (!Number.isFinite(numeric) || numeric <= 0) return 0;
	return Math.min(TAG_GROUP_SLOT_HARD_LIMIT, Math.max(1, Math.trunc(numeric)));
}

function getTagGroupSlotLimit(library, groupName) {
	const group = (library?.slot_config ?? []).find((item) => String(item?.name ?? "") === String(groupName ?? ""));
	return normalizeTagGroupSlotLimit(group?.slots, 0);
}

function toggleBoundedTagSelection(selection, groupName, rawTag, limit) {
	if (!selection || typeof selection !== "object") return { changed: false, reason: "invalid", count: 0, limit: 0 };
	const tag = String(rawTag ?? "").trim();
	const boundedLimit = normalizeTagGroupSlotLimit(limit, 0);
	const current = Array.isArray(selection[groupName]) ? selection[groupName] : (selection[groupName] = []);
	const existingIndex = current.indexOf(tag);
	if (existingIndex >= 0) {
		current.splice(existingIndex, 1);
		return { changed: true, reason: "removed", count: current.length, limit: boundedLimit };
	}
	if (!tag) return { changed: false, reason: "empty", count: current.length, limit: boundedLimit };
	if (current.length >= boundedLimit) return { changed: false, reason: "full", count: current.length, limit: boundedLimit };
	current.push(tag);
	return { changed: true, reason: "added", count: current.length, limit: boundedLimit };
}

function getRuntimeRandomAdditionCap(currentCount, slotCount, intensity) {
	const remaining = Math.max(0, Math.min(RUNTIME_RANDOM_AUTO_SLOT_BUDGET, normalizeTagGroupSlotLimit(slotCount, 0)) - Math.max(0, Math.trunc(Number(currentCount) || 0)));
	if (String(intensity ?? "").trim() === "弱") return Math.min(1, remaining);
	if (String(intensity ?? "").trim() === "中") return Math.min(2, remaining);
	return remaining;
}

function collectNsfwWorkspaceTerms(workspace) {
	const nextWorkspace = cloneNsfwWorkspaceState(workspace ?? null);
	const terms = [];
	const push = (value, normalizeSelector = false) => {
		for (const text of parseCustomTags(value)) {
			const term = normalizeSelector ? normalizeNsfwSelectorTerm(text) : text;
			if (term && term !== "——" && !terms.includes(term)) terms.push(term);
		}
	};
	for (const tag of nextWorkspace.trigger_words ?? []) push(tag);
	for (const tag of nextWorkspace.workspace_custom_tags ?? []) push(tag);
	for (const key of ["selector_character", "selector_outfit", "selector_action", "selector_scene", "selector_expression", "selector_prop", "scene", "action", "outfit", "mood", "anatomy_terms", "explicit_terms", "adult_action_style", "camera_movement", "camera_angle", "light_source", "light_type", "lens_type", "focal_length", "color_tone", "visual_style", "effect", "filter", "custom_prefix", "custom_suffix"]) {
		push(nextWorkspace[key], key.startsWith("selector_"));
	}
	return terms;
}

function getNsfwSelectorAliasTerm(term) {
	const text = String(term ?? "").trim();
	if (!text) return "";
	const alias = text.replace(/\s+[A-Za-z0-9][A-Za-z0-9_\- ]*$/u, "").replace(/[ /()]+$/u, "").trim();
	return alias && alias !== text ? alias : "";
}

function normalizeNsfwSelectorTerm(term) {
	const text = String(term ?? "").trim();
	return getNsfwSelectorAliasTerm(text) || text;
}

function collectNsfwWorkspaceAppliedTerms(workspace) {
	if (!workspace || typeof workspace !== "object") return [];
	const applied = workspace.applied_custom_tags ?? workspace.appliedCustomTags ?? [];
	return Array.isArray(applied) ? parseCustomTags(applied.join(", ")) : parseCustomTags(applied);
}

function collectNsfwWorkspaceAppliedSelection(workspace) {
	if (!workspace || typeof workspace !== "object") return {};
	const rawSelection = workspace.applied_selected_tags ?? workspace.appliedSelectedTags ?? {};
	if (!rawSelection || typeof rawSelection !== "object" || Array.isArray(rawSelection)) return {};
	const selected = {};
	for (const [groupName, tags] of Object.entries(rawSelection)) {
		const parsed = Array.isArray(tags) ? parseCustomTags(tags.join(", ")) : parseCustomTags(tags);
		if (parsed.length) selected[groupName] = parsed;
	}
	return selected;
}

function collectNsfwRuntimeProtectedTags(state) {
	const workspace = state?.nsfwWorkspace ?? state?.nsfw_workspace ?? null;
	if (!workspace?.enabled) return [];
	const appliedSelection = collectNsfwWorkspaceAppliedSelection(workspace);
	const appliedTerms = [
		...Object.values(appliedSelection).flatMap((tags) => tags ?? []),
		...collectNsfwWorkspaceAppliedTerms(workspace),
	];
	const workspaceTerms = appliedTerms.length ? appliedTerms : collectNsfwWorkspaceTerms(workspace);
	return uniqueTextList(workspaceTerms);
}

function collectNsfwWorkspaceManualCustomTags(workspace) {
	if (!workspace || typeof workspace !== "object") return [];
	const manual = workspace.manual_custom_tags ?? workspace.manualCustomTags ?? workspace.user_custom_tags ?? workspace.userCustomTags ?? [];
	return Array.isArray(manual) ? parseCustomTags(manual.join(", ")) : parseCustomTags(manual);
}

function rewriteNsfwWorkspaceCustomTags(customTags, previousWorkspace, nextAppliedTerms) {
	const sourceTags = [...(Array.isArray(customTags) ? customTags : [])];
	const manualTags = collectNsfwWorkspaceManualCustomTags(previousWorkspace);
	const nextTerms = parseCustomTags(nextAppliedTerms ?? []);
	const removalTerms = collectNsfwWorkspaceAppliedTerms(previousWorkspace);
	const legacyRemovalTerms = removalTerms.length ? removalTerms : collectNsfwWorkspaceTerms(previousWorkspace);
	const nextCustomTags = sourceTags.filter((tag) => !legacyRemovalTerms.includes(tag) || manualTags.includes(tag));
	for (const tag of nextTerms) addUniqueTag(nextCustomTags, tag);
	return {
		customTags: nextCustomTags,
		manualCustomTags: nextCustomTags.filter((tag) => !nextTerms.includes(tag) && (!legacyRemovalTerms.includes(tag) || manualTags.includes(tag))),
		appliedCustomTags: nextTerms,
	};
}

function reconcileNsfwWorkspaceSelectedTags(previousSelected, previousWorkspace, mappedSelected, nextAppliedTerms) {
	const previousApplied = collectNsfwWorkspaceAppliedSelection(previousWorkspace);
	const generatedSet = new Set(parseCustomTags(nextAppliedTerms ?? []));
	const baseSelected = cloneSelection(previousSelected ?? {});
	for (const [groupName, tags] of Object.entries(previousApplied)) {
		const removalSet = new Set(tags ?? []);
		baseSelected[groupName] = (baseSelected[groupName] ?? []).filter((tag) => !removalSet.has(tag));
	}
	const selected = cloneSelection(mappedSelected ?? {});
	for (const [groupName, tags] of Object.entries(previousApplied)) {
		const previousAppliedSet = new Set(tags ?? []);
		selected[groupName] = (selected[groupName] ?? []).filter((tag) => !previousAppliedSet.has(tag) || generatedSet.has(tag));
	}
	const appliedSelectedTags = {};
	for (const [groupName, tags] of Object.entries(selected)) {
		const manualTags = new Set(baseSelected[groupName] ?? []);
		const appliedTags = (tags ?? []).filter((tag) => tag && generatedSet.has(tag) && !manualTags.has(tag));
		if (appliedTags.length) appliedSelectedTags[groupName] = [...new Set(appliedTags)];
	}
	return { selected, appliedSelectedTags };
}

function removeNsfwWorkspaceSelectedTags(state, workspace) {
	const selected = collectNsfwWorkspaceAppliedSelection(workspace);
	for (const [groupName, tags] of Object.entries(selected)) {
		const removalSet = new Set(tags);
		state.selected[groupName] = (state.selected?.[groupName] ?? []).filter((tag) => !removalSet.has(tag));
	}
}

function cloneSettingRestoreSnapshot(snapshot, settingNames = []) {
	const source = snapshot && typeof snapshot === "object" && !Array.isArray(snapshot) ? snapshot : {};
	const structured = Object.prototype.hasOwnProperty.call(source, "original") || Object.prototype.hasOwnProperty.call(source, "applied");
	const originalSource = structured && source.original && typeof source.original === "object" && !Array.isArray(source.original)
		? source.original
		: structured ? {} : source;
	const appliedSource = structured && source.applied && typeof source.applied === "object" && !Array.isArray(source.applied)
		? source.applied
		: {};
	const allowed = new Set(settingNames ?? []);
	const copyValues = (values) => Object.fromEntries(
		Object.entries(values ?? {}).filter(([name]) => !allowed.size || allowed.has(name)),
	);
	return { original: copyValues(originalSource), applied: copyValues(appliedSource) };
}

function updateSettingRestoreSnapshot(snapshot, beforeSettings, afterSettings, settingNames) {
	const next = cloneSettingRestoreSnapshot(snapshot, settingNames);
	for (const name of settingNames ?? []) {
		const beforeValue = beforeSettings?.[name];
		const afterValue = afterSettings?.[name];
		if (beforeValue === afterValue) continue;
		if (!Object.prototype.hasOwnProperty.call(next.original, name)) next.original[name] = beforeValue;
		next.applied[name] = afterValue;
	}
	return next;
}

function hasSettingRestoreSnapshot(snapshot) {
	return !!snapshot && typeof snapshot === "object" && Object.keys(snapshot.original ?? {}).length > 0;
}

function restoreSettingsFromSnapshot(settings, snapshot, settingNames) {
	const nextSettings = { ...(settings ?? {}) };
	const normalized = cloneSettingRestoreSnapshot(snapshot, settingNames);
	for (const [name, originalValue] of Object.entries(normalized.original)) {
		if (!Object.prototype.hasOwnProperty.call(normalized.applied, name) || nextSettings[name] === normalized.applied[name]) {
			nextSettings[name] = originalValue;
		}
	}
	return nextSettings;
}

function cloneCharacterSheetRestoreState(value = null) {
	const source = value && typeof value === "object" && !Array.isArray(value) ? value : {};
	return {
		settings: cloneSettingRestoreSnapshot(source.settings ?? source.setting_restore ?? source.settingRestore ?? {}, CHARACTER_SHEET_SETTING_NAMES),
		addedTags: uniqueTextList(source.addedTags ?? source.added_tags ?? []),
	};
}

function clonePresetState(state) {
	const nextState = {
		selected: cloneSelection(state.selected ?? {}),
		customTags: [...(state.customTags ?? [])],
		settings: { ...(state.settings ?? {}) },
	};
	if (Object.prototype.hasOwnProperty.call(state ?? {}, "nsfwWorkspace") || Object.prototype.hasOwnProperty.call(state ?? {}, "nsfw_workspace")) {
		nextState.nsfwWorkspace = cloneNsfwWorkspaceState(state.nsfwWorkspace ?? state.nsfw_workspace ?? null);
	}
	if (Object.prototype.hasOwnProperty.call(state ?? {}, "characterSheetRestore")) {
		nextState.characterSheetRestore = cloneCharacterSheetRestoreState(state.characterSheetRestore);
	}
	if (Object.prototype.hasOwnProperty.call(state ?? {}, "smartTextAutoExtra")) {
		nextState.smartTextAutoExtra = String(state.smartTextAutoExtra ?? "").trim();
	}
	return nextState;
}

function createPresetBaseState(node, library, preset) {
	const currentState = collectNodeState(node, library);
	const baseState = clonePresetState(currentState);
	if (preset?.mergeWithCurrent) {
		return baseState;
	}
	baseState.selected = Object.fromEntries((library.slot_config ?? []).map((group) => [group.name, []]));
	baseState.customTags = [];
	return baseState;
}

function cloneSelectionOnlyState(state) {
	return { selected: cloneSelection(state?.selected ?? {}), customTags: [...(state?.customTags ?? [])] };
}

function serializeSelectionOnlyState(state) {
	try { return JSON.stringify(cloneSelectionOnlyState(state)); } catch { return ""; }
}

function resizeNodeToComputedSize(node) {
	try {
		if (typeof node?.computeSize === "function" && typeof node?.setSize === "function") {
			const size = node.computeSize();
			const currentWidth = Number(node?.size?.[0] ?? 0) || 0;
			const nextWidth = Math.max(currentWidth, Number(size?.[0] ?? 0) || 0);
			const nextHeight = Math.max(Number(size?.[1] ?? 0) || 0, 0);
			node.setSize([nextWidth, nextHeight]);
		}
	} catch (error) {
		console.warn("[QwenTE UI] node layout resize failed", error);
	}
	try { app?.graph?.setDirtyCanvas?.(true, true); } catch (_error) {}
	try { node?.graph?.setDirtyCanvas?.(true, true); } catch (_error) {}
}

function getUnscaledElementHeight(element, fallback = 0) {
	if (!(element instanceof HTMLElement)) return fallback;
	const offsetHeight = Number(element.offsetHeight ?? 0) || 0;
	if (offsetHeight > 0) return offsetHeight;
	return Number(element.scrollHeight ?? 0) || Number(element.getBoundingClientRect?.().height ?? 0) || fallback;
}

function scheduleNodeLayoutUpdate(node) {
	if (!node || node[NODE_REMOVED_KEY]) return;
	const raf = typeof requestAnimationFrame === "function" ? requestAnimationFrame : (fn) => setTimeout(fn, 0);
	resizeNodeToComputedSize(node);
	raf(() => { if (!node[NODE_REMOVED_KEY]) raf(() => { if (!node[NODE_REMOVED_KEY]) resizeNodeToComputedSize(node); }); });
	setTimeout(() => { if (!node[NODE_REMOVED_KEY]) resizeNodeToComputedSize(node); }, 80);
}

function getGridColumnCount(element, fallback = 1) {
	if (!(element instanceof HTMLElement)) return fallback;
	const template = window.getComputedStyle(element).gridTemplateColumns || "";
	const normalized = template.trim();
	if (!normalized || normalized === "none") return fallback;
	return Math.max(1, normalized.split(/\s+/).length);
}

function measureActionGroupHeight(group) {
	if (!(group instanceof HTMLElement) || group.offsetParent === null) return 0;
	const buttons = [...group.children].filter((child) => child instanceof HTMLElement && child.offsetParent !== null);
	if (!buttons.length) return 0;
	const style = window.getComputedStyle(group);
	const rowGap = Number.parseFloat(style.rowGap || style.gap || "0") || 0;
	const columns = getGridColumnCount(group, buttons.length);
	const rows = Math.max(1, Math.ceil(buttons.length / columns));
	const firstButton = buttons[0];
	const buttonHeight = Math.ceil(getUnscaledElementHeight(firstButton, Number.parseFloat(window.getComputedStyle(firstButton).minHeight || "32") || 32));
	return rows * buttonHeight + Math.max(0, rows - 1) * rowGap;
}

function measureActionShellHeight(actionShell) {
	if (!(actionShell instanceof HTMLElement) || actionShell.offsetParent === null) return 0;
	const groups = [...actionShell.children].filter((child) => child instanceof HTMLElement && child.offsetParent !== null);
	if (!groups.length) return 0;
	const style = window.getComputedStyle(actionShell);
	const gap = Number.parseFloat(style.rowGap || style.gap || "0") || 0;
	let total = 0;
	for (const group of groups) total += measureActionGroupHeight(group);
	if (groups.length > 1) total += gap * (groups.length - 1);
	return total;
}

function measurePanelContentHeight(panel, minHeight = 160) {
	if (!(panel instanceof HTMLElement)) return minHeight;
	const computed = window.getComputedStyle(panel);
	const gap = Number.parseFloat(computed.rowGap || computed.gap || "0") || 0;
	const paddingTop = Number.parseFloat(computed.paddingTop || "0") || 0;
	const paddingBottom = Number.parseFloat(computed.paddingBottom || "0") || 0;
	let total = paddingTop + paddingBottom;
	const children = [...panel.children].filter((child) => child instanceof HTMLElement && child.offsetParent !== null);
	const directActionShell = children.find((child) => child.classList?.contains("qwen-te-panel__actions-shell")) ?? null;
	for (const child of children) {
		if (child.classList?.contains("qwen-te-panel__advanced")) {
			const maxHeight = Number.parseFloat(window.getComputedStyle(child).maxHeight || "0") || 0;
			const measuredHeight = getUnscaledElementHeight(child);
			total += maxHeight > 0 ? Math.min(measuredHeight, maxHeight) : measuredHeight;
			continue;
		}
		if (child.classList?.contains("qwen-te-panel__slots")) {
			const maxHeight = Number.parseFloat(window.getComputedStyle(child).maxHeight || "0") || 0;
			const measuredHeight = getUnscaledElementHeight(child);
			total += maxHeight > 0 ? Math.min(measuredHeight, maxHeight) : measuredHeight;
			continue;
		}
		total += getUnscaledElementHeight(child);
	}
	if (children.length > 1) total += gap * (children.length - 1);
	if (directActionShell) {
		total -= getUnscaledElementHeight(directActionShell);
		total += measureActionShellHeight(directActionShell);
	}
	return Math.max(minHeight, Math.ceil(total + 10));
}

function stopCanvasTextInputEvent(event) {
	event.stopPropagation();
}

function stopCanvasWheelEvent(event) {
	event.stopPropagation();
}

function attachPanelResizeObserver(node, panel) {
	if (!(panel instanceof HTMLElement) || typeof ResizeObserver === "undefined") return null;
	if (node[PANEL_KEY]?.resizeObserver) {
		try { node[PANEL_KEY].resizeObserver.disconnect(); } catch (_error) {}
	}
	const observer = new ResizeObserver(() => {
		scheduleNodeLayoutUpdate(node);
	});
	observer.observe(panel);
	return observer;
}

function normalizeStageWidgetValue(name, value) {
	if (name === "模型来源") return normalizeModelSourceValue(value);
	if (name === "标签反推模式") {
		const normalized = LEGACY_REVERSE_MODE_ALIASES[String(value ?? "").trim()];
		if (normalized) return normalized;
	}
	return value;
}

function isLikelyStaleApiModelValue(value) {
	const text = String(value ?? "").trim();
	return text ? MODEL_API_STALE_MODEL_VALUES.has(text) : false;
}

function setWidgetValue(node, name, value) {
	const widget = getWidget(node, name);
	if (!widget) return;
	const writeDepth = Math.max(0, Number(node?.[NODE_PROGRAMMATIC_WIDGET_WRITE_DEPTH_KEY] ?? 0) || 0);
	if (node) node[NODE_PROGRAMMATIC_WIDGET_WRITE_DEPTH_KEY] = writeDepth + 1;
	try {
		const nextValue = normalizeStageWidgetValue(name, value);
		widget.value = nextValue;
		if (widget.inputEl) widget.inputEl.value = nextValue;
		if (widget.element && "value" in widget.element) widget.element.value = nextValue;
		try { widget.callback?.(nextValue, app, node); } catch (_error) {}
	} finally {
		if (node) {
			if (writeDepth > 0) node[NODE_PROGRAMMATIC_WIDGET_WRITE_DEPTH_KEY] = writeDepth;
			else delete node[NODE_PROGRAMMATIC_WIDGET_WRITE_DEPTH_KEY];
		}
	}
	persistNamedWidgetState(node);
}

function isHiddenWidgetType(type) {
	return /^easyHidden/u.test(String(type ?? ""));
}

function getFallbackWidgetType(widget) {
	if (Array.isArray(widget?.options?.values) || Array.isArray(widget?.options)) return "combo";
	if (typeof widget?.value === "boolean") return "toggle";
	if (typeof widget?.value === "number") return "number";
	return "text";
}

function isHiddenWidgetSize(computeSize) {
	if (typeof computeSize !== "function") return false;
	try {
		const size = computeSize();
		return Number(size?.[0] ?? 0) === 0 && Number(size?.[1] ?? 0) <= 0;
	} catch (_error) {
		return false;
	}
}

function toggleWidget(node, widget, show = false, suffix = "") {
	if (!widget) return;
	if (!widget[HIDDEN_KEY]) widget[HIDDEN_KEY] = {};
	if (!isHiddenWidgetType(widget.type)) widget[HIDDEN_KEY].type = widget.type;
	if (typeof widget.computeSize === "function" && !isHiddenWidgetSize(widget.computeSize)) {
		widget[HIDDEN_KEY].computeSize = widget.computeSize;
	}
	const visibleType = !isHiddenWidgetType(widget[HIDDEN_KEY].type) ? widget[HIDDEN_KEY].type : getFallbackWidgetType(widget);
	widget.type = show ? visibleType : `easyHidden${suffix}`;
	if (show) {
		if (typeof widget[HIDDEN_KEY].computeSize === "function") widget.computeSize = widget[HIDDEN_KEY].computeSize;
		else delete widget.computeSize;
	} else {
		widget.computeSize = () => [0, -4];
	}
	widget.hidden = !show;
	if (widget.inputEl) widget.inputEl.style.display = show ? "" : "none";
	if (widget.element) widget.element.style.display = show ? "" : "none";
}

function setWidgetGroupVisibility(node, names, show, suffix = "") {
	let changed = 0;
	for (const name of names) {
		const widget = getWidget(node, name);
		if (!widget) continue;
		toggleWidget(node, widget, show, suffix);
		changed += 1;
	}
	scheduleNodeLayoutUpdate(node);
	setTimeout(() => scheduleNodeLayoutUpdate(node), 60);
	setTimeout(() => scheduleNodeLayoutUpdate(node), 180);
	return changed;
}

function resolveModelWidgetName(node, name) {
	for (const candidate of MODEL_WIDGET_ALIASES[name] ?? [name]) {
		if (getWidget(node, candidate)) return candidate;
	}
	return name;
}

function getModelWidget(node, name) {
	return getWidget(node, resolveModelWidgetName(node, name));
}

function getModelWidgetOptions(node, name) {
	return getWidgetOptions(node, resolveModelWidgetName(node, name));
}

function getApiProviderDisplayName(provider, baseUrl = "") {
	const rawProvider = String(provider ?? "").trim();
	if (MODEL_API_PROVIDER_VALUES.has(rawProvider)) return rawProvider;
	const url = String(baseUrl ?? "").trim().toLowerCase();
	if (url) {
		const inferred = MODEL_API_PROVIDER_HOST_HINTS.find((item) => url.includes(item.token));
		if (inferred) return inferred.label;
	}
	return rawProvider ? "自定义/未识别" : "未选择服务商";
}

function getModelApiProviderPreset(provider) {
	const normalizedProvider = String(provider ?? "").trim();
	return MODEL_API_PROVIDER_BUTTONS.find((item) => String(item.value ?? "").trim() === normalizedProvider) ?? null;
}

function normalizeModelApiBaseUrl(rawUrl) {
	const text = String(rawUrl ?? "").trim();
	if (!text) return "";
	try {
		const parsed = new URL(text);
		const pathname = String(parsed.pathname ?? "").replace(/\/+$/u, "");
		return `${String(parsed.protocol ?? "").toLowerCase()}//${String(parsed.host ?? "").toLowerCase()}${pathname && pathname !== "/" ? pathname : ""}`;
	} catch (_error) {
		return text.replace(/\/+$/u, "");
	}
}

function getModelApiEffectiveConfig(node) {
	const provider = String(getModelWidget(node, "API服务商")?.value ?? "OpenAI兼容").trim() || "OpenAI兼容";
	const preset = getModelApiProviderPreset(provider);
	const rawBaseUrl = String(getModelWidget(node, "API地址")?.value ?? "").trim();
	const rawModel = String(getModelWidget(node, "API模型")?.value ?? "").trim();
	return {
		provider,
		baseUrl: normalizeModelApiBaseUrl(rawBaseUrl || preset?.baseUrl || ""),
		model: rawModel || String(preset?.model ?? "").trim(),
		keyReference: String(getModelWidget(node, "API密钥")?.value ?? "").trim(),
		extraHeaders: String(getModelWidget(node, "API额外请求头")?.value ?? "").trim().replace(/\r\n?/gu, "\n"),
	};
}

function getModelApiConfigValidationError(node) {
	const provider = String(getModelWidget(node, "API服务商")?.value ?? "OpenAI兼容").trim() || "OpenAI兼容";
	const preset = getModelApiProviderPreset(provider);
	const rawBaseUrl = String(getModelWidget(node, "API地址")?.value ?? "").trim() || String(preset?.baseUrl ?? "").trim();
	if (!rawBaseUrl) return "API 地址为空。";
	if (/\s/u.test(rawBaseUrl)) return "API 地址不能包含空白字符。";
	if (/%(?:2e|5c)/iu.test(rawBaseUrl) || /\\/u.test(rawBaseUrl) || /\/(?:\.{1,2})(?:\/|$)/u.test(rawBaseUrl)) {
		return "API 地址路径必须规范，不能包含转义点段、反斜杠或 . / .. 路径段。";
	}
	try {
		const parsed = new URL(rawBaseUrl);
		if (!/^https?:$/iu.test(String(parsed.protocol ?? ""))) return "API 地址只允许 http:// 或 https://。";
		if (parsed.username || parsed.password) return "API 地址不能包含用户名或密码。";
		if (parsed.search || parsed.hash) return "API 地址不能包含查询参数或片段。";
		let decodedPath = String(parsed.pathname ?? "");
		try { decodedPath = decodeURI(decodedPath); } catch (_error) {}
		const decodedSegments = decodedPath.split("/").filter(Boolean);
		if (
			decodedPath.includes("\\")
			|| decodedSegments.some((segment) => segment === "." || segment === "..")
			|| [...decodedPath].some((char) => /\s/u.test(char) || char.codePointAt(0) < 32 || char.codePointAt(0) === 127 || char.codePointAt(0) > 127)
		) {
			return "API 地址路径只能使用规范 ASCII 字符，且不能包含点段、反斜杠或控制字符。";
		}
	} catch (_error) {
		return "API 地址格式无效。";
	}
	return "";
}


function buildModelApiConfigSignatureFromValues(provider, baseUrl, model, keyReference = "", extraHeaders = "") {
	const canonical = JSON.stringify([
		"API接口",
		String(provider ?? "").trim(),
		normalizeModelApiBaseUrl(baseUrl),
		String(model ?? "").trim(),
		String(keyReference ?? "").trim(),
		String(extraHeaders ?? "").trim().replace(/\r\n?/gu, "\n"),
	]);
	let hash = 0xcbf29ce484222325n;
	const prime = 0x100000001b3n;
	for (let index = 0; index < canonical.length; index += 1) {
		const codeUnit = canonical.charCodeAt(index);
		hash ^= BigInt(codeUnit & 0xff);
		hash = BigInt.asUintN(64, hash * prime);
		hash ^= BigInt((codeUnit >>> 8) & 0xff);
		hash = BigInt.asUintN(64, hash * prime);
	}
	return `model-api-v1:${hash.toString(16).padStart(16, "0")}`;
}

function buildModelApiConfigSignature(node) {
	const config = getModelApiEffectiveConfig(node);
	return buildModelApiConfigSignatureFromValues(
		config.provider,
		config.baseUrl,
		config.model,
		config.keyReference,
		config.extraHeaders,
	);
}

function getStoredModelApiRuntimeSignature(node) {
	const panelValue = String(node?.[PANEL_KEY]?.modelApiRuntimeSignature ?? "").trim();
	if (panelValue) return panelValue;
	return String(node?.properties?.[NODE_MODEL_API_RUNTIME_SIGNATURE_KEY] ?? "").trim();
}

function setStoredModelApiRuntimeSignature(node, signature) {
	const normalized = String(signature ?? "").trim();
	if (!normalized) return false;
	ensureNodeProperties(node)[NODE_MODEL_API_RUNTIME_SIGNATURE_KEY] = normalized;
	if (node?.[PANEL_KEY]) {
		node[PANEL_KEY].modelApiRuntimeSignature = normalized;
		node[PANEL_KEY].modelApiRuntimeInvalidated = false;
	}
	return true;
}

function invalidateModelApiRuntimeStatus(node) {
	if (node?.properties) delete node.properties[NODE_MODEL_API_RUNTIME_SIGNATURE_KEY];
	if (node?.[PANEL_KEY]) {
		node[PANEL_KEY].modelApiRuntimeSignature = "";
		node[PANEL_KEY].pendingModelApiConfigSignature = "";
		node[PANEL_KEY].modelApiRuntimeInvalidated = true;
	}
}

function clearPendingModelApiRun(node) {
	if (!node?.[PANEL_KEY]) return false;
	const hadPending = !!String(node[PANEL_KEY].pendingModelApiConfigSignature ?? "").trim();
	node[PANEL_KEY].pendingModelApiConfigSignature = "";
	if (hadPending) refreshModelLoaderPanel(node);
	return hadPending;
}

function getModelRuntimePayloadSignature(payload) {
	return String(payload?.model_config_signature ?? "").trim();
}
function parseModelRuntimePayloadFromSlots(slots) {
	const jsonText = String(Array.isArray(slots) ? slots[3] ?? "" : "").trim();
	if (!jsonText) return null;
	try {
		const payload = JSON.parse(jsonText);
		return payload && typeof payload === "object" && !Array.isArray(payload) ? payload : null;
	} catch (_error) {
		return null;
	}
}

function rememberModelApiRuntimeSignature(node, slots, _options = {}) {
	const payload = parseModelRuntimePayloadFromSlots(slots);
	if (!payload || String(payload.model_source ?? "") !== "API接口" || !String(payload.model_call_status ?? "").trim()) return false;
	const pending = String(node?.[PANEL_KEY]?.pendingModelApiConfigSignature ?? "").trim();
	const signature = getModelRuntimePayloadSignature(payload);
	if (!signature) return false;
	if (node?.[PANEL_KEY]?.modelApiRuntimeInvalidated && !pending) return false;
	if (pending && pending !== signature) return false;
	if (node?.[PANEL_KEY]) node[PANEL_KEY].pendingModelApiConfigSignature = "";
	return setStoredModelApiRuntimeSignature(node, signature);
}
function getModelApiPresetKeyRequirement(provider, baseUrl) {
	const preset = getModelApiProviderPreset(provider);
	const presetBaseUrl = normalizeModelApiBaseUrl(preset?.baseUrl ?? "");
	if (!presetBaseUrl || provider === "Ollama本地" || provider === "LM Studio本地") return false;
	const effectiveBaseUrl = normalizeModelApiBaseUrl(baseUrl || presetBaseUrl);
	try {
		const hostname = String(new URL(effectiveBaseUrl).hostname ?? "").toLowerCase();
		if (["127.0.0.1", "localhost", "::1", "0.0.0.0"].includes(hostname)) return false;
		return new URL(effectiveBaseUrl).origin === new URL(presetBaseUrl).origin;
	} catch (_error) {
		return effectiveBaseUrl === presetBaseUrl;
	}
}

function getModelLoaderSummary(node) {
	const source = normalizeModelSourceValue(getModelWidget(node, "模型来源")?.value);
	if (source === "仅Skill") return "Skill 离线 · 不调用模型";
	if (source === "API接口") {
		const config = getModelApiEffectiveConfig(node);
		const provider = config.provider;
		const rawModelName = String(getModelWidget(node, "API模型")?.value ?? "").trim();
		const modelName = config.model || "未填写模型";
		const rawBaseUrl = String(getModelWidget(node, "API地址")?.value ?? "").trim();
		const baseUrl = config.baseUrl;
		const displayProvider = getApiProviderDisplayName(provider, baseUrl);
		const shortModel = modelName.length > 34 ? `${modelName.slice(0, 31)}...` : modelName;
		const incomplete = !config.model || !config.baseUrl;
		return `API · ${displayProvider} · ${shortModel}${rawBaseUrl ? " · 自定义地址" : " · 预设地址"}${incomplete ? " · 未完整会回退Skill" : ""}`;
	}
	const family = String(getModelWidget(node, "模型系列")?.value ?? "未知").trim();
	const model = String(getModelWidget(node, "主模型")?.value ?? "未选择").trim();
	const mmproj = String(getModelWidget(node, "视觉投影mmproj")?.value ?? "无").trim();
	const ctx = String(getModelWidget(node, "上下文长度")?.value ?? "");
	const shortModel = model.length > 30 ? `${model.slice(0, 27)}...` : model;
	const incomplete = !model || model === "未选择" || model.startsWith("（请把模型放到");
	return `本地模型 · ${family} · ${shortModel || "外接输入/未选择"} · ctx ${ctx || "?"}${mmproj && mmproj !== "无" ? " · VL" : ""}${incomplete ? " · 无外接输入时需选择内置GGUF" : ""}`;
}

function getModelRuntimeStatusSummary(node) {
	const source = normalizeModelSourceValue(getModelWidget(node, "模型来源")?.value);
	if (source === "仅Skill") {
		return { tone: "muted", text: "API 未启用：当前运行只使用 Skill，不会发送模型请求。" };
	}
	if (source === "API接口") {
		const config = getModelApiEffectiveConfig(node);
		const provider = config.provider;
		const model = config.model;
		const baseUrl = config.baseUrl;
		const apiKey = String(getModelWidget(node, "API密钥")?.value ?? "").trim();
		const configError = getModelApiConfigValidationError(node);
		if (configError) return { tone: "error", text: `API 配置无效：${configError}` };
		if (!model || !baseUrl) {
			return { tone: "warn", text: "API 未就绪：请选择带默认值的服务商，或填写 API 地址和模型名。" };
		}
		const pending = String(node?.[PANEL_KEY]?.pendingModelApiConfigSignature ?? "").trim();
		if (pending) {
			return { tone: "ready", text: "API 请求已入队或正在运行，等待后端返回实际调用状态。" };
		}
		try {
			const jsonText = String(getCurrentStageOutputText(node, STAGE_OUTPUT_INDEX.jsonResult) ?? "").trim();
			const payload = jsonText ? JSON.parse(jsonText) : null;
			if (payload && String(payload.model_source ?? "") === "API接口") {
				const status = String(payload.model_call_status ?? "").trim();
				const fallback = String(payload.model_fallback_note ?? "").trim();
				if (status) {
					const currentSignature = buildModelApiConfigSignature(node);
					const runtimeSignature = getModelRuntimePayloadSignature(payload);
					if (!runtimeSignature) {
						return { tone: "warn", text: "旧运行结果没有配置签名，无法确认是否属于当前 API 配置。" };
					}
					if (node?.[PANEL_KEY]?.modelApiRuntimeInvalidated || runtimeSignature !== currentSignature) {
						return { tone: "warn", text: "配置已变更，等待新运行确认 API 调用状态。" };
					}
					const failedCount = Number(payload.model_call_failure_count ?? 0);
					const successCount = Number(payload.model_call_success_count ?? 0);
					const activeFallback = Number(payload.model_active_fallback_count ?? 0);
					const recovered = activeFallback <= 0 && /已恢复|无输出回退/u.test(status);
					const failureSignal = activeFallback > 0 || !!fallback || (!recovered && (failedCount > 0 || /失败|回退|错误|未找到/u.test(status)));
					return {
						tone: failureSignal ? (successCount > 0 ? "warn" : "error") : (successCount > 0 ? "success" : "ready"),
						text: `最近运行：${status}${fallback ? `；${fallback}` : ""}`,
					};
				}
			}
		} catch (_error) {}
		const envReference = apiKey.toLowerCase().startsWith("env:") ? apiKey.slice(4).trim() : "";
		if (apiKey.toLowerCase().startsWith("env:") && !envReference) {
			return { tone: "warn", text: "API 未就绪：env: 后缺少环境变量名。" };
		}
		if (envReference) {
			return { tone: "warn", text: `API 参数已填写；环境变量 ${envReference} 需后端验证，等待运行确认。` };
		}
		if (getModelApiPresetKeyRequirement(provider, baseUrl) && !apiKey) {
			return { tone: "warn", text: `未填写 API Key；运行时将检查服务商“${provider}”的标准环境变量。` };
		}
		if (!apiKey) {
			return { tone: "ready", text: "自定义/本地 API 地址允许无 Key，等待运行验证实际调用状态。" };
		}
		return { tone: "ready", text: "API 参数已填写，等待运行验证实际调用状态。" };
	}
	return { tone: "ready", text: "本地模型已选择，等待运行后确认实际调用状态。" };
}
function refreshModelLoaderDeck(deck, node) {
	if (!deck?.panel) return;
	const source = normalizeModelSourceValue(getModelWidget(node, "模型来源")?.value);
	const family = String(getModelWidget(node, "模型系列")?.value ?? "");
	const ctx = Number(getModelWidget(node, "上下文长度")?.value ?? 0);
	const gpu = Number(getModelWidget(node, "GPU层数")?.value ?? -1);
	const think = !!getModelWidget(node, "启用思考")?.value;
	const kvK = String(getModelWidget(node, "KV缓存K类型")?.value ?? "默认(F16)");
	const kvV = String(getModelWidget(node, "KV缓存V类型")?.value ?? "默认(F16)");
	const provider = String(getModelWidget(node, "API服务商")?.value ?? "OpenAI兼容").trim();
	const apiModel = String(getModelWidget(node, "API模型")?.value ?? "").trim();
	const apiBaseUrl = String(getModelWidget(node, "API地址")?.value ?? "").trim();
	const apiKey = String(getModelWidget(node, "API密钥")?.value ?? "").trim();
	const apiTimeout = Number(getModelWidget(node, "API超时秒")?.value ?? 120);
	const apiProviderDisplay = getApiProviderDisplayName(provider, apiBaseUrl);
	if (deck.statusEl) {
		const text = getModelLoaderSummary(node);
		deck.statusEl.textContent = text;
		deck.statusEl.title = text;
	}
	if (deck.runtimeStatusEl) {
		const runtime = getModelRuntimeStatusSummary(node);
		deck.runtimeStatusEl.textContent = runtime.text;
		deck.runtimeStatusEl.title = runtime.text;
		deck.runtimeStatusEl.dataset.tone = runtime.tone;
	}
	for (const button of deck.sourceButtons ?? []) {
		button.classList.toggle("is-active", String(button.dataset.value) === source);
	}
	for (const button of deck.familyButtons ?? []) {
		button.classList.toggle("is-active", String(button.dataset.value) === family);
	}
	for (const button of deck.providerButtons ?? []) {
		button.classList.toggle("is-active", String(button.dataset.value) === provider);
	}
	for (const button of deck.ctxButtons ?? []) {
		button.classList.toggle("is-active", Number(button.dataset.value) === ctx);
	}
	for (const button of deck.gpuButtons ?? []) {
		button.classList.toggle("is-active", Number(button.dataset.value) === gpu);
	}
	for (const button of deck.kvButtons ?? []) {
		button.classList.toggle("is-active", String(button.dataset.value) === kvK && String(button.dataset.value) === kvV);
	}
	if (deck.thinkButton) {
		deck.thinkButton.classList.toggle("is-active", think);
		deck.thinkButton.textContent = think ? "思考 开" : "思考 关";
	}
	if (deck.sectionValues) {
		const values = deck.sectionValues;
		if (values.source) {
			values.source.textContent = source;
			values.source.title = source;
		}
		if (values.family) {
			values.family.textContent = family || "未选择";
			values.family.title = values.family.textContent;
		}
		if (values.model) {
			values.model.textContent = `${getModelLoaderSummary(node).replace(/^.*?·\s*/u, "")}`;
			values.model.title = values.model.textContent;
		}
		if (values.runtime) {
			values.runtime.textContent = `${think ? "思考开" : "思考关"} / ${gpu < 0 ? "自动GPU" : gpu === 0 ? "CPU" : `${gpu}层`}`;
			values.runtime.title = values.runtime.textContent;
		}
		if (values.context) {
			values.context.textContent = ctx ? `${ctx / 1024}K` : "未设置";
			values.context.title = values.context.textContent;
		}
		if (values.kv) {
			values.kv.textContent = kvK === kvV ? kvK : `${kvK} / ${kvV}`;
			values.kv.title = values.kv.textContent;
		}
		if (values.apiProvider) {
			values.apiProvider.textContent = apiProviderDisplay;
			values.apiProvider.title = MODEL_API_PROVIDER_VALUES.has(provider) ? apiProviderDisplay : `原始值：${provider || "空"}；可点击服务商按钮修正。`;
		}
		if (values.apiModel) {
			values.apiModel.textContent = apiModel || "未填写";
			values.apiModel.title = values.apiModel.textContent;
		}
		if (values.apiAuth) {
			values.apiAuth.textContent = apiKey ? (apiKey.startsWith("env:") ? apiKey : "已填写 Key") : "本地/无 Key";
			values.apiAuth.title = values.apiAuth.textContent;
		}
		if (values.apiRuntime) {
			values.apiRuntime.textContent = `${apiTimeout || 60}s${apiBaseUrl ? " / 自定义地址" : " / 预设地址"}`;
			values.apiRuntime.title = values.apiRuntime.textContent;
		}
	}
	for (const select of deck.selects ?? []) {
		const widget = getModelWidget(node, select.dataset.widgetName);
		if (widget) select.value = String(widget.value ?? "");
	}
	for (const input of deck.inputs ?? []) {
		const widget = getModelWidget(node, input.dataset.widgetName);
		if (widget && document.activeElement !== input) input.value = String(widget.value ?? "");
	}
	for (const section of deck.localSections ?? []) {
		section.hidden = source !== "本地模型";
	}
	for (const section of deck.apiSections ?? []) {
		section.hidden = source !== "API接口";
	}
}

function refreshModelLoaderPanel(node) {
	const panelState = node?.[MODEL_LOADER_PANEL_KEY];
	if (!panelState) return;
	if (panelState.panel) refreshModelLoaderDeck(panelState, node);
	const connectedDecks = (panelState.modalDecks ?? []).filter((deck) => deck?.panel?.isConnected);
	panelState.modalDecks = connectedDecks;
	for (const deck of connectedDecks) refreshModelLoaderDeck(deck, node);
}

function setModelLoaderWidgetValue(node, name, value) {
	const resolvedName = resolveModelWidgetName(node, name);
	const previousValue = getWidget(node, resolvedName)?.value;
	beginNodeStateMutation(node);
	setWidgetValue(node, resolvedName, value);
	if (["模型来源", ...STAGE_EMBEDDED_API_MODEL_WIDGET_NAMES].includes(resolvedName) && String(previousValue ?? "") !== String(value ?? "")) {
		invalidateModelApiRuntimeStatus(node);
	}
	if (name === "模型来源" || STAGE_EMBEDDED_LOCAL_MODEL_WIDGET_NAMES.includes(resolvedName)) {
		try { sanitizeStagePromptNode(node, node[PANEL_KEY]?.library ?? { slot_config: [] }); } catch (_error) {}
	}
	refreshModelLoaderPanel(node);
	scheduleNodeLayoutUpdate(node);
}

function applyModelApiProviderPreset(node, item = {}) {
	const nextProvider = String(item.value ?? "OpenAI兼容");
	const previousProvider = String(getModelWidget(node, "API服务商")?.value ?? "");
	beginNodeStateMutation(node);
	invalidateModelApiRuntimeStatus(node);
	setWidgetValue(node, resolveModelWidgetName(node, "模型来源"), "API接口");
	setWidgetValue(node, resolveModelWidgetName(node, "API服务商"), nextProvider);
	setWidgetValue(node, resolveModelWidgetName(node, "API地址"), String(item.baseUrl ?? ""));
	setWidgetValue(node, resolveModelWidgetName(node, "API模型"), String(item.model ?? ""));
	if (previousProvider !== nextProvider) {
		setWidgetValue(node, resolveModelWidgetName(node, "API密钥"), String(item.keyRef ?? ""));
		setWidgetValue(node, resolveModelWidgetName(node, "API额外请求头"), "");
	}
	refreshModelLoaderPanel(node);
	scheduleNodeLayoutUpdate(node);
}

function createModelLoaderButton(node, label, value, onClick) {
	const button = document.createElement("button");
	button.type = "button";
	button.className = "qwen-te-model__button";
	button.textContent = label;
	button.dataset.value = String(value);
	button.addEventListener("pointerdown", (event) => { event.stopPropagation(); });
	button.addEventListener("mousedown", (event) => { event.stopPropagation(); });
	button.addEventListener("click", (event) => { event.stopPropagation(); onClick?.(); });
	return button;
}

function createModelLoaderSelect(node, widgetName, label) {
	const select = document.createElement("select");
	select.className = "qwen-te-model__select";
	select.dataset.widgetName = widgetName;
	select.title = label;
	const options = getModelWidgetOptions(node, widgetName);
	const current = String(getModelWidget(node, widgetName)?.value ?? "");
	for (const value of options.length ? options : [current].filter(Boolean)) {
		const option = document.createElement("option");
		option.value = value;
		option.textContent = value;
		select.appendChild(option);
	}
	select.value = current;
	select.addEventListener("pointerdown", (event) => { event.stopPropagation(); });
	select.addEventListener("mousedown", (event) => { event.stopPropagation(); });
	select.addEventListener("change", (event) => {
		event.stopPropagation();
		setModelLoaderWidgetValue(node, widgetName, select.value);
	});
	return select;
}

function createModelLoaderTextInput(node, widgetName, label, options = {}) {
	const input = document.createElement(options.multiline ? "textarea" : "input");
	input.className = "qwen-te-model__input";
	input.dataset.widgetName = widgetName;
	input.title = label;
	if (!options.multiline) input.type = widgetName === "API密钥" ? "password" : "text";
	input.placeholder = options.placeholder ?? label;
	input.value = String(getModelWidget(node, widgetName)?.value ?? "");
	input.addEventListener("pointerdown", (event) => { event.stopPropagation(); });
	input.addEventListener("mousedown", (event) => { event.stopPropagation(); });
	input.addEventListener("input", (event) => {
		event.stopPropagation();
		setModelLoaderWidgetValue(node, widgetName, input.value);
		refreshModelLoaderPanel(node);
	});
	input.addEventListener("change", (event) => {
		event.stopPropagation();
		setModelLoaderWidgetValue(node, widgetName, input.value);
		refreshModelLoaderPanel(node);
		scheduleNodeLayoutUpdate(node);
	});
	return input;
}

function createModelSection(titleText, valueText = "") {
	const section = document.createElement("div");
	section.className = "qwen-te-model__section qwen-te-model__section--card";
	const head = document.createElement("div");
	head.className = "qwen-te-model__section-head";
	section.appendChild(head);
	const title = document.createElement("div");
	title.className = "qwen-te-model__section-title";
	title.textContent = titleText;
	head.appendChild(title);
	const value = document.createElement("div");
	value.className = "qwen-te-model__section-value";
	value.textContent = valueText;
	value.title = valueText;
	head.appendChild(value);
	return { section, value };
}

function buildModelLoaderDeck(node, options = {}) {
	const availableFamilies = new Set(getModelWidgetOptions(node, "模型系列"));
	const hasStageModelSource = !!getModelWidget(node, "模型来源");
	const panel = document.createElement("div");
	panel.className = `qwen-te-model${options.modal ? " qwen-te-model--modal" : ""}`;
	panel.addEventListener("pointerdown", (event) => { event.stopPropagation(); });
	panel.addEventListener("mousedown", (event) => { event.stopPropagation(); });
	panel.addEventListener("click", (event) => { event.stopPropagation(); });

	const card = document.createElement("div");
	card.className = "qwen-te-model__card";
	panel.appendChild(card);
	const head = document.createElement("div");
	head.className = "qwen-te-model__head";
	card.appendChild(head);
	const title = document.createElement("div");
	title.className = "qwen-te-model__title";
	title.textContent = "TE MODEL DECK";
	head.appendChild(title);
	const statusEl = document.createElement("div");
	statusEl.className = "qwen-te-model__status";
	head.appendChild(statusEl);
	const runtimeStatusEl = document.createElement("div");
	runtimeStatusEl.className = "qwen-te-model__runtime-status";
	runtimeStatusEl.dataset.tone = "muted";
	card.appendChild(runtimeStatusEl);

	const sourceSection = createModelSection("模型来源", "Skill / 本地 / API");
	sourceSection.section.hidden = !hasStageModelSource;
	card.appendChild(sourceSection.section);
	const sourceGrid = document.createElement("div");
	sourceGrid.className = "qwen-te-model__grid qwen-te-model__grid--wide";
	sourceSection.section.appendChild(sourceGrid);
	const sourceButtons = MODEL_SOURCE_BUTTONS.map((item) => {
		const button = createModelLoaderButton(node, item.label, item.value, () => setModelLoaderWidgetValue(node, "模型来源", item.value));
		button.title = item.hint;
		sourceGrid.appendChild(button);
		return button;
	});

	const apiProviderSection = createModelSection("API 服务商", "选服务商会自动填地址");
	apiProviderSection.section.hidden = true;
	card.appendChild(apiProviderSection.section);
	const apiProviderGrid = document.createElement("div");
	apiProviderGrid.className = "qwen-te-model__grid";
	apiProviderSection.section.appendChild(apiProviderGrid);
	const providerButtons = MODEL_API_PROVIDER_BUTTONS.map((item) => {
		const button = createModelLoaderButton(node, item.label, item.value, () => applyModelApiProviderPreset(node, item));
		button.title = item.hint ?? `${item.value} API`;
		apiProviderGrid.appendChild(button);
		return button;
	});

	const apiTextSection = createModelSection("API 参数", "Base URL / Key / 模型名");
	apiTextSection.section.hidden = true;
	card.appendChild(apiTextSection.section);
	const apiInputGrid = document.createElement("div");
	apiInputGrid.className = "qwen-te-model__api-grid";
	apiTextSection.section.appendChild(apiInputGrid);
	const apiBaseInput = createModelLoaderTextInput(node, "API地址", "API Base URL", { placeholder: "留空用服务商预设，或填 https://host/v1" });
	const apiKeyInput = createModelLoaderTextInput(node, "API密钥", "API Key", { placeholder: "推荐 env:变量名；自定义地址需授权来源" });
	const apiModelInput = createModelLoaderTextInput(node, "API模型", "API 模型名", { placeholder: "例如 gpt-4o-mini / deepseek-chat / qwen-plus" });
	const apiTimeoutInput = createModelLoaderTextInput(node, "API超时秒", "超时秒", { placeholder: "建议 90-180，瞬时错误自动重试" });
	apiInputGrid.appendChild(apiBaseInput);
	apiInputGrid.appendChild(apiKeyInput);
	apiInputGrid.appendChild(apiModelInput);
	apiInputGrid.appendChild(apiTimeoutInput);

	const apiHeaderSection = createModelSection("API 额外请求头", "可选 Header");
	apiHeaderSection.section.hidden = true;
	card.appendChild(apiHeaderSection.section);
	const apiHeaderInput = createModelLoaderTextInput(node, "API额外请求头", "API 额外请求头", {
		multiline: true,
		placeholder: "可选，每行一个 Header: Value\nOpenRouter 示例：HTTP-Referer: https://...\nX-Title: ComfyUI Qwen TE",
	});
	apiHeaderSection.section.appendChild(apiHeaderInput);

	const familySection = createModelSection("模型系列", "自动匹配模型格式");
	card.appendChild(familySection.section);
	const familyGrid = document.createElement("div");
	familyGrid.className = "qwen-te-model__grid";
	familySection.section.appendChild(familyGrid);
	const familyButtons = MODEL_FAMILY_BUTTONS.map((item) => {
		const button = createModelLoaderButton(node, item.label, item.value, () => setModelLoaderWidgetValue(node, "模型系列", item.value));
		button.title = item.hint;
		button.disabled = availableFamilies.size > 0 && !availableFamilies.has(item.value);
		familyGrid.appendChild(button);
		return button;
	});

	const selectSection = createModelSection("模型文件", "主模型 / 视觉投影");
	card.appendChild(selectSection.section);
	const selectRow = document.createElement("div");
	selectRow.className = "qwen-te-model__select-row";
	selectSection.section.appendChild(selectRow);
	const modelSelect = createModelLoaderSelect(node, "主模型", "主模型");
	const mmprojSelect = createModelLoaderSelect(node, "视觉投影mmproj", "视觉投影mmproj");
	selectRow.appendChild(modelSelect);
	selectRow.appendChild(mmprojSelect);

	const settingsGrid = document.createElement("div");
	settingsGrid.className = "qwen-te-model__settings";
	card.appendChild(settingsGrid);
	const runtimeSection = createModelSection("推理开关", "思考 / GPU");
	settingsGrid.appendChild(runtimeSection.section);
	const quickbar = document.createElement("div");
	quickbar.className = "qwen-te-model__quickbar";
	runtimeSection.section.appendChild(quickbar);
	const thinkButton = createModelLoaderButton(node, "思考开", "think", () => setModelLoaderWidgetValue(node, "启用思考", !getModelWidget(node, "启用思考")?.value));
	quickbar.appendChild(thinkButton);
	const gpuButtons = [];
	for (const item of MODEL_GPU_BUTTONS.slice(0, 2)) {
		const button = createModelLoaderButton(node, item.label, item.value, () => setModelLoaderWidgetValue(node, "GPU层数", item.value));
		gpuButtons.push(button);
		quickbar.appendChild(button);
	}
	const gpuExtraButton = createModelLoaderButton(node, "99层", 99, () => setModelLoaderWidgetValue(node, "GPU层数", 99));
	gpuButtons.push(gpuExtraButton);
	quickbar.appendChild(gpuExtraButton);

	const ctxSection = createModelSection("上下文长度", "默认 8K");
	settingsGrid.appendChild(ctxSection.section);
	const ctxGrid = document.createElement("div");
	ctxGrid.className = "qwen-te-model__grid qwen-te-model__grid--wide";
	ctxSection.section.appendChild(ctxGrid);
	const ctxButtons = MODEL_CONTEXT_BUTTONS.map((value) => {
		const button = createModelLoaderButton(node, `${value / 1024}K`, value, () => setModelLoaderWidgetValue(node, "上下文长度", value));
		ctxGrid.appendChild(button);
		return button;
	});

	const kvSection = createModelSection("KV 缓存精度", "K / V 同步");
	settingsGrid.appendChild(kvSection.section);
	const kvGrid = document.createElement("div");
	kvGrid.className = "qwen-te-model__quickbar";
	kvSection.section.appendChild(kvGrid);
	const kvButtons = MODEL_KV_BUTTONS.map((item) => {
		const button = createModelLoaderButton(node, item.label, item.value, () => {
			beginNodeStateMutation(node);
			setWidgetValue(node, resolveModelWidgetName(node, "KV缓存K类型"), item.value);
			setWidgetValue(node, resolveModelWidgetName(node, "KV缓存V类型"), item.value);
			refreshModelLoaderPanel(node);
			scheduleNodeLayoutUpdate(node);
		});
		kvGrid.appendChild(button);
		return button;
	});
	const hint = document.createElement("div");
	hint.className = "qwen-te-model__hint";
	hint.textContent = options.hint ?? "当前节点按“模型来源”决定是否调用模型；env 密钥只发送到服务商预设来源，自定义来源需配置 QWEN_TE_CUSTOM_API_SECRET_ORIGINS。直接填写的 Key 会保存在工作流里。";
	card.appendChild(hint);
	return {
		panel,
		statusEl,
		runtimeStatusEl,
		sectionValues: {
			source: sourceSection.value,
			apiProvider: apiProviderSection.value,
			apiModel: apiTextSection.value,
			apiAuth: apiHeaderSection.value,
			family: familySection.value,
			model: selectSection.value,
			runtime: runtimeSection.value,
			context: ctxSection.value,
			kv: kvSection.value,
		},
		sourceButtons,
		providerButtons,
		familyButtons,
		ctxButtons,
		gpuButtons,
		kvButtons,
		thinkButton,
		selects: [modelSelect, mmprojSelect],
		inputs: [apiBaseInput, apiKeyInput, apiModelInput, apiTimeoutInput, apiHeaderInput],
		apiSections: hasStageModelSource ? [apiProviderSection.section, apiTextSection.section, apiHeaderSection.section] : [],
		localSections: [familySection.section, selectSection.section, runtimeSection.section, ctxSection.section, kvSection.section],
	};
}

function openStageModelDialog(stageNode) {
	ensureSingleModal("stage-model-deck");
	if (!getModelWidget(stageNode, "主模型")) {
		setNodeStatusText(stageNode, "当前节点还没有内置模型控件。请重启 ComfyUI 后刷新工作流。");
		return;
	}
	const overlay = document.createElement("div");
	overlay.className = "qwen-te-modal";
	overlay.dataset.qwenModal = "stage-model-deck";
	overlay.__qwenNode = stageNode;
	const dialog = document.createElement("div");
	dialog.className = "qwen-te-modal__dialog";
	dialog.style.width = "min(820px,95vw)";
	overlay.appendChild(dialog);
	const header = document.createElement("div");
	header.className = "qwen-te-modal__header";
	dialog.appendChild(header);
	const titleWrap = document.createElement("div");
	header.appendChild(titleWrap);
	const title = document.createElement("div");
	title.className = "qwen-te-modal__title";
	title.textContent = "模型";
	titleWrap.appendChild(title);
	const subtitle = document.createElement("div");
	subtitle.className = "qwen-te-modal__subtitle";
	subtitle.textContent = "选择提示词增强方式：Skill、本地模型或 API。本地模型支持外接兼容对象，未连接时使用内置 GGUF；不完整时自动回退 Skill。";
	titleWrap.appendChild(subtitle);
	const closeButton = document.createElement("button");
	closeButton.className = "qwen-te-modal__footer-button";
	closeButton.textContent = "关闭";
	header.appendChild(closeButton);
	const body = document.createElement("div");
	body.className = "qwen-te-modal__body";
	dialog.appendChild(body);
	const statusEl = document.createElement("div");
	statusEl.className = "qwen-te-modal__status";
	statusEl.textContent = `当前模型策略：${getModelLoaderSummary(stageNode)}`;
	body.appendChild(statusEl);
	const deck = buildModelLoaderDeck(stageNode, { modal: true, hint: "API 支持 OpenAI 兼容、Claude、Gemini、Ollama、LM Studio 等；env 密钥只发送到受信任来源，自定义来源需显式授权。若模型名或本地文件缺失，运行时会回退 Skill 并在标签摘要里提示原因。" });
	body.appendChild(deck.panel);
	const footer = document.createElement("div");
	footer.className = "qwen-te-modal__footer";
	dialog.appendChild(footer);
	const focusButton = document.createElement("button");
	focusButton.className = "qwen-te-modal__footer-button";
	focusButton.textContent = "收起底层";
	footer.appendChild(focusButton);
	const doneButton = document.createElement("button");
	doneButton.className = "qwen-te-modal__footer-button qwen-te-modal__footer-button--primary";
	doneButton.textContent = "完成";
	footer.appendChild(doneButton);
	if (!stageNode[MODEL_LOADER_PANEL_KEY]) stageNode[MODEL_LOADER_PANEL_KEY] = {};
	if (!Array.isArray(stageNode[MODEL_LOADER_PANEL_KEY].modalDecks)) stageNode[MODEL_LOADER_PANEL_KEY].modalDecks = [];
	stageNode[MODEL_LOADER_PANEL_KEY].modalDecks.push(deck);
	const refreshDeckStatus = () => {
		refreshModelLoaderDeck(deck, stageNode);
		statusEl.textContent = `当前模型策略：${getModelLoaderSummary(stageNode)}`;
	};
	refreshDeckStatus();
	focusButton.onclick = () => {
		setWidgetGroupVisibility(stageNode, STAGE_EMBEDDED_MODEL_WIDGET_NAMES, false, "Model");
		setNodeStatusText(stageNode, "已收起模型底层控件，按钮面板仍会同步当前设置。");
	};
	const disposeDeck = () => {
		const decks = stageNode[MODEL_LOADER_PANEL_KEY]?.modalDecks;
		if (Array.isArray(decks)) stageNode[MODEL_LOADER_PANEL_KEY].modalDecks = decks.filter((item) => item !== deck);
	};
	overlay.__qwenDispose = disposeDeck;
	const close = () => disposeModalOverlay(overlay);
	doneButton.onclick = close;
	closeButton.onclick = close;
	overlay.addEventListener("click", (event) => { if (event.target === overlay) close(); });
	document.body.appendChild(overlay);
	setNodeStatusText(stageNode, `模型面板已打开：${getModelLoaderSummary(stageNode)}`);
}

function setPanelToggleButtonState(button, active, activeLabel, inactiveLabel) {
	const labelEl = button?.querySelector?.(".qwen-te-panel__button-label");
	if (labelEl) labelEl.textContent = active ? activeLabel : inactiveLabel;
	button?.classList?.toggle?.("is-active", !!active);
	button?.setAttribute?.("aria-pressed", active ? "true" : "false");
}

function isButtonLikeElement(element) {
	return !!element && typeof element === "object" && typeof element.classList?.toggle === "function";
}

function isWidgetGroupVisible(node, names, expectedHiddenSuffix = "") {
	for (const name of names ?? []) {
		const widget = getWidget(node, name);
		if (!widget) continue;
		if (!widget.hidden && !isHiddenWidgetType(widget.type)) return true;
		if (expectedHiddenSuffix && String(widget.type ?? "") === `easyHidden${expectedHiddenSuffix}`) return false;
	}
	return false;
}

const STAGE_OUTPUT_INDEX = {
	fullText: 0,
	promptText: 1,
	selectedTags: 2,
	jsonResult: 3,
	negativePrompt: 4,
	promptCollection: 5,
	smartText: 6,
};

const STAGE_DISPLAY_MODES = [
	{ key: "prompt", label: "正向", source: "正向输出" },
	{ key: "negative", label: "负面", source: "负面输出" },
	{ key: "tags", label: "标签", source: "标签输出" },
	{ key: "blocks", label: "编排", source: "标签块编排" },
	{ key: "json", label: "JSON", source: "JSON结果" },
	{ key: "smart", label: "智能文本", source: "智能文本" },
];
const STAGE_OUTPUT_FIELD_KEYS = ["full_text", "prompt_text", "selected_tags_text", "json_result", "negative_prompt", "prompt_collection", "smart_text_prompt"];
const STAGE_OUTPUT_TIMESTAMP_TOLERANCE_MS = 50;
const STAGE_OUTPUT_LEGACY_SECONDS_TOLERANCE_MS = 1100;
const STAGE_OUTPUT_POLL_IDLE_LIMIT = 12;
const STAGE_OUTPUT_POLL_ACTIVE_LIMIT = 600;
const STAGE_CANVAS_OUTPUT_LABELS = ["全文", "正向", "标签", "JSON", "负面", "合集", "智能"];

function compactStagePromptOutputs(node) {
	const outputs = node?.outputs ?? [];
	if (!Array.isArray(outputs) || !outputs.length) return false;
	let changed = false;
	for (let index = 0; index < outputs.length; index += 1) {
		const output = outputs[index];
		if (!output || typeof output !== "object") continue;
		const compactLabel = STAGE_CANVAS_OUTPUT_LABELS[index] ?? String(output.name ?? "");
		if (!("_qwenTeOriginalName" in output)) output._qwenTeOriginalName = String(output.name ?? "");
		if (String(output.name ?? "") !== compactLabel) {
			output.name = compactLabel;
			changed = true;
		}
		output.label = compactLabel;
		output.localized_name = compactLabel;
	}
	if (changed) app.graph?.setDirtyCanvas?.(true, true);
	return changed;
}

function flattenStageOutputValues(value, depth = 0) {
	if (depth > 5 || value == null) return [];
	if (typeof value === "string") return [value];
	if (typeof value === "number" || typeof value === "boolean") return [String(value)];
	if (Array.isArray(value)) {
		const result = [];
		for (const item of value) result.push(...flattenStageOutputValues(item, depth + 1));
		return result;
	}
	if (typeof value === "object") {
		const orderedKeys = STAGE_OUTPUT_FIELD_KEYS;
		if (orderedKeys.every((key) => key in value)) {
			return orderedKeys.map((key) => normalizeStageTextValue(value[key]));
		}
		for (const key of ["text", "string", "strings", "values", "result", "output", "outputs", "ui", "value", "content"]) {
			if (!(key in value)) continue;
			const nested = flattenStageOutputValues(value[key], depth + 1);
			if (nested.length) return nested;
		}
	}
	return [];
}

function normalizeStageExecutionOutputs(payload) {
	const orderedKeys = STAGE_OUTPUT_FIELD_KEYS;
	if (payload && typeof payload === "object" && orderedKeys.every((key) => key in payload)) {
		return orderedKeys.map((key) => normalizeStageTextValue(payload[key]));
	}
	const flattened = flattenStageOutputValues(payload).map((item) => String(item ?? ""));
	return flattened.length ? flattened : [];
}

function normalizeStageExecutionOutputSlots(payload) {
	const outputs = normalizeStageExecutionOutputs(payload);
	return Array.from({ length: STAGE_OUTPUT_FIELD_KEYS.length }, (_, index) => String(outputs[index] ?? "").trim());
}

function scoreStageOutputSlots(slots) {
	if (!Array.isArray(slots)) return 0;
	let score = 0;
	for (const value of slots) {
		if (String(value ?? "").trim()) score += 1;
	}
	if (String(slots[STAGE_OUTPUT_INDEX.promptText] ?? "").trim()) score += 8;
	if (String(slots[STAGE_OUTPUT_INDEX.fullText] ?? "").trim()) score += 3;
	if (String(slots[STAGE_OUTPUT_INDEX.jsonResult] ?? "").trim()) score += 2;
	if (String(slots[STAGE_OUTPUT_INDEX.smartText] ?? "").trim()) score += 2;
	return score;
}

function extractStageOutputSlotsFromPayload(payload) {
	if (!payload || typeof payload !== "object") return normalizeStageExecutionOutputSlots(payload);
	const candidates = [];
	const pushCandidate = (candidate) => {
		const slots = normalizeStageExecutionOutputSlots(candidate);
		const score = scoreStageOutputSlots(slots);
		if (score > 0) candidates.push({ slots, score });
	};
	for (const key of ["qwen_te_stage_output", "output", "outputs", "ui", "result", "value", "content"]) {
		if (key in payload) pushCandidate(payload[key]);
	}
	pushCandidate(payload);
	candidates.sort((left, right) => right.score - left.score);
	return candidates[0]?.slots ?? [];
}

function extractStageOutputSlotsFromExecutedArgs(argsLike) {
	const candidates = [];
	for (const arg of Array.from(argsLike ?? [])) {
		const slots = extractStageOutputSlotsFromPayload(arg);
		const score = scoreStageOutputSlots(slots);
		if (score > 0) candidates.push({ slots, score });
	}
	candidates.sort((left, right) => right.score - left.score);
	return candidates[0]?.slots ?? [];
}

function normalizeStageTimestampMs(value) {
	const numberValue = Number(value ?? 0) || 0;
	if (numberValue <= 0) return 0;
	// Python cache payloads use milliseconds, but older/debug payloads may use seconds.
	return numberValue < 1000000000000 ? numberValue * 1000 : numberValue;
}

function getStageOutputTimestampToleranceMs(value) {
	const numberValue = Number(value ?? 0) || 0;
	return numberValue > 0 && numberValue < 1000000000000
		? STAGE_OUTPUT_LEGACY_SECONDS_TOLERANCE_MS
		: STAGE_OUTPUT_TIMESTAMP_TOLERANCE_MS;
}

function captureStageExecutionOutputsFromArgs(node, argsLike) {
	const panelState = node?.[PANEL_KEY];
	if (!panelState) return false;
	const slots = extractStageOutputSlotsFromExecutedArgs(argsLike);
	if (!scoreStageOutputSlots(slots)) return false;
	panelState.lastExecutionOutputs = slots;
	rememberModelApiRuntimeSignature(node, slots, { allowCurrent: true });
	return true;
}

function getStageOutputCacheLookupIds(node) {
	const ids = [
		node?.id,
		node?.properties?.unique_id,
		node?.properties?.uniqueId,
		node?.properties?.node_id,
		node?.properties?.nodeId,
		node?.properties?.id,
	];
	for (const widget of Array.isArray(node?.widgets) ? node.widgets : []) {
		const name = String(widget?.name ?? "").trim().toLowerCase();
		if (["unique_id", "uniqueid", "node_id", "nodeid"].includes(name)) ids.push(widget?.value);
	}
	return [...new Set(ids.map((value) => String(value ?? "").trim()).filter(Boolean))];
}

async function syncNodeStageOutputCache(node, options = {}) {
	const nodeIds = getStageOutputCacheLookupIds(node);
	if (!nodeIds.length) return null;
	const cacheNamespace = ensureNodeCacheNamespace(node);
	const shouldCommit = typeof options.shouldCommit === "function" ? options.shouldCommit : () => true;
	try {
		for (const nodeId of nodeIds) {
			if (!shouldCommit()) return null;
			const { response, data: payload } = await fetchJsonWithTimeout(`/qwen_te/stage_output/${encodeURIComponent(nodeId)}?namespace=${encodeURIComponent(cacheNamespace)}`, { cache: "no-store" }, {
				owner: options.requestOwner ?? node,
				key: options.requestKey ?? "stage-output",
				timeoutMs: options.requestTimeoutMs ?? 12000,
			});
			if (!shouldCommit()) return null;
			if (!response.ok) continue;
			if (!shouldCommit()) return null;
			const output = payload?.output && typeof payload.output === "object" ? payload.output : null;
			if (!output) continue;
			if (node?.[PANEL_KEY]) {
				const queuedAt = Number(node[PANEL_KEY]?.lastWorkflowQueueRequestedAt ?? 0) || 0;
				const outputUpdatedAt = normalizeStageTimestampMs(output.updated_at);
				const timestampToleranceMs = getStageOutputTimestampToleranceMs(output.updated_at);
				const clearedAt = Number(node[PANEL_KEY]?.displayClearedAt ?? 0) || 0;
				if (clearedAt > 0 && (outputUpdatedAt <= 0 || outputUpdatedAt + 50 <= clearedAt)) {
					continue;
				}
				const freshnessBaseline = Math.max(queuedAt, clearedAt);
				const staleForCurrentRun = freshnessBaseline > 0 && (outputUpdatedAt <= 0 || outputUpdatedAt + timestampToleranceMs < freshnessBaseline);
				node[PANEL_KEY].directStageOutputCache = { ...output, _qwenStaleForCurrentRun: staleForCurrentRun };
				node[PANEL_KEY].directStageOutputCacheId = nodeId;
				const normalizedOutputs = extractStageOutputSlotsFromPayload(output);
				if (!staleForCurrentRun && normalizedOutputs.some((value) => String(value ?? "").trim())) {
					node[PANEL_KEY].lastExecutionOutputs = normalizedOutputs;
					if (node[PANEL_KEY].pendingModelApiConfigSignature) rememberModelApiRuntimeSignature(node, normalizedOutputs);
				}
			}
			return output;
		}
		return null;
	} catch {
		return null;
	}
}

function stopStageOutputPolling(node) {
	const panelState = node?.[PANEL_KEY];
	if (!panelState) return;
	panelState.stageOutputPollGeneration = Math.max(0, Number(panelState.stageOutputPollGeneration ?? 0) || 0) + 1;
	if (panelState.stageOutputPollTimer) clearInterval(panelState.stageOutputPollTimer);
	abortOwnedRequest(node, "stage-output");
	panelState.stageOutputPollTimer = null;
	panelState.stageOutputPollIdleCount = 0;
	panelState.stageOutputPollActiveCount = 0;
}

function ensureStageOutputPolling(node, options = {}) {
	const panelState = node?.[PANEL_KEY];
	if (!panelState || node?.[NODE_REMOVED_KEY]) return;
	panelState.stageOutputPollIdleCount = 0;
	panelState.stageOutputPollActiveCount = 0;
	if (panelState.stageOutputPollTimer) return;
	const intervalMs = Math.max(400, Number(options.intervalMs ?? 700) || 700);
	const idleLimit = Math.max(1, Math.trunc(Number(options.idleLimit ?? STAGE_OUTPUT_POLL_IDLE_LIMIT) || STAGE_OUTPUT_POLL_IDLE_LIMIT));
	const activeLimit = Math.max(idleLimit, Math.trunc(Number(options.activeLimit ?? STAGE_OUTPUT_POLL_ACTIVE_LIMIT) || STAGE_OUTPUT_POLL_ACTIVE_LIMIT));
	const pollGeneration = Math.max(0, Number(panelState.stageOutputPollGeneration ?? 0) || 0) + 1;
	panelState.stageOutputPollGeneration = pollGeneration;
	let inFlight = false;
	let pollTimer = null;
	pollTimer = setInterval(async () => {
		if (inFlight) return;
		const isPollCurrent = () => !node?.[NODE_REMOVED_KEY]
			&& node?.[PANEL_KEY] === panelState
			&& panelState.stageOutputPollGeneration === pollGeneration
			&& panelState.stageOutputPollTimer === pollTimer
			&& (app.graph?._nodes ?? []).includes(node);
		if (!isPollCurrent()) {
			if (panelState.stageOutputPollTimer === pollTimer) stopStageOutputPolling(node);
			return;
		}
		panelState.stageOutputPollActiveCount = Math.max(0, Number(panelState.stageOutputPollActiveCount ?? 0) || 0) + 1;
		if (panelState.stageOutputPollActiveCount > activeLimit) {
			clearPendingModelApiRun(node);
			stopStageOutputPolling(node);
			return;
		}
		inFlight = true;
		try {
			const output = await syncNodeStageOutputCache(node, { shouldCommit: isPollCurrent });
			if (!isPollCurrent()) return;
			const staleForCurrentRun = !!node?.[PANEL_KEY]?.directStageOutputCache?._qwenStaleForCurrentRun;
			const outputStatus = String(output?.status ?? "").trim().toLowerCase();
			const outputIsRunning = ["running", "queued", "pending", "processing"].includes(outputStatus);
			const outputIsFailed = ["error", "failed", "cancelled", "canceled"].includes(outputStatus);
			const outputIsFinal = !outputStatus || outputStatus === "done";
			if (staleForCurrentRun) {
				panelState.stageOutputPollIdleCount = Math.max(0, Number(panelState.stageOutputPollIdleCount ?? 0) || 0) + 1;
				if (panelState.stageOutputPollIdleCount >= idleLimit) {
					clearPendingModelApiRun(node);
					stopStageOutputPolling(node);
				}
				return;
			}
			if (outputIsRunning) {
				panelState.stageOutputPollIdleCount = 0;
				if (output) refreshStageDisplay(node);
				return;
			}
			if (output && outputIsFailed) {
				clearPendingModelApiRun(node);
				refreshStageDisplay(node);
				stopStageOutputPolling(node);
				return;
			}
			if (output && outputIsFinal) {
				const directStageOutput = normalizeHistoryStageOutputPayload(output);
				const hasUsableOutput = hasUsableStageOutputSnapshot(directStageOutput);
				if (hasUsableOutput && node?.[PANEL_KEY]) {
					node[PANEL_KEY].lastExecutionOutputs = buildStageOutputListFromSnapshot(directStageOutput);
				}
				if (hasUsableOutput) {
					syncNodeRandomDedupeCacheFromResult(node, directStageOutput?.jsonPayload ?? null);
					syncNodePromptDedupeCacheFromResult(node, directStageOutput?.jsonPayload ?? null);
					refreshStageDisplay(node);
					recordStageExecution(node, node?.[PANEL_KEY]?.library ?? { slot_config: [] }, null, directStageOutput);
					stopStageOutputPolling(node);
					return;
				}
			}
			panelState.stageOutputPollIdleCount = Math.max(0, Number(panelState.stageOutputPollIdleCount ?? 0) || 0) + 1;
			if (panelState.stageOutputPollIdleCount >= idleLimit) {
				clearPendingModelApiRun(node);
				stopStageOutputPolling(node);
			}
		} finally {
			inFlight = false;
		}
	}, intervalMs);
	panelState.stageOutputPollTimer = pollTimer;
	// Node-based contract tests and server-side previews should not be kept alive by UI polling.
	panelState.stageOutputPollTimer?.unref?.();
}

function getStageOutputValueFromList(values, outputIndex) {
	if (!Array.isArray(values) || !values.length) return "";
	const direct = values.length > outputIndex ? normalizeStageTextValue(values[outputIndex]).trim() : "";
	if (direct) return direct;
	if (outputIndex === STAGE_OUTPUT_INDEX.promptText) {
		return normalizeStageTextValue(
			values[STAGE_OUTPUT_INDEX.promptText]
			?? values[STAGE_OUTPUT_INDEX.promptCollection]
			?? values[STAGE_OUTPUT_INDEX.smartText]
			?? values[STAGE_OUTPUT_INDEX.fullText]
			?? "",
		).trim();
	}
	return "";
}

function getDirectStageOutputValue(directCache, outputIndex) {
	if (!directCache || typeof directCache !== "object") return "";
	const outputList = Array.isArray(directCache.outputs) ? directCache.outputs : STAGE_OUTPUT_FIELD_KEYS.map((key) => directCache[key]);
	const direct = getStageOutputValueFromList(outputList, outputIndex);
	if (direct) return direct;
	const slots = extractStageOutputSlotsFromPayload(directCache);
	return getStageOutputValueFromList(slots, outputIndex);
}

function getWidgetLikeTextValue(widget) {
	const candidates = [
		widget?.value,
		widget?.text,
		widget?.content,
		widget?.inputEl?.value,
		widget?.inputEl?.textContent,
		widget?.inputEl?.innerText,
		widget?.element?.value,
		widget?.element?.textContent,
		widget?.element?.innerText,
		widget?.textarea?.value,
		widget?.domElement?.value,
		widget?.domElement?.textContent,
		widget?.domElement?.innerText,
		widget?.el?.value,
		widget?.el?.textContent,
		widget?.el?.innerText,
		widget?.options?.value,
	];
	for (const value of candidates) {
		const text = normalizeStageTextValue(value).trim();
		if (text) return text;
	}
	return "";
}

function collectOutputLinkReferences(output) {
	const result = [];
	const seen = new Set();
	const push = (value) => {
		if (value == null) return;
		if (Array.isArray(value) && !(value.length >= 4 && (typeof value[3] === "string" || typeof value[3] === "number"))) {
			for (const item of value) push(item);
			return;
		}
		const key = Array.isArray(value)
			? JSON.stringify(value.slice(0, 5))
			: typeof value === "object"
				? JSON.stringify([value.id, value.target_id, value.targetId, value.target_slot, value.targetSlot])
				: String(value);
		if (seen.has(key)) return;
		seen.add(key);
		result.push(value);
	};
	push(output?.links);
	push(output?.link);
	push(output?._links);
	return result;
}

function resolveGraphLink(linkRef) {
	if (linkRef && typeof linkRef === "object") return linkRef;
	const graphLinks = app.graph?.links;
	if (!graphLinks) return null;
	const direct = graphLinks?.[linkRef] ?? graphLinks?.[String(linkRef)];
	if (direct) return direct;
	const matchesId = (link) => String(Array.isArray(link) ? link[0] : link?.id ?? "") === String(linkRef);
	if (Array.isArray(graphLinks)) return graphLinks.find(matchesId) ?? null;
	if (typeof graphLinks === "object") return Object.values(graphLinks).find(matchesId) ?? null;
	return null;
}

function getGraphLinkId(link, fallback = "") {
	return String(Array.isArray(link) ? link[0] ?? fallback : link?.id ?? fallback ?? "");
}

function getGraphLinkTargetId(link) {
	if (Array.isArray(link)) return link[3];
	return link?.target_id ?? link?.targetId ?? link?.target ?? link?.target_node_id ?? link?.targetNodeId;
}

function getGraphLinkTargetSlot(link) {
	if (Array.isArray(link)) return link[4];
	return link?.target_slot ?? link?.targetSlot ?? link?.target_input ?? link?.targetInput ?? 0;
}

function getGraphNodeByIdSafe(nodeId) {
	const id = String(nodeId ?? "");
	if (!id) return null;
	const direct = app.graph?.getNodeById?.(nodeId);
	if (direct) return direct;
	const nodes = app.graph?._nodes ?? app.graph?.nodes ?? [];
	return Array.from(nodes ?? []).find((item) => String(item?.id ?? "") === id) ?? null;
}

function collectLinkedStageOutputCandidates(node, outputIndex) {
	const outputs = node.outputs ?? [];
	if (outputs.length <= outputIndex) return [];
	const output = outputs[outputIndex];
	const linkRefs = collectOutputLinkReferences(output);
	if (!linkRefs.length) return [];
	const candidates = [];
	for (const linkRef of linkRefs) {
		const link = resolveGraphLink(linkRef);
		if (!link) continue;
		const linkId = getGraphLinkId(link, linkRef);
		const targetNode = getGraphNodeByIdSafe(getGraphLinkTargetId(link));
		const nodeType = String(targetNode?.type ?? "");
		const nodeTitle = String(targetNode?.title ?? "");
		let textValue = "";
		if (targetNode?.widgets?.length) {
			const exactShowTextWidget = targetNode.widgets.find((widget) => /^text_[1-9]\d*$/iu.test(String(widget?.name ?? "")) && getWidgetLikeTextValue(widget));
			const fallbackShowTextWidget = targetNode.widgets.find((widget) => /^text(?:_\d+)?$/iu.test(String(widget?.name ?? "")) && getWidgetLikeTextValue(widget));
			const genericTextWidget = targetNode.widgets.find((widget) => getWidgetLikeTextValue(widget));
			textValue = getWidgetLikeTextValue(exactShowTextWidget) || getWidgetLikeTextValue(fallbackShowTextWidget) || getWidgetLikeTextValue(genericTextWidget);
		}
		if (!textValue && Array.isArray(targetNode?.widgets_values)) {
			const valueFromWidgets = [...targetNode.widgets_values].reverse()
				.map((value) => normalizeStageTextValue(value).trim())
				.find((value) => value);
			textValue = String(valueFromWidgets ?? "").trim();
		}
		if (!textValue && targetNode?.properties && typeof targetNode.properties === "object") {
			const valueFromProperties = [
				targetNode.properties.text,
				targetNode.properties.value,
				targetNode.properties.content,
				targetNode.properties.prompt,
				targetNode.properties.prompt_text,
				targetNode.properties.positivePrompt,
				targetNode.properties.positive_prompt,
				targetNode.properties.output,
				targetNode.properties.result,
				targetNode.properties.display_text,
			]
				.map((value) => normalizeStageTextValue(value).trim())
				.find((value) => value);
			textValue = String(valueFromProperties ?? "").trim();
		}
		if (!textValue) continue;
		const score =
			(/showtext/i.test(nodeType) ? 4 : 0)
			+ (/显示文本|showtext/i.test(nodeTitle) ? 3 : 0)
			+ (/text/i.test(nodeType) ? 1 : 0)
			+ (/^text(?:_\d+)?$/iu.test(String(targetNode?.widgets?.[0]?.name ?? "")) ? 1 : 0);
		candidates.push({
			score,
			value: textValue,
			linkId,
			targetId: Number(targetNode?.id ?? getGraphLinkTargetId(link) ?? 0) || 0,
			targetType: nodeType,
			targetTitle: nodeTitle,
			targetSlot: Number(getGraphLinkTargetSlot(link) ?? 0) || 0,
			textWidgets: (targetNode?.widgets ?? [])
				.filter((widget) => getWidgetLikeTextValue(widget))
				.map((widget, index) => ({
					index,
					name: String(widget?.name ?? ""),
					value: getWidgetLikeTextValue(widget),
				})),
			widgetsValues: Array.isArray(targetNode?.widgets_values)
				? targetNode.widgets_values
					.map((value, index) => ({
						index,
						value: normalizeStageTextValue(value).trim(),
					}))
					.filter((item) => item.value)
				: [],
		});
	}
	candidates.sort((left, right) => right.score - left.score);
	return candidates;
}

function getLinkedStageOutputText(node, outputIndex) {
	return collectLinkedStageOutputCandidates(node, outputIndex)[0]?.value ?? "";
}

function buildLinkedStageOutputSnapshot(node) {
	return STAGE_OUTPUT_FIELD_KEYS.map((_key, index) => getLinkedStageOutputText(node, index));
}

function getCurrentStageOutputText(node, outputIndex) {
	const panelState = node?.[PANEL_KEY];
	const sessionValue = getStageOutputValueFromList(panelState?.lastExecutionOutputs, outputIndex);
	if (sessionValue) return sessionValue;
	const directCache = panelState?.directStageOutputCache;
	if (directCache && typeof directCache === "object" && !directCache._qwenStaleForCurrentRun) {
		const directValue = getDirectStageOutputValue(directCache, outputIndex);
		if (directValue) return directValue;
	}
	return "";
}

function isStageDisplayManuallyCleared(node) {
	const panelState = node?.[PANEL_KEY];
	if (!panelState) return false;
	const clearedAt = Number(panelState.displayClearedAt ?? 0) || 0;
	if (clearedAt <= 0) return false;
	const executedAt = Number(panelState.lastExecutedAt ?? 0) || 0;
	return executedAt <= 0 || clearedAt >= executedAt;
}

function getStageOutputEntry(node, outputIndex) {
	const panelState = node?.[PANEL_KEY];
	const previewSource = String(panelState?.displayPreviewSource ?? "").trim();
	const previewValue = getStageOutputValueFromList(panelState?.previewExecutionOutputs, outputIndex);
	if (previewSource && previewValue) {
		return { value: previewValue, source: previewSource, sourceKey: "preview" };
	}

	if (isStageDisplayManuallyCleared(node)) {
		const linkedValue = getLinkedStageOutputText(node, outputIndex);
		const clearedLinkedValue = getStageOutputValueFromList(panelState?.clearedLinkedOutputSnapshot, outputIndex);
		const clearedAt = Number(panelState?.displayClearedAt ?? 0) || 0;
		const queuedAfterClear = Number(panelState?.lastWorkflowQueueRequestedAt ?? 0) > clearedAt;
		if (linkedValue && (queuedAfterClear || linkedValue !== clearedLinkedValue)) {
			return { value: linkedValue, source: "下游文本节点", sourceKey: "linked-node-after-clear" };
		}
		return { value: "", source: "", sourceKey: "manual-clear" };
	}

	const currentValue = getStageOutputValueFromList(panelState?.lastExecutionOutputs, outputIndex);
	if (currentValue) {
		const cacheStatus = String(panelState?.directStageOutputCache?.status ?? "").trim().toLowerCase();
		return { value: currentValue, source: cacheStatus === "running" ? "实时生成中" : "本次执行", sourceKey: "session-cache" };
	}

	const directCache = panelState?.directStageOutputCache;
	if (directCache && typeof directCache === "object" && !directCache._qwenStaleForCurrentRun) {
		const directValue = getDirectStageOutputValue(directCache, outputIndex);
		if (directValue) {
			const cacheStatus = String(directCache?.status ?? "").trim().toLowerCase();
			return { value: directValue, source: cacheStatus === "running" ? "实时生成中" : "实时缓存", sourceKey: "direct-cache" };
		}
	}

	const workflowMetaOutputs = panelState?.workflowOutputMeta?.stageOutputs;
	if (shouldPreferWorkflowStageOutputMeta(node)) {
		const workflowValue = getStageOutputValueFromList(workflowMetaOutputs, outputIndex);
		if (workflowValue) return { value: workflowValue, source: "PNG 元数据", sourceKey: "workflow-meta-preferred" };
	}

	const latestHistoryStageOutput = getNodeLatestHistoryStageOutput(node);
	if (shouldPreferHistoryStageOutput(node)) {
		const historyValue = getHistoryStageOutputTextByIndex(latestHistoryStageOutput, outputIndex);
		if (historyValue) return { value: historyValue, source: "历史记录", sourceKey: "history-preferred" };
	}

	const hydratedValue = getStageOutputValueFromList(panelState?.hydratedExecutionOutputs, outputIndex);
	if (hydratedValue) {
		const hydratedSource = String(panelState?.hydratedExecutionSourceLabel ?? "").trim() || "持久化缓存";
		return { value: hydratedValue, source: hydratedSource, sourceKey: "hydrated" };
	}

	const linkedValue = getLinkedStageOutputText(node, outputIndex);
	if (linkedValue) return { value: linkedValue, source: "下游文本节点", sourceKey: "linked-node" };

	const workflowFallbackValue = getStageOutputValueFromList(workflowMetaOutputs, outputIndex);
	if (workflowFallbackValue) return { value: workflowFallbackValue, source: "PNG 元数据", sourceKey: "workflow-meta-fallback" };

	const historyFallbackValue = getHistoryStageOutputTextByIndex(latestHistoryStageOutput, outputIndex);
	if (historyFallbackValue) return { value: historyFallbackValue, source: "历史记录", sourceKey: "history-fallback" };

	return { value: "", source: "", sourceKey: "empty" };
}

function shouldPreferPersistedStageOutput(node) {
	const panelState = node?.[PANEL_KEY];
	const hasExecutedInSession = Number(panelState?.lastExecutedAt ?? 0) > 0;
	if (hasExecutedInSession) return false;
	const directCache = panelState?.directStageOutputCache;
	const cacheStatus = String(directCache?.status ?? "").trim().toLowerCase();
	if (cacheStatus === "running" || cacheStatus === "error") return false;
	return true;
}

function shouldPreferWorkflowStageOutputMeta(node) {
	const panelState = node?.[PANEL_KEY];
	const workflowMetaOutputs = panelState?.workflowOutputMeta?.stageOutputs;
	if (!Array.isArray(workflowMetaOutputs) || !workflowMetaOutputs.some((value) => String(value ?? "").trim())) {
		return false;
	}
	return shouldPreferPersistedStageOutput(node);
}

function getNodeLatestHistoryStageOutput(node) {
	const history = getNodeHistory(node);
	for (const item of history) {
		const stageOutput = getHistoryStageOutput(item);
		if (stageOutput) return stageOutput;
	}
	return null;
}

function getHistoryStageOutputTextByIndex(stageOutput, outputIndex) {
	if (!stageOutput || typeof stageOutput !== "object") return "";
	const values = buildStageOutputListFromSnapshot(stageOutput);
	return String(values[outputIndex] ?? "").trim();
}

function shouldPreferHistoryStageOutput(node) {
	const stageOutput = getNodeLatestHistoryStageOutput(node);
	if (!stageOutput) return false;
	return shouldPreferPersistedStageOutput(node);
}

function buildCompactHistoryJsonText(stageOutput) {
	const directText = String(stageOutput?.jsonResult ?? "").trim();
	if (directText) return directText;
	const compactPayload = compactHistoryJsonPayload(stageOutput?.jsonPayload);
	if (!compactPayload) return "";
	try {
		return JSON.stringify(compactPayload, null, 2);
	} catch (_error) {
		return "";
	}
}

function buildStageOutputListFromSnapshot(stageOutput) {
	if (!stageOutput || typeof stageOutput !== "object") return [];
	return [
		String(stageOutput.fullText ?? "").trim(),
		String(stageOutput.promptText ?? "").trim(),
		String(stageOutput.selectedTags ?? "").trim(),
		buildCompactHistoryJsonText(stageOutput),
		String(stageOutput.negativePrompt ?? "").trim(),
		String(stageOutput.promptCollection ?? "").trim(),
		String(stageOutput.smartText ?? "").trim(),
	];
}

function hydrateStageDisplayStateFromPersistedData(node) {
	const panelState = node?.[PANEL_KEY];
	if (!panelState) return false;
	if (isStageDisplayManuallyCleared(node)) return false;
	if (Array.isArray(panelState.lastExecutionOutputs) && panelState.lastExecutionOutputs.some((value) => String(value ?? "").trim())) {
		return true;
	}

	const latestHistoryStageOutput = getNodeLatestHistoryStageOutput(node);
	const historyOutputs = buildStageOutputListFromSnapshot(latestHistoryStageOutput);
	if (historyOutputs.some((value) => String(value ?? "").trim())) {
		panelState.hydratedExecutionOutputs = historyOutputs;
		panelState.hydratedExecutionSourceLabel = "历史记录";
		return true;
	}

	const workflowMetaOutputs = panelState.workflowOutputMeta?.stageOutputs;
	if (Array.isArray(workflowMetaOutputs) && workflowMetaOutputs.some((value) => String(value ?? "").trim())) {
		panelState.hydratedExecutionOutputs = workflowMetaOutputs.map((value) => String(value ?? ""));
		panelState.hydratedExecutionSourceLabel = "PNG 元数据";
		return true;
	}
	return false;
}

function applyStageOutputSnapshotToDisplay(node, stageOutput) {
	const panelState = node?.[PANEL_KEY];
	if (!panelState || !stageOutput || typeof stageOutput !== "object") return false;
	const outputs = buildStageOutputListFromSnapshot(stageOutput);
	if (!outputs.some((value) => String(value ?? "").trim())) return false;
	panelState.previewExecutionOutputs = outputs;
	panelState.displayPreviewSource = String(panelState.displayPreviewSource ?? "").trim() || "历史预览";
	refreshStageDisplay(node);
	return true;
}

function setStageDisplayPreview(node, stageOutput, source = "历史预览") {
	const panelState = node?.[PANEL_KEY];
	if (!panelState) return false;
	panelState.displayPreviewSource = String(source ?? "").trim() || "历史预览";
	return applyStageOutputSnapshotToDisplay(node, stageOutput);
}

function clearStageDisplayPreview(node) {
	const panelState = node?.[PANEL_KEY];
	if (!panelState) return;
	panelState.displayPreviewSource = "";
	panelState.previewExecutionOutputs = [];
}

function clearStageTerminalPreviewState(node, options = {}) {
	const panelState = node?.[PANEL_KEY];
	if (!panelState) return false;
	const clearedAt = Date.now();
	clearStageDisplayPreview(node);
	panelState.lastExecutionOutputs = [];
	panelState.directStageOutputCache = null;
	panelState.hydratedExecutionOutputs = [];
	panelState.hydratedExecutionSourceLabel = "";
	panelState.workflowOutputMeta = null;
	panelState.clearedLinkedOutputSnapshot = buildLinkedStageOutputSnapshot(node);
	panelState.displayClearedAt = clearedAt;
	markNodeWorkflowQueueRequested(node, clearedAt);
	setNodeWorkflowOutputMeta(node, null);
	if (options.clearSmartInput !== false) {
		setWidgetValue(node, "智能文本输入", "");
		setWidgetValue(node, "智能文本匹配", false);
	}
	refreshStageDisplay(node);
	return true;
}

function scheduleHydrateStageDisplayState(node, attempts = 6, delayMs = 80) {
	let remaining = Math.max(1, Number(attempts) || 1);
	const run = () => {
		if (!node || node[NODE_REMOVED_KEY]) return;
		const hydrated = hydrateStageDisplayStateFromPersistedData(node);
		if (hydrated) refreshStageDisplay(node);
		remaining -= 1;
		if (hydrated || remaining <= 0) return;
		setTimeout(run, Math.max(20, Number(delayMs) || 80));
	};
	setTimeout(run, Math.max(0, Number(delayMs) || 80));
}

function getStageOutputText(node, outputIndex) {
	return getStageOutputEntry(node, outputIndex).value ?? "";
}

function getStageJsonPayload(node) {
	const text = getStageOutputText(node, STAGE_OUTPUT_INDEX.jsonResult);
	if (!text) return null;
	try {
		const payload = JSON.parse(text);
		return payload && typeof payload === "object" ? payload : null;
	} catch {
		return null;
	}
}

function getStageDecisionState(node) {
	const payload = getStageJsonPayload(node);
	const library = node?.[PANEL_KEY]?.library ?? { slot_config: [], tag_library: {} };
	const state = collectNodeState(node, library);
	const settings = state?.settings ?? {};
	return {
		configuredRandom: String(settings["运行时随机模式"] ?? PRESET_SETTING_DEFAULTS["运行时随机模式"] ?? "自动判断").trim() || "自动判断",
		resolvedRandom: String(payload?.runtime_random_mode_resolved ?? "").trim(),
		configuredSmartPriority: String(settings["智能文本风格优先"] ?? PRESET_SETTING_DEFAULTS["智能文本风格优先"] ?? "自动判断").trim() || "自动判断",
		resolvedSmartPriority: String(payload?.smart_text_style_priority_resolved ?? "").trim(),
		resolvedSmartStyle: String(payload?.smart_text_style_resolved ?? "").trim(),
	};
}

function formatStageDecisionSummary(node) {
	const info = getStageDecisionState(node);
	if (!info.resolvedRandom && !info.resolvedSmartPriority && !info.resolvedSmartStyle) return "";
	const bits = [];
	if (info.configuredRandom) {
		bits.push(info.resolvedRandom ? `随机 ${info.configuredRandom}->${info.resolvedRandom}` : `随机 ${info.configuredRandom}`);
	}
	if (info.configuredSmartPriority) {
		const smartTail = info.resolvedSmartStyle ? `/${info.resolvedSmartStyle}` : "";
		bits.push(info.resolvedSmartPriority ? `智能 ${info.resolvedSmartPriority}${smartTail}` : `智能 ${info.configuredSmartPriority}`);
	}
	return bits.join(" | ");
}

function getStageNegativePromptText(node) {
	return getStageOutputText(node, STAGE_OUTPUT_INDEX.negativePrompt);
}

function getStageHistoryOutputSnapshot(node) {
	const fullText = String(getStageOutputText(node, STAGE_OUTPUT_INDEX.fullText) ?? "").trim();
	let promptText = String(getStagePromptOutputText(node) ?? "").trim();
	const selectedTags = String(getStageOutputText(node, STAGE_OUTPUT_INDEX.selectedTags) ?? "").trim();
	const jsonResult = String(getStageOutputText(node, STAGE_OUTPUT_INDEX.jsonResult) ?? "").trim();
	const negativePrompt = String(getStageNegativePromptText(node) ?? "").trim();
	const promptCollection = String(getStageOutputText(node, STAGE_OUTPUT_INDEX.promptCollection) ?? "").trim();
	const smartText = String(getStageOutputText(node, STAGE_OUTPUT_INDEX.smartText) ?? "").trim();
	if (!promptText) promptText = promptCollection || smartText || fullText;
	let jsonPayload = null;
	if (jsonResult) {
		try {
			jsonPayload = JSON.parse(jsonResult);
		} catch (_error) {}
	}
	return { fullText, promptText, selectedTags, jsonResult, negativePrompt, promptCollection, smartText, jsonPayload };
}

function hasUsableStageOutputSnapshot(stageOutput) {
	const normalized = normalizeHistoryStageOutputPayload(stageOutput) ?? stageOutput;
	if (!normalized || typeof normalized !== "object") return false;
	return [
		normalized.promptText,
		normalized.promptCollection,
		normalized.smartText,
		normalized.fullText,
		normalized.negativePrompt,
		normalized.selectedTags,
		normalized.jsonResult,
	].some((value) => normalizeStageTextValue(value).trim());
}

function getCurrentStageOutputSnapshot(node) {
	const snapshot = getStageHistoryOutputSnapshot(node);
	return hasUsableStageOutputSnapshot(snapshot) ? snapshot : null;
}

function pickHistoryStageTextField(source, keys) {
	if (!source || typeof source !== "object") return "";
	for (const key of keys) {
		const text = normalizeStageTextValue(source?.[key]).trim();
		if (text) return text;
	}
	return "";
}

function normalizeHistoryStageOutputPayload(output) {
	if (!output || typeof output !== "object") return null;
	const slots = extractStageOutputSlotsFromPayload(output);
	const jsonResult = pickHistoryStageTextField(output, ["jsonResult", "json_result", "json", "json_text"]) || String(slots[STAGE_OUTPUT_INDEX.jsonResult] ?? "").trim();
	let jsonPayload = output.jsonPayload ?? output.json_payload ?? null;
	if (!jsonPayload && jsonResult) {
		try {
			jsonPayload = JSON.parse(jsonResult);
		} catch (_error) {}
	}
	const normalized = {
		fullText: pickHistoryStageTextField(output, ["fullText", "full_text", "full", "resultText", "result_text"]) || String(slots[STAGE_OUTPUT_INDEX.fullText] ?? "").trim(),
		promptText: pickHistoryStageTextField(output, ["promptText", "prompt_text", "positivePrompt", "positive_prompt", "primaryPrompt", "primary_prompt", "promptOnly", "prompt_only", "prompt"]) || String(slots[STAGE_OUTPUT_INDEX.promptText] ?? "").trim(),
		selectedTags: pickHistoryStageTextField(output, ["selectedTags", "selected_tags", "selected_tags_text", "tagSummary", "tagsText", "tags_text"]) || String(slots[STAGE_OUTPUT_INDEX.selectedTags] ?? "").trim(),
		jsonResult,
		negativePrompt: pickHistoryStageTextField(output, ["negativePrompt", "negative_prompt", "negative", "negative_prompt_recommendation"]) || String(slots[STAGE_OUTPUT_INDEX.negativePrompt] ?? "").trim(),
		promptCollection: pickHistoryStageTextField(output, ["promptCollection", "prompt_collection", "promptOnly", "prompt_only", "prompt_texts", "prompts"]) || String(slots[STAGE_OUTPUT_INDEX.promptCollection] ?? "").trim(),
		smartText: pickHistoryStageTextField(output, ["smartText", "smart_text", "smartTextPrompt", "smart_text_prompt", "smartPrompt", "smart_prompt"]) || String(slots[STAGE_OUTPUT_INDEX.smartText] ?? "").trim(),
		styleTrack: pickHistoryStageTextField(output, ["styleTrack", "style_track", "runtime_random_style_track", "track"]),
		jsonPayload,
	};
	if (!normalized.promptText) {
		normalized.promptText = normalized.promptCollection || normalized.smartText || normalized.fullText;
	}
	if (!normalized.styleTrack && normalized.jsonPayload && typeof normalized.jsonPayload === "object") {
		normalized.styleTrack = String(normalized.jsonPayload.runtime_random_style_track ?? "").trim();
	}
	return Object.values(normalized).some((value) => typeof value === "string" ? value.trim() : !!value)
		? normalized
		: null;
}

const HISTORY_JSON_PAYLOAD_KEYS = new Set([
	"runtime_random_enabled",
	"runtime_random_mode_resolved",
	"runtime_random_style_track",
	"runtime_random_track",
	"runtime_random_profile",
	"runtime_random_generated_tags",
	"smart_text_style_priority_resolved",
	"smart_text_style_resolved",
	"random_theme_profile",
	"theme_pool_profile",
	"template_style",
]);

function truncateHistoryText(value, maxChars) {
	const text = String(value ?? "").trim();
	return text.length > maxChars ? text.slice(0, maxChars) : text;
}

function compactHistoryJsonPayload(payload) {
	if (!payload || typeof payload !== "object" || Array.isArray(payload)) return null;
	const result = {};
	for (const key of HISTORY_JSON_PAYLOAD_KEYS) {
		if (!Object.prototype.hasOwnProperty.call(payload, key)) continue;
		if (/dedupe_cache/iu.test(key)) continue;
		const value = payload[key];
		if (Array.isArray(value)) {
			result[key] = value.slice(0, 64).map((item) => truncateHistoryText(item, 256)).filter(Boolean);
		} else if (["string", "number", "boolean"].includes(typeof value)) {
			result[key] = typeof value === "string" ? truncateHistoryText(value, 1024) : value;
		}
	}
	return Object.keys(result).length ? result : null;
}

function compactHistoryStageOutputPayload(output) {
	const normalized = normalizeHistoryStageOutputPayload(output);
	if (!normalized) return null;
	const promptText = truncateHistoryText(normalized.promptText || normalized.promptCollection || normalized.smartText || normalized.fullText, 32768);
	const promptCollection = truncateHistoryText(normalized.promptCollection, 32768);
	const smartText = truncateHistoryText(normalized.smartText, 16384);
	const compact = {
		promptText,
		selectedTags: truncateHistoryText(normalized.selectedTags, 8192),
		negativePrompt: truncateHistoryText(normalized.negativePrompt, 16384),
		promptCollection: promptCollection && promptCollection !== promptText ? promptCollection : "",
		smartText: smartText && smartText !== promptText ? smartText : "",
		styleTrack: truncateHistoryText(normalized.styleTrack, 512),
		jsonPayload: compactHistoryJsonPayload(normalized.jsonPayload),
	};
	if (!promptText) compact.fullText = truncateHistoryText(normalized.fullText, 32768);
	return Object.values(compact).some((value) => typeof value === "string" ? value.trim() : !!value) ? compact : null;
}

function getHistoryStageOutput(item) {
	const candidates = [
		item?.meta?.stageOutput,
		item?.meta?.stage_output,
		item?.meta?.output,
		item?.meta?.outputs,
		item?.meta,
		item?.stageOutput,
		item?.stage_output,
		item?.output,
		item?.outputs,
		item,
	];
	for (const candidate of candidates) {
		const normalized = normalizeHistoryStageOutputPayload(candidate);
		if (normalized) return normalized;
	}
	return null;
}

function findRelatedHistoryStageOutput(node, item) {
	const ownOutput = getHistoryStageOutput(item);
	if (ownOutput) return ownOutput;
	const serialized = serializeState(item?.state);
	if (!serialized) return null;
	const itemUpdatedAt = Number(item?.updatedAt ?? 0) || 0;
	const history = getNodeHistory(node);
	const candidates = [];
	for (const other of history) {
		if (!other || other === item || String(other?.id ?? "") === String(item?.id ?? "")) continue;
		const stageOutput = getHistoryStageOutput(other);
		if (!stageOutput) continue;
		if (serializeState(other?.state) !== serialized) continue;
		const distance = itemUpdatedAt > 0 ? Math.abs((Number(other?.updatedAt ?? 0) || 0) - itemUpdatedAt) : 0;
		candidates.push({ stageOutput, distance, updatedAt: Number(other?.updatedAt ?? 0) || 0 });
	}
	candidates.sort((left, right) => left.distance - right.distance || right.updatedAt - left.updatedAt);
	return candidates[0]?.stageOutput ?? null;
}

function resolveHistoryPromptViewStageOutput(node, item) {
	const ownStageOutput = getHistoryStageOutput(item);
	if (hasUsableStageOutputSnapshot(ownStageOutput)) {
		return { stageOutput: ownStageOutput, sourceKey: "own" };
	}
	const relatedStageOutput = findRelatedHistoryStageOutput(node, item);
	if (hasUsableStageOutputSnapshot(relatedStageOutput)) {
		return { stageOutput: relatedStageOutput, sourceKey: "related" };
	}
	const liveStageOutput = getCurrentStageOutputSnapshot(node);
	if (hasUsableStageOutputSnapshot(liveStageOutput)) {
		return { stageOutput: liveStageOutput, sourceKey: "live" };
	}
	return { stageOutput: null, sourceKey: "legacy" };
}

function attachStageOutputToRecentStateHistory(node, currentState, stageOutput) {
	if (!node || !stageOutput?.promptText) return false;
	const compactStageOutput = compactHistoryStageOutputPayload(stageOutput);
	if (!compactStageOutput?.promptText) return false;
	const serialized = serializeState(currentState);
	if (!serialized) return false;
	const attachableSources = new Set(["random", "manual-apply", "example", "preset-load", "history-load", "nsfw-workspace", "nsfw-workspace-disabled", "arrange-preview"]);
	const history = getNodeHistory(node);
	let changed = false;
	const nextHistory = history.map((item, index) => {
		if (changed || index > 12 || !item || typeof item !== "object") return item;
		if (!attachableSources.has(String(item.source ?? ""))) return item;
		if (getHistoryStageOutput(item)) return item;
		if (serializeState(item.state) !== serialized) return item;
		changed = true;
		return {
			...item,
			meta: {
				...cloneJsonSafe(item.meta, {}),
				stageOutput: compactStageOutput,
			},
		};
	});
	if (changed) setNodeHistory(node, nextHistory);
	return changed;
}

function buildHistoryDisplaySummaryText(item) {
	const fallback = String(item?.summary ?? summarizeHistoryState(item?.state ?? {})).trim();
	const stageOutput = getHistoryStageOutput(item);
	const styleTrack = String(stageOutput?.styleTrack ?? stageOutput?.runtime_random_style_track ?? stageOutput?.jsonPayload?.runtime_random_style_track ?? "").trim();
	const promptText = String(stageOutput?.promptText || stageOutput?.promptCollection || "").replace(/\s+/gu, " ").trim();
	if (promptText) return styleTrack ? `[轨道:${styleTrack}] ${promptText}` : promptText;
	const smartText = String(stageOutput?.smartText ?? "").replace(/\s+/gu, " ").trim();
	if (smartText) return styleTrack ? `[轨道:${styleTrack}] ${smartText}` : smartText;
	return fallback;
}

function hasHistoryStageOutput(item) {
	const output = getHistoryStageOutput(item);
	return !!(output?.promptText || output?.promptCollection || output?.smartText || output?.negativePrompt || output?.selectedTags || output?.fullText || output?.jsonResult);
}

function buildHistoryStageOutputText(stageOutput) {
	if (!stageOutput) return "";
	const lines = ["【QwenTE 本次生成提示词】"];
	const styleTrack = String(stageOutput?.styleTrack ?? stageOutput?.runtime_random_style_track ?? stageOutput?.jsonPayload?.runtime_random_style_track ?? "").trim();
	if (styleTrack) lines.push("", `当前轨道：${styleTrack}`);
	if (stageOutput.promptText) lines.push("", "正向提示词：", stageOutput.promptText);
	if (stageOutput.promptCollection && stageOutput.promptCollection !== stageOutput.promptText) lines.push("", "正向提示词合集：", stageOutput.promptCollection);
	if (stageOutput.smartText) lines.push("", "智能文本：", stageOutput.smartText);
	if (stageOutput.negativePrompt) lines.push("", "推荐负面词：", stageOutput.negativePrompt);
	if (stageOutput.selectedTags) lines.push("", "标签与参数摘要：", stageOutput.selectedTags);
	if (!stageOutput.promptText && stageOutput.fullText) lines.push("", "结果全文：", stageOutput.fullText);
	return lines.join("\n").trim();
}

function buildHistoryPromptViewText(item, fallbackStageOutput = null) {
	const stageOutput = getHistoryStageOutput(item) ?? normalizeHistoryStageOutputPayload(fallbackStageOutput);
	const stageText = buildHistoryStageOutputText(stageOutput);
	if (stageText) return stageText;
	const summary = buildHistoryDisplaySummaryText(item);
	const stateSummary = summarizeHistoryState(item?.state ?? {});
	const lines = ["【QwenTE 历史记录摘要】"];
	lines.push("", `来源：${getHistorySourceLabel(item?.source)}`);
	if (summary) lines.push("", "摘要：", summary);
	if (stateSummary && stateSummary !== summary) lines.push("", "标签状态：", stateSummary);
	lines.push("", "提示：这条历史没有保存完整生成提示词，只能查看当时的标签与状态摘要。");
	return lines.join("\n").trim();
}

function getStageDisplayPayload(node, modeKey) {
	const activeMode = STAGE_DISPLAY_MODES.find((item) => item.key === modeKey) ?? STAGE_DISPLAY_MODES[0];
	const panelState = node?.[PANEL_KEY];
	const directCache = panelState?.directStageOutputCache;
	const cacheStatus = String(directCache?.status ?? "");
	const preferWorkflowMeta = shouldPreferWorkflowStageOutputMeta(node);
	const runningSource = cacheStatus === "running" ? "实时生成中" : activeMode.source;
	const errorText = cacheStatus === "error" ? String(directCache?.error ?? directCache?.prompt_text ?? "阶段提示词生成失败。") : "";
	const outputIndex = activeMode.key === "negative"
		? STAGE_OUTPUT_INDEX.negativePrompt
		: activeMode.key === "tags"
			? STAGE_OUTPUT_INDEX.selectedTags
			: activeMode.key === "json"
				? STAGE_OUTPUT_INDEX.jsonResult
				: activeMode.key === "smart"
					? STAGE_OUTPUT_INDEX.smartText
					: STAGE_OUTPUT_INDEX.promptText;
	const entry = getStageOutputEntry(node, outputIndex);
	const stableSource = entry.source || (preferWorkflowMeta ? "PNG 元数据" : activeMode.source);
	if (activeMode.key === "blocks") {
		if (errorText) return { text: errorText, empty: false, source: "生成失败", state: readTagBlockComposerState(node) };
		return getTagBlockComposerPayloadForDisplay(node, activeMode, cacheStatus, runningSource);
	}
	if (activeMode.key === "negative") {
		const text = entry.value;
		if (errorText) return { text: errorText, empty: false, source: "生成失败" };
		return { text: text || (cacheStatus === "running" ? "正在生成中，推荐负面词会在主提示词稳定后出现。" : "还没有推荐负面词。请先运行一次节点。"), empty: !text, source: text ? (cacheStatus === "running" ? runningSource : stableSource) : cacheStatus === "running" ? "实时生成中" : "等待输出" };
	}
	if (activeMode.key === "tags") {
		const text = entry.value;
		if (errorText) return { text: errorText, empty: false, source: "生成失败" };
		return { text: text || (cacheStatus === "running" ? "正在生成中，标签摘要会在结果整理后出现。" : "当前没有可显示的标签输出。若工作流未桥接这一槽位，这是正常现象。"), empty: !text, source: text ? (cacheStatus === "running" ? runningSource : stableSource) : cacheStatus === "running" ? "实时生成中" : "暂无标签输出" };
	}
	if (activeMode.key === "json") {
		const raw = entry.value;
		let text = raw;
		if (raw) {
			try {
				text = JSON.stringify(JSON.parse(raw), null, 2);
			} catch (_error) {}
		}
		if (errorText) return { text: errorText, empty: false, source: "生成失败" };
		return { text: text || (cacheStatus === "running" ? "正在生成中，JSON 结果会在最终整理完成后出现。" : "当前没有可显示的 JSON 输出。若工作流未桥接这一槽位，这是正常现象。"), empty: !text, source: text ? (cacheStatus === "running" ? runningSource : stableSource) : cacheStatus === "running" ? "实时生成中" : "暂无 JSON 输出" };
	}
	if (activeMode.key === "smart") {
		const text = entry.value;
		if (errorText) return { text: errorText, empty: false, source: "生成失败" };
		return { text: text || (cacheStatus === "running" ? "正在生成智能文本..." : "还没有智能文本。切到“智能文本”，输入一句描述后点“匹配启用”。"), empty: !text, source: text ? (cacheStatus === "running" ? runningSource : stableSource) : cacheStatus === "running" ? "实时生成中" : "等待匹配" };
	}
	const text = entry.value;
	if (errorText) return { text: errorText, empty: false, source: "生成失败" };
	return { text: text || (cacheStatus === "running" ? "正在生成阶段提示词..." : "还没有正向提示词。请点击 ComfyUI 运行按钮，或用“随机跑 / 匹配启用”自动入队。"), empty: !text, source: text ? (cacheStatus === "running" ? runningSource : stableSource) : cacheStatus === "running" ? "实时生成中" : "等待输出" };
}

function computeStageTextMetrics(text) {
	const raw = String(text ?? "");
	const trimmed = raw.trim();
	const lines = trimmed ? trimmed.split(/\n+/u).filter(Boolean) : [];
	return {
		chars: raw.length,
		lines: lines.length || (trimmed ? 1 : 0),
	};
}

function formatStageOutputForReading(text, modeKey) {
	const raw = String(text ?? "");
	if (!raw.trim()) return raw;
	if (modeKey === "json") return raw;

	let next = raw.replace(/\r\n/gu, "\n");
	if (modeKey === "smart") {
		next = next
			.replace(/(^|[^\n])((?:主体|场景|动作|光影|镜头|画质|构图|服装|表情|氛围|提示词)\s*[:：])/gu, "$1\n$2")
			.replace(/(^|[^\n])((?:成年女性|年轻成年女性|人物主体|书店里的年轻成年女性|杂志感人像))/gu, "$1\n$2")
			.replace(/(^|[^\n])((?:近景|中景半身|全身|面部聚焦|镜头近距离|85mm人像镜头|35mm镜头))/gu, "$1\n$2")
			.replace(/(^|[^\n])((?:杂志感|电影感|封面感|高细节|柔和高光|霓虹夜色|浴室蒸汽|湿发))/gu, "$1\n$2")
			.replace(/，(?=\s*(?:成年女性|年轻成年女性|人物主体|杂志感人像|近景|中景半身|全身|面部聚焦|镜头近距离|85mm人像镜头|35mm镜头|霓虹夜色|浴室蒸汽|湿发))/gu, "，\n");
	}
	if (modeKey === "prompt" || modeKey === "negative" || modeKey === "smart") {
		next = next
			.replace(/,\s+/gu, ",\n")
			.replace(/，\s*/gu, "，\n")
			.replace(/;\s*/gu, ";\n")
			.replace(/；\s*/gu, "；\n");
	}
	if (modeKey === "tags") {
		next = next
			.replace(/(^|[^\n])(模板风格：|主体类型：|案例输出结构：|请求生成数量：|实际生成数量：|运行时随机标签：|运行时随机模式：|核心标签锁定数量：|运行时随机强度：|优先柔和肤质：|抑制文字伪影：|锁定标签白名单：|随机排除标签：|推荐负面词：)/gu, "$1\n$2")
			.replace(/\n{3,}/gu, "\n\n");
	}
	return next.trim();
}

function setStageDisplaySourceText(target, value) {
	if (!target?.sourceEl) return;
	const text = String(value ?? "");
	target.sourceEl.textContent = text;
	target.sourceEl.title = text;
}

function renderStageDisplayTarget(node, target, modeKey) {
	if (!target?.bodyEl) return;
	const payload = getStageDisplayPayload(node, modeKey);
	const bodyEl = target.bodyEl;
	const viewMode = String(target.viewMode ?? "readable");
	const displayText = viewMode === "raw" ? payload.text : formatStageOutputForReading(payload.text, modeKey);
	const metrics = computeStageTextMetrics(payload.text);
	if (modeKey === "smart" && target.inlineSmart !== false) {
		renderInlineSmartTextDisplay(node, bodyEl, payload, displayText);
		setStageDisplaySourceText(target, payload.source);
		for (const [key, button] of target.tabButtons ?? []) button.classList.toggle("is-active", key === modeKey);
		return;
	}
	if (modeKey === "blocks" && target.inlineBlocks !== false) {
		if (bodyEl.__qwenSmartUi) delete bodyEl.__qwenSmartUi;
		bodyEl.classList.remove("qwen-te-panel__display-screen--smart");
		renderInlineTagBlockComposer(node, bodyEl, payload);
		setStageDisplaySourceText(target, payload.source);
		for (const [key, button] of target.tabButtons ?? []) button.classList.toggle("is-active", key === modeKey);
		return;
	}
	bodyEl.classList.remove("qwen-te-panel__display-screen--smart");
	bodyEl.classList.remove("qwen-te-panel__display-screen--blocks");
	if (bodyEl.__qwenSmartUi) delete bodyEl.__qwenSmartUi;
	const previousTop = bodyEl.scrollTop;
	const previousHeight = bodyEl.scrollHeight;
	const followTail = previousHeight - previousTop - bodyEl.clientHeight <= 24;
	if (bodyEl.textContent !== displayText) {
		bodyEl.textContent = displayText;
		if (followTail) bodyEl.scrollTop = bodyEl.scrollHeight;
		else bodyEl.scrollTop = Math.max(0, previousTop + Math.max(0, bodyEl.scrollHeight - previousHeight));
	}
	bodyEl.classList.toggle("is-empty", !!payload.empty);
	if (target.sourceEl) {
		const decisionSummary = formatStageDecisionSummary(node);
		setStageDisplaySourceText(target, decisionSummary ? `${payload.source} · ${decisionSummary}` : payload.source);
	}
	if (target.metricsEl) {
		target.metricsEl.replaceChildren();
		const metricItems = [
			`字数 ${metrics.chars}`,
			`段数 ${metrics.lines}`,
			viewMode === "raw" ? "视图 原文" : "视图 阅读",
		];
		for (const text of metricItems) {
			const metric = document.createElement("div");
			metric.className = "qwen-te-modal__stage-output-metric";
			metric.textContent = text;
			target.metricsEl.appendChild(metric);
		}
	}
	for (const [key, button] of target.tabButtons ?? []) {
		button.classList.toggle("is-active", key === modeKey);
	}
	for (const [key, button] of target.viewTabButtons ?? []) {
		button.classList.toggle("is-active", key === viewMode);
	}
}

function refreshStageDisplay(node) {
	const panelState = node?.[PANEL_KEY];
	if (!panelState) return;
	const activeMode = panelState.displayMode ?? STAGE_DISPLAY_MODES[0]?.key ?? "prompt";
	renderStageDisplayTarget(node, {
		bodyEl: panelState.displayBodyEl,
		sourceEl: panelState.displaySourceEl,
		tabButtons: panelState.displayTabButtons,
		viewMode: "readable",
	}, activeMode);
	renderStageDisplayTarget(node, {
		bodyEl: panelState.expandedDisplayBodyEl,
		sourceEl: panelState.expandedDisplaySourceEl,
		tabButtons: panelState.expandedDisplayTabButtons,
		metricsEl: panelState.expandedDisplayMetricsEl,
		viewTabButtons: panelState.expandedDisplayViewTabButtons,
		viewMode: panelState.expandedDisplayViewMode ?? "readable",
	}, activeMode);
}

function openStageOutputDialog(node) {
	const panelState = node?.[PANEL_KEY];
	if (!panelState) return;
	if (panelState.expandedDisplayOverlay?.isConnected) {
		refreshStageDisplay(node);
		return;
	}
	const overlay = document.createElement("div");
	overlay.className = "qwen-te-modal";
	overlay.dataset.qwenModal = "stage-output";
	overlay.__qwenNode = node;
	const dialog = document.createElement("div");
	dialog.className = "qwen-te-modal__dialog";
	overlay.appendChild(dialog);
	const header = document.createElement("div");
	header.className = "qwen-te-modal__header";
	dialog.appendChild(header);
	const titleWrap = document.createElement("div");
	header.appendChild(titleWrap);
	const title = document.createElement("div");
	title.className = "qwen-te-modal__title";
	title.textContent = "输出窗口 · 展开查看";
	titleWrap.appendChild(title);
	const subtitle = document.createElement("div");
	subtitle.className = "qwen-te-modal__subtitle";
	subtitle.textContent = "长段内容在这里独立滚动，节点本体保持紧凑。";
	titleWrap.appendChild(subtitle);
	const closeButton = document.createElement("button");
	closeButton.type = "button";
	closeButton.className = "qwen-te-modal__close";
	closeButton.textContent = "关闭";
	header.appendChild(closeButton);
	const body = document.createElement("div");
	body.className = "qwen-te-modal__body qwen-te-modal__stage-output-body";
	dialog.appendChild(body);
	const toolbar = document.createElement("div");
	toolbar.className = "qwen-te-modal__stage-output-toolbar";
	body.appendChild(toolbar);
	const toolbarMain = document.createElement("div");
	toolbarMain.className = "qwen-te-modal__stage-output-toolbar-main";
	toolbar.appendChild(toolbarMain);
	const source = document.createElement("div");
	source.className = "qwen-te-modal__stage-output-source";
	source.textContent = "等待输出";
	toolbarMain.appendChild(source);
	const tabs = document.createElement("div");
	tabs.className = "qwen-te-modal__stage-output-tabs";
	toolbarMain.appendChild(tabs);
	const toolbarSide = document.createElement("div");
	toolbarSide.className = "qwen-te-modal__stage-output-toolbar-side";
	toolbar.appendChild(toolbarSide);
	const metrics = document.createElement("div");
	metrics.className = "qwen-te-modal__stage-output-metrics";
	toolbarSide.appendChild(metrics);
	const viewTabs = document.createElement("div");
	viewTabs.className = "qwen-te-modal__stage-output-view-tabs";
	toolbarSide.appendChild(viewTabs);
	const screen = document.createElement("div");
	screen.className = "qwen-te-modal__stage-output-screen is-empty";
	screen.textContent = "这里会显示最近一次节点输出。";
	body.appendChild(screen);
	const footer = document.createElement("div");
	footer.className = "qwen-te-modal__stage-output-footer";
	body.appendChild(footer);
	const note = document.createElement("div");
	note.className = "qwen-te-modal__stage-output-note";
	note.textContent = "支持实时更新；切换标签会和节点里的输出窗口保持同步，可一键复制当前页签内容。";
	footer.appendChild(note);
	const actions = document.createElement("div");
	actions.className = "qwen-te-modal__stage-output-actions";
	footer.appendChild(actions);
	const copyButton = document.createElement("button");
	copyButton.type = "button";
	copyButton.className = "qwen-te-modal__footer-button qwen-te-modal__footer-button--primary";
	copyButton.textContent = "复制当前页签";
	actions.appendChild(copyButton);
	const copyRawButton = document.createElement("button");
	copyRawButton.type = "button";
	copyRawButton.className = "qwen-te-modal__footer-button";
	copyRawButton.textContent = "复制原文";
	actions.appendChild(copyRawButton);
	const doneButton = document.createElement("button");
	doneButton.type = "button";
	doneButton.className = "qwen-te-modal__footer-button";
	doneButton.textContent = "关闭";
	actions.appendChild(doneButton);
	const tabButtons = new Map();
	const viewTabButtons = new Map();
	for (const mode of STAGE_DISPLAY_MODES) {
		const button = document.createElement("button");
		button.type = "button";
		button.className = "qwen-te-modal__stage-output-tab";
		button.textContent = mode.label;
		button.addEventListener("click", (event) => {
			event.stopPropagation();
			if (!node[PANEL_KEY]) return;
			node[PANEL_KEY].displayMode = mode.key;
			refreshStageDisplay(node);
		});
		tabs.appendChild(button);
		tabButtons.set(mode.key, button);
	}
	for (const view of [
		{ key: "readable", label: "阅读" },
		{ key: "raw", label: "原文" },
	]) {
		const button = document.createElement("button");
		button.type = "button";
		button.className = "qwen-te-modal__stage-output-view-tab";
		button.textContent = view.label;
		button.addEventListener("click", (event) => {
			event.stopPropagation();
			if (!node[PANEL_KEY]) return;
			node[PANEL_KEY].expandedDisplayViewMode = view.key;
			refreshStageDisplay(node);
		});
		viewTabs.appendChild(button);
		viewTabButtons.set(view.key, button);
	}
	const disposeStageOutput = () => {
		const state = node?.[PANEL_KEY];
		if (state?.expandedDisplayOverlay === overlay) {
			state.expandedDisplayOverlay = null;
			state.expandedDisplayBodyEl = null;
			state.expandedDisplaySourceEl = null;
			state.expandedDisplayTabButtons = null;
			state.expandedDisplayMetricsEl = null;
			state.expandedDisplayViewTabButtons = null;
		}
	};
	overlay.__qwenDispose = disposeStageOutput;
	const close = () => disposeModalOverlay(overlay);
	copyButton.addEventListener("click", async (event) => {
		event.stopPropagation();
		const activeMode = node?.[PANEL_KEY]?.displayMode ?? STAGE_DISPLAY_MODES[0]?.key ?? "prompt";
		const payload = getStageDisplayPayload(node, activeMode);
		if (!payload.text) {
			note.textContent = "当前没有可复制的输出。";
			return;
		}
		const ok = await copyToClipboard(payload.text);
		note.textContent = ok ? `已复制当前${STAGE_DISPLAY_MODES.find((item) => item.key === activeMode)?.label ?? "输出"}内容。` : "复制失败，浏览器可能阻止了剪贴板访问。";
	});
	copyRawButton.addEventListener("click", async (event) => {
		event.stopPropagation();
		const activeMode = node?.[PANEL_KEY]?.displayMode ?? STAGE_DISPLAY_MODES[0]?.key ?? "prompt";
		const payload = getStageDisplayPayload(node, activeMode);
		if (!payload.text) {
			note.textContent = "当前没有可复制的原文。";
			return;
		}
		const ok = await copyToClipboard(payload.text);
		note.textContent = ok ? "已复制当前页签原文。" : "复制失败，浏览器可能阻止了剪贴板访问。";
	});
	doneButton.addEventListener("click", close);
	closeButton.addEventListener("click", close);
	overlay.addEventListener("click", (event) => { if (event.target === overlay) close(); });
	panelState.expandedDisplayOverlay = overlay;
	panelState.expandedDisplayBodyEl = screen;
	panelState.expandedDisplaySourceEl = source;
	panelState.expandedDisplayTabButtons = tabButtons;
	panelState.expandedDisplayMetricsEl = metrics;
	panelState.expandedDisplayViewTabButtons = viewTabButtons;
	document.body.appendChild(overlay);
	refreshStageDisplay(node);
}

function findNegativeClipTextEncodeNode(sourceNode) {
	const nodes = app.graph?._nodes ?? [];
	const candidates = nodes.filter((node) => String(node?.type ?? "") === "CLIPTextEncode");
	const linkedClipsFromOutput = (outputIndex) => {
		const linked = [];
		for (const linkId of sourceNode?.outputs?.[outputIndex]?.links ?? []) {
			const link = app.graph?.links?.[linkId];
			const targetNode = link ? app.graph?.getNodeById?.(link.target_id) : null;
			if (String(targetNode?.type ?? "") === "CLIPTextEncode" && !linked.includes(targetNode)) linked.push(targetNode);
		}
		return linked;
	};
	const directlyLinkedNegative = linkedClipsFromOutput(STAGE_OUTPUT_INDEX.negativePrompt);
	if (directlyLinkedNegative.length === 1) return directlyLinkedNegative[0];
	if (directlyLinkedNegative.length > 1) return null;
	const sourceKs = new Set();
	for (const positiveClip of linkedClipsFromOutput(STAGE_OUTPUT_INDEX.promptText)) {
		for (const linkId of positiveClip?.outputs?.[0]?.links ?? []) {
			const link = app.graph?.links?.[linkId];
			const targetNode = link ? app.graph?.getNodeById?.(link.target_id) : null;
			if (String(targetNode?.type ?? "") === "KSampler" && Number(link.target_slot) === 1) {
				sourceKs.add(String(link.target_id));
			}
		}
	}
	const sameWorkflowNegative = candidates.filter((node) => {
		const output = node?.outputs?.[0];
		if (!output?.links?.length) return false;
		return output.links.some((linkId) => {
			const link = app.graph?.links?.[linkId];
			return link && sourceKs.has(String(link.target_id)) && Number(link.target_slot) === 2;
		});
	});
	if (sameWorkflowNegative.length === 1) return sameWorkflowNegative[0];
	if (sameWorkflowNegative.length > 1) return null;
	const directNegative = candidates.filter((node) => {
		const output = node?.outputs?.[0];
		if (!output?.links?.length) return false;
		return output.links.some((linkId) => {
			const link = app.graph?.links?.[linkId];
			return link && String(app.graph.getNodeById?.(link.target_id)?.type ?? "") === "KSampler" && Number(link.target_slot) === 2;
		});
	});
	if (directNegative.length === 1) return directNegative[0];
	if (!directNegative.length && candidates.length === 1) return candidates[0];
	return null;
}

function syncNegativePromptToGraph(node, negativeText, targetNode = null) {
	const normalized = String(negativeText ?? "").trim();
	if (!normalized) return { ok: false, reason: "empty" };
	const resolvedTargetNode = targetNode ?? findNegativeClipTextEncodeNode(node);
	if (!resolvedTargetNode) return { ok: false, reason: "not_found" };
	const currentText = String(getWidget(resolvedTargetNode, "text")?.value ?? "").trim();
	if (currentText === normalized) return { ok: true, reason: "unchanged", targetNode: resolvedTargetNode };
	setWidgetValue(resolvedTargetNode, "text", normalized);
	app.graph?.setDirtyCanvas?.(true, true);
	return { ok: true, targetNode: resolvedTargetNode };
}

function autoSyncStageNegativePrompt(node) {
	if (!getNodeAutoNegativeSyncEnabled(node)) return { ok: false, reason: "disabled" };
	return syncNegativePromptToGraph(node, getStageNegativePromptText(node));
}

function syncRawWidgetOptions(node, library) {
	for (const group of library.slot_config ?? []) {
		const values = ["无", ...flattenUniqueTags(library.tag_library?.[group.name])];
		for (let index = 1; index <= getTagGroupSlotLimit(library, group.name); index += 1) {
			const widget = getWidget(node, `${group.name}标签${index}`);
			if (!widget) continue;
			widget.options = widget.options ?? {};
			widget.options.values = values;
			if (widget.value == null || (values.length && !values.includes(widget.value))) setWidgetValue(node, widget.name, "无");
		}
	}
}

function sanitizeStagePromptNode(node, library) {
	const comboDefaults = {
		"模型来源": "仅Skill",
		"内置模型系列": "Qwen3.5-VL",
		"内置主模型": "",
		"内置视觉投影mmproj": "无",
		"内置KV缓存K类型": "默认(F16)",
		"内置KV缓存V类型": "默认(F16)",
		"API服务商": "OpenAI兼容",
		"模板风格": "自动",
		"主体类型": "自动",
		"案例输出结构": "自动",
		"运行时随机模式": "自动判断",
		"运行时随机强度": "中",
		"随机主题池": "自动",
		"提示词语言": "纯中文",
		"详细度": "标准",
		"输出模式": "完整结果",
		"标签反推模式": "自动平衡",
		"风格隔离策略": "平衡收敛",
		"智能文本风格优先": "自动判断",
		"图片反推模式": "角色设定图",
	};
	const boolDefaults = { "内置启用思考": false, "运行时随机标签": false, "优先柔和肤质": false, "抑制文字伪影": false, "图片反推生成": false, "智能文本匹配": false, [TAG_BLOCK_COMPOSER_ENABLED_WIDGET_NAME]: false, "输出think块": false };
	const intDefaults = {
		"内置上下文长度": { defaultValue: 8192, min: 1024, max: 327680 },
		"内置GPU层数": { defaultValue: -1, min: -1, max: 9999 },
		"API超时秒": { defaultValue: 120, min: 5, max: 600 },
		"图片反推最大边长": { defaultValue: 960, min: 256, max: 2048 },
		"核心标签锁定数量": { defaultValue: 10, min: 0, max: 500 },
		"生成数量": { defaultValue: 3, min: 1, max: 20 },
		"最大生成token": { defaultValue: 1800, min: 128, max: 8192 },
		"top_k": { defaultValue: 40, min: 0, max: 200 },
		"seed": { defaultValue: 0, min: 0, max: 0xffffffffffffffff },
	};
	const floatDefaults = { "温度": { defaultValue: 0.62, min: 0, max: 2 }, "top_p": { defaultValue: 0.9, min: 0, max: 1 }, "重复惩罚": { defaultValue: 1.08, min: 0.5, max: 2 }, "频率惩罚": { defaultValue: 0, min: 0, max: 2 }, "存在惩罚": { defaultValue: 0, min: 0, max: 2 } };
	for (const [name, defaultValue] of Object.entries(comboDefaults)) {
		const widget = getWidget(node, name);
		if (!widget) continue;
		const allowed = Array.isArray(widget?.options?.values) ? widget.options.values : [];
		const fallbackValue = allowed.includes(defaultValue) ? defaultValue : (allowed[0] ?? defaultValue);
		const normalizedValue = normalizeStageWidgetValue(name, widget.value);
		if (normalizedValue !== widget.value) {
			setWidgetValue(node, name, normalizedValue);
			continue;
		}
		if (allowed.length && !allowed.includes(widget.value)) setWidgetValue(node, name, fallbackValue);
	}
	for (const [name, defaultValue] of Object.entries(boolDefaults)) {
		const widget = getWidget(node, name);
		if (!widget) continue;
		const nextValue = widget.value == null ? defaultValue : !!widget.value;
		if (!Object.is(widget.value, nextValue)) setWidgetValue(node, name, nextValue);
	}
	for (const [name, rule] of Object.entries(intDefaults)) {
		const widget = getWidget(node, name);
		if (!widget) continue;
		let value = Number(widget.value);
		if (!Number.isFinite(value)) value = rule.defaultValue;
		const nextValue = Math.max(rule.min, Math.min(rule.max, Math.trunc(value)));
		if (!Object.is(widget.value, nextValue)) setWidgetValue(node, name, nextValue);
	}
	for (const [name, rule] of Object.entries(floatDefaults)) {
		const widget = getWidget(node, name);
		if (!widget) continue;
		let value = Number(widget.value);
		if (!Number.isFinite(value)) value = rule.defaultValue;
		const nextValue = Math.max(rule.min, Math.min(rule.max, value));
		if (!Object.is(widget.value, nextValue)) setWidgetValue(node, name, nextValue);
	}
	const apiModelWidget = getWidget(node, "API模型");
	if (apiModelWidget && isLikelyStaleApiModelValue(apiModelWidget.value)) setWidgetValue(node, apiModelWidget.name, "");
	for (const group of library.slot_config ?? []) {
		for (let index = 1; index <= getTagGroupSlotLimit(library, group.name); index += 1) {
			const widget = getWidget(node, `${group.name}标签${index}`);
			if (widget && widget.value == null) setWidgetValue(node, widget.name, "无");
		}
	}
}

function randomItem(items) { return items?.length ? items[Math.floor(Math.random() * items.length)] : null; }
function chance(probability) { return Math.random() < probability; }
function intensityChance(intensity, weak, medium, strong) { return intensity === "弱" ? weak : (intensity === "强" || intensity === "强 / 极限拉开") ? strong : medium; }
function addUniqueTag(target, tag) { if (tag && !target.includes(tag)) target.push(tag); }
function shouldSkipRandomTag(tag, whitelistSet, excludeSet) { return excludeSet.has(tag) && !whitelistSet.has(tag); }

function cloneSelectedWithLimit(selected, library, limit) {
	const next = Object.fromEntries((library.slot_config ?? []).map((group) => [group.name, []]));
	if (!selected || limit <= 0) return next;
	let used = 0;
	for (const group of library.slot_config ?? []) {
		for (const tag of selected[group.name] ?? []) {
			if (used >= limit) return next;
			next[group.name].push(tag);
			used += 1;
		}
	}
	return next;
}

function cloneCoreStateWithLimit(currentState, library, limit, whitelist = [], excludeSet = new Set()) {
	const selected = Object.fromEntries((library.slot_config ?? []).map((group) => [group.name, []]));
	const customTags = [];
	const whitelistSet = new Set(whitelist ?? []);
	const mapping = buildTagGroupIndex(library);
	let used = 0;

	const canKeep = (tag) => !excludeSet.has(tag) || whitelistSet.has(tag);
	const pushCustom = (tag) => {
		if (tag && !customTags.includes(tag)) customTags.push(tag);
	};

	if (limit > 0) {
		for (const group of library.slot_config ?? []) {
			for (const tag of currentState?.selected?.[group.name] ?? []) {
				if (used >= limit) break;
				if (!canKeep(tag)) continue;
				if (!selected[group.name].includes(tag)) {
					selected[group.name].push(tag);
					used += 1;
				}
			}
			if (used >= limit) break;
		}

		if (used < limit) {
			for (const tag of currentState?.customTags ?? []) {
				if (used >= limit) break;
				if (!canKeep(tag)) continue;
				pushCustom(tag);
				used += 1;
			}
		}
	}

	for (const tag of whitelist ?? []) {
		if (!tag) continue;
		const groupName = mapping.get(tag);
		if (!groupName) {
			pushCustom(tag);
			continue;
		}
		const groupConfig = (library.slot_config ?? []).find((group) => group.name === groupName);
		if (!groupConfig) {
			pushCustom(tag);
			continue;
		}
		if ((selected[groupName] ?? []).includes(tag)) continue;
		if ((selected[groupName] ?? []).length < Number(groupConfig.slots ?? 0)) selected[groupName].push(tag);
		else pushCustom(tag);
	}

	return { selected, customTags };
}

function hasAdultIntent(state, library) {
	const adultTags = flattenUniqueTags(library.tag_library?.["成人向表达"]);
	const adultSet = new Set(adultTags);
	return (state.selected?.["成人向表达"] ?? []).some((tag) => adultSet.has(tag))
		|| (state.customTags ?? []).some((tag) => adultSet.has(tag));
}

function buildTagGroupIndex(library) {
	const mapping = new Map();
	for (const group of library.slot_config ?? []) {
		for (const tag of flattenUniqueTags(library.tag_library?.[group.name])) if (!mapping.has(tag)) mapping.set(tag, group.name);
	}
	return mapping;
}

function collectNodeState(node, library) {
	const selected = {};
	for (const group of library.slot_config ?? []) {
		const tags = [];
		for (let index = 1; index <= getTagGroupSlotLimit(library, group.name); index += 1) {
			const value = String(getWidget(node, `${group.name}标签${index}`)?.value ?? "").trim();
			if (value && value !== "无" && !tags.includes(value)) tags.push(value);
		}
		selected[group.name] = tags;
	}
	const properties = ensureNodeProperties(node);
	const hasNsfwWorkspace = Object.prototype.hasOwnProperty.call(properties, "nsfw_workspace") || Object.prototype.hasOwnProperty.call(properties, "nsfwWorkspace");
	const nsfwWorkspace = hasNsfwWorkspace
		? cloneNsfwWorkspaceState(properties.nsfw_workspace ?? properties.nsfwWorkspace ?? null)
		: null;
	if (nsfwWorkspace && !nsfwWorkspace.generation_profile_restore && properties[NODE_NSFW_PROFILE_RESTORE_KEY]) {
		const legacyProfileRestore = cloneSettingRestoreSnapshot(
			properties[NODE_NSFW_PROFILE_RESTORE_KEY],
			NSFW_GENERATION_PROFILE_SETTING_NAMES,
		);
		if (hasSettingRestoreSnapshot(legacyProfileRestore)) nsfwWorkspace.generation_profile_restore = legacyProfileRestore;
	}
	const state = {
		selected,
		customTags: parseCustomTags(getWidget(node, "自定义补充标签")?.value ?? ""),
		settings: Object.fromEntries(PRESET_SETTING_NAMES.map((name) => [name, getWidget(node, name)?.value ?? PRESET_SETTING_DEFAULTS[name]])),
		...(hasNsfwWorkspace
			? { nsfwWorkspace }
			: {}),
		...(Object.prototype.hasOwnProperty.call(properties, NODE_CHARACTER_SHEET_RESTORE_KEY)
			? { characterSheetRestore: cloneCharacterSheetRestoreState(properties[NODE_CHARACTER_SHEET_RESTORE_KEY]) }
			: {}),
		...(String(properties[NODE_SMART_TEXT_AUTO_EXTRA_KEY] ?? "").trim()
			? { smartTextAutoExtra: String(properties[NODE_SMART_TEXT_AUTO_EXTRA_KEY]).trim() }
			: {}),
	};
	state.settings[RUNTIME_RANDOM_PROTECTED_TAGS_WIDGET_NAME] = collectNsfwRuntimeProtectedTags(state).join(", ");
	return state;
}

function removeTagSetFromState(state, groupName, tagSet) {
	if (!state || typeof state !== "object" || !(tagSet instanceof Set) || !tagSet.size) return;
	state.selected[groupName] = (state.selected?.[groupName] ?? []).filter((tag) => !tagSet.has(tag));
	state.customTags = (state.customTags ?? []).filter((tag) => !tagSet.has(tag));
}

function buildIdentitySceneComboPools(library) {
	const identityGroup = library?.tag_library?.[RANDOM_COMBO_IDENTITY_GROUP_NAME] ?? {};
	const sceneGroup = library?.tag_library?.[RANDOM_COMBO_SCENE_GROUP_NAME] ?? {};
	const identityPool = flattenSectionTags(identityGroup, RANDOM_COMBO_IDENTITY_SECTION_NAMES).filter((tag) => tag && tag !== "无");
	const scenePool = flattenUniqueTags(sceneGroup).filter((tag) => tag && tag !== "无" && !RANDOM_COMBO_SCENE_EXCLUDE_TAGS.has(tag));
	return { identityPool, scenePool };
}

function pickRandomIdentitySceneCombo(node, library) {
	const { identityPool, scenePool } = buildIdentitySceneComboPools(library);
	if (!identityPool.length || !scenePool.length) return null;
	const comboHistory = getNodeRandomComboHistory(node);
	const recentIdentitySet = new Set(comboHistory.map((entry) => entry.identity));
	const recentSceneSet = new Set(comboHistory.map((entry) => entry.scene));
	const recentComboSet = new Set(comboHistory.map((entry) => `${entry.identity}__${entry.scene}`));
	const identityCandidates = identityPool.filter((tag) => !recentIdentitySet.has(tag));
	const effectiveIdentityPool = identityCandidates.length ? identityCandidates : identityPool;
	const identity = randomItem(effectiveIdentityPool);
	if (!identity) return null;
	const freshSceneCandidates = scenePool.filter((tag) => !recentSceneSet.has(tag) && !recentComboSet.has(`${identity}__${tag}`));
	const comboOnlyCandidates = scenePool.filter((tag) => !recentComboSet.has(`${identity}__${tag}`));
	const effectiveScenePool = freshSceneCandidates.length ? freshSceneCandidates : comboOnlyCandidates.length ? comboOnlyCandidates : scenePool;
	const scene = randomItem(effectiveScenePool);
	if (!scene) return null;
	return { identity, scene, identityPool, scenePool };
}

function buildIdentitySceneRandomBaseState(node, library) {
	const combo = pickRandomIdentitySceneCombo(node, library);
	if (!combo) return null;
	const currentState = collectNodeState(node, library);
	const state = clonePresetState(currentState);
	const identityTagSet = new Set(combo.identityPool);
	const sceneTagSet = new Set(combo.scenePool);
	removeTagSetFromState(state, RANDOM_COMBO_IDENTITY_GROUP_NAME, identityTagSet);
	removeTagSetFromState(state, RANDOM_COMBO_SCENE_GROUP_NAME, sceneTagSet);
	addUniqueTag(state.selected[RANDOM_COMBO_IDENTITY_GROUP_NAME] ?? (state.selected[RANDOM_COMBO_IDENTITY_GROUP_NAME] = []), combo.identity);
	addUniqueTag(state.selected[RANDOM_COMBO_SCENE_GROUP_NAME] ?? (state.selected[RANDOM_COMBO_SCENE_GROUP_NAME] = []), combo.scene);
	state.settings = {
		...state.settings,
		"运行时随机标签": true,
		"主体类型": "人物角色",
	};
	return { state, combo };
}

function buildCharacterSheetState(node, library, options = {}) {
	const mode = CHARACTER_SHEET_MODE_OPTIONS.some((item) => item.key === options.mode) ? options.mode : "reference";
	const userText = String(options.userText ?? "").trim();
	const currentState = collectNodeState(node, library);
	const nextState = clonePresetState(currentState);
	const previousRestore = cloneCharacterSheetRestoreState(currentState.characterSheetRestore);
	const legacyCharacterSheetEnabled = !!currentState.settings?.["图片反推生成"] && currentState.settings?.["图片反推模式"] === "角色设定图";
	const previousAddedTags = previousRestore.addedTags.length
		? previousRestore.addedTags
		: legacyCharacterSheetEnabled ? [...CHARACTER_SHEET_LEGACY_CLEANUP_TAGS] : [];
	removeCharacterSheetAutoTagsFromState(nextState, previousAddedTags);
	const baseExtraRequirement = stripCharacterSheetPromptText(nextState.settings?.["额外要求"]);
	const settingsBefore = { ...(nextState.settings ?? {}) };
	nextState.settings = {
		...(nextState.settings ?? {}),
		"模板风格": nextState.settings?.["模板风格"] ?? "自动",
		"主体类型": "人物角色",
		"案例输出结构": "案例长段版",
		"详细度": "详细",
		"输出模式": "完整结果",
		"优先柔和肤质": true,
		"抑制文字伪影": true,
		"图片反推生成": true,
		"图片反推模式": "角色设定图",
		"图片反推最大边长": 960,
		"额外要求": mergeRequirementText(
			baseExtraRequirement,
			[userText, CHARACTER_SHEET_PROMPTS[mode]].filter(Boolean).join("\n"),
		),
	};
	const beforeTags = collectStateTagSet(nextState);
	const automaticTags = uniqueTextList([
		...CHARACTER_SHEET_BASE_TAGS,
		...CHARACTER_SHEET_STYLE_TAGS,
		mode === "reference" ? "参考图一致性" : "纯提示词角色设计",
	]);
	const mergedCustomTags = [...(nextState.customTags ?? [])];
	for (const tag of automaticTags) {
		if (!beforeTags.has(tag)) addUniqueTag(mergedCustomTags, tag);
	}
	nextState.customTags = uniqueTextList(mergedCustomTags);
	const afterTags = collectStateTagSet(nextState);
	nextState.characterSheetRestore = {
		settings: updateSettingRestoreSnapshot(previousRestore.settings, settingsBefore, nextState.settings, CHARACTER_SHEET_SETTING_NAMES),
		addedTags: automaticTags.filter((tag) => CHARACTER_SHEET_AUTO_TAGS.has(tag) && !beforeTags.has(tag) && afterTags.has(tag)),
	};
	return nextState;
}

function stripCharacterSheetPromptText(text) {
	const promptTexts = new Set(Object.values(CHARACTER_SHEET_PROMPTS).map((item) => String(item ?? "").trim()).filter(Boolean));
	return String(text ?? "")
		.split(/\r?\n/u)
		.map((line) => line.trim())
		.filter((line) => line && !promptTexts.has(line) && !line.startsWith(CHARACTER_SHEET_STRATEGY_PREFIX))
		.join("\n");
}

function collectStateTagSet(state) {
	return new Set([
		...Object.values(state?.selected ?? {}).flatMap((tags) => tags ?? []),
		...(state?.customTags ?? []),
	].map((tag) => String(tag ?? "").trim()).filter(Boolean));
}

function removeCharacterSheetAutoTagsFromState(state, tagsToRemove = []) {
	if (!state || typeof state !== "object") return;
	const removalSet = new Set(uniqueTextList(tagsToRemove));
	if (!removalSet.size) return;
	for (const groupName of Object.keys(state.selected ?? {})) {
		state.selected[groupName] = (state.selected[groupName] ?? []).filter((tag) => !removalSet.has(tag));
	}
	state.customTags = (state.customTags ?? []).filter((tag) => !removalSet.has(tag));
}

function buildCharacterSheetDisabledState(node, library) {
	const currentState = collectNodeState(node, library);
	const nextState = clonePresetState(currentState);
	const restoreState = cloneCharacterSheetRestoreState(currentState.characterSheetRestore);
	const legacyCharacterSheetEnabled = !!currentState.settings?.["图片反推生成"] && currentState.settings?.["图片反推模式"] === "角色设定图";
	const removalTags = restoreState.addedTags.length
		? restoreState.addedTags
		: legacyCharacterSheetEnabled ? [...CHARACTER_SHEET_LEGACY_CLEANUP_TAGS] : [];
	removeCharacterSheetAutoTagsFromState(nextState, removalTags);
	let nextSettings = {
		...(nextState.settings ?? {}),
		"额外要求": stripCharacterSheetPromptText(nextState.settings?.["额外要求"]),
	};
	if (hasSettingRestoreSnapshot(restoreState.settings)) {
		nextSettings = restoreSettingsFromSnapshot(nextSettings, restoreState.settings, CHARACTER_SHEET_SETTING_NAMES);
	} else {
		nextSettings["图片反推生成"] = false;
		nextSettings["图片反推模式"] = "仅反推描述";
	}
	nextState.settings = nextSettings;
	delete nextState.characterSheetRestore;
	return nextState;
}

function applyIdentitySceneComboToState(state, library, combo) {
	const nextState = clonePresetState(state);
	const identityTagSet = new Set(combo?.identityPool ?? []);
	const sceneTagSet = new Set(combo?.scenePool ?? []);
	removeTagSetFromState(nextState, RANDOM_COMBO_IDENTITY_GROUP_NAME, identityTagSet);
	removeTagSetFromState(nextState, RANDOM_COMBO_SCENE_GROUP_NAME, sceneTagSet);
	const identityGroupConfig = (library?.slot_config ?? []).find((group) => group.name === RANDOM_COMBO_IDENTITY_GROUP_NAME);
	const sceneGroupConfig = (library?.slot_config ?? []).find((group) => group.name === RANDOM_COMBO_SCENE_GROUP_NAME);
	const identityLimit = Math.max(1, Number(identityGroupConfig?.slots ?? 1));
	const sceneLimit = Math.max(1, Number(sceneGroupConfig?.slots ?? 1));
	const keptIdentityTags = (nextState.selected?.[RANDOM_COMBO_IDENTITY_GROUP_NAME] ?? []).filter((tag) => tag !== combo.identity);
	const keptSceneTags = (nextState.selected?.[RANDOM_COMBO_SCENE_GROUP_NAME] ?? []).filter((tag) => tag !== combo.scene);
	nextState.selected[RANDOM_COMBO_IDENTITY_GROUP_NAME] = [combo.identity, ...keptIdentityTags].slice(0, identityLimit);
	nextState.selected[RANDOM_COMBO_SCENE_GROUP_NAME] = [combo.scene, ...keptSceneTags].slice(0, sceneLimit);
	nextState.settings = {
		...(nextState.settings ?? {}),
		"运行时随机标签": true,
		"主体类型": "人物角色",
	};
	return nextState;
}

function beginNodeStateMutation(node) {
	if (!node || typeof node !== "object") return 0;
	const nextRevision = Math.max(0, Number(node[NODE_STATE_MUTATION_REVISION_KEY] ?? 0) || 0) + 1;
	node[NODE_STATE_MUTATION_REVISION_KEY] = nextRevision;
	return nextRevision;
}

function isNodeStateMutationCurrent(node, revision) {
	const expected = Math.max(0, Number(revision ?? 0) || 0);
	return !!node && !node[NODE_REMOVED_KEY] && expected > 0 && Number(node[NODE_STATE_MUTATION_REVISION_KEY] ?? 0) === expected;
}

function applyNodeState(node, library, state, options = {}) {
	const mutationRevision = Math.max(0, Number(options.mutationRevision ?? 0) || 0);
	if (mutationRevision > 0) {
		if (!isNodeStateMutationCurrent(node, mutationRevision)) return false;
	} else {
		beginNodeStateMutation(node);
	}
	const selected = state?.selected ?? {};
	const mergedCustomTags = uniqueTextList(state?.customTags ?? []);
	for (const group of library.slot_config ?? []) {
		const allowedValues = new Set(flattenUniqueTags(library.tag_library?.[group.name]));
		const values = [];
		for (const value of selected[group.name] ?? []) {
			if (allowedValues.has(value)) {
				if (!values.includes(value)) values.push(value);
			} else addUniqueTag(mergedCustomTags, value);
		}
		const limit = getTagGroupSlotLimit(library, group.name);
		for (const extra of values.slice(limit)) addUniqueTag(mergedCustomTags, extra);
		for (let index = 1; index <= limit; index += 1) {
			setWidgetValue(node, `${group.name}标签${index}`, values[index - 1] ?? "无");
		}
	}
	setWidgetValue(node, "自定义补充标签", mergedCustomTags.join(", "));
	for (const name of PRESET_SETTING_NAMES) {
		if (!state?.settings || !(name in state.settings)) continue;
		setWidgetValue(node, name, state.settings[name]);
	}
	setWidgetValue(
		node,
		RUNTIME_RANDOM_PREVIEW_TOKEN_WIDGET_NAME,
		String(state?.settings?.[RUNTIME_RANDOM_PREVIEW_TOKEN_WIDGET_NAME] ?? "").trim(),
	);
	const properties = ensureNodeProperties(node);
	delete properties[NODE_NSFW_PROFILE_RESTORE_KEY];
	const hasNsfwWorkspace = Object.prototype.hasOwnProperty.call(state ?? {}, "nsfwWorkspace") || Object.prototype.hasOwnProperty.call(state ?? {}, "nsfw_workspace");
	if (hasNsfwWorkspace) {
		const nextWorkspace = cloneNsfwWorkspaceState(state.nsfwWorkspace ?? state.nsfw_workspace ?? null);
		properties.nsfw_workspace = nextWorkspace;
		properties.nsfwWorkspace = cloneNsfwWorkspaceState(nextWorkspace);
	} else {
		delete properties.nsfw_workspace;
		delete properties.nsfwWorkspace;
	}
	if (Object.prototype.hasOwnProperty.call(state ?? {}, "characterSheetRestore")) {
		properties[NODE_CHARACTER_SHEET_RESTORE_KEY] = cloneCharacterSheetRestoreState(state.characterSheetRestore);
	} else {
		delete properties[NODE_CHARACTER_SHEET_RESTORE_KEY];
	}
	const smartTextAutoExtra = String(state?.smartTextAutoExtra ?? "").trim();
	if (smartTextAutoExtra) properties[NODE_SMART_TEXT_AUTO_EXTRA_KEY] = smartTextAutoExtra;
	else delete properties[NODE_SMART_TEXT_AUTO_EXTRA_KEY];
	setWidgetValue(node, RUNTIME_RANDOM_PROTECTED_TAGS_WIDGET_NAME, collectNsfwRuntimeProtectedTags({ ...state, nsfwWorkspace: hasNsfwWorkspace ? properties.nsfw_workspace : null }).join(", "));
	if ((options.historySource ?? "") === "random") {
		if (state?._randomCoreState) {
			setNodeRandomCoreState(node, state._randomCoreState);
			setNodeRandomCoreSignature(node, state?._randomCoreSignature ?? "");
		} else {
			clearNodeRandomCoreState(node);
			clearNodeRandomCoreSignature(node);
		}
		setNodeRandomLastState(node, { selected, customTags: mergedCustomTags });
		writeNodeRandomDedupeCache(node, Array.isArray(state?._randomSupplementTags) ? state._randomSupplementTags : []);
		setNodeRandomComboPreview(node, options.randomComboPreview ?? null);
	} else {
		clearNodeRandomRuntimeState(node);
		clearNodeRandomDedupeCache(node);
		setNodeRandomComboPreview(node, null);
	}
	persistNamedWidgetState(node);
	refreshNodeSummary(node, library);
	refreshSlotPanel(node);
	refreshAdvancedPanel(node, { force: true });
	if (options.recordHistory) {
		recordNodeHistory(node, collectNodeState(node, library), options.historySource ?? "random");
	}
	scheduleNodeLayoutUpdate(node);
	return true;
}

function applyClearPromptInputState(node, state) {
	state.settings = { ...(state.settings ?? {}) };
	delete state.smartTextAutoExtra;
	for (const widgetName of CLEAR_PROMPT_INPUT_WIDGET_NAMES) {
		state.settings[widgetName] = "";
	}
	state.settings["智能文本匹配"] = false;
	state.settings[TAG_BLOCK_COMPOSER_ENABLED_WIDGET_NAME] = false;
	for (const widgetName of CLEAR_PROMPT_INPUT_WIDGET_NAMES) {
		setWidgetValue(node, widgetName, "");
	}
	setWidgetValue(node, "智能文本匹配", false);
	setWidgetValue(node, TAG_BLOCK_COMPOSER_ENABLED_WIDGET_NAME, false);
}

function buildClearedNodeState(node, library) {
	const emptyState = collectNodeState(node, library);
	for (const group of library.slot_config ?? []) emptyState.selected[group.name] = [];
	emptyState.customTags = [];
	applyClearPromptInputState(node, emptyState);
	return emptyState;
}

function applyClearedNodeState(node, library, options = {}) {
	const mutationRevision = Math.max(0, Number(options.mutationRevision ?? 0) || 0) || beginNodeStateMutation(node);
	if (!isNodeStateMutationCurrent(node, mutationRevision)) return false;
	recordNodeHistory(node, collectNodeState(node, library), "before-clear");
	const emptyState = buildClearedNodeState(node, library);
	if (!applyNodeState(node, library, emptyState, { recordHistory: true, historySource: "clear", mutationRevision })) return false;
	clearStageTerminalPreviewState(node);
	return emptyState;
}

function summarizeHistoryState(state) {
	const settings = getEffectiveSummarySettings(state);
	const template = settings["模板风格"] ?? "自动";
	const subjectType = settings["主体类型"] ?? "自动";
	const nsfwPrefix = isNsfwWorkspaceEnabledInState(state) ? "NSFW开 | " : "";
	const tags = [...Object.values(state.selected ?? {}).flatMap((items) => items ?? []), ...(state.customTags ?? [])];
	const shown = tags.slice(0, 8);
	const remain = tags.length - shown.length;
	return `${nsfwPrefix}${template} | ${subjectType}${shown.length ? ` | ${shown.join("、")}${remain > 0 ? ` +${remain}` : ""}` : ""}`;
}

function getNsfwWorkspaceFromState(state) {
	return state?.nsfwWorkspace ?? state?.nsfw_workspace ?? null;
}

function isNsfwWorkspaceEnabledInState(state) {
	return !!getNsfwWorkspaceFromState(state)?.enabled;
}

function getEffectiveSummarySettings(state) {
	const settings = { ...PRESET_SETTING_DEFAULTS, ...(state?.settings ?? {}) };
	if (!isNsfwWorkspaceEnabledInState(state)) return settings;
	const templateStyle = String(settings["模板风格"] ?? PRESET_SETTING_DEFAULTS["模板风格"] ?? "自动").trim() || "自动";
	const subjectType = String(settings["主体类型"] ?? PRESET_SETTING_DEFAULTS["主体类型"] ?? "自动").trim() || "自动";
	if (templateStyle === "自动") settings["模板风格"] = NSFW_GENERATION_PROFILE.templateStyle;
	if (subjectType === "自动") settings["主体类型"] = NSFW_GENERATION_PROFILE.subjectType;
	settings["标签反推模式"] = NSFW_GENERATION_PROFILE.reverseMode;
	settings["优先柔和肤质"] = true;
	settings["抑制文字伪影"] = true;
	return settings;
}

function summarizeState(state) {
	const pickedTotal = Object.values(state.selected).reduce((count, tags) => count + tags.length, 0) + state.customTags.length;
	const previewTags = [...Object.values(state.selected).flatMap((tags) => tags), ...state.customTags];
	const slotTags = [...Object.values(state.selected).flatMap((tags) => tags)];
	const settings = getEffectiveSummarySettings(state);
	const nsfwFlag = isNsfwWorkspaceEnabledInState(state) ? " | NSFW开" : "";
	const themePool = String(settings["随机主题池"] ?? PRESET_SETTING_DEFAULTS["随机主题池"] ?? "自动").trim() || "自动";
	const randomFlag = settings["运行时随机标签"] ? ` | 运行随机:${settings["运行时随机模式"]}/${settings["运行时随机强度"]}/锁${settings["核心标签锁定数量"]}` : "";
	const softSkinFlag = settings["优先柔和肤质"] ? " | 柔肤优先" : "";
	const suppressTextFlag = settings["抑制文字伪影"] ? " | 抑字优先" : "";
	const lockedSlotCount = slotTags.length;
	const lockedCustomCount = state.customTags.length;
	const lockedFlag = settings["运行时随机标签"] && settings["运行时随机模式"] === "保留已选核心标签"
		? ` | 锁定槽位:${lockedSlotCount} / 锁定补充:${lockedCustomCount}`
		: "";
	const whiteCount = parseCustomTags(settings["锁定标签白名单"]).length;
	const excludeCount = parseCustomTags(settings["随机排除标签"]).length;
	const filterFlag = whiteCount || excludeCount ? ` | 白${whiteCount}/排${excludeCount}` : "";
	const reverseModeFlag = settings["标签反推模式"] && settings["标签反推模式"] !== "自动平衡" ? ` | 反推:${settings["标签反推模式"]}` : "";
	const themePoolFlag = themePool !== "自动" ? ` | 主题池:${themePool}` : "";
	const lines = [`标签 ${pickedTotal}${nsfwFlag} | ${settings["模板风格"]} | ${settings["主体类型"]} | ${settings["案例输出结构"]}${reverseModeFlag}${randomFlag}${softSkinFlag}${suppressTextFlag}${lockedFlag}${filterFlag}${themePoolFlag}`];
	if (previewTags.length) {
		const shown = previewTags.slice(0, 6);
		const remain = previewTags.length - shown.length;
		lines.push(`已选：${shown.join("、")}${remain > 0 ? ` +${remain}` : ""}`);
	} else lines.push("还没有选择标签，可点“标签”打开选择面板。");
	if (settings["运行时随机标签"] && settings["运行时随机模式"] === "保留已选核心标签") {
		const slotShown = slotTags.slice(0, 4);
		const slotRemain = slotTags.length - slotShown.length;
		const customShown = state.customTags.slice(0, 3);
		const customRemain = state.customTags.length - customShown.length;
		const slotText = slotShown.length ? `${slotShown.join("、")}${slotRemain > 0 ? ` +${slotRemain}` : ""}` : "无";
		const customText = customShown.length ? `${customShown.join("、")}${customRemain > 0 ? ` +${customRemain}` : ""}` : "无";
		lines.push(`锁定预览：槽位[${slotText}] / 补充[${customText}]`);
	}
	return lines.join("\n");
}

function buildNodeSummaryText(node, library) {
	const summaryLines = [summarizeState(collectNodeState(node, library))];
	const decisionSummary = formatStageDecisionSummary(node);
	if (decisionSummary) summaryLines.push(`解析：${decisionSummary}`);
	const panelMessage = String(node?.[PANEL_KEY]?.lastPanelMessage ?? "").trim();
	if (panelMessage) summaryLines.push(`最近：${panelMessage}`);
	const dedupeCount = readNodeRandomDedupeCache(node).length;
	if (dedupeCount > 0) summaryLines.push(`随机避重：已缓存 ${dedupeCount} 个最近补充标签`);
	const randomDiagText = formatRandomRuntimeDiagnostics(node);
	if (randomDiagText) summaryLines.push(`随机诊断：${randomDiagText}`);
	const trackHistoryText = buildRandomTrackHistoryText(node);
	if (trackHistoryText) summaryLines.push(trackHistoryText);
	const qualityMeta = getNodeQualityAuditMeta(node);
	if (qualityMeta?.summary) {
		const summary = qualityMeta.summary;
		summaryLines.push(`质检：OCR ${summary.ocr_risk_images ?? 0} | 皱纹 ${summary.wrinkle_risk_images ?? 0} | 磨皮 ${summary.oversmooth_risk_images ?? 0}`);
	}
	const continuousSummary = formatContinuousReportSummary(getNodeContinuousReportMeta(node));
	const summaryText = summaryLines.join("\n");
	return continuousSummary ? `${summaryText}\n连测：${continuousSummary}` : summaryText;
}

function buildHeroCaptionText(node, library) {
	const state = collectNodeState(node, library);
	const settings = getEffectiveSummarySettings(state);
	const modeBits = [];
	if (isNsfwWorkspaceEnabledInState(state)) modeBits.push(`NSFW ON ${settings["模板风格"]}/${settings["主体类型"]}`);
	modeBits.push(settings["优先柔和肤质"] ? "柔肤 ON" : "柔肤 OFF");
	modeBits.push(settings["抑制文字伪影"] ? "抑字 ON" : "抑字 OFF");
	if (settings["运行时随机标签"]) modeBits.push(`随机 ${settings["运行时随机模式"]}`);
	if (settings["随机主题池"] && settings["随机主题池"] !== "自动") modeBits.push(`主题池 ${settings["随机主题池"]}`);
	const dedupeCount = readNodeRandomDedupeCache(node).length;
	if (dedupeCount > 0) modeBits.push(`避重 ${dedupeCount}`);
	const randomDiag = getNodeRandomRuntimeDiagnostics(node);
	if (randomDiag?.styleTrack) modeBits.push(`轨道 ${randomDiag.styleTrack}`);
	if (randomDiag?.mainSceneGroup) modeBits.push(`片场 ${randomDiag.mainSceneGroup}`);
	if (randomDiag?.mainIdentity) modeBits.push(`身份 ${randomDiag.mainIdentity}`);
	if (randomDiag?.adultSubpool) modeBits.push(`成人池 ${randomDiag.adultSubpool}`);
	const trackHistoryText = buildRandomTrackHistoryText(node);
	if (trackHistoryText) modeBits.push(trackHistoryText.replace(/^轨道历史\s*/u, "轨迹 "));
	const qualityMeta = getNodeQualityAuditMeta(node);
	if (qualityMeta?.summary) {
		modeBits.push(`质检 OCR${qualityMeta.summary.ocr_risk_images ?? 0}/皱${qualityMeta.summary.wrinkle_risk_images ?? 0}/磨${qualityMeta.summary.oversmooth_risk_images ?? 0}`);
	}
	return `围绕标签、随机、预设与历史的一站式操作面板。当前策略：${modeBits.join(" / ")}。`;
}

function setFirstEmptyWidgetValue(node, widgetNames, value) {
	for (const widgetName of widgetNames) {
		const widget = getWidget(node, widgetName);
		const currentValue = String(widget?.value ?? "").trim();
		if (!widget || (currentValue && currentValue !== "无")) continue;
		setWidgetValue(node, widgetName, value);
		return true;
	}
	return false;
}

function applySafeProfileToNode(node, library) {
	const state = collectNodeState(node, library);
	const statusBits = [];
	if (!state.settings["优先柔和肤质"]) {
		setWidgetValue(node, "优先柔和肤质", true);
		statusBits.push("开启柔肤");
	}
	if (!state.settings["抑制文字伪影"]) {
		setWidgetValue(node, "抑制文字伪影", true);
		statusBits.push("开启抑字");
	}

	const subjectType = String(state.settings["主体类型"] ?? "自动");
	const compositionTags = state.selected["构图视角"] ?? [];
	const lightTags = state.selected["光影氛围"] ?? [];
	const techTags = state.selected["技术画质"] ?? [];
	const allSelectedTags = [...Object.values(state.selected).flatMap((tags) => tags ?? []), ...state.customTags];
	const isNonHuman = subjectType === "非人物主体";
	const hasWideShot = compositionTags.some((tag) => SAFE_PROFILE_WIDE_TAGS.has(tag));
	const hasLens = compositionTags.some((tag) => SAFE_PROFILE_LENS_TAGS.has(tag));

	const nextCustomTags = [...state.customTags];
	if (!SAFE_PROFILE_TEXT_SUPPRESSION_TAGS.every((tag) => allSelectedTags.includes(tag))) {
		for (const tag of SAFE_PROFILE_TEXT_SUPPRESSION_TAGS) {
			if (!allSelectedTags.includes(tag) && !nextCustomTags.includes(tag)) nextCustomTags.push(tag);
		}
		statusBits.push("补无字约束");
	}

	if (!isNonHuman && !hasWideShot) {
		if (!hasLens && setFirstEmptyWidgetValue(node, ["构图视角标签1", "构图视角标签2", "构图视角标签3"], "长焦")) {
			statusBits.push("补长焦");
		}
		if (!lightTags.some((tag) => SAFE_PROFILE_SOFT_LIGHT_TAGS.has(tag)) && setFirstEmptyWidgetValue(node, ["光影氛围标签1", "光影氛围标签2", "光影氛围标签3"], "柔光")) {
			statusBits.push("补柔光");
		}
		if (!techTags.includes(SAFE_PROFILE_TECH_TAG)) {
			if (setFirstEmptyWidgetValue(node, ["技术画质标签1", "技术画质标签2", "技术画质标签3"], SAFE_PROFILE_TECH_TAG)) {
				statusBits.push("补柔和高光");
			} else if (!nextCustomTags.includes(SAFE_PROFILE_TECH_TAG)) {
				nextCustomTags.push(SAFE_PROFILE_TECH_TAG);
				statusBits.push("补柔和高光");
			}
		}
		if (!allSelectedTags.includes(SAFE_PROFILE_PORTRAIT_TAG) && !nextCustomTags.includes(SAFE_PROFILE_PORTRAIT_TAG)) {
			nextCustomTags.push(SAFE_PROFILE_PORTRAIT_TAG);
			statusBits.push("补面部聚焦");
		}
	}

	if (nextCustomTags.join(", ") !== state.customTags.join(", ")) {
		setWidgetValue(node, "自定义补充标签", nextCustomTags.join(", "));
	}
	refreshNodeSummary(node, library);
	return statusBits.length ? `一键稳妥：${statusBits.join("，")}。` : "一键稳妥：当前已经是较稳配置。";
}

function setPanelActionButtonState(button, enabled, disabledHint = "") {
	if (!isButtonLikeElement(button)) return;
	const baseHint = String(button.dataset.qwenHint ?? "").trim();
	const busy = button.classList.contains("is-busy");
	button.disabled = busy || !enabled;
	if (button.style) button.style.opacity = busy ? "0.72" : (enabled ? "1" : "0.55");
	button.title = busy ? "处理中..." : (enabled ? baseHint : String(disabledHint || baseHint || "当前不可用。"));
}

function getBooleanWidgetValue(node, name, fallback = false) {
	return !!(getWidget(node, name)?.value ?? fallback);
}

function getWidgetDisplayValue(node, name, fallback = "") {
	const value = getWidget(node, name)?.value;
	if (value === undefined || value === null || value === "") return String(fallback ?? "");
	return String(value);
}

function setControlWidgetValue(node, name, value) {
	const widget = getWidget(node, name);
	if (!widget) return false;
	beginNodeStateMutation(node);
	setWidgetValue(node, name, value);
	persistNamedWidgetState(node);
	refreshNodeSummary(node, node?.[PANEL_KEY]?.library ?? { slot_config: [], tag_library: {} });
	refreshControlSurface(node);
	refreshNodeActionButtons(node);
	scheduleNodeLayoutUpdate(node);
	return true;
}

function createControlChip(node, name, label, value, options = {}) {
	const button = document.createElement("button");
	button.type = "button";
	button.className = `qwen-te-panel__control-chip${options.toggle ? " qwen-te-panel__control-chip--toggle" : ""}${options.danger ? " qwen-te-panel__control-chip--danger" : ""}`;
	button.textContent = label;
	button.dataset.widgetName = name;
	button.dataset.widgetValue = String(value);
	button.addEventListener("pointerdown", (event) => { event.stopPropagation(); });
	button.addEventListener("mousedown", (event) => { event.stopPropagation(); });
	button.addEventListener("click", (event) => {
		event.stopPropagation();
		const nextValue = typeof options.nextValue === "function" ? options.nextValue(node, name, value) : value;
		if (setControlWidgetValue(node, name, nextValue)) {
			setNodeStatusText(node, `${name} 已设为 ${String(nextValue)}。`);
		}
	});
	return button;
}

function normalizeControlOption(option) {
	if (option && typeof option === "object" && Object.prototype.hasOwnProperty.call(option, "value")) {
		return { value: option.value, label: String(option.label ?? option.value), hint: String(option.hint ?? "") };
	}
	return { value: option, label: String(option), hint: "" };
}

function getAdvancedWidgetOptions(node, name) {
	const configured = Array.isArray(CONTROL_WIDGET_OPTIONS[name])
		? CONTROL_WIDGET_OPTIONS[name].map(normalizeControlOption)
		: [];
	const widgetOptions = getWidgetOptions(node, name).map(normalizeControlOption);
	const merged = [];
	const seen = new Set();
	for (const option of [...configured, ...widgetOptions]) {
		const key = `${typeof option.value}:${String(option.value)}`;
		if (seen.has(key)) continue;
		seen.add(key);
		merged.push(option);
	}
	return merged;
}

function getAdvancedOptionColumnCount(name, options) {
	if (!Array.isArray(options) || options.length <= 1) return 1;
	if (["随机主题池", "标签反推模式", "案例输出结构", "运行时随机模式"].includes(name)) return 2;
	if (options.some((option) => String(option?.label ?? option?.value ?? "").length >= 6)) return 2;
	return Math.min(3, Math.max(2, options.length));
}

function isAdvancedTextWidgetName(name) {
	return ["智能文本输入", "额外要求", "系统提示词覆盖", "锁定标签白名单", "随机排除标签"].includes(name);
}

function getAdvancedWidgetTooltip(node, name) {
	return String(getWidget(node, name)?.options?.tooltip ?? "").trim();
}

function createAdvancedChip(node, name, label, value, hint = "", parameterHint = "") {
	const button = document.createElement("button");
	button.type = "button";
	button.className = "qwen-te-panel__advanced-chip";
	button.textContent = label;
	button.dataset.widgetName = name;
	button.dataset.widgetValue = String(value);
	button.title = [parameterHint, hint].map((item) => String(item ?? "").trim()).filter(Boolean).join("\n");
	button.addEventListener("pointerdown", (event) => { event.stopPropagation(); });
	button.addEventListener("mousedown", (event) => { event.stopPropagation(); });
	button.addEventListener("click", (event) => {
		event.stopPropagation();
		if (setControlWidgetValue(node, name, value)) setNodeStatusText(node, hint ? `${name} 已设为 ${String(value)}。${String(hint)}` : `${name} 已设为 ${String(value)}。`);
	});
	return button;
}

function createAdvancedSelect(node, name, options) {
	const select = document.createElement("select");
	select.className = "qwen-te-panel__advanced-select";
	select.dataset.widgetName = name;
	select.title = getAdvancedWidgetTooltip(node, name);
	const widget = getWidget(node, name);
	const currentValue = String(widget?.value ?? "");
	const normalizedOptions = [...options];
	if (currentValue && !normalizedOptions.some((option) => String(option.value) === currentValue)) {
		normalizedOptions.unshift({ value: currentValue, label: currentValue, hint: "当前工作流中的兼容值" });
	}
	for (const option of normalizedOptions) {
		const optionEl = document.createElement("option");
		optionEl.value = String(option.value);
		optionEl.textContent = String(option.label ?? option.value);
		if (option.hint) optionEl.title = String(option.hint);
		select.appendChild(optionEl);
	}
	select.value = currentValue;
	for (const eventName of ["pointerdown", "mousedown", "click", "wheel"]) {
		select.addEventListener(eventName, stopCanvasTextInputEvent, { passive: eventName !== "wheel" });
	}
	select.addEventListener("change", () => {
		const matched = normalizedOptions.find((option) => String(option.value) === select.value);
		const nextValue = matched?.value ?? select.value;
		if (setControlWidgetValue(node, name, nextValue)) {
			setNodeStatusText(node, `${name} 已设为 ${String(nextValue)}。${matched?.hint ? String(matched.hint) : ""}`);
		}
	});
	return select;
}

function bindAdvancedTextInputEvents(input, node, name) {
	for (const eventName of ["pointerdown", "pointerup", "mousedown", "mouseup", "click", "dblclick", "keydown", "keyup", "keypress", "compositionstart", "compositionupdate", "compositionend", "wheel"]) {
		input.addEventListener(eventName, stopCanvasTextInputEvent, { passive: eventName !== "wheel" });
	}
	input.addEventListener("pointerdown", () => {
		setTimeout(() => {
			try { input.focus({ preventScroll: true }); } catch (_error) { input.focus(); }
		}, 0);
	});
	input.addEventListener("input", () => {
		const rawValue = input.value;
		const widget = getWidget(node, name);
		if (!widget) return;
		const nextValue = typeof widget.value === "number" ? Number(rawValue) : rawValue;
		setControlWidgetValue(node, name, Number.isFinite(nextValue) || typeof nextValue === "string" ? nextValue : widget.value);
	});
}

function createAdvancedInput(node, name) {
	const widget = getWidget(node, name);
	const multiline = isAdvancedTextWidgetName(name);
	const input = document.createElement(multiline ? "textarea" : "input");
	input.className = "qwen-te-panel__advanced-input";
	if (!multiline) input.type = typeof widget?.value === "number" ? "number" : "text";
	input.dataset.widgetName = name;
	input.title = getAdvancedWidgetTooltip(node, name);
	input.value = String(widget?.value ?? "");
	input.placeholder = name === "智能文本输入"
		? "输入一句描述，点匹配启用后生成智能文本"
		: name === "额外要求"
			? "可写镜头、氛围、限制或生成偏好"
			: name === "系统提示词覆盖"
				? "默认不建议修改，留空则使用节点内置模板"
				: "";
	bindAdvancedTextInputEvents(input, node, name);
	return input;
}

function buildAdvancedPanel(node) {
	const panel = document.createElement("div");
	panel.className = "qwen-te-panel__advanced qwen-te-hidden";
	const scroll = document.createElement("div");
	scroll.className = "qwen-te-panel__advanced-scroll";
	scroll.addEventListener("wheel", stopCanvasWheelEvent, { passive: true });
	panel.appendChild(scroll);
	for (const [sectionIndex, section] of ADVANCED_PANEL_SECTIONS.entries()) {
		const card = document.createElement("div");
		card.className = `qwen-te-panel__advanced-card${section.rows.some(isAdvancedTextWidgetName) ? " qwen-te-panel__advanced-card--wide" : ""}`;
		card.dataset.sectionTitle = section.title;
		if (sectionIndex > 0) card.classList.add("is-collapsed");
		const head = document.createElement("button");
		head.type = "button";
		head.className = "qwen-te-panel__advanced-head";
		const title = document.createElement("div");
		title.className = "qwen-te-panel__advanced-title";
		title.textContent = section.title;
		const meta = document.createElement("div");
		meta.className = "qwen-te-panel__advanced-meta";
		const desc = document.createElement("div");
		desc.className = "qwen-te-panel__advanced-desc";
		desc.textContent = section.desc;
		const toggle = document.createElement("span");
		toggle.className = "qwen-te-panel__advanced-toggle";
		toggle.textContent = sectionIndex > 0 ? "展开" : "收起";
		meta.append(desc, toggle);
		head.append(title, meta);
		head.addEventListener("pointerdown", (event) => { event.stopPropagation(); });
		head.addEventListener("mousedown", (event) => { event.stopPropagation(); });
		head.addEventListener("click", (event) => {
			event.stopPropagation();
			const collapsed = card.classList.toggle("is-collapsed");
			toggle.textContent = collapsed ? "展开" : "收起";
			scheduleNodeLayoutUpdate(node);
		});
		card.appendChild(head);
		const body = document.createElement("div");
		body.className = "qwen-te-panel__advanced-body";
		for (const name of section.rows) {
			if (!getWidget(node, name)) continue;
			const parameterHint = getAdvancedWidgetTooltip(node, name);
			const row = document.createElement("div");
			row.className = "qwen-te-panel__advanced-row";
			row.dataset.widgetName = name;
			const label = document.createElement("div");
			label.className = "qwen-te-panel__advanced-label";
			label.textContent = name;
			label.title = parameterHint || name;
			const valueEl = document.createElement("div");
			valueEl.className = "qwen-te-panel__advanced-value";
			const options = getAdvancedWidgetOptions(node, name);
			if (options.length > 12) {
				valueEl.appendChild(createAdvancedSelect(node, name, options));
			} else if (options.length) {
				const optionGrid = document.createElement("div");
				optionGrid.className = "qwen-te-panel__advanced-options";
				optionGrid.style.setProperty("--qwen-te-advanced-cols", String(getAdvancedOptionColumnCount(name, options)));
				for (const option of options) optionGrid.appendChild(createAdvancedChip(node, name, option.label, option.value, option.hint, parameterHint));
				valueEl.appendChild(optionGrid);
			} else {
				valueEl.appendChild(createAdvancedInput(node, name));
			}
			row.append(label, valueEl);
			body.appendChild(row);
		}
		if (!body.children.length) {
			const empty = document.createElement("div");
			empty.className = "qwen-te-panel__advanced-note";
			empty.textContent = "当前节点没有可用参数。";
			body.appendChild(empty);
		}
		card.appendChild(body);
		scroll.appendChild(card);
	}
	return panel;
}

function bindPanelTextInputEvents(input, node, name, valueParser = (value) => value) {
	for (const eventName of ["pointerdown", "pointerup", "mousedown", "mouseup", "click", "dblclick", "keydown", "keyup", "keypress", "compositionstart", "compositionupdate", "compositionend", "wheel"]) {
		input.addEventListener(eventName, stopCanvasTextInputEvent, { passive: eventName !== "wheel" });
	}
	input.addEventListener("pointerdown", () => {
		setTimeout(() => {
			try { input.focus({ preventScroll: true }); } catch (_error) { input.focus(); }
		}, 0);
	});
	input.addEventListener("input", () => {
		const widget = getWidget(node, name);
		if (!widget) return;
		setControlWidgetValue(node, name, valueParser(input.value, widget));
	});
}

function createSlotInput(node, widgetName, options, listId) {
	const input = document.createElement("input");
	input.type = "text";
	input.className = "qwen-te-panel__slot-select";
	input.dataset.widgetName = widgetName;
	input.autocomplete = "off";
	input.spellcheck = false;
	input.setAttribute("list", listId);
	input.value = String(getWidget(node, widgetName)?.value ?? "无");
	const allowedValues = new Set(options.map((value) => String(value)));
	const validate = () => {
		const value = String(input.value ?? "").trim() || "无";
		const valid = allowedValues.has(value);
		input.classList.toggle("is-invalid", !valid);
		input.setCustomValidity?.(valid ? "" : "请从当前分组的候选标签中选择。自定义内容请填写在补充标签中。");
		return { valid, value };
	};
	const commitValidValue = (value) => {
		if (String(getWidget(node, widgetName)?.value ?? "无") === value) return;
		setControlWidgetValue(node, widgetName, value);
	};
	for (const eventName of ["pointerdown", "mousedown", "click", "keydown", "wheel"]) {
		input.addEventListener(eventName, stopCanvasTextInputEvent, { passive: eventName !== "wheel" });
	}
	input.addEventListener("input", () => {
		const { valid, value } = validate();
		if (valid) commitValidValue(value);
	});
	input.addEventListener("change", () => {
		const { valid, value } = validate();
		if (!valid) {
			input.reportValidity?.();
			setNodeStatusText(node, `${widgetName} 未写入：请从候选标签中选择。`);
			return;
		}
		input.value = value;
		commitValidValue(value);
		setNodeStatusText(node, value === "无" ? `${widgetName} 已清空。` : `${widgetName} 已设为 ${value}。`);
	});
	return input;
}

function createSlotDatalist(options, listId) {
	const datalist = document.createElement("datalist");
	datalist.id = listId;
	for (const value of options) {
		const option = document.createElement("option");
		option.value = String(value);
		datalist.appendChild(option);
	}
	return datalist;
}

function getSlotPanelGroupValues(library, groupName) {
	const source = library?.tag_library?.[groupName];
	const values = Array.isArray(source) ? source : flattenUniqueTags(source);
	return ["无", ...uniqueTextList(values)];
}

function getSlotPanelLibrarySignature(library) {
	if (!library || typeof library !== "object") return "";
	const cached = SLOT_PANEL_LIBRARY_SIGNATURE_CACHE.get(library);
	if (cached) return cached;
	const signature = JSON.stringify((library.slot_config ?? []).map((group) => {
		const groupName = String(group?.name ?? "");
		return [groupName, normalizeTagGroupSlotLimit(group?.slots, 0), getSlotPanelGroupValues(library, groupName)];
	}));
	SLOT_PANEL_LIBRARY_SIGNATURE_CACHE.set(library, signature);
	return signature;
}

function createSlotPanelShell(library) {
	const panel = document.createElement("div");
	panel.className = "qwen-te-panel__slots qwen-te-hidden";
	panel[SLOT_PANEL_LIBRARY_SIGNATURE_KEY] = getSlotPanelLibrarySignature(library);
	panel[SLOT_PANEL_POPULATED_KEY] = false;
	panel.addEventListener("wheel", stopCanvasWheelEvent, { passive: true });
	return panel;
}

function populateSlotPanel(panel, node, library) {
	if (!(panel instanceof HTMLElement)) return panel ?? null;
	const signature = getSlotPanelLibrarySignature(library);
	if (panel[SLOT_PANEL_POPULATED_KEY] && panel[SLOT_PANEL_LIBRARY_SIGNATURE_KEY] === signature) return panel;
	panel.replaceChildren();
	panel[SLOT_PANEL_LIBRARY_SIGNATURE_KEY] = signature;
	const listNamespace = `qwen-te-slot-list-${++slotPanelListSequence}`;
	let groupIndex = 0;
	for (const group of library?.slot_config ?? []) {
		const groupName = String(group.name ?? "");
		const slotCount = getTagGroupSlotLimit(library, groupName);
		if (!groupName || slotCount <= 0) continue;
		const values = getSlotPanelGroupValues(library, groupName);
		const listId = `${listNamespace}-${groupIndex++}`;
		const card = document.createElement("div");
		card.className = "qwen-te-panel__slot-card";
		const head = document.createElement("div");
		head.className = "qwen-te-panel__slot-head";
		const title = document.createElement("div");
		title.className = "qwen-te-panel__slot-title";
		title.textContent = groupName;
		title.title = groupName;
		const count = document.createElement("div");
		count.className = "qwen-te-panel__slot-count";
		count.dataset.groupName = groupName;
		head.append(title, count);
		card.appendChild(head);
		const body = document.createElement("div");
		body.className = "qwen-te-panel__slot-body";
		card.appendChild(createSlotDatalist(values, listId));
		for (let index = 1; index <= slotCount; index += 1) {
			const widgetName = `${groupName}标签${index}`;
			if (!getWidget(node, widgetName)) continue;
			const row = document.createElement("div");
			row.className = "qwen-te-panel__slot-row";
			row.dataset.widgetName = widgetName;
			row.dataset.groupName = groupName;
			const input = createSlotInput(node, widgetName, values, listId);
			input.title = widgetName;
			row.appendChild(input);
			body.appendChild(row);
		}
		if (!body.children.length) {
			const empty = document.createElement("div");
			empty.className = "qwen-te-panel__slot-empty";
			empty.textContent = "当前分组没有可编辑槽位。";
			body.appendChild(empty);
		}
		card.appendChild(body);
		panel.appendChild(card);
	}
	const customCard = document.createElement("div");
	customCard.className = "qwen-te-panel__slot-card qwen-te-panel__slot-card--custom";
	const customHead = document.createElement("div");
	customHead.className = "qwen-te-panel__slot-head";
	const customTitle = document.createElement("div");
	customTitle.className = "qwen-te-panel__slot-title";
	customTitle.textContent = "自定义补充";
	const customCount = document.createElement("div");
	customCount.className = "qwen-te-panel__slot-count";
	customCount.dataset.widgetName = "自定义补充标签";
	customHead.append(customTitle, customCount);
	const customInput = document.createElement("textarea");
	customInput.className = "qwen-te-panel__slot-custom";
	customInput.dataset.widgetName = "自定义补充标签";
	customInput.placeholder = "输入不在标签库里的补充标签，用逗号或换行分隔。";
	customInput.value = String(getWidget(node, "自定义补充标签")?.value ?? "");
	bindPanelTextInputEvents(customInput, node, "自定义补充标签");
	customCard.append(customHead, customInput);
	panel.appendChild(customCard);
	panel[SLOT_PANEL_POPULATED_KEY] = true;
	return panel;
}

function buildSlotPanel(node, library) {
	return populateSlotPanel(createSlotPanelShell(library), node, library);
}

function buildLazySlotPanel(library) {
	return createSlotPanelShell(library);
}

function replaceSlotPanelForLibrary(node, library) {
	const panelState = node?.[PANEL_KEY];
	const currentPanel = panelState?.slotPanel;
	if (!(currentPanel instanceof HTMLElement)) return currentPanel ?? null;
	const signature = getSlotPanelLibrarySignature(library);
	if (currentPanel[SLOT_PANEL_LIBRARY_SIGNATURE_KEY] === signature) return currentPanel;
	if (!currentPanel[SLOT_PANEL_POPULATED_KEY]) {
		currentPanel[SLOT_PANEL_LIBRARY_SIGNATURE_KEY] = signature;
		return currentPanel;
	}
	const scrollTop = Number(currentPanel.scrollTop ?? 0) || 0;
	populateSlotPanel(currentPanel, node, library);
	currentPanel.scrollTop = scrollTop;
	return currentPanel;
}

function refreshControlSurface(node) {
	const surface = node?.[PANEL_KEY]?.controlSurface;
	if (!(surface instanceof HTMLElement)) return;
	const rows = surface.querySelectorAll?.(".qwen-te-panel__control-row") ?? [];
	for (const row of rows) {
		const name = String(row.dataset?.widgetName ?? "");
		if (!name) continue;
		const widget = getWidget(node, name);
		const current = widget?.value;
		for (const chip of row.querySelectorAll?.(".qwen-te-panel__control-chip") ?? []) {
			const chipValue = String(chip.dataset?.widgetValue ?? "");
			const active = name === "运行时随机标签" || name === "优先柔和肤质" || name === "抑制文字伪影"
				? String(getBooleanWidgetValue(node, name, false)) === chipValue
				: String(current ?? "") === chipValue;
			chip.classList.toggle("is-active", active);
		}
	}
	const hint = surface.querySelector?.(".qwen-te-panel__control-hint");
	if (hint) {
		const randomText = getBooleanWidgetValue(node, "运行时随机标签", false)
			? `随机 ${getWidgetDisplayValue(node, "运行时随机强度", "中")}`
			: "随机关";
		hint.textContent = `${getWidgetDisplayValue(node, "模板风格", "自动")} / ${getWidgetDisplayValue(node, "提示词语言", "纯中文")} / ${randomText}`;
		hint.title = hint.textContent;
	}
}

function refreshSlotPanel(node) {
	const panelState = node?.[PANEL_KEY];
	let panel = panelState?.slotPanel;
	if (!(panel instanceof HTMLElement)) return;
	panel = replaceSlotPanelForLibrary(node, panelState?.library ?? { slot_config: [], tag_library: {} }) ?? panel;
	const groupCounts = new Map();
	for (const row of panel.querySelectorAll?.(".qwen-te-panel__slot-row") ?? []) {
		const name = String(row.dataset?.widgetName ?? "");
		const groupName = String(row.dataset?.groupName ?? "");
		const widget = getWidget(node, name);
		if (!widget) continue;
		for (const input of row.querySelectorAll?.(".qwen-te-panel__slot-select") ?? []) {
			if (document.activeElement !== input) input.value = String(widget.value ?? "无");
			const filled = !!widget.value && widget.value !== "无";
			input.classList.toggle("is-filled", filled);
			if (document.activeElement !== input) {
				input.classList.remove("is-invalid");
				input.setCustomValidity?.("");
			}
			if (filled && groupName) groupCounts.set(groupName, (groupCounts.get(groupName) ?? 0) + 1);
		}
	}
	for (const count of panel.querySelectorAll?.(".qwen-te-panel__slot-count") ?? []) {
		const groupName = String(count.dataset?.groupName ?? "");
		if (groupName) count.textContent = `${groupCounts.get(groupName) ?? 0} / ${getTagGroupSlotLimit(panelState?.library, groupName)}`;
		const widgetName = String(count.dataset?.widgetName ?? "");
		if (widgetName === "自定义补充标签") count.textContent = `${parseCustomTags(getWidget(node, widgetName)?.value ?? "").length} 补充`;
	}
	for (const input of panel.querySelectorAll?.(".qwen-te-panel__slot-custom") ?? []) {
		if (document.activeElement === input) continue;
		input.value = String(getWidget(node, input.dataset?.widgetName)?.value ?? "");
	}
}

function refreshAdvancedPanel(node, options = {}) {
	const panel = node?.[PANEL_KEY]?.advancedPanel;
	if (!(panel instanceof HTMLElement)) return;
	const force = !!options.force;
	for (const row of panel.querySelectorAll?.(".qwen-te-panel__advanced-row") ?? []) {
		const name = String(row.dataset?.widgetName ?? "");
		const widget = getWidget(node, name);
		if (!name || !widget) continue;
		for (const chip of row.querySelectorAll?.(".qwen-te-panel__advanced-chip") ?? []) {
			chip.classList.toggle("is-active", String(widget.value ?? "") === String(chip.dataset?.widgetValue ?? ""));
		}
		for (const select of row.querySelectorAll?.(".qwen-te-panel__advanced-select") ?? []) {
			select.value = String(widget.value ?? "");
		}
		for (const input of row.querySelectorAll?.(".qwen-te-panel__advanced-input") ?? []) {
			if (!force && document.activeElement === input) continue;
			input.value = String(widget.value ?? "");
		}
	}
}

function setSlotPanelVisible(node, visible) {
	const panelState = node?.[PANEL_KEY];
	const panel = panelState?.slotPanel;
	if (!(panel instanceof HTMLElement)) return false;
	if (visible) populateSlotPanel(panel, node, panelState?.library ?? { slot_config: [], tag_library: {} });
	panel.classList.toggle("qwen-te-hidden", !visible);
	refreshSlotPanel(node);
	scheduleNodeLayoutUpdate(node);
	return true;
}

function setAdvancedPanelVisible(node, visible) {
	const panel = node?.[PANEL_KEY]?.advancedPanel;
	if (!(panel instanceof HTMLElement)) return false;
	panel.classList.toggle("qwen-te-hidden", !visible);
	refreshAdvancedPanel(node);
	scheduleNodeLayoutUpdate(node);
	return true;
}

function parseTagBlockComposerState(raw) {
	if (!String(raw ?? "").trim()) return { version: 1, enabled: false, blocks: [] };
	try {
		const data = JSON.parse(String(raw ?? ""));
		const blocks = Array.isArray(data?.blocks) ? data.blocks : [];
		return {
			version: Number(data?.version ?? 1) || 1,
			enabled: !!data?.enabled,
			blocks: blocks.map((block, index) => ({
				id: String(block?.id ?? `block_${index + 1}`),
				type: block?.type === "text" ? "text" : "tag_group",
				group: String(block?.group ?? ""),
				label: String(block?.label ?? block?.group ?? (block?.type === "text" ? "文字块" : `标签块${index + 1}`)),
				tags: Array.isArray(block?.tags) ? block.tags.map((tag) => String(tag ?? "").trim()).filter((tag, tagIndex, arr) => tag && tag !== "无" && arr.indexOf(tag) === tagIndex).slice(0, 24) : [],
				text: String(block?.text ?? "").trim(),
				locked: !!block?.locked,
			})).filter((block) => block.type === "text" ? true : (block.tags.length || block.text)),
		};
	} catch (_error) {
		return { version: 1, enabled: false, blocks: [] };
	}
}

function readTagBlockComposerState(node) {
	const raw = getWidget(node, TAG_BLOCK_COMPOSER_JSON_WIDGET_NAME)?.value ?? "";
	const state = parseTagBlockComposerState(raw);
	state.enabled = getBooleanWidgetValue(node, TAG_BLOCK_COMPOSER_ENABLED_WIDGET_NAME, state.enabled);
	return state;
}

function serializeTagBlockComposerState(state) {
	const safeState = parseTagBlockComposerState(JSON.stringify(state ?? {}));
	safeState.enabled = !!state?.enabled;
	return JSON.stringify(safeState);
}

function writeTagBlockComposerState(node, state, options = {}) {
	beginNodeStateMutation(node);
	const next = {
		version: 1,
		enabled: !!state?.enabled,
		blocks: Array.isArray(state?.blocks) ? state.blocks : [],
	};
	setWidgetValue(node, TAG_BLOCK_COMPOSER_ENABLED_WIDGET_NAME, next.enabled);
	setWidgetValue(node, TAG_BLOCK_COMPOSER_JSON_WIDGET_NAME, serializeTagBlockComposerState(next));
	persistNamedWidgetState(node);
	if (options.statusText) setNodeStatusText(node, options.statusText);
	if (options.refresh !== false) {
		refreshStageDisplay(node);
		scheduleNodeLayoutUpdate(node);
	}
	return next;
}

const TAG_BLOCK_NSFW_IMPORT_SECTIONS = [
	{
		label: "NSFW结构",
		fields: ["trigger_words", "scene", "action", "outfit", "mood", "anatomy_terms", "explicit_terms", "adult_action_style", "preset"],
	},
	{
		label: "NSFW选择器",
		fields: ["selector_character", "selector_outfit", "selector_action", "selector_scene", "selector_expression", "selector_prop"],
	},
	{
		label: "NSFW镜头",
		fields: ["camera_movement", "camera_angle", "light_source", "light_type", "lens_type", "focal_length", "color_tone", "visual_style", "effect", "filter"],
	},
];

function collectNsfwWorkspaceTagBlockTerms(workspace, fields) {
	const terms = [];
	const push = (value, normalizeSelector = false) => {
		for (const raw of parseCustomTags(Array.isArray(value) ? value.join("，") : value)) {
			const text = normalizeSelector ? normalizeNsfwSelectorTerm(raw) : raw;
			if (!text || text === "——" || text === "关闭" || terms.includes(text)) continue;
			terms.push(text);
		}
	};
	for (const field of fields ?? []) {
		if (field === "trigger_words") {
			for (const tag of workspace?.trigger_words ?? []) push(tag);
			continue;
		}
		push(workspace?.[field], field.startsWith("selector_"));
	}
	return terms;
}

function buildNsfwWorkspaceTagBlocksForComposer(node, library, existingTags = new Set()) {
	const rawWorkspace = getNodeNsfwWorkspaceState(node, library);
	if (!rawWorkspace) return [];
	const catalog = resolveNsfwWorkspaceCatalog(library);
	const workspace = resolveNsfwEffectiveWorkspace(rawWorkspace, catalog);
	const blocks = [];
	for (const section of TAG_BLOCK_NSFW_IMPORT_SECTIONS) {
		const tags = collectNsfwWorkspaceTagBlockTerms(workspace, section.fields)
			.filter((tag) => !existingTags.has(tag));
		if (!tags.length) continue;
		for (const tag of tags) existingTags.add(tag);
		blocks.push({
			id: `nsfw_${section.label}_${blocks.length + 1}`,
			type: "tag_group",
			group: section.label,
			label: section.label,
			tags,
			text: "",
			locked: false,
		});
	}
	return blocks;
}

function buildTagBlockComposerStateFromNode(node, library) {
	const state = collectNodeState(node, library ?? node?.[PANEL_KEY]?.library ?? { slot_config: [] });
	const blocks = [];
	const importedTags = new Set();
	for (const group of library?.slot_config ?? []) {
		const tags = state.selected?.[group.name] ?? [];
		if (!Array.isArray(tags) || !tags.length) continue;
		for (const tag of tags) importedTags.add(tag);
		blocks.push({
			id: `group_${group.name}_${blocks.length + 1}`,
			type: "tag_group",
			group: group.name,
			label: group.name,
			tags: [...tags],
			text: "",
			locked: false,
		});
	}
	const nsfwBlocks = buildNsfwWorkspaceTagBlocksForComposer(node, library, importedTags);
	blocks.push(...nsfwBlocks);
	const remainingCustomTags = Array.isArray(state.customTags)
		? state.customTags.filter((tag) => tag && !importedTags.has(tag))
		: [];
	if (remainingCustomTags.length) {
		blocks.push({
			id: `custom_${blocks.length + 1}`,
			type: "tag_group",
			group: "自定义补充",
			label: "自定义",
			tags: remainingCustomTags,
			text: "",
			locked: false,
		});
	}
	return { version: 1, enabled: true, blocks };
}

function getTagBlockComposerPayloadForDisplay(node, activeMode, cacheStatus, runningSource) {
	const state = readTagBlockComposerState(node);
	const blockCount = state.blocks.length;
	return {
		text: blockCount ? state.blocks.map((block, index) => {
			if (block.type === "text") return `${index + 1}. 文字块：${block.text}`;
			return `${index + 1}. ${block.label || block.group || "标签块"}：${block.tags.join("、")}`;
		}).join("\n") : "还没有标签块。点击“导入标签”把当前已选标签打包成可拖拽块。",
		empty: !blockCount,
		source: blockCount
			? `${activeMode.source} · ${state.enabled ? "已启用" : "未启用"} · ${blockCount} 块`
			: cacheStatus === "running" ? runningSource : "等待编排",
		state,
	};
}

function moveTagBlockComposerBlock(node, fromIndex, toIndex) {
	const state = readTagBlockComposerState(node);
	const blocks = [...state.blocks];
	if (fromIndex < 0 || fromIndex >= blocks.length || toIndex < 0 || toIndex >= blocks.length || fromIndex === toIndex) return;
	const [item] = blocks.splice(fromIndex, 1);
	blocks.splice(toIndex, 0, item);
	state.blocks = blocks;
	writeTagBlockComposerState(node, state, { statusText: "已调整标签块顺序。" });
}

function removeTagBlockComposerBlock(node, index) {
	const state = readTagBlockComposerState(node);
	state.blocks = state.blocks.filter((_block, blockIndex) => blockIndex !== index);
	if (!state.blocks.length) state.enabled = false;
	writeTagBlockComposerState(node, state, { statusText: state.blocks.length ? "已删除标签块。" : "标签块已清空。" });
}

function removeTagBlockComposerTag(node, blockIndex, tagIndex) {
	const state = readTagBlockComposerState(node);
	const block = state.blocks[blockIndex];
	if (!block || block.type === "text" || !Array.isArray(block.tags)) return;
	const removed = block.tags[tagIndex];
	block.tags = block.tags.filter((_tag, index) => index !== tagIndex);
	if (!block.tags.length && !block.locked) {
		state.blocks = state.blocks.filter((_item, index) => index !== blockIndex);
	}
	if (!state.blocks.length) state.enabled = false;
	writeTagBlockComposerState(node, state, {
		statusText: removed ? `已删除标签：${removed}` : "已删除标签。",
	});
}

function insertTagBlockComposerTextBlock(node) {
	const state = readTagBlockComposerState(node);
	state.blocks = [...state.blocks, { id: `text_${Date.now()}`, type: "text", group: "文字块", label: "文字块", tags: [], text: "在这里补充你想保留的画面要求", locked: false }];
	state.enabled = true;
	writeTagBlockComposerState(node, state, { statusText: "已插入文字块，可直接编辑。" });
}

function importCurrentTagsToTagBlocks(node) {
	const library = node?.[PANEL_KEY]?.library ?? { slot_config: [] };
	const state = buildTagBlockComposerStateFromNode(node, library);
	writeTagBlockComposerState(node, state, {
		statusText: state.blocks.length ? `已导入 ${state.blocks.length} 个标签块。` : "当前没有已选标签可导入。",
	});
}

async function runTagBlockComposer(node) {
	let state = readTagBlockComposerState(node);
	if (!state.blocks.length) {
		state = buildTagBlockComposerStateFromNode(node, node?.[PANEL_KEY]?.library ?? { slot_config: [] });
	}
	if (!state.blocks.length) {
		setNodeStatusText(node, "请先选择标签，或在编排里插入文字块。");
		return;
	}
	state.enabled = true;
	writeTagBlockComposerState(node, state, { refresh: true, statusText: "标签块编排已启用，正在加入队列。" });
	if (node?.[PANEL_KEY]) {
		node[PANEL_KEY].displayMode = "prompt";
		refreshStageDisplay(node);
	}
	const queued = await queueWorkflowFromNode(node);
	setNodeStatusText(node, queued ? "标签块编排已加入队列，将按模型按钮设置生成。" : "标签块编排已启用，但未能自动加入队列。");
}

function renderInlineTagBlockComposer(node, bodyEl, payload) {
	bodyEl.classList.add("qwen-te-panel__display-screen--blocks");
	bodyEl.classList.remove("qwen-te-panel__display-screen--smart");
	bodyEl.classList.toggle("is-empty", !!payload.empty);
	const state = readTagBlockComposerState(node);
	bodyEl.replaceChildren();
	const toolbar = document.createElement("div");
	toolbar.className = "qwen-te-panel__block-toolbar";
	const buttonSpecs = [
		["导入标签", () => importCurrentTagsToTagBlocks(node), ""],
		["插入文字", () => insertTagBlockComposerTextBlock(node), ""],
		["生成提示词", () => { void runTagBlockComposer(node); }, "qwen-te-panel__block-button--run"],
		[state.enabled ? "停用编排" : "启用编排", () => {
			const next = readTagBlockComposerState(node);
			next.enabled = !next.enabled;
			writeTagBlockComposerState(node, next, { statusText: next.enabled ? "标签块编排已启用。" : "标签块编排已停用。" });
		}, ""],
		["重新导入", () => importCurrentTagsToTagBlocks(node), ""],
		["清空编排", () => writeTagBlockComposerState(node, { version: 1, enabled: false, blocks: [] }, { statusText: "标签块编排已清空。" }), "qwen-te-panel__block-button--danger"],
	];
	for (const [label, onClick, extraClass] of buttonSpecs) {
		const button = document.createElement("button");
		button.type = "button";
		button.className = `qwen-te-panel__block-button ${extraClass}`.trim();
		button.textContent = label;
		for (const eventName of ["pointerdown", "mousedown", "click"]) {
			button.addEventListener(eventName, (event) => event.stopPropagation());
		}
		button.addEventListener("click", onClick);
		toolbar.appendChild(button);
	}
	bodyEl.appendChild(toolbar);
	const status = document.createElement("div");
	status.className = "qwen-te-panel__block-status";
	status.textContent = state.blocks.length
		? `${state.enabled ? "已启用" : "未启用"} · ${state.blocks.length} 个块 · 可拖拽排序，也可插入文字块后再生成。`
		: "把当前已选标签导入为块，或插入文字块；生成时会按块顺序交给 Skill / 本地模型 / API。";
	bodyEl.appendChild(status);
	const list = document.createElement("div");
	list.className = "qwen-te-panel__block-list";
	if (!state.blocks.length) {
		const empty = document.createElement("div");
		empty.className = "qwen-te-panel__block-empty";
		empty.textContent = "暂无标签块。建议先点“导入标签”，再拖动排列：主体、风格、服装、场景、动作、光影、道具、画质。";
		list.appendChild(empty);
	}
	state.blocks.forEach((block, index) => {
		const card = document.createElement("div");
		card.className = "qwen-te-panel__block-card";
		const isCustomBlock = block.type !== "text" && (block.label === "自定义" || block.group === "自定义补充");
		card.classList.toggle("qwen-te-panel__block-card--custom", isCustomBlock);
		card.classList.toggle("is-locked", !!block.locked);
		card.draggable = true;
		card.dataset.blockIndex = String(index);
		card.addEventListener("dragstart", (event) => {
			event.dataTransfer?.setData("text/plain", String(index));
		});
		card.addEventListener("dragover", (event) => {
			event.preventDefault();
			card.classList.add("is-drag-over");
		});
		card.addEventListener("dragleave", () => card.classList.remove("is-drag-over"));
		card.addEventListener("drop", (event) => {
			event.preventDefault();
			card.classList.remove("is-drag-over");
			const from = Number(event.dataTransfer?.getData("text/plain") ?? -1);
			moveTagBlockComposerBlock(node, from, index);
		});
		const head = document.createElement("div");
		head.className = "qwen-te-panel__block-head";
		const titleWrap = document.createElement("div");
		const title = document.createElement("div");
		title.className = "qwen-te-panel__block-title";
		title.textContent = block.type === "text" ? `${index + 1}. ${block.label || "文字块"}` : `${index + 1}. ${block.label || block.group || "标签块"}`;
		const sub = document.createElement("div");
		sub.className = "qwen-te-panel__block-sub";
		sub.textContent = block.type === "text" ? "用户插入文字，会进入同一条提示词主线" : `${block.tags.length} 个标签`;
		titleWrap.appendChild(title);
		titleWrap.appendChild(sub);
		head.appendChild(titleWrap);
		const actions = document.createElement("div");
		actions.className = "qwen-te-panel__block-actions";
		const actionSpecs = [
			["上", () => moveTagBlockComposerBlock(node, index, Math.max(0, index - 1))],
			["下", () => moveTagBlockComposerBlock(node, index, Math.min(state.blocks.length - 1, index + 1))],
			[block.locked ? "解" : "锁", () => {
				const next = readTagBlockComposerState(node);
				if (next.blocks[index]) next.blocks[index].locked = !next.blocks[index].locked;
				writeTagBlockComposerState(node, next, { statusText: next.blocks[index]?.locked ? "标签块已锁定。" : "标签块已解锁。" });
			}],
			["删", () => removeTagBlockComposerBlock(node, index)],
		];
		for (const [label, onClick] of actionSpecs) {
			const action = document.createElement("button");
			action.type = "button";
			action.className = "qwen-te-panel__block-action";
			action.textContent = label;
			action.addEventListener("pointerdown", (event) => event.stopPropagation());
			action.addEventListener("mousedown", (event) => event.stopPropagation());
			action.addEventListener("click", (event) => {
				event.stopPropagation();
				onClick();
			});
			actions.appendChild(action);
		}
		head.appendChild(actions);
		card.appendChild(head);
		if (block.type === "text") {
			const input = document.createElement("textarea");
			input.className = "qwen-te-panel__block-text";
			input.value = block.text;
			input.placeholder = "输入一段要插入提示词主线的文字，例如：保持冷色调，人物在画面左侧，背景不要喧宾夺主。";
			for (const eventName of ["pointerdown", "pointerup", "mousedown", "mouseup", "click", "dblclick", "keydown", "keyup", "keypress", "compositionstart", "compositionupdate", "compositionend", "wheel"]) {
				input.addEventListener(eventName, stopCanvasTextInputEvent, { passive: eventName !== "wheel" });
			}
			input.addEventListener("input", () => {
				const next = readTagBlockComposerState(node);
				if (next.blocks[index]) next.blocks[index].text = input.value;
				writeTagBlockComposerState(node, next, { refresh: false });
			});
			card.appendChild(input);
		} else {
			const chips = document.createElement("div");
			chips.className = "qwen-te-panel__block-chip-list";
			block.tags.forEach((tag, tagIndex) => {
				const chip = document.createElement("button");
				chip.type = "button";
				chip.className = "qwen-te-panel__block-chip";
				chip.title = `删除标签：${tag}`;
				const label = document.createElement("span");
				label.textContent = tag;
				const removeMark = document.createElement("span");
				removeMark.className = "qwen-te-panel__block-chip-remove";
				removeMark.textContent = "×";
				chip.appendChild(label);
				chip.appendChild(removeMark);
				chip.addEventListener("pointerdown", (event) => event.stopPropagation());
				chip.addEventListener("mousedown", (event) => event.stopPropagation());
				chip.addEventListener("click", (event) => {
					event.stopPropagation();
					removeTagBlockComposerTag(node, index, tagIndex);
				});
				chips.appendChild(chip);
			});
			card.appendChild(chips);
		}
		list.appendChild(card);
	});
	bodyEl.appendChild(list);
}

function renderInlineSmartTextDisplay(node, bodyEl, payload, displayText) {
	bodyEl.classList.add("qwen-te-panel__display-screen--smart");
	bodyEl.classList.remove("qwen-te-panel__display-screen--blocks");
	bodyEl.classList.toggle("is-empty", !!payload.empty);
	if (bodyEl.__qwenSmartUi?.input?.parentNode !== bodyEl || bodyEl.__qwenSmartUi?.result?.parentNode !== bodyEl) {
		delete bodyEl.__qwenSmartUi;
	}
	if (!bodyEl.__qwenSmartUi) {
		bodyEl.replaceChildren();
		const input = document.createElement("textarea");
		input.className = "qwen-te-panel__smart-input";
		input.placeholder = "在这里写一句简单或复杂描述，例如：杂志封面感，成年女性，全身人像，浴室蒸汽，湿发。";
		for (const eventName of ["pointerdown", "pointerup", "mousedown", "mouseup", "click", "dblclick", "keydown", "keyup", "keypress", "compositionstart", "compositionupdate", "compositionend", "wheel"]) {
			input.addEventListener(eventName, stopCanvasTextInputEvent, { passive: eventName !== "wheel" });
		}
		input.addEventListener("pointerdown", () => {
			setTimeout(() => {
				try { input.focus({ preventScroll: true }); } catch (_error) { input.focus(); }
			}, 0);
		});
		input.addEventListener("input", () => {
			const widget = getWidget(node, "智能文本输入");
			if (widget) setControlWidgetValue(node, "智能文本输入", input.value);
		});
		input.addEventListener("keydown", async (event) => {
			if (event.isComposing || !(event.ctrlKey || event.metaKey) || event.key !== "Enter") return;
			event.preventDefault();
			event.stopPropagation();
			await runSmartTextMatch(node, input.value);
		});
		const row = document.createElement("div");
		row.className = "qwen-te-panel__smart-row";
		const hint = document.createElement("div");
		hint.className = "qwen-te-panel__smart-hint";
		hint.textContent = "输入后点匹配启用，或 Ctrl+Enter 快速匹配；节点会自动匹配标签并调用模型生成连贯文本。";
		row.appendChild(hint);
		const button = document.createElement("button");
		button.type = "button";
		button.className = "qwen-te-panel__smart-button";
		button.addEventListener("pointerdown", (event) => { event.stopPropagation(); });
		button.addEventListener("mousedown", (event) => { event.stopPropagation(); });
		button.addEventListener("click", async (event) => {
			event.stopPropagation();
			await runSmartTextMatch(node, input.value);
		});
		row.appendChild(button);
		const result = document.createElement("div");
		result.className = "qwen-te-panel__smart-result";
		result.setAttribute("role", "status");
		result.setAttribute("aria-live", "polite");
		const resultLead = document.createElement("div");
		resultLead.className = "qwen-te-panel__smart-result-lead";
		const resultBody = document.createElement("div");
		resultBody.className = "qwen-te-panel__smart-result-body";
		result.appendChild(resultLead);
		result.appendChild(resultBody);
		bodyEl.appendChild(input);
		bodyEl.appendChild(row);
		bodyEl.appendChild(result);
		bodyEl.__qwenSmartUi = { input, hint, button, result, resultLead, resultBody };
	}
	const ui = bodyEl.__qwenSmartUi;
	const current = String(getWidget(node, "智能文本输入")?.value ?? getWidget(node, "额外要求")?.value ?? "");
	if (document.activeElement !== ui.input && ui.input.value !== current) ui.input.value = current;
	const previewText = String(displayText || "").trim();
	const nsfwEnabled = isNsfwWorkspaceEnabledInState(collectNodeState(node, node?.[PANEL_KEY]?.library ?? { slot_config: [] }));
	const currentState = collectNodeState(node, node?.[PANEL_KEY]?.library ?? { slot_config: [] });
	const contextCount = Object.values(currentState?.selected ?? {}).reduce((sum, tags) => sum + (Array.isArray(tags) ? tags.length : 0), 0) + (currentState?.customTags?.length ?? 0);
	updateSmartTextMatchButtonState(node, ui.button, ui.hint);
	ui.resultLead.textContent = payload.empty
		? `还没有可显示的智能文本预览 · ${nsfwEnabled ? "成人向成熟" : "普通策略"} · 上下文 ${contextCount}`
		: `智能文本预览 · ${nsfwEnabled ? "成人向成熟" : "普通策略"} · 上下文 ${contextCount}`;
	renderSmartPreviewBody(ui.resultBody, previewText || "这里会显示模型生成的连贯提示词预览。请在上方输入描述后点击“匹配启用”；如果 NSFW 已开启，会自动走成人向成熟策略。");
	ui.result.classList.toggle("is-empty", !!payload.empty);
}

function updateSmartTextMatchButtonState(node, button, hint = null) {
	const running = !!node?.[PANEL_KEY]?.smartTextMatchRunning;
	if (isButtonLikeElement(button)) {
		button.disabled = running;
		button.textContent = running ? "匹配中" : "匹配启用";
		button.setAttribute?.("aria-busy", running ? "true" : "false");
	}
	if (hint instanceof HTMLElement) {
		hint.textContent = running
			? "正在写入智能文本并加入队列，请等待本次匹配完成。"
			: "输入后点匹配启用，或 Ctrl+Enter 快速匹配；节点会自动匹配标签并调用模型生成连贯文本。";
	}
}

function renderSmartPreviewBody(target, text) {
	if (!(target instanceof HTMLElement)) return;
	const raw = String(text ?? "").replace(/\r\n/gu, "\n").trim();
	target.replaceChildren();
	const lines = raw ? raw.split(/\n+/u).map((line) => line.trim()).filter(Boolean) : [];
	if (!lines.length) {
		target.textContent = "";
		return;
	}
	lines.forEach((line, index) => {
		const row = document.createElement("div");
		row.className = "qwen-te-panel__smart-preview-line";
		if (index === 0) row.classList.add("qwen-te-panel__smart-preview-line--hero");
		const match = line.match(/^(主体|场景|动作|光影|镜头|画质|构图|服装|表情|氛围|提示词)\s*[:：]\s*(.*)$/u);
		if (match) {
			row.classList.add("qwen-te-panel__smart-preview-line--key");
			row.dataset.smartKey = getSmartPreviewKeyType(String(match[1] ?? ""));
			const label = document.createElement("span");
			label.className = "qwen-te-panel__smart-preview-label";
			label.textContent = `${match[1]}：`;
			const value = document.createElement("span");
			value.className = "qwen-te-panel__smart-preview-value";
			appendSmartPreviewValue(value, String(match[2] ?? ""));
			row.appendChild(label);
			row.appendChild(value);
		} else {
			row.textContent = line;
		}
		target.appendChild(row);
	});
}

function getSmartPreviewKeyType(label) {
	if (label === "主体" || label === "表情" || label === "服装") return "subject";
	if (label === "场景" || label === "氛围") return "scene";
	if (label === "镜头" || label === "构图") return "lens";
	if (label === "光影" || label === "画质") return "light";
	return "general";
}

function appendSmartPreviewValue(target, text) {
	const parts = String(text ?? "").split(/[，,、]/u).map((item) => item.trim()).filter(Boolean);
	if (parts.length <= 1) {
		target.textContent = String(text ?? "");
		return;
	}
	for (const part of parts) {
		const chip = document.createElement("span");
		chip.className = "qwen-te-panel__smart-preview-chip";
		chip.textContent = part;
		target.appendChild(chip);
	}
}

function getCurrentThemePool(node) {
	return String(getWidget(node, "随机主题池")?.value ?? PRESET_SETTING_DEFAULTS["随机主题池"] ?? "自动").trim() || "自动";
}

function buildThemePoolQuickStatusText(node) {
	const themePool = getCurrentThemePool(node);
	const runtimeRandomEnabled = getBooleanWidgetValue(node, "运行时随机标签", false);
	const randomMode = String(getWidget(node, "运行时随机模式")?.value ?? PRESET_SETTING_DEFAULTS["运行时随机模式"] ?? "全随机");
	const bits = [`当前 ${themePool}`];
	bits.push(runtimeRandomEnabled ? `随机 ${randomMode}` : "随机未开");
	bits.push(
		QUICK_THEME_POOL_CARD_VALUES.has(themePool)
			? "高级里还有旅行 / 私房 / 暗黑 / 东方赛博 / 废土等完整主题"
			: "当前值不在快捷卡，去高级参数看完整列表",
	);
	return bits.join(" · ");
}

function refreshThemePoolQuickCards(node) {
	const buttons = node?.[PANEL_KEY]?.themePoolQuickCardButtons;
	const statusEl = node?.[PANEL_KEY]?.themePoolQuickStatusEl;
	const currentThemePool = getCurrentThemePool(node);
	if (buttons instanceof Map) {
		for (const [value, button] of buttons.entries()) {
			if (!isButtonLikeElement(button)) continue;
			const active = value === currentThemePool;
			button.classList.toggle("is-active", active);
			button.setAttribute?.("aria-pressed", active ? "true" : "false");
		}
	}
	if (statusEl instanceof HTMLElement) {
		const text = buildThemePoolQuickStatusText(node);
		statusEl.textContent = text;
		statusEl.title = text;
	}
}

function applyThemePoolQuickPick(node, themePool) {
	const nextValue = String(themePool ?? "").trim() || PRESET_SETTING_DEFAULTS["随机主题池"];
	if (getCurrentThemePool(node) !== nextValue) setControlWidgetValue(node, "随机主题池", nextValue);
	const runtimeRandomEnabled = getBooleanWidgetValue(node, "运行时随机标签", false);
	const randomMode = String(getWidget(node, "运行时随机模式")?.value ?? PRESET_SETTING_DEFAULTS["运行时随机模式"] ?? "全随机");
	const prefix = nextValue === "自动" ? "已切回随机主题池：自动。" : `已切换随机主题池：${nextValue}。`;
	const suffix = runtimeRandomEnabled
		? `当前运行时随机为 ${randomMode}，下一次随机会更明显朝这个方向发散。`
		: "当前运行时随机未开启，主题池仍会参与偏置；想更明显可开启运行时随机标签。";
	setNodeStatusText(node, `${prefix}${suffix}`);
	refreshThemePoolQuickCards(node);
}

function syncPanelToggleButton(node, buttonKey, widgetName, labels, hints) {
	const button = node?.[PANEL_KEY]?.panelButtons?.[buttonKey];
	if (!isButtonLikeElement(button)) return;
	const enabled = getBooleanWidgetValue(node, widgetName, false);
	const labelEl = button.querySelector?.(".qwen-te-panel__button-label");
	if (labelEl) labelEl.textContent = enabled ? labels.on : labels.off;
	button.classList.toggle("is-active", enabled);
	button.dataset ??= {};
	button.dataset.qwenHint = enabled ? hints.on : hints.off;
	if (!button.disabled) button.title = button.dataset.qwenHint;
}

function syncHeroToggleBadge(node, badgeKey, widgetName, labels, hints) {
	const badge = node?.[PANEL_KEY]?.heroBadges?.[badgeKey];
	if (!isButtonLikeElement(badge)) return;
	const enabled = getBooleanWidgetValue(node, widgetName, false);
	badge.textContent = enabled ? labels.on : labels.off;
	badge.classList.toggle("qwen-te-panel__hero-badge--secondary", !enabled);
	badge.classList.toggle("is-active", enabled);
	badge.dataset ??= {};
	badge.dataset.qwenHint = enabled ? hints.on : hints.off;
	if (!badge.disabled) badge.title = badge.dataset.qwenHint;
}

function syncNsfwWorkspaceButton(node, library) {
	const button = node?.[PANEL_KEY]?.panelButtons?.nsfwWorkspace;
	if (!isButtonLikeElement(button)) return;
	const workspace = getNodeNsfwWorkspaceState(node, library);
	const enabled = !!workspace?.enabled;
	const labelEl = button.querySelector?.(".qwen-te-panel__button-label");
	if (labelEl) labelEl.textContent = enabled ? "NSFW开" : "NSFW";
	button.classList.toggle("is-active", enabled);
	button.setAttribute?.("aria-pressed", enabled ? "true" : "false");
	button.dataset ??= {};
	button.dataset.qwenHint = enabled
		? "NSFW 工作台已启用：运行时会进入成人向标签与负面词分支。"
		: "打开 NSFW 工作台；写回后会自动切到成人向标签策略。";
	if (!button.disabled) button.title = button.dataset.qwenHint;
}

function syncCharacterSheetButton(node) {
	const button = node?.[PANEL_KEY]?.panelButtons?.characterSheet;
	if (!isButtonLikeElement(button)) return;
	const enabled = getBooleanWidgetValue(node, "图片反推生成", false) && getWidgetDisplayValue(node, "图片反推模式", "角色设定图") === "角色设定图";
	const labelEl = button.querySelector?.(".qwen-te-panel__button-label");
	if (labelEl) labelEl.textContent = enabled ? "设定图开" : "设定图";
	button.classList.toggle("is-active", enabled);
	button.setAttribute?.("aria-pressed", enabled ? "true" : "false");
	button.dataset ??= {};
	button.dataset.qwenHint = enabled
		? "角色设定图已启用：运行时会把当前提示词/标签组织成三视图；有参考图时会先反推。"
		: "打开角色设定图面板；启用后才会生成三视图，停用则保持原样输出。";
	if (!button.disabled) button.title = button.dataset.qwenHint;
}

function refreshNodeActionButtons(node) {
	const panelButtons = node?.[PANEL_KEY]?.panelButtons;
	if (!panelButtons || typeof panelButtons !== "object") return;
	const library = node?.[PANEL_KEY]?.library;
	const runtime = ensureNodeContinuousRuntime(node);
	const isContinuousRunning = !!runtime.running;

	setPanelActionButtonState(panelButtons.tag, !isContinuousRunning, "连续测试进行中，先停止后再改标签。");
	setPanelActionButtonState(panelButtons.onlineSearch, !isContinuousRunning, "连续测试进行中，先停止后再搜索和回填标签。");
	setPanelActionButtonState(panelButtons.example, !isContinuousRunning, "连续测试进行中，先停止后再载入示例。");
	setPanelActionButtonState(panelButtons.random, !isContinuousRunning, "连续测试进行中，先停止后再随机。");
	setPanelActionButtonState(panelButtons.randomRun, !isContinuousRunning, "连续测试进行中，先停止后再随机跑。");
	setPanelActionButtonState(panelButtons.presets, !isContinuousRunning, "连续测试进行中，先停止后再管理预设。");
	setPanelActionButtonState(panelButtons.history, !isContinuousRunning, "连续测试进行中，先停止后再管理历史。");
	setPanelActionButtonState(panelButtons.clearTags, !isContinuousRunning, "连续测试进行中，先停止后再清空标签。");
	const slotPanelOpen = node?.[PANEL_KEY]?.slotPanel instanceof HTMLElement && !node[PANEL_KEY].slotPanel.classList.contains("qwen-te-hidden");
	setPanelToggleButtonState(panelButtons.toggleRawSlots, slotPanelOpen, "收槽位", "槽位");
	const advancedPanelOpen = node?.[PANEL_KEY]?.advancedPanel instanceof HTMLElement && !node[PANEL_KEY].advancedPanel.classList.contains("qwen-te-hidden");
	setPanelToggleButtonState(panelButtons.toggleAdvanced, advancedPanelOpen, "收高级", "高级");
	refreshThemePoolQuickCards(node);
	const themePoolQuickCardButtons = node?.[PANEL_KEY]?.themePoolQuickCardButtons;
	if (themePoolQuickCardButtons instanceof Map) {
		for (const button of themePoolQuickCardButtons.values()) {
			setPanelActionButtonState(button, !isContinuousRunning, "连续测试进行中，先停止后再切换主题池。");
		}
	}
	refreshControlSurface(node);
	refreshSlotPanel(node);
	refreshAdvancedPanel(node);
	if (library) syncNsfwWorkspaceButton(node, library);
	syncCharacterSheetButton(node);
	if (library && node?.[PANEL_KEY]?.heroCaptionEl instanceof HTMLElement) {
		node[PANEL_KEY].heroCaptionEl.textContent = buildHeroCaptionText(node, library);
	}
	const onlineSearchOverlay = document.querySelector?.('[data-qwen-modal="online-search"]');
	if (onlineSearchOverlay?.__qwenNode === node) onlineSearchOverlay.__qwenSyncRuntimeState?.();
}

function setNodeStatusText(node, text) {
	const message = String(text ?? "");
	if (node?.[PANEL_KEY]) node[PANEL_KEY].lastPanelMessage = message;
	if (node?.[PANEL_KEY]?.statusEl instanceof HTMLElement) node[PANEL_KEY].statusEl.textContent = message;
	if (node?.[PANEL_KEY]?.statusWidget) node[PANEL_KEY].statusWidget.value = message;
	refreshNodeActionButtons(node);
	if (node?.[PANEL_KEY]?.summaryEl && node?.[PANEL_KEY]?.library) refreshNodeSummary(node, node[PANEL_KEY].library);
}

function buildStageOutputDiagnostics(node) {
	const panelState = node?.[PANEL_KEY];
	const activeMode = panelState?.displayMode ?? STAGE_DISPLAY_MODES[0]?.key ?? "prompt";
	const latestHistoryStageOutput = getNodeLatestHistoryStageOutput(node);
	const resolvedOutputs = STAGE_OUTPUT_FIELD_KEYS.map((fieldKey, index) => {
		const entry = getStageOutputEntry(node, index);
		return {
			index,
			fieldKey,
			value: String(entry?.value ?? ""),
			source: String(entry?.source ?? ""),
			sourceKey: String(entry?.sourceKey ?? ""),
		};
	});
	const linkedOutputs = (node?.outputs ?? []).map((output, index) => ({
		index,
		name: String(output?.name ?? `output_${index}`),
		links: collectLinkedStageOutputCandidates(node, index).map((candidate) => ({
			linkId: candidate.linkId,
			targetId: candidate.targetId,
			targetType: candidate.targetType,
			targetTitle: candidate.targetTitle,
			targetSlot: candidate.targetSlot,
			score: candidate.score,
			textValue: candidate.value,
			textWidgets: candidate.textWidgets,
			widgetsValues: candidate.widgetsValues,
		})),
	}));
	return {
		nodeId: Number(node?.id ?? 0) || 0,
		nodeType: String(node?.type ?? ""),
		nodeTitle: String(node?.title ?? ""),
		displayMode: activeMode,
		displayPayload: getStageDisplayPayload(node, activeMode),
		lastExecutedAt: Number(panelState?.lastExecutedAt ?? 0) || 0,
		directStageOutputCache: panelState?.directStageOutputCache && typeof panelState.directStageOutputCache === "object"
			? {
				status: String(panelState.directStageOutputCache.status ?? ""),
				updatedAt: Number(panelState.directStageOutputCache.updated_at ?? 0) || 0,
				staleForCurrentRun: !!panelState.directStageOutputCache._qwenStaleForCurrentRun,
				outputs: STAGE_OUTPUT_FIELD_KEYS.map((_, index) => getDirectStageOutputValue(panelState.directStageOutputCache, index)),
			}
			: null,
		lastExecutionOutputs: Array.isArray(panelState?.lastExecutionOutputs) ? panelState.lastExecutionOutputs.map((value) => String(value ?? "")) : [],
		previewExecutionOutputs: Array.isArray(panelState?.previewExecutionOutputs) ? panelState.previewExecutionOutputs.map((value) => String(value ?? "")) : [],
		previewSource: String(panelState?.displayPreviewSource ?? ""),
		hydratedExecutionOutputs: Array.isArray(panelState?.hydratedExecutionOutputs) ? panelState.hydratedExecutionOutputs.map((value) => String(value ?? "")) : [],
		hydratedExecutionSourceLabel: String(panelState?.hydratedExecutionSourceLabel ?? ""),
		workflowMeta: panelState?.workflowOutputMeta && typeof panelState.workflowOutputMeta === "object"
			? {
				promptId: String(panelState.workflowOutputMeta.promptId ?? ""),
				createdAt: Number(panelState.workflowOutputMeta.createdAt ?? 0) || 0,
				stageOutputs: Array.isArray(panelState.workflowOutputMeta.stageOutputs)
					? panelState.workflowOutputMeta.stageOutputs.map((value) => String(value ?? ""))
					: [],
			}
			: null,
		historyStageOutput: latestHistoryStageOutput && typeof latestHistoryStageOutput === "object"
			? {
				fullText: String(latestHistoryStageOutput.fullText ?? ""),
				promptText: String(latestHistoryStageOutput.promptText ?? ""),
				selectedTags: String(latestHistoryStageOutput.selectedTags ?? ""),
				jsonResult: String(latestHistoryStageOutput.jsonResult ?? ""),
				negativePrompt: String(latestHistoryStageOutput.negativePrompt ?? ""),
			}
			: null,
		resolvedOutputs,
		linkedOutputs,
	};
}

async function exportStageOutputDiagnostics(node) {
	const report = buildStageOutputDiagnostics(node);
	window.__QWEN_TE_STAGE_LAST_DIAGNOSTICS__ = report;
	const text = JSON.stringify(report, null, 2);
	const copied = await copyToClipboard(text);
	setNodeStatusText(
		node,
		copied
			? "已复制 Stage 诊断 JSON，并写入 window.__QWEN_TE_STAGE_LAST_DIAGNOSTICS__。"
			: "已生成 Stage 诊断 JSON，请在控制台查看 window.__QWEN_TE_STAGE_LAST_DIAGNOSTICS__。",
	);
	return report;
}

function refreshNodeContinuousBadge(node) {
	const badgeEl = node?.[PANEL_KEY]?.continuousBadgeEl;
	if (!(badgeEl instanceof HTMLElement)) return;
	const badgeState = buildContinuousPanelBadgeState(node);
	badgeEl.textContent = badgeState.text;
	badgeEl.title = badgeState.title;
	badgeEl.classList.toggle("qwen-te-panel__hero-badge--secondary", !!badgeState.muted);
}

function refreshNodeContinuousReportSummary(node) {
	const summaryEl = node?.[PANEL_KEY]?.continuousReportSummaryEl;
	if (!(summaryEl instanceof HTMLElement)) return;
	const meta = getNodeContinuousReportMeta(node);
	summaryEl.textContent = meta?.summary ? `${meta.level ?? "记录"} | ${meta.summary}` : "还没有连续测试记录。";
	summaryEl.title = meta?.summary ? String(meta.summary) : "还没有连续测试记录。";
}

function compactNodeHistoryItem(item) {
	if (!item || typeof item !== "object" || !item.state) return null;
	const meta = cloneJsonSafe(item.meta, {});
	const rawStageOutput = meta.stageOutput ?? meta.stage_output ?? null;
	if (rawStageOutput) {
		const stageOutput = compactHistoryStageOutputPayload(rawStageOutput);
		delete meta.stage_output;
		if (stageOutput) meta.stageOutput = stageOutput;
		else delete meta.stageOutput;
	}
	if (meta.qualityAudit && typeof meta.qualityAudit === "object") {
		meta.qualityAudit = {
			...meta.qualityAudit,
			markdown: truncateHistoryText(meta.qualityAudit.markdown, 16384),
		};
	}
	let normalized = {
		id: String(item.id ?? `history_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`).slice(0, 256),
		source: String(item.source ?? "random").slice(0, 128),
		updatedAt: Number(item.updatedAt ?? Date.now()),
		favorite: !!item.favorite,
		summary: truncateHistoryText(item.summary ?? summarizeHistoryState(item.state), 4096),
		state: clonePresetState(item.state),
		meta,
	};
	if (utf8ByteLength(normalized) <= NODE_HISTORY_ITEM_MAX_BYTES) return normalized;
	const stageOutput = compactHistoryStageOutputPayload(meta.stageOutput);
	normalized = {
		...normalized,
		meta: stageOutput ? { stageOutput } : {},
		summary: truncateHistoryText(normalized.summary, 1024),
	};
	return utf8ByteLength(normalized) <= NODE_HISTORY_ITEM_MAX_BYTES ? normalized : null;
}

function boundNodeHistoryItems(history) {
	const result = [];
	const seen = new Set();
	let totalBytes = 2;
	for (const item of history ?? []) {
		if (result.length >= NODE_HISTORY_LIMIT) break;
		const normalized = compactNodeHistoryItem(item);
		if (!normalized || seen.has(normalized.id)) continue;
		const itemBytes = utf8ByteLength(normalized);
		if (totalBytes + itemBytes > NODE_HISTORY_TOTAL_MAX_BYTES) continue;
		seen.add(normalized.id);
		result.push(normalized);
		totalBytes += itemBytes + 1;
	}
	return result;
}

function ensureNodeContinuousRuntime(node) {
	if (!node?.[PANEL_KEY]) return { running: false, token: 0, mode: "", step: 0, total: 0 };
	if (!node[PANEL_KEY].continuousRuntime) node[PANEL_KEY].continuousRuntime = { running: false, token: 0, mode: "", step: 0, total: 0 };
	return node[PANEL_KEY].continuousRuntime;
}

function updateNodeContinuousRuntime(node, patch = {}) {
	const runtime = ensureNodeContinuousRuntime(node);
	Object.assign(runtime, patch);
	refreshNodeContinuousBadge(node);
	return runtime;
}

function getNodeHistory(node) {
	const props = ensureNodeProperties(node);
	if (!Array.isArray(props[NODE_HISTORY_KEY])) props[NODE_HISTORY_KEY] = [];
	if (!BOUNDED_NODE_HISTORY_ARRAYS.has(props[NODE_HISTORY_KEY])) {
		props[NODE_HISTORY_KEY] = boundNodeHistoryItems(props[NODE_HISTORY_KEY]);
		BOUNDED_NODE_HISTORY_ARRAYS.add(props[NODE_HISTORY_KEY]);
	}
	return props[NODE_HISTORY_KEY].filter((item) => item && typeof item === "object" && item.state).slice(0, NODE_HISTORY_LIMIT);
}
function setNodeHistory(node, history) {
	const bounded = boundNodeHistoryItems(history);
	ensureNodeProperties(node)[NODE_HISTORY_KEY] = bounded;
	BOUNDED_NODE_HISTORY_ARRAYS.add(bounded);
	return bounded;
}
function getSortedNodeHistory(node) { return [...getNodeHistory(node)].sort((a,b)=> (+!!b.favorite)-(+!!a.favorite) || Number(b.updatedAt??0)-Number(a.updatedAt??0)); }
function findLatestRollbackHistoryItem(node) {
	const currentLibrary = node?.[PANEL_KEY]?.library;
	const currentSerialized = currentLibrary ? serializeState(collectNodeState(node, currentLibrary)) : "";
	return getNodeHistory(node).find((item) => {
		const source = String(item?.source ?? "");
		if (!(source === "random" || source === "example" || source === "before-random" || source === "before-clear" || source === "nsfw-workspace")) return false;
		return serializeState(item?.state) !== currentSerialized;
	}) ?? null;
}
function serializeState(state) { try { return JSON.stringify(clonePresetState(state)); } catch { return ""; } }
function recordNodeHistory(node, state, source = "random", options = {}) {
	const history = getNodeHistory(node); const serialized = serializeState(state); if (!serialized) return;
	if (options.dedupe && history[0] && serializeState(history[0].state) === serialized) return;
	setNodeHistory(node, [{ id:`history_${Date.now()}_${Math.random().toString(36).slice(2,8)}`, updatedAt:Date.now(), source, favorite:false, summary: options.summary ?? summarizeHistoryState(state), state: clonePresetState(state), meta: cloneJsonSafe(options.meta, {}) }, ...history]);
}
function getHistorySourceLabel(source) { if (source==="before-random") return "随机前"; if (source==="before-clear") return "清空前"; if (source==="clear") return "清空结果"; if (source==="executed") return "运行结果"; if (source==="random") return "随机结果"; if (source==="history-load") return "历史载入"; if (source==="example") return "示例模板"; if (source==="preset-load") return "预设载入"; if (source==="manual-apply") return "手动应用"; if (source==="arrange-preview") return "整理预览"; if (source==="continuous-report") return "连续测试报告"; if (source==="single-preset") return "单预设快照"; if (source==="single-preset-report") return "单预设报告"; if (source==="history-aggregate-report") return "历史聚合报告"; return "记录"; }
function toggleNodeHistoryFavorite(node,id){ setNodeHistory(node, getNodeHistory(node).map((item)=> item.id===id?{...item,favorite:!item.favorite}:item)); }
function deleteNodeHistoryItem(node,id){ setNodeHistory(node, getNodeHistory(node).filter((item)=> item.id!==id)); }
function normalizeNodeHistoryItems(items){ return Array.isArray(items) ? boundNodeHistoryItems(items) : []; }
function exportNodeHistory(node){ const payload={version:1, exportedAt:Date.now(), nodeType:String(node?.comfyClass ?? TARGET_NODE_CLASS), history:getNodeHistory(node)}; const blob=new Blob([JSON.stringify(payload,null,2)],{type:"application/json"}); const url=URL.createObjectURL(blob); const a=document.createElement("a"); a.href=url; a.download=`qwen-te-history-${Date.now()}.json`; document.body.appendChild(a); a.click(); document.body.removeChild(a); URL.revokeObjectURL(url); }
async function importNodeHistoryFile(node,file){ if(Number(file?.size??0)>NODE_HISTORY_IMPORT_MAX_BYTES) throw new Error("历史文件超过 2 MiB 导入上限。"); const text=await file.text(); if(utf8ByteLength(text)>NODE_HISTORY_IMPORT_MAX_BYTES) throw new Error("历史文件超过 2 MiB 导入上限。"); const payload=JSON.parse(text); const imported=normalizeNodeHistoryItems(payload?.history); if(!imported.length) return {ok:false,message:"文件里没有可导入的历史记录。"}; setNodeHistory(node, normalizeNodeHistoryItems([...imported,...getNodeHistory(node)])); return {ok:true,message:`已导入 ${imported.length} 条历史。`}; }
async function queueWorkflowFromNode(node = null) {
	let requestedAt = Date.now();
	try {
		if (node) {
			sanitizeStagePromptNode(node, node[PANEL_KEY]?.library ?? { slot_config: [] });
			persistNamedWidgetState(node);
		}
		const queueButton = document.querySelector("#queue-button")
			|| document.querySelector(".queue-button")
			|| document.querySelector("[data-testid='queue-button']")
			|| document.querySelector("[title*='Queue']");
		const queueButtonDisabled = !!queueButton?.disabled
			|| queueButton?.getAttribute?.("aria-disabled") === "true"
			|| !!queueButton?.classList?.contains?.("disabled")
			|| !!queueButton?.classList?.contains?.("is-disabled");
		if (queueButton instanceof HTMLElement && !queueButtonDisabled) {
			requestedAt = Date.now();
			if (node) markNodeWorkflowQueueRequested(node, requestedAt);
			queueButton.click();
			return true;
		}
		if (typeof app.queuePrompt === "function") {
			try {
				requestedAt = Date.now();
				if (node) markNodeWorkflowQueueRequested(node, requestedAt);
				await app.queuePrompt(0, 1);
				return true;
			} catch (_error) {
				const workflow = app.graph?.serialize?.();
				if (workflow) {
					requestedAt = Date.now();
					if (node) markNodeWorkflowQueueRequested(node, requestedAt);
					await app.queuePrompt(-1, workflow);
					return true;
				}
			}
		}
	} catch (_error) {}
	clearPendingModelApiRun(node);
	return false;
}
async function runSmartTextMatch(node, explicitText = null) {
	if (node?.[PANEL_KEY]?.smartTextMatchRunning) return false;
	const currentSmart = String(getWidget(node, "智能文本输入")?.value ?? "").trim();
	const currentExtra = String(getWidget(node, "额外要求")?.value ?? "").trim();
	const properties = ensureNodeProperties(node);
	const previousAutoExtra = String(properties[NODE_SMART_TEXT_AUTO_EXTRA_KEY] ?? "").trim();
	const shouldSyncAutoExtra = !currentExtra || (!!previousAutoExtra && currentExtra === previousAutoExtra);
	const initialText = currentSmart || currentExtra || String(getCurrentStageOutputText(node, STAGE_OUTPUT_INDEX.promptText) ?? "").trim();
	const promptText = explicitText == null ? initialText : explicitText;
	const text = String(promptText ?? "").trim();
	if (!text) {
		setNodeStatusText(node, "请先在智能文本输入框里写一句描述。");
		if (node?.[PANEL_KEY]) {
			node[PANEL_KEY].displayMode = "smart";
			refreshStageDisplay(node);
		}
		return false;
	}
	const mutationRevision = beginNodeStateMutation(node);
	const nsfwEnabled = isNsfwWorkspaceEnabledInState(collectNodeState(node, node?.[PANEL_KEY]?.library ?? { slot_config: [] }));
	if (node?.[PANEL_KEY]) {
		node[PANEL_KEY].smartTextMatchRunning = true;
		updateSmartTextMatchButtonState(node, node[PANEL_KEY]?.displayBodyEl?.__qwenSmartUi?.button, node[PANEL_KEY]?.displayBodyEl?.__qwenSmartUi?.hint);
	}
	try {
		setWidgetValue(node, "智能文本匹配", true);
		if (nsfwEnabled) {
			setWidgetValue(node, "标签反推模式", "成人向成熟");
			setWidgetValue(node, "模板风格", "真实感");
			setWidgetValue(node, "主体类型", "人物角色");
		}
		setWidgetValue(node, "智能文本输入", text);
		if (shouldSyncAutoExtra) {
			setWidgetValue(node, "额外要求", text);
			properties[NODE_SMART_TEXT_AUTO_EXTRA_KEY] = text;
		} else {
			delete properties[NODE_SMART_TEXT_AUTO_EXTRA_KEY];
		}
		if (node?.[PANEL_KEY]) {
			node[PANEL_KEY].displayMode = "smart";
			refreshStageDisplay(node);
		}
		setNodeStatusText(node, nsfwEnabled ? "智能文本匹配中，已切到成人向成熟策略。" : "智能文本匹配中，正在加入队列。");
		const queued = await queueWorkflowFromNode(node);
		if (!isNodeStateMutationCurrent(node, mutationRevision)) return false;
		setNodeStatusText(node, queued ? (nsfwEnabled ? "智能文本匹配已加入队列，成人向成熟策略已生效。" : "智能文本匹配已加入队列，等待模型输出。") : "已写入智能文本匹配，但没能自动加入队列。");
		return queued;
	} finally {
		if (node?.[PANEL_KEY]) {
			node[PANEL_KEY].smartTextMatchRunning = false;
			updateSmartTextMatchButtonState(node, node[PANEL_KEY]?.displayBodyEl?.__qwenSmartUi?.button, node[PANEL_KEY]?.displayBodyEl?.__qwenSmartUi?.hint);
		}
	}
}
function getNodeExecutionStamp(node){ return Number(node?.[PANEL_KEY]?.lastExecutedAt ?? 0) || 0; }
function sleep(ms){ return new Promise((resolve)=> setTimeout(resolve, ms)); }
async function waitForNodeExecution(node, baselineStamp, timeoutMs = 180000, pollMs = 500, options = {}){
	const start = Date.now();
	while(Date.now() - start < timeoutMs){
		if (node?.[NODE_REMOVED_KEY] || options.shouldCancel?.()) return false;
		if(getNodeExecutionStamp(node) > baselineStamp) return true;
		await sleep(Math.max(10, Number(pollMs) || 500));
		if (node?.[NODE_REMOVED_KEY] || options.shouldCancel?.()) return false;
	}
	return false;
}
function pushNodeContinuousRunReport(node, library, level, message, meta = {}){
	const nextEntry = {
		at: Date.now(),
		level: String(level ?? "记录"),
		message: String(message ?? ""),
		presetName: String(meta.presetName ?? ""),
		origin: String(meta.origin ?? "continuous"),
		round: Math.max(0, Math.trunc(Number(meta.round ?? 0) || 0)),
		total: Math.max(0, Math.trunc(Number(meta.total ?? 0) || 0)),
	};
	const nextReport = [nextEntry, ...getNodeContinuousRunReport(node)].slice(0, 50);
	setNodeContinuousRunReport(node, nextReport);
	setNodeContinuousReportMeta(node, { at: Date.now(), level, summary: message });
	refreshNodeSummary(node, library);
	return nextReport;
}
function clearNodeContinuousRunArtifacts(node, library){
	clearNodeContinuousRunReport(node);
	clearNodeContinuousReportMeta(node);
	updateNodeContinuousRuntime(node, { running: false, mode: "", step: 0, total: 0 });
	refreshNodeSummary(node, library);
}
async function applyPresetStateToNode(node, library, state, options = {}) {
	const mutationRevision = Math.max(0, Number(options.mutationRevision ?? 0) || 0) || beginNodeStateMutation(node);
	const nextLibrary = await getFreshLibraryForUi(node, library, { mutationRevision });
	if (!isNodeStateMutationCurrent(node, mutationRevision)) return { ok: false, queued: false, stale: true, library: nextLibrary };
	if (node?.[PANEL_KEY]) node[PANEL_KEY].library = nextLibrary;
	if (!applyNodeState(node, nextLibrary, clonePresetState(state), { recordHistory: true, historySource: "preset-load", mutationRevision })) {
		return { ok: false, queued: false, stale: true, library: nextLibrary };
	}
	if (options.randomizeAfterLoad) {
		const applied = await buildAndApplyRandomState(node, nextLibrary, { mutationRevision });
		if (!applied) return { ok: false, queued: false, stale: true, library: nextLibrary };
	}
	if (!options.queue) return { ok: true, queued: false, library: nextLibrary };
	if (!isNodeStateMutationCurrent(node, mutationRevision)) return { ok: false, queued: false, stale: true, library: nextLibrary };
	const queued = await queueWorkflowFromNode(node);
	if (!isNodeStateMutationCurrent(node, mutationRevision)) return { ok: false, queued: false, queueSubmitted: queued, stale: true, library: nextLibrary };
	return { ok: queued, queued, library: nextLibrary };
}
async function runNodeContinuousPresetSequence(node, library, selectedPresets, totalRuns, mode = "cycle") {
	if (!selectedPresets.length) {
		setNodeStatusText(node, "连续测试未启动：还没有配置可用的连测预设。");
		return false;
	}
	const qualityAuditStartAt = Date.now();
	const runtime = updateNodeContinuousRuntime(node, { token: ensureNodeContinuousRuntime(node).token + 1, running: true, mode, step: 0, total: totalRuns });
	const token = runtime.token;
	const targetedPromptIds = [];
	const seenPromptIds = new Set();
	clearNodeContinuousRunReport(node);
		pushNodeContinuousRunReport(node, library, "开始", `连续测试启动：${mode === "cycle" ? "轮流" : "随机"}，共 ${totalRuns} 轮，候选 ${selectedPresets.length} 个预设。`, { total: totalRuns, origin: "continuous" });
	setNodeStatusText(node, `连续测试启动：${mode === "cycle" ? "轮流" : "随机"}，共 ${totalRuns} 轮。`);
	for (let step = 0; step < totalRuns; step += 1) {
		if (token !== ensureNodeContinuousRuntime(node).token) return false;
		const preset = mode === "cycle"
			? selectedPresets[step % selectedPresets.length]
			: selectedPresets[Math.floor(Math.random() * selectedPresets.length)];
		updateNodeContinuousRuntime(node, { step: step + 1 });
		const baselineStamp = getNodeExecutionStamp(node);
			pushNodeContinuousRunReport(node, library, "提交", `第 ${step + 1}/${totalRuns} 轮：${preset.name}`, { presetName: preset.name, round: step + 1, total: totalRuns, origin: "continuous" });
		setNodeStatusText(node, `连续测试 ${step + 1}/${totalRuns}：准备提交 ${preset.name}`);
		const result = await applyPresetStateToNode(node, library, preset.state, { queue: true });
		library = result.library;
		if (token !== ensureNodeContinuousRuntime(node).token) return false;
		if (!result.queued) {
				pushNodeContinuousRunReport(node, library, "失败", `第 ${step + 1}/${totalRuns} 轮：${preset.name} 已载入，但未能自动入队。`, { presetName: preset.name, round: step + 1, total: totalRuns, origin: "continuous" });
			updateNodeContinuousRuntime(node, { running: false, step: 0 });
			setNodeStatusText(node, `连续测试中断：${preset.name} 已载入，但未能自动入队。`);
			refreshNodeSummary(node, library);
			return false;
		}
		const queueRequestedAt = getNodeWorkflowQueueRequestedAt(node);
			pushNodeContinuousRunReport(node, library, "入队", `第 ${step + 1}/${totalRuns} 轮：${preset.name} 已入队。`, { presetName: preset.name, round: step + 1, total: totalRuns, origin: "continuous" });
		setNodeStatusText(node, `连续测试 ${step + 1}/${totalRuns}：${preset.name} 已入队，等待执行完成...`);
		const executed = await waitForNodeExecution(node, baselineStamp, 180000, 500, {
			shouldCancel: () => token !== ensureNodeContinuousRuntime(node).token,
		});
		if (token !== ensureNodeContinuousRuntime(node).token) return false;
		if (!executed) {
				pushNodeContinuousRunReport(node, library, "超时", `第 ${step + 1}/${totalRuns} 轮：${preset.name} 等待执行完成超时。`, { presetName: preset.name, round: step + 1, total: totalRuns, origin: "continuous" });
			updateNodeContinuousRuntime(node, { running: false, step: 0 });
			setNodeStatusText(node, `连续测试超时：${preset.name} 在等待执行完成时超过限制。`);
			refreshNodeSummary(node, library);
			return false;
		}
			pushNodeContinuousRunReport(node, library, "完成", `第 ${step + 1}/${totalRuns} 轮：${preset.name} 执行完成。`, { presetName: preset.name, round: step + 1, total: totalRuns, origin: "continuous" });
		setNodeStatusText(node, `连续测试 ${step + 1}/${totalRuns}：${preset.name} 执行完成，正在确认工作流输出...`);
		const workflowMeta = await waitForNodeContinuousWorkflowOutput(node, {
			createdAfter: queueRequestedAt,
			excludePromptIds: seenPromptIds,
			maxItems: Math.max(24, totalRuns * 6),
			timeoutMs: 180000,
			shouldCancel: () => token !== ensureNodeContinuousRuntime(node).token,
		});
		if (token !== ensureNodeContinuousRuntime(node).token) return false;
		if (workflowMeta?.promptId) {
			seenPromptIds.add(String(workflowMeta.promptId));
			targetedPromptIds.push(String(workflowMeta.promptId));
			pushNodeContinuousRunReport(node, library, "成图", `第 ${step + 1}/${totalRuns} 轮：${preset.name} 已锁定工作流输出 ${workflowMeta.imageCount ?? 0} 张。`, { presetName: preset.name, round: step + 1, total: totalRuns, origin: "continuous" });
			setNodeStatusText(node, `连续测试 ${step + 1}/${totalRuns}：${preset.name} 已锁定工作流输出 ${workflowMeta.imageCount ?? 0} 张。`);
		} else {
			pushNodeContinuousRunReport(node, library, "提示", `第 ${step + 1}/${totalRuns} 轮：${preset.name} 未在历史中定位到对应成图，最终质检将回退到最近输出策略。`, { presetName: preset.name, round: step + 1, total: totalRuns, origin: "continuous" });
			setNodeStatusText(node, `连续测试 ${step + 1}/${totalRuns}：${preset.name} 未定位到对应成图，将回退到最近输出策略。`);
		}
		await sleep(350);
	}
	if (token !== ensureNodeContinuousRuntime(node).token) return false;
		pushNodeContinuousRunReport(node, library, "结束", `连续测试完成：共执行 ${totalRuns} 轮${mode === "cycle" ? "（轮流）" : "（随机）"}。`, { total: totalRuns, origin: "continuous" });
	try {
		const audit = await runNodeQualityAudit(
			node,
			targetedPromptIds.length
				? { limit: totalRuns, historyPromptIds: targetedPromptIds, historyWaitTimeoutMs: 0 }
				: { limit: totalRuns, afterTimestamp: qualityAuditStartAt },
		);
		if (token !== ensureNodeContinuousRuntime(node).token) return false;
		if (audit.ok && audit.summaryText) {
			pushNodeContinuousRunReport(node, library, "质检", `自动质检完成：${audit.summaryText}`, { total: totalRuns, origin: "continuous" });
		}
	} catch (_error) {}
	if (token !== ensureNodeContinuousRuntime(node).token) return false;
	updateNodeContinuousRuntime(node, { running: false, step: 0 });
	setNodeStatusText(node, `连续测试完成：共执行 ${totalRuns} 轮${mode === "cycle" ? "（轮流）" : "（随机）"}。`);
	refreshNodeSummary(node, library);
	return true;
}
async function startNodeContinuousPresetRun(node, library, mode = "cycle") {
	const batchState = getNodePresetBatchState(node);
	const selectedIdSet = new Set(batchState.selectedIds);
	const selectedPresets = getUserPresets().filter((preset) => selectedIdSet.has(String(preset.id ?? "")));
	const totalRuns = Math.max(1, Math.min(99, Math.trunc(Number(batchState.continuousCount ?? 3) || 3)));
	return await runNodeContinuousPresetSequence(node, library, selectedPresets, totalRuns, mode);
}
async function startSinglePresetContinuousRun(node, library, preset, mode = "cycle") {
	if (!preset) {
		setNodeStatusText(node, "连续测试未启动：目标预设不存在。");
		return false;
	}
	const batchState = getNodePresetBatchState(node);
	const totalRuns = Math.max(1, Math.min(99, Math.trunc(Number(batchState.continuousCount ?? 3) || 3)));
	return await runNodeContinuousPresetSequence(node, library, [preset], totalRuns, mode);
}
function stopNodeContinuousPresetRun(node, library, message = "已停止连续测试。") {
	updateNodeContinuousRuntime(node, { token: ensureNodeContinuousRuntime(node).token + 1, running: false, step: 0 });
		pushNodeContinuousRunReport(node, library, "停止", message, { origin: "continuous" });
	setNodeStatusText(node, message);
}
function buildNodeContinuousRunReportText(node, reportOverride = null) {
	const report = Array.isArray(reportOverride) ? reportOverride : getNodeContinuousRunReport(node);
	if (!report.length) return "";
	return report.map((entry) => `[${formatPresetTime(entry.at)}] ${entry.level} ${entry.message}`).join("\n");
}
function buildNodeContinuousRunReportMarkdown(node, reportOverride = null) {
	const report = Array.isArray(reportOverride) ? reportOverride : getNodeContinuousRunReport(node);
	if (!report.length) return "";
	const lines = [
		"# 连续测试报告",
		"",
		`- 事件数：${report.length}`,
		`- 导出时间：${formatPresetTime(Date.now())}`,
		"",
		"| 时间 | 级别 | 说明 |",
		"| --- | --- | --- |",
	];
	for (const entry of report) {
		const time = formatPresetTime(entry.at).replace(/\|/g, "\\|");
		const level = String(entry.level ?? "").replace(/\|/g, "\\|");
		const message = String(entry.message ?? "").replace(/\|/g, "\\|").replace(/\n/g, "<br>");
		lines.push(`| ${time} | ${level} | ${message} |`);
	}
	return lines.join("\n");
}
function buildNodeContinuousRunReportCsv(node, reportOverride = null) {
	const report = Array.isArray(reportOverride) ? reportOverride : getNodeContinuousRunReport(node);
	if (!report.length) return "";
	const escapeCsv = (value) => `"${String(value ?? "").replace(/"/g, '""')}"`;
	const rows = [["时间", "级别", "说明"]];
	for (const entry of report) rows.push([formatPresetTime(entry.at), entry.level, entry.message]);
	return rows.map((row) => row.map(escapeCsv).join(",")).join("\n");
}
function buildContinuousRunAggregate(reportEntries) {
	const report = Array.isArray(reportEntries) ? reportEntries : [];
	const groups = new Map();
		for (const entry of report) {
			const presetName = String(entry.presetName ?? "").trim() || "未标注预设";
			if (!groups.has(presetName)) {
				groups.set(presetName, {
					presetName,
					submitted: 0,
					queued: 0,
					completed: 0,
					failed: 0,
					timeout: 0,
					manual: 0,
					terminal: 0,
					successRate: null,
					outcomeTrail: "·",
					recentRounds: [],
					recentRoundSummaries: [],
					lastAt: Number(entry.at ?? 0),
					lastMessage: String(entry.message ?? ""),
					entries: [],
				});
			}
			const item = groups.get(presetName);
			if (!item) continue;
		if (entry.level === "提交") item.submitted += 1;
		if (entry.level === "入队") item.queued += 1;
			if (entry.level === "完成") item.completed += 1;
			if (entry.level === "失败") item.failed += 1;
			if (entry.level === "超时") item.timeout += 1;
			if (String(entry.origin ?? "") === "manual") item.manual += 1;
			if (Number(entry.at ?? 0) >= item.lastAt) {
				item.lastAt = Number(entry.at ?? 0);
				item.lastMessage = String(entry.message ?? "");
			}
				item.entries.push({
					at: Number(entry.at ?? 0),
					level: String(entry.level ?? ""),
					message: String(entry.message ?? ""),
					origin: String(entry.origin ?? ""),
					round: Number(entry.round ?? 0),
					total: Number(entry.total ?? 0),
				});
		}
		for (const item of groups.values()) {
			item.entries.sort((left, right) => Number(right.at ?? 0) - Number(left.at ?? 0));
			item.terminal = item.completed + item.failed + item.timeout;
			item.successRate = item.terminal > 0 ? item.completed / item.terminal : null;
			item.outcomeTrail = buildContinuousRunOutcomeTrail(item);
			item.recentRounds = buildContinuousRunRecentRoundRows(item);
			item.recentRoundSummaries = buildContinuousRunRecentRoundSummaries(item);
		}
		return [...groups.values()].sort((left, right) => right.lastAt - left.lastAt || right.completed - left.completed || left.presetName.localeCompare(right.presetName, "zh-CN"));
	}

function formatContinuousRunSuccessRate(item) {
	const terminal = Number(item?.terminal ?? 0);
	const successRate = Number(item?.successRate ?? 0);
	if (terminal <= 0 || !Number.isFinite(successRate)) return "待定";
	return `${Math.round(successRate * 100)}%`;
}

function getContinuousRunOutcomeSymbol(level) {
	if (level === "完成") return "✓";
	if (level === "失败") return "✕";
	if (level === "超时") return "⏱";
	return "·";
}

function getContinuousRunLevelTone(level) {
	if (level === "完成") return "success";
	if (level === "超时") return "warn";
	if (level === "失败") return "danger";
	return "info";
}

function buildContinuousRunOutcomeTrail(item, limit = 8) {
	const entries = Array.isArray(item?.entries) ? item.entries : [];
	const terminals = entries.filter((entry) => ["完成", "失败", "超时"].includes(String(entry?.level ?? "")));
	if (!terminals.length) return "·";
	const trail = terminals.slice(0, limit).map((entry) => getContinuousRunOutcomeSymbol(String(entry?.level ?? ""))).join(" ");
	return terminals.length > limit ? `${trail} …` : trail;
}

function buildContinuousRunRecentRoundRows(item, limit = 5) {
	const entries = Array.isArray(item?.entries) ? item.entries : [];
	return entries
		.filter((entry) => ["完成", "失败", "超时"].includes(String(entry?.level ?? "")))
		.slice(0, limit)
		.map((entry) => ({
			at: Number(entry?.at ?? 0),
			level: String(entry?.level ?? ""),
			message: String(entry?.message ?? ""),
			origin: String(entry?.origin ?? ""),
			roundLabel: entry?.round && entry?.total ? `第 ${entry.round}/${entry.total} 轮` : (String(entry?.origin ?? "") === "manual" ? "手动" : "未标轮次"),
			symbol: getContinuousRunOutcomeSymbol(String(entry?.level ?? "")),
			tone: getContinuousRunLevelTone(String(entry?.level ?? "")),
		}));
}

function buildContinuousRunRecentRoundSummaries(item, limit = 5) {
	const entries = Array.isArray(item?.entries) ? item.entries : [];
	if (!entries.length) return [];
	const groups = new Map();
	for (const entry of entries) {
		if (!(entry?.round && entry?.total)) continue;
		const roundLabel = `第 ${entry.round}/${entry.total} 轮`;
		const key = `${entry.round}/${entry.total}`;
		if (!groups.has(key)) {
			groups.set(key, {
				key,
				roundLabel,
				latestAt: Number(entry.at ?? 0),
				origin: String(entry.origin ?? ""),
				entries: [],
			});
		}
		const itemGroup = groups.get(key);
		if (!itemGroup) continue;
		itemGroup.latestAt = Math.max(itemGroup.latestAt, Number(entry.at ?? 0));
		itemGroup.entries.push({
			at: Number(entry.at ?? 0),
			level: String(entry.level ?? ""),
			message: String(entry.message ?? ""),
			origin: String(entry.origin ?? ""),
		});
	}
	const summaries = [...groups.values()]
		.map((group) => {
			group.entries.sort((left, right) => Number(left.at ?? 0) - Number(right.at ?? 0));
			const chain = group.entries.map((entry) => String(entry.level ?? "")).join(" -> ");
			const latestEntry = [...group.entries].sort((left, right) => Number(right.at ?? 0) - Number(left.at ?? 0))[0];
			const terminalEntry = [...group.entries].reverse().find((entry) => ["完成", "失败", "超时"].includes(String(entry.level ?? ""))) ?? latestEntry;
			return {
				key: group.key,
				roundLabel: group.roundLabel,
				latestAt: group.latestAt,
				chain,
				terminalLevel: String(terminalEntry?.level ?? ""),
				terminalSymbol: getContinuousRunOutcomeSymbol(String(terminalEntry?.level ?? "")),
				terminalMessage: String(terminalEntry?.message ?? ""),
				tone: getContinuousRunLevelTone(String(terminalEntry?.level ?? "")),
			};
		})
		.sort((left, right) => Number(right.latestAt ?? 0) - Number(left.latestAt ?? 0));
	return summaries.slice(0, limit);
}

function getContinuousRunRecentTerminalLevels(item, limit = 4) {
	const entries = Array.isArray(item?.entries) ? item.entries : [];
	return entries
		.filter((entry) => ["完成", "失败", "超时"].includes(String(entry?.level ?? "")))
		.slice(0, limit)
		.map((entry) => String(entry?.level ?? ""));
}

function countLeadingContinuousRunLevels(levels, targetLevel) {
	let count = 0;
	for (const level of levels) {
		if (level !== targetLevel) break;
		count += 1;
	}
	return count;
}

function classifyContinuousRunOutcomeRisk(item) {
	const levels = getContinuousRunRecentTerminalLevels(item, 4);
	if (!levels.length) return { tone: "info", label: "暂无终态", streak: 0 };
	let anomalyStreak = 0;
	for (const level of levels) {
		if (level === "完成") break;
		anomalyStreak += 1;
	}
	if (anomalyStreak <= 0) return { tone: "success", label: "最近正常", streak: 0 };
	const timeoutStreak = countLeadingContinuousRunLevels(levels, "超时");
	const failureStreak = countLeadingContinuousRunLevels(levels, "失败");
	if (timeoutStreak >= 2) return { tone: "danger", label: `连超时 ${timeoutStreak}`, streak: anomalyStreak };
	if (failureStreak >= 2) return { tone: "danger", label: `连失败 ${failureStreak}`, streak: anomalyStreak };
	if (anomalyStreak >= 3) return { tone: "danger", label: `连续异常 ${anomalyStreak}`, streak: anomalyStreak };
	if (anomalyStreak >= 2) return { tone: "warn", label: `连续异常 ${anomalyStreak}`, streak: anomalyStreak };
	return { tone: levels[0] === "超时" ? "warn" : "danger", label: levels[0] === "超时" ? "最近超时" : "最近失败", streak: 1 };
}

function getContinuousRunToneRank(tone) {
	return { info: 0, success: 1, warn: 2, danger: 3 }[String(tone ?? "info")] ?? 0;
}

function mergeContinuousRunTones(...tones) {
	return tones.reduce((best, tone) => getContinuousRunToneRank(tone) > getContinuousRunToneRank(best) ? tone : best, "info");
}

function classifyContinuousRunAggregateTrend(item) {
	const terminal = Number(item?.terminal ?? 0);
	const successRate = Number(item?.successRate ?? 0);
	const timeout = Number(item?.timeout ?? 0);
	if (terminal <= 0 || !Number.isFinite(successRate)) {
		return { tone: "info", arrow: "→", label: "待观察" };
	}
	if (successRate >= 0.85 && timeout === 0) {
		return { tone: "success", arrow: "↑", label: terminal >= 3 ? "稳定上扬" : "初步稳定" };
	}
	if (successRate >= 0.5) {
		return { tone: timeout > 0 ? "warn" : "info", arrow: "↔", label: timeout > 0 ? "有超时波动" : "波动观察" };
	}
	return { tone: "danger", arrow: "↓", label: timeout > 0 ? "超时回查" : "失败回查" };
}

function normalizeContinuousRunAggregateItems(reportEntries) {
	const entries = Array.isArray(reportEntries) ? reportEntries : [];
	if (!entries.length) return [];
	const first = entries[0];
	if (first && typeof first === "object" && "presetName" in first && "submitted" in first && "completed" in first) {
		return entries.map((item) => {
			const terminal = Number(item?.terminal ?? (Number(item?.completed ?? 0) + Number(item?.failed ?? 0) + Number(item?.timeout ?? 0)));
			const successRate = terminal > 0 ? Number(item?.completed ?? 0) / terminal : null;
			return {
				...item,
				terminal,
				successRate: Number.isFinite(Number(item?.successRate)) ? Number(item?.successRate) : successRate,
				outcomeTrail: String(item?.outcomeTrail ?? "").trim() || buildContinuousRunOutcomeTrail(item),
				recentRounds: Array.isArray(item?.recentRounds) && item.recentRounds.length ? item.recentRounds : buildContinuousRunRecentRoundRows(item),
				recentRoundSummaries: Array.isArray(item?.recentRoundSummaries) && item.recentRoundSummaries.length ? item.recentRoundSummaries : buildContinuousRunRecentRoundSummaries(item),
			};
		});
	}
	return buildContinuousRunAggregate(entries);
}

function classifyContinuousRunAggregate(item) {
	const failed = Number(item?.failed ?? 0);
	const timeout = Number(item?.timeout ?? 0);
	const completed = Number(item?.completed ?? 0);
	const queued = Number(item?.queued ?? 0);
	const terminal = Number(item?.terminal ?? 0);
	const successRate = Number(item?.successRate ?? 0);
	const successRateText = formatContinuousRunSuccessRate(item);
	if (terminal > 0) {
		if ((failed > 0 || timeout > 0) && completed === 0) {
			return { tone: "danger", label: `${successRateText} | ${timeout > 0 ? "超时风险" : "失败偏多"}` };
		}
		if (timeout > 0 || successRate < 0.5) {
			return { tone: "danger", label: `${successRateText} | 结果波动` };
		}
		if (failed > 0 || successRate < 0.85) {
			return { tone: "warn", label: `${successRateText} | 有失败/超时` };
		}
		return { tone: "success", label: `${successRateText} | 完成稳定` };
	}
	if (queued > 0) {
		return { tone: "info", label: "已入队待完成" };
	}
	return { tone: "info", label: "仅提交记录" };
}
function buildContinuousRunAggregateText(reportEntries) {
	const aggregate = normalizeContinuousRunAggregateItems(reportEntries);
	if (!aggregate.length) return "";
	return aggregate.map((item) => {
		const trend = classifyContinuousRunAggregateTrend(item);
		const state = classifyContinuousRunAggregate(item);
		const risk = classifyContinuousRunOutcomeRisk(item);
		return `${item.presetName} | 成功率${formatContinuousRunSuccessRate(item)} 终态${item.terminal} | 趋势${trend.arrow}${trend.label} | 风险${risk.label} | 最近结果${item.outcomeTrail} | 判定${state.label} | 提交${item.submitted} 入队${item.queued} 完成${item.completed} 失败${item.failed} 超时${item.timeout} | 最近：${item.lastMessage}`;
	}).join("\n");
}
function buildContinuousRunAggregateMarkdown(reportEntries) {
	const aggregate = normalizeContinuousRunAggregateItems(reportEntries);
	if (!aggregate.length) return "";
	const lines = [
		"# 连续测试聚合统计",
		"",
		`- 预设数：${aggregate.length}`,
		`- 导出时间：${formatPresetTime(Date.now())}`,
		"- 阈值说明：成功率 >= 85% 视为稳定，50%-84% 视为观察，低于 50% 建议回查。",
		"- 结果串说明：✓ 完成，✕ 失败，⏱ 超时，顺序为新 -> 旧。",
		"- 风险说明：最近连续 ✕ / ⏱ 会被标为最近失败、连失败、最近超时、连超时或连续异常。",
		"",
		"| 预设 | 成功率 | 趋势 | 风险 | 最近结果 | 判定 | 终态 | 提交 | 入队 | 完成 | 失败 | 超时 | 最近事件 |",
		"| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
	];
	for (const item of aggregate) {
		const trend = classifyContinuousRunAggregateTrend(item);
		const state = classifyContinuousRunAggregate(item);
		const risk = classifyContinuousRunOutcomeRisk(item);
		const presetName = item.presetName.replace(/\|/g, "\\|");
		const message = String(item.lastMessage ?? "").replace(/\|/g, "\\|").replace(/\n/g, "<br>");
		lines.push(`| ${presetName} | ${formatContinuousRunSuccessRate(item)} | ${trend.arrow} ${trend.label} | ${risk.label.replace(/\|/g, "\\|")} | ${String(item.outcomeTrail ?? "").replace(/\|/g, "\\|")} | ${state.label.replace(/\|/g, "\\|")} | ${item.terminal} | ${item.submitted} | ${item.queued} | ${item.completed} | ${item.failed} | ${item.timeout} | ${message} |`);
	}
	return lines.join("\n");
}
function buildContinuousRunAggregateCsv(reportEntries) {
	const aggregate = normalizeContinuousRunAggregateItems(reportEntries);
	if (!aggregate.length) return "";
	const escapeCsv = (value) => `"${String(value ?? "").replace(/"/g, '""')}"`;
	const rows = [["预设", "成功率", "趋势", "风险", "最近结果", "判定", "终态", "提交", "入队", "完成", "失败", "超时", "最近事件"]];
	for (const item of aggregate) {
		const trend = classifyContinuousRunAggregateTrend(item);
		const state = classifyContinuousRunAggregate(item);
		const risk = classifyContinuousRunOutcomeRisk(item);
		rows.push([item.presetName, formatContinuousRunSuccessRate(item), `${trend.arrow} ${trend.label}`, risk.label, item.outcomeTrail, state.label, item.terminal, item.submitted, item.queued, item.completed, item.failed, item.timeout, item.lastMessage]);
	}
	return rows.map((row) => row.map(escapeCsv).join(",")).join("\n");
}

function buildSinglePresetContinuousRunReportPayload(item) {
	const normalized = normalizeContinuousRunAggregateItems([item])[0];
	if (!normalized) return null;
	return {
		version: 1,
		exportedAt: Date.now(),
		source: "qwen-te-single-preset-report",
		presetName: normalized.presetName,
		aggregate: {
			presetName: normalized.presetName,
			successRate: formatContinuousRunSuccessRate(normalized),
			terminal: normalized.terminal,
			submitted: normalized.submitted,
			queued: normalized.queued,
			completed: normalized.completed,
			failed: normalized.failed,
			timeout: normalized.timeout,
			manual: normalized.manual,
			outcomeTrail: normalized.outcomeTrail,
			trend: classifyContinuousRunAggregateTrend(normalized),
			risk: classifyContinuousRunOutcomeRisk(normalized),
			state: classifyContinuousRunAggregate(normalized),
			lastAt: normalized.lastAt,
			lastMessage: normalized.lastMessage,
		},
		recentRoundSummaries: normalized.recentRoundSummaries ?? [],
		recentRounds: normalized.recentRounds ?? [],
		entries: normalized.entries ?? [],
	};
}

function buildSinglePresetContinuousRunReportText(item) {
	const payload = buildSinglePresetContinuousRunReportPayload(item);
	if (!payload) return "";
	const aggregate = payload.aggregate;
	const lines = [
		`${aggregate.presetName}`,
		`成功率 ${aggregate.successRate} | 趋势 ${aggregate.trend.arrow} ${aggregate.trend.label} | 风险 ${aggregate.risk.label} | 判定 ${aggregate.state.label}`,
		`终态 ${aggregate.terminal} | 提交 ${aggregate.submitted} | 入队 ${aggregate.queued} | 完成 ${aggregate.completed} | 失败 ${aggregate.failed} | 超时 ${aggregate.timeout} | 手动 ${aggregate.manual}`,
		`最近结果（新→旧） ${aggregate.outcomeTrail}`,
		`最近事件：${aggregate.lastMessage}`,
	];
	if (payload.recentRoundSummaries.length) {
		lines.push("", "最近轮次链路");
		for (const round of payload.recentRoundSummaries) {
			lines.push(`${round.terminalSymbol} ${round.roundLabel} | ${round.terminalLevel} | ${formatPresetTime(round.latestAt)}`);
			lines.push(`${round.chain}`);
			lines.push(`${round.terminalMessage}`);
		}
	}
	return lines.join("\n");
}

function buildSinglePresetSnapshotName(item) {
	const payload = buildSinglePresetContinuousRunReportPayload(item);
	if (!payload) return `单预设快照-${buildCompactTimestamp()}`;
	return `单预设快照-${payload.presetName}-${buildCompactTimestamp()}`;
}

function buildSinglePresetHistorySummary(item) {
	const payload = buildSinglePresetContinuousRunReportPayload(item);
	if (!payload) return "单预设快照";
	const aggregate = payload.aggregate;
	return `单预设快照 | ${aggregate.presetName} | 成功率 ${aggregate.successRate} | 风险 ${aggregate.risk.label}`;
}

function buildSinglePresetReportHistorySummary(item) {
	const payload = buildSinglePresetContinuousRunReportPayload(item);
	if (!payload) return "单预设报告";
	const aggregate = payload.aggregate;
	return `单预设报告 | ${aggregate.presetName} | 成功率 ${aggregate.successRate} | 趋势 ${aggregate.trend.arrow} ${aggregate.trend.label} | 风险 ${aggregate.risk.label}`;
}

function buildHistoryPresetAggregateExportPayload(item) {
	if (item?.source === "qwen-te-history-preset-aggregate" || Array.isArray(item?.reportPayloads)) {
		return {
			version: 1,
			exportedAt: Number(item?.exportedAt ?? Date.now()),
			source: "qwen-te-history-preset-aggregate",
			presetName: String(item?.presetName ?? ""),
			count: Number(item?.count ?? 0),
			averageSuccessRate: String(item?.averageSuccessRate ?? "待定"),
			dangerCount: Number(item?.dangerCount ?? 0),
			warnCount: Number(item?.warnCount ?? 0),
			latestAt: Number(item?.latestAt ?? 0),
			latestAggregate: cloneJsonSafe(item?.latestAggregate, null),
			reportPayloads: cloneJsonSafe(item?.reportPayloads, []),
		};
	}
	const reportPayloads = (item?.historyItems ?? []).map((historyItem) => historyItem?.meta?.reportPayload).filter(Boolean);
	return {
		version: 1,
		exportedAt: Date.now(),
		source: "qwen-te-history-preset-aggregate",
		presetName: item?.presetName ?? "",
		count: Number(item?.count ?? 0),
		averageSuccessRate: formatHistoryAggregateRate(item?.averageSuccessRate),
		dangerCount: Number(item?.dangerCount ?? 0),
		warnCount: Number(item?.warnCount ?? 0),
		latestAt: Number(item?.latestAt ?? 0),
		latestAggregate: item?.latestAggregate ?? null,
		reportPayloads,
	};
}

function buildHistoryPresetAggregateText(item) {
	const payload = buildHistoryPresetAggregateExportPayload(item);
	if (!payload.presetName) return "";
	const lines = [
		`${payload.presetName}`,
		`报告 ${payload.count} | 平均成功率 ${payload.averageSuccessRate} | 高风险 ${payload.dangerCount} | 观察 ${payload.warnCount}`,
		`最近时间 ${formatPresetTime(payload.latestAt)}`,
	];
	if (payload.latestAggregate) {
		lines.push(`最近趋势 ${payload.latestAggregate?.trend?.arrow ?? "→"} ${payload.latestAggregate?.trend?.label ?? "待观察"} | 风险 ${payload.latestAggregate?.risk?.label ?? "未知"} | 结果 ${payload.latestAggregate?.outcomeTrail ?? "·"}`);
		lines.push(`最近事件：${payload.latestAggregate?.lastMessage ?? ""}`);
	}
	if (payload.reportPayloads.length) {
		lines.push("", "历史报告");
		for (const report of payload.reportPayloads) {
			const aggregate = report?.aggregate ?? {};
			lines.push(`${formatPresetTime(aggregate?.lastAt ?? payload.latestAt)} | ${aggregate?.successRate ?? "待定"} | ${aggregate?.risk?.label ?? "未知"} | ${aggregate?.outcomeTrail ?? "·"}`);
			lines.push(`${aggregate?.lastMessage ?? ""}`);
		}
	}
	return lines.join("\n");
}

function buildHistoryAggregateSnapshotName(item) {
	const payload = buildHistoryPresetAggregateExportPayload(item);
	const presetName = String(payload?.presetName ?? "未标注预设").trim() || "未标注预设";
	return `历史聚合快照-${presetName}-${buildCompactTimestamp(payload?.latestAt ?? Date.now())}`;
}

function buildHistoryAggregateSnapshotMeta(item) {
	const payload = buildHistoryPresetAggregateExportPayload(item);
	return {
		presetName: String(payload?.presetName ?? ""),
		reportCount: Number(payload?.count ?? 0),
		averageSuccessRate: String(payload?.averageSuccessRate ?? "待定"),
		dangerCount: Number(payload?.dangerCount ?? 0),
		warnCount: Number(payload?.warnCount ?? 0),
		latestAt: Number(payload?.latestAt ?? 0),
		latestOutcomeTrail: String(payload?.latestAggregate?.outcomeTrail ?? ""),
		latestTrendArrow: String(payload?.latestAggregate?.trend?.arrow ?? ""),
		latestTrendLabel: String(payload?.latestAggregate?.trend?.label ?? ""),
		latestRisk: String(payload?.latestAggregate?.risk?.label ?? ""),
		latestRiskTone: String(payload?.latestAggregate?.risk?.tone ?? ""),
		latestMessage: String(payload?.latestAggregate?.lastMessage ?? ""),
		aggregatePayload: payload,
	};
}

function buildHistoryAggregatePresetExportPayload(preset) {
	const meta = preset?.meta ?? {};
	const savedPayload = meta.aggregatePayload && typeof meta.aggregatePayload === "object"
		? cloneJsonSafe(meta.aggregatePayload, null)
		: null;
	if (savedPayload?.presetName) return savedPayload;
	const targetName = String(meta.presetName ?? preset?.name ?? "").trim() || String(preset?.name ?? "");
	const latestRiskTone = String(meta.latestRiskTone ?? inferHistoryAggregatePresetTone(preset));
	return {
		version: 1,
		exportedAt: Date.now(),
		source: "qwen-te-history-aggregate-preset",
		presetName: targetName,
		count: Number(meta.reportCount ?? 0),
		averageSuccessRate: String(meta.averageSuccessRate ?? "待定"),
		dangerCount: Number(meta.dangerCount ?? 0),
		warnCount: Number(meta.warnCount ?? 0),
		latestAt: Number(meta.latestAt ?? preset?.updatedAt ?? 0),
		latestAggregate: {
			presetName: targetName,
			successRate: String(meta.averageSuccessRate ?? "待定"),
			trend: {
				arrow: String(meta.latestTrendArrow ?? ""),
				label: String(meta.latestTrendLabel ?? ""),
				tone: latestRiskTone === "danger" ? "danger" : latestRiskTone === "warn" ? "warn" : "info",
			},
			risk: {
				label: String(meta.latestRisk ?? "未知"),
				tone: latestRiskTone,
			},
			outcomeTrail: String(meta.latestOutcomeTrail ?? "·"),
			lastMessage: String(meta.latestMessage ?? ""),
		},
		reportPayloads: [],
	};
}

function buildHistoryPresetAggregateMarkdown(item) {
	const payload = buildHistoryPresetAggregateExportPayload(item);
	if (!payload.presetName) return "";
	const lines = [
		"# 历史聚合预设报告",
		"",
		`- 预设：${payload.presetName}`,
		`- 报告数：${payload.count}`,
		`- 平均成功率：${payload.averageSuccessRate}`,
		`- 高风险：${payload.dangerCount}`,
		`- 观察：${payload.warnCount}`,
		`- 最近时间：${formatPresetTime(payload.latestAt)}`,
		"",
		"| 时间 | 成功率 | 趋势 | 风险 | 最近结果 | 最近事件 |",
		"| --- | --- | --- | --- | --- | --- |",
	];
	for (const report of payload.reportPayloads) {
		const aggregate = report?.aggregate ?? {};
		const time = formatPresetTime(aggregate?.lastAt ?? payload.latestAt).replace(/\|/g, "\\|");
		const successRate = String(aggregate?.successRate ?? "待定").replace(/\|/g, "\\|");
		const trend = `${aggregate?.trend?.arrow ?? "→"} ${aggregate?.trend?.label ?? "待观察"}`.replace(/\|/g, "\\|");
		const risk = String(aggregate?.risk?.label ?? "未知").replace(/\|/g, "\\|");
		const trail = String(aggregate?.outcomeTrail ?? "·").replace(/\|/g, "\\|");
		const message = String(aggregate?.lastMessage ?? "").replace(/\|/g, "\\|").replace(/\n/g, "<br>");
		lines.push(`| ${time} | ${successRate} | ${trend} | ${risk} | ${trail} | ${message} |`);
	}
	return lines.join("\n");
}

function buildHistoryPresetAggregateCsv(item) {
	const payload = buildHistoryPresetAggregateExportPayload(item);
	if (!payload.presetName) return "";
	const escapeCsv = (value) => `"${String(value ?? "").replace(/"/g, '""')}"`;
	const rows = [["时间", "成功率", "趋势", "风险", "最近结果", "最近事件"]];
	for (const report of payload.reportPayloads) {
		const aggregate = report?.aggregate ?? {};
		rows.push([
			formatPresetTime(aggregate?.lastAt ?? payload.latestAt),
			aggregate?.successRate ?? "待定",
			`${aggregate?.trend?.arrow ?? "→"} ${aggregate?.trend?.label ?? "待观察"}`,
			aggregate?.risk?.label ?? "未知",
			aggregate?.outcomeTrail ?? "·",
			aggregate?.lastMessage ?? "",
		]);
	}
	return rows.map((row) => row.map(escapeCsv).join(",")).join("\n");
}

function buildHistoryReportActionStatus(action, reportLabel, ok, presetName = "") {
	const label = String(reportLabel ?? "历史报告").trim() || "历史报告";
	const name = String(presetName ?? "").trim();
	const suffix = name ? `：${name}` : "。";
	const successMap = {
		copy_summary: `已复制${label}摘要${suffix}`,
		copy_json: `已复制${label} JSON${suffix}`,
		copy_markdown: `已复制${label} Markdown${suffix}`,
		export_json: `已导出${label} JSON${suffix}`,
		export_csv: `已导出${label} CSV${suffix}`,
		export_markdown: `已导出${label} Markdown${suffix}`,
	};
	const failureMap = {
		copy_summary: `复制${label}摘要失败${suffix}`,
		copy_json: `复制${label} JSON失败${suffix}`,
		copy_markdown: `复制${label} Markdown失败${suffix}`,
		export_json: `导出${label} JSON失败${suffix}`,
		export_csv: `导出${label} CSV失败${suffix}`,
		export_markdown: `导出${label} Markdown失败${suffix}`,
	};
	return ok
		? (successMap[String(action ?? "")] ?? `已完成${label}操作${suffix}`)
		: (failureMap[String(action ?? "")] ?? `${label}操作失败${suffix}`);
}
function buildNodeContinuousRunHistorySummary(node, reportOverride = null) {
	const report = Array.isArray(reportOverride) ? reportOverride : getNodeContinuousRunReport(node);
	if (!report.length) return "";
	const latest = report[0];
	return `连续测试报告 | ${report.length} 条 | 最新：${latest.level} ${latest.message}`;
}
function exportNodeContinuousRunReport(node, format = "json", reportOverride = null) {
	const report = Array.isArray(reportOverride) ? reportOverride : getNodeContinuousRunReport(node);
	if (!report.length) return false;
	const stamp = buildCompactTimestamp();
	if (format === "csv") return exportTextFile(buildNodeContinuousRunReportCsv(node, report), `qwen-te-continuous-report-${stamp}.csv`, "text/csv;charset=utf-8");
	if (format === "markdown") return exportTextFile(buildNodeContinuousRunReportMarkdown(node, report), `qwen-te-continuous-report-${stamp}.md`, "text/markdown;charset=utf-8");
	const payload = {
		version: 1,
		exportedAt: Date.now(),
		source: "qwen-te-continuous-run-report",
		report,
	};
	const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
	const url = URL.createObjectURL(blob);
	const a = document.createElement("a");
	a.href = url;
	a.download = `qwen-te-continuous-report-${stamp}.json`;
	document.body.appendChild(a);
	a.click();
	document.body.removeChild(a);
	URL.revokeObjectURL(url);
	return true;
}

function ensureSingleModal(modalKey) {
	const key = String(modalKey ?? "").trim();
	if (!key) return;
	const selector = `.qwen-te-modal[data-qwen-modal="${key}"]`;
	for (const existing of document.querySelectorAll?.(selector) ?? []) {
		if (existing instanceof HTMLElement) disposeModalOverlay(existing);
	}
}

function disposeModalOverlay(overlay) {
	if (!(overlay instanceof HTMLElement)) return false;
	if (!overlay.__qwenDisposed) {
		overlay.__qwenDisposed = true;
		abortOwnedRequests(overlay);
		try {
			overlay.__qwenDispose?.();
		} catch (error) {
			console.warn("[QwenTE UI] modal cleanup failed", error);
		}
	}
	overlay.remove();
	return true;
}

function getNodeDisplayName(node) {
	const title = String(node?.title ?? "").trim();
	if (title) return title;
	const type = String(node?.comfyClass ?? node?.type ?? "").trim();
	return type || TARGET_NODE_CLASS;
}

function buildNodeModalContext(node, library = null) {
	const panelLibrary = library ?? node?.[PANEL_KEY]?.library ?? null;
	const outputSource = getStageDisplayPayload(node, node?.[PANEL_KEY]?.displayMode ?? STAGE_DISPLAY_MODES[0]?.key ?? "prompt")?.source ?? "等待输出";
	const hasPrompt = !!getStagePromptOutputText(node);
	const state = panelLibrary ? collectNodeState(node, panelLibrary) : null;
	const tagCount = state ? Object.values(state.selected ?? {}).reduce((count, tags) => count + (tags?.length ?? 0), 0) + (state.customTags?.length ?? 0) : 0;
	return {
		nodeName: getNodeDisplayName(node),
		outputSource,
		hasPrompt,
		tagCount,
		executedAt: getNodeExecutionStamp(node),
	};
}

const NSFW_WORKSPACE_PROVENANCE_FIELDS = [
	"applied_custom_tags",
	"applied_selected_tags",
	"manual_custom_tags",
	"generation_profile_restore",
];
const NSFW_WORKSPACE_LIST_FIELDS = new Set(["trigger_words", "workspace_custom_tags"]);
const NSFW_WORKSPACE_SCALAR_PRIORITY = [
	"enabled",
	"preset",
	"quality_tier",
	"random_mode",
	"random_nonce",
	"negative_preset",
	"negative_apply_mode",
	"custom_negative",
	...Object.keys(NSFW_WORKSPACE_DEFAULTS).filter((field) => ![
		"enabled",
		"preset",
		"quality_tier",
		"random_mode",
		"random_nonce",
		"negative_preset",
		"negative_apply_mode",
		"custom_negative",
		"custom_prefix",
		"custom_suffix",
		...NSFW_WORKSPACE_LIST_FIELDS,
	].includes(field)),
	"custom_prefix",
	"custom_suffix",
];
const NSFW_WORKSPACE_TERM_SPLIT_PATTERN = /[,\n\r\t;；，、]+/u;

function cleanNsfwWorkspaceScalar(value, maxChars) {
	if (value != null && typeof value === "object") return "";
	const limit = Math.max(0, Math.trunc(Number(maxChars) || 0));
	if (!limit) return "";
	let text = String(value ?? "").slice(0, limit * 4);
	try { text = text.normalize("NFKC"); } catch (_error) {}
	return text
		.replace(/[\u0000-\u001f\u007f]+/gu, " ")
		.replace(/\s+/gu, " ")
		.trim()
		.slice(0, limit)
		.trimEnd();
}

function normalizeBoundedNsfwWorkspaceList(value, maxItems = NSFW_WORKSPACE_MAX_LIST_ITEMS) {
	if (value && typeof value === "object" && !Array.isArray(value)) return [];
	const rawValues = Array.isArray(value) ? value : [value];
	const itemLimit = Math.max(0, Math.min(NSFW_WORKSPACE_MAX_LIST_ITEMS, Math.trunc(Number(maxItems) || 0)));
	const result = [];
	const seen = new Set();
	const scanCount = Math.min(rawValues.length, NSFW_WORKSPACE_MAX_SCANNED_LIST_VALUES);
	for (let valueIndex = 0; valueIndex < scanCount && result.length < itemLimit; valueIndex += 1) {
		const rawValue = rawValues[valueIndex];
		if (rawValue != null && typeof rawValue === "object") continue;
		let text = String(rawValue ?? "").slice(0, NSFW_WORKSPACE_MAX_LIST_SCAN_CHARS);
		try { text = text.normalize("NFKC"); } catch (_error) {}
		const terms = text.split(NSFW_WORKSPACE_TERM_SPLIT_PATTERN, NSFW_WORKSPACE_MAX_SCANNED_LIST_VALUES);
		for (const rawTerm of terms) {
			const term = cleanNsfwWorkspaceScalar(rawTerm, NSFW_WORKSPACE_MAX_TERM_CHARS);
			if (!term || term === "——" || seen.has(term)) continue;
			seen.add(term);
			result.push(term);
			if (result.length >= itemLimit) break;
		}
	}
	return result;
}

function fitNsfwWorkspaceText(payload, field, value) {
	const previous = payload[field];
	if (utf8ByteLength({ ...payload, [field]: value }) <= NSFW_WORKSPACE_MAX_JSON_BYTES) {
		payload[field] = value;
		return;
	}
	let low = 0;
	let high = value.length;
	while (low < high) {
		const middle = Math.floor((low + high + 1) / 2);
		if (utf8ByteLength({ ...payload, [field]: value.slice(0, middle) }) <= NSFW_WORKSPACE_MAX_JSON_BYTES) low = middle;
		else high = middle - 1;
	}
	payload[field] = low > 0 ? value.slice(0, low).trimEnd() : previous;
}

function fitNsfwWorkspaceList(payload, field, values, preserveEmpty = false) {
	const hadField = Object.prototype.hasOwnProperty.call(payload, field);
	const fitted = [];
	for (const value of values) {
		const candidate = [...fitted, value];
		if (utf8ByteLength({ ...payload, [field]: candidate }) > NSFW_WORKSPACE_MAX_JSON_BYTES) break;
		fitted.push(value);
	}
	if (fitted.length || hadField || (preserveEmpty && utf8ByteLength({ ...payload, [field]: [] }) <= NSFW_WORKSPACE_MAX_JSON_BYTES)) payload[field] = fitted;
}

function normalizeBoundedNsfwAppliedSelection(value) {
	if (!value || typeof value !== "object" || Array.isArray(value)) return {};
	const selected = {};
	let scannedGroups = 0;
	let acceptedGroups = 0;
	let acceptedTerms = 0;
	for (const rawGroupName in value) {
		if (!Object.prototype.hasOwnProperty.call(value, rawGroupName)) continue;
		scannedGroups += 1;
		if (scannedGroups > NSFW_WORKSPACE_MAX_PROVENANCE_GROUPS * 4 || acceptedGroups >= NSFW_WORKSPACE_MAX_PROVENANCE_GROUPS || acceptedTerms >= NSFW_WORKSPACE_MAX_PROVENANCE_TERMS) break;
		const groupName = cleanNsfwWorkspaceScalar(rawGroupName, NSFW_WORKSPACE_MAX_PROVENANCE_GROUP_CHARS);
		if (!groupName || Object.prototype.hasOwnProperty.call(selected, groupName)) continue;
		const tags = normalizeBoundedNsfwWorkspaceList(
			value[rawGroupName],
			Math.min(NSFW_WORKSPACE_MAX_LIST_ITEMS, NSFW_WORKSPACE_MAX_PROVENANCE_TERMS - acceptedTerms),
		);
		if (!tags.length) continue;
		selected[groupName] = tags;
		acceptedGroups += 1;
		acceptedTerms += tags.length;
	}
	return selected;
}

function fitNsfwAppliedSelection(payload, selection) {
	const fitted = {};
	for (const [groupName, tags] of Object.entries(selection ?? {})) {
		const fittedTags = [];
		for (const tag of tags ?? []) {
			const candidate = { ...fitted, [groupName]: [...fittedTags, tag] };
			if (utf8ByteLength({ ...payload, applied_selected_tags: candidate }) > NSFW_WORKSPACE_MAX_JSON_BYTES) break;
			fittedTags.push(tag);
		}
		if (fittedTags.length) fitted[groupName] = fittedTags;
	}
	if (Object.keys(fitted).length || utf8ByteLength({ ...payload, applied_selected_tags: {} }) <= NSFW_WORKSPACE_MAX_JSON_BYTES) {
		payload.applied_selected_tags = fitted;
	}
}

function cloneBoundedNsfwProfileRestore(value) {
	const source = value && typeof value === "object" && !Array.isArray(value) ? value : {};
	const structured = Object.prototype.hasOwnProperty.call(source, "original") || Object.prototype.hasOwnProperty.call(source, "applied");
	const originalSource = structured && source.original && typeof source.original === "object" && !Array.isArray(source.original) ? source.original : structured ? {} : source;
	const appliedSource = structured && source.applied && typeof source.applied === "object" && !Array.isArray(source.applied) ? source.applied : {};
	const copyValues = (values) => {
		const result = {};
		for (const name of NSFW_GENERATION_PROFILE_SETTING_NAMES) {
			if (!Object.prototype.hasOwnProperty.call(values, name)) continue;
			const raw = values[name];
			if (typeof raw === "boolean") result[name] = raw;
			else if (typeof raw === "number" && Number.isFinite(raw)) result[name] = raw;
			else {
				const text = cleanNsfwWorkspaceScalar(raw, NSFW_WORKSPACE_MAX_SCALAR_CHARS);
				if (text) result[name] = text;
			}
		}
		return result;
	};
	return { original: copyValues(originalSource), applied: copyValues(appliedSource) };
}

function cloneNsfwWorkspaceState(workspace = null) {
	const base = cloneJsonSafe(NSFW_WORKSPACE_DEFAULTS, {});
	const rawSource = workspace && typeof workspace === "object" && !Array.isArray(workspace) ? workspace : {};
	const allowedFields = [...Object.keys(NSFW_WORKSPACE_DEFAULTS), ...NSFW_WORKSPACE_PROVENANCE_FIELDS];
	const allowedSet = new Set(allowedFields);
	const source = {};
	for (const field of allowedFields) {
		if (Object.prototype.hasOwnProperty.call(rawSource, field)) source[field] = rawSource[field];
	}
	for (const [legacyField, currentField] of Object.entries(NSFW_WORKSPACE_FIELD_ALIASES)) {
		if (!allowedSet.has(currentField) || Object.prototype.hasOwnProperty.call(source, currentField)) continue;
		if (Object.prototype.hasOwnProperty.call(rawSource, legacyField)) source[currentField] = rawSource[legacyField];
	}

	for (const field of NSFW_WORKSPACE_SCALAR_PRIORITY) {
		if (!Object.prototype.hasOwnProperty.call(source, field)) continue;
		if (field === "enabled") {
			const rawEnabled = source.enabled;
			base.enabled = typeof rawEnabled === "string"
				? new Set(["1", "true", "yes", "on", "开启", "是"]).has(rawEnabled.trim().toLowerCase())
				: !!rawEnabled;
			continue;
		}
		const maxChars = field === "custom_negative"
			? NSFW_WORKSPACE_MAX_NEGATIVE_CHARS
			: ["custom_prefix", "custom_suffix"].includes(field)
				? NSFW_WORKSPACE_MAX_CUSTOM_TEXT_CHARS
				: NSFW_WORKSPACE_MAX_SCALAR_CHARS;
		let value = cleanNsfwWorkspaceScalar(source[field], maxChars);
		if (field.startsWith("selector_")) value = cleanNsfwWorkspaceScalar(normalizeNsfwSelectorTerm(value), maxChars);
		if (field === "negative_apply_mode" && !["preview", "override", "append"].includes(value)) value = "preview";
		if (!value && !["custom_negative", "custom_prefix", "custom_suffix", "random_nonce"].includes(field)) value = String(base[field] ?? "").trim();
		fitNsfwWorkspaceText(base, field, value);
	}

	if (Object.prototype.hasOwnProperty.call(source, "generation_profile_restore")) {
		const restoreSnapshot = cloneBoundedNsfwProfileRestore(source.generation_profile_restore);
		if (hasSettingRestoreSnapshot(restoreSnapshot) && utf8ByteLength({ ...base, generation_profile_restore: restoreSnapshot }) <= NSFW_WORKSPACE_MAX_JSON_BYTES) {
			base.generation_profile_restore = restoreSnapshot;
		}
	}
	if (Object.prototype.hasOwnProperty.call(source, "applied_selected_tags")) {
		fitNsfwAppliedSelection(base, normalizeBoundedNsfwAppliedSelection(source.applied_selected_tags));
	}
	if (Object.prototype.hasOwnProperty.call(source, "applied_custom_tags")) {
		const tags = normalizeBoundedNsfwWorkspaceList(source.applied_custom_tags);
		fitNsfwWorkspaceList(base, "applied_custom_tags", tags, true);
	}
	if (Object.prototype.hasOwnProperty.call(source, "manual_custom_tags")) {
		const tags = normalizeBoundedNsfwWorkspaceList(source.manual_custom_tags);
		fitNsfwWorkspaceList(base, "manual_custom_tags", tags, true);
	}

	for (const field of NSFW_WORKSPACE_LIST_FIELDS) {
		if (!Object.prototype.hasOwnProperty.call(source, field)) continue;
		fitNsfwWorkspaceList(base, field, normalizeBoundedNsfwWorkspaceList(source[field]));
	}
	return base;
}

function resolveNsfwWorkspaceCatalog(library = null) {
	const remoteCatalog = library?.nsfw_workspace_catalog;
	if (remoteCatalog && typeof remoteCatalog === "object") {
		const defaults = cloneNsfwWorkspaceState(remoteCatalog.defaults ?? remoteCatalog.default ?? {});
		const negativePresets = remoteCatalog.negative_presets && typeof remoteCatalog.negative_presets === "object"
			? { ...NSFW_NEGATIVE_PRESETS, ...remoteCatalog.negative_presets }
			: { ...NSFW_NEGATIVE_PRESETS };
		const options = remoteCatalog.options && typeof remoteCatalog.options === "object"
			? { ...NSFW_WORKSPACE_OPTIONS, ...remoteCatalog.options }
			: { ...NSFW_WORKSPACE_OPTIONS };
		const presets = remoteCatalog.presets && typeof remoteCatalog.presets === "object"
			? { ...NSFW_WORKSPACE_PRESETS, ...remoteCatalog.presets }
			: { ...NSFW_WORKSPACE_PRESETS };
		const qualityTags = remoteCatalog.quality_tags && typeof remoteCatalog.quality_tags === "object"
			? { ...NSFW_QUALITY_TAGS, ...remoteCatalog.quality_tags }
			: { ...NSFW_QUALITY_TAGS };
		return { defaults, negativePresets, options, presets, qualityTags };
	}
	return {
		defaults: cloneNsfwWorkspaceState(),
		negativePresets: { ...NSFW_NEGATIVE_PRESETS },
		options: { ...NSFW_WORKSPACE_OPTIONS },
		presets: { ...NSFW_WORKSPACE_PRESETS },
		qualityTags: { ...NSFW_QUALITY_TAGS },
	};
}

function resolveNsfwNegativePrompt(workspace, negativePresets) {
	const presetName = String(workspace?.negative_preset ?? "标准负面提示词").trim() || "标准负面提示词";
	if (presetName === "自定义负面提示词") return String(workspace?.custom_negative ?? "").trim();
	return String((negativePresets ?? NSFW_NEGATIVE_PRESETS)[presetName] ?? negativePresets?.["标准负面提示词"] ?? NSFW_NEGATIVE_PRESETS["标准负面提示词"]).trim();
}

function isEmptyNsfwWorkspaceValue(value) {
	const text = String(value ?? "").trim();
	return !text || text === "——";
}

function canonicalizeNsfwSeedValue(value) {
	const text = String(value ?? "").normalize("NFKC").replace(/\s+/gu, " ").trim();
	return text === "——" ? "" : text;
}

function canonicalizeNsfwTriggerWordSeed(value) {
	const rawValues = Array.isArray(value) ? value : [value];
	const terms = new Set();
	for (const rawValue of rawValues) {
		for (const term of parseCustomTags(rawValue)) {
			if (term && term !== "——") terms.add(term);
		}
	}
	return [...terms].sort().join("|");
}

function hashNsfwSelectionSeed(value) {
	let hash = 0;
	for (const character of String(value ?? "")) {
		hash = (Math.imul(hash, 31) + character.codePointAt(0)) >>> 0;
	}
	return hash;
}

function buildNsfwSelectionSeed(field, workspace) {
	return [
		canonicalizeNsfwSeedValue(workspace?.preset),
		canonicalizeNsfwSeedValue(workspace?.quality_tier),
		canonicalizeNsfwSeedValue(workspace?.negative_preset),
		canonicalizeNsfwSeedValue(workspace?.random_mode),
		String(field ?? ""),
		canonicalizeNsfwTriggerWordSeed(workspace?.trigger_words),
		canonicalizeNsfwSeedValue(workspace?.random_nonce),
	].join("|");
}

let nsfwRandomNonceSequence = 0;
function createNsfwRandomNonce() {
	nsfwRandomNonceSequence = (nsfwRandomNonceSequence + 1) % Number.MAX_SAFE_INTEGER;
	const timestamp = Date.now().toString(36);
	const sequence = nsfwRandomNonceSequence.toString(36);
	const randomPart = Math.floor(Math.random() * 0x100000000).toString(36);
	return `${timestamp}-${sequence}-${randomPart}`;
}

function prepareNsfwRandomNonceForWriteback(workspace, reuseCurrent = false) {
	const randomMode = String(workspace?.random_mode ?? "关闭").trim() || "关闭";
	if (randomMode === "关闭") return String(workspace?.random_nonce ?? "").trim();
	const current = String(workspace?.random_nonce ?? "").trim();
	if (reuseCurrent && current) return current;
	workspace.random_nonce = createNsfwRandomNonce();
	return workspace.random_nonce;
}

function clearNsfwRandomNonceForField(workspace, field) {
	if (NSFW_RANDOM_SEED_FIELDS.has(field)) workspace.random_nonce = "";
}

function pickNsfwOption(options, field, workspace) {
	const values = Array.isArray(options?.[field])
		? options[field].map((item) => String(item ?? "").trim()).filter((item) => item && item !== "——")
		: [];
	if (!values.length) return "——";
	const hash = hashNsfwSelectionSeed(buildNsfwSelectionSeed(field, workspace));
	return values[hash % values.length];
}

function resolveNsfwEffectiveWorkspace(workspace, catalog = {}) {
	const effective = cloneNsfwWorkspaceState(workspace ?? null);
	const preset = catalog.presets?.[effective.preset];
	if (preset && typeof preset === "object") {
		for (const [key, value] of Object.entries(preset)) {
			if (!Object.prototype.hasOwnProperty.call(effective, key) || !isEmptyNsfwWorkspaceValue(effective[key])) continue;
			const presetValue = String(value ?? "").trim();
			if (!isEmptyNsfwWorkspaceValue(presetValue)) effective[key] = presetValue;
		}
	}
	const randomMode = String(effective.random_mode ?? "关闭").trim() || "关闭";
	if (randomMode === "场景随机" || randomMode === "全部随机") effective.scene = pickNsfwOption(catalog.options, "scene", effective);
	if (randomMode === "动作随机" || randomMode === "全部随机") effective.action = pickNsfwOption(catalog.options, "action", effective);
	if (randomMode === "全部随机") {
		for (const field of ["outfit", "mood", "camera_movement", "camera_angle", "light_source", "light_type", "lens_type", "focal_length", "color_tone", "visual_style", "effect", "filter"]) {
			effective[field] = pickNsfwOption(catalog.options, field, effective);
		}
	}
	return effective;
}

function mapNsfwWorkspaceToStageState(node, library, workspace, catalogOrNegativePresets) {
	const catalog = catalogOrNegativePresets?.negativePresets
		? catalogOrNegativePresets
		: { negativePresets: catalogOrNegativePresets ?? NSFW_NEGATIVE_PRESETS, options: NSFW_WORKSPACE_OPTIONS, presets: NSFW_WORKSPACE_PRESETS, qualityTags: NSFW_QUALITY_TAGS };
	const effectiveWorkspace = resolveNsfwEffectiveWorkspace(workspace, catalog);
	const nextState = collectNodeState(node, library) ?? { selected: {}, customTags: [], settings: {} };
	const selected = cloneSelection(nextState.selected ?? {});
	const customTags = [...(nextState.customTags ?? [])];
	const generatedTerms = [];
	const tagGroupIndex = buildTagGroupIndex(library);
	const groupLimits = Object.fromEntries((library?.slot_config ?? []).map((group) => [group.name, getTagGroupSlotLimit(library, group.name)]));
	const pushGeneratedTerm = (value) => {
		const text = String(value ?? "").trim();
		if (text && text !== "——" && !generatedTerms.includes(text)) generatedTerms.push(text);
	};
	const pushMappedTerm = (value) => {
		const text = String(value ?? "").trim();
		if (!text || text === "——") return;
		pushGeneratedTerm(text);
		const groupName = tagGroupIndex.get(text);
		const limit = Math.max(0, Number(groupLimits[groupName] ?? 0));
		if (groupName && limit > 0) {
			const bucket = selected[groupName] ?? (selected[groupName] = []);
			if (!bucket.includes(text) && bucket.length < limit) {
				bucket.push(text);
				return;
			}
		}
		if (!customTags.includes(text)) customTags.push(text);
	};
	const pushMappedTerms = (value, normalizeSelector = false) => {
		for (const term of parseCustomTags(Array.isArray(value) ? value.join(", ") : value)) {
			pushMappedTerm(normalizeSelector ? normalizeNsfwSelectorTerm(term) : term);
		}
	};
	const triggerWords = Array.isArray(effectiveWorkspace?.trigger_words)
		? effectiveWorkspace.trigger_words.map((item) => String(item ?? "").trim()).filter(Boolean)
		: parseCustomTags(effectiveWorkspace?.trigger_words ?? "");
	const textFields = ["workspace_custom_tags", "selector_character", "selector_outfit", "selector_action", "selector_scene", "selector_expression", "selector_prop", "scene", "action", "outfit", "mood", "anatomy_terms", "explicit_terms", "adult_action_style", "camera_movement", "camera_angle", "light_source", "light_type", "lens_type", "focal_length", "color_tone", "visual_style", "effect", "filter", "custom_prefix", "custom_suffix"];
	for (const tag of triggerWords) pushMappedTerms(tag);
	for (const field of textFields) pushMappedTerms(effectiveWorkspace?.[field], field.startsWith("selector_"));
	for (const tag of catalog.qualityTags?.[effectiveWorkspace.quality_tier] ?? []) {
		const text = String(tag ?? "").trim();
		if (text && !customTags.includes(text)) customTags.push(text);
		pushGeneratedTerm(text);
	}
	const negativePrompt = resolveNsfwNegativePrompt(effectiveWorkspace, catalog.negativePresets);
	const negative = {
		mode: String(effectiveWorkspace?.negative_apply_mode ?? "preview").trim() || "preview",
		prompt: negativePrompt,
		preset: String(effectiveWorkspace?.negative_preset ?? "标准负面提示词").trim() || "标准负面提示词",
	};
	return {
		selected,
		custom_tags: customTags,
		generated_terms: generatedTerms,
		negative_prompt: negativePrompt,
		negative,
		effective_workspace: effectiveWorkspace,
	};
}

function buildNsfwWorkspaceMappedState(node, library, workspace, catalogOrNegativePresets) {
	const nextWorkspace = cloneNsfwWorkspaceState(workspace ?? null);
	const catalog = catalogOrNegativePresets?.negativePresets
		? catalogOrNegativePresets
		: resolveNsfwWorkspaceCatalog(library);
	const mapped = mapNsfwWorkspaceToStageState(node, library, nextWorkspace, catalog);
	return {
		...mapped,
		negative_apply_mode: nextWorkspace.negative_apply_mode,
		nsfw_workspace: nextWorkspace,
	};
}

function buildNsfwWorkspaceNegativeSyncPlan(node, mappedState, negativePresets, baseNegativeText = null) {
	const mode = String(mappedState?.negative_apply_mode ?? "preview").trim() || "preview";
	const negativeText = resolveNsfwNegativePrompt(mappedState?.nsfw_workspace, negativePresets);
	if (!negativeText) return { mode, negativeText: "", syncText: null, reason: "empty" };
	if (mode === "override") return { mode, negativeText, syncText: negativeText, reason: "override" };
	if (mode === "append") {
		const baseNegative = String(baseNegativeText ?? "").trim();
		const syncText = parseCustomTags([baseNegative, negativeText].filter(Boolean).join(", ")).join(", ");
		return { mode, negativeText, syncText, reason: "append" };
	}
	return { mode, negativeText, syncText: null, reason: "preview" };
}

function applyNsfwGenerationProfileToState(state) {
	if (!state || typeof state !== "object") return false;
	const settings = { ...(state.settings ?? {}) };
	let changed = false;
	const templateStyle = String(settings["模板风格"] ?? PRESET_SETTING_DEFAULTS["模板风格"] ?? "自动").trim() || "自动";
	const subjectType = String(settings["主体类型"] ?? PRESET_SETTING_DEFAULTS["主体类型"] ?? "自动").trim() || "自动";
	if (templateStyle === "自动") {
		settings["模板风格"] = NSFW_GENERATION_PROFILE.templateStyle;
		changed = true;
	}
	if (subjectType === "自动") {
		settings["主体类型"] = NSFW_GENERATION_PROFILE.subjectType;
		changed = true;
	}
	if (settings["标签反推模式"] !== NSFW_GENERATION_PROFILE.reverseMode) {
		settings["标签反推模式"] = NSFW_GENERATION_PROFILE.reverseMode;
		changed = true;
	}
	if (settings["优先柔和肤质"] !== true) {
		settings["优先柔和肤质"] = true;
		changed = true;
	}
	if (settings["抑制文字伪影"] !== true) {
		settings["抑制文字伪影"] = true;
		changed = true;
	}
	state.settings = settings;
	return changed;
}

function applyNsfwWorkspaceResultToNodeState(node, library, mappedState) {
	if (!node || !library || !mappedState) return false;
	const current = collectNodeState(node, library);
	const previousWorkspace = current.nsfwWorkspace ?? current.nsfw_workspace ?? null;
	const previousSelected = cloneSelection(current.selected ?? {});
	const nextWorkspace = cloneNsfwWorkspaceState(mappedState.nsfw_workspace ?? previousWorkspace ?? {});
	nextWorkspace.enabled = true;
	const nextTerms = Array.isArray(mappedState.generated_terms) && mappedState.generated_terms.length
		? [...mappedState.generated_terms]
		: collectNsfwWorkspaceTerms(nextWorkspace);
	const reconciledSelection = reconcileNsfwWorkspaceSelectedTags(
		previousSelected,
		previousWorkspace,
		mappedState.selected ?? {},
		nextTerms,
	);
	current.selected = reconciledSelection.selected;
	const baseCustomTags = Array.isArray(mappedState.custom_tags) ? [...mappedState.custom_tags] : [];
	const merged = rewriteNsfwWorkspaceCustomTags(baseCustomTags, previousWorkspace, nextTerms);
	current.customTags = merged.customTags;
	nextWorkspace.applied_custom_tags = [...(merged.appliedCustomTags ?? nextTerms)];
	if (Array.isArray(merged.manualCustomTags)) {
		nextWorkspace.manual_custom_tags = [...merged.manualCustomTags];
		nextWorkspace.user_custom_tags = [...merged.manualCustomTags];
	} else {
		delete nextWorkspace.manual_custom_tags;
		delete nextWorkspace.user_custom_tags;
	}
	nextWorkspace.applied_selected_tags = reconciledSelection.appliedSelectedTags;
	const profileSettingsBefore = { ...(current.settings ?? {}) };
	applyNsfwGenerationProfileToState(current);
	const properties = ensureNodeProperties(node);
	const existingProfileRestore = nextWorkspace.generation_profile_restore ?? properties[NODE_NSFW_PROFILE_RESTORE_KEY] ?? {};
	const profileRestore = updateSettingRestoreSnapshot(
		existingProfileRestore,
		profileSettingsBefore,
		current.settings,
		NSFW_GENERATION_PROFILE_SETTING_NAMES,
	);
	if (hasSettingRestoreSnapshot(profileRestore)) nextWorkspace.generation_profile_restore = profileRestore;
	else delete nextWorkspace.generation_profile_restore;
	delete properties[NODE_NSFW_PROFILE_RESTORE_KEY];
	current.nsfwWorkspace = nextWorkspace;
	applyNodeState(node, library, current, { recordHistory: true, historySource: "nsfw-workspace" });
	return true;
}

function disableNsfwWorkspaceOnNodeState(node, library) {
	if (!node || !library) return false;
	const current = collectNodeState(node, library);
	const previousWorkspace = current.nsfwWorkspace ?? current.nsfw_workspace ?? null;
	const nextWorkspace = cloneNsfwWorkspaceState(previousWorkspace ?? {});
	nextWorkspace.enabled = false;
	const manualTags = collectNsfwWorkspaceManualCustomTags(nextWorkspace);
	const appliedTerms = collectNsfwWorkspaceAppliedTerms(nextWorkspace);
	const legacyTerms = appliedTerms.length ? appliedTerms : collectNsfwWorkspaceTerms(nextWorkspace);
	removeNsfwWorkspaceSelectedTags(current, nextWorkspace);
	current.customTags = (current.customTags ?? []).filter((tag) => !legacyTerms.includes(tag) || manualTags.includes(tag));
	nextWorkspace.applied_custom_tags = [];
	nextWorkspace.applied_selected_tags = {};
	if (manualTags.length) {
		nextWorkspace.manual_custom_tags = [...manualTags];
		nextWorkspace.user_custom_tags = [...manualTags];
	} else {
		delete nextWorkspace.manual_custom_tags;
		delete nextWorkspace.user_custom_tags;
	}
	const properties = ensureNodeProperties(node);
	const profileRestore = cloneSettingRestoreSnapshot(
		nextWorkspace.generation_profile_restore ?? properties[NODE_NSFW_PROFILE_RESTORE_KEY] ?? {},
		NSFW_GENERATION_PROFILE_SETTING_NAMES,
	);
	if (hasSettingRestoreSnapshot(profileRestore)) {
		current.settings = restoreSettingsFromSnapshot(current.settings, profileRestore, NSFW_GENERATION_PROFILE_SETTING_NAMES);
	}
	delete nextWorkspace.generation_profile_restore;
	delete properties[NODE_NSFW_PROFILE_RESTORE_KEY];
	current.nsfwWorkspace = nextWorkspace;
	applyNodeState(node, library, current, { recordHistory: true, historySource: "nsfw-workspace-disabled" });
	return true;
}

function persistNsfwWorkspaceToggleToNodeState(node, library, workspace, enabled) {
	if (!node || !library) return false;
	beginNodeStateMutation(node);
	const properties = ensureNodeProperties(node);
	const previousWorkspace = properties.nsfw_workspace ?? properties.nsfwWorkspace ?? {};
	const nextWorkspace = cloneNsfwWorkspaceState({
		...(previousWorkspace && typeof previousWorkspace === "object" ? previousWorkspace : {}),
		...(workspace && typeof workspace === "object" ? workspace : {}),
	});
	nextWorkspace.enabled = !!enabled;
	properties.nsfw_workspace = nextWorkspace;
	properties.nsfwWorkspace = cloneNsfwWorkspaceState(nextWorkspace);
	setWidgetValue(node, RUNTIME_RANDOM_PROTECTED_TAGS_WIDGET_NAME, collectNsfwRuntimeProtectedTags({ nsfwWorkspace: nextWorkspace, settings: {} }).join(", "));
	persistNamedWidgetState(node);
	refreshNodeSummary(node, library);
	refreshNodeActionButtons(node);
	scheduleNodeLayoutUpdate(node);
	return true;
}

function getNodeNsfwWorkspaceState(node, library = null) {
	const properties = ensureNodeProperties(node);
	if (properties.nsfw_workspace || properties.nsfwWorkspace) {
		return cloneNsfwWorkspaceState(properties.nsfw_workspace ?? properties.nsfwWorkspace ?? null);
	}
	const catalog = resolveNsfwWorkspaceCatalog(library);
	return cloneNsfwWorkspaceState(catalog.defaults);
}

function openNsfwWorkspaceDialog(node, library) {
	ensureSingleModal("nsfw-workspace");
	const modalContext = buildNodeModalContext(node, library);
	const catalog = resolveNsfwWorkspaceCatalog(library);
	const workspace = cloneNsfwWorkspaceState(getNodeNsfwWorkspaceState(node, library) ?? catalog.defaults);
	const overlay = document.createElement("div");
	overlay.className = "qwen-te-modal";
	overlay.dataset.qwenModal = "nsfw-workspace";
	overlay.__qwenNode = node;
	const dialog = document.createElement("div");
	dialog.className = "qwen-te-modal__dialog";
	overlay.appendChild(dialog);
	const header = document.createElement("div");
	header.className = "qwen-te-modal__header";
	dialog.appendChild(header);
	const titleWrap = document.createElement("div");
	header.appendChild(titleWrap);
	const title = document.createElement("div");
	title.className = "qwen-te-modal__title";
	title.textContent = `NSFW 工作台 · ${modalContext.nodeName}`;
	titleWrap.appendChild(title);
	const subtitle = document.createElement("div");
	subtitle.className = "qwen-te-modal__subtitle";
	subtitle.textContent = `在当前阶段面板内预览结构化选择、负面预设和写回结果。当前输出来源：${modalContext.outputSource}。`;
	titleWrap.appendChild(subtitle);
	const closeButton = document.createElement("button");
	closeButton.className = "qwen-te-modal__footer-button";
	closeButton.textContent = "关闭";
	header.appendChild(closeButton);
	const body = document.createElement("div");
	body.className = "qwen-te-modal__body";
	dialog.appendChild(body);
	const toolbar = document.createElement("div");
	toolbar.className = "qwen-te-modal__toolbar";
	body.appendChild(toolbar);
	const enableButton = document.createElement("button");
	enableButton.className = "qwen-te-modal__footer-button qwen-te-modal__footer-button--primary";
	toolbar.appendChild(enableButton);
	const previewButton = document.createElement("button");
	previewButton.className = "qwen-te-modal__footer-button";
	previewButton.textContent = "预览映射";
	toolbar.appendChild(previewButton);
	const applyButton = document.createElement("button");
	applyButton.className = "qwen-te-modal__footer-button qwen-te-modal__footer-button--accent";
	applyButton.textContent = "写回当前节点";
	toolbar.appendChild(applyButton);
	const negativeApplyButton = document.createElement("button");
	negativeApplyButton.className = "qwen-te-modal__footer-button qwen-te-modal__footer-button--accent";
	negativeApplyButton.textContent = "写回并同步负面";
	toolbar.appendChild(negativeApplyButton);
	const statusEl = document.createElement("div");
	statusEl.className = "qwen-te-modal__status";
	statusEl.textContent = "默认是预览态，写回时会把当前工作台结果落到节点状态里。";
	body.appendChild(statusEl);
	const workspaceGrid = document.createElement("div");
	workspaceGrid.className = "qwen-te-modal__workspace";
	body.appendChild(workspaceGrid);
	const workspaceMain = document.createElement("div");
	workspaceMain.className = "qwen-te-modal__workspace-main";
	workspaceGrid.appendChild(workspaceMain);
	const workspaceSide = document.createElement("div");
	workspaceSide.className = "qwen-te-modal__workspace-side";
	workspaceGrid.appendChild(workspaceSide);
	const tabBar = document.createElement("div");
	tabBar.className = "qwen-te-modal__stage-output-tabs qwen-te-modal__nsfw-tabs";
	workspaceMain.appendChild(tabBar);
	const tabButtons = new Map();
	let activeSection = NSFW_WORKSPACE_FIELD_SECTIONS[0].key;
	let reusePreviewNonceOnWriteback = false;
	const getFirstCustomLibraryField = (sectionKey = "") => {
		const section = NSFW_WORKSPACE_FIELD_SECTIONS.find((item) => item.key === sectionKey) ?? NSFW_WORKSPACE_FIELD_SECTIONS[0];
		return section?.fields?.find((field) => NSFW_CUSTOM_FIELD_LIBRARY_FIELDS.includes(field)) ?? NSFW_CUSTOM_FIELD_LIBRARY_FIELDS[0];
	};
	let nsfwCustomLibraryField = getFirstCustomLibraryField(activeSection);
	let nsfwCustomLibraryDraft = "";
	let nsfwCustomLibraryStatus = "这里单独维护 NSFW 下拉项自己的标签库，不走主标签库。";
	const renderWorkspace = () => {
		workspaceMain.querySelectorAll(".qwen-te-modal__nsfw-surface").forEach((item) => item.remove());
		for (const section of NSFW_WORKSPACE_FIELD_SECTIONS) {
			const surface = document.createElement("section");
			surface.className = "qwen-te-modal__surface qwen-te-modal__nsfw-surface";
			surface.style.display = section.key === activeSection ? "flex" : "none";
			workspaceMain.appendChild(surface);
			const head = document.createElement("div");
			head.className = "qwen-te-modal__surface-head";
			surface.appendChild(head);
			const headText = document.createElement("div");
			head.appendChild(headText);
			const surfaceTitle = document.createElement("div");
			surfaceTitle.className = "qwen-te-modal__surface-title";
			surfaceTitle.textContent = section.label;
			headText.appendChild(surfaceTitle);
			const surfaceDesc = document.createElement("div");
			surfaceDesc.className = "qwen-te-modal__surface-desc";
			surfaceDesc.textContent = section.description;
			headText.appendChild(surfaceDesc);
			for (const field of section.fields) {
				const row = document.createElement("div");
				row.className = "qwen-te-modal__toolbar-row qwen-te-modal__nsfw-row";
				surface.appendChild(row);
				const label = document.createElement("div");
				label.className = "qwen-te-modal__toolbar-section-title";
				label.textContent = NSFW_WORKSPACE_FIELD_LABELS[field] ?? field;
				row.appendChild(label);
				if (field === "trigger_words" || field === "custom_negative" || field === "custom_prefix" || field === "custom_suffix") {
					const input = document.createElement("textarea");
					input.className = "qwen-te-modal__textarea";
					input.value = Array.isArray(workspace[field]) ? workspace[field].join(", ") : String(workspace[field] ?? "");
					input.rows = field === "custom_negative" ? 5 : 3;
					input.oninput = () => {
						workspace[field] = field === "trigger_words" ? parseCustomTags(input.value) : String(input.value ?? "").trim();
						clearNsfwRandomNonceForField(workspace, field);
						if (NSFW_RANDOM_SEED_FIELDS.has(field)) reusePreviewNonceOnWriteback = false;
					};
					row.appendChild(input);
					continue;
				}
				const select = document.createElement("select");
				select.className = "qwen-te-modal__search";
				const options = field === "negative_preset"
					? Object.keys(catalog.negativePresets)
					: field === "negative_apply_mode"
						? ["preview", "override", "append"]
						: field === "preset"
							? [NSFW_WORKSPACE_DEFAULTS.preset, ...(catalog.presets ? Object.keys(catalog.presets) : NSFW_WORKSPACE_OPTIONS.preset)]
							: field === "quality_tier"
								? [NSFW_WORKSPACE_DEFAULTS.quality_tier, ...(catalog.qualityTags ? Object.keys(catalog.qualityTags) : NSFW_WORKSPACE_OPTIONS.quality_tier)]
								: catalog.options?.[field] ?? NSFW_WORKSPACE_OPTIONS[field] ?? [NSFW_WORKSPACE_DEFAULTS[field]];
				const customOptions = NSFW_CUSTOM_FIELD_LIBRARY_FIELDS.includes(field) ? getNsfwCustomFieldOptions(field) : [];
				const currentValue = String(workspace[field] ?? "").trim();
				const mergedOptions = uniqueTextList([
					...(Array.isArray(options) ? options : []),
					...customOptions,
					...(currentValue && currentValue !== "——" ? [currentValue] : []),
				]);
				for (const optionValue of mergedOptions) {
					const option = document.createElement("option");
					option.value = optionValue;
					option.textContent = optionValue;
					select.appendChild(option);
				}
				select.value = String(workspace[field] ?? NSFW_WORKSPACE_DEFAULTS[field]);
				select.onchange = () => {
					workspace[field] = select.value;
					clearNsfwRandomNonceForField(workspace, field);
					if (NSFW_RANDOM_SEED_FIELDS.has(field)) reusePreviewNonceOnWriteback = false;
				};
				row.appendChild(select);
			}
		}
		workspaceSide.replaceChildren();
		const customFieldCard = document.createElement("section");
		customFieldCard.className = "qwen-te-modal__surface";
		workspaceSide.appendChild(customFieldCard);
		const customFieldTitle = document.createElement("div");
		customFieldTitle.className = "qwen-te-modal__surface-title";
		customFieldTitle.textContent = "NSFW 自定义字段库";
		customFieldCard.appendChild(customFieldTitle);
		const customFieldDesc = document.createElement("div");
		customFieldDesc.className = "qwen-te-modal__surface-desc";
		customFieldDesc.textContent = "给 NSFW 下拉字段单独添加选项；这些词只在 NSFW 工作台里使用，不会写入主标签库。";
		customFieldCard.appendChild(customFieldDesc);
		const customFieldSelect = document.createElement("select");
		customFieldSelect.className = "qwen-te-modal__search";
		for (const section of NSFW_WORKSPACE_FIELD_SECTIONS) {
			const fields = (section.fields ?? []).filter((field) => NSFW_CUSTOM_FIELD_LIBRARY_FIELDS.includes(field));
			if (!fields.length) continue;
			const group = document.createElement("optgroup");
			group.label = section.label;
			for (const field of fields) {
				const option = document.createElement("option");
				option.value = field;
				option.textContent = NSFW_WORKSPACE_FIELD_LABELS[field] ?? field;
				group.appendChild(option);
			}
			customFieldSelect.appendChild(group);
		}
		customFieldSelect.value = nsfwCustomLibraryField;
		customFieldSelect.onchange = () => {
			nsfwCustomLibraryField = customFieldSelect.value;
			nsfwCustomLibraryStatus = `正在维护字段：${NSFW_WORKSPACE_FIELD_LABELS[nsfwCustomLibraryField] ?? nsfwCustomLibraryField}。`;
			renderWorkspace();
		};
		customFieldCard.appendChild(customFieldSelect);
		const customFieldInput = document.createElement("textarea");
		customFieldInput.className = "qwen-te-modal__textarea";
		customFieldInput.rows = 2;
		customFieldInput.placeholder = "一行一条自定义选项；逗号会保留在同一项里。";
		customFieldInput.value = nsfwCustomLibraryDraft;
		customFieldInput.style.minHeight = "54px";
		customFieldInput.style.maxHeight = "92px";
		customFieldInput.oninput = () => {
			nsfwCustomLibraryDraft = customFieldInput.value;
		};
		customFieldCard.appendChild(customFieldInput);
		const customFieldActions = document.createElement("div");
		customFieldActions.className = "qwen-te-modal__toolbar qwen-te-modal__toolbar--online-actions";
		customFieldCard.appendChild(customFieldActions);
		const addCustomFieldButton = document.createElement("button");
		addCustomFieldButton.type = "button";
		addCustomFieldButton.className = "qwen-te-modal__footer-button qwen-te-modal__footer-button--primary";
		addCustomFieldButton.textContent = "加入当前字段";
		addCustomFieldButton.onclick = () => {
			const result = addNsfwCustomFieldOptions(nsfwCustomLibraryField, nsfwCustomLibraryDraft);
			if (!result.ok) {
				nsfwCustomLibraryStatus = result.reason === "storage"
					? "保存失败：浏览器本地存储空间不足或已被禁用。"
					: "当前字段暂不支持自定义选项。";
			} else if (!result.added) {
				nsfwCustomLibraryStatus = result.skipped ? "没有新增：选项已存在、过长或当前字段已达上限。" : "请输入至少一条自定义选项。";
			} else {
				nsfwCustomLibraryStatus = `已加入 ${result.added} 条到 ${NSFW_WORKSPACE_FIELD_LABELS[nsfwCustomLibraryField] ?? nsfwCustomLibraryField}。`;
				nsfwCustomLibraryDraft = "";
			}
			renderWorkspace();
		};
		customFieldActions.appendChild(addCustomFieldButton);
		const clearCustomFieldButton = document.createElement("button");
		clearCustomFieldButton.type = "button";
		clearCustomFieldButton.className = "qwen-te-modal__footer-button";
		clearCustomFieldButton.textContent = "清空输入";
		clearCustomFieldButton.onclick = () => {
			nsfwCustomLibraryDraft = "";
			nsfwCustomLibraryStatus = "已清空输入框，已保存的自定义库不会被删除。";
			renderWorkspace();
		};
		customFieldActions.appendChild(clearCustomFieldButton);
		const customFieldStatus = document.createElement("div");
		customFieldStatus.className = "qwen-te-modal__status qwen-te-modal__status--panel";
		customFieldStatus.textContent = nsfwCustomLibraryStatus;
		customFieldCard.appendChild(customFieldStatus);
		const savedCustomOptions = getNsfwCustomFieldOptions(nsfwCustomLibraryField);
		const savedCustomWrap = document.createElement("div");
		savedCustomWrap.className = "qwen-te-modal__surface-meta";
		savedCustomWrap.style.maxHeight = "148px";
		savedCustomWrap.style.overflow = "auto";
		customFieldCard.appendChild(savedCustomWrap);
		if (!savedCustomOptions.length) {
			const emptyTip = document.createElement("div");
			emptyTip.className = "qwen-te-modal__surface-desc";
			emptyTip.textContent = `这个字段还没有自定义选项：${NSFW_WORKSPACE_FIELD_LABELS[nsfwCustomLibraryField] ?? nsfwCustomLibraryField}。`;
			savedCustomWrap.appendChild(emptyTip);
		} else {
			for (const optionValue of savedCustomOptions) {
				const optionWrap = document.createElement("span");
				optionWrap.style.display = "inline-flex";
				optionWrap.style.alignItems = "center";
				optionWrap.style.gap = "4px";
				const optionButton = document.createElement("button");
				optionButton.type = "button";
				optionButton.className = "qwen-te-modal__surface-pill";
				optionButton.textContent = optionValue;
				optionButton.title = "点选写入当前 NSFW 字段。";
				if (String(workspace[nsfwCustomLibraryField] ?? "") === optionValue) {
					optionButton.classList.add("qwen-te-modal__surface-pill--accent");
				}
				optionButton.onclick = () => {
					workspace[nsfwCustomLibraryField] = optionValue;
					nsfwCustomLibraryStatus = `已选：${optionValue}`;
					renderWorkspace();
				};
				optionWrap.appendChild(optionButton);
				const removeButton = document.createElement("button");
				removeButton.type = "button";
				removeButton.className = "qwen-te-modal__footer-button";
				removeButton.textContent = "删";
				removeButton.title = "只从 NSFW 自定义字段库删除，不影响已生成历史。";
				removeButton.style.padding = "3px 7px";
				removeButton.onclick = () => {
					const result = removeNsfwCustomFieldOption(nsfwCustomLibraryField, optionValue);
					if (result.removed && String(workspace[nsfwCustomLibraryField] ?? "") === optionValue) {
						workspace[nsfwCustomLibraryField] = NSFW_WORKSPACE_DEFAULTS[nsfwCustomLibraryField] ?? "——";
					}
					nsfwCustomLibraryStatus = result.removed
						? `已删除：${optionValue}`
						: result.reason === "storage" ? "删除保存失败：浏览器本地存储不可用。" : "没有找到要删除的选项。";
					renderWorkspace();
				};
				optionWrap.appendChild(removeButton);
				savedCustomWrap.appendChild(optionWrap);
			}
		}
		const sideCard = document.createElement("section");
		sideCard.className = "qwen-te-modal__surface";
		workspaceSide.appendChild(sideCard);
		const sideTitle = document.createElement("div");
		sideTitle.className = "qwen-te-modal__surface-title";
		sideTitle.textContent = "当前工作台摘要";
		sideCard.appendChild(sideTitle);
		const sideDesc = document.createElement("div");
		sideDesc.className = "qwen-te-modal__surface-desc";
		sideDesc.textContent = `${workspace.enabled ? "已启用：运行时会进入 NSFW 分支" : "未启用：仅预览，写回后自动启用"}。触发词 ${workspace.trigger_words.length} 个，预设：${workspace.preset}，质量：${workspace.quality_tier}，负面预设：${workspace.negative_preset}。`;
		sideCard.appendChild(sideDesc);
		const badgeRow = document.createElement("div");
		badgeRow.className = "qwen-te-modal__surface-meta";
		sideCard.appendChild(badgeRow);
		const summaryBadges = [
			...(workspace.trigger_words ?? []),
			workspace.selector_character,
			workspace.selector_outfit,
			workspace.selector_action,
			workspace.selector_scene,
			workspace.selector_expression,
			workspace.selector_prop,
			workspace.scene,
			workspace.action,
			workspace.outfit,
			workspace.mood,
			workspace.anatomy_terms,
			workspace.explicit_terms,
			workspace.adult_action_style,
			workspace.camera_angle,
			workspace.lens_type,
		].map((item) => String(item ?? "").trim()).filter((item) => item && item !== "——");
		for (const badgeText of summaryBadges.length ? summaryBadges.slice(0, 18) : ["尚未选择"]) {
			const badge = document.createElement("div");
			badge.className = "qwen-te-modal__surface-pill";
			badge.textContent = badgeText;
			badgeRow.appendChild(badge);
		}
		const statePreview = document.createElement("div");
		statePreview.className = "qwen-te-modal__status qwen-te-modal__status--panel";
		statePreview.textContent = workspace.enabled
			? "当前工作台已启用。下一次运行节点会按 NSFW 工作台分支合并标签与负面预设。"
			: "当前工作台未启用。可先预览；点写回会自动启用并写入当前节点。";
		sideCard.appendChild(statePreview);
		const negativePreview = document.createElement("div");
		negativePreview.className = "qwen-te-modal__status qwen-te-modal__status--panel";
		negativePreview.textContent = resolveNsfwNegativePrompt(resolveNsfwEffectiveWorkspace(workspace, catalog), catalog.negativePresets) || "当前没有负面提示词。";
		sideCard.appendChild(negativePreview);
	};
	for (const section of NSFW_WORKSPACE_FIELD_SECTIONS) {
		const button = document.createElement("button");
		button.type = "button";
		button.className = "qwen-te-modal__stage-output-tab";
		button.textContent = section.label;
		button.onclick = () => {
			activeSection = section.key;
			const nextCustomField = section.fields?.find((field) => NSFW_CUSTOM_FIELD_LIBRARY_FIELDS.includes(field));
			if (nextCustomField) nsfwCustomLibraryField = nextCustomField;
			for (const [key, tabButton] of tabButtons.entries()) {
				tabButton.classList.toggle("is-active", key === activeSection);
			}
			renderWorkspace();
		};
		tabBar.appendChild(button);
		tabButtons.set(section.key, button);
	}
	tabButtons.get(activeSection)?.classList.add("is-active");
	const collectMappedState = () => buildNsfwWorkspaceMappedState(node, library, workspace, catalog);
	const refreshEnableButton = () => {
		enableButton.textContent = workspace.enabled ? "停用工作台" : "启用工作台";
		enableButton.classList.toggle("qwen-te-modal__footer-button--primary", !workspace.enabled);
		enableButton.classList.toggle("qwen-te-modal__footer-button--danger", workspace.enabled);
		enableButton.title = workspace.enabled ? "关闭 NSFW 分支，并移除上次由工作台写入的补充词。" : "启用 NSFW 工作台分支。";
	};
	refreshEnableButton();
	enableButton.onclick = () => {
		if (workspace.enabled) {
			if (!disableNsfwWorkspaceOnNodeState(node, library)) {
				statusEl.textContent = "停用失败：节点或节点库不可用。";
				return;
			}
			workspace.enabled = false;
			workspace.applied_custom_tags = [];
			statusEl.textContent = "已停用 NSFW 工作台，并移除上次工作台写入的补充词。";
			refreshEnableButton();
			renderWorkspace();
			return;
		}
		workspace.enabled = true;
		if (!persistNsfwWorkspaceToggleToNodeState(node, library, workspace, true)) {
			workspace.enabled = false;
			statusEl.textContent = "启用失败：节点或节点库不可用。";
			refreshEnableButton();
			renderWorkspace();
			return;
		}
		statusEl.textContent = "工作台已启用并保存到当前节点；外部 NSFW 按钮会保持开启。写回按钮仍用于把当前标签映射写入节点。";
		setNodeStatusText(node, "NSFW 工作台已启用。");
		refreshEnableButton();
		renderWorkspace();
	};
	previewButton.onclick = () => {
		if ((String(workspace.random_mode ?? "关闭").trim() || "关闭") !== "关闭") {
			prepareNsfwRandomNonceForWriteback(workspace, false);
			reusePreviewNonceOnWriteback = true;
			if (!persistNsfwWorkspaceToggleToNodeState(node, library, workspace, workspace.enabled)) {
				statusEl.textContent = "预览失败：随机工作台状态无法保存到当前节点。";
				return;
			}
		}
		const mapped = collectMappedState();
		statusEl.textContent = `预览完成：会写入 ${mapped.custom_tags.length} 个补充词，负面预设 ${workspace.negative_preset}。`;
	};
	applyButton.onclick = async () => {
		prepareNsfwRandomNonceForWriteback(workspace, reusePreviewNonceOnWriteback);
		reusePreviewNonceOnWriteback = false;
		const mapped = collectMappedState();
		if (!applyNsfwWorkspaceResultToNodeState(node, library, mapped)) {
			statusEl.textContent = "写回失败：节点或节点库不可用。";
			return;
		}
		statusEl.textContent = "已写回当前节点。";
		workspace.enabled = true;
		refreshEnableButton();
		renderWorkspace();
	};
	negativeApplyButton.onclick = async () => {
		prepareNsfwRandomNonceForWriteback(workspace, reusePreviewNonceOnWriteback);
		reusePreviewNonceOnWriteback = false;
		const mapped = collectMappedState();
		if (!applyNsfwWorkspaceResultToNodeState(node, library, mapped)) {
			statusEl.textContent = "写回失败：节点或节点库不可用。";
			return;
		}
		const previewPlan = buildNsfwWorkspaceNegativeSyncPlan(node, mapped, catalog.negativePresets);
		if (previewPlan.reason === "preview") {
			setNodeStatusText(node, `已写回当前节点，NSFW 负面预设保持预览：${mapped.nsfw_workspace.negative_preset}。`);
			statusEl.textContent = "已写回当前节点；当前应用方式为 preview，负面词仅预览未同步。";
			workspace.enabled = true;
			refreshEnableButton();
			renderWorkspace();
			return;
		}
		if (previewPlan.reason === "empty") {
			statusEl.textContent = "已写回当前节点；当前负面预设为空，未修改负面编码节点。";
			workspace.enabled = true;
			refreshEnableButton();
			renderWorkspace();
			return;
		}
		const targetNode = findNegativeClipTextEncodeNode(node);
		if (!targetNode) {
			statusEl.textContent = "已写回，但无法唯一定位当前工作流的负面编码节点。";
			return;
		}
		const targetNegativeText = String(getWidget(targetNode, "text")?.value ?? "").trim();
		const syncPlan = buildNsfwWorkspaceNegativeSyncPlan(node, mapped, catalog.negativePresets, targetNegativeText);
		const syncResult = syncNegativePromptToGraph(node, syncPlan.syncText, targetNode);
		if (!syncResult.ok) {
			statusEl.textContent = syncResult.reason === "not_found"
				? "已写回，但没有找到可同步的负面编码节点。"
				: "已写回，但当前没有可同步的负面提示词。";
			return;
		}
		if (syncPlan.mode === "override") {
			setNodeStatusText(node, `已写回并覆盖同步 NSFW 负面预设：${mapped.nsfw_workspace.negative_preset}。`);
			statusEl.textContent = "已写回并同步负面。";
			workspace.enabled = true;
			refreshEnableButton();
			renderWorkspace();
			return;
		}
		setNodeStatusText(node, `已写回并追加同步 NSFW 负面预设：${mapped.nsfw_workspace.negative_preset}。`);
		statusEl.textContent = "已写回并追加负面。";
		workspace.enabled = true;
		refreshEnableButton();
		renderWorkspace();
	};
	closeButton.onclick = () => overlay.remove();
	overlay.addEventListener("click", (event) => { if (event.target === overlay) overlay.remove(); });
	document.body.appendChild(overlay);
	renderWorkspace();
}

function openContinuousReportDialog(node, library) {
	ensureSingleModal("continuous-report");
	const modalContext = buildNodeModalContext(node, library);
	const overlay = document.createElement("div"); overlay.className = "qwen-te-modal";
	overlay.dataset.qwenModal = "continuous-report";
	overlay.__qwenNode = node;
	const dialog = document.createElement("div"); dialog.className = "qwen-te-modal__dialog"; overlay.appendChild(dialog);
	const header = document.createElement("div"); header.className = "qwen-te-modal__header"; dialog.appendChild(header);
	const titleWrap = document.createElement("div"); header.appendChild(titleWrap);
	const title = document.createElement("div"); title.className = "qwen-te-modal__title"; title.textContent = `连续测试报告 · ${modalContext.nodeName}`; titleWrap.appendChild(title);
	const subtitle = document.createElement("div"); subtitle.className = "qwen-te-modal__subtitle"; subtitle.textContent = `查看最近一次连续测试的事件记录，并可复制、导出或存入历史。当前输出来源：${modalContext.outputSource}。`; titleWrap.appendChild(subtitle);
	const closeButton = document.createElement("button"); closeButton.className = "qwen-te-modal__footer-button"; closeButton.textContent = "关闭"; header.appendChild(closeButton);
	const body = document.createElement("div"); body.className = "qwen-te-modal__body"; dialog.appendChild(body);
	const toolbar = document.createElement("div"); toolbar.className = "qwen-te-modal__toolbar"; body.appendChild(toolbar);
	const statusEl = document.createElement("div"); statusEl.className = "qwen-te-modal__status"; statusEl.textContent = `可复制、导出或存入历史。当前已选标签 ${modalContext.tagCount} 个。`; body.appendChild(statusEl);
	const copyButton = document.createElement("button"); copyButton.className = "qwen-te-modal__footer-button"; copyButton.textContent = "复制报告"; toolbar.appendChild(copyButton);
	const exportJsonButton = document.createElement("button"); exportJsonButton.className = "qwen-te-modal__footer-button"; exportJsonButton.textContent = "导出 JSON"; toolbar.appendChild(exportJsonButton);
	const exportCsvButton = document.createElement("button"); exportCsvButton.className = "qwen-te-modal__footer-button"; exportCsvButton.textContent = "导出 CSV"; toolbar.appendChild(exportCsvButton);
	const exportMarkdownButton = document.createElement("button"); exportMarkdownButton.className = "qwen-te-modal__footer-button"; exportMarkdownButton.textContent = "导出 Markdown"; toolbar.appendChild(exportMarkdownButton);
	const saveHistoryButton = document.createElement("button"); saveHistoryButton.className = "qwen-te-modal__footer-button"; saveHistoryButton.textContent = "存入历史"; toolbar.appendChild(saveHistoryButton);
	const clearButton = document.createElement("button"); clearButton.className = "qwen-te-modal__footer-button"; clearButton.textContent = "清空报告"; toolbar.appendChild(clearButton);
	const filterBar = document.createElement("div"); filterBar.className = "qwen-te-modal__pillbar"; body.appendChild(filterBar);
	const searchToolbar = document.createElement("div"); searchToolbar.className = "qwen-te-modal__toolbar"; body.appendChild(searchToolbar);
	const searchInput = document.createElement("input"); searchInput.className = "qwen-te-modal__search"; searchInput.placeholder = "搜索级别 / 时间 / 内容"; searchToolbar.appendChild(searchInput);
	const sortSelect = document.createElement("select"); sortSelect.className = "qwen-te-modal__search"; searchToolbar.appendChild(sortSelect);
	const viewBar = document.createElement("div"); viewBar.className = "qwen-te-modal__pillbar"; body.appendChild(viewBar);
	const list = document.createElement("div"); list.className = "qwen-te-preset-list"; body.appendChild(list);
	const footer = document.createElement("div"); footer.className = "qwen-te-modal__footer"; dialog.appendChild(footer);
	const doneButton = document.createElement("button"); doneButton.className = "qwen-te-modal__footer-button"; doneButton.textContent = "完成"; footer.appendChild(doneButton);
		let activeLevelFilter = "all";
		let activeSort = "time_desc";
		let activeView = "events";
		const levelFilterButtons = new Map();
		const viewButtons = new Map();
		const expandedAggregateKeys = new Set();
			const sortOptions = [
				{ key: "time_desc", label: "最新在前" },
				{ key: "time_asc", label: "最早在前" },
				{ key: "preset_name_asc", label: "按预设名" },
				{ key: "preset_completed_desc", label: "按完成数" },
				{ key: "preset_success_rate_desc", label: "按成功率" },
			];
		for (const [key, label] of [["events", "事件"], ["preset", "按预设"]]) {
			const button = document.createElement("button");
			button.className = "qwen-te-modal__preset";
			button.textContent = label;
			button.onclick = () => {
				activeView = key;
				render();
			};
			viewBar.appendChild(button);
			viewButtons.set(key, button);
		}
		for (const option of sortOptions) {
			const selectOption = document.createElement("option");
			selectOption.value = option.key;
			selectOption.textContent = option.label;
			sortSelect.appendChild(selectOption);
		}
		sortSelect.value = activeSort;
			const getLevelFilteredReport = () => {
				const report = getNodeContinuousRunReport(node);
				return activeLevelFilter === "all"
					? report
					: report.filter((entry) => String(entry.level ?? "") === activeLevelFilter);
			};
			const getFilteredReport = () => {
				const keyword = String(searchInput.value ?? "").trim().toLowerCase();
				const levelFiltered = getLevelFilteredReport();
				const searched = !keyword ? levelFiltered : levelFiltered.filter((entry) => {
					const timeText = formatPresetTime(entry.at);
					const haystack = `${entry.level ?? ""} ${timeText} ${entry.presetName ?? ""} ${entry.message ?? ""}`.toLowerCase();
					return haystack.includes(keyword);
				});
				const timeSort = activeSort === "time_asc" ? "time_asc" : "time_desc";
				searched.sort((left, right) => timeSort === "time_asc" ? Number(left.at ?? 0) - Number(right.at ?? 0) : Number(right.at ?? 0) - Number(left.at ?? 0));
				return searched;
			};
			const getFilteredAggregate = () => {
				const keyword = String(searchInput.value ?? "").trim().toLowerCase();
				const aggregate = buildContinuousRunAggregate(getLevelFilteredReport());
				const searched = !keyword ? aggregate : aggregate.filter((item) => {
					const trend = classifyContinuousRunAggregateTrend(item);
					const state = classifyContinuousRunAggregate(item);
					const risk = classifyContinuousRunOutcomeRisk(item);
					const haystack = `${item.presetName} ${item.lastMessage} ${formatContinuousRunSuccessRate(item)} ${item.outcomeTrail ?? ""} ${trend.arrow} ${trend.label} ${risk.label} ${state.label} ${item.submitted} ${item.queued} ${item.completed} ${item.failed} ${item.timeout}`.toLowerCase();
					return haystack.includes(keyword);
				});
				if (activeSort === "preset_name_asc") {
					searched.sort((left, right) => left.presetName.localeCompare(right.presetName, "zh-CN"));
				} else if (activeSort === "preset_success_rate_desc") {
					searched.sort((left, right) => {
						const rightRate = Number.isFinite(Number(right.successRate)) ? Number(right.successRate) : -1;
						const leftRate = Number.isFinite(Number(left.successRate)) ? Number(left.successRate) : -1;
						return rightRate - leftRate || right.terminal - left.terminal || right.completed - left.completed || right.lastAt - left.lastAt;
					});
				} else if (activeSort === "preset_completed_desc") {
					searched.sort((left, right) => right.completed - left.completed || right.queued - left.queued || right.lastAt - left.lastAt);
				} else if (activeSort === "time_asc") {
					searched.sort((left, right) => left.lastAt - right.lastAt);
				} else {
					searched.sort((left, right) => right.lastAt - left.lastAt);
				}
				return searched;
			};
		const renderFilterButtons = () => {
		const report = getNodeContinuousRunReport(node);
		const counts = new Map();
		for (const entry of report) counts.set(String(entry.level ?? "记录"), (counts.get(String(entry.level ?? "记录")) ?? 0) + 1);
		const levels = ["all", ...counts.keys()];
		filterBar.replaceChildren();
		levelFilterButtons.clear();
		for (const key of levels) {
			const button = document.createElement("button");
			button.className = "qwen-te-modal__preset";
			const count = key === "all" ? report.length : (counts.get(key) ?? 0);
			const label = key === "all" ? "全部" : key;
			button.textContent = `${label} (${count})`;
			const active = key === activeLevelFilter;
			button.style.borderColor = active ? "#caa55b" : "#525252";
			button.style.background = active ? "#59451a" : "#232323";
			button.style.color = active ? "#fff0ca" : "#f7f7f7";
			button.onclick = () => {
				activeLevelFilter = key;
				render();
			};
			filterBar.appendChild(button);
			levelFilterButtons.set(key, button);
		}
			if (!levels.includes(activeLevelFilter)) activeLevelFilter = "all";
		};
		const renderViewButtons = () => {
			for (const [key, button] of viewButtons.entries()) {
				const active = key === activeView;
				button.style.borderColor = active ? "#caa55b" : "#525252";
				button.style.background = active ? "#59451a" : "#232323";
				button.style.color = active ? "#fff0ca" : "#f7f7f7";
			}
		};
			const render = () => {
				const report = getNodeContinuousRunReport(node);
				const filteredReport = getFilteredReport();
				const filteredAggregate = getFilteredAggregate();
				renderFilterButtons();
				renderViewButtons();
				list.replaceChildren();
				const hasReport = activeView === "events" ? filteredReport.length > 0 : filteredAggregate.length > 0;
			for (const button of [copyButton, exportJsonButton, exportCsvButton, exportMarkdownButton, saveHistoryButton, clearButton]) {
				button.disabled = !hasReport;
				button.style.opacity = hasReport ? "1" : "0.55";
		}
			if (!hasReport) {
				const empty = document.createElement("div");
				empty.className = "qwen-te-preset-card__summary";
				const keyword = String(searchInput.value ?? "").trim();
				empty.textContent = keyword
					? "当前筛选与搜索下没有匹配的连续测试事件。"
					: activeLevelFilter === "all"
						? "当前还没有连续测试报告。"
						: `当前筛选下没有“${activeLevelFilter}”级别事件。`;
				list.appendChild(empty);
				return;
			}
				if (activeView === "events") {
					for (const entry of filteredReport.slice(0, 30)) {
					const card = document.createElement("div");
					card.className = "qwen-te-preset-card";
					list.appendChild(card);
					const head = document.createElement("div");
					head.className = "qwen-te-preset-card__header";
					card.appendChild(head);
					const level = document.createElement("div");
					level.className = "qwen-te-preset-card__name";
					level.textContent = entry.level;
					head.appendChild(level);
					const time = document.createElement("div");
					time.className = "qwen-te-preset-card__time";
					time.textContent = formatPresetTime(entry.at);
					head.appendChild(time);
					const summary = document.createElement("div");
					summary.className = "qwen-te-preset-card__summary";
					summary.textContent = entry.message;
					card.appendChild(summary);
				}
				} else {
					const legend = document.createElement("div");
					legend.className = "qwen-te-preset-card__summary";
					legend.textContent = "阈值说明：成功率 >= 85% 视为稳定，50%-84% 视为观察，低于 50% 建议回查；终态 = 完成 + 失败 + 超时；结果串为新 -> 旧，✓ 完成、✕ 失败、⏱ 超时；最近连续 ✕ / ⏱ 会触发风险提醒。";
					list.appendChild(legend);
					for (const item of filteredAggregate) {
						const aggregateState = classifyContinuousRunAggregate(item);
						const trendState = classifyContinuousRunAggregateTrend(item);
						const riskState = classifyContinuousRunOutcomeRisk(item);
						const cardTone = mergeContinuousRunTones(aggregateState.tone, trendState.tone, riskState.tone);
						const card = document.createElement("div");
						const expanded = expandedAggregateKeys.has(item.presetName);
						card.className = `qwen-te-preset-card qwen-te-preset-card--${cardTone} qwen-te-preset-card--clickable${expanded ? " qwen-te-preset-card--expanded" : ""}`;
						list.appendChild(card);
						card.onclick = () => {
							if (expandedAggregateKeys.has(item.presetName)) expandedAggregateKeys.delete(item.presetName);
							else expandedAggregateKeys.add(item.presetName);
							render();
						};
						const head = document.createElement("div");
						head.className = "qwen-te-preset-card__header";
						card.appendChild(head);
						const name = document.createElement("div");
					name.className = "qwen-te-preset-card__name";
					name.textContent = item.presetName;
					head.appendChild(name);
						const time = document.createElement("div");
						time.className = "qwen-te-preset-card__time";
						time.textContent = formatPresetTime(item.lastAt);
						head.appendChild(time);
						const badgeBar = document.createElement("div");
						badgeBar.className = "qwen-te-preset-card__badges";
						card.appendChild(badgeBar);
						const toneBadge = document.createElement("div");
						toneBadge.className = `qwen-te-preset-card__badge qwen-te-preset-card__badge--${aggregateState.tone}`;
						toneBadge.textContent = aggregateState.label;
						badgeBar.appendChild(toneBadge);
						const successRateBadge = document.createElement("div");
						successRateBadge.className = `qwen-te-preset-card__badge qwen-te-preset-card__badge--${aggregateState.tone === "danger" ? "danger" : aggregateState.tone === "warn" ? "warn" : aggregateState.tone === "success" ? "success" : "info"}`;
						successRateBadge.textContent = `成功率 ${formatContinuousRunSuccessRate(item)}`;
						badgeBar.appendChild(successRateBadge);
						const trendBadge = document.createElement("div");
						trendBadge.className = `qwen-te-preset-card__badge qwen-te-preset-card__badge--${trendState.tone}`;
						trendBadge.textContent = `趋势 ${trendState.arrow} ${trendState.label}`;
						badgeBar.appendChild(trendBadge);
						const trailBadge = document.createElement("div");
						trailBadge.className = "qwen-te-preset-card__badge qwen-te-preset-card__badge--info";
						trailBadge.textContent = `结果 ${item.outcomeTrail}`;
						badgeBar.appendChild(trailBadge);
						if (riskState.streak > 0) {
							const riskBadge = document.createElement("div");
							riskBadge.className = `qwen-te-preset-card__badge qwen-te-preset-card__badge--${riskState.tone}`;
							riskBadge.textContent = `风险 ${riskState.label}`;
							badgeBar.appendChild(riskBadge);
						}
							for (const [label, value, tone] of [
								["完成", item.completed, "success"],
								["失败", item.failed, item.failed > 0 ? "danger" : "info"],
								["超时", item.timeout, item.timeout > 0 ? "warn" : "info"],
							]) {
							const badge = document.createElement("div");
							badge.className = `qwen-te-preset-card__badge qwen-te-preset-card__badge--${tone}`;
								badge.textContent = `${label} ${value}`;
								badgeBar.appendChild(badge);
							}
							if ((item.manual ?? 0) > 0) {
								const manualBadge = document.createElement("div");
								manualBadge.className = "qwen-te-preset-card__badge qwen-te-preset-card__badge--info";
								manualBadge.textContent = `手动 ${item.manual}`;
								badgeBar.appendChild(manualBadge);
						}
						const summary = document.createElement("div");
						summary.className = "qwen-te-preset-card__summary";
						summary.textContent = `成功率 ${formatContinuousRunSuccessRate(item)} | 趋势 ${trendState.arrow} ${trendState.label} | 风险 ${riskState.label} | 终态 ${item.terminal}\n最近结果（新→旧） ${item.outcomeTrail}\n提交 ${item.submitted} | 入队 ${item.queued} | 完成 ${item.completed} | 失败 ${item.failed} | 超时 ${item.timeout}\n最近：${item.lastMessage}`;
						card.appendChild(summary);
						if (expanded) {
							const detailWrap = document.createElement("div");
							detailWrap.className = "qwen-te-preset-card__detail";
							card.appendChild(detailWrap);
								if (Array.isArray(item.recentRoundSummaries) && item.recentRoundSummaries.length) {
									const chainTitle = document.createElement("div");
									chainTitle.className = "qwen-te-preset-card__detail-item";
									chainTitle.innerHTML = "<strong>最近轮次链路</strong>";
									detailWrap.appendChild(chainTitle);
									for (const roundSummary of item.recentRoundSummaries) {
										const chainRow = document.createElement("div");
										chainRow.className = `qwen-te-preset-card__detail-item qwen-te-preset-card__detail-item--${roundSummary.tone}`;
										const chainStrong = document.createElement("strong");
										chainStrong.textContent = `${roundSummary.terminalSymbol} ${roundSummary.roundLabel} | ${roundSummary.terminalLevel}`;
										chainRow.appendChild(chainStrong);
										chainRow.appendChild(document.createTextNode(` [${formatPresetTime(roundSummary.latestAt)}]\n${roundSummary.chain}\n${roundSummary.terminalMessage}`));
										detailWrap.appendChild(chainRow);
									}
								}
								if (Array.isArray(item.recentRounds) && item.recentRounds.length) {
									const recentTitle = document.createElement("div");
									recentTitle.className = "qwen-te-preset-card__detail-item";
									recentTitle.innerHTML = "<strong>最近轮次终态</strong>";
									detailWrap.appendChild(recentTitle);
									for (const roundItem of item.recentRounds) {
										const recentRow = document.createElement("div");
										recentRow.className = `qwen-te-preset-card__detail-item qwen-te-preset-card__detail-item--${roundItem.tone}`;
										const recentStrong = document.createElement("strong");
										recentStrong.textContent = `${roundItem.symbol} ${roundItem.roundLabel} | ${roundItem.level}${roundItem.origin === "manual" ? " | 手动" : ""}`;
										recentRow.appendChild(recentStrong);
										recentRow.appendChild(document.createTextNode(` [${formatPresetTime(roundItem.at)}]\n${roundItem.message}`));
										detailWrap.appendChild(recentRow);
									}
								}
								const actionBar = document.createElement("div");
								actionBar.className = "qwen-te-modal__content-tools";
								detailWrap.appendChild(actionBar);
								const targetPreset = getUserPresets().find((preset) => String(preset.name ?? "").trim() === item.presetName);
								if (targetPreset) {
									const refreshReportIfOpen = () => {
										if (overlay.isConnected) render();
									};
										const appendManualReport = (level, message) => {
											pushNodeContinuousRunReport(node, library, level, message, { presetName: targetPreset.name, origin: "manual" });
											refreshReportIfOpen();
										};
									const makeAction = (label, handler) => {
										const button = document.createElement("button");
										button.type = "button";
										button.className = "qwen-te-modal__mini-button";
										button.textContent = label;
									button.onclick = async (event) => {
										event.stopPropagation();
										await handler();
										};
										actionBar.appendChild(button);
									};
									makeAction("复制单预设", async () => {
										const text = buildSinglePresetContinuousRunReportText(item);
										if (!text) {
											statusEl.textContent = `当前没有可复制的单预设报告：${targetPreset.name}`;
											return;
										}
										const ok = await copyToClipboard(text);
										statusEl.textContent = ok ? `已复制单预设报告：${targetPreset.name}` : `复制单预设报告失败：${targetPreset.name}`;
									});
									makeAction("导出单预设", async () => {
										const payload = buildSinglePresetContinuousRunReportPayload(item);
										if (!payload) {
											statusEl.textContent = `当前没有可导出的单预设报告：${targetPreset.name}`;
											return;
										}
										const text = JSON.stringify(payload, null, 2);
										const ok = exportTextFile(text, `qwen-te-single-preset-${buildCompactTimestamp()}-${targetPreset.name.replace(/[\\\\/:*?\"<>|\\s]+/g, "-")}.json`, "application/json");
										statusEl.textContent = ok ? `已导出单预设报告：${targetPreset.name}` : `导出单预设报告失败：${targetPreset.name}`;
									});
									makeAction("报告入历史", async () => {
										const payload = buildSinglePresetContinuousRunReportPayload(item);
										if (!payload) {
											statusEl.textContent = `当前没有可存入历史的单预设报告：${targetPreset.name}`;
											return;
										}
										recordNodeHistory(node, targetPreset.state, "single-preset-report", {
											summary: buildSinglePresetReportHistorySummary(item),
											meta: {
												reportPresetId: String(targetPreset.id ?? ""),
												reportPayload: {
													...payload,
													presetId: String(targetPreset.id ?? ""),
												},
											},
										});
										statusEl.textContent = `已将单预设报告存入历史：${targetPreset.name}`;
									});
									makeAction("存入历史", async () => {
										recordNodeHistory(node, targetPreset.state, "single-preset", {
											summary: buildSinglePresetHistorySummary(item),
										});
										statusEl.textContent = `已将单预设快照存入历史：${targetPreset.name}`;
									});
									makeAction("存为快照", async () => {
										const snapshotName = buildSinglePresetSnapshotName(item);
										const ok = saveUserPreset(snapshotName, targetPreset.state, {
											source: "single-preset",
											meta: {
												presetName: targetPreset.name,
												successRate: formatContinuousRunSuccessRate(item),
												outcomeTrail: item.outcomeTrail,
												risk: classifyContinuousRunOutcomeRisk(item).label,
											},
										});
										statusEl.textContent = ok ? `已保存单预设快照：${snapshotName}` : `保存单预设快照失败：${targetPreset.name}`;
									});
									makeAction("加入连测", async () => {
										const result = addPresetToNodeBatchState(node, targetPreset.id);
										refreshNodeSummary(node, library);
										statusEl.textContent = result.changed
											? `已加入当前连测批次：${targetPreset.name}（共 ${result.count} 个）`
											: `该预设已在当前连测批次中：${targetPreset.name}`;
									});
									makeAction("设为唯一批次", async () => {
										const result = setExclusivePresetBatchState(node, targetPreset.id);
										refreshNodeSummary(node, library);
										statusEl.textContent = result.changed
											? `已将当前连测批次切为唯一预设：${targetPreset.name}`
											: `当前连测批次已是唯一预设：${targetPreset.name}`;
									});
									makeAction("唯一并开跑", async () => {
										setExclusivePresetBatchState(node, targetPreset.id);
										refreshNodeSummary(node, library);
										await startNodeContinuousPresetRun(node, library, "cycle");
										statusEl.textContent = `已将 ${targetPreset.name} 设为唯一连测批次并启动轮流连测。`;
									});
									makeAction("载入预设", async () => {
										await applyPresetToNode(targetPreset);
										appendManualReport("手动载入", `从聚合统计载入预设：${targetPreset.name}`);
										statusEl.textContent = `已从聚合统计载入预设：${targetPreset.name}`;
									});
								makeAction("重跑并入队", async () => {
									const baselineStamp = getNodeExecutionStamp(node);
									appendManualReport("提交", `手动重跑：${targetPreset.name}`);
										const queued = await applyPresetToNode(targetPreset, { queue: true });
										if (!queued) {
											appendManualReport("失败", `手动重跑：${targetPreset.name} 已载入，但未能自动入队。`);
											statusEl.textContent = `已从聚合统计载入预设：${targetPreset.name}，但未能自动入队`;
											return;
										}
										appendManualReport("入队", `手动重跑：${targetPreset.name} 已入队。`);
										statusEl.textContent = `已从聚合统计重跑并入队：${targetPreset.name}`;
										const executed = await waitForNodeExecution(node, baselineStamp, 180000, 500, {
											shouldCancel: () => !overlay.isConnected,
										});
										appendManualReport(executed ? "完成" : "超时", executed ? `手动重跑：${targetPreset.name} 执行完成。` : `手动重跑：${targetPreset.name} 等待执行完成超时。`);
									});
								makeAction("随机跑", async () => {
										const baselineStamp = getNodeExecutionStamp(node);
										appendManualReport("提交", `手动随机跑：${targetPreset.name}`);
										const queued = await applyPresetToNode(targetPreset, { randomizeAfterLoad: true, queue: true });
										if (!queued) {
											appendManualReport("失败", `手动随机跑：${targetPreset.name} 已随机化，但未能自动入队。`);
											statusEl.textContent = `已从聚合统计随机化预设：${targetPreset.name}，但未能自动入队`;
											return;
										}
										appendManualReport("入队", `手动随机跑：${targetPreset.name} 已入队。`);
										statusEl.textContent = `已从聚合统计随机跑：${targetPreset.name}`;
										const executed = await waitForNodeExecution(node, baselineStamp, 180000, 500, {
											shouldCancel: () => !overlay.isConnected,
										});
										appendManualReport(executed ? "完成" : "超时", executed ? `手动随机跑：${targetPreset.name} 执行完成。` : `手动随机跑：${targetPreset.name} 等待执行完成超时。`);
									});
								makeAction("连测轮流", async () => {
									await startSinglePresetContinuousRun(node, library, targetPreset, "cycle");
									statusEl.textContent = `已从聚合统计启动单预设轮流连测：${targetPreset.name}`;
								});
								makeAction("连测随机", async () => {
									await startSinglePresetContinuousRun(node, library, targetPreset, "random");
									statusEl.textContent = `已从聚合统计启动单预设随机连测：${targetPreset.name}`;
								});
							}
							for (const entry of item.entries.slice(0, 12)) {
								const detail = document.createElement("div");
								detail.className = "qwen-te-preset-card__detail-item";
								const roundText = entry.round && entry.total ? `第 ${entry.round}/${entry.total} 轮` : "通用事件";
								const strong = document.createElement("strong");
								strong.textContent = `[${formatPresetTime(entry.at)}] ${entry.level}${entry.origin === "manual" ? " | 手动" : ""}`;
								detail.appendChild(strong);
								detail.appendChild(document.createTextNode(` ${roundText}\n${entry.message}`));
								detailWrap.appendChild(detail);
							}
							if ((item.entries?.length ?? 0) > 12) {
								const more = document.createElement("div");
								more.className = "qwen-te-preset-card__detail-item";
								more.textContent = `还有 ${(item.entries?.length ?? 0) - 12} 条事件未展开显示。`;
								detailWrap.appendChild(more);
							}
						}
					}
				}
				const visibleCount = activeView === "events" ? filteredReport.length : filteredAggregate.length;
				const sortLabel = sortOptions.find((item) => item.key === activeSort)?.label ?? activeSort;
				statusEl.textContent = `已记录 ${report.length} 条连续测试事件，当前显示 ${visibleCount} 条，视图：${activeView === "events" ? "事件" : "按预设"}，排序：${sortLabel}。`;
			};
			copyButton.onclick = () => {
				const filtered = getFilteredReport();
				const text = activeView === "events" ? buildNodeContinuousRunReportText(node, filtered) : buildContinuousRunAggregateText(getFilteredAggregate());
			if (!text) {
				statusEl.textContent = "当前没有可复制的连续测试报告。";
				return;
			}
			void copyToClipboard(text).then((ok) => {
				statusEl.textContent = ok ? "已复制连续测试报告。" : "复制失败，浏览器可能阻止了剪贴板访问。";
			});
		};
			exportJsonButton.onclick = () => {
				if (activeView === "preset") {
					const text = JSON.stringify({ version: 1, exportedAt: Date.now(), source: "qwen-te-continuous-run-aggregate", aggregate: getFilteredAggregate() }, null, 2);
					if (!exportTextFile(text, `qwen-te-continuous-aggregate-${buildCompactTimestamp()}.json`, "application/json")) {
						statusEl.textContent = "当前没有可导出的 JSON 报告。";
						return;
					}
					statusEl.textContent = "已导出 JSON 连续测试聚合报告。";
					return;
				}
				if (!exportNodeContinuousRunReport(node, "json", getFilteredReport())) {
					statusEl.textContent = "当前没有可导出的 JSON 报告。";
					return;
				}
				statusEl.textContent = "已导出 JSON 连续测试报告。";
			};
			exportCsvButton.onclick = () => {
				const filtered = getFilteredReport();
				if (activeView === "preset") {
					const text = buildContinuousRunAggregateCsv(getFilteredAggregate());
					if (!exportTextFile(text, `qwen-te-continuous-aggregate-${buildCompactTimestamp()}.csv`, "text/csv;charset=utf-8")) {
						statusEl.textContent = "当前没有可导出的 CSV 报告。";
						return;
					}
					statusEl.textContent = "已导出 CSV 连续测试聚合报告。";
					return;
				}
				if (!exportNodeContinuousRunReport(node, "csv", filtered)) {
					statusEl.textContent = "当前没有可导出的 CSV 报告。";
					return;
				}
				statusEl.textContent = "已导出 CSV 连续测试报告。";
			};
			exportMarkdownButton.onclick = () => {
				const filtered = getFilteredReport();
				if (activeView === "preset") {
					const text = buildContinuousRunAggregateMarkdown(getFilteredAggregate());
					if (!exportTextFile(text, `qwen-te-continuous-aggregate-${buildCompactTimestamp()}.md`, "text/markdown;charset=utf-8")) {
						statusEl.textContent = "当前没有可导出的 Markdown 报告。";
						return;
					}
					statusEl.textContent = "已导出 Markdown 连续测试聚合报告。";
					return;
				}
				if (!exportNodeContinuousRunReport(node, "markdown", filtered)) {
					statusEl.textContent = "当前没有可导出的 Markdown 报告。";
					return;
				}
				statusEl.textContent = "已导出 Markdown 连续测试报告。";
			};
	saveHistoryButton.onclick = () => {
		const report = getFilteredReport();
		if (!report.length) {
			statusEl.textContent = "当前没有可存入历史的连续测试报告。";
			return;
		}
		recordNodeHistory(node, collectNodeState(node, library), "continuous-report", { dedupe: true, summary: buildNodeContinuousRunHistorySummary(node, report), meta: { qualityAudit: buildQualityAuditHistoryMeta(node) } });
		statusEl.textContent = "已将连续测试报告存入历史。";
	};
		clearButton.onclick = () => {
			clearNodeContinuousRunArtifacts(node, library);
			statusEl.textContent = "已清空连续测试报告。";
			render();
		};
		searchInput.addEventListener("input", render);
		sortSelect.addEventListener("change", () => {
			activeSort = String(sortSelect.value ?? "time_desc");
			render();
		});
		const reportPollTimer = setInterval(() => {
			if (!overlay.isConnected) {
				clearInterval(reportPollTimer);
				return;
			}
			render();
		}, 1000);
		overlay.__qwenDispose = () => clearInterval(reportPollTimer);
		const close = () => disposeModalOverlay(overlay);
		doneButton.onclick = close;
		closeButton.onclick = close;
		overlay.addEventListener("click", (event) => { if (event.target === overlay) close(); });
		document.body.appendChild(overlay);
		render();
		searchInput.focus();
	}
function getStagePromptOutputText(node){ return getStageOutputText(node, STAGE_OUTPUT_INDEX.promptText); }
async function copyToClipboard(text){ if(!text) return false; try{ await navigator.clipboard.writeText(text); return true; } catch { try{ const t=document.createElement("textarea"); t.value=text; document.body.appendChild(t); t.select(); document.execCommand("copy"); document.body.removeChild(t); return true; } catch { return false; } } }
function recordStageExecution(node, library, statusEl, stageOutputOverride = null){
	const stageOutput = normalizeHistoryStageOutputPayload(stageOutputOverride) ?? getStageHistoryOutputSnapshot(node);
	const promptText = String(stageOutput?.promptText ?? stageOutput?.promptCollection ?? stageOutput?.smartText ?? "").trim();
	if(!promptText) return false;
	const signature=JSON.stringify([promptText, stageOutput.negativePrompt, stageOutput.smartText, stageOutput.jsonResult?.slice?.(0, 240) ?? ""]);
	const panelState=node?.[PANEL_KEY];
	if(panelState){
		if(panelState.stageOutputRecordSignature===signature) return false;
		panelState.stageOutputRecordSignature=signature;
		panelState.lastExecutionOutputs = buildStageOutputListFromSnapshot(stageOutput);
	}
	const currentState=collectNodeState(node, library);
	const historyStageOutput=compactHistoryStageOutputPayload(stageOutput);
	if(!historyStageOutput?.promptText) return false;
	const compact=promptText.replace(/\s+/g," ").trim();
	const suffix=compact?` | ${compact.slice(0,120)}${compact.length>120?"...":""}`:"";
	recordNodeHistory(node,currentState,"executed",{force:true,summary:`${summarizeHistoryState(currentState)}${suffix}`,meta:{qualityAudit:buildQualityAuditHistoryMeta(node),stageOutput:historyStageOutput}});
	attachStageOutputToRecentStateHistory(node,currentState,historyStageOutput);
	refreshStageDisplay(node);
	if(statusEl) statusEl.textContent="已记录本次运行结果到历史。";
	return true;
}

function extractStageExecutionHistoryFromArgs(argsLike) {
	for (const arg of Array.from(argsLike ?? [])) {
		const candidates = [arg, arg?.output, arg?.outputs, arg?.ui, arg?.result];
		for (const candidate of candidates) {
			if (Array.isArray(candidate?.qwen_te_stage_output_history)) {
				return candidate.qwen_te_stage_output_history;
			}
		}
	}
	return [];
}

function captureStageExecutionHistoryFromArgs(node, library, argsLike) {
	if (!captureStageExecutionOutputsFromArgs(node, argsLike)) return false;
	refreshStageDisplay(node);
	const recorded = recordStageExecution(node, node?.[PANEL_KEY]?.library ?? library, null);
	if (recorded && node?.[PANEL_KEY]) {
		node[PANEL_KEY].stageOutputEventRecordCount = Math.max(0, Number(node[PANEL_KEY].stageOutputEventRecordCount ?? 0) || 0) + 1;
	}
	const executionHistory = extractStageExecutionHistoryFromArgs(argsLike);
	const recoveredCount = executionHistory.length
		? recordMissingStageExecutionHistoryFromCache(
			node,
			node?.[PANEL_KEY]?.library ?? library,
			{
				...normalizeHistoryStageOutputPayload(node?.[PANEL_KEY]?.lastExecutionOutputs),
				execution_history: executionHistory,
			},
			{ executionStartedAt: Number(node?.[PANEL_KEY]?.lastWorkflowQueueRequestedAt ?? 0) || 0 },
		)
		: 0;
	return recorded || recoveredCount > 0;
}

function getStageExecutionCacheEntryId(entry) {
	const explicit = String(entry?.execution_id ?? "").trim();
	if (explicit) return explicit;
	const prompt = String(entry?.prompt_text ?? entry?.promptText ?? "").trim();
	return JSON.stringify([normalizeStageTimestampMs(entry?.updated_at), prompt.length, prompt.slice(0, 240)]);
}

function recordMissingStageExecutionHistoryFromCache(node, library, directOutput, options = {}) {
	const panelState = node?.[PANEL_KEY];
	if (!panelState || !Array.isArray(directOutput?.execution_history)) return 0;
	const executionStartedAt = Number(options.executionStartedAt ?? 0) || 0;
	const queueRequestedAt = Number(panelState.lastWorkflowQueueRequestedAt ?? 0) || 0;
	const freshnessBaseline = queueRequestedAt > 0 ? queueRequestedAt : executionStartedAt;
	const candidates = directOutput.execution_history
		.filter((entry) => {
			if (!hasUsableStageOutputSnapshot(normalizeHistoryStageOutputPayload(entry))) return false;
			const updatedAt = normalizeStageTimestampMs(entry?.updated_at);
			return freshnessBaseline <= 0 || updatedAt <= 0 || updatedAt + getStageOutputTimestampToleranceMs(entry?.updated_at) >= freshnessBaseline;
		})
		.sort((left, right) => normalizeStageTimestampMs(right?.updated_at) - normalizeStageTimestampMs(left?.updated_at));
	if (!candidates.length) return 0;
	const eventRecordCount = Math.max(0, Math.trunc(Number(
		options.recordedEventCount ?? panelState.stageOutputEventRecordCount ?? 0,
	)) || 0);
	const processed = new Set(Array.isArray(panelState.stageOutputCacheProcessedIds) ? panelState.stageOutputCacheProcessedIds : []);
	let recordedCount = 0;
	for (const entry of candidates.slice(Math.min(eventRecordCount, candidates.length)).reverse()) {
		const executionId = getStageExecutionCacheEntryId(entry);
		if (processed.has(executionId)) continue;
		panelState.stageOutputRecordSignature = "";
		if (recordStageExecution(node, panelState.library ?? library, null, entry)) recordedCount += 1;
		processed.add(executionId);
	}
	panelState.stageOutputCacheProcessedIds = [...processed].slice(-64);
	const latestOutput = normalizeHistoryStageOutputPayload(directOutput);
	if (hasUsableStageOutputSnapshot(latestOutput)) {
		panelState.lastExecutionOutputs = buildStageOutputListFromSnapshot(latestOutput);
		refreshStageDisplay(node);
	}
	return recordedCount;
}

function getHistoryEntryNodeCacheNamespace(entry, node) {
	const nodeId = String(node?.id ?? "");
	const workflowNodes = getHistoryEntryPromptTuple(entry)?.[3]?.extra_pnginfo?.workflow?.nodes;
	if (!nodeId || !Array.isArray(workflowNodes)) return "";
	const workflowNode = workflowNodes.find((item) => String(item?.id ?? "") === nodeId);
	return String(workflowNode?.properties?.[NODE_CACHE_NAMESPACE_KEY] ?? "").trim();
}

async function reconcileStageExecutionHistoryFromWorkflowHistory(node, library, options = {}) {
	const panelState = node?.[PANEL_KEY];
	if (!panelState) return 0;
	const isCurrent = typeof options.shouldCommit === "function"
		? options.shouldCommit
		: () => !node?.[NODE_REMOVED_KEY] && node?.[PANEL_KEY] === panelState;
	const queuedAt = Number(panelState.lastWorkflowQueueRequestedAt ?? 0) || 0;
	const history = await requestWorkflowHistory(120, {
		owner: node,
		key: "stage-output-history-open-workflow",
		timeoutMs: 8000,
	});
	if (!isCurrent()) return 0;
	let candidates = Object.entries(history ?? {})
		.map(([promptId, entry]) => ({
			promptId: String(promptId ?? "").trim(),
			entry,
			createdAt: getHistoryEntryCreateTime(entry),
			cacheNamespace: getHistoryEntryNodeCacheNamespace(entry, node),
			outputs: extractStageOutputsFromHistoryEntry(entry, node),
		}))
		.filter((item) => item.promptId
			&& historyEntryContainsNode(item.entry, node)
			&& item.outputs.some((value) => String(value ?? "").trim())
			&& (queuedAt <= 0 || item.createdAt <= 0 || item.createdAt + 2000 >= queuedAt))
		.sort((left, right) => left.createdAt - right.createdAt);
	if (!candidates.length) return 0;
	const currentNamespace = String(node?.properties?.[NODE_CACHE_NAMESPACE_KEY] ?? "").trim();
	const currentNamespaceCandidates = currentNamespace
		? candidates.filter((item) => item.cacheNamespace === currentNamespace)
		: [];
	if (currentNamespaceCandidates.length) {
		candidates = currentNamespaceCandidates;
	} else {
		const latestNamespace = candidates[candidates.length - 1]?.cacheNamespace ?? "";
		if (latestNamespace) candidates = candidates.filter((item) => item.cacheNamespace === latestNamespace);
	}
	const processed = new Set(Array.isArray(panelState.stageOutputWorkflowProcessedIds)
		? panelState.stageOutputWorkflowProcessedIds
		: []);
	if (!processed.size) {
		const recordedExecutionCount = getNodeHistory(node).filter((item) => item?.source === "executed").length;
		for (const item of candidates.slice(-Math.min(recordedExecutionCount, candidates.length))) {
			processed.add(item.promptId);
		}
	}
	let recordedCount = 0;
	for (const item of candidates) {
		if (processed.has(item.promptId)) continue;
		panelState.stageOutputRecordSignature = "";
		if (recordStageExecution(node, panelState.library ?? library, null, item.outputs)) recordedCount += 1;
		processed.add(item.promptId);
	}
	panelState.stageOutputWorkflowProcessedIds = [...processed].slice(-120);
	const latestOutputs = candidates[candidates.length - 1]?.outputs;
	if (Array.isArray(latestOutputs) && latestOutputs.length) {
		panelState.lastExecutionOutputs = latestOutputs;
		refreshStageDisplay(node);
	}
	return recordedCount;
}

async function reconcileStageExecutionHistoryBeforeOpen(node, library) {
	const panelState = node?.[PANEL_KEY];
	if (!panelState) return 0;
	const isCurrent = () => !node?.[NODE_REMOVED_KEY]
		&& node?.[PANEL_KEY] === panelState
		&& (app.graph?._nodes ?? []).includes(node);
	let recordedCount = 0;
	try {
		const directOutput = await syncNodeStageOutputCache(node, {
			shouldCommit: isCurrent,
			requestKey: "stage-output-history-open",
			requestTimeoutMs: 5000,
		});
		if (!isCurrent()) return 0;
		if (directOutput) {
			const executionHistory = Array.isArray(directOutput.execution_history) ? directOutput.execution_history : [];
			const persistedExecutionCount = getNodeHistory(node).filter((item) => item?.source === "executed").length;
			recordedCount += recordMissingStageExecutionHistoryFromCache(
				node,
				panelState.library ?? library,
				directOutput,
				{
					executionStartedAt: Number(panelState.lastWorkflowQueueRequestedAt ?? 0) || 0,
					recordedEventCount: Math.min(persistedExecutionCount, executionHistory.length),
				},
			);
		}
	} catch (_error) {}
	if (!isCurrent()) return recordedCount;
	try {
		recordedCount += await reconcileStageExecutionHistoryFromWorkflowHistory(
			node,
			panelState.library ?? library,
			{ shouldCommit: isCurrent },
		);
	} catch (_error) {}
	return recordedCount;
}

async function tryCaptureFinalStageOutput(node, library, options = {}) {
	const executionStartedAt = Number(options.executionStartedAt ?? 0) || 0;
	const captureToken = String(options.captureToken ?? "");
	const panelState = node?.[PANEL_KEY];
	const isCaptureCurrent = () => !node?.[NODE_REMOVED_KEY]
		&& node?.[PANEL_KEY] === panelState
		&& (!captureToken || panelState?.stageOutputCaptureToken === captureToken)
		&& (app.graph?._nodes ?? []).includes(node);
	if (!isCaptureCurrent()) return false;
	let directStageOutput = null;
	let directOutput = null;
	try {
		directOutput = await syncNodeStageOutputCache(node, { shouldCommit: isCaptureCurrent });
		if (!isCaptureCurrent()) return false;
		const staleForCurrentRun = !!node?.[PANEL_KEY]?.directStageOutputCache?._qwenStaleForCurrentRun;
		const outputStatus = String(directOutput?.status ?? "").trim().toLowerCase();
		const outputIsFinal = !outputStatus || outputStatus === "done";
		directStageOutput = staleForCurrentRun || !outputIsFinal ? null : normalizeHistoryStageOutputPayload(directOutput);
		if (hasUsableStageOutputSnapshot(directStageOutput) && node?.[PANEL_KEY]) {
			node[PANEL_KEY].lastExecutionOutputs = buildStageOutputListFromSnapshot(directStageOutput);
		}
		if (!getCurrentStageOutputText(node, STAGE_OUTPUT_INDEX.promptText)) {
			await syncNodeWorkflowOutputMetaFromHistory(node, { createdAfter: executionStartedAt, shouldCommit: isCaptureCurrent });
			if (!isCaptureCurrent()) return false;
			hydrateStageDisplayStateFromPersistedData(node);
		}
	} catch (_error) {}
	if (!isCaptureCurrent()) return false;
	syncNodeRandomDedupeCacheFromResult(node, directStageOutput?.jsonPayload ?? null);
	syncNodePromptDedupeCacheFromResult(node, directStageOutput?.jsonPayload ?? null);
	if (!isCaptureCurrent()) return false;
	const recoveredCount = recordMissingStageExecutionHistoryFromCache(
		node,
		node?.[PANEL_KEY]?.library ?? library,
		directOutput,
		{ executionStartedAt },
	);
	const eventRecordCount = Math.max(0, Math.trunc(Number(node?.[PANEL_KEY]?.stageOutputEventRecordCount ?? 0)) || 0);
	const recorded = eventRecordCount > 0 || recoveredCount > 0
		? false
		: recordStageExecution(node, node?.[PANEL_KEY]?.library ?? library, null, directStageOutput);
	refreshStageDisplay(node);
	return recorded || recoveredCount > 0 || (eventRecordCount > 0 && hasUsableStageOutputSnapshot(directStageOutput));
}

function scheduleStageExecutionOutputCapture(node, library, options = {}) {
	const panelState = node?.[PANEL_KEY];
	if (!panelState) return;
	const token = `${Date.now()}_${Math.random().toString(36).slice(2)}`;
	panelState.stageOutputCaptureToken = token;
	const executionStartedAt = Number(options.executionStartedAt ?? Date.now()) || Date.now();
	const maxAttempts = Math.max(3, Math.min(60, Math.trunc(Number(options.attempts ?? 24)) || 24));
	const delayMs = Math.max(250, Math.trunc(Number(options.delayMs ?? 700)) || 700);
	let attempts = 0;
	const isCaptureCurrent = () => !node?.[NODE_REMOVED_KEY]
		&& node?.[PANEL_KEY] === panelState
		&& panelState.stageOutputCaptureToken === token
		&& (app.graph?._nodes ?? []).includes(node);
	const run = async () => {
		if (!isCaptureCurrent()) return;
		attempts += 1;
		const recorded = await tryCaptureFinalStageOutput(node, library, { executionStartedAt, captureToken: token });
		if (!isCaptureCurrent()) return;
		if (recorded) {
			if (attempts >= 2) return;
			setTimeout(run, Math.max(450, delayMs));
			return;
		}
		if (attempts >= maxAttempts) return;
		if (!getCurrentStageOutputText(node, STAGE_OUTPUT_INDEX.promptText)) {
			setTimeout(run, attempts === 1 ? 160 : delayMs);
			return;
		}
		recordStageExecution(node, node?.[PANEL_KEY]?.library ?? library, null);
	};
	setTimeout(run, Math.max(50, Number(options.initialDelayMs ?? 80) || 80));
}

function getEnhancedStagePromptNodes() {
	return (app.graph?._nodes ?? []).filter((node) => isStagePromptNode(node) && node?.[PANEL_KEY]);
}

function prepareStageNodeForQueueCapture(node, requestedAt = Date.now()) {
	const panelState = node?.[PANEL_KEY];
	if (!panelState) return;
	clearStageDisplayPreview(node);
	markNodeWorkflowQueueRequested(node, requestedAt);
	panelState.displayClearedAt = 0;
	panelState.lastExecutionOutputs = [];
	panelState.directStageOutputCache = null;
	panelState.directStageOutputCacheId = "";
	panelState.hydratedExecutionOutputs = [];
	panelState.hydratedExecutionSourceLabel = "";
	panelState.previewExecutionOutputs = [];
	panelState.clearedLinkedOutputSnapshot = [];
	panelState.stageOutputRecordSignature = "";
	panelState.stageOutputEventRecordCount = 0;
	panelState.stageOutputCacheProcessedIds = [];
	refreshStageDisplay(node);
}

function scheduleStageOutputCaptureForAllNodes(options = {}) {
	const executionStartedAt = Number(options.executionStartedAt ?? Date.now()) || Date.now();
	const nodes = getEnhancedStagePromptNodes();
	for (const node of nodes) {
		scheduleStageExecutionOutputCapture(node, node?.[PANEL_KEY]?.library ?? { slot_config: [] }, {
			executionStartedAt,
			initialDelayMs: Number(options.initialDelayMs ?? 300) || 300,
			delayMs: Number(options.delayMs ?? 900) || 900,
			attempts: Number(options.attempts ?? 90) || 90,
		});
	}
}

function installGlobalStagePromptQueueCapture() {
	if (!app || app[GLOBAL_STAGE_QUEUE_CAPTURE_FLAG]) return;
	if (typeof app.queuePrompt !== "function") return;
	const originalQueuePrompt = app.queuePrompt;
	app[GLOBAL_STAGE_QUEUE_CAPTURE_FLAG] = true;
	app.queuePrompt = async function () {
		const requestedAt = Date.now();
		const nodes = getEnhancedStagePromptNodes();
		for (const node of nodes) prepareStageNodeForQueueCapture(node, requestedAt);
		try {
			const result = await originalQueuePrompt.apply(this, arguments);
			return result;
		} catch (error) {
			for (const node of nodes) {
				clearPendingModelApiRun(node);
				if (node?.[PANEL_KEY]) refreshStageDisplay(node);
			}
			throw error;
		}
	};
}

function applyPreset(state, library, preset, statusEl) {
	const baseSettings = { ...(state.settings ?? {}) };
	const baseCustomTags = [...(state.customTags ?? [])];
	const tagGroupIndex = buildTagGroupIndex(library);
	const nextSelected = preset?.mergeWithCurrent
		? Object.fromEntries((library.slot_config ?? []).map((group) => [group.name, [...(state.selected?.[group.name] ?? [])]]))
		: Object.fromEntries((library.slot_config ?? []).map((group) => [group.name, []]));
	const extraTags = preset?.mergeWithCurrent ? [...(state.customTags ?? [])] : [];
	for (const tag of preset.tags ?? []) {
		if (Object.values(nextSelected).some((items) => (items ?? []).includes(tag)) || extraTags.includes(tag)) continue;
		const groupName = tagGroupIndex.get(tag);
		if (!groupName) { extraTags.push(tag); continue; }
		const groupConfig = (library.slot_config ?? []).find((group) => group.name === groupName);
		if (!groupConfig) { extraTags.push(tag); continue; }
		if (nextSelected[groupName].length < Number(groupConfig.slots ?? 0)) nextSelected[groupName].push(tag);
		else extraTags.push(tag);
	}
	state.selected = nextSelected;
	state.customTags = extraTags;
	const nextSettings = { ...baseSettings, ...(preset.settings ?? {}) };
	if (preset?.mergeExtraRequirement) {
		nextSettings["额外要求"] = mergeRequirementText(baseSettings["额外要求"], preset?.settings?.["额外要求"]);
	}
	if (Array.isArray(preset?.randomWhitelistTags) && preset.randomWhitelistTags.length) {
		const extraWhitelist = [
			...preset.randomWhitelistTags,
			...((preset?.preserveCustomTagsForRandom && String(nextSettings["运行时随机模式"] ?? "自动判断") === "全随机") ? baseCustomTags : []),
		];
		nextSettings["锁定标签白名单"] = mergeTagSettingText(baseSettings["锁定标签白名单"], extraWhitelist);
	}
	if (Array.isArray(preset?.randomExcludeTags) && preset.randomExcludeTags.length) {
		nextSettings["随机排除标签"] = mergeTagSettingText(baseSettings["随机排除标签"], preset.randomExcludeTags);
	}
	state.settings = nextSettings;
	if (statusEl) {
		statusEl.textContent = preset?.mergeWithCurrent
			? `${preset.name} 已叠加到当前标签与自定义标签上。超出槽位或不在库内的标签已放入补充标签。`
			: `${preset.name} 已载入。超出槽位或不在库内的标签已放入补充标签。`;
	}
}

function injectStageExample(node, library, statusEl) {
	const currentTemplate = String(getWidget(node, "模板风格")?.value ?? "自动");
	const presetName = EXAMPLE_PRESET_MAP[currentTemplate] ?? EXAMPLE_PRESET_MAP["自动"];
	const preset = CASE_PRESETS.find((item) => item.name === presetName) ?? CASE_PRESETS[0];
	if (!preset) return false;
	const nextState = createPresetBaseState(node, library, preset);
	applyPreset(nextState, library, preset, statusEl);
	recordNodeHistory(node, collectNodeState(node, library), "before-random");
	applyNodeState(node, library, nextState, { recordHistory: true, historySource: "random" });
	return true;
}

const REWRITE_MAINLINE_PERSON_GROUPS = new Set(["主体", "场景背景", "服装造型", "动作姿态", "道具世界观"]);
const REWRITE_MAINLINE_NON_PERSON_GROUPS = new Set(["主体", "场景背景", "道具世界观"]);

function getRewriteMainlineGroupSet(currentState) {
	const subjectType = String(currentState?.settings?.["主体类型解析结果"] ?? currentState?.settings?.["主体类型"] ?? "自动").trim();
	return subjectType === "非人物主体" ? REWRITE_MAINLINE_NON_PERSON_GROUPS : REWRITE_MAINLINE_PERSON_GROUPS;
}

function getRewriteMainlineAdditionCap(groupName, intensity, themePool = "自动") {
	if (String(themePool ?? "").trim() && String(themePool ?? "").trim() !== "自动") return 1;
	const caps = {
		主体: { 弱: 1, 中: 2, 强: 3 },
		场景背景: { 弱: 1, 中: 2, 强: 3 },
		服装造型: { 弱: 1, 中: 2, 强: 3 },
		动作姿态: { 弱: 1, 中: 1, 强: 2 },
		道具世界观: { 弱: 1, 中: 1, 强: 2 },
	};
	return Number(caps[groupName]?.[intensity] ?? 0);
}

function cloneRewriteMainlineState(currentState, library, excludeSet = new Set()) {
	const selected = Object.fromEntries((library.slot_config ?? []).map((group) => [group.name, []]));
	const tagGroupIndex = buildTagGroupIndex(library);
	const rewriteGroups = getRewriteMainlineGroupSet(currentState);
	for (const group of library.slot_config ?? []) {
		if (rewriteGroups.has(group.name)) continue;
		const source = Array.isArray(currentState.selected?.[group.name]) ? currentState.selected[group.name] : [];
		selected[group.name] = source.filter((tag) => tag && !excludeSet.has(tag)).slice(0, getTagGroupSlotLimit(library, group.name));
	}
	const customTags = (currentState.customTags ?? []).filter((tag) => {
		if (!tag || excludeSet.has(tag)) return false;
		return !rewriteGroups.has(tagGroupIndex.get(tag));
	});
	return { selected, customTags: uniqueTextList(customTags), rewriteGroups };
}

function countSettingTags(raw) {
	return parseCustomTags(raw).length;
}

function resolveRandomModeDecision(currentState) {
	const configuredMode = String(currentState?.settings?.["运行时随机模式"] ?? "自动判断").trim() || "自动判断";
	if (configuredMode !== "自动判断") return configuredMode;
	const subjectCount = Array.isArray(currentState?.selected?.["主体"]) ? currentState.selected["主体"].filter(Boolean).length : 0;
	const sceneCount = Array.isArray(currentState?.selected?.["场景背景"]) ? currentState.selected["场景背景"].filter(Boolean).length : 0;
	const compositionCount = Array.isArray(currentState?.selected?.["构图视角"]) ? currentState.selected["构图视角"].filter(Boolean).length : 0;
	const styleCount = Array.isArray(currentState?.selected?.["画面风格"]) ? currentState.selected["画面风格"].filter(Boolean).length : 0;
	const lockedCount = Math.max(0, Number(currentState?.settings?.["核心标签锁定数量"] ?? 0));
	const whitelistCount = countSettingTags(currentState?.settings?.["锁定标签白名单"]);
	const mainlineCount = subjectCount + sceneCount + compositionCount + styleCount;
	if (styleCount >= 1 && subjectCount + sceneCount >= 3) return "重写主体与场景";
	if (whitelistCount > 0) return "保留已选核心标签";
	if (
		lockedCount > 0
		&& mainlineCount > 0
		&& mainlineCount <= Math.max(3, Math.min(lockedCount, 4))
		&& (subjectCount > 0 || sceneCount > 0 || compositionCount > 0)
	) return "保留已选核心标签";
	return "全随机";
}

function createRuntimeRandomPreviewMarker(node, state) {
	const seed = Math.max(1, Math.trunc(Number(state?.settings?.seed ?? 0) || 0));
	return JSON.stringify({
		v: 1,
		source: "ui",
		token: `ui_${String(node?.id ?? "node")}_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 12)}`,
		mode: resolveRandomModeDecision(state),
		seed,
	});
}

function finalizeRuntimeRandomPreviewState(node, state, options = {}) {
	if (!state || typeof state !== "object") return state;
	const properties = ensureNodeProperties(node);
	if (!Object.prototype.hasOwnProperty.call(state, "characterSheetRestore") && properties[NODE_CHARACTER_SHEET_RESTORE_KEY]) {
		state.characterSheetRestore = cloneCharacterSheetRestoreState(properties[NODE_CHARACTER_SHEET_RESTORE_KEY]);
	}
	if (!Object.prototype.hasOwnProperty.call(state, "smartTextAutoExtra")) {
		const smartTextAutoExtra = String(properties[NODE_SMART_TEXT_AUTO_EXTRA_KEY] ?? "").trim();
		if (smartTextAutoExtra) state.smartTextAutoExtra = smartTextAutoExtra;
	}
	state.settings = { ...(state.settings ?? {}) };
	if (!state.settings["运行时随机标签"]) {
		state.settings[RUNTIME_RANDOM_PREVIEW_TOKEN_WIDGET_NAME] = "";
		return state;
	}
	let seed = Math.trunc(Number(state.settings.seed ?? 0) || 0);
	if (seed <= 0) seed = Math.floor(Math.random() * 0x7ffffffe) + 1;
	state.settings.seed = seed;
	if (options.forceNewMarker || !String(state.settings[RUNTIME_RANDOM_PREVIEW_TOKEN_WIDGET_NAME] ?? "").trim()) {
		state.settings[RUNTIME_RANDOM_PREVIEW_TOKEN_WIDGET_NAME] = createRuntimeRandomPreviewMarker(node, state);
	}
	return state;
}

function buildRandomStateLocal(node, library, sourceState = null) {
	const currentState = sourceState ? clonePresetState(sourceState) : collectNodeState(node, library);
	const randomMode = resolveRandomModeDecision(currentState);
	const randomIntensity = currentState.settings["运行时随机强度"] ?? "中";
	const lockedCount = Math.max(0, Number(currentState.settings["核心标签锁定数量"] ?? 10));
	const whitelist = uniqueTextList([
		...parseCustomTags(currentState.settings["锁定标签白名单"]),
		...parseCustomTags(currentState.settings[RUNTIME_RANDOM_PROTECTED_TAGS_WIDGET_NAME]),
	]);
	const excludeSet = new Set(parseCustomTags(currentState.settings["随机排除标签"]));
	const previousSupplementSet = new Set(readNodeRandomDedupeCache(node).filter((tag) => !whitelist.includes(tag)));
	const whitelistSet = new Set(whitelist);
	const tagGroupIndex = buildTagGroupIndex(library);
	const preservedCoreState = randomMode === "保留已选核心标签"
		? cloneCoreStateWithLimit(currentState, library, lockedCount, whitelist, excludeSet)
		: randomMode === "重写主体与场景"
			? cloneRewriteMainlineState(currentState, library, excludeSet)
			: { selected: Object.fromEntries((library.slot_config ?? []).map((group) => [group.name, []])), customTags: [] };
	const state = { selected: preservedCoreState.selected, customTags: [...preservedCoreState.customTags], settings: { ...currentState.settings } };
	if (currentState.nsfwWorkspace) state.nsfwWorkspace = cloneNsfwWorkspaceState(currentState.nsfwWorkspace);
	const preservedFlatTags = [...Object.values(preservedCoreState.selected).flatMap((tags) => tags ?? []), ...preservedCoreState.customTags];
	const rewriteGroups = randomMode === "重写主体与场景" ? getRewriteMainlineGroupSet(currentState) : new Set();
	for (const group of library.slot_config ?? []) {
		if (randomMode === "重写主体与场景" && !rewriteGroups.has(group.name)) continue;
		const allTags = flattenUniqueTags(library.tag_library?.[group.name]);
		const current = state.selected[group.name] ?? [];
		const limit = getTagGroupSlotLimit(library, group.name);
		for (const tag of whitelist) {
			if (allTags.includes(tag) && !current.includes(tag) && current.length < limit) current.push(tag);
		}
		const rewriteSourceTags = randomMode === "重写主体与场景" && rewriteGroups.has(group.name)
			? new Set((currentState.selected?.[group.name] ?? []).filter(Boolean))
			: new Set();
		let pool = allTags.filter((tag) => !current.includes(tag) && !shouldSkipRandomTag(tag, whitelistSet, excludeSet) && !rewriteSourceTags.has(tag));
		if (!pool.length && rewriteSourceTags.size) {
			pool = allTags.filter((tag) => !current.includes(tag) && !shouldSkipRandomTag(tag, whitelistSet, excludeSet));
		}
		const dedupedPool = pool.filter((tag) => !previousSupplementSet.has(tag));
		const effectivePool = dedupedPool.length ? dedupedPool : pool;
		const rewriteAdditionCap = randomMode === "重写主体与场景"
			? getRewriteMainlineAdditionCap(group.name, randomIntensity, currentState.settings["随机主题池"])
			: getRuntimeRandomAdditionCap(current.length, limit, randomIntensity);
		let additions = 0;
		while (current.length < limit && effectivePool.length && additions < rewriteAdditionCap) {
			const tag = randomItem(effectivePool);
			addUniqueTag(current, tag);
			effectivePool.splice(effectivePool.indexOf(tag), 1);
			additions += 1;
		}
		state.selected[group.name] = current;
	}
	for (const tag of whitelist) {
		if (!tag || !whitelistSet.has(tag)) continue;
		const groupName = tagGroupIndex.get(tag);
		if (groupName && (state.selected[groupName] ?? []).includes(tag)) continue;
		addUniqueTag(state.customTags, tag);
	}
	state._randomSupplementTags = [...new Set([...Object.values(state.selected).flatMap((tags) => tags ?? []), ...state.customTags].filter((tag) => !preservedFlatTags.includes(tag)))];
	return finalizeRuntimeRandomPreviewState(node, state, { forceNewMarker: true });
}

async function buildRandomState(node, library, sourceState = null) {
	const currentState = sourceState ? clonePresetState(sourceState) : collectNodeState(node, library);
	const randomMode = resolveRandomModeDecision(currentState);
	const randomIntensity = currentState.settings["运行时随机强度"] ?? "中";
	const lockedCount = Math.max(0, Number(currentState.settings["核心标签锁定数量"] ?? 10));
	const whitelist = parseCustomTags(currentState.settings["锁定标签白名单"]);
	const excludeSet = new Set(parseCustomTags(currentState.settings["随机排除标签"]));
	const randomCoreSignature = getRandomCoreSignature(currentState.settings);
	let requestState = clonePresetState(currentState);
	if (randomMode === "保留已选核心标签") {
		const currentCoreState = cloneCoreStateWithLimit(currentState, library, lockedCount, whitelist, excludeSet);
		const baselineCoreState = getNodeRandomCoreState(node);
		const lastRandomState = getNodeRandomLastState(node);
		const shouldRefreshBaseline =
			!baselineCoreState
			|| getNodeRandomCoreSignature(node) !== randomCoreSignature
			|| !lastRandomState
			|| serializeSelectionOnlyState(currentState) !== serializeSelectionOnlyState(lastRandomState);
		const effectiveCoreState = shouldRefreshBaseline ? currentCoreState : baselineCoreState;
		requestState = {
			selected: cloneSelection(effectiveCoreState.selected),
			customTags: [...effectiveCoreState.customTags],
			settings: { ...currentState.settings },
		};
	} else if (randomMode === "重写主体与场景") {
		const rewrittenState = cloneRewriteMainlineState(currentState, library, excludeSet);
		requestState = {
			selected: cloneSelection(rewrittenState.selected),
			customTags: [...rewrittenState.customTags],
			settings: { ...currentState.settings },
		};
	}
	if (currentState.nsfwWorkspace) requestState.nsfwWorkspace = cloneNsfwWorkspaceState(currentState.nsfwWorkspace);
	requestState.unique_id = String(node?.id ?? "").trim();
	requestState.cache_namespace = ensureNodeCacheNamespace(node);
	requestState.settings[RUNTIME_RANDOM_PREVIEW_TOKEN_WIDGET_NAME] = "";
	requestState._randomDedupeCache = readNodeRandomDedupeCache(node);
	try {
		const data = await mutateTagLibrary("/qwen_te/runtime_random_state", requestState, {
			owner: node,
			key: "runtime-random-state",
			timeoutMs: 30000,
		});
		if (data?.state && typeof data.state === "object") {
			if (randomMode === "保留已选核心标签") {
				data.state._randomCoreState = cloneSelectionOnlyState(requestState);
				data.state._randomCoreSignature = randomCoreSignature;
			} else {
				data.state._randomCoreState = null;
				data.state._randomCoreSignature = "";
			}
			return finalizeRuntimeRandomPreviewState(node, data.state);
		}
	} catch (_error) {}
	const fallbackState = buildRandomStateLocal(node, library, currentState);
	if (randomMode === "保留已选核心标签") {
		fallbackState._randomCoreState = cloneSelectionOnlyState(requestState);
		fallbackState._randomCoreSignature = randomCoreSignature;
	} else {
		fallbackState._randomCoreState = null;
		fallbackState._randomCoreSignature = "";
	}
	return finalizeRuntimeRandomPreviewState(node, fallbackState);
}

async function buildAndApplyRandomState(node, library, options = {}) {
	const mutationRevision = Math.max(0, Number(options.mutationRevision ?? 0) || 0) || beginNodeStateMutation(node);
	if (!isNodeStateMutationCurrent(node, mutationRevision)) return false;
	if (options.recordBefore !== false) {
		recordNodeHistory(node, collectNodeState(node, library), String(options.beforeHistorySource ?? "before-random"));
	}
	const randomState = await buildRandomState(node, library, options.sourceState ?? null);
	if (!isNodeStateMutationCurrent(node, mutationRevision)) return false;
	return applyNodeState(node, library, randomState, {
		recordHistory: options.recordHistory !== false,
		historySource: String(options.historySource ?? "random"),
		randomComboPreview: options.randomComboPreview ?? null,
		mutationRevision,
	});
}

async function applyIdentitySceneComboRandom(node, library, options = {}) {
	const mutationRevision = Math.max(0, Number(options.mutationRevision ?? 0) || 0) || beginNodeStateMutation(node);
	if (!isNodeStateMutationCurrent(node, mutationRevision)) return { ok: false, queued: false, stale: true };
	const prepared = buildIdentitySceneRandomBaseState(node, library);
	if (!prepared) {
		setNodeStatusText(node, "没有可用的人物身份或场景标签，暂时无法自动组合。");
		return { ok: false, queued: false };
	}
	const currentState = collectNodeState(node, library);
	recordNodeHistory(node, currentState, "before-random");
	const randomState = await buildRandomState(node, library, prepared.state);
	if (!isNodeStateMutationCurrent(node, mutationRevision)) return { ok: false, queued: false, stale: true };
	const nextState = applyIdentitySceneComboToState(randomState, library, prepared.combo);
	if (!applyNodeState(node, library, nextState, { recordHistory: true, historySource: "random", randomComboPreview: { identity: prepared.combo.identity, scene: prepared.combo.scene }, mutationRevision })) {
		return { ok: false, queued: false, stale: true };
	}
	pushNodeRandomComboHistory(node, prepared.combo.identity, prepared.combo.scene);
	let queued = false;
	if (options.queue && isNodeStateMutationCurrent(node, mutationRevision)) {
		queued = await queueWorkflowFromNode(node);
	}
	if (!isNodeStateMutationCurrent(node, mutationRevision)) return { ok: false, queued: false, queueSubmitted: queued, stale: true };
	const actionLabel = options.queue ? "已自动组合人物身份+场景并随机跑" : "已自动组合人物身份+场景并随机";
	const queueSuffix = options.queue && !queued ? "，但没能自动加入队列。" : "。";
	setNodeStatusText(node, `${actionLabel}：${prepared.combo.identity} + ${prepared.combo.scene}${queueSuffix}`);
	return { ok: true, queued };
}

function openPresetManager(node, library) {
	ensureSingleModal("preset-manager");
	const modalContext = buildNodeModalContext(node, library);
	const overlay = document.createElement("div"); overlay.className = "qwen-te-modal";
	overlay.dataset.qwenModal = "preset-manager";
	overlay.__qwenNode = node;
	const dialog = document.createElement("div"); dialog.className = "qwen-te-modal__dialog"; overlay.appendChild(dialog);
	const header = document.createElement("div"); header.className = "qwen-te-modal__header"; dialog.appendChild(header);
	const titleWrap = document.createElement("div"); header.appendChild(titleWrap);
	const title = document.createElement("div"); title.className = "qwen-te-modal__title"; title.textContent = `提示词预设 · ${modalContext.nodeName}`; titleWrap.appendChild(title);
	const subtitle = document.createElement("div"); subtitle.className = "qwen-te-modal__subtitle"; subtitle.textContent = `保存、查找、载入常用配置。当前输出来源：${modalContext.outputSource}。`; titleWrap.appendChild(subtitle);
	const closeButton = document.createElement("button"); closeButton.className = "qwen-te-modal__footer-button"; closeButton.textContent = "关闭"; header.appendChild(closeButton);
	const body = document.createElement("div"); body.className = "qwen-te-modal__body"; dialog.appendChild(body);
	const savePanel = document.createElement("section"); savePanel.className = "qwen-te-modal__preset-save-panel"; body.appendChild(savePanel);
	const savePanelHead = document.createElement("div"); savePanelHead.className = "qwen-te-modal__preset-save-head"; savePanel.appendChild(savePanelHead);
	const savePanelHeadText = document.createElement("div"); savePanelHead.appendChild(savePanelHeadText);
	const savePanelTitle = document.createElement("div"); savePanelTitle.className = "qwen-te-modal__preset-save-title"; savePanelTitle.textContent = "保存当前节点配置"; savePanelHeadText.appendChild(savePanelTitle);
	const savePanelDesc = document.createElement("div"); savePanelDesc.className = "qwen-te-modal__preset-save-desc"; savePanelDesc.textContent = "把当前标签与参数存成常用方案，后续一键载入或直接运行。"; savePanelHeadText.appendChild(savePanelDesc);
	const toolbar = document.createElement("div"); toolbar.className = "qwen-te-modal__toolbar qwen-te-modal__toolbar--preset-save"; savePanel.appendChild(toolbar);
	const nameInput = document.createElement("input"); nameInput.className = "qwen-te-modal__search"; nameInput.placeholder = "输入新预设名称"; toolbar.appendChild(nameInput);
	const saveButton = document.createElement("button"); saveButton.className = "qwen-te-modal__footer-button qwen-te-modal__footer-button--primary"; saveButton.textContent = "保存为预设"; toolbar.appendChild(saveButton);
	const quickImportButton = document.createElement("button"); quickImportButton.className = "qwen-te-modal__footer-button"; quickImportButton.textContent = "导入预设"; toolbar.appendChild(quickImportButton);
	const statusEl = document.createElement("div"); statusEl.className = "qwen-te-modal__status"; statusEl.textContent = "保存当前节点配置后，可在下方一键载入、运行、置顶或删除。"; savePanel.appendChild(statusEl);
	const batchBar = document.createElement("details"); batchBar.className = "qwen-te-modal__details qwen-te-modal__toolbar--preset-batch"; body.appendChild(batchBar);
	const batchSummary = document.createElement("summary"); batchSummary.className = "qwen-te-modal__details-summary"; batchSummary.textContent = "预设工具（可选）"; batchBar.appendChild(batchSummary);
	const createBatchSection = (titleText, descText, extraClass = "") => {
		const section = document.createElement("section");
		section.className = `qwen-te-modal__batch-section${extraClass ? ` ${extraClass}` : ""}`;
		const head = document.createElement("div");
		head.className = "qwen-te-modal__batch-head";
		section.appendChild(head);
		const kicker = document.createElement("div");
		kicker.className = "qwen-te-modal__batch-kicker";
		kicker.textContent = "Batch";
		head.appendChild(kicker);
		const headText = document.createElement("div");
		headText.style.minWidth = "0";
		head.appendChild(headText);
		const titleEl = document.createElement("div");
		titleEl.className = "qwen-te-modal__batch-title";
		titleEl.textContent = titleText;
		headText.appendChild(titleEl);
		if (descText) {
			const descEl = document.createElement("div");
			descEl.className = "qwen-te-modal__batch-desc";
			descEl.textContent = descText;
			headText.appendChild(descEl);
		}
		return section;
	};
	const batchMetaSection = createBatchSection("当前选择", "勾选后可批量置顶、删除、载入或导出。", "qwen-te-modal__batch-section--meta");
	batchBar.appendChild(batchMetaSection);
	const batchMetaRow = document.createElement("div"); batchMetaRow.className = "qwen-te-modal__toolbar-row qwen-te-modal__toolbar-row--preset-meta"; batchMetaSection.appendChild(batchMetaRow);
	const selectedBadge = document.createElement("div"); selectedBadge.className = "qwen-te-modal__status qwen-te-modal__status--inline"; selectedBadge.textContent = "未勾选预设"; batchMetaRow.appendChild(selectedBadge);
	const continuousCountWrap = document.createElement("div"); continuousCountWrap.className = "qwen-te-modal__input-inline"; batchMetaRow.appendChild(continuousCountWrap);
	continuousCountWrap.classList.add("qwen-te-hidden");
	const continuousCountLabel = document.createElement("span"); continuousCountLabel.className = "qwen-te-modal__input-label"; continuousCountLabel.textContent = "连测轮数"; continuousCountWrap.appendChild(continuousCountLabel);
	const continuousCountInput = document.createElement("input"); continuousCountInput.className = "qwen-te-modal__search qwen-te-modal__search--compact"; continuousCountInput.type = "number"; continuousCountInput.min = "1"; continuousCountInput.max = "99"; continuousCountInput.step = "1"; continuousCountInput.value = "3"; continuousCountInput.placeholder = "连续次数"; continuousCountWrap.appendChild(continuousCountInput);
	const clearSelectionButton = document.createElement("button"); clearSelectionButton.className = "qwen-te-modal__footer-button"; clearSelectionButton.textContent = "清空已选"; batchMetaRow.appendChild(clearSelectionButton);

	const batchDashboard = document.createElement("div"); batchDashboard.className = "qwen-te-modal__batch-dashboard"; batchBar.appendChild(batchDashboard);
	const batchDashboardMain = document.createElement("div"); batchDashboardMain.className = "qwen-te-modal__batch-dashboard-main"; batchDashboard.appendChild(batchDashboardMain);
	const batchDashboardSide = document.createElement("div"); batchDashboardSide.className = "qwen-te-modal__batch-dashboard-side"; batchDashboard.appendChild(batchDashboardSide);

	const batchManageSection = createBatchSection("批量维护", "对当前已选做置顶、取消置顶或删除。", "qwen-te-modal__batch-section--manage");
	batchDashboardSide.appendChild(batchManageSection);
	const batchManageRow = document.createElement("div"); batchManageRow.className = "qwen-te-modal__toolbar-row qwen-te-modal__toolbar-row--preset-manage"; batchManageSection.appendChild(batchManageRow);
	const batchFavoriteButton = document.createElement("button"); batchFavoriteButton.className = "qwen-te-modal__footer-button"; batchFavoriteButton.textContent = "批量置顶"; batchManageRow.appendChild(batchFavoriteButton);
	const batchUnfavoriteButton = document.createElement("button"); batchUnfavoriteButton.className = "qwen-te-modal__footer-button"; batchUnfavoriteButton.textContent = "批量取消置顶"; batchManageRow.appendChild(batchUnfavoriteButton);
	const batchDeleteButton = document.createElement("button"); batchDeleteButton.className = "qwen-te-modal__footer-button qwen-te-modal__footer-button--danger"; batchDeleteButton.textContent = "批量删除"; batchManageRow.appendChild(batchDeleteButton);
	batchDeleteButton.classList.add("qwen-te-modal__footer-button--span-full");

	const batchRunSection = createBatchSection("载入与入队", "保留最常用的首个载入/入队，减少轮流、随机和连测误触。", "qwen-te-modal__batch-section--run");
	batchDashboardMain.appendChild(batchRunSection);
	const batchRunRow = document.createElement("div"); batchRunRow.className = "qwen-te-modal__toolbar-row qwen-te-modal__toolbar-row--preset-run"; batchRunSection.appendChild(batchRunRow);
	const batchLoadButton = document.createElement("button"); batchLoadButton.className = "qwen-te-modal__footer-button"; batchLoadButton.textContent = "载入首个"; batchRunRow.appendChild(batchLoadButton);
	const batchLoadQueueButton = document.createElement("button"); batchLoadQueueButton.className = "qwen-te-modal__footer-button qwen-te-modal__footer-button--accent"; batchLoadQueueButton.textContent = "首个并入队"; batchRunRow.appendChild(batchLoadQueueButton);
	const batchCycleButton = document.createElement("button"); batchCycleButton.className = "qwen-te-modal__footer-button"; batchCycleButton.textContent = "轮流载入"; batchRunRow.appendChild(batchCycleButton);
	const batchCycleQueueButton = document.createElement("button"); batchCycleQueueButton.className = "qwen-te-modal__footer-button qwen-te-modal__footer-button--accent"; batchCycleQueueButton.textContent = "轮流并入队"; batchRunRow.appendChild(batchCycleQueueButton);
	const batchRandomLoadButton = document.createElement("button"); batchRandomLoadButton.className = "qwen-te-modal__footer-button"; batchRandomLoadButton.textContent = "随机载入"; batchRunRow.appendChild(batchRandomLoadButton);
	const batchRandomQueueButton = document.createElement("button"); batchRandomQueueButton.className = "qwen-te-modal__footer-button qwen-te-modal__footer-button--accent"; batchRandomQueueButton.textContent = "随机并入队"; batchRunRow.appendChild(batchRandomQueueButton);
	const batchRandomRunButton = document.createElement("button"); batchRandomRunButton.className = "qwen-te-modal__footer-button qwen-te-modal__footer-button--accent"; batchRandomRunButton.textContent = "随机载入后开跑"; batchRunRow.appendChild(batchRandomRunButton);
	for (const button of [batchCycleButton, batchCycleQueueButton, batchRandomLoadButton, batchRandomQueueButton, batchRandomRunButton]) {
		button.classList.add("qwen-te-hidden");
		button.setAttribute("aria-hidden", "true");
		button.tabIndex = -1;
	}

	const batchContinuousSection = createBatchSection("连续测试", "直接对当前已选启动批量验证。", "qwen-te-modal__batch-section--continuous");
	batchDashboardSide.appendChild(batchContinuousSection);
	batchContinuousSection.classList.add("qwen-te-hidden");
	const batchContinuousRow = document.createElement("div"); batchContinuousRow.className = "qwen-te-modal__toolbar-row qwen-te-modal__toolbar-row--preset-continuous"; batchContinuousSection.appendChild(batchContinuousRow);
	const continuousCycleButton = document.createElement("button"); continuousCycleButton.className = "qwen-te-modal__footer-button qwen-te-modal__footer-button--accent"; continuousCycleButton.textContent = "按顺序连测"; batchContinuousRow.appendChild(continuousCycleButton);
	const continuousRandomButton = document.createElement("button"); continuousRandomButton.className = "qwen-te-modal__footer-button qwen-te-modal__footer-button--accent"; continuousRandomButton.textContent = "随机连测"; batchContinuousRow.appendChild(continuousRandomButton);
	const stopContinuousButton = document.createElement("button"); stopContinuousButton.className = "qwen-te-modal__footer-button qwen-te-modal__footer-button--danger"; stopContinuousButton.textContent = "停止连续测试"; stopContinuousButton.disabled = true; batchContinuousRow.appendChild(stopContinuousButton);
	stopContinuousButton.classList.add("qwen-te-modal__footer-button--span-full");

	const batchExportSection = createBatchSection("导入导出", "按当前筛选范围导出，或把外部预设导回来。", "qwen-te-modal__batch-section--export");
	batchDashboardMain.appendChild(batchExportSection);
	const batchExportRow = document.createElement("div"); batchExportRow.className = "qwen-te-modal__toolbar-row qwen-te-modal__toolbar-row--preset-export"; batchExportSection.appendChild(batchExportRow);
	const exportSelectedButton = document.createElement("button"); exportSelectedButton.className = "qwen-te-modal__footer-button"; exportSelectedButton.textContent = "导出已选"; batchExportRow.appendChild(exportSelectedButton);
	const exportAllButton = document.createElement("button"); exportAllButton.className = "qwen-te-modal__footer-button"; exportAllButton.textContent = "导出当前筛选"; batchExportRow.appendChild(exportAllButton);
	const exportFavoritesButton = document.createElement("button"); exportFavoritesButton.className = "qwen-te-modal__footer-button"; exportFavoritesButton.textContent = "导出置顶项"; batchExportRow.appendChild(exportFavoritesButton);
	const exportArrangeButton = document.createElement("button"); exportArrangeButton.className = "qwen-te-modal__footer-button"; exportArrangeButton.textContent = "导出整理项"; batchExportRow.appendChild(exportArrangeButton);
	const exportHistoryAggregateButton = document.createElement("button"); exportHistoryAggregateButton.className = "qwen-te-modal__footer-button"; exportHistoryAggregateButton.textContent = "导出聚合快照"; batchExportRow.appendChild(exportHistoryAggregateButton);
	exportHistoryAggregateButton.classList.add("qwen-te-hidden");
	const exportManualButton = document.createElement("button"); exportManualButton.className = "qwen-te-modal__footer-button"; exportManualButton.textContent = "导出手存项"; batchExportRow.appendChild(exportManualButton);
	const importButton = document.createElement("button"); importButton.className = "qwen-te-modal__footer-button qwen-te-modal__footer-button--accent"; importButton.textContent = "导入文件"; batchExportRow.appendChild(importButton);
	const workspace = document.createElement("div"); workspace.className = "qwen-te-modal__workspace"; body.appendChild(workspace);
	const workspaceMain = document.createElement("div"); workspaceMain.className = "qwen-te-modal__workspace-main"; workspace.appendChild(workspaceMain);
	const workspaceSide = document.createElement("div"); workspaceSide.className = "qwen-te-modal__workspace-side"; workspace.appendChild(workspaceSide);
	const filterSurface = document.createElement("section"); filterSurface.className = "qwen-te-modal__surface qwen-te-modal__surface--filter"; workspaceMain.appendChild(filterSurface);
	const filterSurfaceHead = document.createElement("div"); filterSurfaceHead.className = "qwen-te-modal__surface-head"; filterSurface.appendChild(filterSurfaceHead);
	const filterSurfaceHeadText = document.createElement("div"); filterSurfaceHead.appendChild(filterSurfaceHeadText);
	const filterSurfaceTitle = document.createElement("div"); filterSurfaceTitle.className = "qwen-te-modal__surface-title"; filterSurfaceTitle.textContent = "筛选与查找"; filterSurfaceHeadText.appendChild(filterSurfaceTitle);
	const filterSurfaceDesc = document.createElement("div"); filterSurfaceDesc.className = "qwen-te-modal__surface-desc"; filterSurfaceDesc.textContent = "按来源和名称快速定位要复用的配置。"; filterSurfaceHeadText.appendChild(filterSurfaceDesc);
	const filterSurfaceMeta = document.createElement("div"); filterSurfaceMeta.className = "qwen-te-modal__surface-meta"; filterSurfaceHead.appendChild(filterSurfaceMeta);
	const visibleCountPill = document.createElement("div"); visibleCountPill.className = "qwen-te-modal__surface-pill qwen-te-modal__surface-pill--accent"; visibleCountPill.textContent = "当前 0 项"; filterSurfaceMeta.appendChild(visibleCountPill);
	const selectedCountPill = document.createElement("div"); selectedCountPill.className = "qwen-te-modal__surface-pill"; selectedCountPill.textContent = "已选 0 项"; filterSurfaceMeta.appendChild(selectedCountPill);
	const filterBar = document.createElement("div"); filterBar.className = "qwen-te-modal__pillbar"; filterSurface.appendChild(filterBar);
	const searchToolbar = document.createElement("div"); searchToolbar.className = "qwen-te-modal__filter-toolbar"; filterSurface.appendChild(searchToolbar);
	const searchInput = document.createElement("input"); searchInput.className = "qwen-te-modal__search"; searchInput.placeholder = "搜索预设名称 / 来源 / 摘要"; searchToolbar.appendChild(searchInput);
	const sortSelect = document.createElement("select"); sortSelect.className = "qwen-te-modal__search"; searchToolbar.appendChild(sortSelect);
	const guideEl = document.createElement("div"); guideEl.className = "qwen-te-modal__filter-guide"; guideEl.textContent = "默认优先显示置顶项，可直接载入或运行。"; filterSurface.appendChild(guideEl);
	const listSurface = document.createElement("section"); listSurface.className = "qwen-te-modal__surface qwen-te-modal__surface--list"; workspaceMain.appendChild(listSurface);
	const listSurfaceHead = document.createElement("div"); listSurfaceHead.className = "qwen-te-modal__surface-head"; listSurface.appendChild(listSurfaceHead);
	const listSurfaceHeadText = document.createElement("div"); listSurfaceHead.appendChild(listSurfaceHeadText);
	const listSurfaceTitle = document.createElement("div"); listSurfaceTitle.className = "qwen-te-modal__surface-title"; listSurfaceTitle.textContent = "预设结果"; listSurfaceHeadText.appendChild(listSurfaceTitle);
	const listSurfaceDesc = document.createElement("div"); listSurfaceDesc.className = "qwen-te-modal__surface-desc"; listSurfaceDesc.textContent = "可载入、运行或直接修改已保存的标签与参数。"; listSurfaceHeadText.appendChild(listSurfaceDesc);
	const list = document.createElement("div"); list.className = "qwen-te-preset-list qwen-te-modal__list-scroll"; listSurface.appendChild(list);
	const reportSurface = document.createElement("section"); reportSurface.className = "qwen-te-modal__surface"; workspaceSide.appendChild(reportSurface);
	reportSurface.classList.add("qwen-te-hidden");
	const reportSurfaceHead = document.createElement("div"); reportSurfaceHead.className = "qwen-te-modal__surface-head"; reportSurface.appendChild(reportSurfaceHead);
	const reportSurfaceHeadText = document.createElement("div"); reportSurfaceHead.appendChild(reportSurfaceHeadText);
	const reportSummaryTitle = document.createElement("div"); reportSummaryTitle.className = "qwen-te-modal__surface-title"; reportSummaryTitle.textContent = "连续测试报告"; reportSurfaceHeadText.appendChild(reportSummaryTitle);
	const reportSummaryMeta = document.createElement("div"); reportSummaryMeta.className = "qwen-te-modal__surface-desc"; reportSummaryMeta.textContent = "未开始记录"; reportSurfaceHeadText.appendChild(reportSummaryMeta);
	const reportSurfaceMeta = document.createElement("div"); reportSurfaceMeta.className = "qwen-te-modal__surface-meta"; reportSurfaceHead.appendChild(reportSurfaceMeta);
	const reportSummaryCount = document.createElement("div"); reportSummaryCount.className = "qwen-te-modal__surface-pill qwen-te-modal__surface-pill--accent"; reportSummaryCount.textContent = "0 条"; reportSurfaceMeta.appendChild(reportSummaryCount);
	const reportStatus = document.createElement("div"); reportStatus.className = "qwen-te-modal__status qwen-te-modal__status--panel"; reportStatus.textContent = "开始连续测试后，这里会记录每轮执行结果。"; reportSurface.appendChild(reportStatus);
	const reportToolbar = document.createElement("div"); reportToolbar.className = "qwen-te-modal__report-actions"; reportSurface.appendChild(reportToolbar);
	const reportCopyButton = document.createElement("button"); reportCopyButton.className = "qwen-te-modal__footer-button"; reportCopyButton.textContent = "复制报告"; reportToolbar.appendChild(reportCopyButton);
	const reportExportButton = document.createElement("button"); reportExportButton.className = "qwen-te-modal__footer-button"; reportExportButton.textContent = "导出 JSON"; reportToolbar.appendChild(reportExportButton);
	const reportExportCsvButton = document.createElement("button"); reportExportCsvButton.className = "qwen-te-modal__footer-button"; reportExportCsvButton.textContent = "导出 CSV"; reportToolbar.appendChild(reportExportCsvButton);
	const reportExportMarkdownButton = document.createElement("button"); reportExportMarkdownButton.className = "qwen-te-modal__footer-button"; reportExportMarkdownButton.textContent = "导出 Markdown"; reportToolbar.appendChild(reportExportMarkdownButton);
	const reportSaveHistoryButton = document.createElement("button"); reportSaveHistoryButton.className = "qwen-te-modal__footer-button"; reportSaveHistoryButton.textContent = "报告入历史"; reportToolbar.appendChild(reportSaveHistoryButton);
	const reportClearButton = document.createElement("button"); reportClearButton.className = "qwen-te-modal__footer-button"; reportClearButton.textContent = "清空报告"; reportToolbar.appendChild(reportClearButton);
	const reportList = document.createElement("div"); reportList.className = "qwen-te-preset-list qwen-te-modal__report-stream"; reportSurface.appendChild(reportList);
	const footer = document.createElement("div"); footer.className = "qwen-te-modal__footer"; dialog.appendChild(footer);
	const doneButton = document.createElement("button"); doneButton.className = "qwen-te-modal__footer-button"; doneButton.textContent = "完成"; footer.appendChild(doneButton);
	const fileInput = document.createElement("input"); fileInput.type = "file"; fileInput.accept = "application/json,.json"; fileInput.style.display = "none"; dialog.appendChild(fileInput);
	let activeSourceFilter = "all";
	let activeSort = "updated_desc";
	const filterButtons = new Map();
	const expandedPresetIds = new Set();
	let editingPresetId = "";
	const initialBatchState = getNodePresetBatchState(node);
	const selectedPresetIds = new Set(initialBatchState.selectedIds);
		let batchLoadCursor = 0;
		let continuousRunToken = Number(node?.[PANEL_KEY]?.continuousRuntime?.token ?? 0);
		let continuousRunning = !!node?.[PANEL_KEY]?.continuousRuntime?.running;
		let continuousRunReport = getNodeContinuousRunReport(node);
	const visiblePresetFilterKeys = ["all", "favorites", "manual", "arrange-preview"];
	const hiddenPresetSourceKinds = new Set(["history-aggregate", "single-preset"]);
	const sortOptions = [
		{ key: "updated_desc", label: "最新在前" },
		{ key: "name_asc", label: "按名称" },
	];
	continuousCountInput.value = String(initialBatchState.continuousCount);
	const persistPresetBatchState = () => {
		setNodePresetBatchState(node, {
			selectedIds: [...selectedPresetIds],
			continuousCount: continuousCountInput.value,
		});
		refreshNodeSummary(node, library);
	};
	const buildPresetManagerGuideText = (filteredPresets, keyword) => {
		if (activeSourceFilter === "arrange-preview") {
			return "整理预设来自自定义标签智能整理预览，适合保留一套整理后的槽位配置。";
		}
		return keyword ? `当前搜索：${keyword}，匹配 ${filteredPresets.length} 个预设。` : `当前显示 ${filteredPresets.length} 个预设。可直接载入、运行、置顶或删除。`;
	};
	const buildPresetManagerEmptyText = (keyword) => {
		if (keyword) return "当前筛选与搜索下没有匹配的预设。";
		if (activeSourceFilter === "arrange-preview") return "当前筛选下还没有整理预设。可先在整理预览里点“预览存为预设”。";
		if (activeSourceFilter === "all") return "还没有保存过预设。";
		return `当前筛选下没有“${USER_PRESET_FILTER_LABELS[activeSourceFilter] ?? activeSourceFilter}”预设。`;
	};
	const buildPresetBatchStatus = (kind, options = {}) => {
		const count = Number(options.count ?? 0);
		const total = Number(options.total ?? 0);
		const index = Number(options.index ?? 0);
		const presetName = String(options.presetName ?? "").trim();
		const queued = options.queued;
		const selectedLabel = "已选预设";
		const visibleLabel = "当前可见预设";
		const favoritesLabel = "置顶预设";
		const arrangeLabel = "整理预设";
		const historyAggregateLabel = "历史聚合快照";
		const manualLabel = "手存预设";
		const labels = {
			load_first_empty: `当前没有可载入的${selectedLabel}。`,
			load_first_ok: `已载入所选首个预设：${presetName}`,
			load_first_queue_empty: `当前没有可载入并入队的${selectedLabel}。`,
			load_first_queue_ok: queued ? `已载入并入队所选首个预设：${presetName}` : `已载入所选首个预设：${presetName}，但未能自动入队`,
			cycle_empty: `当前没有可轮流载入的${selectedLabel}。`,
			cycle_ok: `已轮流载入预设 ${index}/${total}：${presetName}`,
			cycle_queue_empty: `当前没有可轮流载入并入队的${selectedLabel}。`,
			cycle_queue_ok: queued ? `已轮流载入并入队预设 ${index}/${total}：${presetName}` : `已轮流载入预设 ${index}/${total}：${presetName}，但未能自动入队`,
			random_empty: `当前没有可随机载入的${selectedLabel}。`,
			random_ok: `已随机载入预设 ${index}/${total}：${presetName}`,
			random_queue_empty: `当前没有可随机载入并入队的${selectedLabel}。`,
			random_queue_ok: queued ? `已随机载入并入队预设 ${index}/${total}：${presetName}` : `已随机载入预设 ${index}/${total}：${presetName}，但未能自动入队`,
			random_run_empty: `当前没有可随机载入并随机跑的${selectedLabel}。`,
			random_run_ok: queued ? `已随机载入预设并随机跑 ${index}/${total}：${presetName}` : `已随机载入预设并随机化 ${index}/${total}：${presetName}，但未能自动入队`,
			export_selected_empty: `当前没有可导出的${selectedLabel}。`,
			export_selected_ok: `已导出 ${count} 个${selectedLabel}。`,
			export_visible_empty: `当前没有可导出的预设。`,
			export_visible_ok: `已导出当前可见的 ${count} 个预设。`,
			export_favorites_empty: `当前没有可导出的${favoritesLabel}。`,
			export_favorites_ok: `已导出 ${count} 个${favoritesLabel}。`,
			export_arrange_empty: `当前没有可导出的${arrangeLabel}。`,
			export_arrange_ok: `已导出 ${count} 个${arrangeLabel}。`,
			export_history_aggregate_empty: `当前没有可导出的${historyAggregateLabel}。`,
			export_history_aggregate_ok: `已导出 ${count} 个${historyAggregateLabel}。`,
			export_manual_empty: `当前没有可导出的${manualLabel}。`,
			export_manual_ok: `已导出 ${count} 个${manualLabel}。`,
		};
		return labels[kind] ?? "操作完成。";
	};
	const buildContinuousRunReportText = () => {
		if (!continuousRunReport.length) return "";
		return continuousRunReport.map((entry) => {
			const parts = [`[${formatPresetTime(entry.at)}]`, entry.level, entry.message];
			return parts.join(" ");
		}).join("\n");
	};
	const buildContinuousRunHistorySummary = () => {
		if (!continuousRunReport.length) return "";
		const latest = continuousRunReport[0];
		return `连续测试报告 | ${continuousRunReport.length} 条 | 最新：${latest.level} ${latest.message}`;
	};
	const buildContinuousRunReportMarkdown = () => {
		if (!continuousRunReport.length) return "";
		const lines = [
			"# 连续测试报告",
			"",
			`- 事件数：${continuousRunReport.length}`,
			`- 导出时间：${formatPresetTime(Date.now())}`,
			"",
			"| 时间 | 级别 | 说明 |",
			"| --- | --- | --- |",
		];
		for (const entry of continuousRunReport) {
			const time = formatPresetTime(entry.at).replace(/\|/g, "\\|");
			const level = String(entry.level ?? "").replace(/\|/g, "\\|");
			const message = String(entry.message ?? "").replace(/\|/g, "\\|").replace(/\n/g, "<br>");
			lines.push(`| ${time} | ${level} | ${message} |`);
		}
		return lines.join("\n");
	};
	const buildContinuousRunReportCsv = () => {
		if (!continuousRunReport.length) return "";
		const escapeCsv = (value) => `"${String(value ?? "").replace(/"/g, '""')}"`;
		const rows = [["时间", "级别", "说明"]];
		for (const entry of continuousRunReport) rows.push([formatPresetTime(entry.at), entry.level, entry.message]);
		return rows.map((row) => row.map(escapeCsv).join(",")).join("\n");
	};
	const exportTextFile = (content, filename, mimeType) => {
		if (!content) return false;
		const blob = new Blob([content], { type: mimeType });
		const url = URL.createObjectURL(blob);
		const a = document.createElement("a");
		a.href = url;
		a.download = filename;
		document.body.appendChild(a);
		a.click();
		document.body.removeChild(a);
		URL.revokeObjectURL(url);
		return true;
	};
	const exportContinuousRunReport = () => {
		if (!continuousRunReport.length) return false;
		const payload = {
			version: 1,
			exportedAt: Date.now(),
			source: "qwen-te-continuous-run-report",
			report: continuousRunReport,
		};
		const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
		const url = URL.createObjectURL(blob);
		const a = document.createElement("a");
		a.href = url;
		a.download = `qwen-te-continuous-report-${buildCompactTimestamp()}.json`;
		document.body.appendChild(a);
		a.click();
		document.body.removeChild(a);
		URL.revokeObjectURL(url);
		return true;
	};
	const renderContinuousRunReport = () => {
		reportList.replaceChildren();
		reportSummaryCount.textContent = `${continuousRunReport.length} 条`;
		if (!continuousRunReport.length) {
			reportSummaryMeta.textContent = "未开始记录";
			const empty = document.createElement("div");
			empty.className = "qwen-te-modal__empty-state";
			empty.textContent = "开始连续测试后，这里会记录每轮执行结果。";
			reportList.appendChild(empty);
			reportCopyButton.disabled = true;
			reportCopyButton.style.opacity = "0.55";
			reportExportButton.disabled = true;
			reportExportButton.style.opacity = "0.55";
			reportExportCsvButton.disabled = true;
			reportExportCsvButton.style.opacity = "0.55";
			reportExportMarkdownButton.disabled = true;
			reportExportMarkdownButton.style.opacity = "0.55";
			reportSaveHistoryButton.disabled = true;
			reportSaveHistoryButton.style.opacity = "0.55";
			reportClearButton.disabled = true;
			reportClearButton.style.opacity = "0.55";
			reportStatus.textContent = "开始连续测试后，这里会记录每轮执行结果。";
			return;
		}
		const latestEntry = continuousRunReport[0];
		reportSummaryMeta.textContent = `最新：${String(latestEntry?.level ?? "")} ${String(latestEntry?.message ?? "").trim()}`.trim();
		reportCopyButton.disabled = false;
		reportCopyButton.style.opacity = "1";
		reportExportButton.disabled = false;
		reportExportButton.style.opacity = "1";
		reportExportCsvButton.disabled = false;
		reportExportCsvButton.style.opacity = "1";
		reportExportMarkdownButton.disabled = false;
		reportExportMarkdownButton.style.opacity = "1";
		reportSaveHistoryButton.disabled = false;
		reportSaveHistoryButton.style.opacity = "1";
		reportClearButton.disabled = false;
		reportClearButton.style.opacity = "1";
		const recentEntries = continuousRunReport.slice(0, 20);
		for (const entry of recentEntries) {
			const card = document.createElement("div");
			card.className = "qwen-te-preset-card";
			reportList.appendChild(card);
			const head = document.createElement("div");
			head.className = "qwen-te-preset-card__header";
			card.appendChild(head);
			const title = document.createElement("div");
			title.className = "qwen-te-preset-card__name";
			title.textContent = entry.level;
			head.appendChild(title);
			const time = document.createElement("div");
			time.className = "qwen-te-preset-card__time";
			time.textContent = formatPresetTime(entry.at);
			head.appendChild(time);
			const summary = document.createElement("div");
			summary.className = "qwen-te-preset-card__summary";
			summary.textContent = entry.message;
			card.appendChild(summary);
		}
		reportStatus.textContent = `已记录 ${continuousRunReport.length} 条连续测试事件。`;
	};
		const pushContinuousRunReport = (level, message) => {
			continuousRunReport.unshift({ at: Date.now(), level, message });
			continuousRunReport = continuousRunReport.slice(0, 50);
			setNodeContinuousRunReport(node, continuousRunReport);
			setNodeContinuousReportMeta(node, { at: Date.now(), level, summary: message });
			refreshNodeSummary(node, library);
			renderContinuousRunReport();
		};
		const syncBatchSelectionUi = (visiblePresets = [], allPresets = []) => {
			const allIdSet = new Set((allPresets ?? []).map((preset) => String(preset.id ?? "")));
			for (const id of [...selectedPresetIds]) {
				if (!allIdSet.has(id)) selectedPresetIds.delete(id);
			}
			const selectedCount = selectedPresetIds.size;
			const visibleSelectedCount = visiblePresets.filter((preset) => selectedPresetIds.has(String(preset.id ?? ""))).length;
			selectedBadge.textContent = selectedCount
				? visibleSelectedCount === selectedCount
					? `已勾选 ${selectedCount} 个预设`
					: `已勾选 ${selectedCount} 个预设（当前可见 ${visibleSelectedCount} 个）`
				: "未勾选预设";
			selectedCountPill.textContent = `已选 ${selectedCount} 项`;
			visibleCountPill.textContent = `当前 ${visiblePresets.length} 项`;
			const disabled = selectedCount === 0;
			for (const button of [batchFavoriteButton, batchUnfavoriteButton, batchDeleteButton, batchLoadButton, batchLoadQueueButton, batchCycleButton, batchCycleQueueButton, batchRandomLoadButton, batchRandomQueueButton, batchRandomRunButton, exportSelectedButton, clearSelectionButton]) {
				button.disabled = disabled || continuousRunning;
				button.style.opacity = (disabled || continuousRunning) ? "0.55" : "1";
			}
			for (const button of [continuousCycleButton, continuousRandomButton]) {
				button.disabled = disabled || continuousRunning;
				button.style.opacity = (disabled || continuousRunning) ? "0.55" : "1";
			}
			stopContinuousButton.disabled = !continuousRunning;
			stopContinuousButton.style.opacity = continuousRunning ? "1" : "0.55";
			continuousCountInput.disabled = continuousRunning;
			continuousCountInput.style.opacity = continuousRunning ? "0.7" : "1";
			const favoriteCount = visiblePresets.filter((preset) => !!preset.favorite).length;
			const arrangeCount = visiblePresets.filter((preset) => String(preset.source ?? "manual") === "arrange-preview").length;
			const historyAggregateCount = visiblePresets.filter((preset) => String(preset.source ?? "manual") === "history-aggregate").length;
			const manualCount = visiblePresets.filter((preset) => String(preset.source ?? "manual") === "manual").length;
			exportAllButton.disabled = visiblePresets.length === 0;
			exportAllButton.style.opacity = visiblePresets.length === 0 ? "0.55" : "1";
			exportFavoritesButton.disabled = favoriteCount === 0;
			exportFavoritesButton.style.opacity = favoriteCount === 0 ? "0.55" : "1";
			exportArrangeButton.disabled = arrangeCount === 0;
			exportArrangeButton.style.opacity = arrangeCount === 0 ? "0.55" : "1";
			exportHistoryAggregateButton.disabled = historyAggregateCount === 0;
			exportHistoryAggregateButton.style.opacity = historyAggregateCount === 0 ? "0.55" : "1";
			exportManualButton.disabled = manualCount === 0;
			exportManualButton.style.opacity = manualCount === 0 ? "0.55" : "1";
		};
	const setActiveFilterButton = () => {
		for (const [key, button] of filterButtons.entries()) {
			const active = key === activeSourceFilter;
			button.style.borderColor = active ? "#caa55b" : "#525252";
			button.style.background = active ? "#59451a" : "#232323";
			button.style.color = active ? "#fff0ca" : "#f7f7f7";
		}
	};
		const render = () => {
		const allPresets = getUserPresets().filter((preset) => !hiddenPresetSourceKinds.has(String(preset.source ?? "manual")));
		const hasAnyPreset = allPresets.length > 0;
		batchBar.classList.toggle("qwen-te-hidden", !hasAnyPreset);
		filterSurface.classList.toggle("qwen-te-hidden", !hasAnyPreset);
		listSurfaceDesc.textContent = hasAnyPreset
			? "每个预设只保留高频动作：载入、运行、置顶、删除。"
			: "还没有保存的预设。先在上方输入名称并保存当前节点配置。";
			const sourceCounts = new Map();
			for (const preset of allPresets) {
				const key = String(preset.source ?? "manual");
				sourceCounts.set(key, (sourceCounts.get(key) ?? 0) + 1);
			}
			for (const [key, button] of filterButtons.entries()) {
				const count = key === "all"
					? allPresets.length
					: key === "favorites"
						? allPresets.filter((preset) => !!preset.favorite).length
						: (sourceCounts.get(key) ?? 0);
				const label = USER_PRESET_FILTER_LABELS[key] ?? "用户预设";
				button.textContent = `${label} (${count})`;
				button.classList.toggle("qwen-te-hidden", key !== "all" && count <= 0);
			}
				setActiveFilterButton();
				const presets = activeSourceFilter === "all"
					? allPresets
					: activeSourceFilter === "favorites"
						? allPresets.filter((preset) => !!preset.favorite)
						: allPresets.filter((preset) => String(preset.source ?? "manual") === activeSourceFilter);
			const keyword = String(searchInput.value ?? "").trim().toLowerCase();
			const filteredPresets = !keyword
				? presets
				: presets.filter((preset) => buildUserPresetSearchText(preset).includes(keyword));
				filteredPresets.sort((left, right) => {
					const favoriteCompare = Number(!!right.favorite) - Number(!!left.favorite);
					if (favoriteCompare !== 0) return favoriteCompare;
					if (activeSort === "name_asc") {
						return String(left.name ?? "").localeCompare(String(right.name ?? ""), "zh-CN");
					}
				return Number(right.updatedAt ?? 0) - Number(left.updatedAt ?? 0);
			});
			list.replaceChildren();
			guideEl.textContent = buildPresetManagerGuideText(filteredPresets, keyword);
			visibleCountPill.textContent = `当前 ${filteredPresets.length} 项`;
			selectedCountPill.textContent = `已选 ${selectedPresetIds.size} 项`;
				for (const preset of filteredPresets) {
				const card = document.createElement("div");
				const isHistoryAggregatePreset = false;
				const presetId = String(preset.id ?? "");
				const expanded = isHistoryAggregatePreset && expandedPresetIds.has(presetId);
				card.className = `qwen-te-preset-card${isHistoryAggregatePreset ? ` qwen-te-preset-card--${inferHistoryAggregatePresetTone(preset)}` : ""}${expanded ? " qwen-te-preset-card--expanded" : ""}`;
				list.appendChild(card);
					const head = document.createElement("div");
					head.className = "qwen-te-preset-card__header";
					card.appendChild(head);
					const selectButton = document.createElement("button");
					selectButton.className = `qwen-te-modal__footer-button qwen-te-preset-card__select${selectedPresetIds.has(String(preset.id ?? "")) ? " qwen-te-modal__footer-button--primary" : ""}`;
					selectButton.textContent = selectedPresetIds.has(String(preset.id ?? "")) ? "已勾选" : "勾选";
					selectButton.onclick = () => {
						const presetId = String(preset.id ?? "");
						if (selectedPresetIds.has(presetId)) selectedPresetIds.delete(presetId);
						else selectedPresetIds.add(presetId);
						batchLoadCursor = 0;
						persistPresetBatchState();
						render();
					};
					head.appendChild(selectButton);
					const titleWrap = document.createElement("div");
					titleWrap.className = "qwen-te-preset-card__head-main";
					head.appendChild(titleWrap);
					const n = document.createElement("div");
					n.className = "qwen-te-preset-card__name";
					n.textContent = `${preset.favorite ? "★ " : ""}${preset.name}`;
					titleWrap.appendChild(n);
				const sourceBadge = document.createElement("div");
				sourceBadge.className = "qwen-te-modal__content-pill qwen-te-modal__content-pill--muted qwen-te-preset-card__source";
				sourceBadge.textContent = USER_PRESET_SOURCE_LABELS[preset.source] ?? "用户预设";
				titleWrap.appendChild(sourceBadge);
				const t = document.createElement("div");
				t.className = "qwen-te-preset-card__time";
				t.textContent = formatPresetTime(preset.updatedAt);
				head.appendChild(t);
				const extraBadges = buildUserPresetMetaBadges(preset);
				if (extraBadges.length) {
					const badgeBar = document.createElement("div");
					badgeBar.className = "qwen-te-preset-card__badges";
					card.appendChild(badgeBar);
					for (const badgeItem of extraBadges) {
						const badge = document.createElement("div");
						badge.className = `qwen-te-preset-card__badge qwen-te-preset-card__badge--${badgeItem.tone ?? "info"}`;
						badge.textContent = badgeItem.text;
						badgeBar.appendChild(badge);
					}
				}
				const s = document.createElement("div");
				s.className = "qwen-te-preset-card__summary";
				s.textContent = buildUserPresetSummaryText(preset);
				card.appendChild(s);

				const isEditingPreset = editingPresetId === presetId;
				if (isEditingPreset) {
					let editorBaseState = clonePresetState(preset.state);
					const editor = document.createElement("div");
					editor.className = "qwen-te-preset-card__editor";
					card.appendChild(editor);
					const editorHelp = document.createElement("div");
					editorHelp.className = "qwen-te-preset-card__editor-help";
					editorHelp.textContent = "按“分组: 标签1, 标签2”修改标签；设置区使用 JSON。NSFW、设定图等附加状态会保留，抓取当前节点时会一起替换。";
					editor.appendChild(editorHelp);
					const editorGrid = document.createElement("div");
					editorGrid.className = "qwen-te-preset-card__editor-grid";
					editor.appendChild(editorGrid);
					const nameField = document.createElement("label");
					nameField.className = "qwen-te-preset-card__editor-field qwen-te-preset-card__editor-field--wide";
					editorGrid.appendChild(nameField);
					const nameLabel = document.createElement("span");
					nameLabel.className = "qwen-te-preset-card__editor-label";
					nameLabel.textContent = "预设名称";
					nameField.appendChild(nameLabel);
					const editNameInput = document.createElement("input");
					editNameInput.className = "qwen-te-modal__search";
					editNameInput.maxLength = USER_PRESET_NAME_MAX_CHARS;
					editNameInput.value = String(preset.name ?? "");
					nameField.appendChild(editNameInput);
					const tagField = document.createElement("label");
					tagField.className = "qwen-te-preset-card__editor-field";
					editorGrid.appendChild(tagField);
					const tagLabel = document.createElement("span");
					tagLabel.className = "qwen-te-preset-card__editor-label";
					tagLabel.textContent = "分组标签与自定义标签";
					tagField.appendChild(tagLabel);
					const tagEditor = document.createElement("textarea");
					tagEditor.className = "qwen-te-modal__textarea qwen-te-preset-card__editor-textarea";
					tagEditor.value = formatPresetSelectionEditorText(editorBaseState, library);
					tagField.appendChild(tagEditor);
					const settingsField = document.createElement("label");
					settingsField.className = "qwen-te-preset-card__editor-field";
					editorGrid.appendChild(settingsField);
					const settingsLabel = document.createElement("span");
					settingsLabel.className = "qwen-te-preset-card__editor-label";
					settingsLabel.textContent = "预设参数 JSON";
					settingsField.appendChild(settingsLabel);
					const settingsEditor = document.createElement("textarea");
					settingsEditor.className = "qwen-te-modal__textarea qwen-te-preset-card__editor-textarea";
					settingsEditor.value = formatPresetSettingsEditorText(editorBaseState);
					settingsField.appendChild(settingsEditor);
					const editorActions = document.createElement("div");
					editorActions.className = "qwen-te-preset-card__editor-actions";
					editor.appendChild(editorActions);
					const captureCurrent = document.createElement("button");
					captureCurrent.className = "qwen-te-modal__footer-button";
					captureCurrent.textContent = "抓取当前节点";
					captureCurrent.onclick = () => {
						editorBaseState = clonePresetState(collectNodeState(node, library));
						tagEditor.value = formatPresetSelectionEditorText(editorBaseState, library);
						settingsEditor.value = formatPresetSettingsEditorText(editorBaseState);
						statusEl.textContent = `已抓取当前节点内容，确认后点击“保存修改”：${preset.name}`;
					};
					editorActions.appendChild(captureCurrent);
					const cancelEdit = document.createElement("button");
					cancelEdit.className = "qwen-te-modal__footer-button";
					cancelEdit.textContent = "取消修改";
					cancelEdit.onclick = () => { editingPresetId = ""; statusEl.textContent = "已取消修改预设。"; render(); };
					editorActions.appendChild(cancelEdit);
					const saveEdit = document.createElement("button");
					saveEdit.className = "qwen-te-modal__footer-button qwen-te-modal__footer-button--primary";
					saveEdit.textContent = "保存修改";
					saveEdit.onclick = () => {
						const built = buildEditedPresetState(editorBaseState, library, tagEditor.value, settingsEditor.value);
						if (!built.ok) { statusEl.textContent = built.error || "预设内容格式不正确。"; return; }
						const result = updateUserPreset(presetId, { name: editNameInput.value, state: built.state });
						if (!result.ok) {
							const messages = {
								"invalid-name": "预设名称为空或过长。",
								"duplicate-name": "已有同名预设，请换一个名称。",
								"too-large": "修改后的预设内容超过单项容量上限。",
								capacity: "预设库容量不足，未保存修改。",
								storage: "浏览器本地存储空间不足，未保存修改。",
								"not-found": "原预设已不存在，请刷新列表。",
							};
							statusEl.textContent = messages[result.reason] ?? "保存预设修改失败。";
							return;
						}
						editingPresetId = "";
						statusEl.textContent = `已保存预设修改：${result.preset?.name ?? preset.name}`;
						render();
					};
					editorActions.appendChild(saveEdit);
				}
				const actions = document.createElement("div");
				actions.className = "qwen-te-preset-card__actions";
				card.appendChild(actions);
			const primaryActions = document.createElement("div");
			primaryActions.className = "qwen-te-preset-card__action-row qwen-te-preset-card__action-row--primary";
			actions.appendChild(primaryActions);
			if (isHistoryAggregatePreset) {
				const toggleDetail = document.createElement("button");
				toggleDetail.className = "qwen-te-modal__footer-button";
				toggleDetail.textContent = expanded ? "收起详情" : "展开详情";
				toggleDetail.onclick = () => {
					if (expandedPresetIds.has(presetId)) expandedPresetIds.delete(presetId);
					else expandedPresetIds.add(presetId);
					render();
				};
				primaryActions.appendChild(toggleDetail);
			}
			const editPreset = document.createElement("button");
			editPreset.className = "qwen-te-modal__footer-button";
			editPreset.textContent = isEditingPreset ? "收起修改" : "修改内容";
			editPreset.onclick = () => {
				editingPresetId = isEditingPreset ? "" : presetId;
				statusEl.textContent = isEditingPreset ? `已收起预设修改：${preset.name}` : `正在修改预设：${preset.name}`;
				render();
			};
			primaryActions.appendChild(editPreset);
			const load = document.createElement("button");
			load.className = "qwen-te-modal__footer-button";
			load.textContent = "载入";
			load.onclick = () => {
				applyNodeState(node, library, clonePresetState(preset.state), { recordHistory: true, historySource: "preset-load" });
				statusEl.textContent = `已载入预设：${preset.name}`;
			};
				primaryActions.appendChild(load);
			const loadRun = document.createElement("button");
			loadRun.className = "qwen-te-modal__footer-button qwen-te-modal__footer-button--accent";
			loadRun.textContent = "载入并运行";
			loadRun.onclick = async () => {
				const queued = await applyPresetToNode(preset, { queue: true });
				statusEl.textContent = queued ? `已载入并入队：${preset.name}` : `已载入预设：${preset.name}，但未能自动入队。`;
			};
			primaryActions.appendChild(loadRun);
			const maintainActions = document.createElement("div");
			maintainActions.className = "qwen-te-preset-card__action-row qwen-te-preset-card__action-row--danger";
			actions.appendChild(maintainActions);
			const favorite = document.createElement("button");
				favorite.className = "qwen-te-modal__footer-button";
				favorite.textContent = preset.favorite ? "取消置顶" : "置顶";
				favorite.onclick = () => {
					toggleUserPresetFavorite(preset.id);
					statusEl.textContent = preset.favorite ? `已取消置顶预设：${preset.name}` : `已置顶预设：${preset.name}`;
					render();
				};
				maintainActions.appendChild(favorite);
				const del = document.createElement("button");
			del.className = "qwen-te-modal__footer-button";
			del.textContent = "删除";
			del.onclick = () => {
				const confirmed = window.confirm(`将删除预设「${preset.name}」，确定继续吗？`);
				if (!confirmed) {
					statusEl.textContent = "已取消删除预设。";
					return;
				}
				expandedPresetIds.delete(presetId);
				if (editingPresetId === presetId) editingPresetId = "";
				deleteUserPreset(preset.id);
				statusEl.textContent = `已删除预设：${preset.name}`;
				render();
			};
			maintainActions.appendChild(del);
			if (expanded && isHistoryAggregatePreset) {
				const meta = preset.meta ?? {};
				const detailWrap = document.createElement("div");
				detailWrap.className = "qwen-te-preset-card__detail";
				card.appendChild(detailWrap);

				const detailTitle = document.createElement("div");
				detailTitle.className = "qwen-te-preset-card__detail-item";
				detailTitle.innerHTML = "<strong>历史聚合快照详情</strong>";
				detailWrap.appendChild(detailTitle);

				const rows = [
					[`目标预设`, String(meta.presetName ?? "未知")],
					[`报告数`, String(meta.reportCount ?? "0")],
					[`平均成功率`, String(meta.averageSuccessRate ?? "待定")],
					[`最近趋势`, `${String(meta.latestTrendArrow ?? "").trim()} ${String(meta.latestTrendLabel ?? "").trim()}`.trim() || "待观察"],
					[`最近风险`, String(meta.latestRisk ?? "未知")],
					[`最近结果`, String(meta.latestOutcomeTrail ?? "·")],
					[`最近时间`, formatPresetTime(meta.latestAt)],
				];
				const detailGrid = document.createElement("div");
				detailGrid.className = "qwen-te-preset-card__detail-grid";
				detailWrap.appendChild(detailGrid);
				for (const [label, value] of rows) {
					const row = document.createElement("div");
					row.className = "qwen-te-preset-card__kv";
					const labelEl = document.createElement("div");
					labelEl.className = "qwen-te-preset-card__kv-label";
					labelEl.textContent = label;
					row.appendChild(labelEl);
					const valueEl = document.createElement("div");
					valueEl.className = "qwen-te-preset-card__kv-value";
					valueEl.textContent = String(value ?? "");
					row.appendChild(valueEl);
					detailGrid.appendChild(row);
				}

				if (String(meta.latestMessage ?? "").trim()) {
					const latestRow = document.createElement("div");
					latestRow.className = "qwen-te-preset-card__detail-item";
					const latestStrong = document.createElement("strong");
					latestStrong.textContent = "最近事件";
					latestRow.appendChild(latestStrong);
					latestRow.appendChild(document.createTextNode(` ${String(meta.latestMessage ?? "").trim()}`));
					detailWrap.appendChild(latestRow);
				}

				const aggregatePayload = meta.aggregatePayload && typeof meta.aggregatePayload === "object" ? meta.aggregatePayload : null;
				const reportPayloads = Array.isArray(aggregatePayload?.reportPayloads) ? aggregatePayload.reportPayloads : [];
				if (reportPayloads.length) {
					const aggregateTitle = document.createElement("div");
					aggregateTitle.className = "qwen-te-preset-card__detail-item";
					aggregateTitle.innerHTML = "<strong>聚合子报告</strong>";
					detailWrap.appendChild(aggregateTitle);
					for (const report of reportPayloads.slice(0, 6)) {
						const aggregate = report?.aggregate ?? {};
						const tone = String(aggregate?.risk?.tone ?? "info");
						const row = document.createElement("div");
						row.className = `qwen-te-preset-card__detail-item qwen-te-preset-card__detail-item--${tone}`;
						const strong = document.createElement("strong");
						strong.textContent = `${formatPresetTime(aggregate?.lastAt)} | ${aggregate?.successRate ?? "待定"} | ${aggregate?.risk?.label ?? "未知"}`;
						row.appendChild(strong);
						row.appendChild(document.createTextNode(`\n${aggregate?.trend?.arrow ?? "→"} ${aggregate?.trend?.label ?? "待观察"} | ${aggregate?.outcomeTrail ?? "·"}\n${aggregate?.lastMessage ?? ""}`));
						detailWrap.appendChild(row);
					}
				}
			}
			}
			if (!filteredPresets.length) {
				const empty = document.createElement("div");
				empty.className = "qwen-te-modal__empty-state";
				empty.textContent = hasAnyPreset ? buildPresetManagerEmptyText(keyword) : "还没有保存过预设。输入名称后点击“保存为预设”，就能把当前标签、参数和智能文本设置存成常用方案。";
				list.appendChild(empty);
			}
			syncBatchSelectionUi(filteredPresets, allPresets);
		};
	for (const key of visiblePresetFilterKeys) {
		const button = document.createElement("button");
		button.className = "qwen-te-modal__preset";
		button.onclick = () => {
			activeSourceFilter = key;
			batchLoadCursor = 0;
			render();
		};
		filterBar.appendChild(button);
		filterButtons.set(key, button);
	}
	const getSelectedPresetIds = () => [...selectedPresetIds];
	const getSelectedPresets = () => {
		const selectedIdSet = new Set(getSelectedPresetIds());
		return getUserPresets().filter((preset) => selectedIdSet.has(String(preset.id ?? "")));
	};
	const getFilteredPresets = () => {
		const allPresets = getUserPresets().filter((preset) => !hiddenPresetSourceKinds.has(String(preset.source ?? "manual")));
		const presets = activeSourceFilter === "all"
			? allPresets
			: activeSourceFilter === "favorites"
				? allPresets.filter((preset) => !!preset.favorite)
				: allPresets.filter((preset) => String(preset.source ?? "manual") === activeSourceFilter);
		const keyword = String(searchInput.value ?? "").trim().toLowerCase();
		const filteredPresets = !keyword
			? presets
			: presets.filter((preset) => buildUserPresetSearchText(preset).includes(keyword));
		filteredPresets.sort((left, right) => {
			const favoriteCompare = Number(!!right.favorite) - Number(!!left.favorite);
			if (favoriteCompare !== 0) return favoriteCompare;
			if (activeSort === "name_asc") {
				return String(left.name ?? "").localeCompare(String(right.name ?? ""), "zh-CN");
			}
			return Number(right.updatedAt ?? 0) - Number(left.updatedAt ?? 0);
		});
		return filteredPresets;
	};
	const getSelectedFilteredPresets = () => {
		const selectedIdSet = new Set(getSelectedPresetIds());
		return getFilteredPresets().filter((preset) => selectedIdSet.has(String(preset.id ?? "")));
	};
	const getContinuousRunCount = () => {
		const value = Number(continuousCountInput.value);
		if (!Number.isFinite(value)) return 3;
		return Math.max(1, Math.min(99, Math.trunc(value)));
	};
		const stopContinuousRun = (message = "已停止连续测试。") => {
			continuousRunToken += 1;
			continuousRunning = false;
			abortOwnedRequest(overlay, "continuous-workflow-history");
			updateNodeContinuousRuntime(node, { token: continuousRunToken, running: false, step: 0 });
			pushContinuousRunReport("停止", message);
			statusEl.textContent = message;
			render();
		};
	const startContinuousPresetRun = async (mode) => {
		const selectedPresets = getSelectedPresets();
		if (!selectedPresets.length) {
			statusEl.textContent = "当前没有可连续测试的已选预设。";
			return;
		}
			const qualityAuditStartAt = Date.now();
			const totalRuns = getContinuousRunCount();
			const token = ++continuousRunToken;
			const targetedPromptIds = [];
			const seenPromptIds = new Set();
			continuousRunning = true;
			continuousRunReport = [];
			setNodeContinuousRunReport(node, continuousRunReport);
			updateNodeContinuousRuntime(node, { token, running: true, mode, step: 0, total: totalRuns });
			pushContinuousRunReport("开始", `连续测试启动：${mode === "cycle" ? "轮流" : "随机"}，共 ${totalRuns} 轮，候选 ${selectedPresets.length} 个预设。`);
			render();
			for (let step = 0; step < totalRuns; step += 1) {
				if (token !== continuousRunToken) return;
				const preset = mode === "cycle"
					? selectedPresets[step % selectedPresets.length]
					: selectedPresets[Math.floor(Math.random() * selectedPresets.length)];
				updateNodeContinuousRuntime(node, { token, running: true, mode, step: step + 1, total: totalRuns });
				const baselineStamp = getNodeExecutionStamp(node);
				statusEl.textContent = `连续测试 ${step + 1}/${totalRuns}：准备提交 ${preset.name}`;
			pushContinuousRunReport("提交", `第 ${step + 1}/${totalRuns} 轮：${preset.name}`);
			const queued = await applyPresetToNode(preset, { queue: true });
			if (token !== continuousRunToken) return;
			if (!queued) {
				pushContinuousRunReport("失败", `第 ${step + 1}/${totalRuns} 轮：${preset.name} 已载入，但未能自动入队。`);
				stopContinuousRun(`连续测试中断：${preset.name} 已载入，但未能自动入队。`);
				return;
			}
			const queueRequestedAt = getNodeWorkflowQueueRequestedAt(node);
			statusEl.textContent = `连续测试 ${step + 1}/${totalRuns}：${preset.name} 已入队，等待执行完成...`;
			pushContinuousRunReport("入队", `第 ${step + 1}/${totalRuns} 轮：${preset.name} 已入队。`);
			const executed = await waitForNodeExecution(node, baselineStamp, 180000, 500, {
				shouldCancel: () => token !== continuousRunToken || !overlay.isConnected,
			});
			if (token !== continuousRunToken) return;
			if (!executed) {
				pushContinuousRunReport("超时", `第 ${step + 1}/${totalRuns} 轮：${preset.name} 等待执行完成超时。`);
				stopContinuousRun(`连续测试超时：${preset.name} 在等待执行完成时超过限制。`);
				return;
			}
			batchLoadCursor = step + 1;
			statusEl.textContent = `连续测试 ${step + 1}/${totalRuns}：${preset.name} 执行完成，正在确认工作流输出...`;
			pushContinuousRunReport("完成", `第 ${step + 1}/${totalRuns} 轮：${preset.name} 执行完成。`);
			const workflowMeta = await waitForNodeContinuousWorkflowOutput(node, {
				createdAfter: queueRequestedAt,
				excludePromptIds: seenPromptIds,
				maxItems: Math.max(24, totalRuns * 6),
				timeoutMs: 180000,
				shouldCancel: () => token !== continuousRunToken,
				requestOwner: overlay,
				requestKey: "continuous-workflow-history",
			});
			if (token !== continuousRunToken) return;
			if (workflowMeta?.promptId) {
				seenPromptIds.add(String(workflowMeta.promptId));
				targetedPromptIds.push(String(workflowMeta.promptId));
				statusEl.textContent = `连续测试 ${step + 1}/${totalRuns}：${preset.name} 已锁定工作流输出 ${workflowMeta.imageCount ?? 0} 张。`;
				pushContinuousRunReport("成图", `第 ${step + 1}/${totalRuns} 轮：${preset.name} 已锁定工作流输出 ${workflowMeta.imageCount ?? 0} 张。`);
			} else {
				statusEl.textContent = `连续测试 ${step + 1}/${totalRuns}：${preset.name} 未定位到对应成图，将回退到最近输出策略。`;
				pushContinuousRunReport("提示", `第 ${step + 1}/${totalRuns} 轮：${preset.name} 未在历史中定位到对应成图，最终质检将回退到最近输出策略。`);
			}
			await sleep(350);
			}
			if (token !== continuousRunToken) return;
			continuousRunning = false;
			updateNodeContinuousRuntime(node, { token, running: false, step: 0, total: totalRuns });
			pushContinuousRunReport("结束", `连续测试完成：共执行 ${totalRuns} 轮${mode === "cycle" ? "（轮流）" : "（随机）"}。`);
			try {
				const audit = await runNodeQualityAudit(
					node,
					targetedPromptIds.length
						? { limit: totalRuns, historyPromptIds: targetedPromptIds, historyWaitTimeoutMs: 0, requestOwner: overlay }
						: { limit: totalRuns, afterTimestamp: qualityAuditStartAt, requestOwner: overlay },
				);
				if (token !== continuousRunToken) return;
				if (audit.ok && audit.summaryText) {
					pushContinuousRunReport("质检", `自动质检完成：${audit.summaryText}`);
				}
			} catch (_error) {}
			if (token !== continuousRunToken) return;
			statusEl.textContent = `连续测试完成：共执行 ${totalRuns} 轮${mode === "cycle" ? "（轮流）" : "（随机）"}。`;
			render();
		};
	const applyPresetToNode = async (preset, options = {}) => {
		if (!preset) return false;
		const result = await applyPresetStateToNode(node, library, preset.state, options);
		library = result.library ?? library;
		return options.queue ? !!result.queued : !!result.ok;
	};
	batchFavoriteButton.onclick = () => {
		let changed = 0;
		for (const id of getSelectedPresetIds()) if (setUserPresetFavorite(id, true)) changed += 1;
		statusEl.textContent = changed ? `已置顶 ${changed} 个预设。` : "所选预设都已经置顶。";
		render();
	};
	batchUnfavoriteButton.onclick = () => {
		let changed = 0;
		for (const id of getSelectedPresetIds()) if (setUserPresetFavorite(id, false)) changed += 1;
		statusEl.textContent = changed ? `已取消置顶 ${changed} 个预设。` : "所选预设都不是置顶状态。";
		render();
	};
	batchDeleteButton.onclick = () => {
		const targetIds = getSelectedPresetIds();
		if (!targetIds.length) {
			statusEl.textContent = "没有删除任何预设。";
			return;
		}
		const confirmed = window.confirm(`将删除已勾选的 ${targetIds.length} 个预设，此操作不可撤销。确定继续吗？`);
		if (!confirmed) {
			statusEl.textContent = "已取消批量删除。";
			return;
		}
		const deletedCount = deleteUserPresets(targetIds);
		selectedPresetIds.clear();
		statusEl.textContent = deletedCount ? `已删除 ${deletedCount} 个预设。` : "没有删除任何预设。";
		render();
	};
	batchLoadButton.onclick = async () => {
		const selectedPresets = getSelectedPresets();
		const preset = selectedPresets[0];
		if (!preset) {
			statusEl.textContent = buildPresetBatchStatus("load_first_empty");
			return;
		}
		await applyPresetToNode(preset);
		batchLoadCursor = 1;
		statusEl.textContent = buildPresetBatchStatus("load_first_ok", { presetName: preset.name });
	};
	batchLoadQueueButton.onclick = async () => {
		const selectedPresets = getSelectedPresets();
		const preset = selectedPresets[0];
		if (!preset) {
			statusEl.textContent = buildPresetBatchStatus("load_first_queue_empty");
			return;
		}
		const queued = await applyPresetToNode(preset, { queue: true });
		batchLoadCursor = 1;
		statusEl.textContent = buildPresetBatchStatus("load_first_queue_ok", { presetName: preset.name, queued });
	};
	batchCycleButton.onclick = async () => {
		const selectedPresets = getSelectedPresets();
		if (!selectedPresets.length) {
			statusEl.textContent = buildPresetBatchStatus("cycle_empty");
			return;
		}
		const index = batchLoadCursor % selectedPresets.length;
		const preset = selectedPresets[index];
		await applyPresetToNode(preset);
		batchLoadCursor = index + 1;
		statusEl.textContent = buildPresetBatchStatus("cycle_ok", { index: index + 1, total: selectedPresets.length, presetName: preset.name });
	};
	batchCycleQueueButton.onclick = async () => {
		const selectedPresets = getSelectedPresets();
		if (!selectedPresets.length) {
			statusEl.textContent = buildPresetBatchStatus("cycle_queue_empty");
			return;
		}
		const index = batchLoadCursor % selectedPresets.length;
		const preset = selectedPresets[index];
		const queued = await applyPresetToNode(preset, { queue: true });
		batchLoadCursor = index + 1;
		statusEl.textContent = buildPresetBatchStatus("cycle_queue_ok", { index: index + 1, total: selectedPresets.length, presetName: preset.name, queued });
	};
	batchRandomLoadButton.onclick = async () => {
		const selectedPresets = getSelectedPresets();
		if (!selectedPresets.length) {
			statusEl.textContent = buildPresetBatchStatus("random_empty");
			return;
		}
		const index = Math.floor(Math.random() * selectedPresets.length);
		const preset = selectedPresets[index];
		await applyPresetToNode(preset);
		batchLoadCursor = index + 1;
		statusEl.textContent = buildPresetBatchStatus("random_ok", { index: index + 1, total: selectedPresets.length, presetName: preset.name });
	};
	batchRandomQueueButton.onclick = async () => {
		const selectedPresets = getSelectedPresets();
		if (!selectedPresets.length) {
			statusEl.textContent = buildPresetBatchStatus("random_queue_empty");
			return;
		}
		const index = Math.floor(Math.random() * selectedPresets.length);
		const preset = selectedPresets[index];
		const queued = await applyPresetToNode(preset, { queue: true });
		batchLoadCursor = index + 1;
		statusEl.textContent = buildPresetBatchStatus("random_queue_ok", { index: index + 1, total: selectedPresets.length, presetName: preset.name, queued });
	};
	continuousCycleButton.onclick = () => { void startContinuousPresetRun("cycle"); };
	continuousRandomButton.onclick = () => { void startContinuousPresetRun("random"); };
	stopContinuousButton.onclick = () => { stopContinuousRun("已手动停止连续测试。"); };
	batchRandomRunButton.onclick = async () => {
		const selectedPresets = getSelectedPresets();
		if (!selectedPresets.length) {
			statusEl.textContent = buildPresetBatchStatus("random_run_empty");
			return;
		}
		const index = Math.floor(Math.random() * selectedPresets.length);
		const preset = selectedPresets[index];
		const queued = await applyPresetToNode(preset, { randomizeAfterLoad: true, queue: true });
		batchLoadCursor = index + 1;
		statusEl.textContent = buildPresetBatchStatus("random_run_ok", { index: index + 1, total: selectedPresets.length, presetName: preset.name, queued });
	};
	exportSelectedButton.onclick = () => {
		const selectedIdSet = new Set(getSelectedPresetIds());
		const selectedPresets = getUserPresets().filter((preset) => selectedIdSet.has(String(preset.id ?? "")));
		if (!selectedPresets.length) {
			statusEl.textContent = buildPresetBatchStatus("export_selected_empty");
			return;
		}
		exportUserPresets(selectedPresets);
		statusEl.textContent = buildPresetBatchStatus("export_selected_ok", { count: selectedPresets.length });
	};
	exportAllButton.onclick = () => {
		const filteredPresets = getFilteredPresets();
		if (!filteredPresets.length) {
			statusEl.textContent = buildPresetBatchStatus("export_visible_empty");
			return;
		}
		exportUserPresets(filteredPresets);
		statusEl.textContent = buildPresetBatchStatus("export_visible_ok", { count: filteredPresets.length });
	};
	exportFavoritesButton.onclick = () => {
		const favoritePresets = getFilteredPresets().filter((preset) => !!preset.favorite);
		if (!favoritePresets.length) {
			statusEl.textContent = buildPresetBatchStatus("export_favorites_empty");
			return;
		}
		exportUserPresets(favoritePresets);
		statusEl.textContent = buildPresetBatchStatus("export_favorites_ok", { count: favoritePresets.length });
	};
	exportArrangeButton.onclick = () => {
		const arrangePresets = getFilteredPresets().filter((preset) => String(preset.source ?? "manual") === "arrange-preview");
		if (!arrangePresets.length) {
			statusEl.textContent = buildPresetBatchStatus("export_arrange_empty");
			return;
		}
		exportUserPresets(arrangePresets);
		statusEl.textContent = buildPresetBatchStatus("export_arrange_ok", { count: arrangePresets.length });
	};
	exportHistoryAggregateButton.onclick = () => {
		const historyAggregatePresets = getFilteredPresets().filter((preset) => String(preset.source ?? "manual") === "history-aggregate");
		if (!historyAggregatePresets.length) {
			statusEl.textContent = buildPresetBatchStatus("export_history_aggregate_empty");
			return;
		}
		exportUserPresets(historyAggregatePresets);
		statusEl.textContent = buildPresetBatchStatus("export_history_aggregate_ok", { count: historyAggregatePresets.length });
	};
	exportManualButton.onclick = () => {
		const manualPresets = getFilteredPresets().filter((preset) => String(preset.source ?? "manual") === "manual");
		if (!manualPresets.length) {
			statusEl.textContent = buildPresetBatchStatus("export_manual_empty");
			return;
		}
		exportUserPresets(manualPresets);
		statusEl.textContent = buildPresetBatchStatus("export_manual_ok", { count: manualPresets.length });
	};
	importButton.onclick = () => fileInput.click();
	quickImportButton.onclick = () => fileInput.click();
	clearSelectionButton.onclick = () => {
		selectedPresetIds.clear();
		statusEl.textContent = "已清空预设勾选。";
		persistPresetBatchState();
		render();
	};
	for (const option of sortOptions) {
		const selectOption = document.createElement("option");
		selectOption.value = option.key;
		selectOption.textContent = option.label;
		sortSelect.appendChild(selectOption);
	}
	sortSelect.value = activeSort;
	sortSelect.addEventListener("change", () => {
		activeSort = String(sortSelect.value ?? "updated_desc");
		batchLoadCursor = 0;
		render();
	});
	continuousCountInput.addEventListener("input", () => {
		persistPresetBatchState();
	});
	fileInput.onchange = async () => {
		const file = fileInput.files?.[0];
		fileInput.value = "";
		if (!file) return;
		try {
			const result = await importUserPresetFile(file);
			statusEl.textContent = result.message;
			render();
		} catch (error) {
			statusEl.textContent = `导入预设失败：${error.message}`;
		}
	};
	reportCopyButton.onclick = () => {
		const text = buildContinuousRunReportText();
		if (!text) {
			reportStatus.textContent = "当前没有可复制的连续测试报告。";
			return;
		}
		void copyToClipboard(text).then((ok) => {
			reportStatus.textContent = ok ? "已复制连续测试报告。" : "复制失败，浏览器可能阻止了剪贴板访问。";
		});
	};
	reportExportButton.onclick = () => {
		if (!exportContinuousRunReport()) {
			reportStatus.textContent = "当前没有可导出的连续测试报告。";
			return;
		}
		reportStatus.textContent = "已导出连续测试报告。";
	};
	reportExportCsvButton.onclick = () => {
		const text = buildContinuousRunReportCsv();
		if (!exportTextFile(text, `qwen-te-continuous-report-${buildCompactTimestamp()}.csv`, "text/csv;charset=utf-8")) {
			reportStatus.textContent = "当前没有可导出的 CSV 报告。";
			return;
		}
		reportStatus.textContent = "已导出 CSV 连续测试报告。";
	};
	reportExportMarkdownButton.onclick = () => {
		const text = buildContinuousRunReportMarkdown();
		if (!exportTextFile(text, `qwen-te-continuous-report-${buildCompactTimestamp()}.md`, "text/markdown;charset=utf-8")) {
			reportStatus.textContent = "当前没有可导出的 Markdown 报告。";
			return;
		}
		reportStatus.textContent = "已导出 Markdown 连续测试报告。";
	};
	reportSaveHistoryButton.onclick = () => {
		if (!continuousRunReport.length) {
			reportStatus.textContent = "当前没有可存入历史的连续测试报告。";
			return;
		}
		recordNodeHistory(
			node,
			collectNodeState(node, library),
			"continuous-report",
			{
				dedupe: true,
				summary: buildContinuousRunHistorySummary(),
				meta: { qualityAudit: buildQualityAuditHistoryMeta(node) },
			},
		);
		reportStatus.textContent = "已将连续测试报告存入历史。";
	};
	reportClearButton.onclick = () => {
		if (continuousRunReport.length) {
			const confirmed = window.confirm(`将清空当前 ${continuousRunReport.length} 条连续测试事件，确定继续吗？`);
			if (!confirmed) {
				reportStatus.textContent = "已取消清空连续测试报告。";
				return;
			}
		}
		continuousRunReport = [];
		clearNodeContinuousRunReport(node);
		clearNodeContinuousReportMeta(node);
		reportStatus.textContent = "已清空连续测试报告。";
		refreshNodeSummary(node, library);
		renderContinuousRunReport();
	};
	searchInput.addEventListener("input", () => {
		batchLoadCursor = 0;
		render();
	});
	saveButton.onclick = () => { const presetName = nameInput.value.trim(); if(!presetName){ statusEl.textContent="先输入一个预设名称。"; return; } const saved=saveUserPreset(presetName, collectNodeState(node, library), { source: "manual" }); if(!saved){ statusEl.textContent="保存预设失败：内容过大或浏览器本地存储空间不足。"; return; } nameInput.value = ""; statusEl.textContent=`已保存为常用预设：${presetName}`; render(); };
	overlay.__qwenDispose = () => stopContinuousRun("已关闭预设管理器，连续测试已停止。");
	const closePresetManager = () => disposeModalOverlay(overlay);
	doneButton.onclick = closePresetManager;
	closeButton.onclick = closePresetManager;
	overlay.addEventListener("click", (event) => { if(event.target===overlay) closePresetManager(); });
	document.body.appendChild(overlay); render(); renderContinuousRunReport(); searchInput.focus();
}

function openHistoryPromptViewDialog(node, item) {
	ensureSingleModal("history-prompt-view");
	const resolvedStageOutput = resolveHistoryPromptViewStageOutput(node, item);
	const stageOutput = resolvedStageOutput.stageOutput;
	const hasGeneratedPrompt = hasUsableStageOutputSnapshot(stageOutput);
	const viewText = buildHistoryPromptViewText(item, stageOutput);
	const sourceLabel = getHistorySourceLabel(item?.source);
	const promptStateText = resolvedStageOutput.sourceKey === "own"
		? "已保存完整生成提示词"
		: resolvedStageOutput.sourceKey === "related"
			? "已关联同状态生成提示词"
			: resolvedStageOutput.sourceKey === "live"
				? "已读取当前终端真实输出"
				: "仅保存标签状态摘要";
	const overlay = document.createElement("div");
	overlay.className = "qwen-te-modal";
	overlay.dataset.qwenModal = "history-prompt-view";
	overlay.__qwenNode = node;
	const dialog = document.createElement("div");
	dialog.className = "qwen-te-modal__dialog";
	overlay.appendChild(dialog);

	const header = document.createElement("div");
	header.className = "qwen-te-modal__header";
	dialog.appendChild(header);
	const titleWrap = document.createElement("div");
	header.appendChild(titleWrap);
	const title = document.createElement("div");
	title.className = "qwen-te-modal__title";
	title.textContent = `查看提示词 · ${sourceLabel}`;
	titleWrap.appendChild(title);
	const subtitle = document.createElement("div");
	subtitle.className = "qwen-te-modal__subtitle";
	subtitle.textContent = `${formatPresetTime(item?.updatedAt)} · ${promptStateText}`;
	titleWrap.appendChild(subtitle);
	const closeButton = document.createElement("button");
	closeButton.className = "qwen-te-modal__footer-button";
	closeButton.textContent = "关闭";
	header.appendChild(closeButton);

	const body = document.createElement("div");
	body.className = "qwen-te-modal__body qwen-te-modal__stage-output-body";
	dialog.appendChild(body);
	const statusEl = document.createElement("div");
	statusEl.className = "qwen-te-modal__status";
	statusEl.textContent = resolvedStageOutput.sourceKey === "own"
		? "这里显示这条历史保存的完整提示词，可复制或载入终端预览。"
		: resolvedStageOutput.sourceKey === "related"
			? "这条历史已关联到同状态运行输出，可复制或载入终端预览。"
			: resolvedStageOutput.sourceKey === "live"
				? "这条历史本身没有完整输出，已从当前节点/下游文本节点读取真实提示词。"
				: "这条历史没有完整生成输出，下面显示当时保存的标签状态。";
	body.appendChild(statusEl);
	const screen = document.createElement("div");
	screen.className = `qwen-te-modal__stage-output-screen${hasGeneratedPrompt ? "" : " is-empty"}`;
	screen.textContent = viewText || "这条历史没有可显示内容。";
	body.appendChild(screen);

	const footer = document.createElement("div");
	footer.className = "qwen-te-modal__footer";
	dialog.appendChild(footer);
	const copyButton = document.createElement("button");
	copyButton.className = "qwen-te-modal__footer-button qwen-te-modal__footer-button--primary";
	copyButton.textContent = "复制内容";
	footer.appendChild(copyButton);
	const loadPreviewButton = document.createElement("button");
	loadPreviewButton.className = "qwen-te-modal__footer-button";
	loadPreviewButton.textContent = "载入终端预览";
	loadPreviewButton.disabled = !hasGeneratedPrompt;
	loadPreviewButton.style.opacity = hasGeneratedPrompt ? "1" : "0.55";
	loadPreviewButton.style.cursor = hasGeneratedPrompt ? "pointer" : "not-allowed";
	footer.appendChild(loadPreviewButton);
	const doneButton = document.createElement("button");
	doneButton.className = "qwen-te-modal__footer-button";
	doneButton.textContent = "完成";
	footer.appendChild(doneButton);

	copyButton.onclick = async () => {
		const ok = await copyToClipboard(viewText);
		statusEl.textContent = ok ? "已复制这条历史的提示词内容。" : "复制失败，浏览器可能阻止了剪贴板访问。";
	};
	loadPreviewButton.onclick = () => {
		if (!stageOutput) {
			statusEl.textContent = "这条历史没有完整生成提示词，无法载入终端预览。";
			return;
		}
		const loaded = setStageDisplayPreview(node, stageOutput, `历史预览 · ${sourceLabel}`);
		statusEl.textContent = loaded ? "已载入到节点终端预览。" : "当前节点面板还未初始化，暂时无法载入终端预览。";
	};
	const close = () => overlay.remove();
	doneButton.onclick = close;
	closeButton.onclick = close;
	overlay.addEventListener("click", (event) => { if (event.target === overlay) close(); });
	document.body.appendChild(overlay);
	return overlay;
}

function openHistoryManager(node, library) {
	ensureSingleModal("history-manager");
	const modalContext = buildNodeModalContext(node, library);
	const overlay=document.createElement("div"); overlay.className="qwen-te-modal";
	overlay.dataset.qwenModal = "history-manager";
	overlay.__qwenNode = node;
	const dialog=document.createElement("div"); dialog.className="qwen-te-modal__dialog"; overlay.appendChild(dialog);
	const header=document.createElement("div"); header.className="qwen-te-modal__header"; dialog.appendChild(header);
	const titleWrap=document.createElement("div"); header.appendChild(titleWrap);
	const title=document.createElement("div"); title.className="qwen-te-modal__title"; title.textContent=`节点历史 · ${modalContext.nodeName}`; titleWrap.appendChild(title);
	const subtitle=document.createElement("div"); subtitle.className="qwen-te-modal__subtitle"; subtitle.textContent=`查看、恢复最近生成记录。当前输出来源：${modalContext.outputSource}。`; titleWrap.appendChild(subtitle);
	const closeButton=document.createElement("button"); closeButton.className="qwen-te-modal__footer-button"; closeButton.textContent="关闭"; header.appendChild(closeButton);
	const body=document.createElement("div"); body.className="qwen-te-modal__body"; dialog.appendChild(body);
	const statusEl=document.createElement("div"); statusEl.className="qwen-te-modal__status"; statusEl.textContent=`历史保存本节点状态与最近输出，可恢复、复制或删除。当前已选标签 ${modalContext.tagCount} 个。`; body.appendChild(statusEl);
	const historyTools = document.createElement("details"); historyTools.className="qwen-te-modal__details"; body.appendChild(historyTools);
	const historyToolsSummary = document.createElement("summary"); historyToolsSummary.className="qwen-te-modal__details-summary"; historyToolsSummary.textContent = "历史工具（可选）"; historyTools.appendChild(historyToolsSummary);
	const toolbar=document.createElement("div"); toolbar.className="qwen-te-modal__toolbar"; historyTools.appendChild(toolbar);
	const exportButton=document.createElement("button"); exportButton.className="qwen-te-modal__footer-button"; exportButton.textContent="导出"; toolbar.appendChild(exportButton);
	const importButton=document.createElement("button"); importButton.className="qwen-te-modal__footer-button"; importButton.textContent="导入"; toolbar.appendChild(importButton);
	const filterBar=document.createElement("div"); filterBar.className="qwen-te-modal__pillbar"; body.appendChild(filterBar);
	const searchToolbar=document.createElement("div"); searchToolbar.className="qwen-te-modal__toolbar"; body.appendChild(searchToolbar);
	const searchInput=document.createElement("input"); searchInput.className="qwen-te-modal__search"; searchInput.placeholder="搜索来源 / 摘要 / 标签 / 提示词"; searchToolbar.appendChild(searchInput);
	const sortSelect=document.createElement("select"); sortSelect.className="qwen-te-modal__search"; searchToolbar.appendChild(sortSelect);
	const clearAllButton=document.createElement("button"); clearAllButton.className="qwen-te-modal__footer-button qwen-te-modal__footer-button--danger"; clearAllButton.textContent="一键删除历史"; clearAllButton.title="删除本节点全部历史记录，包括置顶项。"; searchToolbar.appendChild(clearAllButton);
	const guideEl=document.createElement("div"); guideEl.className="qwen-te-modal__status"; guideEl.textContent="只显示可恢复的最近记录，可按来源、搜索与时间排序。"; body.appendChild(guideEl);
	const fileInput=document.createElement("input"); fileInput.type="file"; fileInput.accept="application/json,.json"; fileInput.style.display="none"; dialog.appendChild(fileInput);
	const list=document.createElement("div"); list.className="qwen-te-preset-list"; body.appendChild(list);
	const footer=document.createElement("div"); footer.className="qwen-te-modal__footer"; dialog.appendChild(footer);
	const doneButton=document.createElement("button"); doneButton.className="qwen-te-modal__footer-button"; doneButton.textContent="完成"; footer.appendChild(doneButton);
	const sourceFilters = [
		{ key: "all", label: "全部" },
		{ key: "random", label: "随机结果" },
		{ key: "executed", label: "运行结果" },
		{ key: "arrange-preview", label: "整理预览" },
	];
	const hiddenHistorySourceKinds = new Set([
		"continuous-report",
		"single-preset-report",
		"history-aggregate-report",
		"single-preset",
	]);
	const sortOptions = [
		{ key: "updated_desc", label: "最新在前" },
		{ key: "updated_asc", label: "最早在前" },
	];
	let activeSourceFilter = "all";
	let activeSort = "updated_desc";
	const filterButtons = new Map();
	const expandedHistoryIds = new Set();
	const setActiveFilterButton = () => {
		for (const [key, button] of filterButtons.entries()) {
			const active = key === activeSourceFilter;
			button.style.borderColor = active ? "#caa55b" : "#525252";
			button.style.background = active ? "#59451a" : "#232323";
			button.style.color = active ? "#fff0ca" : "#f7f7f7";
		}
	};
	const buildHistoryGuideText = (historyCount, keyword) => {
		const base = keyword ? `当前搜索：${keyword}` : `当前显示 ${historyCount} 条历史记录。`;
		return `${base} 可恢复、查看提示词、置顶或删除。`;
	};
	const buildHistoryQualitySummaryText = () => "";
	const buildHistoryEmptyText = (keyword) => {
		if (keyword) return "当前筛选和搜索下没有匹配的历史记录。";
		if (activeSourceFilter === "all") return "还没有节点历史。";
		return `当前筛选下没有“${getHistorySourceLabel(activeSourceFilter)}”记录。`;
	};
	for (const option of sortOptions) {
		const selectOption = document.createElement("option");
		selectOption.value = option.key;
		selectOption.textContent = option.label;
		sortSelect.appendChild(selectOption);
	}
	sortSelect.value = activeSort;
	const historyMatchesKeyword = (item, keyword) => {
		if (!keyword) return true;
		const reportPayload = getHistoryReportPayload(item);
		const reportAggregate = getHistoryReportAggregate(item);
		const stageOutput = getHistoryStageOutput(item) ?? findRelatedHistoryStageOutput(node, item);
		const haystack = [
			getHistorySourceLabel(item?.source),
			item?.summary,
			stageOutput?.promptText,
			stageOutput?.smartText,
			stageOutput?.negativePrompt,
			stageOutput?.selectedTags,
			stageOutput?.fullText,
			reportAggregate?.presetName,
			reportAggregate?.successRate,
			reportAggregate?.risk?.label,
			reportAggregate?.trend?.label,
			reportAggregate?.outcomeTrail,
			reportAggregate?.lastMessage,
			...(Array.isArray(reportPayload?.entries) ? reportPayload.entries.slice(0, 8).map((entry) => `${entry?.level ?? ""} ${entry?.message ?? ""}`) : []),
		].filter(Boolean).join(" ").toLowerCase();
		return haystack.includes(keyword);
	};
	const render = () => {
		const allHistory = getSortedNodeHistory(node).filter((item) => !hiddenHistorySourceKinds.has(String(item?.source ?? "")));
		const keyword = String(searchInput.value ?? "").trim().toLowerCase();
		const sourceFiltered = activeSourceFilter === "all"
			? allHistory
			: allHistory.filter((item) => item.source === activeSourceFilter);
		const history = (!keyword
			? sourceFiltered
			: sourceFiltered.filter((item) => historyMatchesKeyword(item, keyword)))
			.sort((left, right) => {
				const favoriteDiff = (+!!right.favorite) - (+!!left.favorite);
				if (favoriteDiff !== 0) return favoriteDiff;
				if (activeSort === "updated_asc") return Number(left.updatedAt ?? 0) - Number(right.updatedAt ?? 0);
				return Number(right.updatedAt ?? 0) - Number(left.updatedAt ?? 0);
			});
		list.replaceChildren();
		setActiveFilterButton();
		guideEl.textContent = buildHistoryGuideText(history.length, keyword);
		const totalHistoryCount = getNodeHistory(node).length;
		clearAllButton.disabled = totalHistoryCount <= 0;
		clearAllButton.style.opacity = totalHistoryCount <= 0 ? "0.5" : "1";
		clearAllButton.style.cursor = totalHistoryCount <= 0 ? "not-allowed" : "pointer";
		if (!history.length) {
			const empty = document.createElement("div");
			empty.className = "qwen-te-preset-card__summary";
			empty.textContent = buildHistoryEmptyText(keyword);
			list.appendChild(empty);
			return;
		}
		for (const item of history) {
			const card = document.createElement("div");
			card.className = "qwen-te-preset-card";
			list.appendChild(card);

			const head = document.createElement("div");
			head.className = "qwen-te-preset-card__header";
			card.appendChild(head);

			const name = document.createElement("div");
			name.className = "qwen-te-preset-card__name";
			name.textContent = `${item.favorite ? "★ " : ""}${getHistorySourceLabel(item.source)}`;
			head.appendChild(name);

			const time = document.createElement("div");
			time.className = "qwen-te-preset-card__time";
			time.textContent = formatPresetTime(item.updatedAt);
			head.appendChild(time);

			const ownStageOutput = getHistoryStageOutput(item);
			const stageOutput = ownStageOutput ?? findRelatedHistoryStageOutput(node, item);
			const hasStageOutput = !!stageOutput;
			const displayItem = ownStageOutput || !stageOutput
				? item
				: { ...item, meta: { ...(item?.meta ?? {}), stageOutput } };

			const summary = document.createElement("div");
			summary.className = "qwen-te-preset-card__summary";
			const qualitySummary = buildHistoryQualitySummaryText(item);
			const summaryText = buildHistoryDisplaySummaryText(displayItem);
			summary.textContent = qualitySummary
				? `${summaryText}\n质检：${qualitySummary}`
				: summaryText;
			card.appendChild(summary);

			const reportPayload = getHistoryReportPayload(item);
			const reportAggregate = getHistoryReportAggregate(item);
			const reportPreset = reportPayload ? resolvePresetFromHistoryReport(item) : null;
			const isAggregateHistoryReport = item.source === "history-aggregate-report" || Array.isArray(reportPayload?.reportPayloads);
			const reportLabel = getHistorySourceLabel(item.source);
			const expanded = expandedHistoryIds.has(String(item.id ?? ""));
			let badgeBar = null;
			if (reportAggregate) {
				const cardTone = mergeContinuousRunTones(
					reportAggregate?.state?.tone ?? "info",
					reportAggregate?.trend?.tone ?? "info",
					reportAggregate?.risk?.tone ?? "info",
				);
				card.className = `qwen-te-preset-card qwen-te-preset-card--${cardTone}${expanded ? " qwen-te-preset-card--expanded" : ""}`;

				const reportSummary = document.createElement("div");
				reportSummary.className = "qwen-te-preset-card__summary";
				reportSummary.textContent = `${reportAggregate.presetName} | 成功率 ${reportAggregate.successRate} | 风险 ${reportAggregate.risk?.label ?? "未知"} | 最近结果 ${reportAggregate.outcomeTrail ?? "·"}`;
				card.appendChild(reportSummary);

				badgeBar = document.createElement("div");
				badgeBar.className = "qwen-te-preset-card__badges";
				card.appendChild(badgeBar);

				const successBadge = document.createElement("div");
				successBadge.className = `qwen-te-preset-card__badge qwen-te-preset-card__badge--${cardTone}`;
				successBadge.textContent = `成功率 ${reportAggregate.successRate ?? "待定"}`;
				badgeBar.appendChild(successBadge);

				const trendBadge = document.createElement("div");
				trendBadge.className = `qwen-te-preset-card__badge qwen-te-preset-card__badge--${reportAggregate?.trend?.tone ?? "info"}`;
				trendBadge.textContent = `趋势 ${reportAggregate?.trend?.arrow ?? "→"} ${reportAggregate?.trend?.label ?? "待观察"}`;
				badgeBar.appendChild(trendBadge);

				const riskBadge = document.createElement("div");
				riskBadge.className = `qwen-te-preset-card__badge qwen-te-preset-card__badge--${reportAggregate?.risk?.tone ?? "info"}`;
				riskBadge.textContent = `风险 ${reportAggregate?.risk?.label ?? "未知"}`;
				badgeBar.appendChild(riskBadge);

				const trailBadge = document.createElement("div");
				trailBadge.className = "qwen-te-preset-card__badge qwen-te-preset-card__badge--info";
				trailBadge.textContent = `结果 ${reportAggregate?.outcomeTrail ?? "·"}`;
				badgeBar.appendChild(trailBadge);
			}
			const qualityBadgeText = buildHistoryQualitySummaryText(item);
			if (qualityBadgeText) {
				const qualityBadge = document.createElement("div");
				qualityBadge.className = "qwen-te-preset-card__badge qwen-te-preset-card__badge--info";
				qualityBadge.textContent = `质检 ${qualityBadgeText}`;
				(badgeBar ?? card).appendChild(qualityBadge);
			}
			if (hasStageOutput) {
				const promptBadge = document.createElement("div");
				promptBadge.className = "qwen-te-preset-card__badge qwen-te-preset-card__badge--success";
				promptBadge.textContent = "已保存提示词";
				(badgeBar ?? card).appendChild(promptBadge);
			}

			const actions = document.createElement("div");
			actions.className = "qwen-te-preset-card__action-row qwen-te-preset-card__action-row--primary";
			card.appendChild(actions);

			const viewPrompt = document.createElement("button");
			viewPrompt.className = "qwen-te-modal__footer-button qwen-te-modal__footer-button--primary";
			viewPrompt.textContent = "查看";
			viewPrompt.onclick = () => {
				openHistoryPromptViewDialog(node, displayItem);
				statusEl.textContent = hasStageOutput ? "已打开这条历史保存的完整提示词。" : "已打开这条历史的标签状态摘要。";
			};
			actions.appendChild(viewPrompt);

			const restore = document.createElement("button");
			restore.className = "qwen-te-modal__footer-button";
			restore.textContent = "恢复";
			restore.onclick = async () => {
				const mutationRevision = beginNodeStateMutation(node);
				const nextLibrary = await getFreshLibraryForUi(node, library, { mutationRevision });
				if (!isNodeStateMutationCurrent(node, mutationRevision)) return;
				library = nextLibrary;
				if (!applyNodeState(node, nextLibrary, clonePresetState(item.state), { recordHistory: true, historySource: "history-load", mutationRevision })) return;
				if (stageOutput) setStageDisplayPreview(node, stageOutput, `历史预览 · ${getHistorySourceLabel(item.source)}`);
				statusEl.textContent = `已恢复：${getHistorySourceLabel(item.source)}`;
				render();
			};
			actions.appendChild(restore);

			if (hasStageOutput) {
				const copyStagePrompt = document.createElement("button");
				copyStagePrompt.className = "qwen-te-modal__footer-button";
				copyStagePrompt.textContent = "复制正向";
				copyStagePrompt.onclick = async () => {
					const ok = await copyToClipboard(stageOutput?.promptText ?? "");
					statusEl.textContent = ok ? "已复制该次历史正向提示词。" : "这条历史里没有可复制的正向提示词。";
				};
				actions.appendChild(copyStagePrompt);

				const copyStageAll = document.createElement("button");
				copyStageAll.className = "qwen-te-modal__footer-button";
				copyStageAll.textContent = "复制全部";
				copyStageAll.onclick = async () => {
					const ok = await copyToClipboard(buildHistoryStageOutputText(stageOutput));
					statusEl.textContent = ok ? "已复制该次历史提示词、负面词与标签摘要。" : "这条历史里没有可复制的提示词内容。";
				};
				actions.appendChild(copyStageAll);
			}

			if (reportPayload) {
				const toggleDetail = document.createElement("button");
				toggleDetail.className = "qwen-te-modal__footer-button";
				toggleDetail.textContent = expanded ? "收起详情" : "展开详情";
				toggleDetail.onclick = () => {
					const id = String(item.id ?? "");
					if (!id) return;
					if (expandedHistoryIds.has(id)) expandedHistoryIds.delete(id);
					else expandedHistoryIds.add(id);
					render();
				};
				actions.appendChild(toggleDetail);

				const addBatch = document.createElement("button");
				addBatch.className = "qwen-te-modal__footer-button";
				addBatch.textContent = "加入连测";
				addBatch.classList.add("qwen-te-hidden");
				addBatch.setAttribute("aria-hidden", "true");
				addBatch.tabIndex = -1;
				addBatch.onclick = () => {
					const ensured = ensurePresetForHistoryReport(item);
					if (!ensured.preset) {
						statusEl.textContent = `无法为${reportLabel}创建可用快照。`;
						return;
					}
					const result = addPresetToNodeBatchState(node, ensured.preset.id);
					refreshNodeSummary(node, library);
					statusEl.textContent = ensured.created
						? `已基于${reportLabel}创建快照并加入连测批次：${ensured.preset.name}`
						: result.changed
							? `已将${reportLabel}预设加入连测批次：${ensured.preset.name}`
							: `该${reportLabel}预设已在连测批次中：${ensured.preset.name}`;
					render();
				};
				actions.appendChild(addBatch);

				const setExclusive = document.createElement("button");
				setExclusive.className = "qwen-te-modal__footer-button";
				setExclusive.textContent = "唯一连测";
				setExclusive.classList.add("qwen-te-hidden");
				setExclusive.setAttribute("aria-hidden", "true");
				setExclusive.tabIndex = -1;
				setExclusive.onclick = () => {
					const ensured = ensurePresetForHistoryReport(item);
					if (!ensured.preset) {
						statusEl.textContent = `无法为${reportLabel}创建可用快照。`;
						return;
					}
					const result = setExclusivePresetBatchState(node, ensured.preset.id);
					refreshNodeSummary(node, library);
					statusEl.textContent = ensured.created
						? `已基于${reportLabel}创建快照并设为唯一连测批次：${ensured.preset.name}`
						: result.changed
							? `已将${reportLabel}预设设为唯一连测批次：${ensured.preset.name}`
							: `当前已是该${reportLabel}预设的唯一连测批次：${ensured.preset.name}`;
					render();
				};
				actions.appendChild(setExclusive);

				const runExclusive = document.createElement("button");
				runExclusive.className = "qwen-te-modal__footer-button";
				runExclusive.textContent = "唯一并开跑";
				runExclusive.classList.add("qwen-te-hidden");
				runExclusive.setAttribute("aria-hidden", "true");
				runExclusive.tabIndex = -1;
				runExclusive.onclick = async () => {
					const mutationRevision = beginNodeStateMutation(node);
					const ensured = ensurePresetForHistoryReport(item);
					if (!ensured.preset) {
						statusEl.textContent = `无法为${reportLabel}创建可用快照。`;
						return;
					}
					const nextLibrary = await getFreshLibraryForUi(node, library, { mutationRevision });
					if (!isNodeStateMutationCurrent(node, mutationRevision)) return;
					library = nextLibrary;
					setExclusivePresetBatchState(node, ensured.preset.id);
					refreshNodeSummary(node, nextLibrary);
					statusEl.textContent = ensured.created
						? `已基于${reportLabel}创建快照并准备启动连测：${ensured.preset.name}`
						: `已将${reportLabel}预设设为唯一批次，准备启动连测：${ensured.preset.name}`;
					await startNodeContinuousPresetRun(node, nextLibrary, "cycle");
					render();
				};
				actions.appendChild(runExclusive);

				const restoreAndRun = document.createElement("button");
				restoreAndRun.className = "qwen-te-modal__footer-button";
				restoreAndRun.textContent = "恢复并开跑";
				restoreAndRun.onclick = async () => {
					const mutationRevision = beginNodeStateMutation(node);
					const nextLibrary = await getFreshLibraryForUi(node, library, { mutationRevision });
					if (!isNodeStateMutationCurrent(node, mutationRevision)) return;
					library = nextLibrary;
					if (!applyNodeState(node, nextLibrary, clonePresetState(item.state), { recordHistory: true, historySource: "history-load", mutationRevision })) return;
					const queued = await queueWorkflowFromNode(node);
					if (!isNodeStateMutationCurrent(node, mutationRevision)) return;
					statusEl.textContent = queued
						? `已恢复${reportLabel}并加入队列：${reportAggregate?.presetName ?? "目标预设"}`
						: `已恢复${reportLabel}，但未能自动入队：${reportAggregate?.presetName ?? "目标预设"}`;
					render();
				};
				actions.appendChild(restoreAndRun);

				if (isAggregateHistoryReport) {
					const copySummary = document.createElement("button");
					copySummary.className = "qwen-te-modal__footer-button";
					copySummary.textContent = "复制摘要";
					copySummary.onclick = async () => {
						const text = buildHistoryPresetAggregateText(reportPayload);
						const ok = await copyToClipboard(text);
						statusEl.textContent = buildHistoryReportActionStatus("copy_summary", reportLabel, ok, reportAggregate?.presetName);
					};
					actions.appendChild(copySummary);

					const saveSnapshot = document.createElement("button");
					saveSnapshot.className = "qwen-te-modal__footer-button";
					saveSnapshot.textContent = "存为快照";
					saveSnapshot.onclick = () => {
						const snapshotName = buildHistoryAggregateSnapshotName(reportPayload);
						const ok = saveUserPreset(snapshotName, item.state, {
							source: "history-aggregate",
							meta: buildHistoryAggregateSnapshotMeta(reportPayload),
						});
						statusEl.textContent = ok ? `已将${reportLabel}存为快照：${snapshotName}` : `保存${reportLabel}快照失败。`;
					};
					actions.appendChild(saveSnapshot);

					const copyJson = document.createElement("button");
					copyJson.className = "qwen-te-modal__footer-button";
					copyJson.textContent = "复制 JSON";
					copyJson.onclick = async () => {
						const text = JSON.stringify(reportPayload, null, 2);
						const ok = await copyToClipboard(text);
						statusEl.textContent = buildHistoryReportActionStatus("copy_json", reportLabel, ok, reportAggregate?.presetName);
					};
					actions.appendChild(copyJson);

					const exportMarkdown = document.createElement("button");
					exportMarkdown.className = "qwen-te-modal__footer-button";
					exportMarkdown.textContent = "导出 Markdown";
					exportMarkdown.onclick = () => {
						const text = buildHistoryPresetAggregateMarkdown(reportPayload);
						const filename = `qwen-te-history-aggregate-report-${buildCompactTimestamp(item.updatedAt)}.md`;
						const ok = exportTextFile(text, filename, "text/markdown;charset=utf-8");
						statusEl.textContent = buildHistoryReportActionStatus("export_markdown", reportLabel, ok, reportAggregate?.presetName);
					};
					actions.appendChild(exportMarkdown);

					const exportCsv = document.createElement("button");
					exportCsv.className = "qwen-te-modal__footer-button";
					exportCsv.textContent = "导出 CSV";
					exportCsv.onclick = () => {
						const text = buildHistoryPresetAggregateCsv(reportPayload);
						const filename = `qwen-te-history-aggregate-report-${buildCompactTimestamp(item.updatedAt)}.csv`;
						const ok = exportTextFile(text, filename, "text/csv;charset=utf-8");
						statusEl.textContent = buildHistoryReportActionStatus("export_csv", reportLabel, ok, reportAggregate?.presetName);
					};
					actions.appendChild(exportCsv);
				}

				const copyReport = document.createElement("button");
				copyReport.className = "qwen-te-modal__footer-button";
				copyReport.textContent = "复制 JSON";
				copyReport.onclick = async () => {
					const text = JSON.stringify(reportPayload, null, 2);
					const ok = await copyToClipboard(text);
					statusEl.textContent = buildHistoryReportActionStatus("copy_json", reportLabel, ok, reportAggregate?.presetName);
				};
				actions.appendChild(copyReport);

				const exportReport = document.createElement("button");
				exportReport.className = "qwen-te-modal__footer-button";
				exportReport.textContent = "导出报告";
				exportReport.onclick = () => {
					const text = JSON.stringify(reportPayload, null, 2);
					const filename = `${item.source === "history-aggregate-report" ? "qwen-te-history-aggregate-history" : "qwen-te-single-preset-history"}-${buildCompactTimestamp(item.updatedAt)}.json`;
					const ok = exportTextFile(text, filename, "application/json");
					statusEl.textContent = buildHistoryReportActionStatus("export_json", reportLabel, ok, reportAggregate?.presetName);
				};
				actions.appendChild(exportReport);
			}

			const favorite = document.createElement("button");
			favorite.className = "qwen-te-modal__footer-button";
			favorite.textContent = item.favorite ? "取消置顶" : "置顶";
			favorite.onclick = () => {
				toggleNodeHistoryFavorite(node, item.id);
				statusEl.textContent = item.favorite ? "已取消置顶该历史。" : "已置顶该历史。";
				render();
			};
			actions.appendChild(favorite);

			const del = document.createElement("button");
			del.className = "qwen-te-modal__footer-button";
			del.textContent = "删除";
			del.onclick = () => {
				const confirmed = window.confirm("将删除这条历史记录，确定继续吗？");
				if (!confirmed) {
					statusEl.textContent = "已取消删除历史。";
					return;
				}
				deleteNodeHistoryItem(node, item.id);
				expandedHistoryIds.delete(String(item.id ?? ""));
				statusEl.textContent = "已删除该条历史。";
				render();
			};
			actions.appendChild(del);

			if ((reportPayload && expanded) || (hasStageOutput && expanded) || (qualitySummary && !reportPayload)) {
				const detailWrap = document.createElement("div");
				detailWrap.className = "qwen-te-preset-card__detail";
				card.appendChild(detailWrap);
				const qualitySummaryText = buildHistoryQualitySummaryText(item);
				if (qualitySummaryText) {
					const qualityRow = document.createElement("div");
					qualityRow.className = "qwen-te-preset-card__detail-item qwen-te-preset-card__detail-item--info";
					const qualityStrong = document.createElement("strong");
					qualityStrong.textContent = "质检摘要";
					qualityRow.appendChild(qualityStrong);
					qualityRow.appendChild(document.createTextNode(` ${qualitySummaryText}`));
					detailWrap.appendChild(qualityRow);
				}

				if (hasStageOutput && expanded) {
					const promptTitle = document.createElement("div");
					promptTitle.className = "qwen-te-preset-card__detail-item";
					promptTitle.innerHTML = "<strong>本次生成提示词</strong>";
					detailWrap.appendChild(promptTitle);
					const addStageOutputRow = (label, text, tone = "info") => {
						if (!String(text ?? "").trim()) return;
						const row = document.createElement("div");
						row.className = `qwen-te-preset-card__detail-item qwen-te-preset-card__detail-item--${tone}`;
						const strong = document.createElement("strong");
						strong.textContent = label;
						row.appendChild(strong);
						row.appendChild(document.createTextNode(`\n${String(text ?? "").trim()}`));
						detailWrap.appendChild(row);
					};
					addStageOutputRow("正向提示词", stageOutput?.promptText, "success");
					if (stageOutput?.promptCollection && stageOutput.promptCollection !== stageOutput?.promptText) {
						addStageOutputRow("正向提示词合集", stageOutput.promptCollection, "success");
					}
					addStageOutputRow("智能文本", stageOutput?.smartText, "info");
					addStageOutputRow("推荐负面词", stageOutput?.negativePrompt, "warn");
					addStageOutputRow("标签与参数摘要", stageOutput?.selectedTags, "info");
				}

				if (reportPayload && isAggregateHistoryReport && Array.isArray(reportPayload?.reportPayloads) && reportPayload.reportPayloads.length) {
					const aggregateTitle = document.createElement("div");
					aggregateTitle.className = "qwen-te-preset-card__detail-item";
					aggregateTitle.innerHTML = "<strong>聚合子报告</strong>";
					detailWrap.appendChild(aggregateTitle);
					for (const report of reportPayload.reportPayloads.slice(0, 6)) {
						const aggregate = report?.aggregate ?? {};
						const tone = String(aggregate?.risk?.tone ?? "info");
						const row = document.createElement("div");
						row.className = `qwen-te-preset-card__detail-item qwen-te-preset-card__detail-item--${tone}`;
						const strong = document.createElement("strong");
						strong.textContent = `${formatPresetTime(aggregate?.lastAt)} | ${aggregate?.successRate ?? "待定"} | ${aggregate?.risk?.label ?? "未知"}`;
						row.appendChild(strong);
						row.appendChild(document.createTextNode(`\n${aggregate?.trend?.arrow ?? "→"} ${aggregate?.trend?.label ?? "待观察"} | ${aggregate?.outcomeTrail ?? "·"}\n${aggregate?.lastMessage ?? ""}`));
						detailWrap.appendChild(row);
					}
				}

				if (reportPayload) {
					const recentRoundSummaries = Array.isArray(reportPayload.recentRoundSummaries) ? reportPayload.recentRoundSummaries : [];
					if (recentRoundSummaries.length) {
						const chainTitle = document.createElement("div");
						chainTitle.className = "qwen-te-preset-card__detail-item";
						chainTitle.innerHTML = "<strong>最近轮次链路</strong>";
						detailWrap.appendChild(chainTitle);
						for (const roundSummary of recentRoundSummaries) {
							const tone = String(roundSummary?.tone ?? getContinuousRunLevelTone(String(roundSummary?.terminalLevel ?? "")));
							const chainRow = document.createElement("div");
							chainRow.className = `qwen-te-preset-card__detail-item qwen-te-preset-card__detail-item--${tone}`;
							const chainStrong = document.createElement("strong");
							chainStrong.textContent = `${roundSummary?.terminalSymbol ?? getContinuousRunOutcomeSymbol(String(roundSummary?.terminalLevel ?? ""))} ${roundSummary?.roundLabel ?? "未标轮次"} | ${roundSummary?.terminalLevel ?? "未知"}`;
							chainRow.appendChild(chainStrong);
							chainRow.appendChild(document.createTextNode(` [${formatPresetTime(roundSummary?.latestAt)}]\n${roundSummary?.chain ?? ""}\n${roundSummary?.terminalMessage ?? ""}`));
							detailWrap.appendChild(chainRow);
						}
					}

					const recentRounds = Array.isArray(reportPayload.recentRounds) ? reportPayload.recentRounds : [];
					if (recentRounds.length) {
						const recentTitle = document.createElement("div");
						recentTitle.className = "qwen-te-preset-card__detail-item";
						recentTitle.innerHTML = "<strong>最近轮次终态</strong>";
						detailWrap.appendChild(recentTitle);
						for (const roundItem of recentRounds) {
							const tone = String(roundItem?.tone ?? getContinuousRunLevelTone(String(roundItem?.level ?? "")));
							const recentRow = document.createElement("div");
							recentRow.className = `qwen-te-preset-card__detail-item qwen-te-preset-card__detail-item--${tone}`;
							const recentStrong = document.createElement("strong");
							recentStrong.textContent = `${roundItem?.symbol ?? getContinuousRunOutcomeSymbol(String(roundItem?.level ?? ""))} ${roundItem?.roundLabel ?? "未标轮次"} | ${roundItem?.level ?? "未知"}${roundItem?.origin === "manual" ? " | 手动" : ""}`;
							recentRow.appendChild(recentStrong);
							recentRow.appendChild(document.createTextNode(` [${formatPresetTime(roundItem?.at)}]\n${roundItem?.message ?? ""}`));
							detailWrap.appendChild(recentRow);
						}
					}

					const reportEntries = Array.isArray(reportPayload.entries) ? reportPayload.entries.slice(0, 6) : [];
					if (reportEntries.length) {
						const eventTitle = document.createElement("div");
						eventTitle.className = "qwen-te-preset-card__detail-item";
						eventTitle.innerHTML = "<strong>最近事件</strong>";
						detailWrap.appendChild(eventTitle);
						for (const entry of reportEntries) {
							const tone = String(getContinuousRunLevelTone(String(entry?.level ?? "")));
							const eventRow = document.createElement("div");
							eventRow.className = `qwen-te-preset-card__detail-item qwen-te-preset-card__detail-item--${tone}`;
							const eventStrong = document.createElement("strong");
							const roundText = entry?.round && entry?.total ? `第 ${entry.round}/${entry.total} 轮` : "通用事件";
							eventStrong.textContent = `[${formatPresetTime(entry?.at)}] ${entry?.level ?? "记录"}${entry?.origin === "manual" ? " | 手动" : ""}`;
							eventRow.appendChild(eventStrong);
							eventRow.appendChild(document.createTextNode(` ${roundText}\n${entry?.message ?? ""}`));
							detailWrap.appendChild(eventRow);
						}
					}
				}
			}
		}
	};
	for (const filter of sourceFilters) {
		const button = document.createElement("button");
		button.className = "qwen-te-modal__preset";
		button.textContent = filter.label;
		button.onclick = () => {
			activeSourceFilter = filter.key;
			render();
		};
		filterBar.appendChild(button);
		filterButtons.set(filter.key, button);
	}
	searchInput.addEventListener("input", render);
	sortSelect.addEventListener("change", () => {
		activeSort = String(sortSelect.value ?? "updated_desc");
		render();
	});
	exportButton.onclick=()=>{ exportNodeHistory(node); statusEl.textContent="已导出当前节点历史。"; };
	importButton.onclick=()=>fileInput.click();
	fileInput.onchange=async()=>{ const file=fileInput.files?.[0]; fileInput.value=""; if(!file) return; try{ const result=await importNodeHistoryFile(node,file); statusEl.textContent=result.message; render(); } catch(error){ statusEl.textContent=`导入失败：${error.message}`; } };
	clearAllButton.onclick=()=>{ const historyCount=getNodeHistory(node).length; if(historyCount<=0){ statusEl.textContent="当前没有可删除的历史。"; render(); return; } const confirmed=window.confirm(`将删除本节点全部 ${historyCount} 条历史记录（包括置顶项），此操作不可撤销。确定继续吗？`); if(!confirmed){ statusEl.textContent="已取消一键删除历史。"; return; } setNodeHistory(node, []); expandedHistoryIds.clear(); clearStageDisplayPreview(node); statusEl.textContent=`已一键删除 ${historyCount} 条历史记录。`; render(); };
	doneButton.onclick=()=>overlay.remove(); closeButton.onclick=()=>overlay.remove(); overlay.addEventListener("click",(event)=>{ if(event.target===overlay) overlay.remove(); }); document.body.appendChild(overlay); render(); searchInput.focus();
}

function openExampleDialog(node, library) {
	const modalContext = buildNodeModalContext(node, library);
	const currentTemplate = String(getWidget(node, "模板风格")?.value ?? "自动");
	const availablePresets = buildDedupedPresets(library, { collection: "example", includeVariants: false });
	const currentState = collectNodeState(node, library);
	const defaultPresetName = EXAMPLE_PRESET_MAP[currentTemplate] ?? EXAMPLE_PRESET_MAP["自动"];
	const initialPreset =
		inferBestExamplePreset(availablePresets, currentTemplate, currentState)
		?? availablePresets.find((item) => item.name === defaultPresetName)
		?? availablePresets[0];
	let selectedPreset = initialPreset ?? null;

	ensureSingleModal("example-dialog");
	const overlay = document.createElement("div");
	overlay.className = "qwen-te-modal";
	overlay.dataset.qwenModal = "example-dialog";
	overlay.__qwenNode = node;
	const dialog = document.createElement("div");
	dialog.className = "qwen-te-modal__dialog";
	overlay.appendChild(dialog);

	const header = document.createElement("div");
	header.className = "qwen-te-modal__header";
	dialog.appendChild(header);
	const titleWrap = document.createElement("div");
	header.appendChild(titleWrap);
	const title = document.createElement("div");
	title.className = "qwen-te-modal__title";
	title.textContent = "示例锚点";
	titleWrap.appendChild(title);
	const subtitle = document.createElement("div");
	subtitle.className = "qwen-te-modal__subtitle";
	subtitle.textContent = `直接选择可出图的示例方向，用于快速定调；稳定复用请保存到“预设”。当前节点：${modalContext.nodeName}。`;
	titleWrap.appendChild(subtitle);
	const closeButton = document.createElement("button");
	closeButton.className = "qwen-te-modal__footer-button";
	closeButton.textContent = "关闭";
	header.appendChild(closeButton);

	const body = document.createElement("div");
	body.className = "qwen-te-modal__body";
	dialog.appendChild(body);

	const statusEl = document.createElement("div");
	statusEl.className = "qwen-te-modal__status";
	body.appendChild(statusEl);

	const toolbar = document.createElement("div");
	toolbar.className = "qwen-te-modal__toolbar";
	body.appendChild(toolbar);
	const searchInput = document.createElement("input");
	searchInput.className = "qwen-te-modal__search";
	searchInput.placeholder = "搜索示例名称、标签、用途";
	toolbar.appendChild(searchInput);

	const useCaseBar = document.createElement("div");
	useCaseBar.className = "qwen-te-modal__pillbar";
	body.appendChild(useCaseBar);
	const shotBar = document.createElement("div");
	shotBar.className = "qwen-te-modal__pillbar";
	body.appendChild(shotBar);

	const listTitle = document.createElement("div");
	listTitle.className = "qwen-te-group__section-title";
	listTitle.textContent = "可用示例";
	body.appendChild(listTitle);
	const presetList = document.createElement("div");
	presetList.className = "qwen-te-preset-list";
	body.appendChild(presetList);

	const customLabel = document.createElement("div");
	customLabel.className = "qwen-te-group__section-title";
	customLabel.textContent = "额外补充（可选）";
	body.appendChild(customLabel);
	const customInput = document.createElement("textarea");
	customInput.className = "qwen-te-modal__textarea";
	customInput.placeholder = "例如：窗边、晨雾、长焦、银白发、薄纱裙。多个标签用逗号分隔。";
	body.appendChild(customInput);

	const footer = document.createElement("div");
	footer.className = "qwen-te-modal__footer";
	dialog.appendChild(footer);
	const cancelButton = document.createElement("button");
	cancelButton.className = "qwen-te-modal__footer-button";
	cancelButton.textContent = "关闭";
	footer.appendChild(cancelButton);
	const applyButton = document.createElement("button");
	applyButton.className = "qwen-te-modal__footer-button qwen-te-modal__footer-button--primary";
	applyButton.textContent = "应用选中";
	footer.appendChild(applyButton);
	const applyRunButton = document.createElement("button");
	applyRunButton.className = "qwen-te-modal__footer-button qwen-te-modal__footer-button--primary";
	applyRunButton.textContent = "选中并运行";
	footer.appendChild(applyRunButton);

	let activeUseCase = "all";
	let activeShot = "all";
	const useCaseButtons = new Map();
	const shotButtons = new Map();
	const inferPresetShotKey = (preset) => {
		const name = String(preset?.name ?? "");
		const tags = new Set(preset?.tags ?? []);
		if (name.includes("·近景") || tags.has("近景") || tags.has("面部特写") || tags.has("头部写真")) return "close";
		if (name.includes("·全身") || tags.has("全景全身") || tags.has("全身") || tags.has("大全景")) return "wide";
		return "mid";
	};
	const setButtonGroupActive = (buttons, activeKey) => {
		for (const [key, button] of buttons.entries()) {
			const active = key === activeKey;
			button.style.borderColor = active ? "#caa55b" : "#525252";
			button.style.background = active ? "#59451a" : "#232323";
			button.style.color = active ? "#fff0ca" : "#f7f7f7";
		}
	};

	const presetMatches = (preset) => {
		const meta = preset.meta ?? {};
		if (activeUseCase !== "all" && !(meta.use_cases ?? []).includes(activeUseCase)) return false;
		if (activeShot !== "all" && inferPresetShotKey(preset) !== activeShot) return false;
		const keyword = String(searchInput.value ?? "").trim().toLowerCase();
		if (!keyword) return true;
		return (meta.search_keywords ?? []).join(" ").toLowerCase().includes(keyword);
	};
	const appendPill = (container, text, extraClass = "") => {
		const pill = document.createElement("div");
		pill.className = `qwen-te-modal__content-pill${extraClass ? ` ${extraClass}` : ""}`;
		pill.textContent = text;
		container.appendChild(pill);
		return pill;
	};
	const renderPresetCard = (preset, options = {}) => {
		const card = document.createElement("div");
		const selected = String(selectedPreset?.name ?? "") === String(preset.name ?? "");
		card.className = `qwen-te-preset-card qwen-te-preset-card--clickable${selected ? " qwen-te-preset-card--expanded" : ""}`;
		const head = document.createElement("div");
		head.className = "qwen-te-preset-card__header";
		card.appendChild(head);
		const headMain = document.createElement("div");
		headMain.className = "qwen-te-preset-card__head-main";
		head.appendChild(headMain);
		const name = document.createElement("div");
		name.className = "qwen-te-preset-card__name";
		name.textContent = preset.name;
		headMain.appendChild(name);
		const meta = preset.meta ?? {};
		appendPill(headMain, String(meta.tier ?? "示例"), "qwen-te-modal__content-pill--muted");
		const summary = document.createElement("div");
		summary.className = "qwen-te-preset-card__summary";
		summary.textContent = preset.description ?? "内置示例锚点。";
		card.appendChild(summary);
		const badges = document.createElement("div");
		badges.className = "qwen-te-preset-card__badges";
		card.appendChild(badges);
		for (const label of [String(meta.group ?? ""), ...(meta.use_cases ?? []), inferPresetShotKey(preset) === "close" ? "近景" : inferPresetShotKey(preset) === "wide" ? "全身" : "中景"].filter(Boolean)) {
			appendPill(badges, label);
		}
		const tagBar = document.createElement("div");
		tagBar.className = "qwen-te-modal__content-pills";
		card.appendChild(tagBar);
		for (const tag of (preset.tags ?? []).slice(0, 10)) appendPill(tagBar, tag, "qwen-te-modal__content-pill--muted");
		const detailGrid = document.createElement("div");
		detailGrid.className = "qwen-te-preset-card__detail-grid";
		card.appendChild(detailGrid);
		for (const item of inferPresetRecommendation(preset).slice(0, 4)) {
			const block = document.createElement("div");
			block.className = "qwen-te-preset-card__kv";
			const label = document.createElement("div");
			label.className = "qwen-te-preset-card__kv-label";
			label.textContent = item.label;
			const value = document.createElement("div");
			value.className = "qwen-te-preset-card__kv-value";
			value.textContent = item.value;
			block.append(label, value);
			detailGrid.appendChild(block);
		}
		const actions = document.createElement("div");
		actions.className = "qwen-te-preset-card__action-row qwen-te-preset-card__action-row--primary";
		card.appendChild(actions);
		const selectButton = document.createElement("button");
		selectButton.className = "qwen-te-modal__footer-button";
		selectButton.textContent = "选中";
		actions.appendChild(selectButton);
		const applyNowButton = document.createElement("button");
		applyNowButton.className = "qwen-te-modal__footer-button qwen-te-modal__footer-button--primary";
		applyNowButton.textContent = "应用";
		actions.appendChild(applyNowButton);
		const runButton = document.createElement("button");
		runButton.className = "qwen-te-modal__footer-button qwen-te-modal__footer-button--primary";
		runButton.textContent = "应用并运行";
		actions.appendChild(runButton);
		const selectPreset = () => {
			selectedPreset = preset;
			render();
		};
		card.onclick = (event) => {
			if (String(event.target?.tagName ?? "").toUpperCase() === "BUTTON") return;
			selectPreset();
		};
		selectButton.onclick = (event) => { event.stopPropagation(); selectPreset(); };
		applyNowButton.onclick = async (event) => { event.stopPropagation(); selectedPreset = preset; await applySelectedExample(); };
		runButton.onclick = async (event) => { event.stopPropagation(); selectedPreset = preset; await applySelectedExample({ queue: true }); };
		if (options.compact) {
			actions.remove();
			detailGrid.remove();
		}
		return card;
	};
	const render = () => {
		presetList.replaceChildren();
		setButtonGroupActive(useCaseButtons, activeUseCase);
		setButtonGroupActive(shotButtons, activeShot);
		const filteredPresets = availablePresets.filter((preset) => presetMatches(preset));
		if (!selectedPreset || !filteredPresets.some((preset) => preset.name === selectedPreset.name)) {
			selectedPreset = filteredPresets[0] ?? initialPreset ?? null;
		}
		if (!filteredPresets.length) {
			const empty = document.createElement("div");
			empty.className = "qwen-te-preset-card__summary";
			empty.textContent = "当前筛选下没有可用示例。可清空搜索词或切换用途。";
			presetList.appendChild(empty);
			statusEl.textContent = `显示 0/${availablePresets.length}`;
			return;
		}
		for (const preset of filteredPresets) presetList.appendChild(renderPresetCard(preset));
		statusEl.textContent = `当前选中：${selectedPreset?.name ?? "无"} | 显示 ${filteredPresets.length}/${availablePresets.length}`;
	};

	const appendFilterButton = (container, store, key, label, onSelect) => {
		const button = document.createElement("button");
		button.className = "qwen-te-modal__preset";
		button.textContent = label;
		button.onclick = () => onSelect(key);
		container.appendChild(button);
		store.set(key, button);
	};

	appendFilterButton(useCaseBar, useCaseButtons, "all", "全部用途", (key) => { activeUseCase = key; render(); });
	for (const label of library?.quick_preset_use_case_order ?? PRESET_USE_CASE_ORDER) {
		appendFilterButton(useCaseBar, useCaseButtons, label, label, (key) => { activeUseCase = key; render(); });
	}
	appendFilterButton(shotBar, shotButtons, "all", "全部景别", (key) => { activeShot = key; render(); });
	appendFilterButton(shotBar, shotButtons, "close", "近景", (key) => { activeShot = key; render(); });
	appendFilterButton(shotBar, shotButtons, "mid", "中景", (key) => { activeShot = key; render(); });
	appendFilterButton(shotBar, shotButtons, "wide", "全身", (key) => { activeShot = key; render(); });

	searchInput.addEventListener("input", render);

	const applySelectedExample = async (options = {}) => {
		const preset = selectedPreset;
		if (!preset) return;
		const mutationRevision = beginNodeStateMutation(node);
		const nextLibrary = await getFreshLibraryForUi(node, library, { mutationRevision });
		if (!isNodeStateMutationCurrent(node, mutationRevision)) return;
		const nextState = createPresetBaseState(node, nextLibrary, preset);
		applyPreset(nextState, nextLibrary, preset, statusEl);
		const extraTags = parseCustomTags(customInput.value);
		const mapping = buildTagGroupIndex(nextLibrary);
		for (const tag of extraTags) {
			const groupName = mapping.get(tag);
			if (!groupName) {
				addUniqueTag(nextState.customTags, tag);
				continue;
			}
			const groupConfig = (nextLibrary.slot_config ?? []).find((group) => group.name === groupName);
			if (!groupConfig) {
				addUniqueTag(nextState.customTags, tag);
				continue;
			}
			if ((nextState.selected[groupName] ?? []).length < Number(groupConfig.slots ?? 0)) addUniqueTag(nextState.selected[groupName], tag);
			else addUniqueTag(nextState.customTags, tag);
		}
		recordNodeHistory(node, collectNodeState(node, nextLibrary), "before-random");
		if (!applyNodeState(node, nextLibrary, nextState, { recordHistory: true, historySource: "example", mutationRevision })) return;
		if (options.queue) {
			const queued = await queueWorkflowFromNode(node);
			if (!isNodeStateMutationCurrent(node, mutationRevision)) return;
			setNodeStatusText(node, queued ? `已应用示例锚点并加入队列：${preset.name}` : `已应用示例锚点：${preset.name}，但未能自动入队。`);
		}
		disposeModalOverlay(overlay);
	};
	applyButton.onclick = async () => { await applySelectedExample(); };
	applyRunButton.onclick = async () => { await applySelectedExample({ queue: true }); };

	const closeExample = () => disposeModalOverlay(overlay);
	cancelButton.onclick = closeExample;
	closeButton.onclick = closeExample;
	overlay.addEventListener("click", (event) => { if (event.target === overlay) closeExample(); });
	document.body.appendChild(overlay);
	render();
	searchInput.focus();
}

function openTagManager(node) {
	let currentLibrary = node[PANEL_KEY]?.library ?? {};
	const getCustomTagRules = () => currentLibrary?.custom_tag_rules ?? {};
	const getDefaultSectionName = (groupName) => String(getCustomTagRules().default_sections?.[groupName] ?? "自定义");
	const getMaxBatchAdd = () => Number(getCustomTagRules().max_batch_add ?? 30);
	const getSeparatorHint = () => String(getCustomTagRules().separator_hint ?? "支持逗号、顿号、分号和换行批量添加。");
	const normalizeFilterKeyword = (value) => String(value ?? "").normalize("NFKC").trim().toLowerCase();
	ensureSingleModal("tag-manager");
	const overlay = document.createElement("div");
	overlay.className = "qwen-te-modal";
	overlay.dataset.qwenModal = "tag-manager";
	overlay.__qwenNode = node;
	const dialog = document.createElement("div");
	dialog.className = "qwen-te-modal__dialog";
	overlay.appendChild(dialog);

	const header = document.createElement("div");
	header.className = "qwen-te-modal__header";
	dialog.appendChild(header);
	const titleWrap = document.createElement("div");
	header.appendChild(titleWrap);
	const title = document.createElement("div");
	title.className = "qwen-te-modal__title";
	title.textContent = "标签管理";
	titleWrap.appendChild(title);
	const subtitle = document.createElement("div");
	subtitle.className = "qwen-te-modal__subtitle";
	subtitle.textContent = "支持大类/小类折叠浏览，标签可多选后批量删除。";
	titleWrap.appendChild(subtitle);
	const closeButton = document.createElement("button");
	closeButton.className = "qwen-te-modal__footer-button";
	closeButton.textContent = "关闭";
	header.appendChild(closeButton);

	const body = document.createElement("div");
	body.className = "qwen-te-modal__body";
	dialog.appendChild(body);

	const stickyWrap = document.createElement("div");
	stickyWrap.style.cssText = "position:sticky;top:0;z-index:3;background:#171717;padding-bottom:10px;display:flex;flex-direction:column;gap:10px;";
	body.appendChild(stickyWrap);

	const toolbar = document.createElement("div");
	toolbar.className = "qwen-te-modal__toolbar";
	stickyWrap.appendChild(toolbar);
	const categorySelect = document.createElement("select");
	categorySelect.className = "qwen-te-modal__search";
	for (const group of currentLibrary?.slot_config ?? []) {
		const option = document.createElement("option");
		option.value = group.name;
		option.textContent = group.name;
		categorySelect.appendChild(option);
	}
	toolbar.appendChild(categorySelect);
	const sectionInput = document.createElement("input");
	sectionInput.className = "qwen-te-modal__search";
	sectionInput.placeholder = "小类名称";
	toolbar.appendChild(sectionInput);
	const tagInput = document.createElement("input");
	tagInput.className = "qwen-te-modal__search";
	tagInput.placeholder = "标签名称，支持批量粘贴";
	toolbar.appendChild(tagInput);
	const addButton = document.createElement("button");
	addButton.className = "qwen-te-modal__footer-button qwen-te-modal__footer-button--primary";
	addButton.textContent = "批量加入标签库";
	toolbar.appendChild(addButton);

	const ruleHint = document.createElement("div");
	ruleHint.className = "qwen-te-modal__status";
	stickyWrap.appendChild(ruleHint);
	const suggestHint = document.createElement("div");
	suggestHint.className = "qwen-te-modal__status";
	stickyWrap.appendChild(suggestHint);

	const actionBar = document.createElement("div");
	actionBar.className = "qwen-te-modal__toolbar";
	stickyWrap.appendChild(actionBar);
	const filterInput = document.createElement("input");
	filterInput.className = "qwen-te-modal__search";
	filterInput.placeholder = "搜索自定义标签 / 小类 / 大类";
	actionBar.appendChild(filterInput);
	const selectedBadge = document.createElement("div");
	selectedBadge.className = "qwen-te-modal__status";
	selectedBadge.style.minWidth = "136px";
	actionBar.appendChild(selectedBadge);
	const deleteSelectedButton = document.createElement("button");
	deleteSelectedButton.className = "qwen-te-modal__footer-button";
	deleteSelectedButton.textContent = "删除已选";
	actionBar.appendChild(deleteSelectedButton);
	const clearSelectedButton = document.createElement("button");
	clearSelectedButton.className = "qwen-te-modal__footer-button";
	clearSelectedButton.textContent = "清空勾选";
	actionBar.appendChild(clearSelectedButton);
	const expandAllButton = document.createElement("button");
	expandAllButton.className = "qwen-te-modal__footer-button";
	expandAllButton.textContent = "全部展开";
	actionBar.appendChild(expandAllButton);
	const collapseAllButton = document.createElement("button");
	collapseAllButton.className = "qwen-te-modal__footer-button";
	collapseAllButton.textContent = "全部折叠";
	actionBar.appendChild(collapseAllButton);

	const statusEl = document.createElement("div");
	statusEl.className = "qwen-te-modal__status";
	statusEl.textContent = "支持批量添加；点击标签可勾选，勾选后可批量删除。";
	body.appendChild(statusEl);

	const list = document.createElement("div");
	list.className = "qwen-te-preset-list";
	body.appendChild(list);

	const footer = document.createElement("div");
	footer.className = "qwen-te-modal__footer";
	dialog.appendChild(footer);
	const doneButton = document.createElement("button");
	doneButton.className = "qwen-te-modal__footer-button";
	doneButton.textContent = "完成";
	footer.appendChild(doneButton);

	const selectedTagKeys = new Set();
	let chipRecords = [];
	let detailRecords = [];
	let lastAutoSection = "";
	let suggestTimer = null;
	let suggestRequestId = 0;
	let renderRequestId = 0;
	const keyForTag = (groupName, sectionName, tag) => JSON.stringify([groupName, sectionName, tag]);
	const parseTagKey = (value) => JSON.parse(value);
	const syncSectionInput = (force = false) => {
		const defaultSection = getDefaultSectionName(categorySelect.value);
		sectionInput.placeholder = `小类名称，留空默认：${defaultSection}`;
		if (force || !sectionInput.value.trim() || sectionInput.value.trim() === lastAutoSection) {
			sectionInput.value = defaultSection;
			lastAutoSection = defaultSection;
		}
		ruleHint.textContent = `${getSeparatorHint()} 小类默认填充为“${defaultSection}”，单个标签建议不超过 ${getCustomTagRules().max_tag_length ?? 40} 个字符。`;
	};
	const updateSuggestHint = async () => {
		const rawText = tagInput.value;
		const tags = parseCustomTags(rawText);
		if (!tags.length) {
			suggestHint.textContent = "输入标签后，这里会显示智能归类建议。";
			return;
		}
		if (tags.length > getMaxBatchAdd()) {
			suggestHint.textContent = `当前解析出 ${tags.length} 个标签，超过单次推荐上限 ${getMaxBatchAdd()} 个。`;
			return;
		}
		const requestId = ++suggestRequestId;
		suggestHint.textContent = `正在分析 ${tags.length} 个标签的推荐归类...`;
		try {
			const detail = await suggestCustomTagGrouping(rawText, { owner: overlay, key: "tag-manager-suggest" });
			if (requestId !== suggestRequestId) return;
			const previews = (detail.tags ?? []).slice(0, 3).map((item) => {
				const tag = String(item.tag ?? "");
				if (item.exists) return `${tag} 已在 ${item.existing_group} / ${item.existing_section}`;
				if (item.recommended_group) return `${tag} -> ${item.recommended_group} / ${item.recommended_section}`;
				return `${tag} 暂无明确归类`;
			});
			suggestHint.textContent = previews.join("；");
		} catch (error) {
			if (requestId !== suggestRequestId) return;
			suggestHint.textContent = `归类分析失败：${error.message}`;
		}
	};
	const queueSuggestHint = () => {
		clearTimeout(suggestTimer);
		suggestRequestId += 1;
		suggestTimer = setTimeout(() => { void updateSuggestHint(); }, 160);
	};

	const syncSelectionUi = () => {
		for (const chip of chipRecords) chip.element.classList.toggle("is-selected", selectedTagKeys.has(chip.key));
		const selectedCount = selectedTagKeys.size;
		const totalCustomTags = Number(currentLibrary?.custom_tag_stats?.tag_count ?? 0);
		selectedBadge.textContent = selectedCount ? `已选 ${selectedCount} 个标签 | 自定义总计 ${totalCustomTags}` : `未勾选标签 | 自定义总计 ${totalCustomTags}`;
		deleteSelectedButton.disabled = selectedCount === 0;
		deleteSelectedButton.style.opacity = selectedCount === 0 ? "0.45" : "1";
		deleteSelectedButton.style.cursor = selectedCount === 0 ? "not-allowed" : "pointer";
		clearSelectedButton.disabled = selectedCount === 0;
		clearSelectedButton.style.opacity = selectedCount === 0 ? "0.45" : "1";
		clearSelectedButton.style.cursor = selectedCount === 0 ? "not-allowed" : "pointer";
	};

	const setAllDetailsOpen = (open) => {
		for (const detail of detailRecords) detail.open = open;
	};

	const render = async (options = {}) => {
		const shouldRefresh = options.refresh !== false;
		const requestId = shouldRefresh ? ++renderRequestId : renderRequestId;
		let latestLibrary = currentLibrary;
		if (shouldRefresh) latestLibrary = await refreshLibraryOnNode(node);
		if ((shouldRefresh && requestId !== renderRequestId) || overlay.__qwenDisposed) return;
		currentLibrary = latestLibrary ?? currentLibrary;
		latestLibrary = currentLibrary;
		const previousCategory = categorySelect.value;
		categorySelect.replaceChildren();
		for (const group of latestLibrary?.slot_config ?? []) {
			const option = document.createElement("option");
			option.value = group.name;
			option.textContent = group.name;
			categorySelect.appendChild(option);
		}
		if ([...categorySelect.options].some((option) => option.value === previousCategory)) categorySelect.value = previousCategory;
		syncSectionInput();
		const customLibrary = latestLibrary.custom_tag_library ?? {};
		const customStats = latestLibrary.custom_tag_stats ?? {};
		const filterKeyword = normalizeFilterKeyword(filterInput.value);
		list.replaceChildren();
		chipRecords = [];
		detailRecords = [];
		const validKeys = new Set();
		const groupsWithCustom = Object.entries(customLibrary).filter(([, sections]) => Object.keys(sections ?? {}).length);
		if (!groupsWithCustom.length) {
			selectedTagKeys.clear();
			const empty = document.createElement("div");
			empty.className = "qwen-te-preset-card__summary";
			empty.textContent = "还没有自定义标签。";
			list.appendChild(empty);
			selectedBadge.textContent = `未勾选标签 | 自定义总计 0`;
			syncSelectionUi();
			return;
		}
		groupsWithCustom.forEach(([groupName, sections], groupIndex) => {
			const sectionEntries = Object.entries(sections ?? {})
				.map(([sectionName, tags]) => {
					const filteredTags = (tags ?? []).filter((tag) => {
						if (!filterKeyword) return true;
						const haystack = `${groupName} ${sectionName} ${tag}`.toLowerCase();
						return haystack.includes(filterKeyword);
					});
					return [sectionName, filteredTags, tags ?? []];
				})
				.filter(([, filteredTags]) => filteredTags.length);
			if (!sectionEntries.length) return;
			const groupCard = document.createElement("details");
			groupCard.className = "qwen-te-group qwen-te-group--manager";
			groupCard.open = groupIndex === 0;
			detailRecords.push(groupCard);
			list.appendChild(groupCard);

			const titleRow = document.createElement("summary");
			titleRow.className = "qwen-te-group__title";
			groupCard.appendChild(titleRow);
				const titleText = document.createElement("div");
				titleText.textContent = groupName;
				titleRow.appendChild(titleText);
				const countText = document.createElement("div");
				countText.className = "qwen-te-group__count";
				const totalTags = Object.values(sections ?? {}).reduce((sum, tags) => sum + (tags?.length ?? 0), 0);
				const visibleTags = sectionEntries.reduce((sum, [, filteredTags]) => sum + filteredTags.length, 0);
				countText.textContent = filterKeyword ? `${visibleTags}/${totalTags} 个` : `${totalTags} 个`;
				titleRow.appendChild(countText);

			const subText = document.createElement("div");
			subText.className = "qwen-te-group__sub";
			subText.textContent = "展开后可按小类浏览，点击标签即可加入批量删除列表。";
			groupCard.appendChild(subText);

				sectionEntries.forEach(([sectionName, filteredTags, sourceTags], sectionIndex) => {
					const sectionCard = document.createElement("details");
					sectionCard.style.cssText = "border-top:1px solid #343434;padding-top:10px;";
					sectionCard.open = groupIndex === 0 && sectionIndex === 0;
					detailRecords.push(sectionCard);
				groupCard.appendChild(sectionCard);

				const sectionSummary = document.createElement("summary");
				sectionSummary.style.cssText = "list-style:none;cursor:pointer;display:flex;align-items:center;justify-content:space-between;gap:10px;";
				sectionCard.appendChild(sectionSummary);
				const sectionTitle = document.createElement("div");
				sectionTitle.className = "qwen-te-group__section-title";
				sectionTitle.style.marginBottom = "0";
				sectionTitle.textContent = sectionName;
				sectionSummary.appendChild(sectionTitle);
					const sectionCount = document.createElement("div");
					sectionCount.className = "qwen-te-group__count";
					sectionCount.textContent = filterKeyword ? `${filteredTags?.length ?? 0}/${sourceTags?.length ?? 0} 个` : `${sourceTags?.length ?? 0} 个`;
					sectionSummary.appendChild(sectionCount);

				const chips = document.createElement("div");
				chips.className = "qwen-te-group__chips";
				chips.style.marginTop = "10px";
				sectionCard.appendChild(chips);
					for (const tag of filteredTags ?? []) {
						const key = keyForTag(groupName, sectionName, tag);
						validKeys.add(key);
					const chip = document.createElement("button");
					chip.type = "button";
					chip.className = "qwen-te-chip";
					chip.textContent = tag;
					chip.title = "点击勾选或取消勾选";
					chip.onclick = () => {
						if (selectedTagKeys.has(key)) selectedTagKeys.delete(key);
						else selectedTagKeys.add(key);
						syncSelectionUi();
					};
					chips.appendChild(chip);
					chipRecords.push({ key, element: chip });
				}
			});
			});
			for (const key of [...selectedTagKeys]) if (!validKeys.has(key)) selectedTagKeys.delete(key);
			const totalCustomTags = Number(customStats.tag_count ?? 0);
			selectedBadge.textContent = selectedTagKeys.size ? `已选 ${selectedTagKeys.size} 个标签 | 自定义总计 ${totalCustomTags}` : `未勾选标签 | 自定义总计 ${totalCustomTags}`;
			syncSelectionUi();
		};

	addButton.onclick = async () => {
		const category = categorySelect.value;
		const section = sectionInput.value.trim() || getDefaultSectionName(category);
		const rawTagText = tagInput.value;
		const tags = parseCustomTags(rawTagText);
		if (!category || !tags.length) {
			statusEl.textContent = "至少要选择大类并填写 1 个标签名称。";
			return;
		}
		if (tags.length > getMaxBatchAdd()) {
			statusEl.textContent = `单次最多添加 ${getMaxBatchAdd()} 个标签，请分批操作。`;
			return;
		}
		try {
			const result = await mutateTagLibrary("/qwen_te/tag_library/add_batch", { category, section, tag: rawTagText }, { owner: overlay, key: "tag-manager-mutation" });
			const detail = result.detail ?? {};
			sectionInput.value = section;
			tagInput.value = "";
			const summaryParts = [];
			if ((detail.added ?? []).length) summaryParts.push(`新增 ${(detail.added ?? []).length} 个`);
			if ((detail.skipped ?? []).length) summaryParts.push(`重复 ${(detail.skipped ?? []).length} 个`);
			if ((detail.errors ?? []).length) summaryParts.push(`无效 ${(detail.errors ?? []).length} 个`);
			statusEl.textContent = summaryParts.length ? `${result.message}：${summaryParts.join("，")}` : result.message;
			void updateSuggestHint();
			await render();
		} catch (error) {
			statusEl.textContent = `添加失败：${error.message}`;
		}
	};

	deleteSelectedButton.onclick = async () => {
		if (!selectedTagKeys.size) {
			statusEl.textContent = "先勾选要删除的标签。";
			return;
		}
		const keys = [...selectedTagKeys];
		const confirmed = window.confirm(`将删除已勾选的 ${keys.length} 个标签，确定继续吗？`);
		if (!confirmed) {
			statusEl.textContent = "已取消删除。";
			return;
		}
		const failedKeys = [];
		statusEl.textContent = `正在删除 ${keys.length} 个标签...`;
		deleteSelectedButton.disabled = true;
		for (const key of keys) {
			const [category, section, tag] = parseTagKey(key);
			try {
				await mutateTagLibrary("/qwen_te/tag_library/delete", { category, section, tag }, { owner: overlay, key: "tag-manager-mutation" });
			} catch (error) {
				failedKeys.push(key);
			}
		}
		selectedTagKeys.clear();
		for (const key of failedKeys) selectedTagKeys.add(key);
		statusEl.textContent = failedKeys.length ? `删除完成，但有 ${failedKeys.length} 个标签删除失败。` : `已删除 ${keys.length} 个标签。`;
		await render();
	};

	clearSelectedButton.onclick = () => {
		if (selectedTagKeys.size) {
			const confirmed = window.confirm(`将清空当前 ${selectedTagKeys.size} 个勾选项，确定继续吗？`);
			if (!confirmed) {
				statusEl.textContent = "已取消清空勾选。";
				return;
			}
		}
		selectedTagKeys.clear();
		statusEl.textContent = "已清空勾选。";
		syncSelectionUi();
	};
	categorySelect.addEventListener("change", () => syncSectionInput(true));
	filterInput.addEventListener("input", () => { void render({ refresh: false }); });
	tagInput.addEventListener("input", () => { queueSuggestHint(); });
	expandAllButton.onclick = () => setAllDetailsOpen(true);
	collapseAllButton.onclick = () => setAllDetailsOpen(false);

	overlay.__qwenDispose = () => {
		clearTimeout(suggestTimer);
		suggestRequestId += 1;
		renderRequestId += 1;
	};
	const closeTagManager = () => disposeModalOverlay(overlay);
	doneButton.onclick = closeTagManager;
	closeButton.onclick = closeTagManager;
	overlay.addEventListener("click", (event) => { if (event.target === overlay) closeTagManager(); });
	document.body.appendChild(overlay);
	syncSectionInput(true);
	void updateSuggestHint();
	render();
	tagInput.focus();
}

function openOnlinePromptSearchDialog(node, library) {
	ensureSingleModal("online-search");
	const modalContext = buildNodeModalContext(node, library);
	let activeBrowserMode = "web";
	const overlay = document.createElement("div");
	overlay.className = "qwen-te-modal";
	overlay.dataset.qwenModal = "online-search";
	overlay.__qwenNode = node;
	const dialog = document.createElement("div");
	dialog.className = "qwen-te-modal__dialog qwen-te-online-search__browser";
	dialog.setAttribute("role", "dialog");
	dialog.setAttribute("aria-modal", "true");
	overlay.appendChild(dialog);

	const header = document.createElement("div");
	header.className = "qwen-te-modal__header qwen-te-online-search__tabstrip";
	dialog.appendChild(header);
	const browserTabs = document.createElement("div");
	browserTabs.className = "qwen-te-online-search__tabs";
	browserTabs.setAttribute("role", "tablist");
	browserTabs.setAttribute("aria-label", "浏览器页面");
	header.appendChild(browserTabs);
	const createBrowserModeTab = (mode, titleText, subtitleText, titleId) => {
		const button = document.createElement("button");
		button.type = "button";
		button.className = "qwen-te-online-search__tab";
		button.id = `${titleId}-tab`;
		button.dataset.qwenBrowserMode = mode;
		button.setAttribute("role", "tab");
		button.setAttribute("aria-selected", mode === activeBrowserMode ? "true" : "false");
		const tabTitle = document.createElement("span");
		tabTitle.className = "qwen-te-modal__title";
		tabTitle.id = titleId;
		tabTitle.textContent = titleText;
		button.appendChild(tabTitle);
		const tabSubtitle = document.createElement("span");
		tabSubtitle.className = "qwen-te-modal__subtitle";
		tabSubtitle.textContent = subtitleText;
		button.appendChild(tabSubtitle);
		browserTabs.appendChild(button);
		return { button, title: tabTitle };
	};
	const webModeTab = createBrowserModeTab("web", "网页浏览器", modalContext.nodeName, "qwen-te-online-search-web-title");
	const tagModeTab = createBrowserModeTab("tags", "提示词搜索", "完整提示词与提示词库", "qwen-te-online-search-tags-title");
	dialog.setAttribute("aria-labelledby", webModeTab.title.id);
	const closeButton = document.createElement("button");
	closeButton.type = "button";
	closeButton.className = "qwen-te-online-search__window-button";
	closeButton.textContent = "×";
	closeButton.title = "关闭浏览器";
	closeButton.setAttribute("aria-label", "关闭浏览器");
	header.appendChild(closeButton);

	const body = document.createElement("div");
	body.className = "qwen-te-modal__body qwen-te-online-search__body";
	dialog.appendChild(body);

	const stack = document.createElement("div");
	stack.className = "qwen-te-online-search__stack";
	body.appendChild(stack);

	const topbar = document.createElement("div");
	topbar.className = "qwen-te-online-search__topbar";
	stack.appendChild(topbar);

	const toolbar = document.createElement("div");
	toolbar.className = "qwen-te-modal__toolbar qwen-te-modal__toolbar--online-search qwen-te-online-search__browser-toolbar";
	toolbar.setAttribute("role", "search");
	topbar.appendChild(toolbar);
	const browserNav = document.createElement("div");
	browserNav.className = "qwen-te-online-search__nav";
	browserNav.setAttribute("aria-label", "网页导航");
	toolbar.appendChild(browserNav);
	const createBrowserNavButton = (text, label) => {
		const button = document.createElement("button");
		button.type = "button";
		button.className = "qwen-te-online-search__nav-button";
		button.textContent = text;
		button.title = label;
		button.setAttribute("aria-label", label);
		browserNav.appendChild(button);
		return button;
	};
	const backButton = createBrowserNavButton("←", "返回上一个手动打开的网址");
	const forwardButton = createBrowserNavButton("→", "前进到下一个手动打开的网址");
	const reloadButton = createBrowserNavButton("↻", "重新加载地址栏网址");
	const homeButton = createBrowserNavButton("⌂", "浏览器主页");
	const addressBar = document.createElement("div");
	addressBar.className = "qwen-te-online-search__addressbar";
	toolbar.appendChild(addressBar);
	const addressBadge = document.createElement("span");
	addressBadge.className = "qwen-te-online-search__address-badge";
	addressBadge.textContent = "网页";
	addressBar.appendChild(addressBadge);
	const searchInput = document.createElement("input");
	searchInput.className = "qwen-te-modal__search qwen-te-online-search__address-input";
	searchInput.placeholder = "输入网址或网页搜索词";
	searchInput.maxLength = 2048;
	searchInput.setAttribute("aria-label", "网页浏览器地址栏");
	addressBar.appendChild(searchInput);
	const searchButton = document.createElement("button");
	searchButton.type = "button";
	searchButton.className = "qwen-te-online-search__go-button";
	searchButton.textContent = "打开";
	searchButton.title = "在内嵌网页中打开";
	toolbar.appendChild(searchButton);
	const openExternalButton = document.createElement("button");
	openExternalButton.type = "button";
	openExternalButton.className = "qwen-te-online-search__nav-button qwen-te-online-search__external-button";
	openExternalButton.textContent = "↗";
	openExternalButton.title = "在新标签页打开当前网址";
	openExternalButton.setAttribute("aria-label", "在新标签页打开当前网址");
	toolbar.appendChild(openExternalButton);
	const companionBrowserButton = document.createElement("button");
	companionBrowserButton.type = "button";
	companionBrowserButton.className = "qwen-te-online-search__nav-button qwen-te-online-search__companion-button";
	companionBrowserButton.textContent = "▣";
	companionBrowserButton.title = "在独立完整浏览器窗口打开当前网址";
	companionBrowserButton.setAttribute("aria-label", "启动完整浏览器窗口");
	toolbar.appendChild(companionBrowserButton);

	const actionBar = document.createElement("div");
	actionBar.className = "qwen-te-modal__toolbar qwen-te-modal__toolbar--online-actions qwen-te-online-search__actions";
	actionBar.setAttribute("role", "group");
	actionBar.setAttribute("aria-label", "候选提示词操作");
	const applyButton = document.createElement("button");
	applyButton.type = "button";
	applyButton.className = "qwen-te-modal__footer-button";
	applyButton.textContent = "回填提示词";
	actionBar.appendChild(applyButton);
	const importButton = document.createElement("button");
	importButton.type = "button";
	importButton.className = "qwen-te-modal__footer-button";
	importButton.textContent = "拆分入库";
	actionBar.appendChild(importButton);
	const importHighButton = document.createElement("button");
	importHighButton.type = "button";
	importHighButton.className = "qwen-te-modal__footer-button";
	importHighButton.textContent = "复制提示词";
	actionBar.appendChild(importHighButton);

	const webQuickBar = document.createElement("div");
	webQuickBar.className = "qwen-te-modal__pillbar qwen-te-online-search__bookmarks qwen-te-online-search__bookmarks--web";
	topbar.appendChild(webQuickBar);
	const websiteBookmarks = [
		{ label: "Google", url: "https://www.google.com/webhp?igu=1" },
		{ label: "Civitai", url: "https://civitai.com/" },
		{ label: "Lexica", url: "https://lexica.art/" },
		{ label: "GitHub", url: "https://github.com/" },
		{ label: "Example", url: "https://example.com/" },
	];
	const webBookmarkButtons = [];
	for (const item of websiteBookmarks) {
		const button = document.createElement("button");
		button.type = "button";
		button.className = "qwen-te-modal__preset";
		button.textContent = item.label;
		button.title = `打开 ${item.url}`;
		button.dataset.qwenBrowserUrl = item.url;
		webQuickBar.appendChild(button);
		webBookmarkButtons.push(button);
	}

	const tagQuickBar = document.createElement("div");
	tagQuickBar.className = "qwen-te-modal__pillbar qwen-te-online-search__bookmarks qwen-te-online-search__bookmarks--tags qwen-te-hidden";
	topbar.appendChild(tagQuickBar);
	const quickQueries = ["cinematic portrait", "都市通勤大片", "古风神女", "赛博朋克夜景", "机甲写实"];
	const quickButtons = [];
	for (const item of quickQueries) {
		const button = document.createElement("button");
		button.type = "button";
		button.className = "qwen-te-modal__preset";
		button.textContent = item;
		button.title = `搜索 ${item}`;
		button.onclick = () => {
			if (searchButton.disabled) return;
			searchInput.value = item;
			tagQueryDraft = item;
			void runSearch();
		};
		tagQuickBar.appendChild(button);
		quickButtons.push(button);
	}

	const statusEl = document.createElement("div");
	statusEl.className = "qwen-te-modal__status qwen-te-online-search__status qwen-te-hidden";
	statusEl.setAttribute("aria-live", "polite");
	statusEl.textContent = "输入主题、画面风格或提示词片段后搜索。";
	topbar.appendChild(statusEl);
	const webStatusEl = document.createElement("div");
	webStatusEl.className = "qwen-te-modal__status qwen-te-online-search__status qwen-te-online-search__web-status";
	webStatusEl.setAttribute("aria-live", "polite");
	webStatusEl.textContent = "主页";
	topbar.appendChild(webStatusEl);

	const filtersWrap = document.createElement("div");
	filtersWrap.className = "qwen-te-online-search__filters qwen-te-online-search__filter-rail";
	filtersWrap.setAttribute("role", "group");
	filtersWrap.setAttribute("aria-label", "搜索结果筛选");

	const summaryBar = document.createElement("div");
	summaryBar.className = "qwen-te-modal__content-pills qwen-te-online-search__summary";
	filtersWrap.appendChild(summaryBar);

	const selectionBadge = document.createElement("div");
	selectionBadge.className = "qwen-te-modal__status qwen-te-modal__status--inline qwen-te-online-search__selection-status";
	selectionBadge.setAttribute("role", "status");
	selectionBadge.textContent = "未选择候选提示词。";

	const groupFilterLabel = document.createElement("div");
	groupFilterLabel.className = "qwen-te-online-search__filter-label";
	groupFilterLabel.id = "qwen-te-online-search-group-filter-label";
	groupFilterLabel.textContent = "提示词来源";
	filtersWrap.appendChild(groupFilterLabel);
	const filterBar = document.createElement("div");
	filterBar.className = "qwen-te-modal__pillbar qwen-te-online-search__filter-list qwen-te-online-search__filter-list--groups";
	filterBar.setAttribute("role", "group");
	filterBar.setAttribute("aria-labelledby", groupFilterLabel.id);
	filtersWrap.appendChild(filterBar);

	const metaFilterLabel = document.createElement("div");
	metaFilterLabel.className = "qwen-te-online-search__filter-label";
	metaFilterLabel.id = "qwen-te-online-search-meta-filter-label";
	metaFilterLabel.textContent = "提示词长度";
	filtersWrap.appendChild(metaFilterLabel);
	const metaFilterBar = document.createElement("div");
	metaFilterBar.className = "qwen-te-modal__pillbar qwen-te-online-search__filter-list qwen-te-online-search__filter-list--status";
	metaFilterBar.setAttribute("role", "group");
	metaFilterBar.setAttribute("aria-labelledby", metaFilterLabel.id);
	filtersWrap.appendChild(metaFilterBar);

	const contentGrid = document.createElement("div");
	contentGrid.className = "qwen-te-online-search__grid qwen-te-online-search__grid--workspace qwen-te-hidden";
	contentGrid.id = "qwen-te-online-search-tags-workspace";
	contentGrid.setAttribute("role", "tabpanel");
	contentGrid.setAttribute("aria-labelledby", tagModeTab.button.id);
	tagModeTab.button.setAttribute("aria-controls", contentGrid.id);
	stack.appendChild(contentGrid);
	contentGrid.appendChild(filtersWrap);

	const resultPanel = document.createElement("div");
	resultPanel.className = "qwen-te-online-search__panel qwen-te-online-search__panel--results";
	resultPanel.setAttribute("role", "region");
	contentGrid.appendChild(resultPanel);

	const resultHead = document.createElement("div");
	resultHead.className = "qwen-te-online-search__panel-head";
	resultPanel.appendChild(resultHead);

	const resultHeadText = document.createElement("div");
	resultHead.appendChild(resultHeadText);

	const resultTitle = document.createElement("div");
	resultTitle.className = "qwen-te-online-search__panel-title";
	resultTitle.id = "qwen-te-online-search-results-title";
	resultTitle.textContent = "搜索结果";
	resultPanel.setAttribute("aria-labelledby", resultTitle.id);
	resultHeadText.appendChild(resultTitle);

	const resultSub = document.createElement("div");
	resultSub.className = "qwen-te-online-search__panel-sub";
	resultSub.textContent = "点击完整提示词即可加入或移出本次操作。";
	resultHeadText.appendChild(resultSub);

	const resultTools = document.createElement("div");
	resultTools.className = "qwen-te-modal__content-tools";
	resultHead.appendChild(resultTools);

	const resultList = document.createElement("div");
	resultList.className = "qwen-te-online-search__cards";
	resultList.setAttribute("role", "group");
	resultList.setAttribute("aria-label", "候选提示词");
	resultPanel.appendChild(resultList);

	const samplePanel = document.createElement("div");
	samplePanel.className = "qwen-te-online-search__panel qwen-te-online-search__panel--samples";
	samplePanel.setAttribute("role", "region");
	contentGrid.appendChild(samplePanel);

	const sampleHead = document.createElement("div");
	sampleHead.className = "qwen-te-online-search__panel-head";
	samplePanel.appendChild(sampleHead);

	const sampleHeadText = document.createElement("div");
	sampleHead.appendChild(sampleHeadText);

	const sampleTitle = document.createElement("div");
	sampleTitle.className = "qwen-te-online-search__panel-title";
	sampleTitle.id = "qwen-te-online-search-reference-title";
	sampleTitle.textContent = "提示词预览";
	samplePanel.setAttribute("aria-labelledby", sampleTitle.id);
	sampleHeadText.appendChild(sampleTitle);

	const sampleSub = document.createElement("div");
	sampleSub.className = "qwen-te-online-search__panel-sub";
	sampleSub.textContent = "检查完整提示词后，可回填、复制或拆分写入标签库。";
	sampleHeadText.appendChild(sampleSub);
	samplePanel.appendChild(selectionBadge);
	const selectedPreview = document.createElement("div");
	selectedPreview.className = "qwen-te-online-search__selected-preview";
	selectedPreview.setAttribute("role", "group");
	selectedPreview.setAttribute("aria-label", "已选择的候选提示词");
	samplePanel.appendChild(selectedPreview);
	samplePanel.appendChild(actionBar);
	const referenceLabel = document.createElement("div");
	referenceLabel.className = "qwen-te-online-search__section-label";
	referenceLabel.textContent = "完整提示词";
	samplePanel.appendChild(referenceLabel);

	const sampleBox = document.createElement("textarea");
	sampleBox.className = "qwen-te-modal__textarea qwen-te-online-search__sample-box";
	sampleBox.readOnly = true;
	sampleBox.placeholder = "搜索后会显示完整提示词。";
	samplePanel.appendChild(sampleBox);

	const sampleList = document.createElement("div");
	sampleList.className = "qwen-te-online-search__sample-list";
	samplePanel.appendChild(sampleList);

	const sampleHint = document.createElement("div");
	sampleHint.className = "qwen-te-online-search__hint";
	sampleHint.textContent = "提示词可能来自联网样本，也可能由本地标签库组合生成。";
	samplePanel.appendChild(sampleHint);

	const webWorkspace = document.createElement("div");
	webWorkspace.className = "qwen-te-online-search__web-workspace";
	webWorkspace.id = "qwen-te-online-search-web-workspace";
	webWorkspace.setAttribute("role", "tabpanel");
	webWorkspace.setAttribute("aria-labelledby", webModeTab.button.id);
	webModeTab.button.setAttribute("aria-controls", webWorkspace.id);
	stack.appendChild(webWorkspace);
	const webHome = document.createElement("div");
	webHome.className = "qwen-te-online-search__web-home";
	webWorkspace.appendChild(webHome);
	const webHomeTitle = document.createElement("div");
	webHomeTitle.className = "qwen-te-online-search__web-home-title";
	webHomeTitle.textContent = "常用网站";
	webHome.appendChild(webHomeTitle);
	const webHomeGrid = document.createElement("div");
	webHomeGrid.className = "qwen-te-online-search__web-home-grid";
	webHome.appendChild(webHomeGrid);
	const webHomeButtons = [];
	for (const item of websiteBookmarks) {
		const button = document.createElement("button");
		button.type = "button";
		button.className = "qwen-te-online-search__site-button";
		button.dataset.qwenBrowserUrl = item.url;
		const icon = document.createElement("span");
		icon.className = "qwen-te-online-search__site-icon";
		icon.textContent = item.label.slice(0, 1).toUpperCase();
		button.appendChild(icon);
		const label = document.createElement("span");
		label.className = "qwen-te-online-search__site-label";
		label.textContent = item.label;
		button.appendChild(label);
		webHomeGrid.appendChild(button);
		webHomeButtons.push(button);
	}
	const webFrameShell = document.createElement("div");
	webFrameShell.className = "qwen-te-online-search__web-frame-shell qwen-te-hidden";
	webWorkspace.appendChild(webFrameShell);
	const webFrame = document.createElement("img");
	webFrame.className = "qwen-te-online-search__web-frame";
	webFrame.alt = "内嵌浏览器实时画面";
	webFrame.title = "点击网页后可直接操作；键盘输入会发送到当前网页焦点。";
	webFrame.draggable = false;
	webFrame.tabIndex = 0;
	webFrameShell.appendChild(webFrame);
	const webFrameOverlay = document.createElement("div");
	webFrameOverlay.className = "qwen-te-online-search__frame-overlay";
	webFrameOverlay.textContent = "正在准备内嵌浏览器...";
	webFrameShell.appendChild(webFrameOverlay);
	const webInputSink = document.createElement("textarea");
	webInputSink.className = "qwen-te-online-search__input-sink";
	webInputSink.tabIndex = -1;
	webInputSink.setAttribute("aria-hidden", "true");
	webInputSink.setAttribute("autocomplete", "off");
	dialog.appendChild(webInputSink);
	const frameExternalButton = document.createElement("button");
	frameExternalButton.type = "button";
	frameExternalButton.className = "qwen-te-online-search__frame-external";
	frameExternalButton.textContent = "▣ 独立浏览器";
	frameExternalButton.title = "在真正的 Edge/Chromium 窗口中打开当前网页，支持标签页、下载、登录和证书操作";
	frameExternalButton.disabled = true;
	webFrameShell.appendChild(frameExternalButton);

	let requestId = 0;
	let candidateTags = [];
	let candidateItems = [];
	let sampleTexts = [];
	let activeGroupFilter = "all";
	let activeMetaFilter = "all";
	const groupFilterButtons = new Map();
	const metaFilterButtons = new Map();
	const resultCards = new Map();
	const selectedTags = new Set();
	const isHighConfidence = (item) => Number(item?.confidence ?? 0) >= 0.72;
	let queryHistory = [];
	let queryHistoryIndex = -1;
	let tagQueryDraft = "";
	let tagAddressBadgeText = "提示词";
	let webAddressDraft = "";
	let webHistory = [PROMPT_BROWSER_HOME_ENTRY];
	let webHistoryIndex = 0;
	let currentWebUrl = "";
	let companionBrowserBusy = false;
	let embeddedNavigationBusy = false;
	let embeddedBrowserSessionId = "";
	let embeddedBrowserFallbackActive = Date.now() < promptBrowserEmbeddedRetryAfter;
	let embeddedBrowserWidth = 1280;
	let embeddedBrowserHeight = 720;
	let embeddedCanGoBack = false;
	let embeddedCanGoForward = false;
	let embeddedFrameTimer = null;
	let embeddedStatusTimer = null;
	let embeddedResizeTimer = null;
	let embeddedFrameBusy = false;
	let embeddedStatusBusy = false;
	let embeddedResizeBusy = false;
	let embeddedResizePending = false;
	let embeddedFrameObjectUrl = "";
	let embeddedLastFrameId = "";
	let embeddedUnchangedFrameCount = 0;
	let embeddedFrameFastUntil = 0;
	let embeddedPageReady = false;
	let embeddedPointerDown = false;
	let embeddedPointerButton = "left";
	let embeddedPointerButtons = 0;
	let embeddedLastPointerMoveAt = 0;
	let embeddedPointerMovePayload = null;
	let embeddedPointerMoveBusy = false;
	let embeddedInputQueue = Promise.resolve();
	let embeddedWheelTimer = null;
	let embeddedWheelPayload = null;
	let embeddedWheelBusy = false;
	let embeddedTextTimer = null;
	let embeddedPendingText = "";
	let embeddedViewportObserver = null;
	let busyState = false;
	const isContinuousRunActive = () => !!ensureNodeContinuousRuntime(node).running;
	const isInteractionBlocked = () => busyState || isContinuousRunActive();
	const rejectDuringContinuousRun = () => {
		if (!isContinuousRunActive()) return false;
		statusEl.textContent = "连续测试进行中，请先停止再搜索、回填、复制或拆分入库。";
		syncActionButtons();
		return true;
	};
	const matchesMetaFilter = (item) => {
		if (activeMetaFilter === "high") return isHighConfidence(item);
		if (activeMetaFilter === "concise") return Number(item?.length ?? String(item?.tag ?? "").length) < 180;
		if (activeMetaFilter === "detailed") return Number(item?.length ?? String(item?.tag ?? "").length) >= 180;
		return true;
	};
	const getFilteredItems = () => {
		return candidateItems.filter((item) => {
			const groupPass = activeGroupFilter === "all" || String(item?.group ?? "").trim() === activeGroupFilter;
			return groupPass && matchesMetaFilter(item);
		});
	};
	const getSelectedItems = () => {
		if (!selectedTags.size) return [];
		return candidateItems.filter((item) => selectedTags.has(item?.tag));
	};
	const renderSummaryBar = () => {
		summaryBar.replaceChildren();
		const items = [
			"提示词 " + candidateItems.length,
			"优选 " + candidateItems.filter((item) => isHighConfidence(item)).length,
			"精简 " + candidateItems.filter((item) => Number(item?.length ?? 0) < 180).length,
			"详细 " + candidateItems.filter((item) => Number(item?.length ?? 0) >= 180).length,
			`已选择 ${selectedTags.size}`,
		];
		for (const text of items) {
			const pill = document.createElement("div");
			pill.className = "qwen-te-modal__content-pill";
			pill.textContent = text;
			summaryBar.appendChild(pill);
		}
		if (!candidateItems.length) {
			const pill = document.createElement("div");
			pill.className = "qwen-te-modal__content-pill qwen-te-modal__content-pill--muted";
			pill.textContent = "等待搜索结果";
			summaryBar.appendChild(pill);
		}
	};
	const setFilterButtonState = (button, active) => {
		button.classList.toggle("is-active", !!active);
	};
	const renderSelectionBadge = () => {
		selectedPreview.replaceChildren();
		if (!candidateItems.length) {
			selectionBadge.textContent = "已选择 0 条提示词";
			const empty = document.createElement("div");
			empty.className = "qwen-te-online-search__selected-empty";
			empty.textContent = "搜索后可在结果列表中选择完整提示词。";
			selectedPreview.appendChild(empty);
			return;
		}
		const selectedItems = getSelectedItems();
		if (!selectedItems.length) {
			selectionBadge.textContent = "已选择 0 条提示词";
			const empty = document.createElement("div");
			empty.className = "qwen-te-online-search__selected-empty";
			empty.textContent = "未选择时不会执行回填、复制或拆分入库。";
			selectedPreview.appendChild(empty);
			return;
		}
		selectionBadge.textContent = "已选择 " + selectedItems.length + " 条提示词";
		for (const item of selectedItems.slice(0, 12)) {
			const chip = document.createElement("button");
			chip.type = "button";
			chip.className = "qwen-te-online-search__selected-chip";
			chip.textContent = `${item.tag} ×`;
			chip.title = `移除 ${item.tag}`;
			chip.disabled = isInteractionBlocked();
			chip.onclick = () => {
				if (isInteractionBlocked()) return;
				selectedTags.delete(item.tag);
				renderResults();
			};
			selectedPreview.appendChild(chip);
		}
		if (selectedItems.length > 12) {
			const more = document.createElement("span");
			more.className = "qwen-te-online-search__selected-more";
			more.textContent = "另有 " + (selectedItems.length - 12) + " 条";
			selectedPreview.appendChild(more);
		}
	};
const getEffectiveSelectionCounts = () => {
        const selectedPrompts = getEffectiveSelection({ onlyHighConfidence: false });
        return {
            applyCount: selectedPrompts.length,
            importCount: parseCustomTags(selectedPrompts.join(", ")).length,
            importHighCount: selectedPrompts.length,
        };
    };
	const getPromptBrowserCurrentOrigin = () => {
		try { return new URL(String(location?.href ?? "")).origin; } catch (_error) { return ""; }
	};
	const setWebStatus = (text) => {
		webStatusEl.textContent = String(text ?? "");
		webStatusEl.title = webStatusEl.textContent;
	};
	const setWebFrameOverlay = (text, options = {}) => {
		const message = String(text ?? "").trim();
		webFrameOverlay.textContent = message;
		webFrameOverlay.classList.toggle("qwen-te-hidden", !message);
		webFrameOverlay.classList.toggle("is-passive", !!options.passive && !!message);
	};
	const revokeEmbeddedFrameObjectUrl = () => {
		if (!embeddedFrameObjectUrl) return;
		try { URL.revokeObjectURL(embeddedFrameObjectUrl); } catch (_error) {}
		embeddedFrameObjectUrl = "";
	};
	const stopEmbeddedBrowserPolling = (options = {}) => {
		if (embeddedFrameTimer != null) clearTimeout(embeddedFrameTimer);
		if (embeddedStatusTimer != null) clearTimeout(embeddedStatusTimer);
		if (embeddedResizeTimer != null) clearTimeout(embeddedResizeTimer);
		embeddedFrameTimer = null;
		embeddedStatusTimer = null;
		embeddedResizeTimer = null;
		abortOwnedRequest(overlay, "embedded-browser-frame");
		abortOwnedRequest(overlay, "embedded-browser-status");
		abortOwnedRequest(overlay, "embedded-browser-resize");
		if (options.revokeFrame) {
			revokeEmbeddedFrameObjectUrl();
			webFrame.removeAttribute("src");
		}
	};
	const applyEmbeddedBrowserStatus = (payload, options = {}) => {
		if (!payload || typeof payload !== "object") return;
		embeddedBrowserWidth = Math.max(1, Number(payload.width ?? embeddedBrowserWidth) || embeddedBrowserWidth);
		embeddedBrowserHeight = Math.max(1, Number(payload.height ?? embeddedBrowserHeight) || embeddedBrowserHeight);
		embeddedCanGoBack = !!payload.can_go_back;
		embeddedCanGoForward = !!payload.can_go_forward;
		const reportedUrl = String(payload.url ?? "").trim();
		if (/^https?:\/\//iu.test(reportedUrl)) {
			currentWebUrl = reportedUrl;
			webAddressDraft = reportedUrl;
			if (activeBrowserMode === "web" && document.activeElement !== searchInput) searchInput.value = reportedUrl;
		}
		embeddedPageReady = String(payload.ready_state ?? "") === "complete";
		if (options.updateMessage !== false) {
			setWebStatus(`${payload.browser || "内嵌浏览器"} · ${embeddedPageReady ? "页面已就绪" : "页面加载中"}${reportedUrl ? ` · ${reportedUrl}` : ""}`);
		}
		syncActionButtons();
	};
	const getEmbeddedFrameCaptureOptions = () => getEmbeddedBrowserFrameCaptureProfile(
		webFrameShell.getBoundingClientRect?.(),
		{
			fast: Date.now() < embeddedFrameFastUntil,
			hasFrame: !!embeddedFrameObjectUrl,
			pageReady: embeddedPageReady,
			pixelRatio: globalThis.devicePixelRatio,
		},
	);
	const getEmbeddedFramePollDelay = () => {
		if (typeof document !== "undefined" && document.hidden) return 4000;
		if (Date.now() < embeddedFrameFastUntil) return 72;
		if (!embeddedPageReady || !embeddedFrameObjectUrl) return 120;
		if (embeddedUnchangedFrameCount >= 4) return 1600;
		return 420;
	};
	const scheduleEmbeddedFramePoll = (delay = null) => {
		if (overlay.__qwenDisposed || !embeddedBrowserSessionId || activeBrowserMode !== "web") return;
		if (embeddedFrameTimer != null) clearTimeout(embeddedFrameTimer);
		const resolvedDelay = delay == null ? getEmbeddedFramePollDelay() : Number(delay);
		const normalizedDelay = Number.isFinite(resolvedDelay) ? resolvedDelay : 120;
		embeddedFrameTimer = setTimeout(() => { embeddedFrameTimer = null; void pollEmbeddedBrowserFrame(); }, Math.max(48, normalizedDelay));
		embeddedFrameTimer?.unref?.();
	};
	const markEmbeddedBrowserActivity = (durationMs = 1800) => {
		embeddedFrameFastUntil = Math.max(embeddedFrameFastUntil, Date.now() + Math.max(400, Number(durationMs) || 1800));
		embeddedUnchangedFrameCount = 0;
		scheduleEmbeddedFramePoll(0);
	};
	const scheduleEmbeddedStatusPoll = (delay = 800) => {
		if (overlay.__qwenDisposed || !embeddedBrowserSessionId || activeBrowserMode !== "web") return;
		if (embeddedStatusTimer != null) clearTimeout(embeddedStatusTimer);
		embeddedStatusTimer = setTimeout(() => { embeddedStatusTimer = null; void pollEmbeddedBrowserStatus(); }, Math.max(300, Number(delay) || 800));
		embeddedStatusTimer?.unref?.();
	};
	const pollEmbeddedBrowserFrame = async () => {
		if (embeddedFrameBusy || overlay.__qwenDisposed || !embeddedBrowserSessionId || activeBrowserMode !== "web") return;
		embeddedFrameBusy = true;
		const sessionId = embeddedBrowserSessionId;
		try {
			const frameCapture = getEmbeddedFrameCaptureOptions();
            const frameResult = await fetchEmbeddedPromptBrowserFrame(sessionId, {
				owner: overlay,
				key: "embedded-browser-frame",
				previousFrameId: embeddedLastFrameId,
                maxWidth: frameCapture.maxWidth,
                maxHeight: frameCapture.maxHeight,
                quality: frameCapture.quality,
				timeoutMs: 20000,
			});
			if (overlay.__qwenDisposed || sessionId !== embeddedBrowserSessionId) return;
			if (!frameResult.changed || !frameResult.blob) {
				embeddedUnchangedFrameCount += 1;
				if (frameResult.frameId) embeddedLastFrameId = frameResult.frameId;
				return;
			}
			embeddedUnchangedFrameCount = 0;
			if (frameResult.frameId) embeddedLastFrameId = frameResult.frameId;
			const nextUrl = URL.createObjectURL(frameResult.blob);
			const previousUrl = embeddedFrameObjectUrl;
			embeddedFrameObjectUrl = nextUrl;
			if (previousUrl) {
				let revoked = false;
				const revokePrevious = () => {
					if (revoked) return;
					revoked = true;
					try { URL.revokeObjectURL(previousUrl); } catch (_error) {}
				};
				webFrame.addEventListener("load", revokePrevious, { once: true });
				setTimeout(revokePrevious, 5000)?.unref?.();
			}
			webFrame.src = nextUrl;
			setWebFrameOverlay("");
		} catch (error) {
			if (isAbortLikeError(error) || overlay.__qwenDisposed || sessionId !== embeddedBrowserSessionId) return;
			setWebFrameOverlay(`画面更新失败：${error?.message ?? error}`, { passive: !!embeddedFrameObjectUrl });
			if ([404, 503].includes(Number(error?.status ?? 0))) embeddedBrowserSessionId = "";
		} finally {
			embeddedFrameBusy = false;
			if (embeddedBrowserSessionId) scheduleEmbeddedFramePoll();
		}
	};
	const pollEmbeddedBrowserStatus = async () => {
		if (embeddedStatusBusy || overlay.__qwenDisposed || !embeddedBrowserSessionId || activeBrowserMode !== "web") return;
		embeddedStatusBusy = true;
		const sessionId = embeddedBrowserSessionId;
		try {
			const data = await requestEmbeddedPromptBrowser("status", { session_id: sessionId }, {
				owner: overlay,
				key: "embedded-browser-status",
				timeoutMs: 10000,
			});
			if (!overlay.__qwenDisposed && sessionId === embeddedBrowserSessionId) applyEmbeddedBrowserStatus(data);
		} catch (error) {
			if (!isAbortLikeError(error) && !overlay.__qwenDisposed) {
				setWebStatus(`内嵌浏览器状态读取失败：${error?.message ?? error}`);
				if ([404, 503].includes(Number(error?.status ?? 0))) embeddedBrowserSessionId = "";
			}
		} finally {
			embeddedStatusBusy = false;
			scheduleEmbeddedStatusPoll(embeddedBrowserSessionId ? (embeddedPageReady ? 1200 : 400) : 1800);
		}
	};
	const startEmbeddedBrowserPolling = () => {
		scheduleEmbeddedFramePoll(0);
		scheduleEmbeddedStatusPoll(300);
		scheduleEmbeddedViewportSync(80);
	};
	const syncEmbeddedBrowserViewport = async () => {
		if (embeddedResizeBusy || overlay.__qwenDisposed || !embeddedBrowserSessionId || activeBrowserMode !== "web") {
			embeddedResizePending = embeddedResizeBusy && !!embeddedBrowserSessionId;
			return;
		}
		const viewport = resolveEmbeddedBrowserViewport(webFrameShell.getBoundingClientRect?.(), {
			minWidth: 640,
			minHeight: 360,
			maxWidth: 1920,
			maxHeight: 1080,
			fallbackWidth: embeddedBrowserWidth,
			fallbackHeight: embeddedBrowserHeight,
		});
		if (Math.abs(viewport.width - embeddedBrowserWidth) <= 2 && Math.abs(viewport.height - embeddedBrowserHeight) <= 2) return;
		embeddedResizeBusy = true;
		embeddedResizePending = false;
		const sessionId = embeddedBrowserSessionId;
		try {
			const data = await requestEmbeddedPromptBrowser("resize", {
				session_id: sessionId,
				width: viewport.width,
				height: viewport.height,
			}, {
				owner: overlay,
				key: "embedded-browser-resize",
				timeoutMs: 12000,
			});
			if (overlay.__qwenDisposed || sessionId !== embeddedBrowserSessionId) return;
			embeddedLastFrameId = "";
			applyEmbeddedBrowserStatus(data, { updateMessage: false });
			markEmbeddedBrowserActivity(900);
		} catch (error) {
			if (!isAbortLikeError(error) && !overlay.__qwenDisposed && sessionId === embeddedBrowserSessionId) {
				setWebStatus(`浏览器尺寸同步失败：${error?.message ?? error}`);
			}
		} finally {
			embeddedResizeBusy = false;
			if (embeddedResizePending && embeddedBrowserSessionId) scheduleEmbeddedViewportSync(80);
		}
	};
	const scheduleEmbeddedViewportSync = (delay = 140) => {
		if (overlay.__qwenDisposed || !embeddedBrowserSessionId || activeBrowserMode !== "web") return;
		if (embeddedResizeTimer != null) clearTimeout(embeddedResizeTimer);
		embeddedResizeTimer = setTimeout(() => {
			embeddedResizeTimer = null;
			void syncEmbeddedBrowserViewport();
		}, Math.max(60, Number(delay) || 140));
		embeddedResizeTimer?.unref?.();
	};
	const closeEmbeddedBrowserSession = async (options = {}) => {
		const sessionId = embeddedBrowserSessionId;
		embeddedBrowserSessionId = "";
		embeddedCanGoBack = false;
		embeddedCanGoForward = false;
		embeddedLastFrameId = "";
		embeddedUnchangedFrameCount = 0;
		embeddedFrameFastUntil = 0;
		embeddedPageReady = false;
		embeddedPointerDown = false;
		embeddedPointerButtons = 0;
		embeddedPointerMovePayload = null;
		embeddedResizePending = false;
		stopEmbeddedBrowserPolling({ revokeFrame: options.revokeFrame !== false });
		if (!sessionId) return false;
		try {
			await requestEmbeddedPromptBrowser("close", { session_id: sessionId }, {
				key: `embedded-browser-close-${sessionId}`,
				timeoutMs: 6000,
			});
			return true;
		} catch (_error) {
			return false;
		}
	};
	const sendEmbeddedBrowserInput = (payload) => {
		if (!embeddedBrowserSessionId || overlay.__qwenDisposed) return Promise.resolve(false);
		const sessionId = embeddedBrowserSessionId;
		markEmbeddedBrowserActivity(payload?.type === "mouseMove" ? 650 : 1800);
		embeddedInputQueue = embeddedInputQueue.catch(() => false).then(async () => {
			if (!sessionId || sessionId !== embeddedBrowserSessionId || overlay.__qwenDisposed) return false;
			await requestEmbeddedPromptBrowser("input", { session_id: sessionId, ...payload }, {
				owner: overlay,
				key: "embedded-browser-input",
				replace: false,
				timeoutMs: 10000,
			});
			if (payload?.type === "mouseUp") scheduleEmbeddedStatusPoll(160);
			scheduleEmbeddedFramePoll(0);
			return true;
		});
		return embeddedInputQueue;
	};
	const flushEmbeddedBrowserPointerMove = async () => {
		if (embeddedPointerMoveBusy) return;
		const payload = embeddedPointerMovePayload;
		embeddedPointerMovePayload = null;
		if (!payload) return;
		embeddedPointerMoveBusy = true;
		try {
			await sendEmbeddedBrowserInput(payload);
		} finally {
			embeddedPointerMoveBusy = false;
			if (embeddedPointerMovePayload && embeddedBrowserSessionId) void flushEmbeddedBrowserPointerMove();
		}
	};
	const queueEmbeddedBrowserPointerMove = (payload) => {
		embeddedPointerMovePayload = payload ?? null;
		markEmbeddedBrowserActivity(650);
		if (!embeddedPointerMoveBusy) void flushEmbeddedBrowserPointerMove();
	};
	const flushEmbeddedBrowserWheel = async () => {
		if (embeddedWheelTimer != null) clearTimeout(embeddedWheelTimer);
		embeddedWheelTimer = null;
		if (embeddedWheelBusy) return;
		const payload = embeddedWheelPayload;
		embeddedWheelPayload = null;
		if (!payload || (!payload.delta_x && !payload.delta_y)) return;
		embeddedWheelBusy = true;
		try {
			await sendEmbeddedBrowserInput(payload);
		} finally {
			embeddedWheelBusy = false;
			if (embeddedWheelPayload && embeddedBrowserSessionId) {
				embeddedWheelTimer = setTimeout(() => { void flushEmbeddedBrowserWheel(); }, 0);
				embeddedWheelTimer?.unref?.();
			}
		}
	};
    const queueEmbeddedBrowserWheel = (payload) => {
        const next = payload ?? {};
        if (!embeddedWheelPayload) {
            embeddedWheelPayload = { ...next, delta_x: 0, delta_y: 0 };
        } else {
            embeddedWheelPayload.x = next.x;
            embeddedWheelPayload.y = next.y;
            embeddedWheelPayload.modifiers = next.modifiers;
        }
        embeddedWheelPayload.delta_x += Number(next.delta_x) || 0;
        embeddedWheelPayload.delta_y += Number(next.delta_y) || 0;
		markEmbeddedBrowserActivity(900);
		if (embeddedWheelBusy || embeddedWheelTimer != null) return;
		embeddedWheelTimer = setTimeout(() => { void flushEmbeddedBrowserWheel(); }, 24);
        embeddedWheelTimer?.unref?.();
    };
    const flushEmbeddedBrowserText = () => {
        if (embeddedTextTimer != null) clearTimeout(embeddedTextTimer);
        embeddedTextTimer = null;
        const value = embeddedPendingText;
        embeddedPendingText = "";
        if (value) void sendEmbeddedBrowserInput({ type: "text", text: value });
    };
    const queueEmbeddedBrowserText = (value) => {
        const textValue = String(value ?? "");
        if (!textValue) return;
        embeddedPendingText += textValue;
        if (embeddedTextTimer != null) return;
		embeddedTextTimer = setTimeout(flushEmbeddedBrowserText, 32);
        embeddedTextTimer?.unref?.();
    };
	const runEmbeddedBrowserCommand = async (action) => {
		if (!embeddedBrowserSessionId) return false;
		try {
			const data = await requestEmbeddedPromptBrowser("command", {
				session_id: embeddedBrowserSessionId,
				action,
			}, { owner: overlay, key: `embedded-browser-command-${action}`, timeoutMs: 15000 });
			if (!overlay.__qwenDisposed) applyEmbeddedBrowserStatus(data);
			return true;
		} catch (error) {
			if (!overlay.__qwenDisposed) setWebStatus(`浏览器命令失败：${error?.message ?? error}`);
			return false;
		}
	};
	const showWebHome = (options = {}) => {
		if (options.recordHistory !== false) {
			const next = pushOnlineSearchBrowserHistory(webHistory, webHistoryIndex, PROMPT_BROWSER_HOME_ENTRY, 30);
			webHistory = next.items;
			webHistoryIndex = next.index;
		}
		void closeEmbeddedBrowserSession({ revokeFrame: true });
		embeddedBrowserFallbackActive = Date.now() < promptBrowserEmbeddedRetryAfter;
		currentWebUrl = "";
		webAddressDraft = "";
		if (activeBrowserMode === "web") searchInput.value = "";
		webFrameShell.classList.add("qwen-te-hidden");
		webHome.classList.remove("qwen-te-hidden");
		setWebStatus("主页");
		syncActionButtons();
	};
	const navigateWebsite = async (rawTarget, options = {}) => {
		if (embeddedNavigationBusy) {
			setWebStatus("内嵌浏览器正在启动或导航，请稍候。");
			return false;
		}
		const target = options.resolved
			? { ok: true, kind: "url", url: String(rawTarget ?? "").trim(), display: String(rawTarget ?? "").trim() }
			: resolvePromptBrowserTarget(rawTarget, { currentOrigin: getPromptBrowserCurrentOrigin() });
		if (!target.ok) {
			setWebStatus(target.message || "网址无效。");
			syncActionButtons();
			return false;
		}
		if (embeddedBrowserFallbackActive && Date.now() >= promptBrowserEmbeddedRetryAfter) {
			embeddedBrowserFallbackActive = false;
		}
		if (options.recordHistory !== false) {
			const next = pushOnlineSearchBrowserHistory(webHistory, webHistoryIndex, target.url, 30);
			webHistory = next.items;
			webHistoryIndex = next.index;
		}
		currentWebUrl = target.url;
		webAddressDraft = target.url;
		if (activeBrowserMode === "web") searchInput.value = target.url;
		webHome.classList.add("qwen-te-hidden");
		webFrameShell.classList.remove("qwen-te-hidden");
		if (embeddedBrowserFallbackActive && !embeddedBrowserSessionId && !options.forceEmbedded) {
			setWebFrameOverlay("正在打开独立浏览器...", { passive: true });
			const companionResult = await openCurrentWebCompanion(target.url);
			if (companionResult) {
				setWebFrameOverlay("已切换到独立浏览器。该窗口支持标签页、下载、登录和证书操作。", { passive: true });
			}
			syncActionButtons();
			return companionResult;
		}
		setWebFrameOverlay(embeddedBrowserSessionId ? "正在导航..." : "正在启动本机内嵌浏览器...");
		embeddedNavigationBusy = true;
		syncActionButtons();
		setWebStatus(`正在内嵌浏览器中打开 ${target.url}`);
		try {
			let data;
			if (embeddedBrowserSessionId) {
				data = await requestEmbeddedPromptBrowser("navigate", {
					session_id: embeddedBrowserSessionId,
					url: target.url,
				}, { owner: overlay, key: "embedded-browser-navigate", timeoutMs: 30000 });
			} else {
				const startViewport = resolveEmbeddedBrowserViewport(webFrameShell.getBoundingClientRect?.(), {
				    minWidth: 640, minHeight: 360, maxWidth: 1920, maxHeight: 1080,
				    fallbackWidth: embeddedBrowserWidth, fallbackHeight: embeddedBrowserHeight,
				});
				embeddedBrowserWidth = startViewport.width;
				embeddedBrowserHeight = startViewport.height;
				data = await requestEmbeddedPromptBrowser("start", {
					url: target.url,
					width: embeddedBrowserWidth,
					height: embeddedBrowserHeight,
				}, { owner: overlay, key: "embedded-browser-start", timeoutMs: 60000 });
				embeddedBrowserSessionId = String(data.session_id ?? "");
				embeddedLastFrameId = "";
				embeddedUnchangedFrameCount = 0;
			}
			if (!embeddedBrowserSessionId) throw new Error("后端没有返回内嵌浏览器会话。");
			embeddedBrowserFallbackActive = false;
			promptBrowserEmbeddedRetryAfter = 0;
			applyEmbeddedBrowserStatus(data, { updateMessage: false });
			markEmbeddedBrowserActivity(2400);
			setWebStatus(`${data.browser || "内嵌浏览器"} 已启动，可直接点击和输入。`);
			startEmbeddedBrowserPolling();
			return true;
		} catch (error) {
			const message = isAbortLikeError(error)
				? "内嵌浏览器启动请求已取消，请稍后重试。"
				: String(error?.message ?? error);
			const status = Number(error?.status ?? 0) || 0;
			if ([500, 502, 503].includes(status) || /调试端口|内嵌浏览器不可用|启动失败/iu.test(message)) {
				embeddedBrowserFallbackActive = true;
				promptBrowserEmbeddedRetryAfter = Date.now() + PROMPT_BROWSER_EMBEDDED_RETRY_DELAY_MS;
				await closeEmbeddedBrowserSession({ revokeFrame: false });
				const companionResult = await openCurrentWebCompanion(target.url);
				if (companionResult) {
					setWebFrameOverlay("内嵌预览不可用，已自动打开独立浏览器。\n该窗口支持标签页、下载、登录和证书操作。", { passive: true });
					return true;
				}
			}
			setWebFrameOverlay(`内嵌浏览器不可用：${message}`);
			setWebStatus(`内嵌浏览器打开失败：${message}。可点击“独立浏览器”继续使用。`);
			if ([404, 503].includes(status)) embeddedBrowserSessionId = "";
			return false;
		} finally {
			embeddedNavigationBusy = false;
			if (!overlay.__qwenDisposed) syncActionButtons();
		}
	};
	const renderWebHistoryEntry = (entry) => {
		if (entry === PROMPT_BROWSER_HOME_ENTRY) {
			showWebHome({ recordHistory: false });
			return;
		}
		void navigateWebsite(entry, { recordHistory: false, resolved: true });
	};
	const openCurrentWebExternally = (rawTarget = "") => {
		const source = String(rawTarget || searchInput.value || currentWebUrl).trim();
		const result = openPromptBrowserExternal(source, { currentOrigin: getPromptBrowserCurrentOrigin() });
		if (!result.ok || !result.opened) {
			setWebStatus(result.message || "未能打开新标签页。");
			return false;
		}
		webAddressDraft = result.url;
		if (activeBrowserMode === "web") searchInput.value = result.url;
		setWebStatus(`已在新标签页打开 ${result.url}`);
		syncActionButtons();
		return true;
	};
	const openCurrentWebCompanion = async (rawTarget = "") => {
		if (companionBrowserBusy) return false;
		const source = String(rawTarget || searchInput.value || currentWebUrl).trim();
		companionBrowserBusy = true;
		setWebStatus("正在启动独立完整浏览器...");
		syncActionButtons();
		try {
			const result = await launchPromptCompanionBrowser(source, {
				currentOrigin: getPromptBrowserCurrentOrigin(),
				owner: overlay,
				key: "companion-browser",
			});
			if (overlay.__qwenDisposed) return false;
			if (!result.ok || !result.launched) {
				setWebStatus(result.message || "完整浏览器启动失败，请使用新标签页打开。");
				return false;
			}
			webAddressDraft = result.url;
			if (activeBrowserMode === "web") searchInput.value = result.url;
			setWebStatus(embeddedBrowserFallbackActive
				? `${result.browser || "完整浏览器"} 已启动，当前已切换为独立浏览器模式。`
				: `${result.browser || "完整浏览器"} 已启动。内嵌预览保持不变。`);
			return true;
		} finally {
			companionBrowserBusy = false;
			if (!overlay.__qwenDisposed) syncActionButtons();
		}
	};
	const setBrowserMode = (mode) => {
		const nextMode = mode === "tags" ? "tags" : "web";
		if (activeBrowserMode === "web") webAddressDraft = String(searchInput.value ?? "");
		else tagQueryDraft = String(searchInput.value ?? "");
		activeBrowserMode = nextMode;
		const tagMode = activeBrowserMode === "tags";
		webModeTab.button.classList.toggle("is-active", !tagMode);
		tagModeTab.button.classList.toggle("is-active", tagMode);
		webModeTab.button.setAttribute("aria-selected", tagMode ? "false" : "true");
		tagModeTab.button.setAttribute("aria-selected", tagMode ? "true" : "false");
		webModeTab.button.tabIndex = tagMode ? -1 : 0;
		tagModeTab.button.tabIndex = tagMode ? 0 : -1;
		contentGrid.classList.toggle("qwen-te-hidden", !tagMode);
		webWorkspace.classList.toggle("qwen-te-hidden", tagMode);
		tagQuickBar.classList.toggle("qwen-te-hidden", !tagMode);
		webQuickBar.classList.toggle("qwen-te-hidden", tagMode);
		statusEl.classList.toggle("qwen-te-hidden", !tagMode);
		webStatusEl.classList.toggle("qwen-te-hidden", tagMode);
		homeButton.classList.toggle("qwen-te-hidden", tagMode);
		openExternalButton.classList.toggle("qwen-te-hidden", tagMode);
		companionBrowserButton.classList.toggle("qwen-te-hidden", tagMode);
		addressBadge.textContent = tagMode ? tagAddressBadgeText : "网页";
		searchInput.maxLength = tagMode ? 256 : 2048;
		searchInput.placeholder = tagMode
			? "输入主题、风格或完整提示词片段，例如：柔和色彩、电影人像"
			: "输入网址或网页搜索词";
		searchInput.setAttribute("aria-label", tagMode ? "提示词搜索地址栏" : "网页浏览器地址栏");
		searchInput.value = tagMode ? tagQueryDraft : webAddressDraft;
		searchButton.textContent = tagMode ? "搜索" : "打开";
		searchButton.title = tagMode ? "执行联网提示词搜索" : "在内嵌网页中打开";
		browserNav.setAttribute("aria-label", tagMode ? "提示词搜索历史导航" : "网页导航");
		dialog.setAttribute("aria-labelledby", tagMode ? tagModeTab.title.id : webModeTab.title.id);
		if (tagMode) stopEmbeddedBrowserPolling();
		else if (embeddedBrowserSessionId) startEmbeddedBrowserPolling();
		syncActionButtons();
	};
	const syncActionButtons = () => {
		const counts = getEffectiveSelectionCounts();
		const runtimeBlocked = isContinuousRunActive();
		const interactionBlocked = busyState || runtimeBlocked;
		const tagMode = activeBrowserMode === "tags";
		const webTarget = resolvePromptBrowserTarget(searchInput.value, { currentOrigin: getPromptBrowserCurrentOrigin() });
		const externalTarget = resolvePromptBrowserTarget(
			String(searchInput.value ?? "").trim() || currentWebUrl,
			{ currentOrigin: getPromptBrowserCurrentOrigin() },
		);
		dialog.setAttribute("aria-busy", (tagMode && busyState) || (!tagMode && embeddedNavigationBusy) ? "true" : "false");
		searchInput.disabled = tagMode ? interactionBlocked : embeddedNavigationBusy;
		searchButton.disabled = tagMode ? interactionBlocked : embeddedNavigationBusy || !webTarget.ok;
		backButton.disabled = tagMode
			? interactionBlocked || queryHistoryIndex <= 0
			: embeddedNavigationBusy || !embeddedBrowserSessionId || !embeddedCanGoBack;
		forwardButton.disabled = tagMode
			? interactionBlocked || queryHistoryIndex < 0 || queryHistoryIndex >= queryHistory.length - 1
			: embeddedNavigationBusy || !embeddedBrowserSessionId || !embeddedCanGoForward;
		reloadButton.disabled = tagMode
			? interactionBlocked || !String(searchInput.value ?? "").trim()
			: embeddedNavigationBusy || !embeddedBrowserSessionId;
		homeButton.disabled = tagMode || embeddedNavigationBusy;
		openExternalButton.disabled = tagMode || !externalTarget.ok;
		companionBrowserButton.disabled = tagMode || companionBrowserBusy || !externalTarget.ok;
		frameExternalButton.disabled = companionBrowserBusy || !currentWebUrl;
		applyButton.disabled = interactionBlocked || counts.applyCount <= 0;
		importButton.disabled = interactionBlocked || counts.importCount <= 0;
		importHighButton.disabled = interactionBlocked || counts.applyCount <= 0;
		applyButton.textContent = counts.applyCount > 0 ? "回填提示词 (" + counts.applyCount + ")" : "回填提示词";
		importButton.textContent = counts.importCount > 0 ? "拆分入库 (" + counts.importCount + ")" : "拆分入库";
		importHighButton.textContent = counts.applyCount > 0 ? "复制提示词 (" + counts.applyCount + ")" : "复制提示词";
		for (const quickButton of quickButtons) quickButton.disabled = interactionBlocked;
		for (const button of groupFilterButtons.values()) button.disabled = interactionBlocked;
		for (const button of metaFilterButtons.values()) button.disabled = interactionBlocked;
		for (const card of resultCards.values()) card.disabled = interactionBlocked;
		for (const chip of selectedPreview.querySelectorAll?.("button") ?? []) chip.disabled = interactionBlocked;
		const blockedHint = runtimeBlocked ? "连续测试进行中，请先停止。" : "";
		for (const button of [applyButton, importButton, importHighButton]) {
			if (blockedHint) button.title = blockedHint;
			else if (button.title === "连续测试进行中，请先停止。") button.title = "";
		}
		if (tagMode && blockedHint) searchButton.title = blockedHint;
		else searchButton.title = tagMode ? "执行联网提示词搜索" : (embeddedBrowserFallbackActive ? "在独立浏览器中打开" : "在内嵌网页中打开");
		searchButton.classList.toggle("is-busy", tagMode ? busyState : embeddedNavigationBusy);
		companionBrowserButton.classList.toggle("is-busy", companionBrowserBusy);
	};
	const setBusy = (busy) => {
		busyState = !!busy;
		syncActionButtons();
	};
	const getGroupOptions = () => {
		const groups = new Set(["all"]);
		for (const item of candidateItems) {
			const group = String(item?.group ?? "").trim();
			if (!group) continue;
			groups.add(group);
		}
		return [...groups];
	};
	const renderGroupFilters = () => {
		filterBar.replaceChildren();
		groupFilterButtons.clear();
		const options = getGroupOptions();
		if (!options.length) return;
		if (!options.includes(activeGroupFilter)) activeGroupFilter = "all";
		for (const option of options) {
			const button = document.createElement("button");
			button.type = "button";
			button.className = "qwen-te-modal__preset";
			const count = option === "all"
				? candidateItems.length
				: candidateItems.filter((item) => String(item?.group ?? "").trim() === option).length;
			button.textContent = `${option === "all" ? "全部来源" : option} (${count})`;
			setFilterButtonState(button, option === activeGroupFilter);
			button.setAttribute("aria-pressed", option === activeGroupFilter ? "true" : "false");
			button.disabled = isInteractionBlocked();
			button.onclick = () => {
				if (isInteractionBlocked()) return;
				activeGroupFilter = option;
				renderGroupFilters();
				renderMetaFilters();
				renderResults();
			};
			filterBar.appendChild(button);
			groupFilterButtons.set(option, button);
		}
	};
    const renderMetaFilters = () => {
        metaFilterBar.replaceChildren();
        metaFilterButtons.clear();
        const options = [
            { key: "all", label: "全部提示词", count: candidateItems.length },
            { key: "high", label: "优选", count: candidateItems.filter((item) => isHighConfidence(item)).length },
            { key: "concise", label: "精简", count: candidateItems.filter((item) => Number(item?.length ?? String(item?.tag ?? "").length) < 180).length },
            { key: "detailed", label: "详细", count: candidateItems.filter((item) => Number(item?.length ?? String(item?.tag ?? "").length) >= 180).length },
        ];
        for (const option of options) {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "qwen-te-modal__preset";
            button.textContent = option.label + " (" + option.count + ")";
            setFilterButtonState(button, option.key === activeMetaFilter);
            button.setAttribute("aria-pressed", option.key === activeMetaFilter ? "true" : "false");
            button.disabled = isInteractionBlocked();
            button.onclick = () => {
                if (isInteractionBlocked()) return;
                activeMetaFilter = option.key;
                renderMetaFilters();
                renderResults();
            };
            metaFilterBar.appendChild(button);
            metaFilterButtons.set(option.key, button);
        }
    };
	const renderSelectionTools = () => {
		resultTools.replaceChildren();
		const tools = [
			{
				label: "全选当前筛选",
				onclick: () => {
					for (const item of getFilteredItems()) selectedTags.add(item.tag);
					renderResults();
				},
			},
			{
				label: "仅选优选",
				onclick: () => {
					selectedTags.clear();
					for (const item of getFilteredItems().filter((entry) => isHighConfidence(entry))) selectedTags.add(item.tag);
					renderResults();
				},
			},
			{
				label: "清空选择",
				onclick: () => {
					selectedTags.clear();
					renderResults();
				},
			},
		];
		for (const tool of tools) {
			const button = document.createElement("button");
			button.type = "button";
			button.className = "qwen-te-modal__mini-button";
			button.textContent = tool.label;
			button.disabled = isInteractionBlocked() || !candidateItems.length;
			button.onclick = () => {
				if (isInteractionBlocked()) return;
				tool.onclick();
			};
			resultTools.appendChild(button);
		}
	};
	const getEffectiveSelection = (options = {}) => {
		return resolveOnlineSearchSelectedTags(candidateItems, selectedTags, options);
	};
	const renderResults = () => {
		resultList.replaceChildren();
		resultCards.clear();
		const filteredItems = getFilteredItems();
		for (const item of filteredItems) {
			const tag = item.tag;
			const card = document.createElement("button");
			card.type = "button";
			card.className = "qwen-te-online-search__card";
			card.title = tag;
			card.classList.toggle("is-selected", selectedTags.has(tag));
			card.classList.toggle("is-high", isHighConfidence(item));
			card.classList.toggle("is-existing", !!item.exists);
			card.setAttribute("aria-pressed", selectedTags.has(tag) ? "true" : "false");
			card.setAttribute("aria-label", `${selectedTags.has(tag) ? "取消选择" : "选择"} ${tag}`);
			card.disabled = isInteractionBlocked();
			const route = document.createElement("div");
			route.className = "qwen-te-online-search__result-route";
			route.textContent = [String(item.group ?? "").trim(), String(item.section ?? "").trim()].filter(Boolean).join(" / ") || "提示词搜索结果";
			card.appendChild(route);

			const head = document.createElement("div");
			head.className = "qwen-te-online-search__card-head";
			card.appendChild(head);

			const name = document.createElement("div");
			name.className = "qwen-te-online-search__card-name";
			name.textContent = tag;
			head.appendChild(name);

			const pillBar = document.createElement("div");
			pillBar.className = "qwen-te-modal__content-pills qwen-te-online-search__result-badges";
			head.appendChild(pillBar);

			const highPill = document.createElement("div");
			highPill.className = `qwen-te-modal__content-pill${isHighConfidence(item) ? "" : " qwen-te-modal__content-pill--muted"}`;
			highPill.textContent = `置信 ${Math.round(Number(item.confidence ?? 0) * 100)}%`;
			pillBar.appendChild(highPill);

			const statusPill = document.createElement("div");
			statusPill.className = `qwen-te-modal__content-pill${item.exists ? " qwen-te-modal__content-pill--muted" : ""}`;
			statusPill.textContent = Number(item.length ?? tag.length) >= 180 ? "详细" : "精简";
			pillBar.appendChild(statusPill);

			const summaryLines = [];
			if (String(item.source ?? "").trim()) summaryLines.push(`来源 ${String(item.source ?? "").trim()}`);
			if (Number(item.count ?? 0) > 0) summaryLines.push("包含片段 " + Number(item.count ?? 0));
			const summary = document.createElement("div");
			summary.className = "qwen-te-online-search__card-summary";
			summary.textContent = summaryLines.join(" · ") || "该提示词来自当前搜索结果。";
			card.appendChild(summary);

			const foot = document.createElement("div");
			foot.className = "qwen-te-online-search__card-foot";
			card.appendChild(foot);

			const actionHint = document.createElement("div");
			actionHint.className = "qwen-te-online-search__hint";
			actionHint.textContent = selectedTags.has(tag) ? "已选择该提示词" : "点击选择该提示词";
			foot.appendChild(actionHint);

			card.onclick = () => {
				if (isInteractionBlocked()) return;
				if (selectedTags.has(tag)) selectedTags.delete(tag);
				else selectedTags.add(tag);
				const selected = selectedTags.has(tag);
				card.classList.toggle("is-selected", selected);
				card.setAttribute("aria-pressed", selected ? "true" : "false");
				card.setAttribute("aria-label", `${selected ? "取消选择" : "选择"} ${tag}`);
				actionHint.textContent = selected ? "已选择该提示词" : "点击选择该提示词";
				renderSummaryBar();
				renderSelectionBadge();
				syncActionButtons();
			};
			resultList.appendChild(card);
			resultCards.set(tag, card);
		}
		if (!filteredItems.length) {
			const empty = document.createElement("div");
			empty.className = "qwen-te-online-search__card-empty";
			empty.textContent = candidateItems.length ? "当前筛选下暂无提示词。" : "暂无提示词结果。";
			resultList.appendChild(empty);
		}
		sampleList.replaceChildren();
		if (sampleTexts.length) {
			sampleBox.value = sampleTexts.map((item, index) => `${index + 1}. ${item}`).join("\n\n");
			for (const [index, item] of sampleTexts.entries()) {
				const card = document.createElement("div");
				card.className = "qwen-te-online-search__sample-item";
				const badge = document.createElement("span");
				badge.className = "qwen-te-online-search__sample-item-index";
				badge.textContent = String(index + 1);
				card.appendChild(badge);
				card.appendChild(document.createTextNode(String(item ?? "")));
				sampleList.appendChild(card);
			}
			sampleList.classList.remove("qwen-te-hidden");
			sampleBox.classList.add("qwen-te-hidden");
		} else {
			sampleBox.value = "";
			const empty = document.createElement("div");
			empty.className = "qwen-te-online-search__card-empty";
			empty.textContent = candidateItems.length
				? "这次没有可用的完整提示词，请尝试更具体的主题或风格。"
				: "搜索后会在这里显示完整提示词。";
			sampleList.appendChild(empty);
			sampleList.classList.remove("qwen-te-hidden");
			sampleBox.classList.add("qwen-te-hidden");
		}
		renderSummaryBar();
		renderSelectionBadge();
		renderSelectionTools();
		syncActionButtons();
	};
	const runSearch = async (options = {}) => {
		if (busyState || rejectDuringContinuousRun()) return;
		const query = String(searchInput.value ?? "").trim();
		if (!query) {
			statusEl.textContent = "请输入关键词后再搜索。";
			return;
		}
		const compacted = options.queryIsEffective
			? { query, dropped: 0, normalized: false }
			: buildOnlineSearchQuery(query, 6);
		const effectiveQuery = String(compacted.query ?? "").trim();
		if (!effectiveQuery) {
			statusEl.textContent = "未提取到有效搜索词，请检查输入。";
			return;
		}
		if (options.recordHistory !== false) {
			const historyState = pushOnlineSearchBrowserHistory(queryHistory, queryHistoryIndex, effectiveQuery, 20);
			queryHistory = historyState.items;
			queryHistoryIndex = historyState.index;
		}
		const currentRequestId = ++requestId;
		setBusy(true);
		if (compacted.normalized) searchInput.value = effectiveQuery;
		tagAddressBadgeText = "正在搜索";
		if (activeBrowserMode === "tags") addressBadge.textContent = tagAddressBadgeText;
		statusEl.textContent = `联网搜索中：${effectiveQuery}${compacted.normalized ? "（已提炼关键词）" : ""}`;
		try {
			const result = await searchOnlinePromptTags(effectiveQuery, 30, { owner: overlay, key: "online-search" });
			if (currentRequestId !== requestId) return;
            candidateTags = [...(result.tags ?? [])];
            candidateItems = Array.isArray(result.promptItems) ? result.promptItems : [];
            sampleTexts = candidateItems.map((item) => String(item?.prompt ?? item?.tag ?? "")).filter(Boolean);
			activeGroupFilter = "all";
			activeMetaFilter = "all";
			selectedTags.clear();
			for (const item of candidateItems.filter((entry) => isHighConfidence(entry)).slice(0, 3)) selectedTags.add(item.tag);
			if (!selectedTags.size) for (const item of candidateItems.slice(0, 2)) selectedTags.add(item.tag);
			renderGroupFilters();
			renderMetaFilters();
			renderResults();
			const sourceMap = {
				searxng: "SearXNG",
				civitai: "Civitai",
				lexica: "Lexica",
				local_fallback: "本地回退",
				network_error: "网络异常回退",
			};
			const source = String(result.source ?? "")
				.split("+")
				.map((item) => sourceMap[item] ?? item)
				.filter(Boolean)
				.join("+") || "联网";
			const warningText = formatOnlineSearchWarning(result.warning);
			const warning = warningText ? `（来源状态：${warningText}）` : "";
			const cacheHint = result.cached ? "（复用近期搜索结果）" : "";
			const highCount = candidateItems.filter((item) => isHighConfidence(item)).length;
			const normalizeHint = compacted.normalized ? `（已过滤 ${compacted.dropped} 个低信息词）` : "";
			const fallbackHint = String(result.source ?? "").includes("local_fallback")
				? "（当前仅命中本地回退，可尝试英文词：adult / boudoir / half body）"
				: "";
            statusEl.textContent = source + "返回 " + candidateItems.length + " 条提示词，其中优选 " + highCount + " 条。" + cacheHint + normalizeHint + warning + fallbackHint;
			statusEl.title = statusEl.textContent;
			tagAddressBadgeText = result.cached ? "缓存" : source.split("+")[0] || "搜索";
			if (activeBrowserMode === "tags") addressBadge.textContent = tagAddressBadgeText;
		} catch (error) {
			if (currentRequestId !== requestId) return;
			candidateTags = [];
			candidateItems = [];
			sampleTexts = [];
			selectedTags.clear();
			renderGroupFilters();
			renderMetaFilters();
			renderResults();
			statusEl.textContent = `联网搜索失败：${error.message}`;
			statusEl.title = statusEl.textContent;
			tagAddressBadgeText = "失败";
			if (activeBrowserMode === "tags") addressBadge.textContent = tagAddressBadgeText;
		} finally {
			if (currentRequestId === requestId) setBusy(false);
		}
	};
	const applyToNode = async () => {
		if (busyState || rejectDuringContinuousRun()) return;
		const tagsToApply = getEffectiveSelection({ onlyHighConfidence: false });
		if (!tagsToApply.length) {
			statusEl.textContent = "没有可回填的提示词。";
			return;
		}
		setBusy(true);
		const currentRequestId = ++requestId;
		const isDialogOperationCurrent = () => currentRequestId === requestId && !overlay.__qwenDisposed;
		const mutationRevision = beginNodeStateMutation(node);
		try {
			const nextLibrary = await getFreshLibraryForUi(node, library, { mutationRevision, commitGuard: isDialogOperationCurrent });
			if (!isDialogOperationCurrent() || !isNodeStateMutationCurrent(node, mutationRevision)) return;
			const nextState = collectNodeState(node, nextLibrary);
			const mergedCustom = [...nextState.customTags];
			const beforeCount = mergedCustom.length;
			for (const tag of tagsToApply) addUniqueTag(mergedCustom, tag);
			const addedCount = Math.max(0, mergedCustom.length - beforeCount);
			const skippedCount = Math.max(0, tagsToApply.length - addedCount);
			nextState.customTags = mergedCustom;
			if (!isDialogOperationCurrent() || rejectDuringContinuousRun()) return;
			if (!applyNodeState(node, nextLibrary, nextState, { recordHistory: true, historySource: "manual-apply", mutationRevision })) return;
			statusEl.textContent = skippedCount > 0
				? `已处理 ${tagsToApply.length} 条提示词：新增 ${addedCount}，重复内容跳过 ${skippedCount}。`
				: `已回填 ${addedCount} 条提示词到“自定义补充标签”。`;
		} catch (error) {
			if (!isDialogOperationCurrent()) return;
			statusEl.textContent = `回填失败：${error.message}`;
		} finally {
			if (isDialogOperationCurrent()) setBusy(false);
		}
	};
    const copySelectedPrompts = async () => {
        if (busyState || rejectDuringContinuousRun()) return;
        const prompts = getEffectiveSelection({ onlyHighConfidence: false });
        if (!prompts.length) {
            statusEl.textContent = "没有可复制的提示词。";
            return;
        }
        const copied = await copyToClipboard(prompts.join("\n\n"));
        statusEl.textContent = copied
            ? "已复制 " + prompts.length + " 条提示词。"
            : "复制失败，请手动选择提示词文本。";
    };
	const importToLibrary = async () => {
		if (busyState || rejectDuringContinuousRun()) return;
        const selectedPrompts = getEffectiveSelection({ onlyHighConfidence: false });
        const tagsToImport = parseCustomTags(selectedPrompts.join(", "));
        if (!tagsToImport.length) {
            statusEl.textContent = "所选提示词没有可拆分入库的标签片段。";
            return;
        }
		setBusy(true);
		const currentRequestId = ++requestId;
		const isDialogOperationCurrent = () => currentRequestId === requestId && !overlay.__qwenDisposed;
		let addedCount = 0;
		try {
			const grouped = new Map();
			for (const batch of chunkOnlineImportTags(tagsToImport, 12)) {
				if (rejectDuringContinuousRun()) return;
				const suggest = await suggestCustomTagGrouping(batch.join(", "), { owner: overlay, key: "online-import-suggest" });
				if (!isDialogOperationCurrent()) return;
				for (const item of suggest.tags ?? []) {
					if (item?.exists) continue;
					const group = String(item?.recommended_group ?? "").trim();
					const section = String(item?.recommended_section ?? "").trim();
					const tag = String(item?.tag ?? "").trim();
					if (!group || !section || !tag) continue;
					const key = `${group}::${section}`;
					if (!grouped.has(key)) grouped.set(key, { group, section, tags: [] });
					const bucket = grouped.get(key);
					if (bucket && !bucket.tags.includes(tag)) bucket.tags.push(tag);
				}
			}
			for (const bucket of grouped.values()) {
				if (rejectDuringContinuousRun()) return;
				const response = await mutateTagLibrary("/qwen_te/tag_library/add_batch", {
					category: bucket.group,
					section: bucket.section,
					tag: bucket.tags.join(", "),
				}, { owner: overlay, key: "online-import-mutation" });
				if (!isDialogOperationCurrent()) return;
				addedCount += Number(response?.detail?.added?.length ?? 0);
			}
			const refreshedLibrary = await refreshLibraryOnNode(node, { commitGuard: isDialogOperationCurrent });
			if (!isDialogOperationCurrent()) return;
			const resolution = resolveOnlineSearchLibraryTags(tagsToImport, refreshedLibrary);
			candidateItems = candidateItems.map((item) => ({
				...item,
				exists: !!item.exists || resolution.existingKeys.has(getOnlineSearchCanonicalKey(item.tag)),
			}));
			const unresolvedCount = resolution.unresolvedTags.length;
			renderGroupFilters();
			renderMetaFilters();
			renderResults();
			if (addedCount > 0) {
				statusEl.textContent = "已拆分入库 " + addedCount + " 个标签片段" + (unresolvedCount > 0 ? "，" + unresolvedCount + " 个未能归类" : "") + "。";
			} else if (unresolvedCount > 0) {
				statusEl.textContent = `${unresolvedCount} 个标签未能归类，本次没有写入新标签。`;
			} else {
				statusEl.textContent = "所选标签已存在于标签库。";
			}
		} catch (error) {
			if (!isDialogOperationCurrent()) return;
			let confirmedCount = addedCount;
			let unresolvedCount = Math.max(0, tagsToImport.length - confirmedCount);
			try {
				const refreshedLibrary = await refreshLibraryOnNode(node, { commitGuard: isDialogOperationCurrent });
				if (!isDialogOperationCurrent()) return;
				const resolution = resolveOnlineSearchLibraryTags(tagsToImport, refreshedLibrary);
				confirmedCount = resolution.resolvedTags.length;
				unresolvedCount = resolution.unresolvedTags.length;
				candidateItems = candidateItems.map((item) => ({
					...item,
					exists: !!item.exists || resolution.existingKeys.has(getOnlineSearchCanonicalKey(item.tag)),
				}));
				renderGroupFilters();
				renderMetaFilters();
				renderResults();
			} catch (_refreshError) {}
			statusEl.textContent = confirmedCount > 0
				? `拆分入库未完全完成：已确认 ${confirmedCount} 个标签在库，${unresolvedCount} 个未完成。${error.message}`
				: `拆分入库失败：${error.message}`;
		} finally {
			if (isDialogOperationCurrent()) setBusy(false);
		}
	};

	searchButton.onclick = () => {
		if (activeBrowserMode === "web") void navigateWebsite(searchInput.value);
		else void runSearch();
	};
	const navigateSearchHistory = (direction) => {
		if (isInteractionBlocked()) return;
		const next = stepOnlineSearchBrowserHistory(queryHistory, queryHistoryIndex, direction);
		if (!next.query || next.index === queryHistoryIndex) return;
		queryHistory = next.items;
		queryHistoryIndex = next.index;
		searchInput.value = next.query;
		tagQueryDraft = next.query;
		void runSearch({ recordHistory: false, queryIsEffective: true });
	};
	const navigateWebHistory = (direction) => {
		if (!embeddedBrowserSessionId) return;
		void runEmbeddedBrowserCommand(Number(direction) < 0 ? "back" : "forward");
	};
	backButton.onclick = () => {
		if (activeBrowserMode === "web") navigateWebHistory(-1);
		else navigateSearchHistory(-1);
	};
	forwardButton.onclick = () => {
		if (activeBrowserMode === "web") navigateWebHistory(1);
		else navigateSearchHistory(1);
	};
	reloadButton.onclick = () => {
		if (activeBrowserMode === "web") {
			if (embeddedBrowserSessionId) void runEmbeddedBrowserCommand("reload");
			return;
		}
		if (isInteractionBlocked()) return;
		const typedQuery = String(searchInput.value ?? "").trim();
		if (!typedQuery) return;
		const historyQuery = String(queryHistory[queryHistoryIndex] ?? "").trim();
		const reusingHistoryQuery = !!historyQuery && typedQuery === historyQuery;
		void runSearch({ recordHistory: !reusingHistoryQuery, queryIsEffective: reusingHistoryQuery });
	};
	homeButton.onclick = () => showWebHome();
	openExternalButton.onclick = () => { void openCurrentWebExternally(); };
	companionBrowserButton.onclick = () => { void openCurrentWebCompanion(); };
	frameExternalButton.onclick = () => { void openCurrentWebCompanion(currentWebUrl); };
	for (const button of [...webBookmarkButtons, ...webHomeButtons]) {
		button.onclick = () => {
			const url = String(button.dataset.qwenBrowserUrl ?? "");
			searchInput.value = url;
			webAddressDraft = url;
			void navigateWebsite(url);
		};
	}
	webModeTab.button.onclick = () => { setBrowserMode("web"); searchInput.focus(); };
	tagModeTab.button.onclick = () => { setBrowserMode("tags"); searchInput.focus(); };
	browserTabs.addEventListener("keydown", (event) => {
		if (!['ArrowLeft', 'ArrowRight'].includes(event.key)) return;
		event.preventDefault();
		const nextMode = event.key === "ArrowRight"
			? (activeBrowserMode === "web" ? "tags" : "web")
			: (activeBrowserMode === "tags" ? "web" : "tags");
		setBrowserMode(nextMode);
		(nextMode === "web" ? webModeTab.button : tagModeTab.button).focus();
	});
	const getEmbeddedInputModifiers = (event) => {
		return (event.altKey ? 1 : 0) | (event.ctrlKey ? 2 : 0) | (event.metaKey ? 4 : 0) | (event.shiftKey ? 8 : 0);
	};
	const getEmbeddedPointerPoint = (event) => {
		if (!embeddedBrowserSessionId) return null;
		return mapEmbeddedBrowserPointerPoint(
			Number(event.clientX),
			Number(event.clientY),
			webFrame.getBoundingClientRect(),
			Number(webFrame.naturalWidth) || embeddedBrowserWidth,
			Number(webFrame.naturalHeight) || embeddedBrowserHeight,
			embeddedBrowserWidth,
			embeddedBrowserHeight,
		);
	};
	const focusEmbeddedKeyboard = () => {
		webInputSink.value = "";
		try { webInputSink.focus({ preventScroll: true }); } catch (_error) { webInputSink.focus(); }
	};
	const pointerButtonName = (button) => (["left", "middle", "right", "back", "forward"][Number(button)] ?? "left");
	webFrame.addEventListener("dragstart", (event) => { event.preventDefault(); });
	webFrame.addEventListener("pointerdown", (event) => {
		const point = getEmbeddedPointerPoint(event);
		if (!point) return;
		event.preventDefault();
		focusEmbeddedKeyboard();
		embeddedPointerDown = true;
		embeddedPointerMovePayload = null;
		embeddedPointerButton = pointerButtonName(event.button);
		embeddedPointerButtons = Number(event.buttons) || 1;
		try { webFrame.setPointerCapture(event.pointerId); } catch (_error) {}
		void sendEmbeddedBrowserInput({ type: "mouseDown", ...point, button: embeddedPointerButton, buttons: embeddedPointerButtons, modifiers: getEmbeddedInputModifiers(event) });
	});
	webFrame.addEventListener("pointermove", (event) => {
		if (!embeddedPointerDown) return;
		const now = performance.now();
		if (now - embeddedLastPointerMoveAt < 24) return;
		const point = getEmbeddedPointerPoint(event);
		if (!point) return;
		embeddedLastPointerMoveAt = now;
		queueEmbeddedBrowserPointerMove({ type: "mouseMove", ...point, button: embeddedPointerButton, buttons: Number(event.buttons) || embeddedPointerButtons, modifiers: getEmbeddedInputModifiers(event) });
	});
	const releaseEmbeddedPointer = (event) => {
		if (!embeddedPointerDown) return;
		const point = getEmbeddedPointerPoint(event);
		embeddedPointerDown = false;
		embeddedPointerButtons = 0;
		embeddedPointerMovePayload = null;
		try { webFrame.releasePointerCapture(event.pointerId); } catch (_error) {}
		if (point) void sendEmbeddedBrowserInput({ type: "mouseUp", ...point, button: embeddedPointerButton, buttons: 0, modifiers: getEmbeddedInputModifiers(event) });
	};
	webFrame.addEventListener("pointerup", releaseEmbeddedPointer);
	webFrame.addEventListener("pointercancel", releaseEmbeddedPointer);
	webFrame.addEventListener("contextmenu", (event) => { event.preventDefault(); });
	webFrame.addEventListener("wheel", (event) => {
		const point = getEmbeddedPointerPoint(event);
		if (!point) return;
		event.preventDefault();
		queueEmbeddedBrowserWheel({ type: "mouseWheel", ...point, delta_x: event.deltaX, delta_y: event.deltaY, modifiers: getEmbeddedInputModifiers(event) });
	}, { passive: false });
	const forwardedControlKeys = new Set(["Backspace", "Tab", "Enter", "Escape", "PageUp", "PageDown", "End", "Home", "ArrowLeft", "ArrowUp", "ArrowRight", "ArrowDown", "Insert", "Delete"]);
	webInputSink.addEventListener("keydown", (event) => {
		if (event.isComposing) return;
		if (!forwardedControlKeys.has(event.key) && !event.ctrlKey && !event.metaKey && !event.altKey) return;
		event.preventDefault();
		void sendEmbeddedBrowserInput({ type: "key", key: event.key, code: event.code, modifiers: getEmbeddedInputModifiers(event) });
	});
	webInputSink.addEventListener("beforeinput", (event) => {
		if (event.isComposing || !event.data) return;
		event.preventDefault();
		queueEmbeddedBrowserText(event.data);
	});
	webInputSink.addEventListener("compositionend", (event) => {
		if (event.data) queueEmbeddedBrowserText(event.data);
		webInputSink.value = "";
	});
	webInputSink.addEventListener("paste", (event) => {
		const text = String(event.clipboardData?.getData?.("text") ?? "");
		if (!text) return;
		event.preventDefault();
		flushEmbeddedBrowserText();
		void sendEmbeddedBrowserInput({ type: "text", text });
	});
	const handleEmbeddedBrowserVisibilityChange = () => {
		if (document.hidden || !embeddedBrowserSessionId || activeBrowserMode !== "web") return;
		markEmbeddedBrowserActivity(900);
		scheduleEmbeddedViewportSync(80);
	};
	document.addEventListener("visibilitychange", handleEmbeddedBrowserVisibilityChange);
	if (typeof ResizeObserver !== "undefined") {
		embeddedViewportObserver = new ResizeObserver(() => {
			if (!embeddedBrowserSessionId || activeBrowserMode !== "web") return;
			scheduleEmbeddedViewportSync();
		});
		embeddedViewportObserver.observe(webFrameShell);
	}
	applyButton.onclick = () => { void applyToNode(); };
	importButton.onclick = () => { void importToLibrary(); };
	importHighButton.onclick = () => { void copySelectedPrompts(); };
	searchInput.addEventListener("keydown", (event) => {
		if (event.isComposing || event.key !== "Enter") return;
		event.preventDefault();
		if (activeBrowserMode === "web") void navigateWebsite(searchInput.value);
		else void runSearch();
	});
	searchInput.addEventListener("input", () => {
		if (activeBrowserMode === "web") webAddressDraft = String(searchInput.value ?? "");
		else tagQueryDraft = String(searchInput.value ?? "");
		syncActionButtons();
	});
	const closeDialog = () => {
		disposeModalOverlay(overlay);
	};
	for (const eventName of ["pointerdown", "pointerup", "mousedown", "mouseup", "click", "dblclick", "contextmenu", "wheel", "touchstart", "touchmove", "touchend"]) {
		dialog.addEventListener(eventName, (event) => { event.stopPropagation(); });
	}
	dialog.addEventListener("keyup", (event) => { event.stopPropagation(); });
	dialog.addEventListener("keydown", (event) => {
		event.stopPropagation();
		if (event.key !== "Escape") return;
		event.preventDefault();
		closeDialog();
	});
	overlay.__qwenSyncRuntimeState = () => {
		if (isContinuousRunActive() && !busyState) statusEl.textContent = "连续测试进行中，请先停止再搜索、回填、复制或拆分入库。";
		syncActionButtons();
		renderSelectionTools();
	};
	overlay.__qwenDispose = () => {
		requestId += 1;
		if (embeddedWheelTimer != null) clearTimeout(embeddedWheelTimer);
		if (embeddedTextTimer != null) clearTimeout(embeddedTextTimer);
		embeddedWheelTimer = null;
		embeddedTextTimer = null;
		embeddedWheelPayload = null;
		embeddedPendingText = "";
		embeddedPointerMovePayload = null;
		embeddedViewportObserver?.disconnect?.();
		embeddedViewportObserver = null;
		document.removeEventListener("visibilitychange", handleEmbeddedBrowserVisibilityChange);
		void closeEmbeddedBrowserSession({ revokeFrame: true });
		webInputSink.value = "";
		delete overlay.__qwenSyncRuntimeState;
	};
	closeButton.onclick = closeDialog;
	overlay.addEventListener("click", (event) => { if (event.target === overlay) closeDialog(); });
	document.body.appendChild(overlay);

	const initialCustom = collectNodeState(node, library).customTags.join(", ");
	tagQueryDraft = buildOnlineSearchQuery(initialCustom, 4).query;
	renderGroupFilters();
	renderMetaFilters();
	renderSummaryBar();
	renderSelectionBadge();
	renderSelectionTools();
	setBusy(false);
	showWebHome({ recordHistory: false });
	setBrowserMode("web");
	searchInput.focus();
}

function openCharacterSheetDialog(node, library) {
	ensureSingleModal("character-sheet");
	const modalContext = buildNodeModalContext(node, library);
	const initialState = collectNodeState(node, library);
	let activeMode = (initialState.customTags ?? []).includes("纯提示词角色设计") ? "prompt" : "reference";
	const overlay = document.createElement("div");
	overlay.className = "qwen-te-modal";
	overlay.dataset.qwenModal = "character-sheet";
	overlay.__qwenNode = node;
	const dialog = document.createElement("div");
	dialog.className = "qwen-te-modal__dialog";
	overlay.appendChild(dialog);

	const header = document.createElement("div");
	header.className = "qwen-te-modal__header";
	dialog.appendChild(header);
	const titleWrap = document.createElement("div");
	header.appendChild(titleWrap);
	const title = document.createElement("div");
	title.className = "qwen-te-modal__title";
	title.textContent = "角色设定图";
	titleWrap.appendChild(title);
	const subtitle = document.createElement("div");
	subtitle.className = "qwen-te-modal__subtitle";
	subtitle.textContent = `生成多视角角色展示图；风格、服装、颜色和背景跟随输入。当前节点：${modalContext.nodeName}。`;
	titleWrap.appendChild(subtitle);
	const closeButton = document.createElement("button");
	closeButton.className = "qwen-te-modal__footer-button";
	closeButton.textContent = "关闭";
	header.appendChild(closeButton);

	const body = document.createElement("div");
	body.className = "qwen-te-modal__body";
	dialog.appendChild(body);
	const statusEl = document.createElement("div");
	statusEl.className = "qwen-te-modal__status qwen-te-modal__status--panel";
	statusEl.textContent = "参考单人图模式会启用节点的“参考图片”输入：接图后先反推，再生成角色设定图提示词；纯提示词模式不需要接图。";
	body.appendChild(statusEl);

	const modeBar = document.createElement("div");
	modeBar.className = "qwen-te-modal__template-groups";
	body.appendChild(modeBar);
	const modeButtons = new Map();
	const refreshModes = () => {
		for (const [key, button] of modeButtons.entries()) {
			button.classList.toggle("is-active", key === activeMode);
		}
	};
	for (const option of CHARACTER_SHEET_MODE_OPTIONS) {
		const card = document.createElement("button");
		card.type = "button";
		card.className = "qwen-te-modal__template-group qwen-te-modal__nav-button";
		card.style.alignItems = "stretch";
		card.style.flexDirection = "column";
		card.style.justifyContent = "flex-start";
		const name = document.createElement("div");
		name.className = "qwen-te-modal__template-group-title";
		name.textContent = option.label;
		card.appendChild(name);
		const desc = document.createElement("div");
		desc.className = "qwen-te-modal__content-sub";
		desc.textContent = option.desc;
		card.appendChild(desc);
		card.onclick = () => {
			activeMode = option.key;
			refreshModes();
			statusEl.textContent = activeMode === "reference"
				? "已选择参考单人图：请把图片接到本节点左侧“参考图片”输入。"
				: "已选择纯提示词：不接图片，直接按文字生成角色设定图提示词。";
		};
		modeBar.appendChild(card);
		modeButtons.set(option.key, card);
	}

	const promptInput = document.createElement("textarea");
	promptInput.className = "qwen-te-modal__textarea";
	promptInput.placeholder = "可选：补充你想保留的角色设定，例如：服装、发型、配色、材质、背景、镜头比例；不填则跟随当前标签或参考图。";
	body.appendChild(promptInput);
	const preview = document.createElement("div");
	preview.className = "qwen-te-modal__status";
	preview.textContent = CHARACTER_SHEET_PROMPTS[activeMode];
	body.appendChild(preview);

	const footer = document.createElement("div");
	footer.className = "qwen-te-modal__footer";
	dialog.appendChild(footer);
	const cancelButton = document.createElement("button");
	cancelButton.className = "qwen-te-modal__footer-button";
	cancelButton.textContent = "取消";
	footer.appendChild(cancelButton);
	const applyButton = document.createElement("button");
	applyButton.className = "qwen-te-modal__footer-button qwen-te-modal__footer-button--primary";
	applyButton.textContent = "启用";
	footer.appendChild(applyButton);
	const disableButton = document.createElement("button");
	disableButton.className = "qwen-te-modal__footer-button qwen-te-modal__footer-button--danger";
	disableButton.textContent = "停用";
	footer.appendChild(disableButton);

	const enableSheet = async () => {
		const mutationRevision = beginNodeStateMutation(node);
		const nextLibrary = await getFreshLibraryForUi(node, library, { mutationRevision });
		if (!isNodeStateMutationCurrent(node, mutationRevision)) return;
		const nextState = buildCharacterSheetState(node, nextLibrary, { mode: activeMode, userText: promptInput.value });
		if (!applyNodeState(node, nextLibrary, nextState, { recordHistory: true, historySource: "manual-apply", mutationRevision })) return;
		setNodeStatusText(node, `已启用角色设定图：${CHARACTER_SHEET_MODE_OPTIONS.find((item) => item.key === activeMode)?.label ?? activeMode}。`);
		refreshNodeActionButtons(node);
		overlay.remove();
	};
	const disableSheet = async () => {
		const mutationRevision = beginNodeStateMutation(node);
		const nextLibrary = await getFreshLibraryForUi(node, library, { mutationRevision });
		if (!isNodeStateMutationCurrent(node, mutationRevision)) return;
		const nextState = buildCharacterSheetDisabledState(node, nextLibrary);
		if (!applyNodeState(node, nextLibrary, nextState, { recordHistory: true, historySource: "manual-apply", mutationRevision })) return;
		setNodeStatusText(node, "已停用角色设定图模式。");
		refreshNodeActionButtons(node);
		overlay.remove();
	};
	const updatePreview = () => {
		preview.textContent = [String(promptInput.value ?? "").trim(), CHARACTER_SHEET_PROMPTS[activeMode]].filter(Boolean).join("\n\n");
	};
	promptInput.addEventListener("input", updatePreview);
	for (const [key, button] of modeButtons.entries()) {
		const originalClick = button.onclick;
		button.onclick = () => {
			originalClick?.();
			updatePreview();
		};
	}
	cancelButton.onclick = () => overlay.remove();
	closeButton.onclick = () => overlay.remove();
	applyButton.onclick = () => { void enableSheet(); };
	disableButton.onclick = () => { void disableSheet(); };
	overlay.addEventListener("click", (event) => { if (event.target === overlay) overlay.remove(); });
	document.body.appendChild(overlay);
	refreshModes();
	promptInput.focus();
}

function openQualityAuditDialog(node) {
	ensureSingleModal("quality-audit");
	const modalContext = buildNodeModalContext(node, node?.[PANEL_KEY]?.library ?? null);
	const overlay = document.createElement("div");
	overlay.className = "qwen-te-modal";
	overlay.dataset.qwenModal = "quality-audit";
	overlay.__qwenNode = node;
	const dialog = document.createElement("div");
	dialog.className = "qwen-te-modal__dialog";
	overlay.appendChild(dialog);

	const header = document.createElement("div");
	header.className = "qwen-te-modal__header";
	dialog.appendChild(header);
	const titleWrap = document.createElement("div");
	header.appendChild(titleWrap);
	const title = document.createElement("div");
	title.className = "qwen-te-modal__title";
	title.textContent = `图片质检 · ${modalContext.nodeName}`;
	titleWrap.appendChild(title);
	const subtitle = document.createElement("div");
	subtitle.className = "qwen-te-modal__subtitle";
	subtitle.textContent = `优先检查当前工作流最近一次成图中的 OCR 伪字、皮肤皱纹/过锐和过度磨皮风险；找不到时再回退到最近输出图片。当前输出来源：${modalContext.outputSource}。`;
	titleWrap.appendChild(subtitle);
	const closeButton = document.createElement("button");
	closeButton.className = "qwen-te-modal__footer-button";
	closeButton.textContent = "关闭";
	header.appendChild(closeButton);

	const body = document.createElement("div");
	body.className = "qwen-te-modal__body";
	dialog.appendChild(body);

	const toolbar = document.createElement("div");
	toolbar.className = "qwen-te-modal__toolbar";
	body.appendChild(toolbar);
	const refreshButton = document.createElement("button");
	refreshButton.className = "qwen-te-modal__footer-button qwen-te-modal__footer-button--primary";
	refreshButton.textContent = "重新质检";
	toolbar.appendChild(refreshButton);
	const copyButton = document.createElement("button");
	copyButton.className = "qwen-te-modal__footer-button";
	copyButton.textContent = "复制摘要";
	toolbar.appendChild(copyButton);

	const statusEl = document.createElement("div");
	statusEl.className = "qwen-te-modal__status qwen-te-modal__status--panel";
	statusEl.textContent = `准备定位当前工作流最近一次成图。当前已选标签 ${modalContext.tagCount} 个。`;
	body.appendChild(statusEl);

	const list = document.createElement("div");
	list.className = "qwen-te-preset-list";
	body.appendChild(list);

	let latestMarkdown = "";

	const renderResult = (result) => {
		list.replaceChildren();
		const summary = result?.summary ?? {};
		statusEl.textContent = `已质检 ${summary.total_images ?? 0} 张 | OCR 风险 ${summary.ocr_risk_images ?? 0} | 皱纹风险 ${summary.wrinkle_risk_images ?? 0} | 过磨皮风险 ${summary.oversmooth_risk_images ?? 0}`;
		const rows = Array.isArray(result?.images) ? result.images : [];
		if (!rows.length) {
			const empty = document.createElement("div");
			empty.className = "qwen-te-preset-card__summary";
			empty.textContent = "没有可展示的质检结果。";
			list.appendChild(empty);
			return;
		}
		for (const row of rows) {
			const card = document.createElement("div");
			card.className = "qwen-te-preset-card";
			list.appendChild(card);
			const head = document.createElement("div");
			head.className = "qwen-te-preset-card__header";
			card.appendChild(head);
			const name = document.createElement("div");
			name.className = "qwen-te-preset-card__name";
			name.textContent = String(row?.image ?? "").split(/[\\/]/u).pop() || "未命名图片";
			head.appendChild(name);
			const badges = document.createElement("div");
			badges.className = "qwen-te-preset-card__badges";
			card.appendChild(badges);
			const addBadge = (text, tone = "info") => {
				const badge = document.createElement("div");
				badge.className = `qwen-te-preset-card__badge qwen-te-preset-card__badge--${tone}`;
				badge.textContent = text;
				badges.appendChild(badge);
			};
			const ocr = row?.ocr ?? {};
			const faces = row?.faces ?? {};
			addBadge(`OCR ${ocr.risk_level ?? "n/a"} ${ocr.risk_score ?? "?"}`, ocr.risk_level === "high" ? "danger" : ocr.risk_level === "medium" ? "warn" : "info");
			addBadge(`皱纹 ${faces.wrinkle_risk_level ?? "n/a"} ${faces.wrinkle_risk_score ?? "?"}`, faces.wrinkle_risk_level === "high" ? "danger" : faces.wrinkle_risk_level === "medium" ? "warn" : "info");
			addBadge(`磨皮 ${faces.oversmooth_risk_level ?? "n/a"} ${faces.oversmooth_risk_score ?? "?"}`, faces.oversmooth_risk_level === "high" ? "danger" : faces.oversmooth_risk_level === "medium" ? "warn" : "info");
			const summary = document.createElement("div");
			summary.className = "qwen-te-preset-card__summary";
			const findings = Array.isArray(row?.findings) && row.findings.length ? row.findings.join(" | ") : "未发现明显风险";
			const recs = Array.isArray(row?.recommendations) ? row.recommendations.join(" | ") : "无建议";
			summary.textContent = `发现：${findings}\n建议：${recs}`;
			card.appendChild(summary);
		}
	};

	const runAudit = async () => {
		statusEl.textContent = "正在定位当前工作流输出并执行质检...";
		refreshButton.disabled = true;
		copyButton.disabled = true;
		try {
			const audit = await runNodeQualityAudit(node, { limit: 6, requestOwner: overlay });
			if (overlay.__qwenDisposed || audit?.stale) return;
			latestMarkdown = audit.markdown;
			renderResult(audit.result ?? {});
			copyButton.disabled = !latestMarkdown;
		} catch (error) {
			if (overlay.__qwenDisposed) return;
			statusEl.textContent = `质检失败：${error.message}`;
			list.replaceChildren();
			copyButton.disabled = true;
		} finally {
			if (!overlay.__qwenDisposed) refreshButton.disabled = false;
		}
	};

	refreshButton.onclick = () => { void runAudit(); };
	copyButton.onclick = async () => {
		if (!latestMarkdown) {
			statusEl.textContent = "当前没有可复制的质检摘要。";
			return;
		}
		const ok = await copyToClipboard(latestMarkdown);
		statusEl.textContent = ok ? "已复制质检摘要。" : "复制质检摘要失败。";
	};
	copyButton.disabled = true;
	overlay.__qwenDispose = () => {
		if (node) node[NODE_QUALITY_AUDIT_REVISION_KEY] = Math.max(0, Number(node[NODE_QUALITY_AUDIT_REVISION_KEY] ?? 0) || 0) + 1;
	};
	const closeQualityAudit = () => disposeModalOverlay(overlay);
	closeButton.onclick = closeQualityAudit;
	overlay.addEventListener("click", (event) => { if (event.target === overlay) closeQualityAudit(); });
	document.body.appendChild(overlay);
	void runAudit();
}

function openTagDialog(node, library) {
	ensureSingleModal("tag-dialog");
	const modalContext = buildNodeModalContext(node, library);
	const currentState = collectNodeState(node, library);
	const workingState = {
		selected: cloneSelection(currentState.selected),
		customTags: [...currentState.customTags],
		settings: { ...currentState.settings },
	};

	const overlay = document.createElement("div");
	overlay.className = "qwen-te-modal";
	overlay.dataset.qwenModal = "tag-dialog";
	overlay.__qwenNode = node;
	const dialog = document.createElement("div");
	dialog.className = "qwen-te-modal__dialog";
	overlay.appendChild(dialog);

	const header = document.createElement("div");
	header.className = "qwen-te-modal__header";
	dialog.appendChild(header);
	const titleWrap = document.createElement("div");
	header.appendChild(titleWrap);
	const title = document.createElement("div");
	title.className = "qwen-te-modal__title";
	title.textContent = "标签选择面板";
	titleWrap.appendChild(title);
	const subtitle = document.createElement("div");
	subtitle.className = "qwen-te-modal__subtitle";
	subtitle.textContent = `按分类选择标签并回填到节点，应用按钮已移动到顶部。当前输出来源：${modalContext.outputSource}。`;
	titleWrap.appendChild(subtitle);
	const closeButton = document.createElement("button");
	closeButton.className = "qwen-te-modal__footer-button";
	closeButton.textContent = "关闭";
	header.appendChild(closeButton);

	const body = document.createElement("div");
	body.className = "qwen-te-modal__body";
	dialog.appendChild(body);
	const toolbar = document.createElement("div");
	toolbar.className = "qwen-te-modal__toolbar";
	toolbar.style.cssText = "position:sticky;top:0;z-index:3;background:#171717;padding-bottom:8px;";
	body.appendChild(toolbar);
	const searchInput = document.createElement("input");
	searchInput.className = "qwen-te-modal__search";
	searchInput.placeholder = "搜索标签";
	toolbar.appendChild(searchInput);
	const resetButton = document.createElement("button");
	resetButton.className = "qwen-te-modal__footer-button";
	resetButton.textContent = "清空本次选择";
	toolbar.appendChild(resetButton);
	const manageButton = document.createElement("button");
	manageButton.className = "qwen-te-modal__footer-button";
	manageButton.textContent = "管理标签";
	toolbar.appendChild(manageButton);
	const applyButton = document.createElement("button");
	applyButton.className = "qwen-te-modal__footer-button qwen-te-modal__footer-button--primary";
	applyButton.textContent = "应用到节点";
	toolbar.appendChild(applyButton);

	const statusEl = document.createElement("div");
	statusEl.className = "qwen-te-modal__status";
	statusEl.textContent = `点击标签可切换选择。当前已选标签 ${modalContext.tagCount} 个。`;
	body.appendChild(statusEl);

	const split = document.createElement("div");
	split.className = "qwen-te-modal__split";
	body.appendChild(split);
	const sidebar = document.createElement("div");
	sidebar.className = "qwen-te-modal__sidebar";
	split.appendChild(sidebar);
	const sidebarTitle = document.createElement("div");
	sidebarTitle.className = "qwen-te-modal__sidebar-title";
	sidebarTitle.textContent = "标签目录";
	sidebar.appendChild(sidebarTitle);
	const nav = document.createElement("div");
	nav.className = "qwen-te-modal__nav";
	sidebar.appendChild(nav);
	const sidebarExtra = document.createElement("div");
	sidebarExtra.className = "qwen-te-modal__sidebar-section";
	sidebar.appendChild(sidebarExtra);
	const content = document.createElement("div");
	content.className = "qwen-te-modal__content";
	split.appendChild(content);

		const chipRecords = [];
		const sectionRecords = [];
		const groupRecords = [];
		const countElements = new Map();
		const navButtons = new Map();
		let activeGroupName = (library.slot_config ?? [])[0]?.name ?? "";
		let renderedGroupName = "";
		let currentGroupUi = null;
		let customSuggestTimer = null;
		let customSuggestRequestId = 0;
		let customArrangeRequestId = 0;
		let customArrangePreview = null;
		let customArrangeUndoState = null;
		let activeArrangeFilter = "all";
		const arrangeFilterButtons = new Map();
		const arrangeBulkButtons = new Map();
		const arrangeFilterLabels = {
			all: "全部",
			split: "拆分",
			replace: "规范替换",
			existing: "已有归位",
		};

	const toggleTag = (groupName, tag) => {
		const result = toggleBoundedTagSelection(
			workingState.selected,
			groupName,
			tag,
			getTagGroupSlotLimit(library, groupName),
		);
		if (result.reason === "full") {
			statusEl.textContent = `${groupName} 已达到 ${result.limit} 个标签上限，请先取消一个已选标签。`;
		} else if (result.changed) {
			statusEl.textContent = `${groupName} 已选 ${result.count} / ${result.limit} 个标签；当前总计 ${Object.values(workingState.selected).reduce((sum, items) => sum + (items?.length ?? 0), 0)} 个。`;
		}
		return result;
	};

	const renderCurrentGroupPills = (groupName) => {
		if (!currentGroupUi || currentGroupUi.groupName !== groupName) return;
		const { contentCount, contentPills } = currentGroupUi;
		const selectedTags = workingState.selected[groupName] ?? [];
		const limit = getTagGroupSlotLimit(library, groupName);
		contentCount.textContent = `${selectedTags.length} / ${limit}`;
		contentPills.replaceChildren();
		if (selectedTags.length) {
			for (const tag of selectedTags.slice(0, TAG_SELECTION_PILL_PREVIEW_LIMIT)) {
				const pill = document.createElement("button");
				pill.type = "button";
				pill.className = "qwen-te-modal__content-pill";
				pill.textContent = tag;
				pill.title = "点击移除此标签";
				pill.onclick = () => { toggleTag(groupName, tag); refreshSelectionUiOnly(); };
				contentPills.appendChild(pill);
			}
			if (selectedTags.length > TAG_SELECTION_PILL_PREVIEW_LIMIT) {
				const pill = document.createElement("div");
				pill.className = "qwen-te-modal__content-pill qwen-te-modal__content-pill--muted";
				pill.textContent = `+${selectedTags.length - TAG_SELECTION_PILL_PREVIEW_LIMIT}`;
				contentPills.appendChild(pill);
			}
		} else {
			const pill = document.createElement("div");
			pill.className = "qwen-te-modal__content-pill qwen-te-modal__content-pill--muted";
			pill.textContent = "当前分组还未选择标签";
			contentPills.appendChild(pill);
		}
	};

	const refreshSelectionUiOnly = () => {
		for (const chip of chipRecords) {
			const selectedTags = workingState.selected[chip.groupName] ?? [];
			const selected = selectedTags.includes(chip.tag);
			const limit = getTagGroupSlotLimit(library, chip.groupName);
			const blocked = !selected && selectedTags.length >= limit;
			chip.element.classList.toggle("is-selected", selected);
			chip.element.classList.toggle("is-capacity-blocked", blocked);
			chip.element.title = selected ? "点击取消选择" : (blocked ? `已达到本组 ${limit} 个标签上限` : "点击选择");
			chip.element.setAttribute?.("aria-disabled", blocked ? "true" : "false");
		}
		for (const group of library.slot_config ?? []) {
			const count = (workingState.selected[group.name] ?? []).length;
			const limit = getTagGroupSlotLimit(library, group.name);
			const countEl = countElements.get(group.name);
			if (countEl) countEl.textContent = `${count} / ${limit}`;
			const navRecord = navButtons.get(group.name);
			if (navRecord) navRecord.count.textContent = `${count}/${limit}`;
		}
		renderCurrentGroupPills(activeGroupName);
	};

	const setSectionOpen = (record, open) => {
		record.open = open;
		record.wrapper.classList.toggle("is-collapsed", !open);
		record.chips.classList.toggle("qwen-te-hidden", !open);
	};

	const renderGroupContent = (groupName) => {
		const previousScrollTop = content.scrollTop;
		const groupChanged = renderedGroupName !== groupName;
		renderedGroupName = groupName;
		content.replaceChildren();
		chipRecords.length = 0;
		sectionRecords.length = 0;
		const groupConfig = (library.slot_config ?? []).find((group) => group.name === groupName);
		if (!groupConfig) {
			const empty = document.createElement("div");
			empty.className = "qwen-te-modal__empty";
			empty.textContent = "当前没有可显示的标签分组。";
			content.appendChild(empty);
			return;
		}
		const contentHeader = document.createElement("div");
		contentHeader.className = "qwen-te-modal__content-header";
		content.appendChild(contentHeader);
		const contentTitle = document.createElement("div");
		contentTitle.className = "qwen-te-modal__content-title";
		contentHeader.appendChild(contentTitle);
		const contentName = document.createElement("div");
		contentName.className = "qwen-te-modal__content-name";
		contentName.textContent = groupConfig.name;
		contentTitle.appendChild(contentName);
		const contentCount = document.createElement("div");
		contentCount.className = "qwen-te-group__count";
		contentCount.textContent = `${(workingState.selected[groupConfig.name] ?? []).length} / ${getTagGroupSlotLimit(library, groupConfig.name)}`;
		contentTitle.appendChild(contentCount);
		const contentSub = document.createElement("div");
		contentSub.className = "qwen-te-modal__content-sub";
		contentSub.textContent = groupConfig.tooltip;
		contentHeader.appendChild(contentSub);
		const contentPills = document.createElement("div");
		contentPills.className = "qwen-te-modal__content-pills";
		contentHeader.appendChild(contentPills);
		currentGroupUi = { groupName: groupConfig.name, contentCount, contentPills };
		renderCurrentGroupPills(groupConfig.name);
		const contentTools = document.createElement("div");
		contentTools.className = "qwen-te-modal__content-tools";
		contentHeader.appendChild(contentTools);
		const makeMiniButton = (label, onClick) => {
			const button = document.createElement("button");
			button.type = "button";
			button.className = "qwen-te-modal__mini-button";
			button.textContent = label;
			button.onclick = onClick;
			contentTools.appendChild(button);
			return button;
		};
		let backToTopButton = null;
		const groupCard = document.createElement("div");
		groupCard.className = "qwen-te-group qwen-te-group--content";
		content.appendChild(groupCard);
		countElements.set(groupConfig.name, contentCount);
		for (const [sectionName, tags] of Object.entries(library.tag_library?.[groupConfig.name] ?? {})) {
			const sectionWrap = document.createElement("div");
			sectionWrap.className = "qwen-te-group__section";
			groupCard.appendChild(sectionWrap);
			const sectionToggle = document.createElement("button");
			sectionToggle.type = "button";
			sectionToggle.className = "qwen-te-group__section-toggle";
			sectionWrap.appendChild(sectionToggle);
			const sectionTitle = document.createElement("div");
			sectionTitle.className = "qwen-te-group__section-title";
			sectionTitle.style.marginBottom = "0";
			sectionTitle.textContent = sectionName;
			sectionToggle.appendChild(sectionTitle);
			const sectionMeta = document.createElement("div");
			sectionMeta.className = "qwen-te-group__section-meta";
			sectionToggle.appendChild(sectionMeta);
			const sectionCount = document.createElement("div");
			sectionCount.className = "qwen-te-group__count";
			sectionCount.textContent = `${tags?.length ?? 0} 个`;
			sectionMeta.appendChild(sectionCount);
			const sectionChevron = document.createElement("div");
			sectionChevron.className = "qwen-te-group__section-chevron";
			sectionChevron.textContent = "▾";
			sectionMeta.appendChild(sectionChevron);
			const chips = document.createElement("div");
			chips.className = "qwen-te-group__section-tags";
			sectionWrap.appendChild(chips);
			const sectionRecord = { groupName: groupConfig.name, wrapper: sectionWrap, chips, toggle: sectionToggle, open: true };
			sectionRecords.push(sectionRecord);
			sectionToggle.onclick = () => {
				setSectionOpen(sectionRecord, !sectionRecord.open);
				scheduleNodeLayoutUpdate(node);
			};
			const orderedTags = [...(tags ?? [])];
			for (const tag of orderedTags) {
				const chip = document.createElement("button");
				chip.type = "button";
				chip.className = "qwen-te-chip";
				chip.textContent = tag;
				chip.onclick = () => {
					toggleTag(groupConfig.name, tag);
					refreshSelectionUiOnly();
				};
				chips.appendChild(chip);
				chipRecords.push({ groupName: groupConfig.name, tag, element: chip, sectionWrap });
			}
		}
		makeMiniButton("清空当前组", () => {
			workingState.selected[groupConfig.name] = [];
			renderSelection();
		});
		backToTopButton = makeMiniButton("回到顶部", () => {
			content.scrollTo({ top: 0, behavior: "smooth" });
		});
		makeMiniButton("展开小类", () => {
			for (const section of sectionRecords) setSectionOpen(section, true);
			scheduleNodeLayoutUpdate(node);
		});
		makeMiniButton("折叠小类", () => {
			for (const section of sectionRecords) setSectionOpen(section, false);
			scheduleNodeLayoutUpdate(node);
		});
		if (backToTopButton) backToTopButton.classList.add("is-hidden");
		content.onscroll = () => {
			if (!backToTopButton) return;
			backToTopButton.classList.toggle("is-hidden", content.scrollTop < 80);
		};
		requestAnimationFrame(() => {
			content.scrollTop = groupChanged ? 0 : previousScrollTop;
			if (backToTopButton) backToTopButton.classList.toggle("is-hidden", content.scrollTop < 80);
		});
	};

	for (const group of library.slot_config ?? []) {
		groupRecords.push({ groupName: group.name });
		const navButton = document.createElement("button");
		navButton.type = "button";
		navButton.className = "qwen-te-modal__nav-button";
		const navLabel = document.createElement("div");
		navLabel.textContent = group.name;
		navButton.appendChild(navLabel);
		const navMeta = document.createElement("div");
		navMeta.className = "qwen-te-modal__nav-meta";
		navButton.appendChild(navMeta);
		const navMatch = document.createElement("div");
		navMatch.className = "qwen-te-modal__nav-match";
		navMeta.appendChild(navMatch);
		const navCount = document.createElement("div");
		navCount.className = "qwen-te-modal__nav-count";
		navMeta.appendChild(navCount);
		navButton.onclick = () => {
			activeGroupName = group.name;
			renderSelection();
		};
		nav.appendChild(navButton);
		navButtons.set(group.name, { button: navButton, count: navCount, match: navMatch });
	}

	const customTitle = document.createElement("div");
	customTitle.className = "qwen-te-group__section-title";
	customTitle.textContent = "自定义补充标签";
	sidebarExtra.appendChild(customTitle);
		const customTagsInput = document.createElement("textarea");
		customTagsInput.className = "qwen-te-modal__textarea";
		customTagsInput.placeholder = "多个标签用逗号分隔。";
		customTagsInput.value = workingState.customTags.join(", ");
		sidebarExtra.appendChild(customTagsInput);
		const customActions = document.createElement("div");
		customActions.className = "qwen-te-modal__content-tools";
		sidebarExtra.appendChild(customActions);
		const autoArrangeButton = document.createElement("button");
		autoArrangeButton.type = "button";
		autoArrangeButton.className = "qwen-te-modal__mini-button";
		autoArrangeButton.textContent = "智能整理到分组";
		customActions.appendChild(autoArrangeButton);
		const clearCustomButton = document.createElement("button");
		clearCustomButton.type = "button";
		clearCustomButton.className = "qwen-te-modal__mini-button";
		clearCustomButton.textContent = "清空自定义";
		customActions.appendChild(clearCustomButton);
		const applyArrangeButton = document.createElement("button");
		applyArrangeButton.type = "button";
		applyArrangeButton.className = "qwen-te-modal__mini-button";
		applyArrangeButton.textContent = "应用整理结果";
		applyArrangeButton.disabled = true;
		customActions.appendChild(applyArrangeButton);
		const undoArrangeButton = document.createElement("button");
		undoArrangeButton.type = "button";
		undoArrangeButton.className = "qwen-te-modal__mini-button";
		undoArrangeButton.textContent = "撤销整理";
		undoArrangeButton.disabled = true;
		customActions.appendChild(undoArrangeButton);
		const customSuggestTitle = document.createElement("div");
		customSuggestTitle.className = "qwen-te-group__section-title";
		customSuggestTitle.textContent = "智能归类建议";
		sidebarExtra.appendChild(customSuggestTitle);
		const customSuggestStatus = document.createElement("div");
		customSuggestStatus.className = "qwen-te-modal__status";
		customSuggestStatus.textContent = "输入自定义补充标签后，会显示推荐归类。";
		sidebarExtra.appendChild(customSuggestStatus);
		const customSuggestList = document.createElement("div");
		customSuggestList.className = "qwen-te-group__chips";
		sidebarExtra.appendChild(customSuggestList);
		const customArrangeTitle = document.createElement("div");
		customArrangeTitle.className = "qwen-te-group__section-title";
		customArrangeTitle.textContent = "整理预览";
		sidebarExtra.appendChild(customArrangeTitle);
		const customArrangeStatus = document.createElement("div");
		customArrangeStatus.className = "qwen-te-modal__status";
		customArrangeStatus.textContent = "点击“智能整理到分组”可先预览，再决定是否应用。";
		sidebarExtra.appendChild(customArrangeStatus);
		const customArrangeFilters = document.createElement("div");
		customArrangeFilters.className = "qwen-te-modal__content-tools";
		sidebarExtra.appendChild(customArrangeFilters);
		const customArrangeBulkActions = document.createElement("div");
		customArrangeBulkActions.className = "qwen-te-modal__content-tools";
		sidebarExtra.appendChild(customArrangeBulkActions);
		const customArrangeList = document.createElement("div");
		customArrangeList.className = "qwen-te-group__chips";
		sidebarExtra.appendChild(customArrangeList);
		const footer = document.createElement("div");
	footer.className = "qwen-te-modal__footer";
	dialog.appendChild(footer);
		const doneButton = document.createElement("button");
		doneButton.className = "qwen-te-modal__footer-button";
		doneButton.textContent = "关闭";
		footer.appendChild(doneButton);

			const cloneArrangeSnapshot = () => ({
				selected: cloneSelection(workingState.selected),
				customTags: parseCustomTags(customTagsInput.value),
			});
			const restoreArrangeSnapshot = (snapshot) => {
				if (!snapshot) return;
				workingState.selected = cloneSelection(snapshot.selected ?? {});
				workingState.customTags = [...(snapshot.customTags ?? [])];
				customTagsInput.value = workingState.customTags.join(", ");
			};
			const removeCustomTagFromInput = (tag) => {
				const nextTags = parseCustomTags(customTagsInput.value).filter((item) => item !== tag);
				workingState.customTags = nextTags;
				customTagsInput.value = nextTags.join(", ");
			};
			const applyArrangeStepToState = (state, step) => {
				if (!step) return "ignored";
				if (step.type === "remove_custom") {
					const cleaned = state.nextCustomTags.filter((tag) => tag !== step.tag);
					const changed = cleaned.length !== state.nextCustomTags.length;
					state.nextCustomTags.length = 0;
					state.nextCustomTags.push(...cleaned);
					return changed ? "removed" : "ignored";
				}
				if (step.type !== "add_group") return "ignored";
				const normalizedTag = String(step.tag ?? "").trim();
				const normalizedGroup = String(step.group ?? "").trim();
				if (!normalizedTag || !normalizedGroup) return "ignored";
				const slotLimit = getTagGroupSlotLimit(library, normalizedGroup);
				const selectedTags = state.nextSelected[normalizedGroup] ?? [];
				if (selectedTags.includes(normalizedTag)) {
					state.nextSelected[normalizedGroup] = selectedTags;
					return "already";
				}
				if (slotLimit > 0 && selectedTags.length < slotLimit) {
					addUniqueTag(selectedTags, normalizedTag);
					state.nextSelected[normalizedGroup] = selectedTags;
					return "selected";
				}
				addUniqueTag(state.nextCustomTags, normalizedTag);
				state.nextSelected[normalizedGroup] = selectedTags;
				return "custom";
			};
			const renderArrangeFilterButtons = () => {
				const changes = customArrangePreview?.changes ?? [];
				const counts = { all: changes.length, split: 0, replace: 0, existing: 0 };
				for (const change of changes) {
					if (change?.kind in counts) counts[change.kind] += 1;
				}
				for (const [key, button] of arrangeFilterButtons.entries()) {
					const active = key === activeArrangeFilter;
					const count = counts[key] ?? 0;
					button.textContent = `${arrangeFilterLabels[key] ?? key} (${count})`;
					button.style.borderColor = active ? "#caa55b" : "#4a5568";
					button.style.background = active ? "#59451a" : "#232a33";
					button.style.color = active ? "#fff0ca" : "#e5ecf6";
					button.disabled = !changes.length;
					button.style.opacity = changes.length ? "1" : "0.55";
					}
				};
			const getVisibleArrangeChanges = () => {
				const changes = customArrangePreview?.changes ?? [];
				return changes.filter((change) => activeArrangeFilter === "all" || change.kind === activeArrangeFilter);
			};
			const getVisibleArrangeOperations = (previewState) => {
				if (!previewState) return [];
				const visibleIds = new Set(getVisibleArrangeChanges().map((change) => change.id));
				return (previewState.operations ?? []).filter((operation) => visibleIds.has(operation.id));
			};
			const buildArrangePreviewSummaryText = (previewState) => {
				if (!customArrangePreview || !previewState) return "";
				const visibleOperations = getVisibleArrangeOperations(previewState);
				const lines = [
					`整理预览摘要`,
					`筛选：${arrangeFilterLabels[activeArrangeFilter] ?? activeArrangeFilter}`,
					`入槽 ${previewState.movedToSlots} 个 | 规范替换 ${previewState.replacedWithCanonical} 个 | 拆分 ${previewState.splitCount} 个 | 剩余自定义 ${previewState.nextCustomTags.length} 个`,
					`当前显示 ${visibleOperations.length}/${(customArrangePreview.changes ?? []).length} 项变化`,
				];
				for (const operation of visibleOperations) {
					lines.push(`- ${operation.text}`);
					for (const detailText of operation.detailItems ?? []) lines.push(`  ${detailText}`);
					if ((operation.slotGain ?? 0) > 0) lines.push(`  将占用 ${operation.slotGain} 个槽位`);
					if (operation.keepsInCustom) lines.push(`  应用后仍会保留部分自定义标签`);
				}
				return lines.join("\n");
			};
			const buildArrangePreviewHistorySummary = (previewState) => {
				if (!customArrangePreview || !previewState) return "";
				const visibleOperations = getVisibleArrangeOperations(previewState);
				const labels = visibleOperations.slice(0, 4).map((item) => item.text);
				const remain = visibleOperations.length - labels.length;
				return [
					`整理预览 | ${arrangeFilterLabels[activeArrangeFilter] ?? activeArrangeFilter}`,
					`入槽${previewState.movedToSlots} 替换${previewState.replacedWithCanonical} 拆分${previewState.splitCount} 剩余自定义${previewState.nextCustomTags.length}`,
					labels.length ? `${labels.join("；")}${remain > 0 ? ` +${remain}` : ""}` : "无可见变化",
				].join(" | ");
			};
			const buildArrangePreviewPresetName = (previewState) => {
				const filterLabel = arrangeFilterLabels[activeArrangeFilter] ?? activeArrangeFilter;
				const visibleOperations = getVisibleArrangeOperations(previewState);
				const suffix = buildCompactTimestamp();
				return `整理预设-${filterLabel}-${visibleOperations.length}项-${suffix}`;
			};
			const exportArrangePreview = (previewState) => {
				if (!customArrangePreview || !previewState) return false;
				const payload = {
					version: 1,
					exportedAt: Date.now(),
					filter: activeArrangeFilter,
					filterLabel: arrangeFilterLabels[activeArrangeFilter] ?? activeArrangeFilter,
					summary: {
						moved_to_slots: previewState.movedToSlots,
						replaced_with_canonical: previewState.replacedWithCanonical,
						split_count: previewState.splitCount,
						remaining_custom_tags: previewState.nextCustomTags,
					},
					operations: getVisibleArrangeOperations(previewState),
				};
				const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
				const url = URL.createObjectURL(blob);
				const a = document.createElement("a");
				a.href = url;
				a.download = `qwen-te-arrange-preview-${Date.now()}.json`;
				document.body.appendChild(a);
				a.click();
				document.body.removeChild(a);
				URL.revokeObjectURL(url);
				return true;
			};
			const renderArrangeBulkButtons = () => {
				const visibleChanges = getVisibleArrangeChanges();
				const hasPreview = !!customArrangePreview;
				for (const [key, button] of arrangeBulkButtons.entries()) {
					const enabled = hasPreview && visibleChanges.length > 0;
					button.disabled = !enabled;
					button.style.opacity = enabled ? "1" : "0.55";
				}
			};
			const computeArrangePreviewState = () => {
				if (!customArrangePreview) return null;
				const state = {
					nextSelected: cloneSelection(customArrangePreview.baseSelected),
					nextCustomTags: [...customArrangePreview.baseCustomTags],
				};
				let movedToSlots = 0;
				let replacedWithCanonical = 0;
				let splitCount = 0;
				const operations = [];
				for (const change of customArrangePreview.changes ?? []) {
					if (!customArrangePreview.activeIds?.has(change.id)) continue;
					let changed = false;
					let slotGainForChange = 0;
					const detailItems = [];
					let keepsInCustom = false;
					for (const step of change.steps ?? []) {
						const result = applyArrangeStepToState(state, step);
						if (result === "selected") {
							movedToSlots += 1;
							slotGainForChange += 1;
							changed = true;
							detailItems.push(`${step.tag} -> ${step.group}（占用槽位）`);
						} else if (result === "already") {
							detailItems.push(`${step.tag} -> ${step.group}（已在分组中）`);
						} else if (result === "custom" || result === "removed") {
							changed = true;
							if (result === "custom") {
								keepsInCustom = true;
								detailItems.push(`${step.tag} -> ${step.group}（槽位已满，暂留自定义区）`);
							} else if (result === "removed") {
								detailItems.push(`${step.tag} 已从自定义区移除`);
							}
						}
					}
					if (!changed) continue;
					if (change.kind === "replace" && change.canonicalReplacement) replacedWithCanonical += 1;
					if (change.kind === "split") splitCount += 1;
					operations.push({
							id: change.id,
							text: change.text,
							kind: change.kind,
							slotGain: slotGainForChange,
							detailItems,
							keepsInCustom,
						});
					}
				return {
					nextSelected: state.nextSelected,
					nextCustomTags: parseCustomTags(state.nextCustomTags.join(", ")),
					movedToSlots,
					replacedWithCanonical,
					splitCount,
					operations,
				};
			};
			const renderArrangePreview = () => {
				customArrangeList.replaceChildren();
				const previewState = computeArrangePreviewState();
				renderArrangeFilterButtons();
				renderArrangeBulkButtons();
				applyArrangeButton.disabled = !customArrangePreview || !(previewState?.operations?.length);
				undoArrangeButton.disabled = !customArrangeUndoState;
				if (!customArrangePreview || !previewState) {
					if (!customArrangeUndoState) customArrangeStatus.textContent = "点击“智能整理到分组”可先预览，再决定是否应用。";
					return;
				}
				const visibleChanges = getVisibleArrangeChanges();
				customArrangeStatus.textContent = `预览：将入槽 ${previewState.movedToSlots} 个，规范替换 ${previewState.replacedWithCanonical} 个，拆分 ${previewState.splitCount} 个，剩余自定义 ${previewState.nextCustomTags.length} 个。当前显示 ${visibleChanges.length}/${(customArrangePreview.changes ?? []).length} 项变化。`;
					for (const change of visibleChanges) {
						const row = document.createElement("div");
						row.style.cssText = "display:flex;align-items:flex-start;gap:8px;flex-wrap:wrap;width:100%;";
						customArrangeList.appendChild(row);
						const toggleButton = document.createElement("button");
					toggleButton.type = "button";
					toggleButton.className = "qwen-te-modal__mini-button";
					const active = customArrangePreview.activeIds?.has(change.id);
					toggleButton.textContent = active ? "已选" : "跳过";
					toggleButton.style.opacity = active ? "1" : "0.65";
					toggleButton.onclick = () => {
						if (!customArrangePreview?.activeIds) return;
						if (customArrangePreview.activeIds.has(change.id)) customArrangePreview.activeIds.delete(change.id);
						else customArrangePreview.activeIds.add(change.id);
						renderArrangePreview();
					};
						row.appendChild(toggleButton);
						const body = document.createElement("div");
						body.style.cssText = "display:flex;flex-direction:column;gap:6px;min-width:0;flex:1 1 280px;";
						row.appendChild(body);
						const pill = document.createElement("div");
						pill.className = `qwen-te-modal__content-pill${active ? "" : " qwen-te-modal__content-pill--muted"}`;
						pill.textContent = change.text;
						body.appendChild(pill);
						const detailBar = document.createElement("div");
						detailBar.className = "qwen-te-modal__content-pills";
						detailBar.style.marginTop = "0";
						body.appendChild(detailBar);
						for (const detailText of change.detailItems ?? []) {
							const detailPill = document.createElement("div");
							detailPill.className = `qwen-te-modal__content-pill--muted qwen-te-modal__content-pill`;
							detailPill.textContent = detailText;
							detailBar.appendChild(detailPill);
						}
						if ((change.slotGain ?? 0) > 0) {
							const slotPill = document.createElement("div");
							slotPill.className = "qwen-te-modal__content-pill qwen-te-modal__content-pill--muted";
							slotPill.textContent = `将占用 ${change.slotGain} 个槽位`;
							detailBar.appendChild(slotPill);
						}
						if (change.keepsInCustom) {
							const keepPill = document.createElement("div");
							keepPill.className = "qwen-te-modal__content-pill qwen-te-modal__content-pill--muted";
							keepPill.textContent = "应用后仍会保留部分自定义标签";
							detailBar.appendChild(keepPill);
						}
					}
				if (!visibleChanges.length) {
					const emptyByFilter = document.createElement("div");
					emptyByFilter.className = "qwen-te-modal__content-pill qwen-te-modal__content-pill--muted";
					emptyByFilter.textContent = "当前筛选下没有变化项。";
					customArrangeList.appendChild(emptyByFilter);
				}
				if (!(previewState.operations ?? []).length) {
					const emptyPill = document.createElement("div");
					emptyPill.className = "qwen-te-modal__content-pill qwen-te-modal__content-pill--muted";
					emptyPill.textContent = "当前所有变化都被跳过。";
					customArrangeList.appendChild(emptyPill);
				}
			};
			for (const [key, label] of Object.entries(arrangeFilterLabels)) {
				const button = document.createElement("button");
				button.type = "button";
				button.className = "qwen-te-modal__mini-button";
				button.textContent = label;
				button.onclick = () => {
					activeArrangeFilter = key;
					renderArrangePreview();
				};
				customArrangeFilters.appendChild(button);
				arrangeFilterButtons.set(key, button);
			}
			const registerArrangeBulkButton = (key, label, onClick) => {
				const button = document.createElement("button");
				button.type = "button";
				button.className = "qwen-te-modal__mini-button";
				button.textContent = label;
				button.onclick = onClick;
				customArrangeBulkActions.appendChild(button);
				arrangeBulkButtons.set(key, button);
			};
			registerArrangeBulkButton("select_visible", "全选当前筛选", () => {
				if (!customArrangePreview?.activeIds) return;
				for (const change of getVisibleArrangeChanges()) customArrangePreview.activeIds.add(change.id);
				renderArrangePreview();
			});
			registerArrangeBulkButton("skip_visible", "跳过当前筛选", () => {
				if (!customArrangePreview?.activeIds) return;
				for (const change of getVisibleArrangeChanges()) customArrangePreview.activeIds.delete(change.id);
				renderArrangePreview();
			});
			registerArrangeBulkButton("apply_visible", "仅应用当前筛选", () => {
				if (!customArrangePreview?.activeIds) return;
				const visibleIds = new Set(getVisibleArrangeChanges().map((change) => change.id));
				customArrangePreview.activeIds = visibleIds;
				renderArrangePreview();
				void applyAutoArrangePreview();
			});
			registerArrangeBulkButton("copy_preview", "复制当前预览", () => {
				const previewState = computeArrangePreviewState();
				const text = buildArrangePreviewSummaryText(previewState);
				if (!text) {
					customArrangeStatus.textContent = "当前没有可复制的整理预览。";
					return;
				}
				void copyToClipboard(text).then((ok) => {
					customArrangeStatus.textContent = ok ? "已复制当前整理预览摘要。" : "复制失败，浏览器可能阻止了剪贴板访问。";
				});
			});
			registerArrangeBulkButton("export_preview", "导出当前预览", () => {
				const previewState = computeArrangePreviewState();
				if (!previewState || !getVisibleArrangeOperations(previewState).length) {
					customArrangeStatus.textContent = "当前没有可导出的整理预览。";
					return;
				}
				exportArrangePreview(previewState);
				customArrangeStatus.textContent = "已导出当前整理预览。";
			});
			registerArrangeBulkButton("save_preview_history", "预览存入历史", () => {
				const previewState = computeArrangePreviewState();
				const visibleOperations = getVisibleArrangeOperations(previewState);
				if (!previewState || !visibleOperations.length) {
					customArrangeStatus.textContent = "当前没有可存入历史的整理预览。";
					return;
				}
				recordNodeHistory(
					node,
					{
						selected: cloneSelection(previewState.nextSelected),
						customTags: [...previewState.nextCustomTags],
						settings: { ...workingState.settings },
					},
					"arrange-preview",
					{
						dedupe: true,
						summary: buildArrangePreviewHistorySummary(previewState),
					},
				);
				customArrangeStatus.textContent = "已将当前整理预览存入历史。";
			});
			registerArrangeBulkButton("save_preview_preset", "预览存为预设", () => {
				const previewState = computeArrangePreviewState();
				const visibleOperations = getVisibleArrangeOperations(previewState);
				if (!previewState || !visibleOperations.length) {
					customArrangeStatus.textContent = "当前没有可存为预设的整理预览。";
					return;
				}
				const presetState = {
					selected: cloneSelection(previewState.nextSelected),
					customTags: [...previewState.nextCustomTags],
					settings: { ...workingState.settings },
				};
				const presetName = buildArrangePreviewPresetName(previewState);
				const ok = saveUserPreset(presetName, presetState, {
					source: "arrange-preview",
					favorite: true,
					meta: {
						summary: buildArrangePreviewHistorySummary(previewState),
						filter: activeArrangeFilter,
					},
				});
				customArrangeStatus.textContent = ok ? `已保存整理预览为预设：${presetName}` : "保存整理预览预设失败。";
			});
			const clearArrangePreview = (message = "") => {
				customArrangeRequestId += 1;
				customArrangePreview = null;
				renderArrangePreview();
				if (message) customArrangeStatus.textContent = message;
			};
			const rememberArrangeUndoState = () => {
				customArrangeUndoState = cloneArrangeSnapshot();
				renderArrangePreview();
			};
			const buildAutoArrangePlan = (detail) => {
				const baseSelected = cloneSelection(workingState.selected);
				const baseCustomTags = parseCustomTags(customTagsInput.value);
				const changes = [];
				for (const item of detail.tags ?? []) {
					const sourceTag = String(item?.tag ?? "");
					if (!sourceTag) continue;
					if (item.exists) {
						const normalizedTag = String(item.existing_tag ?? sourceTag);
						changes.push({
							id: `arrange_${changes.length}_${sourceTag}`,
							kind: "existing",
							text: `${sourceTag} -> ${item.existing_group} / ${item.existing_section}`,
							steps: [
								{ type: "remove_custom", tag: sourceTag },
								...(normalizedTag !== sourceTag ? [{ type: "remove_custom", tag: normalizedTag }] : []),
								{ type: "add_group", group: item.existing_group, tag: normalizedTag },
							],
						});
						continue;
					}
					if (Array.isArray(item.split_suggestions) && item.split_suggestions.length >= 2) {
						changes.push({
							id: `arrange_${changes.length}_${sourceTag}`,
							kind: "split",
							text: `${sourceTag} -> ${(item.split_tags ?? []).join(" + ")}`,
							steps: [
								{ type: "remove_custom", tag: sourceTag },
								...item.split_suggestions.map((splitItem) => ({ type: "add_group", group: splitItem.group, tag: splitItem.tag })),
							],
						});
						continue;
					}
					if (item.matched_tag && item.recommended_group) {
						changes.push({
							id: `arrange_${changes.length}_${sourceTag}`,
							kind: "replace",
							canonicalReplacement: item.matched_tag !== sourceTag,
							text: `${sourceTag} -> ${item.matched_tag}`,
							steps: [
								{ type: "remove_custom", tag: sourceTag },
								{ type: "add_group", group: item.recommended_group, tag: item.matched_tag },
							],
						});
					}
				}
				const activeIds = new Set(changes.map((change) => change.id));
				const changed = changes.length > 0;
				return {
					baseSelected,
					baseCustomTags,
					changes,
					activeIds,
					changed,
				};
			};
			const previewAutoArrangeCustomTags = async () => {
				const sourceText = String(customTagsInput.value ?? "");
				const originalTags = parseCustomTags(sourceText);
				if (!originalTags.length) {
					clearArrangePreview("当前没有可整理的自定义标签。");
					return;
				}
				const requestId = ++customArrangeRequestId;
				customArrangeStatus.textContent = `正在预览 ${originalTags.length} 个自定义标签的整理结果...`;
				try {
					const detail = await suggestCustomTagGrouping(sourceText, { owner: overlay, key: "tag-dialog-arrange" });
					if (requestId !== customArrangeRequestId || overlay.__qwenDisposed || String(customTagsInput.value ?? "") !== sourceText) return;
					const plan = buildAutoArrangePlan(detail);
					if (!plan.changed) {
						clearArrangePreview("预览完成：当前自定义标签没有可整理的变化。");
						return;
					}
					customArrangePreview = plan;
					renderArrangePreview();
				} catch (error) {
					if (requestId !== customArrangeRequestId || overlay.__qwenDisposed) return;
					clearArrangePreview(`整理预览失败：${error.message}`);
				}
			};
			const applyAutoArrangePreview = async () => {
				if (!customArrangePreview) {
					customArrangeStatus.textContent = "先生成整理预览，再决定是否应用。";
					return;
				}
				const previewState = computeArrangePreviewState();
				if (!previewState || !(previewState.operations ?? []).length) {
					customArrangeStatus.textContent = "当前没有勾选任何整理变化。";
					return;
				}
				rememberArrangeUndoState();
				workingState.selected = cloneSelection(previewState.nextSelected);
				workingState.customTags = [...previewState.nextCustomTags];
				customTagsInput.value = workingState.customTags.join(", ");
				const appliedSummary = `已应用整理：入槽 ${previewState.movedToSlots} 个，规范替换 ${previewState.replacedWithCanonical} 个，拆分 ${previewState.splitCount} 个，剩余自定义 ${workingState.customTags.length} 个。`;
				customArrangePreview = null;
				renderSelection();
				await renderCustomTagSuggestions();
				customArrangeStatus.textContent = appliedSummary;
				renderArrangePreview();
			};
			const undoAutoArrange = async () => {
				if (!customArrangeUndoState) {
					customArrangeStatus.textContent = "当前没有可撤销的整理操作。";
					return;
				}
				restoreArrangeSnapshot(customArrangeUndoState);
				customArrangeUndoState = null;
				customArrangePreview = null;
				renderSelection();
				await renderCustomTagSuggestions();
				customArrangeStatus.textContent = "已撤销上一次整理。";
				renderArrangePreview();
			};
			const splitSuggestedTag = (item) => {
				const splitItems = Array.isArray(item?.split_suggestions) ? item.split_suggestions : [];
				if (splitItems.length < 2) return;
				rememberArrangeUndoState();
				const nextCustomTags = parseCustomTags(customTagsInput.value).filter((tag) => tag !== item.tag);
				for (const splitItem of splitItems) {
					applySuggestedTagToSelection(workingState.selected, splitItem.tag, splitItem.group, nextCustomTags);
				}
				workingState.customTags = nextCustomTags;
				customTagsInput.value = nextCustomTags.join(", ");
				clearArrangePreview(`已将 ${item.tag} 拆分为 ${(item.split_tags ?? []).join("、")}`);
				renderSelection();
				queueCustomTagSuggestions();
			};
			const promoteSuggestedTag = async (item) => {
				const category = String(item?.recommended_group ?? "");
				const section = String(item?.recommended_section ?? "");
				const tag = String(item?.tag ?? "");
				if (!category || !section || !tag || item?.exists) return;
				customSuggestStatus.textContent = `正在收录 ${tag} -> ${category} / ${section}...`;
				try {
					await mutateTagLibrary("/qwen_te/tag_library/add_batch", { category, section, tag }, { owner: overlay, key: "tag-dialog-mutation" });
					library = await getFreshLibraryForUi(node, library);
					rememberArrangeUndoState();
					removeCustomTagFromInput(tag);
					clearArrangePreview(`已收录 ${tag} -> ${category} / ${section}`);
					renderSelection();
					await renderCustomTagSuggestions();
				} catch (error) {
					customSuggestStatus.textContent = `收录失败：${error.message}`;
				}
			};

		const renderCustomTagSuggestions = async () => {
			const tags = parseCustomTags(customTagsInput.value);
			customSuggestList.replaceChildren();
			if (!tags.length) {
				customSuggestStatus.textContent = "输入自定义补充标签后，会显示推荐归类。";
				return;
			}
			customSuggestStatus.textContent = `正在分析 ${tags.length} 个自定义标签...`;
			const requestId = ++customSuggestRequestId;
			try {
				const detail = await suggestCustomTagGrouping(customTagsInput.value, { owner: overlay, key: "tag-dialog-suggest" });
				if (requestId !== customSuggestRequestId) return;
				for (const item of detail.tags ?? []) {
					const row = document.createElement("div");
					row.style.cssText = "display:flex;align-items:center;gap:8px;flex-wrap:wrap;width:100%;";
					customSuggestList.appendChild(row);
						const chip = document.createElement("div");
						chip.className = `qwen-te-modal__content-pill${item.exists ? " qwen-te-modal__content-pill--muted" : ""}`;
					const target = item.exists
						? `${item.existing_group} / ${item.existing_section}`
						: item.recommended_group
							? `${item.recommended_group} / ${item.recommended_section}`
							: "暂不明确";
						chip.textContent = `${item.tag}: ${target}`;
						chip.title = String(item.reason ?? "");
						row.appendChild(chip);
						if (Array.isArray(item.split_tags) && item.split_tags.length >= 2) {
							const splitButton = document.createElement("button");
							splitButton.type = "button";
							splitButton.className = "qwen-te-modal__mini-button";
							splitButton.textContent = "拆成多个标签";
							splitButton.title = `拆分为：${item.split_tags.join("、")}`;
							splitButton.onclick = () => { splitSuggestedTag(item); };
							row.appendChild(splitButton);
						}
						const actionButton = document.createElement("button");
					actionButton.type = "button";
					actionButton.className = "qwen-te-modal__mini-button";
					if (item.exists) {
						actionButton.textContent = "已在库中";
						actionButton.disabled = true;
					} else if (item.recommended_group) {
						actionButton.textContent = "收进标签库";
						actionButton.title = `收录到 ${item.recommended_group} / ${item.recommended_section}`;
						actionButton.onclick = () => { void promoteSuggestedTag(item); };
					} else {
						actionButton.textContent = "待观察";
						actionButton.disabled = true;
					}
					row.appendChild(actionButton);
				}
				const summary = detail.summary ?? {};
				customSuggestStatus.textContent = `已分析 ${summary.total ?? tags.length} 个标签，可归类 ${(summary.recommendable_count ?? 0)} 个，已存在 ${(summary.existing_count ?? 0)} 个。`;
			} catch (error) {
				if (requestId !== customSuggestRequestId) return;
				customSuggestStatus.textContent = `归类分析失败：${error.message}`;
			}
		};
			const queueCustomTagSuggestions = () => {
				clearTimeout(customSuggestTimer);
				customSuggestRequestId += 1;
				customSuggestTimer = setTimeout(() => { void renderCustomTagSuggestions(); }, 180);
			};

			const applyCurrentSelection = () => {
				workingState.customTags = parseCustomTags(customTagsInput.value);
			applyNodeState(node, library, workingState, { recordHistory:true, historySource:"manual-apply" });
			disposeModalOverlay(overlay);
		};

	const renderSelection = () => {
		const keyword = String(searchInput.value ?? "").trim().toLowerCase();
		const availableGroups = (library.slot_config ?? []).filter((group) => {
			if (!keyword) return true;
			return Object.values(library.tag_library?.[group.name] ?? {}).some((tags) => (tags ?? []).some((tag) => tag.toLowerCase().includes(keyword)));
		});
		if (!availableGroups.some((group) => group.name === activeGroupName)) {
			activeGroupName = availableGroups[0]?.name ?? (library.slot_config ?? [])[0]?.name ?? "";
		}
		renderGroupContent(activeGroupName);
		for (const chip of chipRecords) {
			const selectedTags = workingState.selected[chip.groupName] ?? [];
			const selected = selectedTags.includes(chip.tag);
			const limit = getTagGroupSlotLimit(library, chip.groupName);
			const blocked = !selected && selectedTags.length >= limit;
			chip.element.classList.toggle("is-selected", selected);
			chip.element.classList.toggle("is-capacity-blocked", blocked);
			chip.element.title = selected ? "点击取消选择" : (blocked ? `已达到本组 ${limit} 个标签上限` : "点击选择");
			chip.element.setAttribute?.("aria-disabled", blocked ? "true" : "false");
			chip.element.classList.toggle("qwen-te-hidden", !!keyword && !chip.tag.toLowerCase().includes(keyword));
		}
		const visibleSectionsByGroup = new Map();
		for (const section of sectionRecords) {
			const hasVisible = [...section.chips.children].some((chip) => !chip.classList.contains("qwen-te-hidden"));
			section.wrapper.classList.toggle("qwen-te-hidden", !hasVisible);
			if (keyword && hasVisible) setSectionOpen(section, true);
			if (hasVisible) visibleSectionsByGroup.set(section.groupName, (visibleSectionsByGroup.get(section.groupName) ?? 0) + 1);
		}
		for (const group of library.slot_config ?? []) {
			const navRecord = navButtons.get(group.name);
			if (!navRecord) continue;
			const groupSections = sectionRecords.filter((section) => section.groupName === group.name);
			const visibleCount = groupSections.filter((section) => !section.wrapper.classList.contains("qwen-te-hidden")).length;
			const isVisible = !keyword || availableGroups.some((item) => item.name === group.name);
			navRecord.button.classList.toggle("qwen-te-hidden", !isVisible);
			navRecord.button.classList.toggle("is-active", group.name === activeGroupName);
			navRecord.button.classList.toggle("is-match", visibleCount > 0 && keyword.length > 0);
			navRecord.match.textContent = keyword && visibleCount > 0 ? `${visibleCount} 匹配` : "";
			navRecord.count.textContent = `${(workingState.selected[group.name] ?? []).length}/${getTagGroupSlotLimit(library, group.name)}`;
		}
		for (const group of library.slot_config ?? []) {
			const count = (workingState.selected[group.name] ?? []).length;
			const countEl = countElements.get(group.name);
			if (countEl) countEl.textContent = `${count} / ${getTagGroupSlotLimit(library, group.name)}`;
		}
	};

			resetButton.onclick = () => {
				const hasSelected = Object.values(workingState.selected).some((items) => Array.isArray(items) && items.length > 0);
				const hasCustom = Array.isArray(workingState.customTags) && workingState.customTags.length > 0;
				if (hasSelected || hasCustom) {
					const confirmed = window.confirm("将清空本次已选标签和自定义补充，确定继续吗？");
					if (!confirmed) {
						statusEl.textContent = "已取消清空本次选择。";
						return;
					}
				}
				for (const group of library.slot_config ?? []) workingState.selected[group.name] = [];
				workingState.customTags = [];
				customTagsInput.value = "";
				statusEl.textContent = "已清空本次选择。";
				customArrangeUndoState = null;
				clearArrangePreview("点击“智能整理到分组”可先预览，再决定是否应用。");
				queueCustomTagSuggestions();
				renderSelection();
			};
			autoArrangeButton.onclick = () => { void previewAutoArrangeCustomTags(); };
			applyArrangeButton.onclick = () => { void applyAutoArrangePreview(); };
			undoArrangeButton.onclick = () => { void undoAutoArrange(); };
			clearCustomButton.onclick = () => {
				if (workingState.customTags.length > 0 || String(customTagsInput.value ?? "").trim()) {
					const confirmed = window.confirm("将清空当前自定义补充标签，确定继续吗？");
					if (!confirmed) {
						statusEl.textContent = "已取消清空自定义补充。";
						return;
					}
				}
				rememberArrangeUndoState();
				workingState.customTags = [];
				customTagsInput.value = "";
				clearArrangePreview("已清空自定义补充标签。");
				renderSelection();
				queueCustomTagSuggestions();
			};
			manageButton.onclick = () => { disposeModalOverlay(overlay); openTagManager(node); };
			searchInput.addEventListener("input", renderSelection);
			customTagsInput.addEventListener("input", () => {
				customArrangeRequestId += 1;
				customArrangePreview = null;
				renderArrangePreview();
				queueCustomTagSuggestions();
			});
			applyButton.onclick = applyCurrentSelection;
		overlay.__qwenDispose = () => {
		clearTimeout(customSuggestTimer);
		customSuggestRequestId += 1;
		customArrangeRequestId += 1;
	};
		const closeTagDialog = () => disposeModalOverlay(overlay);
		doneButton.onclick = closeTagDialog;
		closeButton.onclick = closeTagDialog;
			overlay.addEventListener("click", (event) => { if (event.target === overlay) closeTagDialog(); });
			document.body.appendChild(overlay);
			renderSelection();
			renderArrangePreview();
			void renderCustomTagSuggestions();
			searchInput.focus();
		}
function refreshNodeSummary(node, library) {
	if (!node[PANEL_KEY]?.summaryEl) return;
	const summaryText = buildNodeSummaryText(node, library);
	renderSummaryPills(node[PANEL_KEY].summaryEl, summaryText);
	node[PANEL_KEY].summaryEl.title = summaryText;
	if (node[PANEL_KEY]?.summaryWidget) node[PANEL_KEY].summaryWidget.value = summaryText;
	refreshNodeContinuousBadge(node);
	refreshNodeContinuousReportSummary(node);
	refreshRandomRuntimePills(node);
	refreshRandomTrackHistory(node);
	refreshNodeActionButtons(node);
	scheduleNodeLayoutUpdate(node);
}

function resolveStagePromptBridgeNode(nodeOrId) {
	const targetNode = typeof nodeOrId === "object" && nodeOrId
		? nodeOrId
		: app.graph?._nodes?.find((candidate) => Number(candidate?.id ?? -1) === Number(nodeOrId ?? -2));
	if (!targetNode || targetNode[NODE_REMOVED_KEY] || !isStagePromptNode(targetNode)) return null;
	const graphNodes = app.graph?._nodes;
	return Array.isArray(graphNodes) && !graphNodes.includes(targetNode) ? null : targetNode;
}

async function applyRandomStateFromBridge(nodeOrId, options = {}) {
	const targetNode = resolveStagePromptBridgeNode(nodeOrId);
	if (!targetNode) return false;
	const mutationRevision = beginNodeStateMutation(targetNode);
	const library = await getFreshLibraryForUi(targetNode, targetNode?.[PANEL_KEY]?.library ?? null, { mutationRevision });
	if (!library || !isNodeStateMutationCurrent(targetNode, mutationRevision)) return false;
	return await buildAndApplyRandomState(targetNode, library, { ...options, mutationRevision });
}

async function clearNodeStateFromBridge(nodeOrId) {
	const targetNode = resolveStagePromptBridgeNode(nodeOrId);
	if (!targetNode) return false;
	const mutationRevision = beginNodeStateMutation(targetNode);
	const library = await getFreshLibraryForUi(targetNode, targetNode?.[PANEL_KEY]?.library ?? null, { mutationRevision });
	if (!library || !isNodeStateMutationCurrent(targetNode, mutationRevision)) return false;
	return !!applyClearedNodeState(targetNode, library, { mutationRevision });
}

window.__QWEN_TE_STAGE_OPEN_TAG_DIALOG__ = async (nodeOrId) => {
	const targetNode = resolveStagePromptBridgeNode(nodeOrId);
	if (!targetNode) return false;
	const library = await getFreshLibraryForUi(targetNode, targetNode?.[PANEL_KEY]?.library ?? null);
	if (resolveStagePromptBridgeNode(targetNode) !== targetNode) return false;
	openTagDialog(targetNode, library);
	return true;
};
window.__QWEN_TE_STAGE_GET_FRESH_LIBRARY__ = async (nodeOrId) => {
	const targetNode = resolveStagePromptBridgeNode(nodeOrId);
	if (!targetNode) return null;
	const library = await getFreshLibraryForUi(targetNode, targetNode?.[PANEL_KEY]?.library ?? null);
	return resolveStagePromptBridgeNode(targetNode) === targetNode ? library : null;
};
window.__QWEN_TE_STAGE_BUILD_RANDOM_STATE__ = async (nodeOrId, library, sourceState = null) => {
	const targetNode = resolveStagePromptBridgeNode(nodeOrId);
	if (!targetNode || !library) return null;
	const state = await buildRandomState(targetNode, library, sourceState);
	return resolveStagePromptBridgeNode(targetNode) === targetNode ? state : null;
};
window.__QWEN_TE_STAGE_APPLY_RANDOM_STATE__ = applyRandomStateFromBridge;
window.__QWEN_TE_STAGE_CLEAR_NODE_STATE__ = clearNodeStateFromBridge;
window.__QWEN_TE_STAGE_APPLY_NODE_STATE__ = (nodeOrId, library, state, options = {}) => {
	const targetNode = resolveStagePromptBridgeNode(nodeOrId);
	if (!targetNode || !library || !state) return false;
	return applyNodeState(targetNode, library, state, options);
};
window.__QWEN_TE_STAGE_COLLECT_NODE_STATE__ = (nodeOrId, library) => {
	const targetNode = resolveStagePromptBridgeNode(nodeOrId);
	if (!targetNode || !library) return null;
	return collectNodeState(targetNode, library);
};
window.__QWEN_TE_STAGE_RECORD_HISTORY__ = (nodeOrId, state, source = "random") => {
	const targetNode = resolveStagePromptBridgeNode(nodeOrId);
	if (!targetNode || !state) return false;
	recordNodeHistory(targetNode, state, source);
	return true;
};
window.__QWEN_TE_STAGE_GET_PROMPT_OUTPUT__ = (nodeOrId) => {
	const targetNode = resolveStagePromptBridgeNode(nodeOrId);
	if (!targetNode) return "";
	return String(getStagePromptOutputText(targetNode) ?? "");
};

function getRawTagWidgetNames(library) {
	return (library?.slot_config ?? [])
		.flatMap((group) => Array.from({ length: getTagGroupSlotLimit(library, group?.name) }, (_, index) => `${group.name}标签${index + 1}`))
		.concat(["自定义补充标签"]);
}

function bindSummaryRefresh(node, library) {
	const names = new Set([...PRESET_SETTING_NAMES, ...getRawTagWidgetNames(library)]);
	for (const widget of node.widgets ?? []) {
		if (!names.has(widget.name) || widget[WIDGET_SUMMARY_REFRESH_BOUND_KEY]) continue;
		widget[WIDGET_SUMMARY_REFRESH_BOUND_KEY] = true;
		const originalCallback = widget.callback;
		widget.callback = function (...args) {
			if (!Number(node?.[NODE_PROGRAMMATIC_WIDGET_WRITE_DEPTH_KEY] ?? 0)) beginNodeStateMutation(node);
			const result = originalCallback?.apply(this, args);
			clearNodeRandomDedupeCache(node);
			persistNamedWidgetState(node);
			requestAnimationFrame(() => refreshNodeSummary(node, node?.[PANEL_KEY]?.library ?? library));
			return result;
		};
	}
}

function addFallbackWidget(node, type, name, value, callback, options = {}) {
	const widget = node.addWidget(type, name, value, callback, options);
	if (widget) {
		widget.serialize = false;
		widget.__qwenStageFallbackWidget = true;
	}
	return widget;
}

function addTopWidget(node, type, name, value, callback, options = {}, insertIndexRef = { value: 0 }) {
	const widget = addFallbackWidget(node, type, name, value, callback, options);
	if (!widget || !Array.isArray(node.widgets) || node.widgets.length === 0) return widget;
	const createdIndex = node.widgets.indexOf(widget);
	if (createdIndex < 0) return widget;
	node.widgets.splice(createdIndex, 1);
	node.widgets.splice(insertIndexRef.value, 0, widget);
	insertIndexRef.value += 1;
	return widget;
}

function shouldForceMiniToolbarMode() {
	try {
		const href =
			String(window?.location?.href ?? "") ||
			String(globalThis?.location?.href ?? "");
		return /(?:[?&])qwen_te_mini(?:=(?:1|true))?(?:[&#]|$)/iu.test(href);
	} catch (_error) {
		return false;
	}
}

function ensureStagePromptTopStatusWidgets(node, library, summary) {
	if (!node || typeof node.addWidget !== "function") return;
	if (getWidget(node, "qwen_te_mini_toolbar_dom")) return;
	const findCanonicalWidget = (name) => {
		const matches = (node.widgets ?? []).filter((widget) => widget?.name === name);
		const canonical = matches.find((widget) => widget.__qwenStageFallbackWidget) ?? matches[0] ?? null;
		if (canonical && Array.isArray(node.widgets)) {
			for (let index = node.widgets.length - 1; index >= 0; index -= 1) {
				if (node.widgets[index]?.name === name && node.widgets[index] !== canonical) node.widgets.splice(index, 1);
			}
			canonical.serialize = false;
			canonical.options = canonical.options ?? {};
			canonical.options.serialize = false;
			canonical.__qwenStageFallbackWidget = true;
		}
		return canonical;
	};
	const topInsert = { value: 0 };
	let topStatusWidget = findCanonicalWidget("状态");
	if (!topStatusWidget) {
		topStatusWidget = addTopWidget(node, "text", "状态", "可随机、载入预设，运行后可复制“正向提示词合集”。", () => {}, { serialize: false }, topInsert);
	} else if (Array.isArray(node.widgets)) {
		topInsert.value = Math.max(0, node.widgets.indexOf(topStatusWidget) + 1);
	}
	let topSummaryWidget = findCanonicalWidget("摘要");
	if (!topSummaryWidget) {
		topSummaryWidget = addTopWidget(node, "text", "摘要", buildNodeSummaryText(node, library), () => {}, { serialize: false }, topInsert);
	}
	if (Array.isArray(node.widgets) && topStatusWidget && topSummaryWidget) {
		const remainingWidgets = node.widgets.filter((widget) => widget !== topStatusWidget && widget !== topSummaryWidget);
		node.widgets.splice(0, node.widgets.length, topStatusWidget, topSummaryWidget, ...remainingWidgets);
	}
	if (topSummaryWidget) topSummaryWidget.value = buildNodeSummaryText(node, library);
	if (node[PANEL_KEY]) {
		node[PANEL_KEY].statusWidget = topStatusWidget;
		node[PANEL_KEY].summaryWidget = topSummaryWidget;
	}
}

function enhanceStagePromptNode(node, library) {
	ensureNodeCacheNamespace(node);
	cleanupFixUiArtifacts(node, { preserveMiniToolbar: true });
	compactStagePromptOutputs(node);
	if (node[PANEL_KEY]) return;
	// The mini toolbar must be allowed to take over while this panel is still being built.
	node[PANEL_READY_KEY] = false;
	if (shouldForceMiniToolbarMode()) return;
	if (typeof node.addDOMWidget !== "function") return false;
	const rawTagWidgetNames = getRawTagWidgetNames(library);
	const hiddenState = { showRawTags: false, showAdvanced: false };
	const autoNegativeSyncState = { enabled: getNodeAutoNegativeSyncEnabled(node) };
	const panel = document.createElement("div"); panel.className="qwen-te-panel";
	panel.style.pointerEvents = "auto";
	panel.addEventListener("pointerdown", (event) => { event.stopPropagation(); });
	panel.addEventListener("mousedown", (event) => { event.stopPropagation(); });
	panel.addEventListener("click", (event) => { event.stopPropagation(); });
	const workspace = document.createElement("div"); workspace.className="qwen-te-panel__workspace"; panel.appendChild(workspace);
	const mainWorkspace = document.createElement("div"); mainWorkspace.className="qwen-te-panel__main"; workspace.appendChild(mainWorkspace);
	const summary = document.createElement("div"); summary.className="qwen-te-panel__summary";
	const themePoolQuickCardButtons = new Map();
	const status = { textContent: "" };
	const controlSurface = null;
	const displayCard = document.createElement("div"); displayCard.className="qwen-te-panel__display"; mainWorkspace.appendChild(displayCard);
	const displayTop = document.createElement("div"); displayTop.className="qwen-te-panel__display-top"; displayCard.appendChild(displayTop);
	const displayTitle = document.createElement("div"); displayTitle.className="qwen-te-panel__display-title"; displayTitle.textContent="终端预览"; displayTop.appendChild(displayTitle);
	const displayMeta = document.createElement("div"); displayMeta.className="qwen-te-panel__display-meta"; displayTop.appendChild(displayMeta);
	const displaySource = document.createElement("div"); displaySource.className="qwen-te-panel__display-source"; displaySource.textContent="等待输出"; displayMeta.appendChild(displaySource);
	const displaySearch = document.createElement("button"); displaySearch.type="button"; displaySearch.className="qwen-te-panel__display-expand qwen-te-panel__display-search"; displaySearch.textContent="浏览器"; displaySearch.dataset.qwenHint="打开网页浏览器与标签搜索。网页只在手动打开后访问。"; displaySearch.title=displaySearch.dataset.qwenHint; displaySearch.setAttribute("aria-label","打开网页浏览器"); displaySearch.addEventListener("pointerdown", (event) => { event.stopPropagation(); }); displaySearch.addEventListener("mousedown", (event) => { event.stopPropagation(); }); displaySearch.addEventListener("click", (event) => { event.stopPropagation(); if (displaySearch.disabled) return; openOnlinePromptSearchDialog(node, node?.[PANEL_KEY]?.library ?? library); }); displayMeta.appendChild(displaySearch);
	const displayExpand = document.createElement("button"); displayExpand.type="button"; displayExpand.className="qwen-te-panel__display-expand"; displayExpand.textContent="弹出终端"; displayExpand.addEventListener("pointerdown", (event) => { event.stopPropagation(); }); displayExpand.addEventListener("mousedown", (event) => { event.stopPropagation(); }); displayExpand.addEventListener("click", (event) => { event.stopPropagation(); openStageOutputDialog(node); }); displayMeta.appendChild(displayExpand);
	const displayTabs = document.createElement("div"); displayTabs.className="qwen-te-panel__display-tabs"; displayCard.appendChild(displayTabs);
	const displayBody = document.createElement("div"); displayBody.className="qwen-te-panel__display-screen is-empty"; displayBody.textContent="运行一次后，这里会展示最近的提示词、负面词或 JSON 结果。"; displayCard.appendChild(displayBody);
	const displayTabButtons = new Map();
	for (const mode of STAGE_DISPLAY_MODES) {
		const button = document.createElement("button");
		button.type = "button";
		button.className = "qwen-te-panel__display-tab";
		button.textContent = mode.label;
		button.addEventListener("pointerdown", (event) => { event.stopPropagation(); });
		button.addEventListener("mousedown", (event) => { event.stopPropagation(); });
		button.addEventListener("click", (event) => {
			event.stopPropagation();
			if (!node[PANEL_KEY]) return;
			node[PANEL_KEY].displayMode = mode.key;
			refreshStageDisplay(node);
		});
		displayTabs.appendChild(button);
		displayTabButtons.set(mode.key, button);
	}
	const slotPanel = buildLazySlotPanel(library); mainWorkspace.appendChild(slotPanel);
	const advancedPanel = buildAdvancedPanel(node); mainWorkspace.appendChild(advancedPanel);
	const quickbar = document.createElement("div"); quickbar.className="qwen-te-panel__quickbar"; mainWorkspace.appendChild(quickbar);
	const panelButtons = { onlineSearch: displaySearch };
	const registerPanelButton = (key, button) => {
		if (key) panelButtons[key] = button;
		return button;
	};
	const makeBtn=(container,label,icon,onclick,extraClass="",helpText="")=>{ const b=document.createElement("button"); b.type="button"; b.className=`qwen-te-panel__button${extraClass ? ` ${extraClass}` : ""}`; if(helpText){ b.dataset.qwenHint=helpText; b.title=helpText; } const iconEl=document.createElement("span"); iconEl.className="qwen-te-panel__button-icon"; iconEl.textContent=icon; const labelEl=document.createElement("span"); labelEl.className="qwen-te-panel__button-label"; labelEl.textContent=label; b.appendChild(iconEl); b.appendChild(labelEl); b.addEventListener("pointerdown", (event) => { event.stopPropagation(); }); b.addEventListener("mousedown", (event) => { event.stopPropagation(); }); b.addEventListener("click", async (event) => { event.stopPropagation(); await wrapPanelAction(node, status, label, onclick, b)(); refreshNodeActionButtons(node); }); container.appendChild(b); return b; };
	registerPanelButton("tag", makeBtn(quickbar,"标签","TAG", async(mutationRevision)=>{ const nextLibrary = await getFreshLibraryForUi(node, library, { mutationRevision }); if (isNodeStateMutationCurrent(node, mutationRevision)) openTagDialog(node, nextLibrary); },"qwen-te-panel__button--cool qwen-te-panel__button--primary","打开标签选择面板。"));
	registerPanelButton("randomRun", makeBtn(quickbar,"随机跑","RUN", async(mutationRevision)=>{ const nextLibrary = await getFreshLibraryForUi(node, library, { mutationRevision }); if (!isNodeStateMutationCurrent(node, mutationRevision)) return; const applied = await buildAndApplyRandomState(node, nextLibrary, { mutationRevision }); if (!applied) return; const queued=await queueWorkflowFromNode(node); if (!isNodeStateMutationCurrent(node, mutationRevision)) return; setNodeStatusText(node, queued ? "随机已应用并加入队列。" : "随机已应用，但没能自动加入队列。"); },"qwen-te-panel__button--run qwen-te-panel__button--primary","随机后自动入队执行。"));
	registerPanelButton("smartMatch", makeBtn(quickbar,"匹配启用","AI", async()=>{ await runSmartTextMatch(node); },"qwen-te-panel__button--cool","输入一句描述，自动匹配标签并启用智能文本；NSFW 开启时会自动切到成人向成熟策略。"));
	registerPanelButton("tagBlocks", makeBtn(quickbar,"编排","BLK", async()=>{ if (!node[PANEL_KEY]) return; node[PANEL_KEY].displayMode = "blocks"; refreshStageDisplay(node); openStageOutputDialog(node); },"qwen-te-panel__button--cool","打开标签块编排，可拖拽排序、删词、插入文字并按顺序生成。"));
	registerPanelButton("model", makeBtn(quickbar,"模型","MDL", async()=>{ openStageModelDialog(node); },"qwen-te-panel__button--cool","打开模型面板，可选择本地模型、API 接口或仅 Skill；本地模型支持外接对象和内置 GGUF。"));
	registerPanelButton("characterSheet", makeBtn(quickbar,"设定图","CS", async(mutationRevision)=>{ const nextLibrary = await getFreshLibraryForUi(node, library, { mutationRevision }); if (isNodeStateMutationCurrent(node, mutationRevision)) openCharacterSheetDialog(node, nextLibrary); },"qwen-te-panel__button--accent","生成头像特写、正面、侧面、背面组合的角色设定图提示词。"));
	registerPanelButton("random", makeBtn(quickbar,"随机","RD", async(mutationRevision)=>{ const nextLibrary = await getFreshLibraryForUi(node, library, { mutationRevision }); if (!isNodeStateMutationCurrent(node, mutationRevision)) return; await buildAndApplyRandomState(node, nextLibrary, { mutationRevision }); },"qwen-te-panel__button--warm","按当前规则随机重排标签。"));
	registerPanelButton("example", makeBtn(quickbar,"示例","EX", async(mutationRevision)=>{ const nextLibrary = await getFreshLibraryForUi(node, library, { mutationRevision }); if (isNodeStateMutationCurrent(node, mutationRevision)) openExampleDialog(node, nextLibrary); },"qwen-te-panel__button--accent","打开少量风格锚点，用于定调和选路。"));
	registerPanelButton("presets", makeBtn(quickbar,"预设","PRE", async(mutationRevision)=>{ const nextLibrary = await getFreshLibraryForUi(node, library, { mutationRevision }); if (isNodeStateMutationCurrent(node, mutationRevision)) openPresetManager(node, nextLibrary); },"","管理可直接生产的稳定模板与批量连测。"));
	registerPanelButton("nsfwWorkspace", makeBtn(quickbar,"NSFW","NS", async(mutationRevision)=>{ const nextLibrary = await getFreshLibraryForUi(node, library, { mutationRevision }); if (isNodeStateMutationCurrent(node, mutationRevision)) openNsfwWorkspaceDialog(node, nextLibrary); },"qwen-te-panel__button--accent","在当前阶段面板内打开 NSFW 工作台。"));
	registerPanelButton("history", makeBtn(quickbar,"历史","HIS", async(mutationRevision)=>{ const nextLibrary = await getFreshLibraryForUi(node, library, { mutationRevision }); if (!isNodeStateMutationCurrent(node, mutationRevision)) return; await reconcileStageExecutionHistoryBeforeOpen(node, nextLibrary); if (isNodeStateMutationCurrent(node, mutationRevision)) openHistoryManager(node, nextLibrary); },"qwen-te-panel__button--minor","查看随机与执行历史。"));
	const rawToggleButton=registerPanelButton("toggleRawSlots", makeBtn(quickbar,"槽位","SL", async()=>{ hiddenState.showRawTags=!hiddenState.showRawTags; setWidgetGroupVisibility(node, node[PANEL_KEY]?.rawTagWidgetNames ?? rawTagWidgetNames, false, "Raw"); const changed=setSlotPanelVisible(node, hiddenState.showRawTags); setPanelToggleButtonState(rawToggleButton, hiddenState.showRawTags, "收槽位", "槽位"); setNodeStatusText(node, changed ? (hiddenState.showRawTags ? "已展开槽位设置面板。" : "已收起槽位设置面板。") : "没有找到可展开的槽位设置面板。"); },"qwen-te-panel__button--minor","显示或收起槽位设置面板。"));
	const advancedToggleButton=registerPanelButton("toggleAdvanced", makeBtn(quickbar,"高级","ADV", async()=>{ hiddenState.showAdvanced=!hiddenState.showAdvanced; setWidgetGroupVisibility(node, [...CONTROL_WIDGET_NAMES, ...ADVANCED_WIDGET_NAMES], false, "Advanced"); const changed=setAdvancedPanelVisible(node, hiddenState.showAdvanced); setPanelToggleButtonState(advancedToggleButton, hiddenState.showAdvanced, "收高级", "高级"); setNodeStatusText(node, changed ? (hiddenState.showAdvanced ? "已展开高级设置面板。" : "已收起高级设置面板。") : "没有找到可展开的高级设置面板。"); },"qwen-te-panel__button--minor","显示或收起高级设置面板。"));
	registerPanelButton("clearTags", makeBtn(quickbar,"清空","CLR", async(mutationRevision)=>{ const nextLibrary = await getFreshLibraryForUi(node, library, { mutationRevision }); if (!applyClearedNodeState(node, nextLibrary, { mutationRevision })) return; setNodeStatusText(node, "已清空当前标签、用户输入与终端预览；历史、模型配置和 NSFW 自定义库已保留。"); },"qwen-te-panel__button--danger","清空当前已选标签、用户输入与终端预览；不删除历史、模型配置和 NSFW 自定义库。"));
	let panelWidget = null;
	panelWidget = node.addDOMWidget("qwen_te_tag_panel","div",panel,{serialize:false,getValue(){return undefined;},setValue(){}}) ?? getWidget(node, "qwen_te_tag_panel");
	if (!panelWidget) {
		panel.remove?.();
		return false;
	}
	try { window.__QWEN_TE_STAGE_CLEANUP_MINI_TOOLBAR__?.(node, { scheduleLayout: false }); } catch (_error) {}
	panelWidget.serialize=false;
	panelWidget.computeSize=()=>[Math.max(560, Math.min(node.size[0], 720)), measurePanelContentHeight(panel, 228)];
	const resizeObserver = attachPanelResizeObserver(node, panel);
	node[PANEL_KEY]={ready:false,library,panel,panelWidget,summaryEl:summary,statusEl:null,refreshSummary:()=>refreshNodeSummary(node,node[PANEL_KEY]?.library ?? library), resizeObserver, rawTagWidgetNames, lastPanelMessage: "", lastExecutedAt: 0, lastExecutionOutputs: [], lastWorkflowQueueRequestedAt: 0, workflowOutputMeta: getNodeWorkflowOutputMeta(node), directStageOutputCache: null, directStageOutputCacheId: "", stageOutputPollTimer: null, stageOutputPollIdleCount: 0, stageOutputPollActiveCount: 0, stageOutputEventRecordCount: 0, stageOutputCacheProcessedIds: [], stageOutputWorkflowProcessedIds: [], autoNegativeSync: autoNegativeSyncState.enabled, continuousReportMeta: getNodeContinuousReportMeta(node), presetBatchState: getNodePresetBatchState(node), continuousBadgeEl: null, continuousReportSummaryEl: null, continuousRuntime: { running: false, token: 0, mode: "", step: 0, total: 0 }, heroCaptionEl: null, randomRuntimePillsEl: null, randomTrackHistoryEl: null, heroBadges: {}, themePoolQuickCardButtons, themePoolQuickStatusEl: null, controlSurface, slotPanel, advancedPanel, panelButtons, displayBodyEl: displayBody, displaySourceEl: displaySource, displayMode: STAGE_DISPLAY_MODES[0]?.key ?? "prompt", displayTabButtons, expandedDisplayOverlay: null, expandedDisplayBodyEl: null, expandedDisplaySourceEl: null, expandedDisplayTabButtons: null, expandedDisplayMetricsEl: null, expandedDisplayViewTabButtons: null, expandedDisplayViewMode: "readable", statusWidget: null, summaryWidget: null, originalOnExecuted: null, onExecutedWrapper: null};
	ensureStagePromptTopStatusWidgets(node, library, summary);
	const originalOnExecuted=node.onExecuted; const onExecutedWrapper=function(){
		if (node[NODE_REMOVED_KEY]) return originalOnExecuted?.apply(this, arguments);
		const executionStartedAt = Date.now();
		const executedArgs = Array.from(arguments);
		if(node[PANEL_KEY]){
			stopStageOutputPolling(node);
			clearStageDisplayPreview(node);
			node[PANEL_KEY].stageOutputRecordSignature = "";
			node[PANEL_KEY].lastExecutedAt = executionStartedAt;
			node[PANEL_KEY].displayClearedAt = 0;
			node[PANEL_KEY].lastExecutionOutputs = [];
			node[PANEL_KEY].directStageOutputCache = null;
			node[PANEL_KEY].directStageOutputCacheId = "";
			node[PANEL_KEY].hydratedExecutionOutputs = [];
			node[PANEL_KEY].hydratedExecutionSourceLabel = "";
			node[PANEL_KEY].previewExecutionOutputs = [];
			node[PANEL_KEY].clearedLinkedOutputSnapshot = [];
			refreshStageDisplay(node);
		}
		const result=originalOnExecuted?.apply(this, arguments);
		captureStageExecutionHistoryFromArgs(node, node[PANEL_KEY]?.library ?? library, executedArgs);
		scheduleStageExecutionOutputCapture(node, node[PANEL_KEY]?.library ?? library, { executionStartedAt });
		setTimeout(()=>{
			if (node[NODE_REMOVED_KEY] || !node[PANEL_KEY]) return;
			const hasPrompt = !!getCurrentStageOutputText(node, STAGE_OUTPUT_INDEX.promptText);
			refreshStageDisplay(node);
			const syncResult = autoSyncStageNegativePrompt(node);
			if (syncResult.ok) {
				setNodeStatusText(node, `已自动同步推荐负面词到 ${String(syncResult.targetNode?.title || syncResult.targetNode?.type || 'CLIPTextEncode')}。`);
			} else if (syncResult.reason === "disabled") {
				setNodeStatusText(node, hasPrompt ? "已记录本次运行结果到历史。" : "正在等待最终提示词写入历史。");
			} else if (syncResult.reason === "not_found") {
				setNodeStatusText(node, hasPrompt ? "已记录本次运行结果到历史。未找到可同步的负面 CLIPTextEncode。" : "正在等待最终提示词写入历史。未找到可同步的负面 CLIPTextEncode。");
			} else {
				setNodeStatusText(node, hasPrompt ? "已记录本次运行结果到历史。" : "正在等待最终提示词写入历史。");
			}
		}, 80);
		return result;
	};
	node.onExecuted=onExecutedWrapper;
	node[PANEL_KEY].originalOnExecuted=originalOnExecuted;
	node[PANEL_KEY].onExecutedWrapper=onExecutedWrapper;
	bindSummaryRefresh(node, library); syncRawWidgetOptions(node, library); const namedState=ensureNodeProperties(node)[NAMED_STATE_KEY]; if(!applyNamedWidgetState(node, namedState)) sanitizeStagePromptNode(node, library); sanitizeStagePromptNode(node, library); persistNamedWidgetState(node); setWidgetGroupVisibility(node, rawTagWidgetNames, false); setWidgetGroupVisibility(node, CONTROL_WIDGET_NAMES, false); setWidgetGroupVisibility(node, ADVANCED_WIDGET_NAMES, false); setWidgetGroupVisibility(node, ALWAYS_HIDDEN_WIDGET_NAMES, false); setSlotPanelVisible(node, false); setAdvancedPanelVisible(node, false); hydrateStageDisplayStateFromPersistedData(node); scheduleHydrateStageDisplayState(node, 8, 90); refreshNodeSummary(node, library); refreshControlSurface(node); refreshSlotPanel(node); refreshAdvancedPanel(node); refreshStageDisplay(node);
	// Only expose a healthy main panel after native controls are compacted and display state is ready.
	node[PANEL_KEY].ready = true;
	node[PANEL_READY_KEY] = true;
	void syncNodeStageOutputCache(node, { shouldCommit: () => !node[NODE_REMOVED_KEY] && !!node[PANEL_KEY] }).then((output)=>{ if (node[NODE_REMOVED_KEY] || !node[PANEL_KEY]) return; if (output) refreshStageDisplay(node); else if (!getStagePromptOutputText(node)) { if (!hydrateStageDisplayStateFromPersistedData(node)) { void syncNodeWorkflowOutputMetaFromHistory(node, { createdAfter: getNodeWorkflowHistorySearchAfter(node), shouldCommit: () => !node[NODE_REMOVED_KEY] && !!node[PANEL_KEY] }).then(() => { if (node[NODE_REMOVED_KEY] || !node[PANEL_KEY]) return; hydrateStageDisplayStateFromPersistedData(node); refreshStageDisplay(node); }).catch(() => {}); } else { refreshStageDisplay(node); } } }).catch(() => {}); requestAnimationFrame(()=>{ if (node[NODE_REMOVED_KEY] || !node[PANEL_KEY]) return; if (node.size[0] < 560) node.setSize([560, node.size[1]]); scheduleNodeLayoutUpdate(node); });
	return true;
}

function rollbackStagePromptNodeEnhancement(node) {
	node[PANEL_READY_KEY] = false;
	const panelState = node?.[PANEL_KEY];
	if (!panelState) {
		const orphanPanelWidget = getWidget(node, "qwen_te_tag_panel");
		const removed = orphanPanelWidget ? removeNodeWidgetSafely(node, orphanPanelWidget) : false;
		if (removed || !orphanPanelWidget) delete node[PANEL_READY_KEY];
		return removed;
	}
	stopStageOutputPolling(node);
	try { panelState.resizeObserver?.disconnect?.(); } catch (_error) {}
	if (node.onExecuted === panelState.onExecutedWrapper) node.onExecuted = panelState.originalOnExecuted;
	if (panelState.panelWidget && Array.isArray(node.widgets) && node.widgets.includes(panelState.panelWidget)) {
		removeNodeWidgetSafely(node, panelState.panelWidget);
	}
	try { panelState.panel?.remove?.(); } catch (_error) {}
	delete node[PANEL_KEY];
	delete node[PANEL_READY_KEY];
	return true;
}

function scheduleEnhanceStagePromptNode(node) {
	if (!node || node[NODE_REMOVED_KEY] || node[PANEL_KEY] || shouldForceMiniToolbarMode()) return;
	let state = node[NODE_ENHANCE_RETRY_STATE_KEY];
	if (!state) {
		state = { running: false, timer: null, tries: 0, cancelled: false, run: null };
		const scheduleRetry = () => {
			if (state.cancelled || node[NODE_REMOVED_KEY] || node[PANEL_KEY] || state.timer != null) return;
			if (state.tries >= 120) {
				state.cancelled = true;
				return;
			}
			state.tries += 1;
			const delayMs = node.addWidget ? Math.min(5000, 200 + state.tries * 150) : Math.min(1000, 50 + state.tries * 25);
			state.timer = setTimeout(() => {
				state.timer = null;
				void state.run?.();
			}, delayMs);
			state.timer?.unref?.();
		};
		state.run = async () => {
			if (state.cancelled || node[NODE_REMOVED_KEY] || node[PANEL_KEY] || state.running || shouldForceMiniToolbarMode()) return;
			if (typeof node.addWidget !== "function" || typeof node.addDOMWidget !== "function") {
				scheduleRetry();
				return;
			}
			state.running = true;
			try {
				let library = await getPromptLibrary();
				if (state.cancelled || node[NODE_REMOVED_KEY] || node[PANEL_KEY]) return;
				if (!hasPromptLibraryContent(library)) {
					library = buildNativePromptLibraryFallback(node);
					if (!hasPromptLibraryContent(library)) {
						scheduleRetry();
						return;
					}
				}
				const enhanced = enhanceStagePromptNode(node, library);
				if (enhanced && node[PANEL_KEY]) clearStageNodeEnhanceRetry(node);
				else scheduleRetry();
			} catch (error) {
				rollbackStagePromptNodeEnhancement(node);
				try { window.__QWEN_TE_STAGE_ENSURE_MINI_TOOLBAR__?.(node); } catch (_error) {}
				console.error("[QwenTE UI] enhanceStagePromptNode failed", error);
				scheduleRetry();
			} finally {
				state.running = false;
			}
		};
		node[NODE_ENHANCE_RETRY_STATE_KEY] = state;
	}
	if (!state.running && state.timer == null) void state.run?.();
}

function clearStageNodeEnhanceRetry(node) {
	const state = node?.[NODE_ENHANCE_RETRY_STATE_KEY];
	if (!state) return;
	state.cancelled = true;
	if (state.timer != null) clearTimeout(state.timer);
	state.timer = null;
	delete node[NODE_ENHANCE_RETRY_STATE_KEY];
}

function disposeNodeOwnedModals(node) {
	for (const overlay of document.querySelectorAll?.(".qwen-te-modal") ?? []) {
		if (overlay?.__qwenNode === node) disposeModalOverlay(overlay);
	}
}

function cleanupStagePromptNodeRuntime(node) {
	if (!node) return;
	node[NODE_REMOVED_KEY] = true;
	abortOwnedRequests(node);
	clearStageNodeEnhanceRetry(node);
	disposeNodeOwnedModals(node);
	node[NODE_STATE_MUTATION_REVISION_KEY] = Math.max(0, Number(node[NODE_STATE_MUTATION_REVISION_KEY] ?? 0) || 0) + 1;
	node[NODE_LIBRARY_REFRESH_REVISION_KEY] = Math.max(0, Number(node[NODE_LIBRARY_REFRESH_REVISION_KEY] ?? 0) || 0) + 1;
	node[NODE_QUALITY_AUDIT_REVISION_KEY] = Math.max(0, Number(node[NODE_QUALITY_AUDIT_REVISION_KEY] ?? 0) || 0) + 1;
	const panelState = node[PANEL_KEY];
	node[PANEL_READY_KEY] = false;
	if (!panelState) {
		delete node[PANEL_READY_KEY];
		return;
	}
	panelState.stageOutputCaptureToken = `removed_${Date.now()}`;
	if (panelState.continuousRuntime) {
		panelState.continuousRuntime.token = Math.max(0, Number(panelState.continuousRuntime.token ?? 0) || 0) + 1;
		panelState.continuousRuntime.running = false;
	}
	stopStageOutputPolling(node);
	try { panelState.resizeObserver?.disconnect?.(); } catch (_error) {}
	if (panelState.expandedDisplayOverlay instanceof HTMLElement) disposeModalOverlay(panelState.expandedDisplayOverlay);
	if (node.onExecuted === panelState.onExecutedWrapper) node.onExecuted = panelState.originalOnExecuted;
	const panelWidget = panelState.panelWidget;
	if (panelWidget && Array.isArray(node.widgets) && node.widgets.includes(panelWidget)) {
		removeNodeWidgetSafely(node, panelWidget);
	}
	try { panelState.panel?.remove?.(); } catch (_error) {}
	delete node[PANEL_KEY];
	delete node[PANEL_READY_KEY];
}

function enhanceExistingStagePromptNodes() {
	try {
		disableFixUiRuntime();
		const nodes = app.graph?._nodes ?? [];
		for (const node of nodes) {
			if (node?.[NODE_REMOVED_KEY]) continue;
			if (isStagePromptNode(node)) {
				cleanupFixUiArtifacts(node, { preserveMiniToolbar: !node[PANEL_KEY] });
				compactStagePromptOutputs(node);
				const panelState = node[PANEL_KEY];
				const topWidgetsHealthy =
					panelState &&
					node.widgets?.[0]?.name === "状态" &&
					node.widgets?.[1]?.name === "摘要" &&
					node.widgets.filter((widget) => widget?.name === "状态").length === 1 &&
					node.widgets.filter((widget) => widget?.name === "摘要").length === 1;
				if (panelState && !topWidgetsHealthy) {
					ensureStagePromptTopStatusWidgets(node, panelState.library ?? { slot_config: [], tag_library: {} }, panelState.summaryEl ?? { textContent: "" });
					scheduleNodeLayoutUpdate(node);
				}
			}
			if (isStagePromptNode(node) && !node[PANEL_KEY] && !shouldForceMiniToolbarMode()) {
				scheduleEnhanceStagePromptNode(node);
			}
		}
	} catch (_error) {}
}

function registerStagePromptMiniBridge() {
	window.__QWEN_TE_STAGE_ROLLBACK__ = (nodeOrId) => {
		const targetNode = resolveStagePromptBridgeNode(nodeOrId);
		return targetNode ? rollbackStagePromptNodeEnhancement(targetNode) : false;
	};
	window.__QWEN_TE_STAGE_OPEN_TAG_DIALOG__ = async (nodeOrId) => {
		const targetNode = resolveStagePromptBridgeNode(nodeOrId);
		if (!targetNode) return false;
		const library = await getFreshLibraryForUi(targetNode, targetNode?.[PANEL_KEY]?.library ?? null);
		if (resolveStagePromptBridgeNode(targetNode) !== targetNode) return false;
		openTagDialog(targetNode, library);
		return true;
	};
	window.__QWEN_TE_STAGE_OPEN_NSFW_WORKSPACE__ = async (nodeOrId) => {
		const targetNode = resolveStagePromptBridgeNode(nodeOrId);
		if (!targetNode) return false;
		const library = await getFreshLibraryForUi(targetNode, targetNode?.[PANEL_KEY]?.library ?? null);
		if (resolveStagePromptBridgeNode(targetNode) !== targetNode) return false;
		openNsfwWorkspaceDialog(targetNode, library);
		return true;
	};
	window.__QWEN_TE_STAGE_GET_FRESH_LIBRARY__ = async (nodeOrId) => {
		const targetNode = resolveStagePromptBridgeNode(nodeOrId);
		if (!targetNode) return null;
		const library = await getFreshLibraryForUi(targetNode, targetNode?.[PANEL_KEY]?.library ?? null);
		return resolveStagePromptBridgeNode(targetNode) === targetNode ? library : null;
	};
	window.__QWEN_TE_STAGE_BUILD_RANDOM_STATE__ = async (nodeOrId, library, sourceState = null) => {
		const targetNode = resolveStagePromptBridgeNode(nodeOrId);
		if (!targetNode || !library) return null;
		const state = await buildRandomState(targetNode, library, sourceState);
		return resolveStagePromptBridgeNode(targetNode) === targetNode ? state : null;
	};
	window.__QWEN_TE_STAGE_APPLY_RANDOM_STATE__ = applyRandomStateFromBridge;
	window.__QWEN_TE_STAGE_CLEAR_NODE_STATE__ = clearNodeStateFromBridge;
	window.__QWEN_TE_STAGE_APPLY_NODE_STATE__ = (nodeOrId, library, state, options = {}) => {
		const targetNode = resolveStagePromptBridgeNode(nodeOrId);
		if (!targetNode || !library || !state) return false;
		return applyNodeState(targetNode, library, state, options);
	};
	window.__QWEN_TE_STAGE_COLLECT_NODE_STATE__ = (nodeOrId, library) => {
		const targetNode = resolveStagePromptBridgeNode(nodeOrId);
		if (!targetNode || !library) return null;
		return collectNodeState(targetNode, library);
	};
	window.__QWEN_TE_STAGE_RECORD_HISTORY__ = (nodeOrId, state, source = "random") => {
		const targetNode = resolveStagePromptBridgeNode(nodeOrId);
		if (!targetNode || !state) return false;
		recordNodeHistory(targetNode, state, source);
		return true;
	};
	window.__QWEN_TE_STAGE_GET_PROMPT_OUTPUT__ = (nodeOrId) => {
		const targetNode = resolveStagePromptBridgeNode(nodeOrId);
		if (!targetNode) return "";
		return String(getStagePromptOutputText(targetNode) ?? "");
	};
}

const registerStagePromptExtension = () => {
	if (!app?.registerExtension) return false;
	registerStagePromptMiniBridge();

	app.registerExtension({
		name: EXTENSION_NAME,
		async beforeRegisterNodeDef(nodeType, nodeData) {
			const isTargetNodeDef =
				TARGET_NODE_CLASSES.has(nodeData.name) ||
				(typeof nodeData.display_name === "string" && hasStagePromptDisplayName(nodeData.display_name)) ||
				(typeof nodeData.displayName === "string" && hasStagePromptDisplayName(nodeData.displayName));
			if (!isTargetNodeDef) return;
			if (nodeType.prototype[STAGE_NODE_LIFECYCLE_PATCH_KEY]) return;
			nodeType.prototype[STAGE_NODE_LIFECYCLE_PATCH_KEY] = true;
			const originalConfigure = nodeType.prototype.configure;
			nodeType.prototype.configure = function () {
				const config = arguments[0];
				if (config?.widgets_values instanceof Array) config.widgets_values = normalizeConfiguredWidgetValues(this, config);
				const result = originalConfigure?.apply(this, arguments);
				if (isStagePromptNode(this)) compactStagePromptOutputs(this);
				if (isStagePromptNode(this)) scheduleHydrateStageDisplayState(this, 10, 120);
				return result;
			};
			const originalOnSerialize = nodeType.prototype.onSerialize;
			nodeType.prototype.onSerialize = function (serialized) {
				const result = originalOnSerialize?.apply(this, arguments);
				normalizeSerializedNodePayload(this, serialized);
				return result;
			};
			const originalSerialize = nodeType.prototype.serialize;
			nodeType.prototype.serialize = function () {
				const serialized = originalSerialize?.apply(this, arguments) ?? {};
				return normalizeSerializedNodePayload(this, serialized);
			};
			const originalOnNodeCreated = nodeType.prototype.onNodeCreated;
			nodeType.prototype.onNodeCreated = function () {
				const result = originalOnNodeCreated?.apply(this, arguments);
				delete this[NODE_REMOVED_KEY];
				ensureNodeCacheNamespace(this);
				scheduleEnhanceStagePromptNode(this);
				return result;
			};
			const originalOnRemoved = nodeType.prototype.onRemoved;
			nodeType.prototype.onRemoved = function () {
				cleanupStagePromptNodeRuntime(this);
				return originalOnRemoved?.apply(this, arguments);
			};
		},
		async setup() {
			injectStyles();
			disableFixUiRuntime();
			enhanceExistingStagePromptNodes();
			installGlobalStagePromptQueueCapture();
			if (window.__qwenTeStagePromptTimer != null) clearInterval(window.__qwenTeStagePromptTimer);
			let maintenancePasses = 0;
			const timer = setInterval(() => {
				maintenancePasses += 1;
				enhanceExistingStagePromptNodes();
				installGlobalStagePromptQueueCapture();
				if (maintenancePasses >= 30) {
					clearInterval(timer);
					if (window.__qwenTeStagePromptTimer === timer) window.__qwenTeStagePromptTimer = null;
				}
			}, 1000);
			timer?.unref?.();
			if (app.graph && !app.graph[GRAPH_NODE_ADDED_PATCH_KEY]) {
				const originalOnNodeAdded = app.graph.onNodeAdded;
				app.graph[GRAPH_NODE_ADDED_PATCH_KEY] = true;
				app.graph.onNodeAdded = function (node) {
					const result = originalOnNodeAdded?.apply(this, arguments);
					delete node?.[NODE_REMOVED_KEY];
					if (isStagePromptNode(node)) {
						ensureNodeCacheNamespace(node);
						scheduleEnhanceStagePromptNode(node);
					}
					return result;
				};
			}
			window.__qwenTeStagePromptTimer = timer;
		},
		async nodeCreated(node) {
			if (node) delete node[NODE_REMOVED_KEY];
			if (isStagePromptNode(node)) {
				ensureNodeCacheNamespace(node);
				scheduleEnhanceStagePromptNode(node);
			}
		},
	});
	return true;
};

if (!registerStagePromptExtension()) {
	const waitTimer = setInterval(() => {
		if (registerStagePromptExtension()) clearInterval(waitTimer);
	}, 300);
}
