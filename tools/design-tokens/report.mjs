// The mapping table is the review artifact: every raw value has to be traceable
// to the token that replaced it, including the ones that were thrown away.

export function renderMapping(data) {
  return [
    header(data),
    colorSection(data),
    typographySection(data),
    spacingSection(data),
    shapeSection(data),
  ].join('\n')
}

function header({ audit, threshold }) {
  return `# Таблица соответствия: макет → токены

Источник: \`${audit.meta.file}\`, страница ${audit.meta.pagesAudited.map((p) => `«${p}»`).join(', ')},
фреймы шириной ${audit.meta.rootWidthFilter?.join('/') ?? 'любой'}px, ${audit.meta.stats.nodesVisited} узлов.
Порог склейки цветов: ΔE OKLab ≤ ${threshold}.

Сгенерировано \`node tools/design-tokens/build.mjs\` — файл не редактируется руками.
`
}

function colorSection({ clusters, byGroup, ramps, mergedAway, colorJunk, translucent, contrast, semantic }) {
  const lines = ['\n## Цвета\n', '### Склейки\n']
  lines.push('| токен-кандидат | исходные значения | ΔE | использований | контекст |')
  lines.push('|---|---|---|---|---|')
  for (const cluster of clusters.filter((item) => item.members.length > 1)) {
    const members = cluster.members.map((member) => `\`${member.value}\` ×${member.count}`).join(', ')
    const maxDelta = Math.max(...cluster.members.map((member) => member.distance))
    const tags = Object.entries(cluster.members[0].tags ?? {}).map(([k, v]) => `${k} ${v}`).join(', ')
    lines.push(`| \`${cluster.hex}\` | ${members} | ${maxDelta.toFixed(3)} | ${cluster.count} | ${tags} |`)
  }
  const single = clusters.filter((item) => item.members.length === 1)
  lines.push(`\nБез склейки прошли ${single.length} цветов: ${single.map((c) => `\`${c.hex}\``).join(', ')}.\n`)

  lines.push('### Группы\n')
  for (const [group, items] of byGroup) {
    lines.push(`- **${group}** — ${items.map((c) => `\`${c.hex}\` (${c.count})`).join(', ')}`)
  }

  lines.push('\n### Шкалы\n')
  for (const [group, ramp] of Object.entries(ramps)) {
    lines.push(`\n**${group}**\n`)
    lines.push('| ступень | значение | откуда | использований в макете |')
    lines.push('|---|---|---|---|')
    for (const [step, value] of Object.entries(ramp)) {
      const origin = { figma: 'из макета', generated: 'достроено', invented: 'придумано' }[value.source]
      lines.push(`| \`${group}-${step}\` | \`${value.hex}\` | ${origin} | ${value.count || '—'} |`)
    }
  }

  if (mergedAway.length) {
    lines.push('\n### Поглощённые ступени\n')
    lines.push('Цвет попал на ступень, которую уже занял более частотный сосед.\n')
    lines.push('| цвет | использований | группа | ближайшая ступень |')
    lines.push('|---|---|---|---|')
    for (const item of mergedAway) {
      lines.push(`| \`${item.cluster.hex}\` | ${item.cluster.count} | ${item.group} | \`${item.group}-${item.step}\` |`)
    }
  }

  if (colorJunk.length) {
    lines.push('\n### Отброшено как шум (частота ≤ 2)\n')
    lines.push('| цвет | использований | где встречается |')
    lines.push('|---|---|---|')
    for (const entry of colorJunk) {
      const where = [...new Set(entry.samples.map((s) => s.name))].slice(0, 2).join(', ')
      lines.push(`| \`${entry.value}\` | ${entry.count} | ${where} |`)
    }
  }

  if (translucent.length) {
    lines.push('\n### Полупрозрачные заливки\n')
    for (const entry of translucent) lines.push(`- \`${entry.value}\` ×${entry.count}`)
  }

  lines.push('\n### Семантические роли\n')
  lines.push('| роль | ступень | значение |')
  lines.push('|---|---|---|')
  for (const [role, values] of Object.entries(semantic)) {
    for (const [name, value] of Object.entries(values)) {
      lines.push(`| \`${role}.${name}\` | \`${value.reference ?? '—'}\` | \`${value.hex}\` |`)
    }
  }

  lines.push('\n### Контраст по WCAG\n')
  lines.push('| цвет | на белом | на `surface.subtle` | вердикт | ближайшая ступень с AA |')
  lines.push('|---|---|---|---|---|')
  for (const item of contrast) {
    const verdict = item.onWhite >= 4.5 ? 'AA текст' : item.onWhite >= 3 ? 'только крупный текст и иконки' : 'не для текста'
    lines.push(`| \`${item.hex}\` | ${item.onWhite} | ${item.onSubtle} | ${verdict} | ${item.fix ?? '—'} |`)
  }
  return lines.join('\n')
}

function typographySection({ typography }) {
  const lines = ['\n\n## Типографика\n']
  lines.push('| ступень | размер | line-height (токен) | по большинству в макете | использований | фактические line-height | веса | пример |')
  lines.push('|---|---|---|---|---|---|---|---|')
  for (const step of typography.steps) {
    const actual = step.lineHeights.map(([ratio, count]) => `${ratio}×${count}`).join(', ')
    const weights = step.weights.map(([weight, count]) => `${weight}×${count}`).join(', ')
    lines.push(
      `| \`text-${step.name}\` | ${step.fontSize}px | ${step.lineHeight} | ${step.dataLineHeight}${step.dataLineHeight === step.lineHeight ? '' : ' ⚠'} | ${step.count} | ${actual} | ${weights} | ${step.samples[0] ?? ''} |`,
    )
  }
  if (typography.junk.length) {
    lines.push('\n**Размеры-одиночки (частота ≤ 2), отнесены к ближайшей ступени:**\n')
    for (const item of typography.junk) {
      lines.push(`- ${item.fontSize}px ×${item.count} → ${item.snappedTo}px — «${item.samples[0] ?? ''}»`)
    }
  }
  lines.push('\n**Letter-spacing.** Доминирует ' + typography.letterSpacing.dominant + '% от кегля: ')
  lines.push(typography.letterSpacing.distribution.map(([percent, count]) => `${percent}% ×${count}`).join(', ') + '.')
  lines.push('\n**Веса.** ' + typography.weights.map((w) => `${w.weight} (${w.name}) ×${w.count}`).join(', ') + '.')
  return lines.join('\n')
}

function spacingSection({ spacing }) {
  const lines = ['\n\n## Отступы\n']
  lines.push('| токен | значение | использований | из каких исходных |')
  lines.push('|---|---|---|---|')
  for (const step of spacing.scale) {
    const from = step.from
      .map((item) => `${item.value}${item.drift ? ` (${item.drift > 0 ? '+' : ''}${item.drift})` : ''}×${item.count}`)
      .join(', ')
    const origin = step.manual ? `**добавлено вручную:** ${step.manual}` : from
    lines.push(`| \`${step.px / 4}\` | ${step.px}px | ${step.count || '—'} | ${origin} |`)
  }
  lines.push('\n### Не легли на сетку 4px\n')
  lines.push('| исходное | использований | ушло в | сдвиг |')
  lines.push('|---|---|---|---|')
  for (const item of spacing.offGrid) {
    lines.push(`| ${item.value}px | ${item.count} | ${item.target}px | ${item.drift > 0 ? '+' : ''}${item.drift}px |`)
  }
  lines.push('\n### Расстояния уровня раскладки (>160px, в шкалу не вошли)\n')
  lines.push('| значение | использований | где |')
  lines.push('|---|---|---|')
  for (const item of spacing.layout) {
    const where = [...new Set(item.samples.map((s) => s.name))].slice(0, 2).join(', ')
    lines.push(`| ${item.value}px | ${item.count} | ${where} |`)
  }
  lines.push(`\nОтброшено как шум (частота ≤ 2): ${spacing.junk.map((i) => `${i.value}px`).join(', ')}.`)
  return lines.join('\n')
}

function shapeSection({ radii, strokes, audit }) {
  const names = ['xs', 'sm', 'md', 'lg', 'xl', '2xl']
  const lines = ['\n\n## Радиусы\n']
  lines.push('| токен | значение | использований | из каких исходных |')
  lines.push('|---|---|---|---|')
  radii.steps.forEach((step, index) => {
    const from = step.from
      .map((item) => `${item.value}${item.drift ? ` (${item.drift > 0 ? '+' : ''}${item.drift})` : ''}×${item.count}`)
      .join(', ')
    lines.push(`| \`rounded-${names[index] ?? index}\` | ${step.px}px | ${step.count} | ${from} |`)
  })
  lines.push(`\nОтброшено как шум: ${radii.junk.map((i) => `${i.value}px`).join(', ') || '—'}.`)
  lines.push('\n### Таблетки (радиус = половина короткой стороны) → `rounded-full`\n')
  lines.push('| исходный радиус | использований | пример |')
  lines.push('|---|---|---|')
  for (const item of audit.pillRadii ?? []) {
    const where = [...new Set(item.samples.map((s) => s.name))].slice(0, 2).join(', ')
    lines.push(`| ${item.value}px | ${item.count} | ${where} |`)
  }
  lines.push('\n## Обводки\n')
  for (const stroke of strokes) lines.push(`- ${stroke.px}px ×${stroke.count}`)
  lines.push(`\n## Тени\n\nВ макете ${audit.shadows.length === 0 ? 'нет ни одной тени' : `${audit.shadows.length} теней`}.`)
  return lines.join('\n')
}
