import { useEffect, useRef, useState } from 'react'
import type { LevelUpEvent } from '../api/client'
import './LevelUpCelebration.css'

interface LevelUpCelebrationProps {
  events: LevelUpEvent[]
  onDone: () => void
}

interface Particle {
  x: number
  y: number
  vx: number
  vy: number
  sway: number
  swaySpeed: number
  size: number
  color: string
  life: number
  age: number
}

const COLORS = ['#e8a63c', '#ef7f63', '#6fb3c9', '#9b6fa8', '#4fada0']

function eventTitle(event: LevelUpEvent): string {
  if (event.type === 'skill') {
    const label = event.skill_key ? event.skill_key.charAt(0).toUpperCase() + event.skill_key.slice(1) : 'Skill'
    return `${label} Leveled Up!`
  }
  if (event.type === 'course') {
    return `${event.course_name ?? 'Course'} Mastery Up!`
  }
  return 'Level Up!'
}

function LevelUpCelebration({ events, onDone }: LevelUpCelebrationProps) {
  const [index, setIndex] = useState(0)
  const [show, setShow] = useState(false)
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const rafRef = useRef<number | null>(null)
  const particlesRef = useRef<Particle[]>([])

  const event = events[index]

  useEffect(() => {
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const showTimeout = setTimeout(() => setShow(true), 20)

    const canvas = canvasRef.current
    if (!canvas || reduced) return () => clearTimeout(showTimeout)

    const ctx = canvas.getContext('2d')
    if (!ctx) return () => clearTimeout(showTimeout)

    function resize() {
      if (!canvas) return
      canvas.width = window.innerWidth * devicePixelRatio
      canvas.height = window.innerHeight * devicePixelRatio
      canvas.style.width = `${window.innerWidth}px`
      canvas.style.height = `${window.innerHeight}px`
    }
    resize()
    window.addEventListener('resize', resize)

    const w = window.innerWidth
    const h = window.innerHeight
    const particles: Particle[] = []
    for (let i = 0; i < 70; i++) {
      const angle = Math.random() * Math.PI * 2
      const speed = 1 + Math.random() * 4
      particles.push({
        x: w / 2,
        y: h * 0.4,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed - 1.5,
        sway: Math.random() * Math.PI * 2,
        swaySpeed: 0.05 + Math.random() * 0.05,
        size: 3 + Math.random() * 5,
        color: COLORS[(Math.random() * COLORS.length) | 0],
        life: 90 + Math.random() * 60,
        age: 0,
      })
    }
    particlesRef.current = particles

    function tick() {
      if (!ctx || !canvas) return
      ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0)
      ctx.clearRect(0, 0, window.innerWidth, window.innerHeight)
      let alive = false
      particlesRef.current.forEach((p) => {
        if (p.age > p.life) return
        alive = true
        p.age++
        p.sway += p.swaySpeed
        p.x += p.vx + Math.sin(p.sway) * 0.6
        p.y += p.vy * 0.35
        p.vy += 0.01
        const fade = 1 - p.age / p.life
        ctx.save()
        ctx.globalAlpha = Math.max(fade, 0) * 0.85
        ctx.fillStyle = p.color
        ctx.shadowColor = p.color
        ctx.shadowBlur = 8
        ctx.beginPath()
        ctx.arc(p.x, p.y, p.size / 2, 0, Math.PI * 2)
        ctx.fill()
        ctx.restore()
      })
      if (alive) {
        rafRef.current = requestAnimationFrame(tick)
      } else {
        ctx.clearRect(0, 0, window.innerWidth, window.innerHeight)
      }
    }
    rafRef.current = requestAnimationFrame(tick)

    return () => {
      clearTimeout(showTimeout)
      window.removeEventListener('resize', resize)
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
    }
  }, [index])

  const advance = () => {
    setShow(false)
    setTimeout(() => {
      if (index + 1 < events.length) {
        setIndex((i) => i + 1)
      } else {
        onDone()
      }
    }, 220)
  }

  if (!event) return null

  return (
    <div
      className={`levelup-overlay${show ? ' show' : ''}`}
      role="dialog"
      aria-label="Level up celebration"
      onClick={advance}
    >
      <canvas ref={canvasRef} />
      <div className="levelup-card">
        <div className="glow-ring" />
        <div className="glow-ring r2" />
        <div className="glow-ring r3" />
        <div className="levelup-up">{eventTitle(event)}</div>
        <div className="levelup-big">
          {event.from_level}
          <span className="arrow">➜</span>
          <span className="to">{event.to_level}</span>
        </div>
        <p className="levelup-hint">
          tap anywhere to continue{events.length > 1 ? ` (${index + 1}/${events.length})` : ''}
        </p>
      </div>
    </div>
  )
}

export default LevelUpCelebration
