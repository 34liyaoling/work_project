<template>
  <el-card class="new-role-list" v-loading="loading">
    <template #header>
      <div class="card-header">
        <span>新岗位发现结果</span>
        <el-tag size="small" type="warning">{{ roles.length }} 个待审核</el-tag>
      </div>
    </template>
    <el-empty v-if="!loading && roles.length === 0" description="暂无新岗位发现" />
    <el-row v-else :gutter="16">
      <el-col v-for="r in roles" :key="r.role_id" :span="8" class="role-col">
        <el-card shadow="hover" class="mini-card">
          <div class="card-top">
            <div class="title">{{ r.name }}</div>
            <el-tag size="small" :type="confidenceTag(r.confidence)">
              置信度 {{ formatPercent(r.confidence) }}
            </el-tag>
          </div>
          <div class="meta">
            <el-tag v-if="r.category" size="small" effect="plain">{{ r.category }}</el-tag>
            <el-tag v-if="r.level" size="small" type="info" effect="plain">{{ r.level }}</el-tag>
          </div>
          <div class="responsibilities">
            <div v-for="(t, i) in (r.core_responsibilities || []).slice(0, 2)" :key="i" class="resp">
              • {{ t }}
            </div>
            <div v-if="(r.core_responsibilities || []).length > 2" class="more">
              +{{ r.core_responsibilities.length - 2 }} 项...
            </div>
          </div>
          <div class="skills">
            <el-tag
              v-for="s in (r.required_skills || []).slice(0, 4)"
              :key="s.name"
              type="primary"
              size="small"
              effect="light"
            >{{ s.name }}</el-tag>
          </div>
          <el-button type="primary" size="small" class="action-btn" @click="$emit('review', r)">
            <el-icon><EditPen /></el-icon>
            <span>审核</span>
          </el-button>
        </el-card>
      </el-col>
    </el-row>
  </el-card>
</template>

<script setup>
import { formatPercent } from '@/utils/format'

defineProps({
  roles: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false }
})
defineEmits(['review'])

const confidenceTag = (c) => {
  if (c >= 0.85) return 'success'
  if (c >= 0.7) return 'primary'
  if (c >= 0.5) return 'warning'
  return 'danger'
}
</script>

<style lang="scss" scoped>
.new-role-list {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-weight: 600;
  }
  .role-col { margin-bottom: 16px; }
  .mini-card {
    height: 240px;
    display: flex;
    flex-direction: column;
    border: 1px solid #e2e8f0;
    .card-top {
      display: flex;
      justify-content: space-between;
      align-items: center;
      .title { font-weight: 700; font-size: 15px; }
    }
    .meta {
      display: flex;
      gap: 6px;
      margin: 8px 0;
    }
    .responsibilities {
      color: #475569;
      font-size: 12px;
      line-height: 1.6;
      flex: 1;
      .more { color: #94a3b8; }
    }
    .skills {
      display: flex;
      flex-wrap: wrap;
      gap: 4px;
      margin: 8px 0;
    }
    .action-btn { align-self: stretch; margin-top: auto; }
  }
}
</style>
