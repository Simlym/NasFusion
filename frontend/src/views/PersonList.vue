<template>
  <div class="page-container">
    <el-backtop target=".el-main" :right="40" :bottom="40" />

    <div class="page-header">
      <h2 class="page-title">人员 <span v-if="pagination.total > 0" class="page-count">({{ pagination.total.toLocaleString() }})</span></h2>
      <div class="header-actions">
        <!-- 筛选条件 -->
        <el-select
          v-model="filterGender"
          placeholder="性别"
          clearable
          style="width: 100px"
          @change="handleFilterChange"
        >
          <el-option label="男" :value="2" />
          <el-option label="女" :value="1" />
        </el-select>

        <el-select
          v-model="filterDepartment"
          placeholder="职能"
          clearable
          style="width: 130px"
          @change="handleFilterChange"
        >
          <el-option
            v-for="dept in departments"
            :key="dept"
            :label="translateDepartment(dept)"
            :value="dept"
          />
        </el-select>

        <el-select
          v-model="filterCountry"
          placeholder="国家/地区"
          clearable
          style="width: 120px"
          @change="handleFilterChange"
        >
          <el-option label="中国大陆" value="CN" />
          <el-option label="中国香港" value="HK" />
          <el-option label="中国台湾" value="TW" />
          <el-option label="日本" value="JP" />
          <el-option label="韩国" value="KR" />
          <el-option label="美国" value="US" />
          <el-option label="英国" value="GB" />
          <el-option label="法国" value="FR" />
          <el-option label="德国" value="DE" />
          <el-option label="印度" value="IN" />
          <el-option label="泰国" value="TH" />
          <el-option label="加拿大" value="CA" />
          <el-option label="澳大利亚" value="AU" />
          <el-option label="其他" value="OTHER" />
        </el-select>

        <el-select
          v-model="filterSource"
          placeholder="数据来源"
          clearable
          style="width: 120px"
          @change="handleFilterChange"
        >
          <el-option label="TMDB" value="tmdb" />
          <el-option label="豆瓣" value="douban" />
        </el-select>

        <el-select
          v-model="filterDetailLoaded"
          placeholder="详情同步"
          clearable
          style="width: 120px"
          @change="handleFilterChange"
        >
          <el-option label="已同步" :value="true" />
          <el-option label="未同步" :value="false" />
        </el-select>

        <el-select
          v-model="sortBy"
          placeholder="排序"
          style="width: 120px"
          @change="handleFilterChange"
        >
          <el-option label="热度" value="popularity" />
          <el-option label="作品总数" value="total_credits" />
          <el-option label="电影数量" value="movie_count" />
          <el-option label="剧集数量" value="tv_count" />
          <el-option label="姓名" value="name" />
          <el-option label="生日" value="birthday" />
          <el-option label="创建时间" value="created_at" />
        </el-select>

        <el-button
          :icon="sortOrder === 'desc' ? SortDown : SortUp"
          circle
          @click="toggleSortOrder"
          :title="sortOrder === 'desc' ? '降序' : '升序'"
        />

        <el-input
          v-model="searchKeyword"
          placeholder="搜索人员姓名"
          clearable
          class="search-input"
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
      </div>
    </div>

    <div v-loading="loading" class="person-list-container">
      <div v-if="persons.length > 0" class="person-grid">
        <div
          v-for="person in persons"
          :key="person.id"
          class="person-card"
          @click="goToPerson(person.id)"
        >
          <div class="person-avatar">
            <el-image
              v-if="person.profileUrl"
              :src="getProxiedImageUrl(person.profileUrl)"
              fit="cover"
              class="avatar-image"
              loading="lazy"
            >
              <template #error>
                <div class="avatar-placeholder">
                  <el-icon :size="48"><User /></el-icon>
                </div>
              </template>
            </el-image>
            <div v-else class="avatar-placeholder">
              <el-icon :size="48"><User /></el-icon>
            </div>
            <!-- 数据来源角标 -->
            <div v-if="person.metadataSource" class="source-badge" :class="person.metadataSource">
              {{ person.metadataSource === 'douban' ? '豆' : 'T' }}
            </div>
          </div>
          <div class="person-info">
            <div class="person-name" :title="person.name">{{ person.name }}</div>
            <div v-if="person.birthday" class="person-meta-row" :title="person.birthday">
              <el-icon :size="12"><Calendar /></el-icon>
              <span>{{ formatBirthday(person.birthday, person.deathday) }}</span>
            </div>
            <div v-if="person.placeOfBirth" class="person-meta-row" :title="person.placeOfBirth">
              <el-icon :size="12"><Location /></el-icon>
              <span class="meta-place">{{ person.placeOfBirth }}</span>
            </div>
            <div v-if="(person.movieCount && person.movieCount > 0) || (person.tvCount && person.tvCount > 0)" class="person-credits">
              <span v-if="person.movieCount && person.movieCount > 0" class="credit-item">
                <AppIcon name="lucide:film" :size="12" />
                <span>{{ person.movieCount }}</span>
              </span>
              <span v-if="person.tvCount && person.tvCount > 0" class="credit-item">
                <AppIcon name="lucide:tv" :size="12" />
                <span>{{ person.tvCount }}</span>
              </span>
            </div>
          </div>
        </div>
      </div>

      <el-empty
        v-else-if="!loading"
        description="暂无人员数据"
      />

      <!-- 加载更多指示器 -->
      <div v-if="loadingMore" class="loading-more">
        <el-icon class="is-loading">
          <Loading />
        </el-icon>
        <span>加载中...</span>
      </div>

      <!-- 已加载全部 -->
      <div v-if="noMore && persons.length > 0" class="no-more">
        已加载全部内容
      </div>

      <!-- 无限滚动触发器 -->
      <div ref="scrollTrigger" class="scroll-trigger"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Search, User, SortDown, SortUp, Loading, Calendar, Location } from '@element-plus/icons-vue'
import AppIcon from '@/components/common/AppIcon.vue'
import api from '@/api'
import { getProxiedImageUrl } from '@/utils'

const router = useRouter()

const loading = ref(false)
const loadingMore = ref(false)
const noMore = ref(false)
const persons = ref<any[]>([])
const searchKeyword = ref('')
const scrollTrigger = ref<HTMLElement | null>(null)

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0,
})

// 筛选条件
const filterGender = ref<number | undefined>(undefined)
const filterCountry = ref<string>('')
const filterDepartment = ref<string>('')
const filterSource = ref<string>('')
const filterDetailLoaded = ref<boolean | undefined>(undefined)
const sortBy = ref<string>('popularity')
const sortOrder = ref<string>('desc')
const departments = ref<string[]>([])

// 持久化存储 Key
const STORAGE_KEY = 'nasfusion_persons_filter'

// 保存筛选状态
const saveFilterState = () => {
  const state = {
    search: searchKeyword.value,
    gender: filterGender.value,
    country: filterCountry.value,
    department: filterDepartment.value,
    source: filterSource.value,
    detailLoaded: filterDetailLoaded.value,
    sortBy: sortBy.value,
    sortOrder: sortOrder.value
  }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
}

// 恢复筛选状态
const restoreFilterState = () => {
  const saved = localStorage.getItem(STORAGE_KEY)
  if (saved) {
    try {
      const state = JSON.parse(saved)
      if (state.search) searchKeyword.value = state.search
      if (state.gender !== undefined) filterGender.value = state.gender
      if (state.country) filterCountry.value = state.country
      if (state.department) filterDepartment.value = state.department
      if (state.source) filterSource.value = state.source
      if (state.detailLoaded !== undefined) filterDetailLoaded.value = state.detailLoaded
      if (state.sortBy) sortBy.value = state.sortBy
      if (state.sortOrder) sortOrder.value = state.sortOrder
    } catch (e) {
      console.error('Failed to restore filter state', e)
    }
  }
}

// 职能翻译
const departmentMap: Record<string, string> = {
  'Acting': '演员',
  'Actor': '演员',
  'Directing': '导演',
  'Director': '导演',
  'Writing': '编剧',
  'Writer': '编剧',
  'Production': '制片',
  'Camera': '摄影',
  'Editing': '剪辑',
  'Sound': '音效',
  'Art': '美术',
  'Crew': '幕后',
  'Visual Effects': '视觉效果',
  'Costume & Make-Up': '服装化妆',
  'Lighting': '灯光',
  'Creator': '创作者',
}

const translateDepartment = (dept: string) => {
  return departmentMap[dept] || dept
}

const calculateAge = (birthday: string, deathday?: string): number | null => {
  const birth = new Date(birthday)
  if (isNaN(birth.getTime())) return null
  const end = deathday ? new Date(deathday) : new Date()
  let age = end.getFullYear() - birth.getFullYear()
  const monthDiff = end.getMonth() - birth.getMonth()
  if (monthDiff < 0 || (monthDiff === 0 && end.getDate() < birth.getDate())) {
    age--
  }
  return age >= 0 ? age : null
}

const formatBirthday = (birthday: string, deathday?: string): string => {
  const age = calculateAge(birthday, deathday)
  if (age !== null) {
    return `${birthday}（${age}岁）`
  }
  return birthday
}

const loadPersons = async (append = false) => {
  if (append) {
    loadingMore.value = true
  } else {
    loading.value = true
  }

  try {
    const response = await api.person.getPersonList({
      page: pagination.page,
      pageSize: pagination.pageSize,
      search: searchKeyword.value || undefined,
      gender: filterGender.value,
      country: filterCountry.value || undefined,
      department: filterDepartment.value || undefined,
      metadataSource: filterSource.value || undefined,
      detailLoaded: filterDetailLoaded.value,
      sortBy: sortBy.value,
      sortOrder: sortOrder.value,
    })

    const data = response.data
    if (data) {
      const newPersons = data.items || []

      if (append) {
        persons.value = [...persons.value, ...newPersons]
      } else {
        persons.value = newPersons
      }

      pagination.total = data.total || 0

      // 检查是否已加载全部
      noMore.value = persons.value.length >= pagination.total
    }
  } catch (error) {
    console.error('Failed to load persons:', error)
    ElMessage.error('获取人员列表失败')
  } finally {
    loading.value = false
    loadingMore.value = false
  }
}

const loadMorePersons = () => {
  if (loading.value || loadingMore.value || noMore.value) return

  pagination.page++
  loadPersons(true)
}

const loadDepartments = async () => {
  try {
    const response = await api.person.getPersonDepartments()
    departments.value = response.data || []
  } catch (error) {
    console.error('Failed to load departments:', error)
  }
}

const handleSearch = () => {
  saveFilterState()
  pagination.page = 1
  noMore.value = false
  loadPersons(false)
}

const handleFilterChange = () => {
  saveFilterState()
  pagination.page = 1
  noMore.value = false
  loadPersons(false)
}

const toggleSortOrder = () => {
  sortOrder.value = sortOrder.value === 'desc' ? 'asc' : 'desc'
  saveFilterState()
  pagination.page = 1
  noMore.value = false
  loadPersons(false)
}

const goToPerson = (id: number) => {
  router.push(`/person/${id}`)
}

// IntersectionObserver for infinite scroll
let observer: IntersectionObserver | null = null

const setupIntersectionObserver = () => {
  if (!scrollTrigger.value) return

  observer = new IntersectionObserver(
    (entries) => {
      const target = entries[0]
      if (target.isIntersecting) {
        loadMorePersons()
      }
    },
    {
      root: null,
      rootMargin: '300px',
      threshold: 0.1,
    }
  )

  observer.observe(scrollTrigger.value)
}

const cleanupIntersectionObserver = () => {
  if (observer && scrollTrigger.value) {
    observer.unobserve(scrollTrigger.value)
    observer.disconnect()
    observer = null
  }
}

onMounted(async () => {
  restoreFilterState()
  await Promise.all([
    loadPersons(),
    loadDepartments(),
  ])
  setTimeout(() => {
    setupIntersectionObserver()
  }, 100)
})

onUnmounted(() => {
  cleanupIntersectionObserver()
})
</script>

<style scoped>
.page-container {
  width: 100%;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 12px;
}

.page-title {
  margin: 0;
  font-size: 22px;
  font-weight: 600;
  color: var(--nf-text-primary, var(--el-text-color-primary));
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.page-count {
  font-size: 14px;
  color: var(--el-text-color-secondary);
  font-weight: normal;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.person-list-container {
  min-height: 200px;
}

.person-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 20px;
}

.person-card {
  cursor: pointer;
  transition: transform 0.3s ease, box-shadow 0.3s ease;
  border-radius: 10px;
  overflow: hidden;
  background: var(--nf-bg-overlay, var(--el-bg-color-overlay));
  border: 1px solid var(--nf-border-base, var(--el-border-color-lighter));
}

.person-card:hover {
  transform: translateY(-6px);
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.18);
}

.person-avatar {
  width: 100%;
  aspect-ratio: 2 / 3;
  overflow: hidden;
  position: relative;
}

.avatar-image {
  width: 100%;
  height: 100%;
}

.avatar-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, var(--el-fill-color-light) 0%, var(--el-fill-color) 100%);
  color: var(--el-text-color-secondary);
}

.source-badge {
  position: absolute;
  top: 6px;
  left: 6px;
  width: 22px;
  height: 22px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: bold;
  color: #fff;
  opacity: 0.9;
}

.source-badge.douban {
  background: linear-gradient(135deg, #41b883, #2d9c5a);
}

.source-badge.tmdb {
  background: linear-gradient(135deg, #01b4e4, #0d82a8);
}

.person-info {
  padding: 10px 12px;
}

.person-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--nf-text-primary, var(--el-text-color-primary));
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.person-meta-row {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: var(--nf-text-secondary, var(--el-text-color-secondary));
  margin-top: 4px;
  line-height: 1.4;
}

.person-meta-row .el-icon {
  flex-shrink: 0;
  color: var(--el-text-color-placeholder);
}

.person-meta-row .meta-place {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.person-credits {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: var(--nf-text-secondary, var(--el-text-color-secondary));
  margin-top: 4px;
  line-height: 1.4;
}

.credit-item {
  display: inline-flex;
  align-items: center;
  gap: 3px;
}

.credit-item .el-icon {
  flex-shrink: 0;
  color: var(--el-text-color-placeholder);
}

/* 加载更多和结束提示 */
.loading-more,
.no-more {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
  padding: 32px 0;
  color: var(--el-text-color-secondary);
  font-size: 14px;
}

.loading-more .el-icon {
  font-size: 18px;
}

.search-input {
  width: 240px;
}

/* 无限滚动触发器 */
.scroll-trigger {
  height: 1px;
  width: 100%;
  visibility: hidden;
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .header-actions {
    width: 100%;
    overflow-x: auto;
  }

  .person-grid {
    grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
    gap: 12px;
  }

  .search-input {
    width: 100%;
  }
}
</style>
