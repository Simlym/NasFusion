---
layout: home

hero:
  name: "NasFusion"
  text: "PT 媒体资源管理系统"
  tagline: 以 PT 站点为起点，全生命周期管理你的媒体库。同步、识别、追剧、整理，一步到位。
  image:
    src: /images/hero.png
    alt: NasFusion
  actions:
    - theme: brand
      text: 快速开始
      link: /guide/quick-start
    - theme: alt
      text: 了解更多
      link: /guide/introduction
    - theme: alt
      text: 在 GitHub 上查看
      link: https://github.com/Simlym/NasFusion

features:
  - icon: 🎯
    title: PT 优先，本地缓存
    details: 定期将 PT 站点资源索引同步到本地数据库，搜索响应 < 100ms，无需频繁访问站点，降低封号风险。
  - icon: 🔍
    title: 智能资源识别
    details: 自动解析资源标题，识别电影/电视剧，关联 TMDB/豆瓣元数据。支持中英文、动漫等多种标题格式。
  - icon: 📺
    title: 全自动追剧
    details: 订阅电视剧季度，新资源出现后自动匹配并下载。按质量优先级打分，优先选择最优资源。
  - icon: 📁
    title: 智能文件整理
    details: 下载完成后自动硬链接整理，保持做种不受影响。自动刮削海报、简介等元数据，符合 Jellyfin/Plex 规范。
  - icon: 🎬
    title: 媒体服务器集成
    details: 与 Jellyfin / Emby / Plex 深度集成，文件整理后自动刷新媒体库，同步观看历史。
  - icon: ⏰
    title: 任务调度系统
    details: 基于 APScheduler 的后台任务系统，定时同步、健康检查、下载监控全自动运行，支持手动触发和进度追踪。
  - icon: 🔔
    title: 多渠道实时通知
    details: 事件驱动的通知系统，下载完成、站点异常即时推送 Telegram 或邮件，让你随时掌握系统状态。
  - icon: 🌐
    title: 多站点支持
    details: 内置 MTeam 适配器，支持多站点同时配置。适配器模式便于扩展，计划支持更多 PT 站点。
---

<style>
:root {
  --vp-home-hero-name-color: transparent;
  --vp-home-hero-name-background: -webkit-linear-gradient(120deg, #bd34fe 30%, #41d1ff);
  --vp-home-hero-image-background-image: linear-gradient(-45deg, #bd34fe50 50%, #47caff50 50%);
  --vp-home-hero-image-filter: blur(44px);
}
</style>
