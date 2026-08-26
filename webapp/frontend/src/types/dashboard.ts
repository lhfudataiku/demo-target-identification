export type DeltaDirection = 'up' | 'down' | 'flat'

export interface KpiValue {
  label: string
  value: string
  deltaLabel: string
  deltaDirection: DeltaDirection
  upIsGood: boolean
  sparkline: number[]
  caption?: string
}
