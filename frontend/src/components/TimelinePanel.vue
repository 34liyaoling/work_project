<template>
  <el-card class="timeline-panel" v-loading="loading">
    <template #header>
      <div class="card-header">
        <span>技能变化时间线</span>
        <el-tag v-if="skillName" size="small" type="info">{{ skillName }}</el-tag>
      </div>
    </template>
    <div v-if="!skillName" class="empty">
      <el-empty description="点击图谱中的节点查看时间线" :image-size="80" />
    </div>
    <div v-else-if="timeline.length === 0" class="empty">
      <el-empty description="暂无该技能的变化记录" :image-size="80" />
    </div>
    <el-timeline v-else>
      <el-timeline-item
        v-for="(item, idx) in timeline"
        :key="idx"
        :timestamp="formatDate(item.date)"
        :type="iconType(item.change_type)"
        :hollow="idx !== 0"
        placement="top"
      >
        <div class="event-title">{{ eventTitle(item.change_type) }}: {{ item.skill_name || skillName }}</div>
        <div class="event-detail" v-if="item.change_detail">
          <span v-for="(v, k) in item.change_detail" :key="k" class="detail-chip">
            {{ k }}: {{ v }}
          </span>
        </div>
        <div class="event-confidence">
          置信度: <el-progress :percentage="Math.round((item.confidence || 0) * 100)" :stroke-width="6" />
        </div>
      </el-timeline-item>
    </el-timeline>
  </el-card>
</template>

<script setup>
import { computed } from 'vue'
import { formatDateTime } from '@/utils/format'

const props = defineProps({
  skillName: { type: String, default: '' },
  timeline: { type: Array, default: () => [] }
})

const loading = computed(() => false)

const formatDate = (d) => formatDateTime(d, 'YYYY-MM-DD HH:mm')

const eventTitle = (type) => {
  return {
    added: '新增',
    removed: '移除',
    weight_changed: '权重变化',
    usage_changed: '热度变化'
  }[type] || type
}

const iconType = (type) => {
  return {
    added: 'success',
    removed: 'danger',
    weight_changed: 'warning',
    usage_changed: 'primary'
  }[type] || 'info'
}
</script>

<style lang="scss" scoped>
.timeline-panel {
  height: 720px;
  overflow-y: auto;
  :deep(.el-card__body) { padding: 16px; }
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.empty {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 80%;
}

.event-title {
  font-weight: 600;
  margin-bottom: 4px;
}

.event-detail {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 6px 0;
  .detail-chip {
    background: #eef2ff;
    color: #3730a3;
    border-radius: 4px;
    padding: 2px 6px;
    font-size: 12px;
  }
}

.event-confidence {
  margin-top: 6px;
  font-size: 12px;
  color: #64748b;
}
</style>
