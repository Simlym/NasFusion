/**
 * 确认对话框组合函数
 */

import { ElMessageBox, ElMessage } from 'element-plus'

export interface ConfirmOptions {
  title?: string
  message: string
  type?: 'warning' | 'info' | 'success' | 'error'
  confirmButtonText?: string
  cancelButtonText?: string
  showCancelButton?: boolean
}

export function useConfirm() {
  // 确认操作
  async function confirm(options: ConfirmOptions | string): Promise<boolean> {
    const config: ConfirmOptions = typeof options === 'string' ? { message: options } : options

    const {
      title = '提示',
      message,
      type = 'warning',
      confirmButtonText = '确定',
      cancelButtonText = '取消',
      showCancelButton = true
    } = config

    try {
      await ElMessageBox.confirm(message, title, {
        confirmButtonText,
        cancelButtonText,
        type,
        showCancelButton
      })
      return true
    } catch {
      return false
    }
  }

  // 删除确认
  async function confirmDelete(itemName?: string): Promise<boolean> {
    const message = itemName ? `确定要删除 "${itemName}" 吗？` : '确定要删除吗？'

    return confirm({
      title: '删除确认',
      message: `${message} 此操作不可恢复。`,
      type: 'warning'
    })
  }

  // 危险操作确认
  async function confirmDanger(message: string): Promise<boolean> {
    return confirm({
      title: '危险操作',
      message,
      type: 'error'
    })
  }

  // 信息提示
  async function alert(message: string, title = '提示'): Promise<void> {
    await ElMessageBox.alert(message, title, {
      confirmButtonText: '确定'
    })
  }

  // 输入提示
  async function prompt(
    message: string,
    title = '请输入',
    defaultValue = ''
  ): Promise<string | null> {
    try {
      const { value } = await ElMessageBox.prompt(message, title, {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        inputValue: defaultValue
      })
      return value
    } catch {
      return null
    }
  }

  // 成功消息
  function success(message: string) {
    ElMessage.success(message)
  }

  // 错误消息
  function error(message: string) {
    ElMessage.error(message)
  }

  // 警告消息
  function warning(message: string) {
    ElMessage.warning(message)
  }

  // 信息消息
  function info(message: string) {
    ElMessage.info(message)
  }

  return {
    confirm,
    confirmDelete,
    confirmDanger,
    alert,
    prompt,
    success,
    error,
    warning,
    info
  }
}
