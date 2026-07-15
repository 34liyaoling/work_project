<template>
  <el-card class="audit-queue" v-loading="loading">
    <template #header>
      <div class="card-header">
        <span>人工审核队列</span>
        <el-tag size="small" type="warning">{{ items.length }} 条待处理</el-tag>
      </div>
    </template>
    <el-empty v-if="!loading && items.length === 0" description="暂无审核任务" />
    <el-timeline v-else>
      <el-timeline-item
        v-for="item in items"
        :key="item.id"
        :timestamp="formatDateTime(item.created_at)"
        :type="statusType(item.status)"
        placement="top"
      >
        <el-card class="audit-card">
          <div class="audit-header">
            <span class="entity-type">{{ entityTypeText(item.entity_type) }}</span>
            <el-tag :type="statusType(item.status)" size="small">{{ statusText(item.status) }}</el-tag>
          </div>
          <div class="entity-id">ID: {{ item.entity_id }}</div>
          <div v-if="item.reason" class="reason">
            <strong>进入原因：</strong>{{ item.reason }}
          </div>
          <div v-if="item.review_comment" class="comment">
            <strong>审核意见：</strong>{{ item.review_comment }}
            <span v-if="item.reviewed_by">（by {{ item.reviewed_by }}）</span>
          </div>
        </el-card>
      </el-timeline-item>
    </el-timeline>
  </el-card>
</template>

<script setup>
import { formatDateTime } from '@/utils/format'

defineProps({
  items: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false }
})

const statusText = (s) => ({ pending: '待审核', approved: '已通过', rejected: '已拒绝' }[s] || s)
const statusType = (s) => ({ pending: 'warning', approved: 'success', rejected: 'danger' }[s] || 'info')
const entityTypeText = (t) => ({ jobrole: '岗位定义', skill: '技能', edge: '关系' }[t] || t)
</script>

<style lang="scss" scoped>
.audit-queue {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-weight: 600;
  }
  .audit-card {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    .audit-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 8px;
    }
    .entity-type { font-weight: 600; }
    .entity-id { color: #94a3b8; font-size: 12px; font-family: monospace; }
    .reason, .comment {
      margin-top: 6px;
      color: #475569;
      font-size: 13px;
    }
  }
}
</style>
