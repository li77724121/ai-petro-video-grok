# 🐱 AI 宠物短视频生成器（纯本地 · 零 API 费用）

用 **Python 逐帧程序化绘制 + ffmpeg 编码**，在一台 16GB 的 Mac mini M1 上本地生成竖屏宠物短视频。
不调用任何云端 API，不需要下载扩散模型权重，10 秒成片约 **1 分 40 秒**渲染完成。

## 🎬 成片参数

- 分辨率 1080×1920（9:16 竖屏），30 fps，10 秒，H.264 + AAC，约 2.1 MB
- 主体：卡通橘猫「豆豆」，会呼吸起伏、摇尾巴、间隔眨眼、偶尔张嘴叫
- 动效：尾巴正弦摆动、身体呼吸缩放、耳朵抖动、爱心粒子上浮、镜头缓慢推近
- 配乐：ffmpeg 本地合成柔和和弦垫音（无版权素材依赖）

## 🚀 运行

```bash
# 依赖：Python 3.11+、Pillow、numpy、ffmpeg（macOS: brew install ffmpeg）
python3 -m venv .venv && . .venv/bin/activate
pip install pillow numpy

python render_pet_video.py
# 输出：~/Desktop/M1hermes/media/pet-ai-cartoon.mp4
```

定制入口：`W, H, FPS, DUR`（尺寸/帧率/时长）、`draw_text()` 里的标题文案、
`draw_cat()` 里的配色常量 `ORANGE / PINK / DARK`。

## ☁️ 可选：接云端图生视频

同一目录内保留了 Grok / MiniMax 的 curl 封装（`grok-api.sh`、`demo.sh`），
配置 `XAI_API_KEY` 或 `MINIMAX_API_KEY` 后即可用真图生成：

```bash
export AUTH_TOKEN=$(cat ~/.hermes-web-ui/.token)
./grok-api.sh ~/Desktop/pet.jpg "尾巴摇摆 + 眨眼" 8
```

## ⚠️ 为什么默认不走 AI 图生视频

实测三种云端/本地模型的可用性：

| 方案 | 结论 |
|---|---|
| Hermes Web UI → Grok | 接口通（`127.0.0.1:8748`），但返回 `missing_xai_token`，需要 xAI 凭据 |
| MiniMax Hailuo | 需要 `MINIMAX_API_KEY`，未配置 |
| 本地 mflux Z-Image-Turbo | 权重仅下载 255MB / 24.6GB，hf-mirror 实测 420 KB/s ≈ 16 小时，不可行 |

因此改用零依赖的程序化渲染路线，保证「本地、免费、可复现」。

## 🧩 踩过的坑（改代码时会遇到）

1. **尾巴分节条纹**：用多段粗线（`draw.line(width=...)`）画尾巴，圆角接头处必然叠出条带。必须按路径法线偏移生成**单条闭合多边形**再填充。
2. **爪子和肚皮融成一片**：两者都是米白且肚皮底边与爪子重叠。要让肚皮上移收口，并把爪子调深一档、加描边。
3. **胡须穿过腮红**：绘制顺序应为「胡须 → 腮红」，让腮红盖住笔触根部。
4. **爱心糊在猫脸上**：粒子层若在猫之后合成会盖住主体，应画在猫之前。
5. **`alpha_composite` 报 `image has wrong mode`**：背景函数返回 RGB 时必须先 `.convert("RGBA")`。
6. **逐帧高斯模糊太慢**：柔光/暗角用 numpy 预计算一张 mask 复用，不要每帧 `GaussianBlur`。

## 📄 License

MIT
