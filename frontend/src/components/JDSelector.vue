<template>
  <div class="jd-selector">
    <el-input
      v-model="keyword"
      placeholder="搜索 JD（按公司/岗位）"
      clearable
      @input="onSearch"
    >
      <template #prefix>
        <el-icon><Search /></el-icon>
      </template>
    </el-input>
    <el-select
      :model-value="modelValue"
      placeholder="选择 JD"
      filterable
      remote
      :remote-method="onSearch"
      :loading="loading"
      style="width: 100%; margin-top: 8px"
      @change="onSelect"
    >
      <el-option
        v-for="jd in jds"
        :key="jd.jd_id"
        :label="`${jd.company} · ${jd.title}`"
        :value="jd.jd_id"
      >
        <span style="float:left">{{ jd.company }} · {{ jd.title }}</span>
        <span style="float:right; color:#94a3b8; font-size:12px">
          {{ jd.salary_range || '-' }}
        </span>
      </el-option>
    </el-select>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { listJds } from '@/api/jd'

const props = defineProps({
  modelValue: { type: String, default: '' }
})
const emit = defineEmits(['update:modelValue'])

const keyword = ref('')
const jds = ref([])
const loading = ref(false)

const onSearch = async (kw) => {
  loading.value = true
  try {
    const data = await listJds({ page: 1, page_size: 30, keyword: kw || '' })
    jds.value = data?.items || []
  } finally {
    loading.value = false
  }
}

const onSelect = (v) => {
  emit('update:modelValue', v)
}

onMounted(() => onSearch(''))
</script>

<style lang="scss" scoped>
.jd-selector {
  width: 100%;
}
</style>
