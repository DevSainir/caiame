const MAX_SAMPLES = 6

/**
 * Value -> occurrence counter that also keeps a few example layers,
 * so a raw number can be traced back to the place it came from.
 */
export class Histogram {
  constructor() {
    this.entries = new Map()
  }

  add(key, { fields = {}, sample = null, tags = [] } = {}) {
    let entry = this.entries.get(key)
    if (!entry) {
      entry = { value: key, count: 0, ...fields, tags: {}, samples: [] }
      this.entries.set(key, entry)
    }
    entry.count += 1
    for (const tag of tags) entry.tags[tag] = (entry.tags[tag] ?? 0) + 1
    if (sample && entry.samples.length < MAX_SAMPLES) entry.samples.push(sample)
    return entry
  }

  get size() {
    return this.entries.size
  }

  get total() {
    let total = 0
    for (const entry of this.entries.values()) total += entry.count
    return total
  }

  toJSON() {
    return [...this.entries.values()]
      .sort((a, b) => b.count - a.count || String(a.value).localeCompare(String(b.value)))
      .map((entry) => (Object.keys(entry.tags).length ? entry : omit(entry, 'tags')))
  }
}

function omit(object, key) {
  const { [key]: _dropped, ...rest } = object
  return rest
}
