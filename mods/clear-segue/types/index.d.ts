export type Armed = { cwd: string; at: number; handoff?: string }

declare module 'claude-code' {
  interface PluginState {
    'clear-segue': { isArmed: boolean; isStale: boolean; isUpdating: boolean }
  }
}
