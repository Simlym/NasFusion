import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'NasFusion',
  description: '基于 PT 站点的媒体资源管理系统',
  base: '/NasFusion/',
  ignoreDeadLinks: [/^http:\/\/localhost/],

  head: [
    ['link', { rel: 'icon', href: '/NasFusion/favicon.ico' }]
  ],

  themeConfig: {
    logo: '/logo.png',
    siteTitle: 'NasFusion',

    nav: [
      { text: '首页', link: '/' },
      {
        text: '指南',
        items: [
          { text: '项目介绍', link: '/guide/introduction' },
          { text: '快速开始', link: '/guide/quick-start' },
          { text: '系统架构', link: '/guide/architecture' },
          { text: '配置说明', link: '/guide/configuration' },
        ]
      },
      {
        text: '功能特性',
        items: [
          { text: 'PT 站点管理', link: '/features/pt-sites' },
          { text: '资源同步与搜索', link: '/features/resource-sync' },
          { text: '资源识别', link: '/features/identification' },
          { text: '订阅与自动下载', link: '/features/subscription' },
          { text: '下载管理', link: '/features/download' },
          { text: '媒体库管理', link: '/features/media-library' },
          { text: '任务调度', link: '/features/scheduler' },
          { text: '通知系统', link: '/features/notification' },
        ]
      },
      {
        text: '部署',
        items: [
          { text: 'Docker 部署', link: '/deploy/docker' },
          { text: '手动部署', link: '/deploy/manual' },
        ]
      },
      { text: '常见问题', link: '/faq' },
    ],

    sidebar: {
      '/guide/': [
        {
          text: '入门指南',
          items: [
            { text: '项目介绍', link: '/guide/introduction' },
            { text: '快速开始', link: '/guide/quick-start' },
            { text: '系统架构', link: '/guide/architecture' },
            { text: '配置说明', link: '/guide/configuration' },
          ]
        }
      ],
      '/features/': [
        {
          text: '数据采集',
          items: [
            { text: 'PT 站点管理', link: '/features/pt-sites' },
            { text: '资源同步与搜索', link: '/features/resource-sync' },
            { text: '资源识别', link: '/features/identification' },
          ]
        },
        {
          text: '自动化下载',
          items: [
            { text: '订阅与自动下载', link: '/features/subscription' },
            { text: '下载管理', link: '/features/download' },
          ]
        },
        {
          text: '媒体库',
          items: [
            { text: '媒体库管理', link: '/features/media-library' },
          ]
        },
        {
          text: '系统运维',
          items: [
            { text: '任务调度', link: '/features/scheduler' },
            { text: '通知系统', link: '/features/notification' },
          ]
        }
      ],
      '/deploy/': [
        {
          text: '部署指南',
          items: [
            { text: 'Docker 部署', link: '/deploy/docker' },
            { text: '手动部署', link: '/deploy/manual' },
          ]
        }
      ]
    },

    socialLinks: [
      { icon: 'github', link: 'https://github.com/Simlym/NasFusion' }
    ],

    footer: {
      message: '基于 MIT 协议发布',
      copyright: 'Copyright © 2025-present NasFusion'
    },

    search: {
      provider: 'local'
    },

    outline: {
      label: '本页目录',
      level: [2, 3]
    },

    docFooter: {
      prev: '上一页',
      next: '下一页'
    },

    lastUpdated: {
      text: '最后更新于'
    },

    editLink: {
      pattern: 'https://github.com/Simlym/NasFusion/edit/main/docs/:path',
      text: '在 GitHub 上编辑此页'
    }
  },

  locales: {
    root: {
      label: '简体中文',
      lang: 'zh-CN'
    }
  }
})
