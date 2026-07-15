<template>
  <div class="role-card">
    <div class="header">
      <h3 class="name">{{ role.name }}</h3>
      <el-tag :type="confidenceType" size="default">
        置信度 {{ formatPercent(role.confidence) }}
      </el-tag>
    </div>

    <div class="meta">
      <el-tag v-if="role.category" size="small" effect="plain">{{ role.category }}</el-tag>
      <el-tag v-if="role.level" size="small" type="info" effect="plain">{{ role.level }}</el-tag>
      <el-tag v-if="role.is_new" size="small" type="warning">新岗位</el-tag>
    </div>

    <el-divider content-position="left">核心职责</el-divider>
    <ul class="responsibilities">
      <li v-for="(t, i) in role.core_responsibilities || []" :key="i">{{ t }}</li>
    </ul>

    <el-divider content-position="left">必备技能</el-divider>
    <div class="skills">
      <el-tag
        v-for="s in role.required_skills || []"
        :key="s.name"
        type="primary"
        effect="light"
        style="margin: 2px"
      >
        {{ s.name }}
        <span v-if="s.weight" class="weight">{{ (s.weight * 100).toFixed(0) }}%</span>
      </el-tag>
    </div>

    <template v-if="role.preferred_skills?.length">
      <el-divider content-position="left">加分技能</el-divider>
      <div class="skills">
        <el-tag
          v-for="s in role.preferred_skills"
          :key="s.name"
          type="success"
          effect="light"
          style="margin: 2px"
        >{{ s.name }}</el-tag>
      </div>
    </template>

    <template v-if="role.typical_scenarios?.length">
      <el-divider content-position="left">典型场景</el-divider>
      <ul class="scenarios">
        <li v-for="(t, i) in role.typical_scenarios" :key="i">{{ t }}</li>
      </ul>
    </template>

    <el-divider content-position="left">证据来源</el-divider>
    <div class="sources">
      <el-tag
        v-for="(src, i) in role.evidence_sources || []"
        :key="i"
        size="small"
        type="info"
        effect="plain"
        style="margin: 2px"
      >{{ src }}</el-tag>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { formatPercent } from '@/utils/format'

const props = defineProps({
  role: { type: Object, required: true }
})

const confidenceType = computed(() => {
  const c = props.role.confidence || 0
  if (c >= 0.85) return 'success'
  if (c >= 0.7) return 'primary'
  if (c >= 0.5) return 'warning'
  return 'danger'
})
</script>

<style lang="scss" scoped>
.role-card {
  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    .name { margin: 0; }
  }
  .meta {
    display: flex;
    gap: 6px;
    margin-top: 8px;
  }
  .responsibilities, .scenarios {
    color: #475569;
    line-height: 1.7;
    padding-left: 20px;
    margin: 0;
  }
  .weight {
    color: #94a3b8;
    font-size: 11px;
    margin-left: 4px;
  }
  .sources {
    display: flex;
    flex-wrap: wrap;
  }
}
</style>
