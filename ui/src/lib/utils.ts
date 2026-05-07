import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

const WEEK_DAYS = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'] as const

/**
 * 将日期字符串格式化为相对日期标签
 * - 今天 → "今天"
 * - 昨天 → "昨天"
 * - 本周内 → "周一"..."周六"
 * - 更早 → "MM/DD"
 *
 * 注意：此函数在 SSR 和客户端应产生相同结果，避免使用 Date.now()
 */
export function formatRelativeDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '今天'
  const date = new Date(dateStr)
  if (isNaN(date.getTime())) return '今天'

  // 使用传入日期当天的午夜时间作为 "今天" 的基准
  // 避免 SSR/客户端时间不一致导致的 hydration 问题
  const now = new Date()
  // 归一化到当天 0:00，使用 UTC 方法避免时区问题
  const today = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()))
  const target = new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate()))
  const diffDays = Math.floor((today.getTime() - target.getTime()) / (1000 * 60 * 60 * 24))

  if (diffDays === 0) return '今天'
  if (diffDays === 1) return '昨天'
  if (diffDays < 7) return WEEK_DAYS[date.getDay()]

  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${month}/${day}`
}

/**
 * 格式化文件大小
 * @param bytes 文件大小（字节）
 * @returns 格式化后的文件大小字符串，如 "2.52 MB"
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B'
  
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  
  return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`
}
