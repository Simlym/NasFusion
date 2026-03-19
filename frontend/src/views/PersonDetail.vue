<template>
  <div class="page-container">
    <el-page-header @back="handleBack">
      <template #content>
        <span class="page-title">人员详情</span>
      </template>
    </el-page-header>

    <div v-loading="loading" class="person-detail-container">
      <el-card v-if="person" class="person-info-card">
        <div class="person-header">
          <!-- 左侧：头像 -->
          <div class="person-image-section">
            <el-image
              v-if="person.profileUrl"
              :src="getProxiedImageUrl(person.profileUrl)"
              fit="cover"
              class="person-image"
            >
              <template #error>
                <div class="image-slot">
                  <el-icon :size="48"><User /></el-icon>
                </div>
              </template>
            </el-image>
            <div v-else class="image-slot">
              <el-icon :size="48"><User /></el-icon>
            </div>
          </div>

          <!-- 右侧：详细信息 -->
          <div class="person-info-section">
            <div class="person-title-row">
              <h1 class="person-name">{{ person.name }}</h1>
              <el-button type="primary" link :icon="Edit" @click="handleEdit">编辑</el-button>
            </div>
            
            <!-- 基础元信息行 -->
            <div class="person-meta-row">
              <div v-if="person.gender !== undefined && person.gender !== 0" class="meta-item">
                <el-icon><Male v-if="person.gender === 2" /><Female v-else /></el-icon>
                <span>{{ person.gender === 2 ? '男' : '女' }}</span>
              </div>
              <div v-if="person.birthday" class="meta-item">
                <el-icon><Calendar /></el-icon>
                <span>{{ person.birthday }}</span>
                <span v-if="person.deathday"> - {{ person.deathday }}</span>
                <span v-else-if="person.birthday"> ({{ calculateAge(person.birthday) }}岁)</span>
              </div>
              <div v-if="person.placeOfBirth" class="meta-item">
                <el-icon><Location /></el-icon>
                <span>{{ person.placeOfBirth }}</span>
              </div>
            </div>

            <!-- 标签行 -->
            <div class="person-tags">
              <el-tag v-if="person.knownForDepartment" effect="plain" class="tag-item">
                {{ translateDepartment(person.knownForDepartment) }}
              </el-tag>
              <el-tag v-if="person.metadataSource" :type="person.metadataSource === 'douban' ? 'success' : 'primary'" effect="plain" class="tag-item">
                {{ person.metadataSource === 'douban' ? '豆瓣' : 'TMDB' }}
              </el-tag>
              <el-tag v-if="person.popularity" type="warning" effect="plain" class="tag-item">
                热度: {{ person.popularity?.toFixed(1) }}
              </el-tag>
            </div>

            <!-- 别名 -->
            <div v-if="displayOtherNames" class="info-block">
              <div class="info-label">
                <el-icon><User /></el-icon>
                别名
              </div>
              <div class="info-value">{{ displayOtherNames }}</div>
            </div>

            <!-- 家庭成员 -->
            <div v-if="person.familyInfo" class="info-block">
              <div class="info-label">
                <el-icon><House /></el-icon>
                家庭成员
              </div>
              <div class="info-value">{{ person.familyInfo }}</div>
            </div>

            <!-- 简介 -->
            <div v-if="person.biography" class="person-biography">
              <div class="info-label">
                <el-icon><Document /></el-icon>
                简介
              </div>
              <p :class="{ 'collapsed': isBioCollapsed }" @click="toggleBio">
                {{ person.biography }}
              </p>
              <el-button v-if="isBioLong" link type="primary" size="small" @click="toggleBio">
                {{ isBioCollapsed ? '展开' : '收起' }}
              </el-button>
            </div>

            <!-- 外部链接 -->
            <div class="person-external-ids">
              <el-link v-if="person.homepage" :href="person.homepage" target="_blank" type="info" :underline="false" class="external-link">
                <span class="external-icon homepage-icon">🏠</span>
                主页
              </el-link>
              <el-link v-if="person.doubanId" :href="`https://www.douban.com/personage/${person.doubanId}/`" target="_blank" type="success" :underline="false" class="external-link">
                <span class="external-icon douban-icon">豆</span>
                豆瓣
              </el-link>
              <el-link v-if="person.tmdbId" :href="`https://www.themoviedb.org/person/${person.tmdbId}`" target="_blank" type="primary" :underline="false" class="external-link">
                <span class="external-icon tmdb-icon">T</span>
                TMDB
              </el-link>
              <el-link v-if="person.imdbId" :href="`https://www.imdb.com/name/${person.imdbId}`" target="_blank" type="warning" :underline="false" class="external-link">
                <span class="external-icon imdb-icon">I</span>
                IMDB
              </el-link>
            </div>

            <!-- 详细ID信息 -->
            <div class="person-ids">
              <span v-if="person.doubanId" class="id-item">豆瓣ID: {{ person.doubanId }}</span>
              <span v-if="person.tmdbId" class="id-item">TMDB ID: {{ person.tmdbId }}</span>
              <span v-if="person.imdbId" class="id-item">IMDB ID: {{ person.imdbId }}</span>
            </div>
          </div>
        </div>
      </el-card>

      <!-- 参演作品 -->
      <div v-if="hasCredits" class="credits-section">
        <h2 class="section-title">参演作品</h2>
        <el-tabs v-model="activeTab" class="credits-tabs">
          <!-- 参演电影 -->
          <el-tab-pane
            v-if="credits.castMovies && credits.castMovies.length"
            :label="`参演电影 (${credits.castMovies.length})`"
            name="cast_movies"
          >
            <div class="sort-controls">
              <el-button
                :type="sortBy === 'year' ? 'primary' : 'default'"
                size="small"
                @click="toggleSort('year')"
              >
                年份
                <el-icon v-if="sortBy === 'year'" class="sort-icon">
                  <SortUp v-if="sortOrder === 'asc'" />
                  <SortDown v-else />
                </el-icon>
              </el-button>
              <el-button
                :type="sortBy === 'rating' ? 'primary' : 'default'"
                size="small"
                @click="toggleSort('rating')"
              >
                评分
                <el-icon v-if="sortBy === 'rating'" class="sort-icon">
                  <SortUp v-if="sortOrder === 'asc'" />
                  <SortDown v-else />
                </el-icon>
              </el-button>
            </div>
            <div class="credits-grid">
              <div
                v-for="credit in sortedCastMovies"
                :key="`cm-${credit.movie.id}`"
                class="credit-card"
                @click="goToMovie(credit.movie.id)"
              >
                <div class="credit-poster-wrap">
                  <el-image 
                    :src="getProxiedImageUrl(credit.movie.posterUrl)" 
                    class="credit-poster" 
                    fit="cover" 
                    loading="lazy"
                  >
                    <template #error>
                      <div class="poster-placeholder">
                        <el-icon :size="32"><Picture /></el-icon>
                      </div>
                    </template>
                  </el-image>
                  <div v-if="credit.movie.ratingDouban || credit.movie.ratingTmdb" class="credit-rating">
                    {{ (credit.movie.ratingDouban || credit.movie.ratingTmdb)?.toFixed(1) }}
                  </div>
                </div>
                <div class="credit-info">
                  <div class="credit-title" :title="credit.movie.title">{{ credit.movie.title }}</div>
                  <div class="credit-year" v-if="credit.movie.year">({{ credit.movie.year }})</div>
                  <div class="credit-character" v-if="credit.character">饰 {{ credit.character }}</div>
                </div>
              </div>
            </div>
          </el-tab-pane>

          <!-- 参演剧集 -->
          <el-tab-pane
            v-if="credits.castTv && credits.castTv.length"
            :label="`参演剧集 (${credits.castTv.length})`"
            name="cast_tv"
          >
            <div class="sort-controls">
              <el-button
                :type="sortBy === 'year' ? 'primary' : 'default'"
                size="small"
                @click="toggleSort('year')"
              >
                年份
                <el-icon v-if="sortBy === 'year'" class="sort-icon">
                  <SortUp v-if="sortOrder === 'asc'" />
                  <SortDown v-else />
                </el-icon>
              </el-button>
              <el-button
                :type="sortBy === 'rating' ? 'primary' : 'default'"
                size="small"
                @click="toggleSort('rating')"
              >
                评分
                <el-icon v-if="sortBy === 'rating'" class="sort-icon">
                  <SortUp v-if="sortOrder === 'asc'" />
                  <SortDown v-else />
                </el-icon>
              </el-button>
            </div>
            <div class="credits-grid">
              <div
                v-for="credit in sortedCastTv"
                :key="`ct-${credit.tvSeries.id}`"
                class="credit-card"
                @click="goToTv(credit.tvSeries.id)"
              >
                <div class="credit-poster-wrap">
                  <el-image 
                    :src="getProxiedImageUrl(credit.tvSeries.posterUrl)" 
                    class="credit-poster" 
                    fit="cover" 
                    loading="lazy"
                  >
                    <template #error>
                      <div class="poster-placeholder">
                        <el-icon :size="32"><Picture /></el-icon>
                      </div>
                    </template>
                  </el-image>
                  <div v-if="credit.tvSeries.ratingDouban || credit.tvSeries.ratingTmdb" class="credit-rating">
                    {{ (credit.tvSeries.ratingDouban || credit.tvSeries.ratingTmdb)?.toFixed(1) }}
                  </div>
                </div>
                <div class="credit-info">
                  <div class="credit-title" :title="credit.tvSeries.title">{{ credit.tvSeries.title }}</div>
                  <div class="credit-year" v-if="credit.tvSeries.year">({{ credit.tvSeries.year }})</div>
                  <div class="credit-character" v-if="credit.character">饰 {{ credit.character }}</div>
                </div>
              </div>
            </div>
          </el-tab-pane>

          <!-- 幕后制作（电影） -->
          <el-tab-pane
            v-if="credits.crewMovies && credits.crewMovies.length"
            :label="`幕后电影 (${credits.crewMovies.length})`"
            name="crew_movies"
          >
            <div class="sort-controls">
              <el-button
                :type="sortBy === 'year' ? 'primary' : 'default'"
                size="small"
                @click="toggleSort('year')"
              >
                年份
                <el-icon v-if="sortBy === 'year'" class="sort-icon">
                  <SortUp v-if="sortOrder === 'asc'" />
                  <SortDown v-else />
                </el-icon>
              </el-button>
              <el-button
                :type="sortBy === 'rating' ? 'primary' : 'default'"
                size="small"
                @click="toggleSort('rating')"
              >
                评分
                <el-icon v-if="sortBy === 'rating'" class="sort-icon">
                  <SortUp v-if="sortOrder === 'asc'" />
                  <SortDown v-else />
                </el-icon>
              </el-button>
            </div>
            <div class="credits-grid">
              <div
                v-for="credit in sortedCrewMovies"
                :key="`crm-${credit.movie.id}-${credit.job}`"
                class="credit-card"
                @click="goToMovie(credit.movie.id)"
              >
                <div class="credit-poster-wrap">
                  <el-image 
                    :src="getProxiedImageUrl(credit.movie.posterUrl)" 
                    class="credit-poster" 
                    fit="cover" 
                    loading="lazy"
                  >
                    <template #error>
                      <div class="poster-placeholder">
                        <el-icon :size="32"><Picture /></el-icon>
                      </div>
                    </template>
                  </el-image>
                  <div v-if="credit.movie.ratingDouban || credit.movie.ratingTmdb" class="credit-rating">
                    {{ (credit.movie.ratingDouban || credit.movie.ratingTmdb)?.toFixed(1) }}
                  </div>
                </div>
                <div class="credit-info">
                  <div class="credit-title" :title="credit.movie.title">{{ credit.movie.title }}</div>
                  <div class="credit-year" v-if="credit.movie.year">({{ credit.movie.year }})</div>
                  <div class="credit-job">{{ translateDepartment(credit.job) }}</div>
                </div>
              </div>
            </div>
          </el-tab-pane>

          <!-- 幕后制作（剧集） -->
          <el-tab-pane
            v-if="credits.crewTv && credits.crewTv.length"
            :label="`幕后剧集 (${credits.crewTv.length})`"
            name="crew_tv"
          >
            <div class="sort-controls">
              <el-button
                :type="sortBy === 'year' ? 'primary' : 'default'"
                size="small"
                @click="toggleSort('year')"
              >
                年份
                <el-icon v-if="sortBy === 'year'" class="sort-icon">
                  <SortUp v-if="sortOrder === 'asc'" />
                  <SortDown v-else />
                </el-icon>
              </el-button>
              <el-button
                :type="sortBy === 'rating' ? 'primary' : 'default'"
                size="small"
                @click="toggleSort('rating')"
              >
                评分
                <el-icon v-if="sortBy === 'rating'" class="sort-icon">
                  <SortUp v-if="sortOrder === 'asc'" />
                  <SortDown v-else />
                </el-icon>
              </el-button>
            </div>
            <div class="credits-grid">
              <div
                v-for="credit in sortedCrewTv"
                :key="`crt-${credit.tvSeries.id}-${credit.job}`"
                class="credit-card"
                @click="goToTv(credit.tvSeries.id)"
              >
                <div class="credit-poster-wrap">
                  <el-image 
                    :src="getProxiedImageUrl(credit.tvSeries.posterUrl)" 
                    class="credit-poster" 
                    fit="cover" 
                    loading="lazy"
                  >
                    <template #error>
                      <div class="poster-placeholder">
                        <el-icon :size="32"><Picture /></el-icon>
                      </div>
                    </template>
                  </el-image>
                  <div v-if="credit.tvSeries.ratingDouban || credit.tvSeries.ratingTmdb" class="credit-rating">
                    {{ (credit.tvSeries.ratingDouban || credit.tvSeries.ratingTmdb)?.toFixed(1) }}
                  </div>
                </div>
                <div class="credit-info">
                  <div class="credit-title" :title="credit.tvSeries.title">{{ credit.tvSeries.title }}</div>
                  <div class="credit-year" v-if="credit.tvSeries.year">({{ credit.tvSeries.year }})</div>
                  <div class="credit-job">{{ translateDepartment(credit.job) }}</div>
                </div>
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>

      <!-- 无关联作品提示 -->
      <el-card v-else-if="!loading && person" class="no-credits-card">
        <el-empty description="暂无关联影视作品" />
      </el-card>
    </div>

    <!-- 编辑对话框 -->
    <el-dialog
      v-model="editDialogVisible"
      title="编辑人员信息"
      width="600px"
      :close-on-click-modal="false"
    >
      <el-form :model="editForm" label-width="100px">
        <el-form-item label="姓名">
          <el-input v-model="editForm.name" />
        </el-form-item>
        <el-form-item label="别名">
          <el-select
            v-model="editForm.otherNames"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="输入别名并回车"
          />
        </el-form-item>
        <el-form-item label="性别">
          <el-radio-group v-model="editForm.gender">
            <el-radio :label="1">女</el-radio>
            <el-radio :label="2">男</el-radio>
            <el-radio :label="0">未知</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="出生日期">
          <el-date-picker
            v-model="editForm.birthday"
            type="date"
            placeholder="选择日期"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>
        <el-form-item label="逝世日期">
          <el-date-picker
            v-model="editForm.deathday"
            type="date"
            placeholder="选择日期"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>
        <el-form-item label="出生地">
          <el-input v-model="editForm.placeOfBirth" />
        </el-form-item>
        <el-form-item label="知名部门">
          <el-input v-model="editForm.knownForDepartment" />
        </el-form-item>
        <el-form-item label="简介">
          <el-input
            v-model="editForm.biography"
            type="textarea"
            :rows="6"
          />
        </el-form-item>
        <el-form-item label="头像URL">
          <el-input v-model="editForm.profileUrl" />
        </el-form-item>
        <el-form-item label="主页">
          <el-input v-model="editForm.homepage" />
        </el-form-item>
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="TMDB ID" label-width="80px">
              <el-input v-model.number="editForm.tmdbId" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="IMDB ID" label-width="80px">
              <el-input v-model="editForm.imdbId" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="豆瓣 ID" label-width="80px">
              <el-input v-model="editForm.doubanId" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="editDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="savePerson" :loading="saving">
            保存
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Calendar, Location, Male, Female, Picture, House, Link, Document, Edit, SortUp, SortDown } from '@element-plus/icons-vue'
import api from '@/api'
import type { UnifiedPerson, PersonCredits } from '@/types'
import { getProxiedImageUrl } from '@/utils'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const person = ref<UnifiedPerson | null>(null)
const credits = ref<PersonCredits>({
  castMovies: [],
  crewMovies: [],
  castTv: [],
  crewTv: [],
})
const activeTab = ref('cast_movies')
const isBioCollapsed = ref(true)

const editDialogVisible = ref(false)
const saving = ref(false)
const editForm = ref<Partial<UnifiedPerson>>({})

// 排序相关
const sortBy = ref<'year' | 'rating'>('year')
const sortOrder = ref<'desc' | 'asc'>('desc')

// 切换排序
const toggleSort = (field: 'year' | 'rating') => {
  if (sortBy.value === field) {
    sortOrder.value = sortOrder.value === 'desc' ? 'asc' : 'desc'
  } else {
    sortBy.value = field
    sortOrder.value = 'desc'
  }
}

// 排序函数
const sortCredits = <T extends { movie?: { year?: number | null; ratingDouban?: number | null; ratingTmdb?: number | null }; tvSeries?: { year?: number | null; ratingDouban?: number | null; ratingTmdb?: number | null } }>(items: T[]): T[] => {
  return [...items].sort((a, b) => {
    const itemA = a.movie || a.tvSeries
    const itemB = b.movie || b.tvSeries
    if (!itemA || !itemB) return 0

    let valueA: number | null = null
    let valueB: number | null = null

    if (sortBy.value === 'year') {
      valueA = itemA.year ?? null
      valueB = itemB.year ?? null
    } else {
      valueA = itemA.ratingDouban || itemA.ratingTmdb || null
      valueB = itemB.ratingDouban || itemB.ratingTmdb || null
    }

    // null 值排到最后
    if (valueA === null && valueB === null) return 0
    if (valueA === null) return 1
    if (valueB === null) return -1

    return sortOrder.value === 'desc' ? valueB - valueA : valueA - valueB
  })
}

// 排序后的数据
const sortedCastMovies = computed(() => sortCredits(credits.value.castMovies || []))
const sortedCastTv = computed(() => sortCredits(credits.value.castTv || []))
const sortedCrewMovies = computed(() => sortCredits(credits.value.crewMovies || []))
const sortedCrewTv = computed(() => sortCredits(credits.value.crewTv || []))

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

const hasCredits = computed(() => {
  return credits.value.castMovies?.length > 0 ||
         credits.value.crewMovies?.length > 0 ||
         credits.value.castTv?.length > 0 ||
         credits.value.crewTv?.length > 0
})

const isBioLong = computed(() => {
    return person.value?.biography && person.value.biography.length > 300
})

const toggleBio = () => {
    isBioCollapsed.value = !isBioCollapsed.value
}

const calculateAge = (birthday: string) => {
    const birthDate = new Date(birthday)
    const ageDifMs = Date.now() - birthDate.getTime()
    const ageDate = new Date(ageDifMs)
    return Math.abs(ageDate.getUTCFullYear() - 1970)
}

const displayOtherNames = computed(() => {
    if (!person.value || !person.value.otherNames) return ''
    return person.value.otherNames
        .filter(n => n !== person.value?.name)
        .join(' / ')
})

const loadData = async () => {
    loading.value = true
    try {
        const id = Number(route.params.id)
        const [personRes, creditsRes] = await Promise.all([
            api.person.getPersonDetail(id),
            api.person.getPersonCredits(id)
        ])
        
        person.value = personRes.data
        credits.value = creditsRes.data

        // Set default tab
        if (credits.value.castMovies?.length) activeTab.value = 'cast_movies'
        else if (credits.value.castTv?.length) activeTab.value = 'cast_tv'
        else if (credits.value.crewMovies?.length) activeTab.value = 'crew_movies'
        else if (credits.value.crewTv?.length) activeTab.value = 'crew_tv'
    } catch (error) {
        console.error("Failed to load person data", error)
        ElMessage.error("获取人员信息失败")
    } finally {
        loading.value = false
    }
}

const handleBack = () => {
    router.back()
}

const goToMovie = (id: number) => {
    router.push(`/movies/${id}`)
}
const goToTv = (id: number) => {
    router.push(`/tv/${id}`)
}

const handleEdit = () => {
    if (!person.value) return
    editForm.value = {
        ...person.value,
        otherNames: person.value.otherNames ? [...person.value.otherNames] : []
    }
    editDialogVisible.value = true
}

const savePerson = async () => {
    if (!person.value) return
    saving.value = true
    try {
        const res = await api.person.updatePerson(person.value.id, editForm.value)
        person.value = res.data
        ElMessage.success('保存成功')
        editDialogVisible.value = false
    } catch (error) {
        console.error('Failed to update person', error)
        ElMessage.error('保存失败')
    } finally {
        saving.value = false
    }
}

onMounted(() => {
    loadData()
})
</script>

<style scoped>
.page-container {
  padding: 20px;
}

.page-title {
  color: var(--nf-text-primary, var(--el-text-color-primary));
}

.person-info-card {
  margin-bottom: 20px;
}

.person-header {
  display: flex;
  gap: 30px;
}

.person-image-section {
  width: 220px;
  flex-shrink: 0;
}

.person-image {
  width: 100%;
  border-radius: 10px;
  aspect-ratio: 2/3;
  background-color: var(--el-fill-color-light);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
}

.image-slot {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
  height: 100%;
  min-height: 300px;
  background: linear-gradient(135deg, var(--el-fill-color-light) 0%, var(--el-fill-color) 100%);
  color: var(--el-text-color-secondary);
  border-radius: 10px;
}

.person-info-section {
  flex: 1;
  min-width: 0;
}

.person-title-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.person-name {
  margin: 0;
  font-size: 28px;
  font-weight: bold;
  color: var(--nf-text-primary, var(--el-text-color-primary));
}

.person-meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  margin-bottom: 16px;
  color: var(--nf-text-secondary, var(--el-text-color-regular));
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 5px;
}

.person-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}

.tag-item {
  border-radius: 6px;
}

.info-block {
  margin-bottom: 14px;
}

.info-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--nf-text-secondary, var(--el-text-color-secondary));
  margin-bottom: 4px;
}

.info-value {
  font-size: 14px;
  color: var(--nf-text-primary, var(--el-text-color-regular));
  line-height: 1.6;
  padding-left: 22px;
}

.person-biography {
  margin-top: 16px;
  line-height: 1.6;
  color: var(--nf-text-primary, var(--el-text-color-regular));
}

.person-biography p {
  white-space: pre-wrap;
  margin: 6px 0;
  padding-left: 22px;
  cursor: pointer;
}

.person-biography p.collapsed {
  display: -webkit-box;
  -webkit-line-clamp: 4;
  line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.person-external-ids {
  margin-top: 20px;
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.external-link {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 8px;
  background: var(--el-fill-color-light);
  transition: background 0.2s, transform 0.2s;
}

.external-link:hover {
  transform: translateY(-1px);
}

.external-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: bold;
  color: #fff;
}

.douban-icon {
  background: linear-gradient(135deg, #41b883, #2d9c5a);
}

.tmdb-icon {
  background: linear-gradient(135deg, #01b4e4, #0d82a8);
}

.imdb-icon {
  background: linear-gradient(135deg, #f5c518, #ddb000);
  color: #000;
}

.homepage-icon {
  background: linear-gradient(135deg, #909399, #606266);
  font-size: 14px;
}

.person-ids {
  margin-top: 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}

.id-item {
  font-size: 12px;
  color: var(--el-text-color-placeholder);
  font-family: 'Courier New', monospace;
}

/* ========== 参演作品部分 ========== */
.credits-section {
  margin-top: 24px;
}

.section-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--nf-text-primary, var(--el-text-color-primary));
  margin: 0 0 16px 0;
}

.credits-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 20px;
}

.credit-card {
  cursor: pointer;
  transition: transform 0.3s ease;
}

.credit-card:hover {
  transform: translateY(-5px);
}

.credit-poster-wrap {
  position: relative;
  border-radius: 8px;
  overflow: hidden;
  margin-bottom: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.credit-poster {
  width: 100%;
  aspect-ratio: 2/3;
}

.poster-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  aspect-ratio: 2/3;
  background: linear-gradient(135deg, var(--el-fill-color-light) 0%, var(--el-fill-color) 100%);
  color: var(--el-text-color-secondary);
}

.credit-rating {
  position: absolute;
  top: 6px;
  right: 6px;
  background: rgba(0, 0, 0, 0.7);
  color: #f7ba2a;
  font-size: 12px;
  font-weight: bold;
  padding: 2px 6px;
  border-radius: 4px;
  backdrop-filter: blur(4px);
}

.credit-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--nf-text-primary, var(--el-text-color-primary));
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.credit-year {
  font-size: 12px;
  color: var(--nf-text-secondary, var(--el-text-color-secondary));
}

.credit-character,
.credit-job {
  font-size: 12px;
  color: var(--nf-text-secondary, var(--el-text-color-regular));
  margin-top: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.no-credits-card {
  margin-top: 24px;
}

/* 排序控件 */
.sort-controls {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  padding: 0 4px;
}

.sort-icon {
  margin-left: 4px;
  font-size: 12px;
}

/* 响应式 */
@media (max-width: 768px) {
  .person-header {
    flex-direction: column;
    align-items: center;
    text-align: center;
  }
  
  .person-image-section {
    width: 160px;
  }
  
  .person-meta-row {
    justify-content: center;
  }

  .person-tags {
    justify-content: center;
  }

  .info-value {
    padding-left: 0;
    text-align: center;
  }

  .person-biography p {
    padding-left: 0;
  }

  .person-external-ids {
    justify-content: center;
  }

  .person-ids {
    justify-content: center;
  }

  .credits-grid {
    grid-template-columns: repeat(auto-fill, minmax(110px, 1fr));
    gap: 12px;
  }
}
</style>
