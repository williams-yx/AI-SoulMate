# 硬件商城商品图片说明

## 图片位置
请将商品图片放在此目录：`/home/ubuntu/ai-soul-mate/v0.7.0/frontend-vue/public/images/products/`

## 图片要求

### 尺寸和比例
- **推荐尺寸**：224px × 192px（桌面端显示尺寸）
- **图片比例**：7:6（约 1.17:1）
- **最小尺寸**：建议至少 448px × 384px（2倍图，适配高分辨率屏幕）

### 文件格式
- 支持格式：JPG、PNG、WebP
- 推荐格式：JPG（文件小）或 WebP（质量好且文件小）

### 文件命名
请按照以下命名规则放置图片：

1. **AI 智能底座**：`base-soul.jpg`（或 `.png`、`.webp`）
2. **定制白模（PLA 打印）**：`print-pla.jpg`
3. **PLA 耗材**：`material-pla.jpg`

## 图片路径映射

代码中使用的路径：
- `/images/products/base-soul.jpg` → `public/images/products/base-soul.jpg`
- `/images/products/print-pla.jpg` → `public/images/products/print-pla.jpg`
- `/images/products/material-pla.jpg` → `public/images/products/material-pla.jpg`

## 注意事项

1. 图片会被自动裁剪为 7:6 比例显示（使用 `object-cover`）
2. 如果图片加载失败，会自动显示占位图 `/images/product-placeholder.png`
3. 建议图片文件大小控制在 200KB 以内，以保证加载速度
4. 图片背景建议使用透明或与页面主题色（深色）协调的颜色

## 示例图片尺寸

```
桌面端显示：224px × 192px
移动端显示：全宽 × 192px（高度固定）
```

如果需要调整显示尺寸，请修改 `MarketPage.vue` 中的 Tailwind CSS 类：
- `md:w-56`：桌面端宽度（224px）
- `h-48`：高度（192px）
