<template>
  <el-card class="role-update-list" v-loading="loading">
    <template #header>
      <div class="card-header">
        <span>既有岗位更新</span>
        <el-tag size="small" type="info">{{ roles.length }} 个发生更新</el-tag>
      </div>
    </template>
    <el-empty v-if="!loading && roles.length === 0" description="近期无岗位更新" />
    <el-table v-else :data="roles" stripe>
      <el-table-column prop="name" label="岗位名称" min-width="200" />
      <el-table-column label="类别" width="100">
        <template #default="{ row }">
          <el-tag v-if="row.category" size="small" effect="plain">{{ row.category }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="级别" width="100">
        <template #default="{ row }">
          <el-tag v-if="row.level" size="small" type="info" effect="plain">{{ row.level }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="置信度" width="120">
        <template #default="{ row }">
          {{ formatPercent(row.confidence) }}
        </template>
      </el-table-column>
      <el-table-column label="技能数" width="100">
        <template #default="{ row }">
          {{ (row.required_skills || []).length }} 必备
        </template>
      </el-table-column>
      <el-table-column label="审核状态" width="120">
        <template #default="{ row }">
          <el-tag v-if="row.is_reviewed" type="success" size="small">已审核</el-tag>
          <el-tag v-else type="warning" size="small">未审核</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="更新时间" width="180">
        <template #default="{ row }">
          {{ fromNow(row.updated_at) }}
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup>
import { formatPercent, fromNow } from '@/utils/format'

defineProps({
  roles: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false }
})
</script>

<style lang="scss" scoped>
.role-update-list {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-weight: 600;
  }
}
</style>
