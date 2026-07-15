<template>
  <el-card class="learning-path">
    <template #header>
      <div class="card-header">
        <span>学习路径建议</span>
      </div>
    </template>

    <div v-if="recommendations?.length" class="recs">
      <h4>推荐学习内容</h4>
      <ul>
        <li v-for="(r, i) in recommendations" :key="i">
          <el-icon><Reading /></el-icon>
          <span>{{ r }}</span>
        </li>
      </ul>
    </div>

    <el-empty v-if="!path?.length && !recommendations?.length" description="暂无学习路径" />

    <div v-if="path?.length" class="path">
      <h4>推荐学习顺序</h4>
      <el-steps direction="vertical" :active="path.length">
        <el-step
          v-for="(p, i) in path"
          :key="i"
          :title="p.title || p.skill || `第 ${i + 1} 步`"
          :description="p.description || p.detail"
        />
      </el-steps>
    </div>
  </el-card>
</template>

<script setup>
defineProps({
  path: { type: Array, default: () => [] },
  recommendations: { type: Array, default: () => [] }
})
</script>

<style lang="scss" scoped>
.learning-path {
  .card-header { font-weight: 600; }
  h4 { color: #1e3a8a; margin: 0 0 8px; }
  .recs {
    margin-bottom: 16px;
    ul {
      list-style: none;
      padding: 0;
      margin: 0;
      li {
        display: flex;
        align-items: flex-start;
        gap: 6px;
        padding: 6px 0;
        color: #475569;
        .el-icon { color: #5b8def; margin-top: 3px; }
      }
    }
  }
  .path {
    :deep(.el-step__title) { font-size: 14px; }
  }
}
</style>
