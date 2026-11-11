import createClient from 'openapi-fetch'
import type {components, paths} from './schema'

export const api = createClient<paths>({credentials: 'same-origin'})
export type Job = components['schemas']['Job']
export type Run = components['schemas']['Run']
export type User = components['schemas']['User']
export type Preferences = components['schemas']['Preferences']
export type Message = components['schemas']['Message']
export type PipelineCard = components['schemas']['PipelineCard']

export interface Evidence {
  id: string
  title: string
  text: string
  type: string
  source: string
  skills: string[]
  industry: string
}
export interface Claim {
  text: string
  status: string
  evidence_id?: string
}
export interface RunResult {
  evidence?: Evidence[]
  job_spec?: {deliverables: string[]; duration_days: number; screening_questions: string[]}
  fit_report?: {score: number; matrix: Record<string, string[]>; missing_skills: string[]}
  risk_report?: {score: number; flags: string[]; explanation: string}
  decision?: {action: string; reason: string}
  price_quote?: {amount: number; rationale: string; connects: number}
  proposal_draft?: {cover_letter: string; screening_answers: string[]}
  critique?: {accepted: boolean; feedback: string[]; revision: number}
  compliance_verdict?: {allowed: boolean; reasons: string[]}
  claim_verification?: Claim[]
  liaison?: {intent: string; draft: string; slots: string[]}
  approval?: {reason: string}
  preview?: {connects: number; payload: {text: string; amount: number}}
  outcome?: {stage?: string}
  selected_persona?: string
}

export function result(run: Run | undefined | null): RunResult {
  return (run?.result ?? {}) as RunResult
}
export function errorText(error: unknown, fallback = 'The request failed. Please retry.') {
  if (error && typeof error === 'object' && 'detail' in error) {
    const detail = error.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) return detail.map(item => item.msg).join('. ')
  }
  return error instanceof Error ? error.message : fallback
}
export const usd = (amount: number) => new Intl.NumberFormat('en-US', {style: 'currency', currency: 'USD', maximumFractionDigits: 0}).format(amount)
export const categories: Record<string, string> = {ai: 'AI / ML', web: 'Web development', data: 'Data & analytics', agency: 'Agency workspace'}
export const active = new Set(['queued', 'running', 'marketplace_unavailable'])
