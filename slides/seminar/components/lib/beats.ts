// Click-driven motion for a figure, shared by the animated slides.
//
// A figure describes each click as a set of numbers (channels): opacities, positions,
// progress of a line. target(n) gives the end state of click n. beats[n] lists the
// segments that move the channels from the end of click n - 1 to the end of click n.
//
// The rules this enforces:
//   - a click forward plays its beat at once (the first frame is applied in the same tick);
//   - going back, jumping or clicking during a beat lands on the end state of the click;
//   - print, thumbnails and the next-slide preview always show the end state;
//   - reduced motion shows the end state of each click behind a short fade;
//   - the entry beat (click 0) plays only when the slide opens in the main view or the
//     presenter view.
import { computed, onBeforeUnmount, reactive, ref, unref, watch } from 'vue'
import { onSlideEnter, onSlideLeave, useIsSlideActive, useNav, useSlideContext } from '@slidev/client'

export type Channels = Record<string, number>
export type Ease = (t: number) => number
export type Seg = { k: string; to: number; at: number; dur: number; ease?: Ease }

export const linear: Ease = (t) => t
export const outCubic: Ease = (t) => 1 - Math.pow(1 - t, 3)
export const inOutCubic: Ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2)

export function useBeats(opts: {
  target: (n: number) => Channels
  beats: Record<number, Seg[]>
  entry?: { from: Channels; segs: Seg[] }
}) {
  const { $clicks, $renderContext } = useSlideContext()
  const active = useIsSlideActive()
  // The export pages give each slide its own nav without isPrintMode, so read the shared one
  const { isPrintMode } = useNav()
  const clicks = computed(() => Number(unref($clicks) ?? 0))
  const print = computed(() => !!unref(isPrintMode))
  const live = computed(() => {
    const ctx = unref($renderContext)
    return (ctx === 'slide' || ctx === 'presenter') && !print.value
  })
  const reduced =
    typeof window !== 'undefined' &&
    typeof window.matchMedia === 'function' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches

  const ch = reactive<Channels>({ ...opts.target(clicks.value) })
  const fade = ref(1) // the whole figure fades in after a jump

  let raf = 0
  let run: { seg: Seg; from: number | null; done: boolean }[] = []
  function stop() {
    if (raf) cancelAnimationFrame(raf)
    raf = 0
    run = []
  }
  function set(v: Channels) {
    stop()
    Object.assign(ch, v)
    fade.value = 1
  }
  function play(segs: Seg[]) {
    stop()
    run = [...segs].sort((a, b) => a.at - b.at).map((seg) => ({ seg, from: null, done: false }))
    const t0 = performance.now()
    const tick = (now: number) => {
      const t = now - t0
      let left = false
      for (const r of run) {
        if (r.done) continue
        const { seg } = r
        if (t < seg.at) {
          left = true
          continue
        }
        if (r.from === null) r.from = ch[seg.k] ?? 0
        const p = seg.dur > 0 ? Math.min(1, (t - seg.at) / seg.dur) : 1
        ch[seg.k] = r.from + (seg.to - r.from) * (seg.ease ?? outCubic)(p)
        if (p >= 1) r.done = true
        else left = true
      }
      if (left) raf = requestAnimationFrame(tick)
      else {
        raf = 0
        run = []
      }
    }
    tick(t0)
  }
  // Going back or jumping: the end state of the click at once, behind a short fade
  function settle(n: number) {
    stop()
    Object.assign(ch, opts.target(n))
    fade.value = 0.3
    const t0 = performance.now()
    const tick = (now: number) => {
      const p = Math.min(1, (now - t0) / 200)
      fade.value = 0.3 + 0.7 * p
      if (p < 1) raf = requestAnimationFrame(tick)
      else raf = 0
    }
    raf = requestAnimationFrame(tick)
  }

  watch(clicks, (n, o) => {
    if (!live.value || !unref(active)) return set(opts.target(n))
    const beat = opts.beats[n]
    if (!reduced && n === o + 1 && beat) {
      set(opts.target(o))
      play(beat)
    } else settle(n)
  })
  watch(print, (p) => {
    if (p) set(opts.target(clicks.value))
  })
  onSlideEnter(() => {
    if (!live.value) return set(opts.target(clicks.value))
    if (clicks.value === 0 && opts.entry && !reduced) {
      set({ ...opts.target(0), ...opts.entry.from })
      play(opts.entry.segs)
    } else set(opts.target(clicks.value))
  })
  onSlideLeave(() => set(opts.target(clicks.value)))
  onBeforeUnmount(stop)

  return { ch, fade, clicks, live, print, reduced }
}
