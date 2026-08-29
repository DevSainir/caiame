<script setup>
import { ref } from 'vue'
import BaseContainer from '@/core/components/BaseContainer.vue'
import IconAngleDown from '@/core/components/icons/IconAngleDown.vue'
import IconQuestionCircle from '@/core/components/icons/IconQuestionCircle.vue'

const props = defineProps({
  questions: { type: Array, default: () => [] },
})

// Раскрыт ровно один вопрос: в макете все свёрнуты, и открытая гармошка на весь экран
// прячет остальные вопросы вместо того, чтобы отвечать на один.
const openId = ref(null)

const toggle = (id) => {
  openId.value = openId.value === id ? null : id
}
</script>

<template>
  <section v-if="props.questions.length > 0" class="pb-14 pt-14 lg:pb-35 lg:pt-35">
    <BaseContainer>
      <h2 class="text-2xl font-bold text-ink lg:text-3xl">Обсуждение</h2>

      <div class="flex flex-col gap-5 pt-6 lg:flex-row lg:items-start lg:gap-8 lg:pt-8">
        <div class="lg:basis-2/3">
          <div class="rounded-xl border border-subtle bg-page px-4 lg:px-15">
            <div
              v-for="(item, index) in props.questions"
              :key="item.id"
              :class="index > 0 ? 'border-t border-subtle' : ''"
            >
              <button
                class="flex w-full items-center justify-between gap-4 py-5 text-left lg:py-8"
                type="button"
                @click="toggle(item.id)"
              >
                <span class="text-sm font-semibold text-ink lg:text-base">{{ item.question }}</span>
                <IconAngleDown
                  class="w-5 shrink-0 text-accent transition-transform"
                  :class="openId === item.id ? 'rotate-180' : ''"
                />
              </button>
              <p
                v-if="openId === item.id"
                class="pb-5 text-sm font-medium text-muted lg:pb-8 lg:text-base"
              >
                {{ item.answer }}
              </p>
            </div>
          </div>
        </div>

        <div
          class="flex items-center gap-4 rounded-xl border border-subtle bg-page p-5 lg:basis-1/3 lg:gap-6 lg:p-6"
        >
          <IconQuestionCircle class="w-6 shrink-0 text-ink" />
          <div class="flex flex-col gap-2">
            <p class="text-base font-semibold text-ink lg:text-lg">Остались ещё вопросы?</p>
            <RouterLink class="text-sm font-medium text-accent" to="/support">
              Задайте свой вопрос
            </RouterLink>
          </div>
        </div>
      </div>
    </BaseContainer>
  </section>
</template>
