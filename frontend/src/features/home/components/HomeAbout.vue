<script setup>
import BaseContainer from '@/core/components/BaseContainer.vue'
import BaseButton from '@/core/components/BaseButton.vue'
import IconBook from '@/core/components/icons/IconBook.vue'
import IconMedicalBag from '@/core/components/icons/IconMedicalBag.vue'
import IconSparkle from '@/core/components/icons/IconSparkle.vue'
import illustrationUrl from '@/assets/images/about-illustration.png'

const PARAGRAPHS = [
  'Платформа НМО предлагает медицинским профессионалам доступ к современным и актуальным образовательным ресурсам.',
  'Наши курсы разработаны ведущими экспертами в различных медицинских областях и обеспечивают повышение квалификации, развитие навыков и углубление знаний.',
  'Мы стремимся поддерживать высокий уровень медицинской практики, предоставляя качественное обучение, удобное и доступное в любое время.',
]
</script>

<template>
  <section class="py-35">
    <BaseContainer>
      <div class="flex items-center gap-8">
        <div class="flex basis-1/2 flex-col gap-6">
          <h2 class="text-5xl font-bold text-ink">О нашей платформе</h2>
          <p v-for="paragraph in PARAGRAPHS" :key="paragraph" class="text-base font-medium text-ink">
            {{ paragraph }}
          </p>
          <BaseButton class="mt-6 self-start" to="/courses">Узнать подробнее</BaseButton>
        </div>

        <div class="relative basis-1/2">
          <IconMedicalBag class="absolute left-0 top-1/3 w-10 text-primary-500" />
          <IconBook class="absolute bottom-1/4 left-6 w-10 text-primary-500" />
          <IconSparkle class="absolute left-12 top-1/2 w-5 text-primary-500" />
          <IconSparkle class="absolute bottom-1/3 left-0 w-8 text-primary-500" />
          <IconSparkle class="absolute right-1/4 top-6 w-4 text-neutral-100" />
          <img :src="illustrationUrl" alt="" class="ml-auto w-full" />
        </div>
      </div>
    </BaseContainer>
  </section>
</template>
