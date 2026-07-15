<template>
  <div class="role-view">
    <!-- 控制栏 -->
    <el-card class="control-bar">
      <div class="control-inner">
        <el-radio-group v-model="activeTab" @change="onTabChange">
          <el-radio-button label="new">
            新岗位发现
            <el-badge v-if="store.newRoles.length" :value="store.newRoles.length" class="tab-badge" />
          </el-radio-button>
          <el-radio-button label="update">既有岗位更新</el-radio-button>
          <el-radio-button label="audit">审核队列</el-radio-button>
        </el-radio-group>
        <div class="right-tools">
          <el-button @click="triggerDiscover" :loading="discovering">
            <el-icon><MagicStick /></el-icon>
            <span>触发发现</span>
          </el-button>
          <el-button @click="reload" :loading="store.loading">
            <el-icon><Refresh /></el-icon>
            <span>刷新</span>
          </el-button>
        </div>
      </div>
    </el-card>

    <!-- 内容区 -->
    <NewRoleList
      v-show="activeTab === 'new'"
      :roles="store.newRoles"
      :loading="store.loading"
      @review="openAuditDialog"
    />
    <RoleUpdateList
      v-show="activeTab === 'update'"
      :roles="store.updatedRoles"
      :loading="store.loading"
    />
    <AuditQueue
      v-show="activeTab === 'audit'"
      :items="store.auditQueue"
      :loading="store.loading"
    />

    <!-- 审核弹窗 -->
    <el-dialog v-model="auditDialogVisible" title="岗位审核" width="640px">
      <RoleCard v-if="currentRole" :role="currentRole" />
      <el-form label-position="top" style="margin-top: 16px">
        <el-form-item label="审核备注">
          <el-input v-model="auditComment" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="审核人">
          <el-input v-model="reviewer" placeholder="您的姓名或 ID" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="auditDialogVisible = false">取消</el-button>
        <el-button type="danger" :loading="acting" @click="doReview('reject')">
          拒绝
        </el-button>
        <el-button type="warning" :loading="acting" @click="doReview('modify')">
          修改
        </el-button>
        <el-button type="success" :loading="acting" @click="doReview('approve')">
          通过
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useRoleStore } from '@/stores/role'
import NewRoleList from '@/components/NewRoleList.vue'
import RoleUpdateList from '@/components/RoleUpdateList.vue'
import AuditQueue from '@/components/AuditQueue.vue'
import RoleCard from '@/components/RoleCard.vue'

const store = useRoleStore()
const activeTab = ref('new')
const discovering = ref(false)
const auditDialogVisible = ref(false)
const currentRole = ref(null)
const auditComment = ref('')
const reviewer = ref('admin')
const acting = ref(false)

const onTabChange = (t) => {
  reload()
}

const reload = () => {
  if (activeTab.value === 'new') {
    store.loadNewRoles({ page: 1, page_size: 30 })
  } else if (activeTab.value === 'update') {
    store.loadUpdates({ page: 1, page_size: 30, days: 7 })
  } else if (activeTab.value === 'audit') {
    store.loadAuditQueue({ page: 1, page_size: 30 })
  }
}

const triggerDiscover = async () => {
  discovering.value = true
  try {
    const data = await store.triggerJobDiscovery({ days: 30, min_source_count: 3 })
    ElMessage.success(`岗位发现任务已启动: ${data.task_id}`)
    setTimeout(reload, 2000)
  } catch (e) {
    // ignore
  } finally {
    discovering.value = false
  }
}

const openAuditDialog = (role) => {
  currentRole.value = role
  auditComment.value = ''
  auditDialogVisible.value = true
}

const doReview = async (action) => {
  acting.value = true
  try {
    await store.doReview(currentRole.value.role_id, {
      action,
      reviewer: reviewer.value,
      comment: auditComment.value
    })
    ElMessage.success(`已${action === 'approve' ? '通过' : action === 'reject' ? '拒绝' : '修改'}`)
    auditDialogVisible.value = false
  } catch (e) {
    // 拦截器已提示
  } finally {
    acting.value = false
  }
}

onMounted(reload)
</script>

<style lang="scss" scoped>
.role-view {
  max-width: 1400px;
  margin: 0 auto;
}

.control-bar {
  margin-bottom: 16px;
  .control-inner {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .right-tools {
    display: flex;
    gap: 8px;
  }
  .tab-badge {
    margin-left: 4px;
  }
}
</style>
