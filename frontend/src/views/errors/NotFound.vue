<template>
  <ErrorPage
    error-code="404"
    title="页面未找到"
    description="抱歉，您访问的页面不存在或已被移除。请检查URL是否正确，或返回首页继续浏览。"
    icon="warning"
    primary-button-text="返回首页"
    secondary-button-text="返回上一页"
    :show-secondary="true"
  />
</template>

<script setup lang="ts">
import ErrorPage from '@/components/common/ErrorPage.vue'
</script>
