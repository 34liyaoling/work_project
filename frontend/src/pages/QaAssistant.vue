<template>
  <div class="page-container">
    <div class="page-header">
      <h2>智能问答</h2>
      <p>基于知识图谱与 LLM 的智能问答助手，解答技能发展与行业趋势问题</p>
    </div>

    <div class="qa-layout">
      <div class="qa-main">
        <div class="chat-messages" ref="messagesRef">
          <div
            v-for="(msg, idx) in messages"
            :key="idx"
            class="message-row"
            :class="msg.role"
          >
            <div class="message-bubble" :class="msg.role">
              <div class="message-content">{{ msg.content }}</div>
              <div class="message-time">{{ msg.time }}</div>
            </div>
          </div>
          <div v-if="loading" class="message-row assistant">
            <div class="message-bubble assistant">
              <div class="typing-indicator">
                <span></span><span></span><span></span>
              </div>
            </div>
          </div>
        </div>

        <div class="chat-input-area">
          <el-input
            v-model="inputText"
            type="textarea"
            :rows="2"
            placeholder="输入您的问题..."
            resize="none"
            @keydown.enter.prevent="sendMessage"
          />
          <el-button type="primary" :loading="loading" @click="sendMessage" class="send-btn">
            <el-icon><Promotion /></el-icon>
            发送
          </el-button>
        </div>
      </div>

      <div class="qa-sidebar">
        <el-card shadow="never" class="preset-card">
          <template #header>
            <div class="card-header">
              <span>快速提问</span>
            </div>
          </template>
          <div class="preset-list">
            <el-button
              v-for="(q, idx) in presetQuestions"
              :key="idx"
              size="small"
              class="preset-btn"
              @click="usePreset(q)"
            >
              {{ q }}
            </el-button>
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import api from '../api'

const messages = ref([
  {
    role: 'assistant',
    content: '您好！我是智能问答助手，可以为您解答技能发展、行业趋势、岗位要求等问题。请问有什么可以帮您的？',
    time: formatTime(new Date())
  }
])

const inputText = ref('')
const loading = ref(false)
const messagesRef = ref(null)

const presetQuestions = [
  '当前热门技能有哪些？',
  '如何从Java转AI？',
  'IT行业发展趋势？',
  '未来五年最有前景的技术领域',
  '学习AI需要什么基础？',
  '哪些技能薪资增长最快？'
]

function formatTime(d) {
  const h = String(d.getHours()).padStart(2, '0')
  const m = String(d.getMinutes()).padStart(2, '0')
  return `${h}:${m}`
}

function _fallbackReply(question) {
  return `关于「${question}」的问题：\n\n我正在连接知识图谱系统获取最新数据。如果回答不够详细，请确认后端服务已启动并执行了图谱初始化。\n\n您可以尝试：\n1. 访问「管理面板」检查系统状态\n2. 点击「初始化图谱」加载示例数据\n3. 再回来提问`
}

function usePreset(q) {
  inputText.value = q
}

async function sendMessage() {
  const text = inputText.value.trim()
  if (!text || loading.value) return

  messages.value.push({
    role: 'user',
    content: text,
    time: formatTime(new Date())
  })
  inputText.value = ''
  loading.value = true

  scrollToBottom()

  try {
    const res = await api.askQA(text)
    const answer = res?.data?.answer || res?.answer || ''

    setTimeout(() => {
      messages.value.push({
        role: 'assistant',
        content: answer || _fallbackReply(text),
        time: formatTime(new Date())
      })
      loading.value = false
      scrollToBottom()
    }, 400)
  } catch (err) {
    setTimeout(() => {
      messages.value.push({
        role: 'assistant',
        content: _fallbackReply(text),
        time: formatTime(new Date())
      })
      loading.value = false
      scrollToBottom()
    }, 400)
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  })
}
</script>

<style scoped>
.qa-layout {
  display: flex;
  gap: 16px;
  height: calc(100vh - 220px);
  min-height: 500px;
}

.qa-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 8px;
  border: 1px solid var(--border-color);
  overflow: hidden;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.message-row {
  display: flex;
}

.message-row.user {
  justify-content: flex-end;
}

.message-row.assistant {
  justify-content: flex-start;
}

.message-bubble {
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 12px;
  position: relative;
  word-break: break-word;
  line-height: 1.6;
  font-size: 14px;
}

.message-bubble.user {
  background: #409eff;
  color: #fff;
  border-bottom-right-radius: 4px;
}

.message-bubble.assistant {
  background: #f5f7fa;
  color: var(--text-primary);
  border-bottom-left-radius: 4px;
}

.message-content {
  white-space: pre-wrap;
}

.message-time {
  font-size: 11px;
  margin-top: 4px;
  opacity: 0.7;
}

.message-bubble.user .message-time {
  text-align: right;
  color: rgba(255, 255, 255, 0.8);
}

.message-bubble.assistant .message-time {
  color: var(--text-muted);
}

.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 4px 0;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #c0c4cc;
  animation: typing 1.4s infinite ease-in-out;
}

.typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 60%, 100% {
    transform: translateY(0);
    opacity: 0.4;
  }
  30% {
    transform: translateY(-6px);
    opacity: 1;
  }
}

.chat-input-area {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  padding: 12px 16px;
  border-top: 1px solid var(--border-color);
  background: #fafafa;
}

.chat-input-area .el-textarea__inner {
  border-radius: 8px;
}

.send-btn {
  height: 56px;
  min-width: 90px;
  flex-shrink: 0;
}

.qa-sidebar {
  width: 240px;
  flex-shrink: 0;
}

.preset-card {
  border-radius: 8px;
  border: 1px solid var(--border-color);
}

.card-header {
  font-weight: 600;
  font-size: 15px;
}

.preset-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.preset-btn {
  width: 100%;
  text-align: left;
  justify-content: flex-start;
  white-space: normal;
  height: auto;
  line-height: 1.4;
  padding: 8px 12px;
  border-radius: 6px;
}
</style>
