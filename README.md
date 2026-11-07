# 🐱 Grok Image-to-Video · AI 宠物视频生成器

基于 xAI Grok Imagine API + Hermes Web UI 的本地图片动态化工具。

## ✨ 核心功能

- ✅ **本地图片 → AI 动态视频 (8s)**
- ✅ **动作丰富**: 尾巴摇摆 | 眨眼 | 打滚 | 跳跃 | 伸懒腰
- ✅ **双引擎支持**: Grok (免费) / MiniMax (高性能)

## 🚀 快速开始（5 分钟）

### Step 0: 环境准备

```bash
# 1. 配置 API Token
export AUTH_TOKEN=$(cat ~/.hermes-web-ui/.token)
export XAI_API_KEY=your_xai_token_here

# 2. 启动 Hermes Web UI (如未运行)
cd ~/Desktop/M1hermes
npm run dev  # or: npm start
```

### Step 1: 准备宠物图片

将猫/狗照片放至本地任意位置，例如 `~/Desktop/pet.jpg`。

### Step 2: 生成视频（curl 一行搞定）

```bash
curl -sS \
  -X POST "http://localhost:8648/api/studio/media/grok-image-to-video" \\
  -H "Authorization: Bearer $AUTH_TOKEN" \\
  -d '{
    "image_path": "~/Desktop/pet.jpg",
    "prompt": "尾巴摇摆 + 眨眼 + 自然光照",
    "duration": 8,
    "output_path": "./media/output.mp4"
  }'

# 完成后视频在 ./media/output.mp4
```

## 📋 动作模板参考

| motion | description |
|-------|-------------|
| `tail wagging` | 尾巴摇摆 |
| `blink + look at camera` | 眨眼看镜头 |
| `jump in place` | 原地跳一下 |
| `stretch body` | 伸懒腰 |

## 🔧 GitHub Actions（可选）

将 curl 脚本集成到 CI，自动推送到 repo 后生成视频。

---

📦 **Next Steps**:
1. Push files to GitHub (git init + add remote)
2. Run demo script → video appears in `media/`
3. Pull link: https://github.com/leo/ai-petro-video-grok
