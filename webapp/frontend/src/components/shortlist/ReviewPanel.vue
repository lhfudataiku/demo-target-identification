<script setup lang="ts">
  /**
   * Recorded reviews of the selected pair (webapp revision W4, D2–D3).
   *
   * A review is the scientist's judgement, labelled as such: a verdict and a required comment, stored
   * in DSS (`POST /api/reviews`) with the reviewer's DSS login, the rank, the score and the model. The
   * app proposes no verdict. Reviews are append-only: the newest one for the pair leads, earlier ones
   * stay listed beneath it.
   */
  import { computed, ref, watch } from 'vue'
  import {
    Alert, AlertDescription, Button, Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader,
    DialogTitle, Label, RadioGroup, RadioGroupItem, Textarea,
  } from '@dataiku/ea-ui-kit'
  import { CommentAdd } from '@dataiku/vue-icons'
  import { StatusBadge } from 'bs-blueprint'
  import { apiUrl } from '@/utils/api'
  import { VERDICTS, verdictStatus, type Review, type Row, type Verdict } from './types'

  const props = defineProps<{ row: Row; diseaseIndex: number; diseaseName: string; reviews: Review[] }>()
  const emit = defineEmits<{ (e: 'recorded', review: Review): void }>()

  // This pair's reviews, newest first (the parent passes them sorted).
  const mine = computed(() => props.reviews.filter((r) => r.gene_index_now === props.row.gene_index))

  const open = ref(false)
  const verdict = ref<Verdict | ''>('')
  const comment = ref('')
  const busy = ref(false)
  const error = ref<string | null>(null)
  watch(open, (o) => { if (o) { verdict.value = ''; comment.value = ''; error.value = null } })
  const ready = computed(() => !!verdict.value && !!comment.value.trim() && !busy.value)

  async function submit() {
    if (!ready.value) return
    busy.value = true; error.value = null
    try {
      const res = await fetch(apiUrl('/api/reviews'), {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ disease: props.diseaseIndex, gene: props.row.gene_index,
                               verdict: verdict.value, comment: comment.value }),
      })
      const body = await res.json().catch(() => null)
      // The POST returns only once the file is written; anything else keeps the dialog open.
      if (!res.ok) throw new Error(body?.detail ?? `HTTP ${res.status}`)
      emit('recorded', { ...body, gene_index_now: props.row.gene_index, verdict_label: VERDICTS[body.verdict as Verdict] })
      open.value = false
    } catch (e) {
      error.value = `The review was not recorded: ${e instanceof Error ? e.message : String(e)}`
    } finally { busy.value = false }
  }

  const when = (iso: string) => new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
</script>

<template>
  <div class="flex flex-col gap-2">
    <div class="flex flex-wrap items-center gap-2">
      <Button size="sm" variant="outline" @click="open = true"><CommentAdd class="size-4" /> Record review</Button>
      <span v-if="mine.length" class="text-xs text-muted-foreground">
        {{ mine.length }} review{{ mine.length > 1 ? 's' : '' }} recorded for this pair
      </span>
    </div>

    <ul v-if="mine.length" class="flex flex-col gap-2">
      <li v-for="(r, i) in mine" :key="r.review_id" class="rounded-lg border p-3 text-sm"
          :class="i > 0 ? 'opacity-70' : ''">
        <div class="flex flex-wrap items-center gap-2">
          <StatusBadge :status="verdictStatus(r.verdict)">{{ r.verdict_label ?? r.verdict }}</StatusBadge>
          <span class="text-xs text-muted-foreground">
            {{ r.reviewer }} · {{ when(r.reviewed_at) }} · rank {{ r.rank }} on {{ r.model_name }}
            <template v-if="i > 0"> · superseded</template>
          </span>
        </div>
        <p class="mt-1.5 whitespace-pre-line leading-relaxed">{{ r.comment }}</p>
      </li>
    </ul>

    <Dialog v-model:open="open">
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Review {{ row.gene_name }} for {{ diseaseName }}</DialogTitle>
          <DialogDescription>
            Your judgement, recorded in DSS with your login, the gene's rank ({{ row.rank_in_disease }}) and the
            model. Reviews are never edited: a new one supersedes this one on screen, and both are kept.
          </DialogDescription>
        </DialogHeader>
        <div class="flex flex-col gap-4">
          <RadioGroup v-model="verdict" class="flex flex-wrap gap-4">
            <div v-for="(label, v) in VERDICTS" :key="v" class="flex items-center gap-2">
              <RadioGroupItem :id="`verdict-${v}`" :value="v" />
              <Label :for="`verdict-${v}`">{{ label }}</Label>
            </div>
          </RadioGroup>
          <div class="flex flex-col gap-1.5">
            <Label for="review-comment">Why (required)</Label>
            <Textarea id="review-comment" v-model="comment" rows="5"
                      placeholder="What you checked, what decided it, and what the next stage should look at." />
          </div>
          <Alert v-if="error" variant="destructive"><AlertDescription>{{ error }}</AlertDescription></Alert>
        </div>
        <DialogFooter>
          <Button variant="outline" :disabled="busy" @click="open = false">Cancel</Button>
          <Button :disabled="!ready" @click="submit">{{ busy ? 'Recording…' : 'Record review' }}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>
