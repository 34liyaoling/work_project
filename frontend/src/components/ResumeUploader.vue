<template>
  <div
    class="resume-uploader"
    :class="{ 'is-dragover': isDragover }"
    @dragenter.prevent="isDragover = true"
    @dragover.prevent="isDragover = true"
    @dragleave.prevent="isDragover = false"
    @drop.prevent="onDrop"
  >
    <el-upload
      drag
      :auto-upload="false"
      :show-file-list="false"
      :accept="'.pdf,.doc,.docx'"
      :on-change="onChange"
    >
      <el-icon class="upload-icon" size="48"><UploadFilled /></el-icon>
      <div class="upload-text">
        拖拽简历到此处，或<em>点击上传</em>
      </div>
      <template #tip>
        <div class="el-upload__tip">支持 PDF / Word，≤ 10MB</div>
      </template>
    </el-upload>

    <div v-if="uploading" class="progress">
      <el-progress :percentage="progress" :stroke-width="10" />
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { uploadResume } from '@/api/resume'

const emit = defineEmits(['uploaded'])
const isDragover = ref(false)
const uploading = ref(false)
const progress = ref(0)

const onChange = async (file) => {
  if (!file?.raw) return
  if (file.size > 10 * 1024 * 1024) {
    ElMessage.warning('文件大小不能超过 10MB')
    return
  }
  uploading.value = true
  progress.value = 0
  try {
    const data = await uploadResume(file.raw, (p) => { progress.value = p })
    if (data?.resume_id) {
      emit('uploaded', data.resume_id)
    }
  } catch (e) {
    // 拦截器已提示
  } finally {
    uploading.value = false
  }
}

const onDrop = (e) => {
  isDragover.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file) {
    onChange({ raw: file })
  }
}
</script>

<style lang="scss" scoped>
.resume-uploader {
  border-radius: 8px;
  &.is-dragover :deep(.el-upload-dragger) {
    border-color: #5b8def;
    background: #eef4ff;
  }
}

.upload-icon { color: #5b8def; }
.upload-text { color: #475569; margin: 8px 0; }

.progress { margin-top: 12px; }

:deep(.el-upload-dragger) {
  width: 100%;
  padding: 24px 12px;
}
</style>
