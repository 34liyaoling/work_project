<template>
  <div class="view-switcher">
    <span class="label">视图：</span>
    <el-radio-group v-model="localValue" @change="onChange" size="small">
      <el-radio-button label="default">默认</el-radio-button>
      <el-radio-button label="technology_stack">技术栈</el-radio-button>
      <el-radio-button label="level">级别</el-radio-button>
      <el-radio-button label="domain">领域</el-radio-button>
    </el-radio-group>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: 'default' }
})
const emit = defineEmits(['update:modelValue', 'change'])

const localValue = ref(props.modelValue)

watch(
  () => props.modelValue,
  (v) => { localValue.value = v }
)

const onChange = (v) => {
  emit('update:modelValue', v)
  emit('change', v)
}
</script>

<style lang="scss" scoped>
.view-switcher {
  display: flex;
  align-items: center;
  gap: 8px;
  .label {
    color: #64748b;
    font-size: 13px;
  }
}
</style>
