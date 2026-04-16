/**
 * 与后端 utils/studio_display.format_hunyuan_image23d_display_prompt 一致，
 * 用于历史列表等在 prompt 字段为空时从 params 回显图生3D 配置。
 */
export function formatImage23dDisplayFromParams(
  withTexture: boolean,
  generationParams: Record<string, unknown> | null | undefined
): string {
  const gp = generationParams && typeof generationParams === 'object' ? generationParams : {}
  const parts: string[] = ['图生3D']
  const model = gp.Model
  if (model != null && String(model).trim()) parts.push(`模型${model}`)
  const gtRaw = String(
    gp.GenerateType != null && String(gp.GenerateType).trim()
      ? gp.GenerateType
      : withTexture
        ? 'Normal'
        : 'Geometry'
  )
  const gtMap: Record<string, string> = {
    Normal: '标准',
    LowPoly: '低多边形',
    Geometry: '几何白模',
    Sketch: '草图'
  }
  const gtZh = gtMap[gtRaw] || gtRaw
  parts.push(`${gtZh}·${withTexture ? '彩色' : '白模'}`)
  const fc = gp.FaceCount
  let fcInt = 0
  if (fc != null) {
    const n = typeof fc === 'number' ? fc : parseInt(String(fc), 10)
    fcInt = Number.isFinite(n) ? n : 0
  }
  if (fcInt > 0) {
    if (fcInt >= 10000 && fcInt % 10000 === 0) parts.push(`${fcInt / 10000}万面`)
    else parts.push(`面数${fcInt}`)
  }
  if (gp.EnablePBR) parts.push('PBR')
  const pt = gp.PolygonType
  if (pt != null && String(pt).trim()) {
    const pk = String(pt).toLowerCase()
    const ptMap: Record<string, string> = { triangle: '三角面', quadrilateral: '四边面' }
    parts.push(ptMap[pk] || String(pt))
  }
  const rf = gp.ResultFormat
  if (rf != null && String(rf).trim() && String(rf).toUpperCase() !== 'GLB') {
    parts.push(`输出${String(rf).toUpperCase()}`)
  }
  return parts.join(' · ')
}

/** 与后端 prompt_from_studio_history_row(image23d, params) 对齐（params 为历史条里的归一化对象） */
export function image23dSummaryFromHistoryParams(params: Record<string, unknown> | undefined): string {
  if (!params || typeof params !== 'object') return ''
  const wt = params.with_texture !== false
  const gp = params.generation_params
  const g =
    gp && typeof gp === 'object' && !Array.isArray(gp) ? (gp as Record<string, unknown>) : undefined
  if (!g || Object.keys(g).length === 0) return ''
  return formatImage23dDisplayFromParams(wt, g)
}
