export const meta = {
  name: 'meaning-pilot',
  description: 'D039 pilot: questions written from page pictures, answered from the picture, from TrueDoc text and from plain text, then marked; held-out half returns counts only',
  phases: [
    { title: 'Write questions', detail: 'one helper per candidate page, sees only the picture' },
    { title: 'Answer', detail: 'three blind answerers per page: picture, text A, text B' },
    { title: 'Mark', detail: 'a marker sees question, true answer and given answer only' },
    { title: 'Arbitrate', detail: 'where the picture answer disagrees with the question writer, a fresh look at the picture' },
  ],
}

const ROOT = args.root
const PER_HALF = 15
const pages = args.pages.map(p => ({
  pid: p[0], held: p[0][0] === 'h', kind: p[1],
  pics: [ROOT + 'pic/' + p[2] + '_whole.png', ROOT + 'pic/' + p[2] + '_top.png', ROOT + 'pic/' + p[2] + '_bottom.png'],
  td: ROOT + 'td/' + p[3] + '.md', plain: ROOT + 'plain/' + p[4] + '.txt',
}))

const KINDS = ['covered', 'limit_or_excess', 'exclusion_list', 'mark', 'time_limit', 'definition', 'other']
const TYPES = ['yes_no_optional', 'amount', 'list', 'phrase']

const WRITE_SCHEMA = { type: 'object', required: ['task_id', 'usable', 'reason', 'questions'], properties: {
  task_id: { type: 'string' }, usable: { type: 'boolean' }, reason: { type: 'string' },
  questions: { type: 'array', items: { type: 'object', required: ['id', 'kind', 'question', 'answer_type', 'answer', 'evidence', 'doubt', 'doubt_note'], properties: {
    id: { type: 'string' }, kind: { type: 'string', enum: KINDS }, question: { type: 'string' },
    answer_type: { type: 'string', enum: TYPES }, answer: { type: 'string' }, evidence: { type: 'string' },
    doubt: { type: 'boolean' }, doubt_note: { type: 'string' } } } } } }

const ANSWER_SCHEMA = { type: 'object', required: ['task_id', 'answers'], properties: {
  task_id: { type: 'string' },
  answers: { type: 'array', items: { type: 'object', required: ['id', 'answer', 'where'], properties: {
    id: { type: 'string' }, answer: { type: 'string' }, where: { type: 'string' } } } } } }

const MARK_SCHEMA = { type: 'object', required: ['task_id', 'marks'], properties: {
  task_id: { type: 'string' },
  marks: { type: 'array', items: { type: 'object', required: ['id', 'verdict', 'note'], properties: {
    id: { type: 'string' }, verdict: { type: 'string', enum: ['correct', 'partial', 'missing', 'wrong'] }, note: { type: 'string' } } } } } }

const ARBITER_SCHEMA = { type: 'object', required: ['task_id', 'rulings'], properties: {
  task_id: { type: 'string' },
  rulings: { type: 'array', items: { type: 'object', required: ['id', 'right', 'page_says', 'ambiguous', 'note'], properties: {
    id: { type: 'string' }, right: { type: 'string', enum: ['A', 'B', 'both', 'neither'] }, page_says: { type: 'string' },
    ambiguous: { type: 'boolean' }, note: { type: 'string' } } } } } }

const LOOK = p => `Read exactly these three image files with the Read tool, and nothing else - do not list folders, search, or open any other file:
  ${p.pics[0]}   (the whole page)
  ${p.pics[1]}   (its top half, larger)
  ${p.pics[2]}   (its bottom half, larger; the two halves overlap)
They are one page of an Australian general-insurance document (a product disclosure statement or the like).`

const FORMAT = `Answer formats, by answer_type:
  yes_no_optional - start with Yes, No or Optional, then any condition the page attaches, in a few words ("Yes, if the home is occupied").
  amount - the figure exactly as printed, with its unit ("$2,500 per item", "72 hours", "10% of the sum insured").
  list - the items, separated by "; ".
  phrase - at most 15 words.`

function writePrompt(p) {
  return `TASK-ID: ${p.pid}/write
You are helping to build a reading test for insurance documents. ${LOOK(p)}

First decide whether the page is usable. It is NOT usable if it is a cover, a contents list, an index, a blank or near-blank page, a page of contact or complaints details only, or otherwise holds nothing a policyholder would ask about their cover (what is covered, what is not, limits, excesses, conditions, time limits, definitions, how a claim is settled). If not usable, return usable=false with the reason and no questions.

If it is usable, write 5 questions that a policyholder might ask and that THIS PAGE ALONE answers (fewer only if the page truly cannot support five; never pad). Rules:
- Whoever answers will see only this page. Name the cover, section or item in the question as the page names it. Never say "the table above" or "this section".
- The answer must be exactly what the page says. Use no outside knowledge of insurance.
- Spread the questions over these kinds as far as the page allows: covered (is X covered, and on what condition), limit_or_excess (a dollar amount, percentage or number), exclusion_list (is Y in a list of things covered or not covered), mark (what a tick, cross or other symbol says), time_limit, definition, other.
- If the page has a table, at least TWO questions must be table look-ups whose answer depends on reading the right row AND the right column. If it has ticks, crosses or similar marks, at least one question must depend on them. If it has a bulleted or numbered list, at least one must depend on what is, or is not, in the list.
- Prefer questions where a mistake would matter to the reader, and where the answer depends on which words belong together: which limit goes with which item, which condition with which cover, which heading a line sits under.
- id: q1, q2, ...
- evidence: the few words on the page that settle it, and where they are ("table, row Jewellery, column Limit").
- doubt: true if the page is ambiguous or hard to read there, or you are not sure of the answer; say why in doubt_note (else leave doubt_note empty).
${FORMAT}
Echo the TASK-ID in task_id.`
}

function questionsBlock(qs) {
  return qs.map(q => `${q.id} [answer_type: ${q.answer_type}] ${q.question}`).join('\n')
}

function answerPicPrompt(p, qs) {
  return `TASK-ID: ${p.pid}/answer-picture
${LOOK(p)}

Answer each question below ONLY from what this page shows. Use no outside knowledge of insurance. If the page does not say, answer exactly NOT_STATED.
${FORMAT}
For each, give "where": a few words on where on the page you found it (empty if NOT_STATED). Echo the TASK-ID in task_id.

Questions:
${questionsBlock(qs)}`
}

function answerTextPrompt(p, qs, path, role) {
  return `TASK-ID: ${p.pid}/${role}
Read exactly this one file with the Read tool, and nothing else - do not list folders, search, or open any other file:
  ${path}
It is the text of one page of an Australian general-insurance document. It may hold markdown or HTML tables; read them as tables (a cell belongs to its row and to the heading of its column).

Answer each question below ONLY from what this text says, as a careful reader of this text would. Use no outside knowledge of insurance and do not repair the text from what you expect such a document to say: if, as written, it does not let a reader be sure, answer exactly NOT_STATED.
${FORMAT}
For each, give "where": the few words of the text you relied on (empty if NOT_STATED). Echo the TASK-ID in task_id.

Questions:
${questionsBlock(qs)}`
}

function markPrompt(p, qs, answers, role) {
  const byId = {}
  for (const a of answers) byId[a.id] = a.answer
  const items = qs.map(q => `${q.id} [${q.answer_type}] ${q.question}\n   TRUE ANSWER: ${q.answer}\n   GIVEN ANSWER: ${byId[q.id] === undefined ? 'NOT_STATED' : byId[q.id]}`).join('\n')
  return `TASK-ID: ${p.pid}/mark-${role}
Use no tools. Mark each given answer against the true answer. Judge as a policyholder would be affected:
  correct - a reader acting on the given answer would be exactly as right as one acting on the true answer: the same Yes/No/Optional and the same condition in substance; the same figure and unit; the same list items, in any order; the same meaning.
  partial - right as far as it goes but it leaves out, or adds, something that matters: a condition dropped, a list item missing or extra, a range where the truth is one figure.
  missing - the given answer is NOT_STATED, or says it cannot tell.
  wrong - a different answer, which would mislead the reader.
Formatting does not matter ("$1,000" = "1000 dollars"). Do not be lenient on figures: a different number is wrong. Do not be lenient on Yes against No.
Give a short note for anything not correct. Echo the TASK-ID in task_id.

${items}`
}

function arbiterPrompt(p, items) {
  const body = items.map(it => `${it.id} ${it.question}\n   ANSWER A: ${it.a}\n   ANSWER B: ${it.b}`).join('\n')
  return `TASK-ID: ${p.pid}/arbitrate
${LOOK(p)}

Two people answered each question below from this page and did not agree. Look at the page yourself and say which answer is what the page says: A, B, both (they say the same thing in different words) or neither. Give "page_says": the answer as the page has it. Set ambiguous=true if the page itself can fairly be read both ways, or the question is unclear. Use no outside knowledge of insurance. Echo the TASK-ID in task_id.

${body}`
}

// ---- mechanical cross-check of the marker, for the two answer types a machine can compare
function numbers(s) { return ((s || '').match(/\d[\d,]*(?:\.\d+)?/g) || []).map(x => x.replace(/,/g, '')).sort().join('|') }
function firstWord(s) { const m = (s || '').toLowerCase().match(/[a-z_]+/); return m ? m[0] : '' }
function mechanical(q, given) {
  if ((given || '').trim() === 'NOT_STATED') return 'missing'
  if (q.answer_type === 'amount') { const t = numbers(q.answer); return t ? (t === numbers(given) ? 'same' : 'different') : 'na' }
  if (q.answer_type === 'yes_no_optional') { const t = firstWord(q.answer); return ['yes', 'no', 'optional'].includes(t) ? (t === firstWord(given) ? 'same' : 'different') : 'na' }
  return 'na'
}

// ---- 1. questions, from the picture only
phase('Write questions')
const written = await parallel(pages.map(p => () =>
  agent(writePrompt(p), { label: `write:${p.pid}`, phase: 'Write questions', schema: WRITE_SCHEMA })
    .then(r => ({ p, r }))))

// the barrier is needed: the pilot's pages are the first PER_HALF usable ones of each half, in the order of the draw
const chosen = []
const usability = { tuned: { seen: 0, unusable: 0, failed: 0 }, held: { seen: 0, unusable: 0, failed: 0 } }
for (const half of [false, true]) {
  let n = 0
  for (const w of written) {
    if (!w || w.p.held !== half) continue
    const u = usability[half ? 'held' : 'tuned']
    if (n >= PER_HALF) continue
    u.seen++
    if (!w.r) { u.failed++; continue }
    if (!w.r.usable || !w.r.questions || w.r.questions.length < 3) { u.unusable++; continue }
    chosen.push({ p: w.p, qs: w.r.questions.map((q, i) => Object.assign({}, q, { id: 'q' + (i + 1) })) })
    n++
  }
  log(`${half ? 'held-out' : 'tuned-on'} half: ${n} usable pages of ${usability[half ? 'held' : 'tuned'].seen} looked at`)
}

// ---- 2-4. answer, mark, arbitrate: page by page, no barrier
const records = await pipeline(chosen,
  c => parallel([
    () => agent(answerPicPrompt(c.p, c.qs), { label: `answer-picture:${c.p.pid}`, phase: 'Answer', schema: ANSWER_SCHEMA }),
    () => agent(answerTextPrompt(c.p, c.qs, c.p.td, 'answer-text-a'), { label: `answer-truedoc:${c.p.pid}`, phase: 'Answer', schema: ANSWER_SCHEMA }),
    () => agent(answerTextPrompt(c.p, c.qs, c.p.plain, 'answer-text-b'), { label: `answer-plain:${c.p.pid}`, phase: 'Answer', schema: ANSWER_SCHEMA }),
  ]).then(a => ({ pic: a[0] ? a[0].answers : null, td: a[1] ? a[1].answers : null, plain: a[2] ? a[2].answers : null })),
  (ans, c) => parallel(['pic', 'td', 'plain'].map(src => () => ans[src]
    ? agent(markPrompt(c.p, c.qs, ans[src], src === 'pic' ? 'p' : src === 'td' ? 'a' : 'b'), { label: `mark-${src}:${c.p.pid}`, phase: 'Mark', schema: MARK_SCHEMA, effort: 'medium' })
    : Promise.resolve(null)))
    .then(m => ({ ans, marks: { pic: m[0] ? m[0].marks : null, td: m[1] ? m[1].marks : null, plain: m[2] ? m[2].marks : null } })),
  (am, c, index) => {
    const verdictOf = (src, id) => { const m = (am.marks[src] || []).find(x => x.id === id); return m ? m.verdict : 'unmarked' }
    const answerOf = (src, id) => { const a = (am.ans[src] || []).find(x => x.id === id); return a ? a.answer : 'NOT_STATED' }
    const disputed = c.qs.filter(q => verdictOf('pic', q.id) !== 'correct')
    const flip = index % 2 === 1
    const items = disputed.map(q => ({ id: q.id, question: q.question, a: flip ? answerOf('pic', q.id) : q.answer, b: flip ? q.answer : answerOf('pic', q.id) }))
    const next = items.length
      ? agent(arbiterPrompt(c.p, items), { label: `arbitrate:${c.p.pid}`, phase: 'Arbitrate', schema: ARBITER_SCHEMA })
      : Promise.resolve(null)
    return next.then(arb => {
      const truthLetter = flip ? 'B' : 'A'
      return { pid: c.p.pid, held: c.p.held, page_kind: c.p.kind, questions: c.qs.map(q => {
        const ruling = arb ? (arb.rulings || []).find(x => x.id === q.id) : null
        const truthStands = ruling ? (ruling.right === truthLetter || ruling.right === 'both') : null
        const v = { pic: verdictOf('pic', q.id), td: verdictOf('td', q.id), plain: verdictOf('plain', q.id) }
        const given = { pic: answerOf('pic', q.id), td: answerOf('td', q.id), plain: answerOf('plain', q.id) }
        const mech = { td: mechanical(q, given.td), plain: mechanical(q, given.plain) }
        const conflict = src => (mech[src] === 'same' && v[src] !== 'correct' && v[src] !== 'partial') || (mech[src] === 'different' && v[src] === 'correct')
        return { id: q.id, kind: q.kind, answer_type: q.answer_type, question: q.question, truth: q.answer, evidence: q.evidence,
          writer_doubt: q.doubt, doubt_note: q.doubt_note, given, verdict: v,
          arbiter: ruling ? { truth_stands: truthStands, page_says: ruling.page_says, ambiguous: ruling.ambiguous, note: ruling.note } : null,
          for_owner: !!(q.doubt || (ruling && (!truthStands || ruling.ambiguous))),
          marker_conflict: { td: conflict('td'), plain: conflict('plain') } }
      }) }
    })
  })

// ---- 5. the numbers
function tally(recs) {
  const blank = () => ({ correct: 0, partial: 0, missing: 0, wrong: 0, unmarked: 0 })
  const out = { pages: recs.length, questions: 0, counted: 0, thrown_out_picture_answer_not_correct: 0, picture: blank(),
    truedoc: blank(), plain: blank(), for_owner: 0, arbitrated: 0, arbiter_sided_with_the_question_writer: 0, arbiter_ambiguous: 0,
    marker_conflicts_with_the_mechanical_check: 0, by_question_kind: {}, by_page_kind: {}, by_answer_type: {} }
  for (const r of recs) for (const q of r.questions) {
    out.questions++
    out.picture[q.verdict.pic]++
    if (q.for_owner) out.for_owner++
    if (q.arbiter) { out.arbitrated++; if (q.arbiter.truth_stands) out.arbiter_sided_with_the_question_writer++; if (q.arbiter.ambiguous) out.arbiter_ambiguous++ }
    if (q.marker_conflict.td || q.marker_conflict.plain) out.marker_conflicts_with_the_mechanical_check++
    if (q.verdict.pic !== 'correct') { out.thrown_out_picture_answer_not_correct++; continue }
    out.counted++
    out.truedoc[q.verdict.td]++
    out.plain[q.verdict.plain]++
    for (const [group, key] of [['by_question_kind', q.kind], ['by_page_kind', r.page_kind], ['by_answer_type', q.answer_type]]) {
      const g = out[group][key] || (out[group][key] = { counted: 0, truedoc_correct: 0, plain_correct: 0, truedoc_wrong: 0, plain_wrong: 0 })
      g.counted++
      if (q.verdict.td === 'correct') g.truedoc_correct++
      if (q.verdict.plain === 'correct') g.plain_correct++
      if (q.verdict.td === 'wrong') g.truedoc_wrong++
      if (q.verdict.plain === 'wrong') g.plain_wrong++
    }
  }
  return out
}

const done = records.filter(Boolean)
const tuned = done.filter(r => !r.held)
const held = done.filter(r => r.held)
log(`pages finished: tuned-on ${tuned.length}, held out ${held.length}; pages lost on the way: ${chosen.length - done.length}`)
return {
  usability,
  pages_lost_in_the_pipeline: chosen.length - done.length,
  tuned_on: { numbers: tally(tuned), records: tuned },
  held_out: { numbers: tally(held), note: 'counts only: no question, answer or page of this half is returned',
    // marks without words: which held-out questions were not correct from a text, or await the owner, and how each was marked
    marks_without_words: held.flatMap(r => r.questions
      .filter(q => q.for_owner || q.verdict.pic !== 'correct' || q.verdict.td !== 'correct' || q.verdict.plain !== 'correct')
      .map(q => ({ pid: r.pid, id: q.id, page_kind: r.page_kind, kind: q.kind, answer_type: q.answer_type, for_owner: q.for_owner, verdict: q.verdict }))) },
}
