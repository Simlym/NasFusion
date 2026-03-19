<template>
  <div class="notification-manager">
    <!-- 导航提示 -->
    <el-alert
      :closable="false"
      type="info"
      style="margin-bottom: 20px"
    >
      <template #default>
        想要查看收到的消息？
        <el-link
          type="primary"
          underline="never"
          style="margin-left: 8px"
          @click="router.push('/notifications')"
        >
          前往消息中心 →
        </el-link>
      </template>
    </el-alert>

    <!-- Tab 切换 -->
    <el-tabs v-model="activeTab" class="notification-tabs">
      <!-- Section 1: 全局通知设置 -->
      <el-tab-pane label="全局设置" name="global">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>全局通知设置</span>
              <el-button type="primary" :loading="savingSettings" @click="saveGlobalSettings">
                保存设置
              </el-button>
            </div>
          </template>

          <el-form v-loading="settingsLoading" :model="globalSettings" label-width="180px">
            <div class="global-settings-grid">
              <!-- 基础设置 -->
              <div class="global-settings-section">
                <h4>基础设置</h4>
                <el-form-item label="启用系统内消息">
                  <el-switch v-model="globalSettings.enableInternalMessages" />
                  <div class="form-item-tips">站内消息显示在消息中心</div>
                </el-form-item>

                <el-form-item label="启用站外消息">
                  <el-switch v-model="globalSettings.enableExternalMessages" />
                  <div class="form-item-tips">通过 Telegram/Email/Webhook 发送消息</div>
                </el-form-item>

                <el-form-item label="默认语言">
                  <el-select v-model="globalSettings.defaultLanguage" style="width: 200px">
                    <el-option label="简体中文" value="zh-CN" />
                    <el-option label="English" value="en-US" />
                  </el-select>
                </el-form-item>
              </div>

              <!-- 消息管理 -->
              <div class="global-settings-section">
                <h4>消息管理</h4>
                <el-form-item label="消息保留天数">
                  <el-input-number v-model="globalSettings.retentionDays" :min="1" :max="365" />
                  <span class="hint-text">超过此天数的已读消息将自动清理</span>
                </el-form-item>

                <el-form-item label="启用去重">
                  <el-switch v-model="globalSettings.enableDeduplication" />
                  <div class="form-item-tips">相同消息在去重窗口内只发送一次</div>
                </el-form-item>

                <el-form-item v-if="globalSettings.enableDeduplication" label="去重窗口（分钟）">
                  <el-input-number v-model="globalSettings.deduplicationWindow" :min="1" :max="1440" />
                </el-form-item>
              </div>

              <!-- 发送配置 -->
              <div class="global-settings-section">
                <h4>发送配置</h4>
                <el-form-item label="最大重试次数">
                  <el-input-number v-model="globalSettings.maxRetries" :min="0" :max="10" />
                  <div class="form-item-tips">站外消息发送失败时的最大重试次数</div>
                </el-form-item>

                <el-form-item label="重试间隔（秒）">
                  <el-input-number v-model="globalSettings.retryDelay" :min="1" :max="3600" />
                </el-form-item>
              </div>
            </div>
          </el-form>
        </el-card>
      </el-tab-pane>

      <!-- Section 2: 通知渠道管理 -->
      <el-tab-pane label="通知渠道" name="channels">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>已配置渠道</span>
              <el-button type="primary" :icon="Plus" @click="showChannelDialog()">
                添加渠道
              </el-button>
            </div>
          </template>

          <!-- 渠道列表 -->
          <el-row v-loading="channelsLoading" :gutter="16">
            <el-col v-for="channel in channels" :key="channel.id" :span="8">
              <el-card shadow="hover" class="channel-card">
                <div class="channel-header">
                  <el-icon :size="24" :color="getChannelColor(channel.channelType)">
                    <Message />
                  </el-icon>
                  <div class="channel-info">
                    <h4>{{ channel.name }}</h4>
                    <p>{{ getChannelTypeName(channel.channelType) }}</p>
                  </div>
                  <el-switch
                    v-model="channel.enabled"
                    @change="toggleChannel(channel)"
                  />
                </div>
                <div class="channel-body">
                  <el-tag v-if="channel.status === 'healthy'" type="success" size="small">
                    健康
                  </el-tag>
                  <el-tag v-else-if="channel.status === 'error'" type="danger" size="small">
                    错误
                  </el-tag>
                  <el-tag v-else type="info" size="small">
                    未测试
                  </el-tag>
                  <span v-if="channel.lastTestAt" class="channel-test-time">
                    上次测试: {{ formatDateTime(channel.lastTestAt) }}
                  </span>
                </div>
                <div class="channel-actions">
                  <el-button size="small" :icon="Refresh" @click="testChannel(channel)">
                    测试连接
                  </el-button>
                  <el-button size="small" :icon="Edit" @click="showChannelDialog(channel)">
                    编辑
                  </el-button>
                  <el-button size="small" type="danger" :icon="Delete" @click="deleteChannel(channel)">
                    删除
                  </el-button>
                </div>
              </el-card>
            </el-col>
          </el-row>

          <!-- 空状态 -->
          <el-empty v-if="channels.length === 0 && !channelsLoading" description="暂未配置通知渠道">
            <el-button type="primary" @click="showChannelDialog()">立即添加</el-button>
          </el-empty>
        </el-card>
      </el-tab-pane>

      <!-- Section 3: 通知规则管理 -->
      <el-tab-pane label="通知规则" name="rules">
        <el-alert
          :closable="false"
          type="info"
          style="margin-bottom: 20px"
        >
          <template #default>
            想要更详细地配置规则？
            <el-link
              type="primary"
              underline="never"
              style="margin-left: 8px"
              @click="router.push('/notifications/rules')"
            >
              前往规则管理页面 →
            </el-link>
          </template>
        </el-alert>

        <el-card>
          <template #header>
            <div class="card-header">
              <span>通知规则配置</span>
              <el-button type="primary" :icon="Plus" @click="showRuleDialog()">
                创建规则
              </el-button>
            </div>
          </template>

          <!-- 规则列表 -->
          <el-table v-loading="rulesLoading" :data="rules" style="width: 100%">
            <el-table-column prop="name" label="规则名称" min-width="200" />
            <el-table-column prop="eventType" label="事件类型" width="150">
              <template #default="{ row }">
                <el-tag size="small">{{ getEventTypeName(row.eventType) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="发送渠道" width="180">
              <template #default="{ row }">
                <el-tag v-for="cid in row.channelIds" :key="cid" size="small" style="margin-right: 4px">
                  {{ getChannelName(cid) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="enabled" label="状态" width="100">
              <template #default="{ row }">
                <el-switch v-model="row.enabled" @change="toggleRule(row)" />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="140" fixed="right">
              <template #default="{ row }">
                <el-button link type="warning" size="small" @click="showRuleDialog(row)">
                  编辑
                </el-button>
                <el-button link type="danger" size="small" @click="deleteRule(row)">
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-empty v-if="rules.length === 0 && !rulesLoading" description="暂无通知规则">
            <el-button type="primary" @click="showRuleDialog()">创建第一条规则</el-button>
          </el-empty>
        </el-card>
      </el-tab-pane>

      <!-- Section 4: 通知模板管理 -->
      <el-tab-pane label="通知模板" name="templates">
        <el-alert
          :closable="false"
          type="info"
          style="margin-bottom: 20px"
        >
          <template #default>
            想要更详细地配置模板？
            <el-link
              type="primary"
              underline="never"
              style="margin-left: 8px"
              @click="router.push('/notifications/templates')"
            >
              前往模板管理页面 →
            </el-link>
          </template>
        </el-alert>

        <el-card>
          <template #header>
            <div class="card-header">
              <span>通知模板</span>
              <el-button type="primary" :icon="Plus" @click="showTemplateDialog()">
                创建模板
              </el-button>
            </div>
          </template>

          <!-- 模板列表 -->
          <el-table v-loading="templatesLoading" :data="templates" style="width: 100%">
            <el-table-column prop="name" label="模板名称" min-width="200" />
            <el-table-column prop="eventType" label="事件类型" width="180">
              <template #default="{ row }">
                <el-tag>{{ getEventTypeName(row.eventType) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="language" label="语言" width="120">
              <template #default="{ row }">
                <el-tag type="info" size="small">{{ row.language === 'zh-CN' ? '简体中文' : 'English' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="类型" width="120">
              <template #default="{ row }">
                <el-tag :type="(row.isSystem || row.is_system) ? 'success' : 'primary'" size="small">
                  {{ (row.isSystem || row.is_system) ? '系统模板' : '自定义' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="updatedAt" label="更新时间" width="180">
              <template #default="{ row }">
                {{ formatDateTime(row.updatedAt) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="160" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="viewTemplate(row)">
                  查看
                </el-button>
                <el-button link type="success" size="small" @click="previewTemplate(row)">
                  预览
                </el-button>
                <el-dropdown @command="(cmd) => handleTemplateCommand(cmd, row)">
                  <el-button link type="info" size="small">
                    更多<el-icon class="el-icon--right"><ArrowDown /></el-icon>
                  </el-button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item
                        v-if="!(row.isSystem || row.is_system)"
                        command="edit"
                        icon="Edit"
                      >
                        编辑
                      </el-dropdown-item>
                      <el-dropdown-item
                        v-if="!(row.isSystem || row.is_system)"
                        command="delete"
                        icon="Delete"
                        divided
                      >
                        删除
                      </el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </template>
            </el-table-column>
          </el-table>

          <el-empty
            v-if="templates.length === 0 && !templatesLoading"
            description="暂无通知模板"
          >
            <el-button type="primary" @click="showTemplateDialog()">创建第一个模板</el-button>
          </el-empty>
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <!-- 规则配置对话框 -->
    <el-dialog
      v-model="ruleDialogVisible"
      :title="isEditMode ? '编辑规则' : '创建规则'"
      width="800px"
      @close="resetRuleForm"
    >
      <el-form
        ref="ruleFormRef"
        :model="ruleForm"
        :rules="ruleFormRules"
        label-width="120px"
      >
        <!-- 基本信息 -->
        <el-divider content-position="left">基本信息</el-divider>
        <el-form-item label="规则名称" prop="name">
          <el-input v-model="ruleForm.name" placeholder="请输入规则名称" />
        </el-form-item>
        <el-form-item label="事件类型" prop="eventType">
          <el-select
            v-model="ruleForm.eventType"
            placeholder="请选择事件类型"
            style="width: 100%"
            filterable
          >
            <el-option-group
              v-for="group in eventTypeGroups"
              :key="group.label"
              :label="group.label"
            >
              <el-option
                v-for="event in group.options"
                :key="event.value"
                :label="event.label"
                :value="event.value"
              >
                <div style="display: flex; justify-content: space-between">
                  <span>{{ event.label }}</span>
                  <span class="option-desc">{{ event.description }}</span>
                </div>
              </el-option>
            </el-option-group>
          </el-select>
        </el-form-item>
        <el-form-item label="启用规则" prop="enabled">
          <el-switch v-model="ruleForm.enabled" />
        </el-form-item>
        <el-form-item label="优先级" prop="priority">
          <el-select v-model="ruleForm.priority" placeholder="请选择优先级" style="width: 100%">
            <el-option label="低" value="low" />
            <el-option label="普通" value="medium" />
            <el-option label="高" value="high" />
            <el-option label="紧急" value="urgent" />
          </el-select>
        </el-form-item>

        <!-- 通知渠道 -->
        <el-divider content-position="left">通知渠道</el-divider>
        <el-form-item label="发送站内信">
          <el-switch v-model="ruleForm.sendInApp" />
        </el-form-item>
        <el-form-item label="外部渠道" prop="channelIds">
          <el-select
            v-model="ruleForm.channelIds"
            multiple
            placeholder="请选择通知渠道"
            style="width: 100%"
          >
            <el-option
              v-for="channel in channels"
              :key="channel.id"
              :label="channel.name"
              :value="channel.id"
              :disabled="!channel.enabled"
            >
              <div style="display: flex; justify-content: space-between; align-items: center">
                <span>
                  <el-tag :type="getChannelTagType(channel.channelType)" size="small" style="margin-right: 8px">
                    {{ getChannelTypeName(channel.channelType) }}
                  </el-tag>
                  {{ channel.name }}
                </span>
                <el-tag v-if="!channel.enabled" type="danger" size="small">已禁用</el-tag>
              </div>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="通知模板">
          <el-select
            v-model="ruleForm.templateId"
            placeholder="使用默认模板"
            clearable
            style="width: 100%"
          >
            <el-option
              v-for="template in templates"
              :key="template.id"
              :label="template.name"
              :value="template.id"
            />
          </el-select>
        </el-form-item>

        <!-- 触发条件 -->
        <el-divider content-position="left">触发条件（可选）</el-divider>
        <el-form-item label="过滤条件">
          <el-button
            size="small"
            icon="Plus"
            style="margin-bottom: 10px"
            @click="addCondition"
          >
            添加条件
          </el-button>
          <div v-for="(condition, index) in conditions" :key="index" class="condition-item">
            <el-select
              v-model="condition.field"
              placeholder="字段"
              style="width: 150px; margin-right: 10px"
            >
              <el-option label="文件大小(GB)" value="size_gb" />
              <el-option label="质量" value="quality" />
              <el-option label="促销类型" value="promotion_type" />
              <el-option label="站点名称" value="site_name" />
              <el-option label="媒体类型" value="media_type" />
            </el-select>
            <el-select
              v-model="condition.operator"
              placeholder="运算符"
              style="width: 120px; margin-right: 10px"
            >
              <el-option label="等于" value="eq" />
              <el-option label="不等于" value="ne" />
              <el-option label="大于" value="gt" />
              <el-option label="小于" value="lt" />
              <el-option label="大于等于" value="gte" />
              <el-option label="小于等于" value="lte" />
              <el-option label="包含" value="contains" />
              <el-option label="在列表中" value="in" />
            </el-select>
            <el-input
              v-model="condition.value"
              placeholder="值"
              style="width: 200px; margin-right: 10px"
            />
            <el-button
              icon="Delete"
              type="danger"
              size="small"
              @click="removeCondition(index)"
            />
          </div>
          <el-alert
            v-if="conditions.length === 0"
            title="无条件限制，所有事件都会触发通知"
            type="info"
            :closable="false"
            show-icon
          />
        </el-form-item>

        <!-- 高级设置 -->
        <el-divider content-position="left">高级设置</el-divider>
        <el-form-item label="静默时段">
          <el-switch v-model="silentHoursEnabled" />
        </el-form-item>
        <el-form-item v-if="silentHoursEnabled" label="时段设置">
          <el-button
            size="small"
            icon="Plus"
            style="margin-bottom: 10px"
            @click="addSilentPeriod"
          >
            添加时段
          </el-button>
          <div v-for="(period, index) in silentPeriods" :key="index" class="silent-period-item">
            <el-select
              v-model="period.days"
              multiple
              placeholder="选择星期（空表示每天）"
              style="width: 200px; margin-right: 10px"
            >
              <el-option label="周一" value="monday" />
              <el-option label="周二" value="tuesday" />
              <el-option label="周三" value="wednesday" />
              <el-option label="周四" value="thursday" />
              <el-option label="周五" value="friday" />
              <el-option label="周六" value="saturday" />
              <el-option label="周日" value="sunday" />
            </el-select>
            <el-time-picker
              v-model="period.start"
              placeholder="开始时间"
              format="HH:mm"
              value-format="HH:mm"
              style="width: 150px; margin-right: 10px"
            />
            <el-time-picker
              v-model="period.end"
              placeholder="结束时间"
              format="HH:mm"
              value-format="HH:mm"
              style="width: 150px; margin-right: 10px"
            />
            <el-button
              icon="Delete"
              type="danger"
              size="small"
              @click="removeSilentPeriod(index)"
            />
          </div>
        </el-form-item>
        <el-form-item label="去重窗口">
          <el-input-number
            v-model="ruleForm.deduplicationWindow"
            :min="0"
            :max="86400"
            :step="60"
            placeholder="秒"
            style="width: 200px"
          />
          <span class="hint-text">
            在此时间内相同事件不会重复通知（0表示不去重）
          </span>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="ruleDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="ruleSaving" @click="saveRule">保存</el-button>
      </template>
    </el-dialog>

    <!-- 模板配置对话框 -->
    <el-dialog
      v-model="templateDialogVisible"
      :title="isTemplateEditMode ? '编辑模板' : isTemplateViewMode ? '查看模板' : '创建模板'"
      width="900px"
      @close="resetTemplateForm"
    >
      <el-form
        ref="templateFormRef"
        :model="templateForm"
        :rules="templateFormRules"
        label-width="120px"
        :disabled="isTemplateViewMode"
      >
        <!-- 基本信息 -->
        <el-divider content-position="left">基本信息</el-divider>
        <el-form-item label="模板名称" prop="name">
          <el-input v-model="templateForm.name" placeholder="请输入模板名称" />
        </el-form-item>
        <el-form-item label="事件类型" prop="eventType">
          <el-select
            v-model="templateForm.eventType"
            placeholder="请选择事件类型"
            style="width: 100%"
            @change="onTemplateEventTypeChange"
          >
            <el-option-group
              v-for="group in eventTypeGroups"
              :key="group.label"
              :label="group.label"
            >
              <el-option
                v-for="event in group.options"
                :key="event.value"
                :label="event.label"
                :value="event.value"
              >
                <div style="display: flex; justify-content: space-between">
                  <span>{{ event.label }}</span>
                  <span class="option-desc">{{ event.description }}</span>
                </div>
              </el-option>
            </el-option-group>
          </el-select>
        </el-form-item>
        <el-form-item label="语言" prop="language">
          <el-select v-model="templateForm.language" placeholder="请选择语言" style="width: 100%">
            <el-option label="简体中文" value="zh-CN" />
            <el-option label="English" value="en-US" />
          </el-select>
        </el-form-item>
        <el-form-item label="格式" prop="format">
          <el-select v-model="templateForm.format" placeholder="请选择格式" style="width: 100%">
            <el-option label="纯文本" value="text" />
            <el-option label="Markdown" value="markdown" />
            <el-option label="HTML" value="html" />
          </el-select>
        </el-form-item>

        <!-- 可用变量提示 -->
        <el-alert
          v-if="availableTemplateVariables.length > 0"
          :title="`可用变量: ${availableTemplateVariables.join(', ')}`"
          type="info"
          :closable="false"
          style="margin-bottom: 20px"
        >
          <template #default>
            <p style="margin: 5px 0">在模板中使用变量格式: &#123;&#123; variable_name &#125;&#125;</p>
            <p style="margin: 5px 0; font-size: 12px; color: #666">
              例如: &#123;&#123; media_name &#125;&#125;, &#123;&#123; quality &#125;&#125;, &#123;&#123; size_gb &#125;&#125;
            </p>
          </template>
        </el-alert>

        <!-- 模板内容 -->
        <el-divider content-position="left">模板内容</el-divider>
        <el-form-item label="标题模板" prop="titleTemplate">
          <el-input
            v-model="templateForm.titleTemplate"
            placeholder="例如: 【订阅匹配】{{ media_name }}"
          />
        </el-form-item>
        <el-form-item label="内容模板" prop="contentTemplate">
          <el-input
            v-model="templateForm.contentTemplate"
            type="textarea"
            :rows="8"
            placeholder="输入模板内容，使用 {{ variable }} 引用变量"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="templateDialogVisible = false">
          {{ isTemplateViewMode ? '关闭' : '取消' }}
        </el-button>
        <el-button v-if="!isTemplateViewMode" type="primary" :loading="templateSaving" @click="saveTemplate">
          保存
        </el-button>
      </template>
    </el-dialog>

    <!-- 模板预览对话框 -->
    <el-dialog v-model="previewDialogVisible" title="模板预览" width="700px">
      <el-alert
        title="输入测试数据预览渲染效果"
        type="info"
        :closable="false"
        style="margin-bottom: 20px"
      />

      <el-form label-width="120px">
        <el-form-item label="模板名称">
          <el-tag>{{ currentPreviewTemplate?.name }}</el-tag>
        </el-form-item>
        <el-form-item label="测试数据">
          <el-input
            v-model="previewVariables"
            type="textarea"
            :rows="6"
            placeholder='输入 JSON 格式的变量数据，例如: {"media_name": "复仇者联盟", "quality": "1080p"}'
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="rendering" @click="renderPreview">渲染预览</el-button>
        </el-form-item>
      </el-form>

      <!-- 渲染结果 -->
      <el-card v-if="renderResult" class="preview-result" shadow="never">
        <template #header>
          <div style="display: flex; justify-content: space-between; align-items: center">
            <span>渲染结果</span>
            <el-tag type="success">{{ currentPreviewTemplate?.format }}</el-tag>
          </div>
        </template>
        <div class="preview-content">
          <div class="preview-item">
            <div class="preview-label">标题:</div>
            <div class="preview-value">{{ renderResult.title }}</div>
          </div>
          <el-divider />
          <div class="preview-item">
            <div class="preview-label">内容:</div>
            <div
              class="preview-value"
              v-html="formatPreviewContent(renderResult.content)"
            ></div>
          </div>
        </div>
      </el-card>
    </el-dialog>

    <!-- 渠道配置对话框 -->
    <el-dialog
      v-model="channelDialogVisible"
      :title="channelFormMode === 'create' ? '添加通知渠道' : '编辑通知渠道'"
      width="600px"
    >
      <el-form
        ref="channelFormRef"
        :model="channelForm"
        :rules="channelFormRules"
        label-width="100px"
      >
        <el-form-item label="渠道名称" prop="name">
          <el-input v-model="channelForm.name" placeholder="请输入渠道名称" />
        </el-form-item>
        <el-form-item label="渠道类型" prop="channel_type">
          <el-select
            v-model="channelForm.channel_type"
            placeholder="请选择渠道类型"
            :disabled="channelFormMode === 'edit'"
            @change="handleChannelTypeChange"
          >
            <el-option label="Telegram" value="telegram" />
            <el-option label="邮件" value="email" />
            <el-option label="Webhook" value="webhook" />
          </el-select>
        </el-form-item>

        <!-- Telegram 配置 -->
        <template v-if="channelForm.channel_type === 'telegram'">
          <el-form-item label="Bot Token" prop="config.bot_token">
            <el-input
              v-model="channelForm.config.bot_token"
              placeholder="请输入 Telegram Bot Token"
              show-password
            />
          </el-form-item>
          <el-form-item label="Chat ID" prop="config.chat_id">
            <el-input v-model="channelForm.config.chat_id" placeholder="请输入 Chat ID" />
          </el-form-item>
        </template>

        <!-- Email 配置 -->
        <template v-if="channelForm.channel_type === 'email'">
          <el-form-item label="SMTP 主机" prop="config.smtp_host">
            <el-input v-model="channelForm.config.smtp_host" placeholder="smtp.example.com" />
          </el-form-item>
          <el-form-item label="SMTP 端口" prop="config.smtp_port">
            <el-input-number v-model="channelForm.config.smtp_port" :min="1" :max="65535" />
          </el-form-item>
          <el-form-item label="用户名" prop="config.smtp_user">
            <el-input v-model="channelForm.config.smtp_user" placeholder="user@example.com" />
          </el-form-item>
          <el-form-item label="密码" prop="config.smtp_password">
            <el-input v-model="channelForm.config.smtp_password" type="password" show-password />
          </el-form-item>
          <el-form-item label="收件人" prop="config.to_email">
            <el-input v-model="channelForm.config.to_email" placeholder="recipient@example.com" />
          </el-form-item>
          <el-form-item label="使用 TLS">
            <el-switch v-model="channelForm.config.use_tls" />
          </el-form-item>
        </template>

        <!-- Webhook 配置 -->
        <template v-if="channelForm.channel_type === 'webhook'">
          <el-form-item label="Webhook URL" prop="config.url">
            <el-input v-model="channelForm.config.url" placeholder="https://example.com/webhook" />
          </el-form-item>
          <el-form-item label="请求方法">
            <el-select v-model="channelForm.config.method">
              <el-option label="POST" value="POST" />
              <el-option label="PUT" value="PUT" />
            </el-select>
          </el-form-item>
        </template>

        <el-form-item label="启用">
          <el-switch v-model="channelForm.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="channelDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="channelSaving" @click="saveChannel">
          保存
        </el-button>
      </template>
    </el-dialog>

  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import {
  Plus,
  View,
  Delete,
  Edit,
  Refresh,
  Message,
  ArrowDown
} from '@element-plus/icons-vue'
import type { NotificationChannel, NotificationRule, NotificationTemplate } from '@/types'
import {
  getNotificationChannelList,
  createNotificationChannel,
  updateNotificationChannel,
  deleteNotificationChannel,
  testNotificationChannel,
  getNotificationRuleList,
  createNotificationRule,
  updateNotificationRule,
  deleteNotificationRule,
  toggleNotificationRule,
  getNotificationTemplateList,
  createNotificationTemplate,
  updateNotificationTemplate,
  deleteNotificationTemplate
} from '@/api/modules/notification'
import { getSettings, upsertSetting } from '@/api/modules/settings'
import { formatDateTime } from '@/utils'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

// Tab 状态
const activeTab = ref('global')

// 事件类型分组定义
const eventTypeGroups = [
  {
    label: '📺 订阅相关',
    options: [
      { value: 'subscription_matched', label: '订阅匹配', description: '订阅资源匹配成功时' },
      { value: 'subscription_downloaded', label: '订阅下载', description: '订阅资源下载完成时' },
      { value: 'subscription_completed', label: '订阅完成', description: '订阅全部完成时' },
      { value: 'subscription_no_resource', label: '订阅无资源', description: '订阅没有可用资源时' }
    ]
  },
  {
    label: '⬇️ 下载相关',
    options: [
      { value: 'download_started', label: '下载开始', description: '下载任务开始时' },
      { value: 'download_completed', label: '下载完成', description: '下载任务完成时' },
      { value: 'download_failed', label: '下载失败', description: '下载任务失败时' },
      { value: 'download_paused', label: '下载暂停', description: '下载任务暂停时' }
    ]
  },
  {
    label: '🎯 资源相关',
    options: [
      { value: 'resource_free_promotion', label: '免费促销', description: '发现免费促销资源时' },
      { value: 'resource_2x_promotion', label: '2倍促销', description: '发现2倍促销资源时' },
      { value: 'resource_high_quality', label: '高质量资源', description: '发现高质量资源时' }
    ]
  },
  {
    label: '🌐 PT站点相关',
    options: [
      { value: 'site_connection_failed', label: '站点连接失败', description: 'PT站点连接失败时' },
      { value: 'site_auth_expired', label: '站点认证过期', description: 'PT站点认证过期时' },
      { value: 'site_sync_completed', label: '站点同步完成', description: 'PT站点资源同步完成时' }
    ]
  },
  {
    label: '📁 媒体文件相关',
    options: [
      { value: 'media_scan_completed', label: '媒体扫描完成', description: '媒体文件扫描完成时' },
      { value: 'media_organized', label: '媒体整理完成', description: '媒体文件整理完成时' },
      { value: 'media_metadata_scraped', label: '媒体元数据刮削', description: '媒体元数据刮削完成时' }
    ]
  },
  {
    label: '⚙️ 任务相关',
    options: [
      { value: 'task_failed', label: '任务失败', description: '后台任务执行失败时' },
      { value: 'task_completed', label: '任务完成', description: '后台任务执行完成时' }
    ]
  },
  {
    label: '🖥️ 系统相关',
    options: [
      { value: 'system_error', label: '系统错误', description: '系统发生错误时' },
      { value: 'disk_space_low', label: '磁盘空间不足', description: '磁盘空间不足时' },
      { value: 'user_login_anomaly', label: '用户登录异常', description: '检测到异常登录时' },
      { value: 'system_update_available', label: '系统更新可用', description: '有新版本可用时' }
    ]
  }
]

// 扁平化的事件类型列表，用于查找
const eventTypes = eventTypeGroups.flatMap(group => group.options)

// 事件类型变量映射
const eventVariablesMap: Record<string, string[]> = {
  // 订阅相关
  'subscription_matched': [
    'media_name',
    'quality',
    'size_gb',
    'site_name',
    'promotion_type',
    'seeders',
    'leechers'
  ],
  'subscription_downloaded': ['media_name', 'size_gb', 'site_name', 'save_path'],
  'subscription_completed': ['media_name', 'total_episodes', 'downloaded_episodes', 'duration'],
  'subscription_no_resource': ['media_name', 'subscription_id', 'last_check_at'],

  // 下载相关
  'download_started': ['media_name', 'size_gb', 'torrent_hash', 'site_name'],
  'download_completed': ['media_name', 'size_gb', 'save_path', 'duration', 'ratio'],
  'download_failed': ['media_name', 'error_message', 'torrent_hash', 'retry_count'],
  'download_paused': ['media_name', 'progress', 'reason'],

  // 资源相关
  'resource_free_promotion': ['media_name', 'site_name', 'size_gb', 'promotion_end_at'],
  'resource_2x_promotion': ['media_name', 'site_name', 'size_gb', 'promotion_end_at'],
  'resource_high_quality': ['media_name', 'site_name', 'quality', 'size_gb', 'seeders'],

  // PT站点相关
  'site_connection_failed': ['site_name', 'error_message', 'last_success_at'],
  'site_auth_expired': ['site_name', 'expired_at'],
  'site_sync_completed': ['site_name', 'resources_count', 'duration'],

  // 媒体文件相关
  'media_scan_completed': ['directory', 'files_found', 'duration'],
  'media_organized': ['media_name', 'source_path', 'target_path', 'media_type'],
  'media_metadata_scraped': ['media_name', 'tmdb_id', 'source'],

  // 任务相关
  'task_failed': ['task_name', 'error_message', 'task_type'],
  'task_completed': ['task_name', 'duration', 'result'],

  // 系统相关
  'system_error': ['error_type', 'error_message', 'timestamp', 'module'],
  'disk_space_low': ['disk_path', 'available_gb', 'total_gb', 'usage_percent'],
  'user_login_anomaly': ['username', 'ip_address', 'login_at', 'reason'],
  'system_update_available': ['current_version', 'new_version', 'release_notes']
}

// ==================== 全局通知设置 ====================
const settingsLoading = ref(false)
const savingSettings = ref(false)
const globalSettings = reactive({
  enableInternalMessages: true,
  enableExternalMessages: true,
  defaultLanguage: 'zh-CN',
  retentionDays: 30,
  maxRetries: 3,
  retryDelay: 60,
  enableDeduplication: true,
  deduplicationWindow: 10
})

// 加载全局设置
const loadGlobalSettings = async () => {
  settingsLoading.value = true
  try {
    const res = await getSettings('notification')
    if (res.data && res.data.data) {
      const settings = res.data.data.items || []

      // 解析配置项
      settings.forEach((setting: any) => {
        switch (setting.key) {
          case 'notification.enable_internal_messages':
            globalSettings.enableInternalMessages = setting.value === 'true'
            break
          case 'notification.enable_external_messages':
            globalSettings.enableExternalMessages = setting.value === 'true'
            break
          case 'notification.default_language':
            globalSettings.defaultLanguage = setting.value || 'zh-CN'
            break
          case 'notification.retention_days':
            globalSettings.retentionDays = parseInt(setting.value) || 30
            break
          case 'notification.max_retries':
            globalSettings.maxRetries = parseInt(setting.value) || 3
            break
          case 'notification.retry_delay':
            globalSettings.retryDelay = parseInt(setting.value) || 60
            break
          case 'notification.enable_deduplication':
            globalSettings.enableDeduplication = setting.value === 'true'
            break
          case 'notification.deduplication_window':
            globalSettings.deduplicationWindow = parseInt(setting.value) || 10
            break
        }
      })
    }
  } catch (error) {
    console.error('加载全局设置失败:', error)
  } finally {
    settingsLoading.value = false
  }
}

// 保存全局设置
const saveGlobalSettings = async () => {
  savingSettings.value = true
  try {
    await upsertSetting('notification', 'notification.enable_internal_messages', String(globalSettings.enableInternalMessages))
    await upsertSetting('notification', 'notification.enable_external_messages', String(globalSettings.enableExternalMessages))
    await upsertSetting('notification', 'notification.default_language', globalSettings.defaultLanguage)
    await upsertSetting('notification', 'notification.retention_days', String(globalSettings.retentionDays))
    await upsertSetting('notification', 'notification.max_retries', String(globalSettings.maxRetries))
    await upsertSetting('notification', 'notification.retry_delay', String(globalSettings.retryDelay))
    await upsertSetting('notification', 'notification.enable_deduplication', String(globalSettings.enableDeduplication))
    await upsertSetting('notification', 'notification.deduplication_window', String(globalSettings.deduplicationWindow))

    ElMessage.success('全局设置已保存')
  } catch (error) {
    console.error('保存全局设置失败:', error)
    ElMessage.error('保存失败')
  } finally {
    savingSettings.value = false
  }
}

// ==================== 通知渠道 ====================
const channelsLoading = ref(false)
const channels = ref<NotificationChannel[]>([])

const channelDialogVisible = ref(false)
const channelFormMode = ref<'create' | 'edit'>('create')
const channelFormRef = ref<FormInstance>()
const channelForm = reactive<any>({
  id: null,
  name: '',
  channel_type: '',
  enabled: true,
  config: {}
})
const channelSaving = ref(false)

const channelFormRules: FormRules = {
  name: [{ required: true, message: '请输入渠道名称', trigger: 'blur' }],
  channel_type: [{ required: true, message: '请选择渠道类型', trigger: 'change' }]
}

// 加载渠道列表
const loadChannels = async () => {
  channelsLoading.value = true
  try {
    const res = await getNotificationChannelList()
    if (res.data) {
      channels.value = res.data.items || []
    }
  } catch (error) {
    ElMessage.error('加载渠道列表失败')
  } finally {
    channelsLoading.value = false
  }
}

// 显示渠道对话框
const showChannelDialog = (channel?: NotificationChannel) => {
  channelFormMode.value = channel ? 'edit' : 'create'
  if (channel) {
    Object.assign(channelForm, {
      id: channel.id,
      name: channel.name,
      channel_type: channel.channelType,
      enabled: channel.enabled,
      config: { ...channel.config }
    })
  } else {
    Object.assign(channelForm, {
      id: null,
      name: '',
      channel_type: '',
      enabled: true,
      config: {}
    })
  }
  channelDialogVisible.value = true
}

// 渠道类型改变
const handleChannelTypeChange = (type: string) => {
  channelForm.config = {}
  if (type === 'telegram') {
    channelForm.config = { bot_token: '', chat_id: '' }
  } else if (type === 'email') {
    channelForm.config = {
      smtp_host: '',
      smtp_port: 587,
      smtp_user: '',
      smtp_password: '',
      to_email: '',
      use_tls: true
    }
  } else if (type === 'webhook') {
    channelForm.config = { url: '', method: 'POST' }
  }
}

// 保存渠道
const saveChannel = async () => {
  if (!channelFormRef.value) return

  await channelFormRef.value.validate(async (valid) => {
    if (!valid) return

    channelSaving.value = true
    try {
      const data = {
        name: channelForm.name,
        channel_type: channelForm.channel_type,
        enabled: channelForm.enabled,
        config: channelForm.config
      }

      if (channelFormMode.value === 'create') {
        await createNotificationChannel(data)
        ElMessage.success('创建成功')
      } else {
        await updateNotificationChannel(channelForm.id, data)
        ElMessage.success('更新成功')
      }

      channelDialogVisible.value = false
      await loadChannels()
    } catch (error) {
      ElMessage.error('保存失败')
    } finally {
      channelSaving.value = false
    }
  })
}

// 切换渠道状态
const toggleChannel = async (channel: NotificationChannel) => {
  try {
    await updateNotificationChannel(channel.id, { enabled: channel.enabled })
    ElMessage.success('状态已更新')
  } catch (error) {
    ElMessage.error('更新失败')
    channel.enabled = !channel.enabled
  }
}

// 测试渠道
const testChannel = async (channel: NotificationChannel) => {
  try {
    const res = await testNotificationChannel(channel.id)
    if (res.data.success) {
      ElMessage.success('测试成功')
      await loadChannels()
    } else {
      ElMessage.error(res.data.message || '测试失败')
    }
  } catch (error) {
    ElMessage.error('测试失败')
  }
}

// 删除渠道
const deleteChannel = async (channel: NotificationChannel) => {
  try {
    await ElMessageBox.confirm(`确定要删除渠道"${channel.name}"吗？`, '确认删除', {
      type: 'warning'
    })
    await deleteNotificationChannel(channel.id)
    ElMessage.success('删除成功')
    await loadChannels()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

// ==================== 通知规则 ====================
const rulesLoading = ref(false)
const rules = ref<NotificationRule[]>([])

// 规则对话框
const ruleDialogVisible = ref(false)
const isEditMode = ref(false)
const ruleSaving = ref(false)
const ruleFormRef = ref<FormInstance>()

// 规则表单
const ruleForm = reactive({
  name: '',
  enabled: true,
  eventType: '',
  conditions: {},
  channelIds: [],
  sendInApp: true,
  templateId: undefined,
  silentHours: undefined,
  deduplicationWindow: 0,
  priority: 'medium',
  _id: undefined as number | undefined
})

const ruleFormRules: FormRules = {
  name: [{ required: true, message: '请输入规则名称', trigger: 'blur' }],
  eventType: [{ required: true, message: '请选择事件类型', trigger: 'change' }]
}

// 条件构建器
interface Condition {
  field: string
  operator: string
  value: string
}

const conditions = ref<Condition[]>([])

const addCondition = () => {
  conditions.value.push({ field: '', operator: 'eq', value: '' })
}

const removeCondition = (index: number) => {
  conditions.value.splice(index, 1)
}

// 静默时段
interface SilentPeriod {
  days: string[]
  start: string
  end: string
}

const silentHoursEnabled = ref(false)
const silentPeriods = ref<SilentPeriod[]>([])

const addSilentPeriod = () => {
  silentPeriods.value.push({ days: [], start: '22:00', end: '08:00' })
}

const removeSilentPeriod = (index: number) => {
  silentPeriods.value.splice(index, 1)
}

// ==================== 通知模板 ====================
const templatesLoading = ref(false)
const templates = ref<NotificationTemplate[]>([])

// 模板对话框
const templateDialogVisible = ref(false)
const isTemplateEditMode = ref(false)
const isTemplateViewMode = ref(false)
const templateSaving = ref(false)
const templateFormRef = ref<FormInstance>()

// 模板表单
const templateForm = reactive({
  name: '',
  eventType: '',
  language: 'zh-CN',
  format: 'text',
  titleTemplate: '',
  contentTemplate: '',
  variables: [],
  _id: undefined as number | undefined
})

const templateFormRules: FormRules = {
  name: [{ required: true, message: '请输入模板名称', trigger: 'blur' }],
  eventType: [{ required: true, message: '请选择事件类型', trigger: 'change' }],
  language: [{ required: true, message: '请选择语言', trigger: 'change' }],
  format: [{ required: true, message: '请选择格式', trigger: 'change' }],
  titleTemplate: [{ required: true, message: '请输入标题模板', trigger: 'blur' }],
  contentTemplate: [{ required: true, message: '请输入内容模板', trigger: 'blur' }]
}

// 计算可用变量
const availableTemplateVariables = computed(() => {
  return eventVariablesMap[templateForm.eventType] || []
})

// 预览对话框
const previewDialogVisible = ref(false)
const currentPreviewTemplate = ref<NotificationTemplate | null>(null)
const previewVariables = ref('')
const renderResult = ref<{ title: string; content: string } | null>(null)
const rendering = ref(false)

// 加载规则列表
const loadRules = async () => {
  rulesLoading.value = true
  try {
    const res = await getNotificationRuleList({ limit: 100 })
    if (res.data && res.data.items) {
      rules.value = res.data.items
    } else if (res.data && res.data.data && res.data.data.items) {
      rules.value = res.data.data.items
    }
  } catch (error) {
    console.error('Failed to load rules:', error)
    ElMessage.error('加载规则列表失败')
  } finally {
    rulesLoading.value = false
  }
}

// 显示规则对话框
const showRuleDialog = (rule?: NotificationRule) => {
  if (rule) {
    isEditMode.value = true
    Object.assign(ruleForm, {
      name: rule.name,
      enabled: rule.enabled,
      eventType: rule.eventType,
      conditions: rule.conditions || {},
      channelIds: rule.channelIds || [],
      sendInApp: rule.sendInApp,
      templateId: rule.templateId,
      silentHours: rule.silentHours,
      deduplicationWindow: rule.deduplicationWindow || 0,
      priority: rule.priority || 'medium',
      _id: rule.id
    })

    // 解析条件
    if (rule.conditions) {
      conditions.value = Object.entries(rule.conditions)
        .filter(([_, config]) => config != null) // 过滤掉 null/undefined 的条件
        .map(([field, config]: [string, any]) => ({
          field,
          operator: config?.operator || 'eq',
          value: String(config?.value || '')
        }))
    } else {
      conditions.value = []
    }

    // 解析静默时段
    if (rule.silentHours && rule.silentHours.enabled) {
      silentHoursEnabled.value = true
      silentPeriods.value = rule.silentHours.periods || []
    } else {
      silentHoursEnabled.value = false
      silentPeriods.value = []
    }
  } else {
    isEditMode.value = false
    resetRuleForm()
  }
  ruleDialogVisible.value = true
}

// 保存规则
const saveRule = async () => {
  if (!ruleFormRef.value) return

  await ruleFormRef.value.validate(async (valid) => {
    if (!valid) return

    ruleSaving.value = true
    try {
      // 构建条件对象
      const conditionsObj: Record<string, any> = {}
      conditions.value.forEach((cond) => {
        if (cond.field && cond.operator && cond.value) {
          conditionsObj[cond.field] = {
            operator: cond.operator,
            value: cond.value
          }
        }
      })

      // 构建静默时段
      let silentHours = undefined
      if (silentHoursEnabled.value && silentPeriods.value.length > 0) {
        silentHours = {
          enabled: true,
          periods: silentPeriods.value
        }
      }

      // 检查渠道选择
      if (!ruleForm.sendInApp && (!ruleForm.channelIds || ruleForm.channelIds.length === 0)) {
        ElMessage.error('请至少选择一种通知方式（站内信或外部渠道）')
        return
      }

      const data: any = {
        name: ruleForm.name,
        enabled: ruleForm.enabled,
        eventType: ruleForm.eventType,
        conditions: Object.keys(conditionsObj).length > 0 ? conditionsObj : undefined,
        channelIds: ruleForm.channelIds || [],
        sendInApp: ruleForm.sendInApp,
        templateId: ruleForm.templateId || undefined,
        silentHours: silentHours,
        deduplicationWindow: ruleForm.deduplicationWindow || undefined,
        priority: mapPriorityToNumber(ruleForm.priority),
        userId: userStore.user?.id || 1
      }

      if (isEditMode.value && ruleForm._id) {
        await updateNotificationRule(ruleForm._id, data)
        ElMessage.success('规则更新成功')
      } else {
        await createNotificationRule(data)
        ElMessage.success('规则创建成功')
      }

      ruleDialogVisible.value = false
      await loadRules()
    } catch (error) {
      console.error('Failed to save rule:', error)
      ElMessage.error('保存失败')
    } finally {
      ruleSaving.value = false
    }
  })
}

// 重置规则表单
const resetRuleForm = () => {
  Object.assign(ruleForm, {
    name: '',
    enabled: true,
    eventType: '',
    conditions: {},
    channelIds: [],
    sendInApp: true,
    templateId: undefined,
    silentHours: undefined,
    deduplicationWindow: 0,
    priority: 'medium',
    _id: undefined
  })
  conditions.value = []
  silentHoursEnabled.value = false
  silentPeriods.value = []
}

// 切换规则状态
const toggleRule = async (rule: NotificationRule) => {
  try {
    await toggleNotificationRule(rule.id)
    ElMessage.success(rule.enabled ? '规则已启用' : '规则已禁用')
  } catch (error) {
    console.error('Failed to toggle rule:', error)
    // 恢复状态
    rule.enabled = !rule.enabled
    ElMessage.error('操作失败')
  }
}

// 删除规则
const deleteRule = async (rule: NotificationRule) => {
  try {
    await ElMessageBox.confirm(`确定要删除规则"${rule.name}"吗？`, '确认删除', {
      type: 'warning'
    })
    await deleteNotificationRule(rule.id)
    ElMessage.success('删除成功')
    await loadRules()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

// ==================== 通知模板 ====================

// 加载模板列表
const loadTemplates = async () => {
  templatesLoading.value = true
  try {
    const res = await getNotificationTemplateList({ limit: 100 })
    if (res.data) {
      templates.value = res.data.items || []
    }
  } catch (error) {
    ElMessage.error('加载模板列表失败')
  } finally {
    templatesLoading.value = false
  }
}

// 显示模板对话框
const showTemplateDialog = (template?: NotificationTemplate) => {
  if (template) {
    isTemplateEditMode.value = true
    isTemplateViewMode.value = false
    loadTemplateData(template)
  } else {
    isTemplateEditMode.value = false
    isTemplateViewMode.value = false
    resetTemplateForm()
  }
  templateDialogVisible.value = true
}

// 查看模板
const viewTemplate = (template: NotificationTemplate) => {
  isTemplateEditMode.value = false
  isTemplateViewMode.value = true
  loadTemplateData(template)
  templateDialogVisible.value = true
}

// 加载模板数据到表单
const loadTemplateData = (template: NotificationTemplate) => {
  Object.assign(templateForm, {
    name: template.name,
    eventType: template.eventType,
    language: template.language,
    format: template.format,
    titleTemplate: template.titleTemplate,
    contentTemplate: template.contentTemplate,
    variables: template.variables || [],
    _id: template.id
  })
}

// 事件类型变化
const onTemplateEventTypeChange = () => {
  // 清空变量列表，让系统重新计算
  templateForm.variables = []
}

// 保存模板
const saveTemplate = async () => {
  if (!templateFormRef.value) return

  await templateFormRef.value.validate(async (valid) => {
    if (!valid) return

    templateSaving.value = true
    try {
      // 简单提取变量（实际项目中应该使用更复杂的正则表达式）
      const titleVars = extractVariables(templateForm.titleTemplate)
      const contentVars = extractVariables(templateForm.contentTemplate)
      const allVars = [...new Set([...titleVars, ...contentVars])]

      // 将变量数组转换为对象格式，符合后端API要求
      const variablesObj: Record<string, any> = {}
      allVars.forEach(variable => {
        variablesObj[variable] = ""  // 空字符串值，后端可能会填充默认值
      })

      const data: any = {
        name: templateForm.name,
        eventType: templateForm.eventType,
        language: templateForm.language,
        format: templateForm.format,
        titleTemplate: templateForm.titleTemplate,
        contentTemplate: templateForm.contentTemplate,
        variables: variablesObj,
        isSystem: false  // 明确设置为自定义模板
      }

      if (isTemplateEditMode.value && templateForm._id) {
        await updateNotificationTemplate(templateForm._id, data)
        ElMessage.success('模板更新成功')
      } else {
        await createNotificationTemplate(data)
        ElMessage.success('模板创建成功')
      }

      templateDialogVisible.value = false
      await loadTemplates()
    } catch (error) {
      console.error('Failed to save template:', error)
      ElMessage.error('保存失败')
    } finally {
      templateSaving.value = false
    }
  })
}

// 重置模板表单
const resetTemplateForm = () => {
  Object.assign(templateForm, {
    name: '',
    eventType: '',
    language: 'zh-CN',
    format: 'text',
    titleTemplate: '',
    contentTemplate: '',
    variables: [],
    _id: undefined
  })
}

// 提取模板变量
const extractVariables = (template: string): string[] => {
  const regex = /\{\{(\w+)\}\}/g
  const variables: string[] = []
  let match

  while ((match = regex.exec(template)) !== null) {
    variables.push(match[1])
  }

  return variables
}

// 预览模板
const previewTemplate = (template: NotificationTemplate) => {
  currentPreviewTemplate.value = template
  const variables = eventVariablesMap[template.eventType] || []
  const sampleData: Record<string, any> = {}

  // 生成示例数据
  variables.forEach((variable) => {
    if (variable === 'media_name') sampleData[variable] = '复仇者联盟4'
    else if (variable === 'quality') sampleData[variable] = '1080p'
    else if (variable === 'size_gb') sampleData[variable] = 15.5
    else if (variable === 'site_name') sampleData[variable] = 'MTeam'
    else if (variable === 'promotion_type') sampleData[variable] = '免费'
    else sampleData[variable] = `示例${variable}`
  })

  previewVariables.value = JSON.stringify(sampleData, null, 2)
  renderResult.value = null
  previewDialogVisible.value = true
}

// 渲染预览
const renderPreview = async () => {
  if (!currentPreviewTemplate.value) return

  rendering.value = true
  try {
    const variables = JSON.parse(previewVariables.value)
    // 简单的模板渲染（实际项目中应该使用后端API）
    let title = currentPreviewTemplate.value.titleTemplate
    let content = currentPreviewTemplate.value.contentTemplate

    // 替换变量
    Object.entries(variables).forEach(([key, value]) => {
      const regex = new RegExp(`\\{\\{${key}\\}\\}`, 'g')
      title = title.replace(regex, String(value))
      content = content.replace(regex, String(value))
    })

    renderResult.value = { title, content }
  } catch (error) {
    console.error('Failed to render preview:', error)
    ElMessage.error('渲染失败，请检查输入的 JSON 格式')
  } finally {
    rendering.value = false
  }
}

// 格式化预览内容
const formatPreviewContent = (content: string) => {
  if (currentPreviewTemplate.value?.format === 'markdown') {
    // 简单的 Markdown 渲染（实际项目中应使用专业的 Markdown 渲染库）
    return content
      .replace(/\n/g, '<br>')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
  } else if (currentPreviewTemplate.value?.format === 'html') {
    return content
  } else {
    return content.replace(/\n/g, '<br>')
  }
}

// 处理模板下拉菜单命令
const handleTemplateCommand = (command: string, template: NotificationTemplate) => {
  if (command === 'edit') {
    showTemplateDialog(template)
  } else if (command === 'delete') {
    deleteTemplate(template)
  }
}

// 删除模板
const deleteTemplate = async (template: NotificationTemplate) => {
  try {
    await ElMessageBox.confirm(`确定要删除模板"${template.name}"吗？`, '确认删除', {
      type: 'warning'
    })

    await deleteNotificationTemplate(template.id)
    ElMessage.success('删除成功')
    await loadTemplates()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to delete template:', error)
      ElMessage.error('删除失败')
    }
  }
}

// ==================== 辅助函数 ====================
const getEventTypeName = (type: string) => {
  return eventTypes.find((e) => e.value === type)?.label || type
}

// 优先级映射 (字符串转数字)
const mapPriorityToNumber = (priority: string): number => {
  const priorityMap: Record<string, number> = {
    'low': 2,
    'medium': 5,
    'high': 8,
    'urgent': 10
  }
  return priorityMap[priority] || 5  // 默认中等优先级
}

const getChannelTypeName = (type: string) => {
  const map: Record<string, string> = {
    telegram: 'Telegram',
    email: '邮件',
    webhook: 'Webhook'
  }
  return map[type] || type
}

const getChannelColor = (type: string) => {
  const map: Record<string, string> = {
    telegram: '#0088cc',
    email: '#409EFF',
    webhook: '#67C23A'
  }
  return map[type] || '#909399'
}

const getChannelTagType = (type: string) => {
  const map: Record<string, 'primary' | 'success' | 'info' | 'warning' | 'danger'> = {
    telegram: 'primary',
    email: 'info',
    webhook: 'success'
  }
  return map[type] || 'info'
}

const getChannelName = (channelId: number) => {
  const channel = channels.value.find(c => c.id === channelId)
  return channel?.name || `渠道${channelId}`
}

// ==================== 生命周期 ====================
onMounted(() => {
  loadGlobalSettings()
  loadChannels()
  loadRules()
  loadTemplates()
})
</script>

<style scoped>
.notification-manager {
  padding: var(--nf-spacing-lg);
}

.form-item-tips {
  font-size: var(--nf-font-size-mini);
  color: var(--nf-text-secondary);
  margin-top: var(--nf-spacing-xs);
  line-height: var(--nf-line-height-base);
}

.hint-text {
  margin-left: var(--nf-spacing-sm);
  color: var(--nf-text-secondary);
  font-size: var(--nf-font-size-mini);
}

.option-desc {
  color: var(--nf-text-placeholder);
  font-size: var(--nf-font-size-mini);
}

.notification-tabs {
  margin-top: var(--nf-spacing-lg);
}

.notification-tabs :deep(.el-tabs__header) {
  margin-bottom: var(--nf-spacing-lg);
}

.notification-tabs :deep(.el-tab-pane) {
  padding-top: 0;
}

.global-settings-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: var(--nf-spacing-lg);
}

.global-settings-section {
  background: var(--nf-bg-container);
  padding: var(--nf-spacing-lg);
  border-radius: var(--nf-radius-base);
  border: 1px solid var(--nf-border-base);
}

.global-settings-section h4 {
  margin: 0 0 var(--nf-spacing-base) 0;
  color: var(--nf-text-primary);
  font-size: var(--nf-font-size-h5);
  font-weight: var(--nf-font-weight-semibold);
  border-bottom: 2px solid var(--nf-primary);
  padding-bottom: var(--nf-spacing-sm);
}

.global-settings-section .el-form-item {
  margin-bottom: var(--nf-spacing-base);
}

.global-settings-section .el-form-item:last-child {
  margin-bottom: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: var(--nf-text-primary);
}

.channel-card {
  margin-bottom: var(--nf-spacing-base);
}

.channel-header {
  display: flex;
  align-items: center;
  gap: var(--nf-spacing-md);
  margin-bottom: var(--nf-spacing-md);
}

.channel-info {
  flex: 1;
}

.channel-info h4 {
  margin: 0 0 var(--nf-spacing-xs) 0;
  font-size: var(--nf-font-size-h5);
  color: var(--nf-text-primary);
}

.channel-info p {
  margin: 0;
  color: var(--nf-text-secondary);
  font-size: var(--nf-font-size-small);
}

.channel-body {
  display: flex;
  align-items: center;
  gap: var(--nf-spacing-sm);
  margin-bottom: var(--nf-spacing-md);
}

.channel-test-time {
  font-size: var(--nf-font-size-mini);
  color: var(--nf-text-secondary);
}

.channel-actions {
  display: flex;
  gap: var(--nf-spacing-sm);
}

.condition-item {
  display: flex;
  align-items: center;
  margin-bottom: var(--nf-spacing-sm);
}

.silent-period-item {
  display: flex;
  align-items: center;
  margin-bottom: var(--nf-spacing-sm);
}

.preview-result {
  margin-top: var(--nf-spacing-lg);

  .preview-content {
    .preview-item {
      margin-bottom: var(--nf-spacing-base);

      .preview-label {
        font-weight: var(--nf-font-weight-semibold);
        margin-bottom: var(--nf-spacing-sm);
        color: var(--nf-text-secondary);
      }

      .preview-value {
        padding: var(--nf-spacing-md);
        background: var(--nf-bg-container);
        border-radius: var(--nf-radius-sm);
        line-height: var(--nf-line-height-base);
        color: var(--nf-text-regular);
      }
    }
  }
}
</style>
