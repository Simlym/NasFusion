<template>
  <div class="login-page">
    <!-- Ambient ocean bubbles -->
    <div class="ocean-ambient" aria-hidden="true">
      <span v-for="n in 14" :key="n" class="bubble"></span>
    </div>

    <!-- Bottom wave decoration -->
    <div class="page-waves" aria-hidden="true">
      <svg viewBox="0 0 1440 180" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M0 90 Q180 30 360 90 Q540 150 720 90 Q900 30 1080 90 Q1260 150 1440 90 L1440 180 L0 180 Z"
              fill="rgba(56,189,248,0.04)"/>
        <path d="M0 110 Q200 60 400 110 Q600 160 800 110 Q1000 60 1200 110 Q1320 140 1440 120 L1440 180 L0 180 Z"
              fill="rgba(56,189,248,0.06)"/>
        <path d="M0 135 Q240 105 480 135 Q720 165 960 135 Q1200 105 1440 135 L1440 180 L0 180 Z"
              fill="rgba(56,189,248,0.05)"/>
      </svg>
    </div>

    <!-- Centered login card -->
    <div class="login-card">
      <!-- Brand header -->
      <div class="card-brand">
        <div class="brand-logo">
          <NasFusionLogo size="48" />
        </div>
        <div class="brand-text">
          <h1 class="brand-name">NasFusion</h1>
          <p class="brand-tagline">智能媒体资源管理平台</p>
        </div>
      </div>

      <div class="card-divider">
        <span class="divider-label">登录账户</span>
      </div>

      <!-- Form -->
      <el-form
        ref="loginFormRef"
        :model="loginForm"
        :rules="rules"
        class="login-form"
        @submit.prevent="handleLogin"
      >
        <el-form-item prop="username">
          <el-input
            v-model="loginForm.username"
            placeholder="用户名"
            size="large"
            clearable
            @keyup.enter="handleLogin"
          >
            <template #prefix>
              <el-icon class="input-icon"><User /></el-icon>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="密码"
            size="large"
            show-password
            @keyup.enter="handleLogin"
          >
            <template #prefix>
              <el-icon class="input-icon"><Lock /></el-icon>
            </template>
          </el-input>
        </el-form-item>

        <div class="form-options">
          <el-checkbox v-model="loginForm.remember">记住登录状态</el-checkbox>
        </div>

        <transition name="alert-fade">
          <div v-if="securityAlert.visible" :class="['security-alert', securityAlert.type]">
            <svg class="alert-icon" viewBox="0 0 16 16" fill="currentColor">
              <path d="M8 1a7 7 0 1 0 0 14A7 7 0 0 0 8 1zm0 3a.75.75 0 0 1 .75.75v3.5a.75.75 0 0 1-1.5 0v-3.5A.75.75 0 0 1 8 4zm0 7.5a1 1 0 1 1 0-2 1 1 0 0 1 0 2z"/>
            </svg>
            <div class="alert-body">
              <span>{{ securityAlert.message }}</span>
              <span v-if="lockoutCountdown > 0" class="countdown">{{ formatCountdown(lockoutCountdown) }} 后可重试</span>
            </div>
          </div>
        </transition>

        <el-button
          type="primary"
          size="large"
          :loading="loading"
          :disabled="lockoutCountdown > 0"
          class="login-btn"
          @click="handleLogin"
        >
          <span v-if="lockoutCountdown > 0">账户已锁定 ({{ formatCountdown(lockoutCountdown) }})</span>
          <span v-else-if="!loading">登 录</span>
          <span v-else>登录中...</span>
        </el-button>
      </el-form>
    </div>

    <p class="page-footer">© 2026 NasFusion</p>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onUnmounted, defineComponent, h } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import type { FormInstance, FormRules } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { useSettingsStore } from '@/stores'
import type { LoginForm, LoginErrorDetail } from '@/types'

// ===== NasFusion Logo Component =====
const NasFusionLogo = defineComponent({
  props: { size: { type: [Number, String], default: 56 } },
  setup(props) {
    return () => h('svg', {
      viewBox: '0 0 56 56', fill: 'none',
      xmlns: 'http://www.w3.org/2000/svg',
      width: props.size, height: props.size,
      style: 'display:block;flex-shrink:0'
    }, [
      h('defs', [
        h('linearGradient', { id: 'nf-bg', x1: '0', y1: '0', x2: '56', y2: '56', gradientUnits: 'userSpaceOnUse' }, [
          h('stop', { 'stop-color': '#071524' }),
          h('stop', { offset: '1', 'stop-color': '#0c2038' })
        ]),
        h('linearGradient', { id: 'nf-mark', x1: '14', y1: '16', x2: '42', y2: '40', gradientUnits: 'userSpaceOnUse' }, [
          h('stop', { 'stop-color': '#7DD3FC' }),
          h('stop', { offset: '0.45', 'stop-color': '#38BDF8' }),
          h('stop', { offset: '1', 'stop-color': '#0EA5E9' })
        ]),
        h('filter', { id: 'nf-glow', x: '-20%', y: '-20%', width: '140%', height: '140%' }, [
          h('feGaussianBlur', { stdDeviation: '1.5', result: 'blur' }),
          h('feMerge', [h('feMergeNode', { in: 'blur' }), h('feMergeNode', { in: 'SourceGraphic' })])
        ])
      ]),
      h('rect', { width: '56', height: '56', rx: '13', fill: 'url(#nf-bg)' }),
      h('rect', { x: '1', y: '1', width: '54', height: '54', rx: '12', stroke: 'rgba(56,189,248,0.35)', 'stroke-width': '1' }),
      h('circle', { cx: '10', cy: '10', r: '1.5', fill: 'rgba(56,189,248,0.4)' }),
      h('circle', { cx: '46', cy: '46', r: '1.5', fill: 'rgba(56,189,248,0.4)' }),
      h('path', {
        d: 'M14 40 L14 16 C19 25 23 21 28 27 C33 33 37 29 42 40 L42 16',
        stroke: 'url(#nf-mark)', 'stroke-width': '3', 'stroke-linecap': 'round',
        'stroke-linejoin': 'round', fill: 'none', filter: 'url(#nf-glow)'
      }),
      h('path', {
        d: 'M18 44 Q23 41 28 44 Q33 47 38 44',
        stroke: 'rgba(56,189,248,0.35)', 'stroke-width': '1.5', 'stroke-linecap': 'round', fill: 'none'
      })
    ])
  }
})

// ===== Auth Logic =====
const router = useRouter()
const userStore = useUserStore()
const settingsStore = useSettingsStore()

const loading = ref(false)
const loginFormRef = ref<FormInstance>()
const lockoutCountdown = ref(0)
let countdownTimer: ReturnType<typeof setInterval> | null = null

const loginForm = reactive<LoginForm>({ username: '', password: '', remember: false })

const securityAlert = reactive({
  visible: false,
  type: 'warning' as 'warning' | 'error',
  message: ''
})

const rules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名长度在 3 到 50 个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少 6 个字符', trigger: 'blur' }
  ]
}

function formatCountdown(seconds: number): string {
  const min = Math.floor(seconds / 60)
  const sec = seconds % 60
  return min > 0 ? `${min}分${sec}秒` : `${sec}秒`
}

function startLockoutCountdown(seconds: number) {
  if (countdownTimer) clearInterval(countdownTimer)
  lockoutCountdown.value = seconds
  countdownTimer = setInterval(() => {
    lockoutCountdown.value--
    if (lockoutCountdown.value <= 0) {
      if (countdownTimer) { clearInterval(countdownTimer); countdownTimer = null }
      securityAlert.visible = false
    }
  }, 1000)
}

function handleLoginError(error: any) {
  const detail: LoginErrorDetail | undefined = error?.response?.data?.detail
  if (detail && typeof detail === 'object' && detail.code) {
    switch (detail.code) {
      case 'wrong_password':
        securityAlert.type = detail.remaining_attempts !== undefined && detail.remaining_attempts <= 2 ? 'error' : 'warning'
        securityAlert.message = detail.remaining_attempts !== undefined
          ? `密码错误，还剩 ${detail.remaining_attempts} 次尝试机会`
          : '用户名或密码错误'
        securityAlert.visible = true
        break
      case 'account_locked':
        securityAlert.type = 'error'
        securityAlert.message = '由于多次密码错误，账户已被临时锁定'
        securityAlert.visible = true
        if (detail.remaining_seconds) startLockoutCountdown(detail.remaining_seconds)
        break
      case 'account_disabled':
        securityAlert.type = 'error'
        securityAlert.message = '账户已被禁用，请联系管理员'
        securityAlert.visible = true
        break
      default:
        ElMessage.error(detail.message || '登录失败')
    }
  } else {
    ElMessage.error('登录失败，请检查用户名和密码')
  }
}

const handleLogin = async () => {
  if (!loginFormRef.value) return
  await loginFormRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        const success = await userStore.login(loginForm)
        if (success) {
          securityAlert.visible = false
          await settingsStore.initSettings()
          ElMessage.success('登录成功')
          router.push('/dashboard')
        } else {
          ElMessage.error('登录失败，请检查用户名和密码')
        }
      } catch (error: any) {
        handleLoginError(error)
      } finally {
        loading.value = false
      }
    }
  })
}

onUnmounted(() => { if (countdownTimer) clearInterval(countdownTimer) })
</script>

<style scoped lang="scss">
// ==========================================
// Page Shell
// ==========================================
.login-page {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 24px 16px 80px;
  overflow: hidden;
  background: radial-gradient(
    ellipse 120% 80% at 50% 0%,
    var(--nf-bg-container) 0%,
    var(--nf-bg-base) 60%
  );
  font-family: var(--nf-font-family);
}

// ==========================================
// Animated Bubbles
// ==========================================
.ocean-ambient {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;
}

.bubble {
  position: absolute;
  bottom: -80px;
  border-radius: 50%;
  background: radial-gradient(circle at 35% 35%, rgba(56, 189, 248, 0.15), rgba(14, 165, 233, 0.04));
  border: 1px solid rgba(56, 189, 248, 0.12);
  animation: bubble-rise linear infinite;
  will-change: transform, opacity;
}

@for $i from 1 through 14 {
  .bubble:nth-child(#{$i}) {
    $size: (($i * 17) % 28 + 10) * 1px;
    $left: (($i * 43) % 90 + 5) * 1%;
    $duration: (($i * 11) % 12 + 8) * 1s;
    $delay: -(($i * 7) % 10) * 1s;
    width: $size;
    height: $size;
    left: $left;
    animation-duration: $duration;
    animation-delay: $delay;
  }
}

@keyframes bubble-rise {
  0%   { transform: translateY(0) translateX(0);   opacity: 0; }
  8%   { opacity: 0.55; }
  85%  { opacity: 0.2; }
  100% { transform: translateY(-100vh) translateX(12px); opacity: 0; }
}

// ==========================================
// Bottom Wave
// ==========================================
.page-waves {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 180px;
  pointer-events: none;
  z-index: 0;

  svg {
    width: 100%;
    height: 100%;
  }
}

// ==========================================
// Login Card
// ==========================================
.login-card {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 420px;
  background: var(--nf-bg-elevated);
  border: 1px solid var(--nf-border-base);
  border-radius: var(--nf-radius-xl);
  padding: 36px 40px 40px;
  box-shadow:
    var(--nf-shadow-xl),
    0 0 0 1px rgba(56, 189, 248, 0.06),
    inset 0 1px 0 rgba(56, 189, 248, 0.1);

  @media (max-width: 480px) {
    padding: 28px 24px 32px;
    border-radius: var(--nf-radius-lg);
  }
}

// ==========================================
// Brand Header
// ==========================================
.card-brand {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 24px;
}

.brand-logo {
  flex-shrink: 0;
  filter: drop-shadow(0 0 12px rgba(56, 189, 248, 0.28));
}

.brand-text {
  min-width: 0;
}

.brand-name {
  font-size: 26px;
  font-weight: 800;
  color: var(--nf-text-primary);
  margin: 0 0 3px;
  letter-spacing: -0.03em;
  line-height: 1;
}

.brand-tagline {
  font-size: 12px;
  color: var(--nf-text-secondary);
  margin: 0;
  letter-spacing: 0.01em;
}

// ==========================================
// Divider
// ==========================================
.card-divider {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;

  &::before,
  &::after {
    content: '';
    flex: 1;
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--nf-border-base));
  }

  &::after {
    background: linear-gradient(90deg, var(--nf-border-base), transparent);
  }
}

.divider-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--nf-text-placeholder);
  letter-spacing: 0.1em;
  text-transform: uppercase;
  white-space: nowrap;
}

// ==========================================
// Form
// ==========================================
.login-form {
  :deep(.el-form-item) {
    margin-bottom: 16px;
  }

  :deep(.el-form-item__error) {
    padding-top: 4px;
    font-size: 12px;
  }

  :deep(.el-input__wrapper) {
    border-radius: var(--nf-radius-base);
    box-shadow: 0 0 0 1px var(--nf-border-base);
    background: var(--nf-bg-container);
    transition: box-shadow 0.2s ease, background 0.2s ease;
    padding: 2px 12px;

    &:hover {
      box-shadow: 0 0 0 1px var(--nf-border-light);
    }

    &.is-focus {
      box-shadow: 0 0 0 2px var(--nf-primary), 0 0 14px rgba(56, 189, 248, 0.12);
      background: var(--nf-bg-container);
    }
  }

  :deep(.el-input__inner) {
    height: 42px;
    font-size: 14px;
    color: var(--nf-text-primary);

    &::placeholder { color: var(--nf-text-placeholder); }
  }
}

.input-icon {
  color: var(--nf-text-placeholder);
  font-size: 16px;
}

.form-options {
  margin: 2px 0 20px;

  :deep(.el-checkbox__label) {
    font-size: 13px;
    color: var(--nf-text-secondary);
  }

  :deep(.el-checkbox__input.is-checked + .el-checkbox__label) {
    color: var(--nf-primary);
  }
}

// ==========================================
// Security Alert
// ==========================================
.security-alert {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 11px 14px;
  border-radius: var(--nf-radius-base);
  margin-bottom: 16px;
  font-size: 13px;

  &.warning {
    background: rgba(230, 162, 60, 0.08);
    border: 1px solid rgba(230, 162, 60, 0.25);
    color: #d97706;
  }

  &.error {
    background: rgba(245, 108, 108, 0.08);
    border: 1px solid rgba(245, 108, 108, 0.25);
    color: #dc2626;
  }
}

.alert-icon {
  width: 15px;
  height: 15px;
  flex-shrink: 0;
  margin-top: 1px;
}

.alert-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
  line-height: 1.5;
}

.countdown {
  font-size: 12px;
  opacity: 0.75;
}

.alert-fade-enter-active,
.alert-fade-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}
.alert-fade-enter-from,
.alert-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

// ==========================================
// Login Button
// ==========================================
.login-btn {
  width: 100%;
  height: 44px;
  font-size: 15px;
  font-weight: 600;
  border-radius: var(--nf-radius-base);
  background: linear-gradient(135deg, #0EA5E9, #38BDF8 50%, #7DD3FC);
  border: none;
  color: #071524;
  letter-spacing: 0.08em;
  transition: opacity 0.2s, transform 0.15s, box-shadow 0.2s;
  box-shadow: 0 4px 16px rgba(56, 189, 248, 0.25);

  &:hover:not(:disabled) {
    opacity: 0.9;
    transform: translateY(-1px);
    box-shadow: 0 6px 24px rgba(56, 189, 248, 0.4);
  }

  &:active:not(:disabled) {
    transform: translateY(0);
    box-shadow: 0 2px 8px rgba(56, 189, 248, 0.2);
  }

  &:disabled {
    opacity: 0.45;
    cursor: not-allowed;
    box-shadow: none;
  }
}

// ==========================================
// Footer
// ==========================================
.page-footer {
  position: relative;
  z-index: 1;
  margin-top: 24px;
  font-size: 12px;
  color: var(--nf-text-placeholder);
}
</style>
