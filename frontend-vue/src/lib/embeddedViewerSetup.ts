import * as OV from 'online-3d-viewer'

export type EmbeddedViewerLike = {
  GetViewer?: () => {
    shadingModel?: {
      ambientLight?: { color: { set: (hex: number) => void }; intensity: number }
      directionalLight?: { color: { set: (hex: number) => void }; intensity: number }
    }
    renderer?: { toneMappingExposure: number }
    SetNavigationMode?: (mode: number) => void
    SetUpVector?: (direction: number, animate: boolean) => void
    GetBoundingSphere?: (needToProcess: (meshUserData: unknown) => boolean) => unknown
    FitSphereToWindow?: (boundingSphere: unknown, animation: boolean) => void
    Render?: () => void
  } | null
} | null
  | undefined

/**
 * 模型加载完成后对 OV.EmbeddedViewer 的统一后处理：
 * 轻微提亮、Y 轴向上、自由轨道（全向旋转），并重新适配视窗。
 */
export function applyEmbeddedViewerPostLoad(
  embeddedViewer: EmbeddedViewerLike,
  options?: { logLabel?: string }
): void {
  const logLabel = options?.logLabel
  try {
    const coreViewer = embeddedViewer?.GetViewer?.()
    const shadingModel = coreViewer?.shadingModel
    if (!coreViewer || !shadingModel) return

    if (shadingModel.ambientLight) {
      shadingModel.ambientLight.color.set(0x2a2a2a)
      shadingModel.ambientLight.intensity = 2.2 * Math.PI
    }
    if (shadingModel.directionalLight) {
      shadingModel.directionalLight.color.set(0x979797)
      shadingModel.directionalLight.intensity = 1.51 * Math.PI
    }
    if (coreViewer.renderer) {
      coreViewer.renderer.toneMappingExposure = 1.12
    }

    if (typeof coreViewer.SetNavigationMode === 'function') {
      coreViewer.SetNavigationMode(OV.NavigationMode.FreeOrbit)
    }
    if (typeof coreViewer.SetUpVector === 'function') {
      coreViewer.SetUpVector(OV.Direction.Y, false)
    }

    if (typeof coreViewer.GetBoundingSphere === 'function' && typeof coreViewer.FitSphereToWindow === 'function') {
      const boundingSphere = coreViewer.GetBoundingSphere(() => true)
      if (boundingSphere) {
        coreViewer.FitSphereToWindow(boundingSphere, false)
      }
    }

    if (typeof coreViewer.Render === 'function') {
      coreViewer.Render()
    }
  } catch (e) {
    const prefix = logLabel ? `[${logLabel}] ` : ''
    console.warn(`${prefix}applyEmbeddedViewerPostLoad failed:`, e)
  }
}
