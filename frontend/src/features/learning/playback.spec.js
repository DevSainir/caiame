import { describe, expect, it } from 'vitest'
import { createPlaybackTracker } from '@/features/learning/playback'

describe('счётчик просмотренного', () => {
  it('копит время при обычном проигрывании', () => {
    const tracker = createPlaybackTracker({ reportEvery: 5 })
    tracker.advance(0)

    for (let time = 0.5; time <= 3; time += 0.5) tracker.advance(time)

    expect(tracker.take()).toBe(3)
  })

  it('не засчитывает перемотку вперёд', () => {
    // Ровно тот случай, ради которого модуль существует: ползунок в конец — не просмотр.
    const tracker = createPlaybackTracker({ reportEvery: 5 })
    tracker.advance(0)

    tracker.advance(600)

    expect(tracker.take()).toBe(0)
  })

  it('не засчитывает перемотку назад', () => {
    const tracker = createPlaybackTracker({ reportEvery: 5 })
    tracker.advance(100)

    tracker.advance(10)

    expect(tracker.take()).toBe(0)
  })

  it('отдаёт накопленное, когда пора отправлять', () => {
    const tracker = createPlaybackTracker({ reportEvery: 2 })
    tracker.advance(0)
    tracker.advance(1)

    const ready = tracker.advance(2)

    expect(ready).toBe(2)
    expect(tracker.take()).toBe(0)
  })

  it('после сброса считает с нуля', () => {
    const tracker = createPlaybackTracker({ reportEvery: 5 })
    tracker.advance(0)
    tracker.advance(1)

    tracker.reset()
    tracker.advance(50)

    expect(tracker.take()).toBe(0)
  })
})
