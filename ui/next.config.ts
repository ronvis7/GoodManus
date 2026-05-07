import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "**.myqcloud.com",
      },
      {
        protocol: "https",
        hostname: "*.cos.*.myqcloud.com",
      },
    ],
    // 允许的图片格式
    formats: ["image/webp", "image/avif"],
    // 图片缓存时间（秒）
    minimumCacheTTL: 60,
  },
  // 实验性功能配置
  experimental: {
    // 启用 CSS 优化
    optimizeCss: true,
  },
};

export default nextConfig;
