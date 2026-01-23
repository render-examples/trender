/**
 * Format large numbers into K/M notation
 * 1000+ -> 1K
 * 1000000+ -> 1M
 * 
 * @param num - Number to format
 * @returns Formatted string
 */
export function formatStarCount(num: number | null | undefined): string {
  if (num === null || num === undefined) {
    return '0'
  }
  
  if (num >= 1000000) {
    return Math.round(num / 1000000) + 'M'
  }
  
  if (num >= 1000) {
    return Math.round(num / 1000) + 'K'
  }
  
  return num.toString()
}

