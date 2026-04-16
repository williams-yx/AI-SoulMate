<template>
  <!-- 按旧版 tpl-workflow 完全还原 -->
  <div class="page-transition min-h-[70vh] md:min-h-[80vh] relative flex flex-col">
    <!-- 顶部工具栏 -->
    <div class="flex justify-between items-center mb-4 shrink-0 px-1">
      <div class="flex gap-4 items-center">
        <div>
          <h2 class="font-bold text-lg">L3-Final: 多模态交互逻辑</h2>
          <div class="text-xs text-slate-500 flex items-center gap-2">
            <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span id="save-status">实时保存中...</span>
          </div>
        </div>
      </div>
      <div class="flex gap-2 items-center">
        <div class="bg-slate-800 p-1 rounded-lg border border-slate-700 shadow-xl flex gap-1">
          <button class="px-3 py-1 bg-slate-700 hover:bg-slate-600 text-white text-xs font-bold rounded flex items-center gap-2" type="button" @click="openPalette = true" title="添加节点">
            <i data-lucide="plus" class="w-3 h-3"></i> 添加节点
          </button>
          <button class="px-3 py-1 bg-slate-700 hover:bg-slate-600 text-white text-xs font-bold rounded flex items-center gap-2" type="button" @click="clearWorkflow" title="清空画布">
            <i data-lucide="trash-2" class="w-3 h-3"></i> 清空
          </button>
          <button class="px-3 py-1 bg-slate-700 hover:bg-slate-600 text-white text-xs font-bold rounded flex items-center gap-2" type="button" @click="saveWorkflow" title="保存工作流">
            <i data-lucide="save" class="w-3 h-3"></i> 保存
          </button>
          <button class="px-3 py-1 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold rounded flex items-center gap-2" type="button" @click="executeWorkflow" title="运行工作流">
            <i data-lucide="play" class="w-3 h-3"></i> 运行全流
          </button>
        </div>
      </div>
    </div>

    <!-- 中间区域：画布 + 右侧配置面板 -->
    <div class="flex-1 border border-slate-700 rounded-xl relative overflow-hidden flex shadow-2xl bg-[#111827]">
      <!-- 节点库（左侧悬浮面板） -->
      <div v-if="openPalette" class="absolute left-4 top-4 z-30 glass-panel p-4 rounded-xl border border-slate-700 w-64 max-h-[80vh] overflow-y-auto shadow-2xl">
        <div class="flex justify-between items-center mb-4">
          <h3 class="font-bold text-sm">节点库</h3>
          <button class="text-slate-400 hover:text-white" type="button" @click="openPalette = false">
            <i data-lucide="x" class="w-4 h-4"></i>
          </button>
        </div>
        <div class="space-y-3 text-sm">
          <div class="text-xs font-bold text-slate-500 uppercase mb-2">输入节点</div>
          <button
            class="w-full text-left px-3 py-2 rounded-xl bg-slate-800/90 hover:bg-slate-700 border border-emerald-500/40 hover:border-emerald-400 flex items-center justify-between gap-2 transition"
            type="button"
            @click="addNode('start', '开始 (Start)', 'play', 'emerald')"
          >
            <span class="flex items-center gap-2">
              <span class="w-7 h-7 rounded-full bg-emerald-500/15 border border-emerald-500/50 flex items-center justify-center">
                <i data-lucide="play" class="w-4 h-4 text-emerald-400"></i>
              </span>
              <span class="flex flex-col">
                <span class="font-bold text-slate-50">开始节点</span>
                <span class="text-[11px] text-slate-400">工作流入口</span>
              </span>
            </span>
            <span class="text-[11px] text-emerald-300 font-mono">IN</span>
          </button>
          <button
            class="w-full text-left px-3 py-2 rounded-xl bg-slate-800/90 hover:bg-slate-700 border border-emerald-500/30 flex items-center justify-between gap-2 transition"
            type="button"
            @click="addNode('camera', '摄像头', 'camera', 'emerald')"
          >
            <span class="flex items-center gap-2">
              <span class="w-7 h-7 rounded-full bg-emerald-500/10 border border-emerald-500/40 flex items-center justify-center">
                <i data-lucide="camera" class="w-4 h-4 text-emerald-300"></i>
              </span>
              <span class="flex flex-col">
                <span class="font-bold text-slate-50">摄像头</span>
                <span class="text-[11px] text-slate-400">图像 / 视频输入</span>
              </span>
            </span>
            <span class="text-[11px] text-emerald-300 font-mono">IN</span>
          </button>
          <button
            class="w-full text-left px-3 py-2 rounded-xl bg-slate-800/90 hover:bg-slate-700 border border-emerald-500/30 flex items-center justify-between gap-2 transition"
            type="button"
            @click="addNode('sensor', '传感器', 'wifi', 'emerald')"
          >
            <span class="flex items-center gap-2">
              <span class="w-7 h-7 rounded-full bg-emerald-500/10 border border-emerald-500/40 flex items-center justify-center">
                <i data-lucide="wifi" class="w-4 h-4 text-emerald-300"></i>
              </span>
              <span class="flex flex-col">
                <span class="font-bold text-slate-50">传感器</span>
                <span class="text-[11px] text-slate-400">硬件信号输入</span>
              </span>
            </span>
            <span class="text-[11px] text-emerald-300 font-mono">IN</span>
          </button>

          <div class="text-xs font-bold text-slate-500 uppercase mb-2 mt-4">处理节点</div>
          <button
            class="w-full text-left px-3 py-2 rounded-xl bg-slate-800/90 hover:bg-slate-700 border border-slate-600 flex items-center justify-between gap-2 transition"
            type="button"
            @click="addNode('prompt', '提示词', 'user', 'slate')"
          >
            <span class="flex items-center gap-2">
              <span class="w-7 h-7 rounded-full bg-slate-500/15 border border-slate-400/40 flex items-center justify-center">
                <i data-lucide="user" class="w-4 h-4 text-slate-200"></i>
              </span>
              <span class="flex flex-col">
                <span class="font-bold text-slate-50">提示词处理</span>
                <span class="text-[11px] text-slate-400">拼接 / 清洗文本</span>
              </span>
            </span>
            <span class="text-[11px] text-slate-300 font-mono">PROC</span>
          </button>
          <button
            class="w-full text-left px-3 py-2 rounded-xl bg-slate-800/90 hover:bg-slate-700 border border-indigo-500/40 flex items-center justify-between gap-2 transition"
            type="button"
            @click="addNode('llm', 'LLM推理', 'cpu', 'indigo')"
          >
            <span class="flex items-center gap-2">
              <span class="w-7 h-7 rounded-full bg-indigo-500/15 border border-indigo-400/50 flex items-center justify-center">
                <i data-lucide="cpu" class="w-4 h-4 text-indigo-300"></i>
              </span>
              <span class="flex flex-col">
                <span class="font-bold text-slate-50">LLM 推理</span>
                <span class="text-[11px] text-slate-400">对话 / 决策中枢</span>
              </span>
            </span>
            <span class="text-[11px] text-indigo-300 font-mono">LLM</span>
          </button>
          <button
            class="w-full text-left px-3 py-2 rounded-xl bg-slate-800/90 hover:bg-slate-700 border border-pink-500/40 flex items-center justify-between gap-2 transition"
            type="button"
            @click="addNode('mcp', 'MCP工具', 'heart', 'pink')"
          >
            <span class="flex items-center gap-2">
              <span class="w-7 h-7 rounded-full bg-pink-500/15 border border-pink-400/50 flex items-center justify-center">
                <i data-lucide="heart" class="w-4 h-4 text-pink-300"></i>
              </span>
              <span class="flex flex-col">
                <span class="font-bold text-slate-50">MCP 工具</span>
                <span class="text-[11px] text-slate-400">外部工具调用</span>
              </span>
            </span>
            <span class="text-[11px] text-pink-300 font-mono">MCP</span>
          </button>
          <button
            class="w-full text-left px-3 py-2 rounded-xl bg-slate-800/90 hover:bg-slate-700 border border-cyan-500/40 flex items-center justify-between gap-2 transition"
            type="button"
            @click="addNode('logic', '逻辑判断', 'git-branch', 'cyan')"
          >
            <span class="flex items-center gap-2">
              <span class="w-7 h-7 rounded-full bg-cyan-500/15 border border-cyan-400/50 flex items-center justify-center">
                <i data-lucide="git-branch" class="w-4 h-4 text-cyan-300"></i>
              </span>
              <span class="flex flex-col">
                <span class="font-bold text-slate-50">逻辑判断</span>
                <span class="text-[11px] text-slate-400">条件分支 / 路由</span>
              </span>
            </span>
            <span class="text-[11px] text-cyan-300 font-mono">IF</span>
          </button>

          <div class="text-xs font-bold text-slate-500 uppercase mb-2 mt-4">输出节点</div>
          <button
            class="w-full text-left px-3 py-2 rounded-xl bg-slate-800/90 hover:bg-slate-700 border border-slate-500/40 flex items-center justify-between gap-2 transition"
            type="button"
            @click="addNode('end', '结束', 'square', 'slate')"
          >
            <span class="flex items-center gap-2">
              <span class="w-7 h-7 rounded-full bg-slate-500/15 border border-slate-400/50 flex items-center justify-center">
                <i data-lucide="square" class="w-4 h-4 text-slate-300"></i>
              </span>
              <span class="flex flex-col">
                <span class="font-bold text-slate-50">结束节点</span>
                <span class="text-[11px] text-slate-400">工作流终点</span>
              </span>
            </span>
            <span class="text-[11px] text-slate-300 font-mono">OUT</span>
          </button>
          <button
            class="w-full text-left px-3 py-2 rounded-xl bg-slate-800/90 hover:bg-slate-700 border border-slate-500/40 flex items-center justify-between gap-2 transition"
            type="button"
            @click="addNode('tts', '语音输出', 'mic', 'slate')"
          >
            <span class="flex items-center gap-2">
              <span class="w-7 h-7 rounded-full bg-slate-500/15 border border-slate-400/50 flex items-center justify-center">
                <i data-lucide="mic" class="w-4 h-4 text-slate-300"></i>
              </span>
              <span class="flex flex-col">
                <span class="font-bold text-slate-50">语音输出</span>
                <span class="text-[11px] text-slate-400">TTS 语音播报</span>
              </span>
            </span>
            <span class="text-[11px] text-slate-300 font-mono">OUT</span>
          </button>
          <button
            class="w-full text-left px-3 py-2 rounded-xl bg-slate-800/90 hover:bg-slate-700 border border-slate-500/40 flex items-center justify-between gap-2 transition"
            type="button"
            @click="addNode('ui', '界面反馈', 'monitor', 'slate')"
          >
            <span class="flex items-center gap-2">
              <span class="w-7 h-7 rounded-full bg-slate-500/15 border border-slate-400/50 flex items-center justify-center">
                <i data-lucide="monitor" class="w-4 h-4 text-slate-300"></i>
              </span>
              <span class="flex flex-col">
                <span class="font-bold text-slate-50">界面反馈</span>
                <span class="text-[11px] text-slate-400">在屏幕上显示结果</span>
              </span>
            </span>
            <span class="text-[11px] text-slate-300 font-mono">OUT</span>
          </button>
        </div>
      </div>

      <!-- 画布容器 -->
      <div class="flex-1 node-canvas relative z-0 w-full h-full" id="canvas-container" @click="closeWorkflowPanel(); closeNodePalette();">
        <svg id="cable-layer" class="absolute top-0 left-0 w-[2500px] h-[2500px] pointer-events-none z-0"></svg>
        <div id="nodes-layer" class="w-[2500px] h-[2500px] relative z-10"></div>
      </div>

      <!-- 右侧配置面板（动态宽度） -->
      <div id="wf-config-panel" class="w-0 bg-slate-800 border-l-0 border-slate-700 flex flex-col z-20 transition-all duration-300 ease-in-out overflow-hidden h-full absolute right-0 top-0 shadow-2xl"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'

declare const lucide: any

type NodeColor = 'emerald' | 'indigo' | 'slate' | 'pink' | 'orange' | 'cyan' | 'red'
type WFNode = {
  id: string
  type: string
  title: string
  x: number
  y: number
  color: NodeColor
  icon: string
}
type Connection = { f: string; t: string }

const STORAGE_KEY = 'workflow_draft'

let workflowState: { nodes: WFNode[]; connections: Connection[]; nodeCounter: number } = {
  nodes: [],
  connections: [],
  nodeCounter: 0
}

let workflowDragState: {
  dragEl: HTMLElement | null
  offset: { x: number; y: number }
  connecting: boolean
  sourceHandle: string | null
  sourceNode: string | null
  tempPath: SVGPathElement | null
} = {
  dragEl: null,
  offset: { x: 0, y: 0 },
  connecting: false,
  sourceHandle: null,
  sourceNode: null,
  tempPath: null
}

const openPalette = ref(false)

const colors: Record<NodeColor, string> = {
  emerald: 'text-emerald-400 bg-emerald-900/30',
  indigo: 'text-indigo-400 bg-indigo-900/30',
  slate: 'text-slate-300 bg-slate-700/50',
  pink: 'text-pink-400 bg-pink-900/30',
  orange: 'text-orange-400 bg-orange-900/30',
  cyan: 'text-cyan-400 bg-cyan-900/30',
  red: 'text-red-400 bg-red-900/30'
}

function renderIcons() {
  if (typeof lucide !== 'undefined' && lucide?.createIcons) {
    lucide.createIcons()
  }
}

function initWorkflowSystem() {
  const container = document.getElementById('canvas-container')
  const nodesLayer = document.getElementById('nodes-layer')
  const svgLayer = document.getElementById('cable-layer')

  if (!container || !nodesLayer || !svgLayer) return

  // 初始化默认节点（如果为空）
  if (workflowState.nodes.length === 0) {
    workflowState.nodes = [
      { id: 'n1', type: 'start', title: '开始 (Start)', x: 50, y: 100, color: 'emerald', icon: 'play' },
      { id: 'n2', type: 'prompt', title: '角色设定 (Prompt)', x: 350, y: 100, color: 'slate', icon: 'user' },
      { id: 'n3', type: 'llm', title: 'LLM (Reasoning)', x: 650, y: 80, color: 'indigo', icon: 'cpu' },
      { id: 'n4', type: 'mcp', title: '情感分析 (MCP)', x: 950, y: 100, color: 'pink', icon: 'heart' },
      { id: 'n5', type: 'end', title: '语音 (TTS)', x: 1250, y: 100, color: 'slate', icon: 'mic' }
    ]
    workflowState.connections = [
      { f: 'n1', t: 'n2' },
      { f: 'n2', t: 'n3' },
      { f: 'n3', t: 'n4' },
      { f: 'n4', t: 'n5' }
    ]
    workflowState.nodeCounter = 5
  }

  renderWorkflow()

  // 全局拖动和连线事件
  document.addEventListener('mousemove', onWorkflowMouseMove)
  document.addEventListener('mouseup', onWorkflowMouseUp)
}

function startNodeDrag(e: MouseEvent, el: HTMLElement) {
  const container = document.getElementById('canvas-container')
  if (!container) return

  workflowDragState.dragEl = el
  const rect = container.getBoundingClientRect()
  const nodeRect = el.getBoundingClientRect()
  workflowDragState.offset = {
    x: e.clientX - nodeRect.left,
    y: e.clientY - nodeRect.top
  }
  el.style.cursor = 'grabbing'
}

function startConnection(e: MouseEvent, nodeId: string, handleType: string) {
  e.stopPropagation()
  const svgLayer = document.getElementById('cable-layer')
  if (!svgLayer) return

  workflowDragState.connecting = true
  workflowDragState.sourceNode = nodeId
  workflowDragState.sourceHandle = handleType

  workflowDragState.tempPath = document.createElementNS('http://www.w3.org/2000/svg', 'path')
  workflowDragState.tempPath.setAttribute('class', 'temp-connection')
  workflowDragState.tempPath.setAttribute('stroke', '#10b981')
  workflowDragState.tempPath.setAttribute('stroke-width', '2')
  workflowDragState.tempPath.setAttribute('fill', 'none')
  svgLayer.appendChild(workflowDragState.tempPath)
}

function onWorkflowMouseMove(e: MouseEvent) {
  const container = document.getElementById('canvas-container')
  if (!container) return

  const containerRect = container.getBoundingClientRect()

  if (workflowDragState.dragEl && !workflowDragState.connecting) {
    let x = e.clientX - containerRect.left - workflowDragState.offset.x + container.scrollLeft
    let y = e.clientY - containerRect.top - workflowDragState.offset.y + container.scrollTop

    workflowDragState.dragEl.style.left = x + 'px'
    workflowDragState.dragEl.style.top = y + 'px'

    const nodeId = workflowDragState.dragEl.dataset.id
    const node = workflowState.nodes.find((n) => n.id === nodeId)
    if (node) {
      node.x = x
      node.y = y
    }

    requestAnimationFrame(drawWorkflowLines)
  }

  if (workflowDragState.connecting && workflowDragState.tempPath) {
    const sourceNode = document.querySelector(`[data-id="${workflowDragState.sourceNode}"]`) as HTMLElement
    if (sourceNode && workflowDragState.tempPath) {
      const sourceRect = sourceNode.getBoundingClientRect()
      const sx = sourceRect.left + sourceRect.width - containerRect.left + container.scrollLeft
      const sy = sourceRect.top + sourceRect.height / 2 - containerRect.top + container.scrollTop
      const tx = e.clientX - containerRect.left + container.scrollLeft
      const ty = e.clientY - containerRect.top + container.scrollTop
      const dx = Math.max(80, (tx - sx) / 2)
      const d = `M ${sx} ${sy} C ${sx + dx} ${sy}, ${tx - dx} ${ty}, ${tx} ${ty}`
      workflowDragState.tempPath.setAttribute('d', d)
    }
  }
}

function onWorkflowMouseUp(e: MouseEvent) {
  if (workflowDragState.dragEl && !workflowDragState.connecting) {
    workflowDragState.dragEl.style.cursor = 'grab'
    workflowDragState.dragEl = null
    autoSave()
  }

  if (workflowDragState.connecting) {
    const target = e.target as HTMLElement
    const targetNode = target.closest('.flow-node') as HTMLElement

    if (targetNode && workflowDragState.sourceNode) {
      const targetNodeId = targetNode.dataset.id
      const sourceNodeId = workflowDragState.sourceNode

      if (targetNodeId && targetNodeId !== sourceNodeId) {
        const exists = workflowState.connections.some((c) => c.f === sourceNodeId && c.t === targetNodeId)
        if (!exists) {
          workflowState.connections.push({ f: sourceNodeId, t: targetNodeId })
          drawWorkflowLines()
          autoSave()
        }
      }
    }

    if (workflowDragState.tempPath) {
      workflowDragState.tempPath.remove()
      workflowDragState.tempPath = null
    }

    const sourceNode = document.querySelector(`[data-id="${workflowDragState.sourceNode}"]`) as HTMLElement
    if (sourceNode) {
      sourceNode.style.cursor = 'grab'
    }

    workflowDragState.connecting = false
    workflowDragState.sourceNode = null
    workflowDragState.sourceHandle = null
  }
}

function drawWorkflowLines() {
  const svgLayer = document.getElementById('cable-layer')
  if (!svgLayer) return

  const container = document.getElementById('canvas-container')
  if (!container) return

  const containerRect = container.getBoundingClientRect()

  // 清除旧连线
  svgLayer.querySelectorAll('.connection-line').forEach((el) => el.remove())

  workflowState.connections.forEach((cx) => {
    const fromNode = document.querySelector(`[data-id="${cx.f}"]`) as HTMLElement
    const toNode = document.querySelector(`[data-id="${cx.t}"]`) as HTMLElement

    if (!fromNode || !toNode) return

    const fromRect = fromNode.getBoundingClientRect()
    const toRect = toNode.getBoundingClientRect()

    const sx = fromRect.left + fromRect.width - containerRect.left + container.scrollLeft
    const sy = fromRect.top + fromRect.height / 2 - containerRect.top + container.scrollTop
    const tx = toRect.left - containerRect.left + container.scrollLeft
    const ty = toRect.top + toRect.height / 2 - containerRect.top + container.scrollTop

    const dx = Math.max(80, (tx - sx) / 2)
    const d = `M ${sx} ${sy} C ${sx + dx} ${sy}, ${tx - dx} ${ty}, ${tx} ${ty}`

    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path')
    path.setAttribute('class', 'connection-line')
    path.setAttribute('d', d)
    path.setAttribute('stroke', '#6366f1')
    path.setAttribute('stroke-width', '2')
    path.setAttribute('fill', 'none')
    path.setAttribute('opacity', '0.8')
    svgLayer.appendChild(path)
  })
}

function renderWorkflow() {
  const nodesLayer = document.getElementById('nodes-layer')
  if (!nodesLayer) return

  nodesLayer.innerHTML = ''

  workflowState.nodes.forEach((node) => {
    const el = document.createElement('div')
    el.className = 'flow-node pointer-events-auto group'
    el.style.left = node.x + 'px'
    el.style.top = node.y + 'px'
    el.style.position = 'absolute'
    el.dataset.id = node.id
    const c = colors[node.color] || colors.slate
    el.innerHTML = `
      <div class="node-header ${c} px-3 py-2 rounded-t-lg flex justify-between items-center border-b border-white/5">
        <span class="text-xs font-bold flex items-center gap-2">
          <i data-lucide="${node.icon}" class="w-3 h-3"></i> ${node.title}
        </span>
        <button onclick="deleteNode('${node.id}')" class="text-slate-400 hover:text-red-400 opacity-0 group-hover:opacity-100 transition" onmousedown="event.stopPropagation()">
          <i data-lucide="x" class="w-3 h-3"></i>
        </button>
      </div>
      <div class="p-3 text-xs text-slate-500">ID: ${node.id}</div>
      ${node.type !== 'start' ? `<div class="handle input" onmousedown="startConnection(event, '${node.id}', 'input')" title="输入连接点"></div>` : ''}
      ${node.type !== 'end' ? `<div class="handle output" onmousedown="startConnection(event, '${node.id}', 'output')" title="输出连接点"></div>` : ''}
    `

    // 节点头部拖动
    const header = el.querySelector('.node-header') as HTMLElement
    if (header) {
      header.style.cursor = 'grab'
      header.addEventListener('mousedown', (e) => {
        if ((e.target as HTMLElement).closest('button')) return
        startNodeDrag(e as MouseEvent, el)
      })
    }

    // 节点点击（打开配置）
    el.addEventListener('click', (e) => {
      if ((e.target as HTMLElement).closest('.handle')) return
      e.stopPropagation()
      openParams(node)
      highlight(el)
    })

    nodesLayer.appendChild(el)
  })

  renderIcons()
  drawWorkflowLines()
}

function addNode(type: string, title: string, icon: string, color: NodeColor) {
  workflowState.nodeCounter++
  const nodeId = `n${workflowState.nodeCounter}`
  const container = document.getElementById('canvas-container')
  if (!container) return

  const rect = container.getBoundingClientRect()
  const x = Math.random() * 400 + 100
  const y = Math.random() * 300 + 100

  const node: WFNode = {
    id: nodeId,
    type: type,
    title: title,
    x: x,
    y: y,
    color: color,
    icon: icon
  }

  workflowState.nodes.push(node)
  renderWorkflow()
  closeNodePalette()
  autoSave()
  showToast(`已添加节点: ${title}`)
}

function deleteNode(nodeId: string) {
  if (confirm('确定要删除这个节点吗？')) {
    workflowState.nodes = workflowState.nodes.filter((n) => n.id !== nodeId)
    workflowState.connections = workflowState.connections.filter((c) => c.f !== nodeId && c.t !== nodeId)
    renderWorkflow()
    autoSave()
    showToast('节点已删除')
  }
}

function clearWorkflow() {
  if (confirm('确定要清空所有节点吗？此操作不可恢复！')) {
    workflowState.nodes = []
    workflowState.connections = []
    workflowState.nodeCounter = 0
    renderWorkflow()
    showToast('画布已清空')
  }
}

function saveWorkflow() {
  const workflowData = {
    nodes: workflowState.nodes,
    connections: workflowState.connections
  }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(workflowData))
  const saveStatus = document.getElementById('save-status')
  if (saveStatus) {
    saveStatus.textContent = '已保存'
    setTimeout(() => {
      saveStatus.textContent = '实时保存中...'
    }, 2000)
  }
  showToast('工作流已保存')
}

function executeWorkflow() {
  if (workflowState.nodes.length === 0) {
    showToast('工作流为空，请先添加节点')
    return
  }
  showToast('正在编译并运行工作流...')
}

function closeNodePalette() {
  openPalette.value = false
}

function openParams(node: WFNode) {
  const configPanel = document.getElementById('wf-config-panel')
  if (!configPanel) return

  configPanel.style.width = '320px'
  configPanel.style.borderLeftWidth = '1px'

  // 统计连接数
  const incoming = workflowState.connections.filter((c) => c.t === node.id).length
  const outgoing = workflowState.connections.filter((c) => c.f === node.id).length

  configPanel.innerHTML = `
    <div class="p-4 border-b border-slate-700 flex justify-between items-center">
      <h3 class="font-bold text-white">${node.title}</h3>
      <button onclick="closeWorkflowPanel()" class="text-slate-400 hover:text-white">
        <i data-lucide="x" class="w-4 h-4"></i>
      </button>
    </div>
    <div class="p-4 space-y-4 overflow-y-auto">
      <div>
        <label class="text-xs text-slate-500 mb-1 block">节点 ID</label>
        <input disabled class="w-full bg-slate-900 border border-slate-700 rounded p-2 text-slate-400 text-sm" value="${node.id}">
      </div>
      <div>
        <label class="text-xs text-slate-500 mb-1 block">节点标题</label>
        <input type="text" class="input-dark text-sm" value="${node.title}" onchange="updateNodeTitle('${node.id}', this.value)">
      </div>
      <div>
        <label class="text-xs text-slate-500 mb-1 block">节点类型</label>
        <input disabled class="w-full bg-slate-900 border border-slate-700 rounded p-2 text-slate-400 text-sm" value="${node.type}">
      </div>
      <div class="grid grid-cols-2 gap-2 pt-2">
        <div class="bg-slate-900 p-2 rounded text-center">
          <div class="text-xs text-slate-400">输入连接</div>
          <div class="text-lg font-bold text-indigo-400">${incoming}</div>
        </div>
        <div class="bg-slate-900 p-2 rounded text-center">
          <div class="text-xs text-slate-400">输出连接</div>
          <div class="text-lg font-bold text-emerald-400">${outgoing}</div>
        </div>
      </div>
      ${incoming > 0 || outgoing > 0 ? `
      <div class="pt-2">
        <button onclick="disconnectNode('${node.id}')" class="w-full bg-orange-600 hover:bg-orange-500 text-white py-2 rounded text-sm font-bold flex items-center justify-center gap-2">
          <i data-lucide="unlink" class="w-4 h-4"></i> 断开所有连接
        </button>
      </div>
      ` : ''}
      <div class="pt-4 border-t border-slate-700">
        <button onclick="deleteNode('${node.id}')" class="w-full bg-red-600 hover:bg-red-500 text-white py-2 rounded text-sm font-bold flex items-center justify-center gap-2">
          <i data-lucide="trash-2" class="w-4 h-4"></i> 删除节点
        </button>
      </div>
    </div>
  `
  renderIcons()
}

function updateNodeTitle(nodeId: string, newTitle: string) {
  const node = workflowState.nodes.find((n) => n.id === nodeId)
  if (node) {
    node.title = newTitle
    renderWorkflow()
    autoSave()
  }
}

function disconnectNode(nodeId: string) {
  if (confirm('确定要断开此节点的所有连接吗？')) {
    workflowState.connections = workflowState.connections.filter((c) => c.f !== nodeId && c.t !== nodeId)
    renderWorkflow()
    autoSave()
    showToast('已断开所有连接')
    closeWorkflowPanel()
  }
}

function highlight(el: HTMLElement) {
  document.querySelectorAll('.flow-node').forEach((n) => {
    n.classList.remove('selected', 'border-indigo-500', 'ring-2', 'ring-indigo-500/20')
  })
  el.classList.add('selected', 'border-indigo-500', 'ring-2', 'ring-indigo-500/20')
}

function closeWorkflowPanel() {
  const p = document.getElementById('wf-config-panel')
  if (p) {
    p.style.width = '0px'
    p.style.borderLeftWidth = '0px'
  }
}

function autoSave() {
  const workflowData = {
    nodes: workflowState.nodes,
    connections: workflowState.connections
  }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(workflowData))
}

function loadWorkflow() {
  const saved = localStorage.getItem(STORAGE_KEY)
  if (saved) {
    try {
      const data = JSON.parse(saved)
      workflowState.nodes = data.nodes || []
      workflowState.connections = data.connections || []
      if (workflowState.nodes.length > 0) {
        const maxId = Math.max(...workflowState.nodes.map((n) => parseInt(n.id.replace('n', ''))))
        workflowState.nodeCounter = maxId
      }
    } catch (e) {
      console.error('加载工作流失败:', e)
    }
  }
}

function showToast(message: string) {
  // 简单的 toast 实现
  const toast = document.createElement('div')
  toast.className = 'fixed top-4 right-4 bg-slate-800 text-white px-4 py-2 rounded-lg shadow-lg z-50'
  toast.textContent = message
  document.body.appendChild(toast)
  setTimeout(() => {
    toast.remove()
  }, 3000)
}

// 暴露到全局作用域（供内联 onclick 调用）
;(window as any).deleteNode = deleteNode
;(window as any).startConnection = startConnection
;(window as any).updateNodeTitle = updateNodeTitle
;(window as any).disconnectNode = disconnectNode
;(window as any).closeWorkflowPanel = closeWorkflowPanel

onMounted(() => {
  loadWorkflow()
  initWorkflowSystem()
  renderIcons()
  // 再渲染一次，确保页面完全布局完成后连线位置正确（修复初次进入时轻微错位）
  setTimeout(() => {
    renderWorkflow()
  }, 50)
})

onUnmounted(() => {
  document.removeEventListener('mousemove', onWorkflowMouseMove)
  document.removeEventListener('mouseup', onWorkflowMouseUp)
})

watch(openPalette, () => {
  renderIcons()
})
</script>

<style scoped>
.page-transition {
  @apply animate-[slideUp_0.3s_cubic-bezier(0.16,1,0.3,1)];
}

/* 画布样式（完全匹配旧版） */
.node-canvas {
  background-color: #111827;
  background-image: radial-gradient(#374151 1px, transparent 1px);
  background-size: 24px 24px;
  overflow: auto;
  position: relative;
  cursor: default;
}

/* 节点样式（完全匹配旧版） */
.flow-node {
  position: absolute;
  background: #1f2937;
  border: 1px solid #374151;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.5);
  width: 240px;
  border-radius: 0.75rem;
  z-index: 10;
  user-select: none;
  transition: border-color 0.2s, box-shadow 0.2s;
  pointer-events: auto;
}

.flow-node:hover,
.flow-node.selected {
  border-color: #6366f1;
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.3);
  z-index: 20;
}

.node-header {
  cursor: grab;
}

.node-header:active {
  cursor: grabbing;
}

.handle {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #64748b;
  border: 2px solid #1f2937;
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  z-index: 30;
  cursor: crosshair;
  transition: all 0.2s;
  pointer-events: auto;
}

.handle:hover {
  background: #6366f1;
  border-color: #6366f1;
  transform: translateY(-50%) scale(1.3);
}

.handle.input {
  left: -6px;
}

.handle.output {
  right: -6px;
}

.handle.connecting {
  background: #10b981;
  border-color: #10b981;
}

/* 临时连接线 */
.temp-connection {
  stroke: #10b981;
  stroke-width: 2;
  stroke-dasharray: 5, 5;
  pointer-events: none;
}

/* 连接线样式 */
.connection-line {
  pointer-events: none;
}
</style>
