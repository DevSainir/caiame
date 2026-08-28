import { ref } from 'vue'
import { defineStore } from 'pinia'

const DISMISS_AFTER_MS = 5000
let nextId = 0

export const useNotificationStore = defineStore('notifications', () => {
  const items = ref([])

  function dismiss(id) {
    items.value = items.value.filter((item) => item.id !== id)
  }

  /** Show a message in the corner. Auto-dismissed, because nobody closes these by hand. */
  function notify(text, tone = 'success') {
    const id = (nextId += 1)
    items.value = [...items.value, { id, text, tone }]
    setTimeout(() => dismiss(id), DISMISS_AFTER_MS)
    return id
  }

  return { items, notify, dismiss }
})
