<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import BaseContainer from '@/core/components/BaseContainer.vue'
import { describeError } from '@/core/api/messages'
import { setPageTitle } from '@/core/page'
import CourseBenefits from '@/features/catalog/components/CourseBenefits.vue'
import CourseDiscussion from '@/features/catalog/components/CourseDiscussion.vue'
import CourseHero from '@/features/catalog/components/CourseHero.vue'
import CourseProgress from '@/features/catalog/components/CourseProgress.vue'
import CourseReviews from '@/features/catalog/components/CourseReviews.vue'
import CourseUnitList from '@/features/catalog/components/CourseUnitList.vue'
import { fetchCourse, fetchQuestions, fetchReviews, fetchSyllabus } from '@/features/catalog/api'

const REVIEWS_PER_PAGE = 3

const route = useRoute()

const course = ref(null)
const syllabus = ref(null)
const questions = ref([])
const reviews = ref({ items: [], total: 0, page: 0, summary: null })
const isLoading = ref(true)
const isLoadingReviews = ref(false)
const error = ref(null)

const isMissing = computed(() => error.value?.status === 404)
const hasMoreReviews = computed(() => reviews.value.items.length < reviews.value.total)

// Описание приходит одним текстом с пустой строкой между абзацами: колонка текста в макете
// разбита на абзацы, а хранить их массивом ради одного экрана незачем.
const paragraphs = computed(() =>
  (course.value?.description ?? '')
    .split('\n\n')
    .map((text) => text.trim())
    .filter(Boolean),
)

/**
 * Догрузить следующую страницу отзывов.
 *
 * Страницы складываются, а не заменяют друг друга: «Посмотреть остальные отзывы» в макете
 * стоит под списком, а не рядом с номерами страниц.
 */
async function loadMoreReviews() {
  if (isLoadingReviews.value) return
  isLoadingReviews.value = true
  try {
    const next = await fetchReviews(route.params.slug, {
      page: reviews.value.page + 1,
      size: REVIEWS_PER_PAGE,
    })
    reviews.value = { ...next, items: [...reviews.value.items, ...next.items] }
  } catch {
    // Список уже показан: молча оставляем кнопку, чтобы попробовать ещё раз.
  } finally {
    isLoadingReviews.value = false
  }
}

async function load(slug) {
  isLoading.value = true
  error.value = null
  try {
    // Четыре запроса разом, а не цепочкой: каждый следующий не зависит от предыдущего,
    // и последовательная загрузка стоила бы четыре круга до сервера вместо одного.
    const [detail, outline, discussion, firstReviews] = await Promise.all([
      fetchCourse(slug),
      fetchSyllabus(slug),
      fetchQuestions(slug),
      fetchReviews(slug, { page: 1, size: REVIEWS_PER_PAGE }),
    ])
    course.value = detail
    setPageTitle(detail.title)
    syllabus.value = outline
    questions.value = discussion.items
    reviews.value = firstReviews
  } catch (failure) {
    error.value = failure
    course.value = null
  } finally {
    isLoading.value = false
  }
}

watch(() => route.params.slug, load, { immediate: true })
</script>

<template>
  <div>
    <p
      v-if="isLoading"
      class="py-24 text-center text-sm font-semibold text-subtle lg:py-35 lg:text-lg"
    >
      Загружаем курс…
    </p>

    <div v-else-if="error" class="flex flex-col items-center gap-5 py-24 lg:py-35">
      <p class="text-center text-sm font-semibold text-subtle lg:text-lg">
        {{ isMissing ? 'Такого курса нет' : describeError(error, 'Не удалось открыть курс') }}
      </p>
      <RouterLink v-if="isMissing" class="text-base font-bold text-accent" to="/">
        Ко всем курсам
      </RouterLink>
      <button
        v-else
        class="text-base font-bold text-accent"
        type="button"
        @click="load(route.params.slug)"
      >
        Попробовать ещё раз
      </button>
    </div>

    <template v-else-if="course">
      <CourseHero :course="course" />

      <section class="pt-14 lg:pt-35">
        <BaseContainer>
          <h2 class="text-2xl font-bold text-ink lg:text-3xl">Основная информация</h2>
          <div class="flex max-w-xl flex-col gap-5 pt-5 lg:gap-6 lg:pt-8">
            <p
              v-for="(text, index) in paragraphs"
              :key="index"
              class="text-sm font-medium leading-relaxed text-muted lg:text-base"
            >
              {{ text }}
            </p>
          </div>
        </BaseContainer>
      </section>

      <CourseBenefits :benefits="course.benefits" />

      <section v-if="syllabus?.modules.length" class="pt-14 lg:pt-35">
        <BaseContainer>
          <CourseUnitList :units="syllabus.modules" />
        </BaseContainer>
      </section>

      <section v-if="syllabus?.activities.length" class="pt-14 lg:pt-35">
        <BaseContainer>
          <CourseUnitList :units="syllabus.activities">
            <CourseProgress :percent="syllabus.progress_percent" />
          </CourseUnitList>
        </BaseContainer>
      </section>

      <CourseReviews
        :has-more="hasMoreReviews"
        :is-loading="isLoadingReviews"
        :reviews="reviews.items"
        :summary="reviews.summary"
        @more="loadMoreReviews"
      />
      <CourseDiscussion :questions="questions" />
    </template>
  </div>
</template>
