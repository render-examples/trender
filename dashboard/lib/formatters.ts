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
    return (num / 1000000).toFixed(1).replace(/\.0$/, '') + 'M'
  }
  
  if (num >= 1000) {
    return (num / 1000).toFixed(1).replace(/\.0$/, '') + 'K'
  }
  
  return num.toString()
}

