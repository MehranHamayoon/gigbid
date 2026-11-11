import {useEffect, useRef, useState} from 'react'
import {active, api, errorText, type Run} from './api/client'

export function useLoad<T>(load: () => Promise<T>, initial: T, key: unknown) {
  const [data, setData] = useState(initial)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [version, setVersion] = useState(0)
  const latest = useRef(load)
  latest.current = load
  useEffect(() => {
    let alive = true
    setLoading(true)
    setError('')
    latest.current().then(value => {if (alive) setData(value)}).catch(problem => {
      if (alive) setError(errorText(problem))
    }).finally(() => {if (alive) setLoading(false)})
    return () => { alive = false }
  }, [key, version])
  return {data, loading, error, refresh: () => setVersion(value => value + 1)}
}

export function useRun(id?: string) {
  const [run, setRun] = useState<Run>()
  const [error, setError] = useState('')
  const [version, setVersion] = useState(0)
  useEffect(() => {
    if (!id) {setRun(undefined); return}
    let alive = true
    let timer: number
    const poll = async () => {
      try {
        const reply = await api.GET('/api/runs/{run_id}', {params: {path: {run_id: id}}})
        if (!alive) return
        if (reply.error || !reply.data) {setError(errorText(reply.error)); return}
        setRun(reply.data)
        setError('')
        if (active.has(reply.data.status)) timer = window.setTimeout(poll, 450)
      } catch (problem) {
        if (alive) setError(errorText(problem))
      }
    }
    void poll()
    return () => {alive = false; window.clearTimeout(timer)}
  }, [id, version])
  return {run: run?.id === id ? run : undefined, error, reload: () => setVersion(current => current + 1)}
}
