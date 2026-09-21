export const meta = {
  name: 'meaning-test-structure',
  description: 'D039 round 2: questions a keyword search cannot answer, put to a strong and a small reader, from TrueDoc text and from a plain dump',
  phases: [
    { title: 'Write questions', detail: 'one helper a page, sees only the picture; questions a keyword search cannot settle' },
    { title: 'Answer', detail: 'a strong and a small reader, each blind, on each of the two texts' },
    { title: 'Mark', detail: 'one marker a page for each reader' },
    { title: 'Settle', detail: 'where both texts missed, a fresh look at the picture' },
  ],
}

const ROOT = args.root
const pages = args.pages.map((p, i) => {
  const td = ROOT + 'texts/' + p[3] + '.txt'
  const plain = ROOT + 'texts/' + p[4] + '.txt'
  const swap = i % 2 === 1              // which text is called A changes page by page
  return {
    pid: p[0], held: p[0][0] === 'h', kind: p[1],
    pics: [ROOT + 'pic/' + p[2] + '_whole.png', ROOT + 'pic/' + p[2] + '_top.png', ROOT + 'pic/' + p[2] + '_bottom.png'],
    td, plain, qold: ROOT + 'qold/' + p[5] + '.json',
    A: swap ? plain : td, B: swap ? td : plain,
    sourceOf: { A: swap ? 'plain' : 'truedoc', B: swap ? 'truedoc' : 'plain' },
  }
})

const SHAPES = ['count_rows', 'compare_rows', 'two_columns', 'same_word_twice', 'absent', 'far_apart']
const TYPES = ['yes_no_optional', 'amount', 'list', 'phrase', 'number']

const HARD_SCHEMA = { type: 'object', required: ['task_id', 'questions'], properties: {
  task_id: { type: 'string' },
  questions: { type: 'array', items: { type: 'object', required: ['id', 'shape', 'question', 'answer_type', 'answer', 'evidence', 'why_search_fails', 'doubt'], properties: {
    id: { type: 'string' }, shape: { type: 'string', enum: SHAPES }, question: { type: 'string' },
    answer_type: { type: 'string', enum: TYPES }, answer: { type: 'string' }, evidence: { type: 'string' },
    why_search_fails: { type: 'string' }, doubt: { type: 'boolean' } } } } } }

const ANSWER_SCHEMA = { type: 'object', required: ['task_id', 'answers'], properties: {
  task_id: { type: 'string' },
  answers: { type: 'array', items: { type: 'object', required: ['id', 'answer'], properties: {
    id: { type: 'string' }, answer: { type: 'string' }, where: { type: 'string' } } } } } }

const MARK_SCHEMA = { type: 'object', required: ['task_id', 'marks'], properties: {
  task_id: { type: 'string' },
  marks: { type: 'array', items: { type: 'object', required: ['source', 'id', 'verdict'], properties: {
    source: { type: 'string', enum: ['A', 'B'] }, id: { type: 'string' },
    verdict: { type: 'string', enum: ['correct', 'partial', 'missing', 'wrong'] }, note: { type: 'string' } } } } } }

const SETTLE_SCHEMA = { type: 'object', required: ['task_id', 'rulings'], properties: {
  task_id: { type: 'string' },
  rulings: { type: 'array', items: { type: 'object', required: ['id', 'page_answers', 'page_says'], properties: {
    id: { type: 'string' }, page_answers: { type: 'boolean' }, page_says: { type: 'string' }, note: { type: 'string' } } } } } }

const LOOK = p => `Read exactly these three image files with the Read tool, and nothing else - do not list folders, search, or open any other file:
  ${p.pics[0]}   (the whole page)
  ${p.pics[1]}   (its top half, larger)
  ${p.pics[2]}   (its bottom half, larger; the two halves overlap)
They are one page of an Australian general-insurance document (a product disclosure statement or the like).`

const FORMAT = `Answer formats, by answer_type:
  yes_no_optional - start with Yes, No or Optional, then any condition the page attaches, in a few words.
  amount - the figure exactly as printed, with its unit ("$2,500 per item", "10% of the sum insured").
  number - a bare count ("4").
  list - the items, separated by "; ".
  phrase - at most 15 words.`

function writePrompt(p) {
  return `TASK-ID: ${p.pid}/hard
${LOOK(p)}

An earlier test of this page asked five straightforward questions, and a reader answered them from almost any text of the page: each question named the row or the heading it was about, so finding that word and reading the next few words was enough. Your job is to write five questions of a different kind.

Write 5 questions that a policyholder might really ask, that THIS PAGE ALONE answers, and **that cannot be answered by finding one word of the question in the text and reading the few words that follow it**. A reader who has the page's words but has lost how they were arranged - which cell sits in which column, which line belongs under which heading, what order things came in - should get them wrong or be unable to tell.

The shapes, and at least three different ones among your five:
  count_rows - counting or naming every entry that meets a condition ("how many of the events listed are optional?", "which events are not covered at all?").
  compare_rows - a comparison or superlative across entries ("which listed item has the largest limit, and what is it?").
  two_columns - a value that only the right row AND the right column give, on a row that shows several bare figures.
  same_word_twice - a term the page uses in more than one place with different answers; the question must say which one it means.
  absent - whether something is NOT among what the page lists.
  far_apart - a condition, heading or footnote in one part of the page that governs an item in another part.
If the page holds a table, at least two questions must be count_rows, compare_rows or two_columns. If the page has no table, lean on same_word_twice, absent and far_apart.

Rules.
- Whoever answers will see only this page, as text. Name things as the page names them; never say "the table above" or "this section".
- The answer must be exactly what the page says, short, and of the given answer_type. Use no outside knowledge of insurance.
- id: n1, n2, n3, n4, n5.
- evidence: what settles it, and where ("table, row Jewellery, column Limit"; "the four rows marked Optional").
- why_search_fails: one line - what a reader who only found the keyword would get wrong, or why they could not tell.
- doubt: true if the page is ambiguous there or you are unsure.
- Write fewer than five only if the page truly cannot support five of these shapes; never pad.
${FORMAT}
Echo the TASK-ID in task_id.`
}

function answerPrompt(p, qs, path, role) {
  const extra = qs.map(q => `${q.id} [answer_type: ${q.answer_type}] ${q.question}`).join('\n')
  return `TASK-ID: ${p.pid}/${role}
Read exactly these two files with the Read tool, and nothing else - do not list folders, search, or open any other file:
  ${path}
  ${p.qold}
The first is the text of one page of an Australian general-insurance document. It may hold markdown or HTML tables; it may instead be a flat dump in which a table's rows and columns have run together. Read it as it is. The second is a JSON file holding questions, each with an id and an answer_type.

Answer **every question in the JSON file**, and **every question listed below**, ONLY from what the text says, as a careful reader of this text would. Use no outside knowledge of insurance, and do not repair the text from what you expect such a document to say: if, as written, it does not let a reader be sure, answer exactly NOT_STATED.
${FORMAT}
Give "where": at most eight words of the text you relied on (empty if NOT_STATED). Report each answer under the id it was asked with. Echo the TASK-ID in task_id.

Questions besides those in the file:
${extra}`
}

function markPrompt(p, qs, answers, tier) {
  const truths = qs.map(q => `${q.id} [${q.answer_type}] ${q.question}\n   TRUE ANSWER: ${q.answer}`).join('\n')
  const given = src => (answers[src] || []).map(a => `${a.id}: ${a.answer}`).join('\n')
  return `TASK-ID: ${p.pid}/mark-${tier}
Read exactly this one file with the Read tool, and nothing else:
  ${p.qold}
It is a JSON file of questions; each has an id, the question, and "answer", which is the TRUE answer to it.

Here are the true answers to five further questions:
${truths}

Two people each read a different text of the same page and answered all of these questions. Text A's answers:
${given('A')}

Text B's answers:
${given('B')}

Mark every answer of A and of B against its true answer. Judge as a policyholder would be affected:
  correct - a reader acting on the given answer would be exactly as right as one acting on the true answer: the same Yes/No/Optional and the same condition in substance; the same figure and unit; the same count; the same list items, in any order; the same meaning.
  partial - right as far as it goes, but it leaves out or adds something that matters: a condition dropped, a list item missing or extra, a count of the right things but the wrong number.
  missing - the answer is NOT_STATED, or says it cannot tell.
  wrong - a different answer, which would mislead the reader.
Formatting does not matter ("$1,000" = "1000 dollars"). Do not be lenient on figures, counts, or Yes against No. Give a short note for anything not correct.

Return one entry for every id under source A and one for every id under source B. Echo the TASK-ID in task_id.`
}

function settlePrompt(p, items) {
  const body = items.map(it => it.text ? `${it.id} ${it.text}` : `${it.id} (this one is in the JSON file)`).join('\n')
  return `TASK-ID: ${p.pid}/settle
${LOOK(p)}
Also read this one file with the Read tool: ${p.qold} - a JSON file of questions, each with an id.

Two texts of this page were both unable to answer the questions listed below, or answered them differently from what was expected. For each, look at the page yourself and say whether **the page itself** answers it (page_answers), and what the page says (page_says, short). Use no outside knowledge of insurance. Echo the TASK-ID in task_id.

${body}`
}

phase('Write questions')
const records = await pipeline(pages,
  // 1. five questions a keyword search cannot settle, from the picture only
  p => agent(writePrompt(p), { label: `questions:${p.pid}`, phase: 'Write questions', schema: HARD_SCHEMA, model: 'sonnet' })
    .then(r => (r && r.questions ? r.questions.map((q, i) => Object.assign({}, q, { id: 'n' + (i + 1) })) : [])),

  // 2. two readers, each blind, on each of the two texts; every answerer takes the older questions too
  (qs, p) => parallel([
    () => agent(answerPrompt(p, qs, p.A, 'strong-A'), { label: `strong A:${p.pid}`, phase: 'Answer', schema: ANSWER_SCHEMA, model: 'sonnet' }),
    () => agent(answerPrompt(p, qs, p.B, 'strong-B'), { label: `strong B:${p.pid}`, phase: 'Answer', schema: ANSWER_SCHEMA, model: 'sonnet' }),
    () => agent(answerPrompt(p, qs, p.A, 'small-A'), { label: `small A:${p.pid}`, phase: 'Answer', schema: ANSWER_SCHEMA, model: 'haiku', effort: 'low' }),
    () => agent(answerPrompt(p, qs, p.B, 'small-B'), { label: `small B:${p.pid}`, phase: 'Answer', schema: ANSWER_SCHEMA, model: 'haiku', effort: 'low' }),
  ]).then(a => ({ qs, given: {
    strong: { A: a[0] ? a[0].answers : null, B: a[1] ? a[1].answers : null },
    small: { A: a[2] ? a[2].answers : null, B: a[3] ? a[3].answers : null } } })),

  // 3. one marker a page for each reader; it sees question, true answer and given answer, never the page
  (r, p) => parallel(['strong', 'small'].map(tier => () =>
    agent(markPrompt(p, r.qs, r.given[tier], tier), { label: `mark ${tier}:${p.pid}`, phase: 'Mark', schema: MARK_SCHEMA, model: 'sonnet', effort: 'medium' })))
    .then(m => Object.assign({}, r, { marks: { strong: m[0] ? m[0].marks : null, small: m[1] ? m[1].marks : null } })),

  // 4. where both texts missed one, look at the page: was it the texts, or was the question unanswerable?
  (r, p) => {
    const verdict = (tier, src, id) => { const m = (r.marks[tier] || []).find(x => x.source === src && x.id === id); return m ? m.verdict : 'unmarked' }
    const ids = []
    for (const q of r.qs) ids.push({ id: q.id, text: q.question })
    for (let i = 1; i <= 5; i++) ids.push({ id: 'o' + i, text: null })
    const bothMissed = ids.filter(it => verdict('strong', 'A', it.id) !== 'correct' && verdict('strong', 'B', it.id) !== 'correct')
    const next = bothMissed.length
      ? agent(settlePrompt(p, bothMissed), { label: `settle:${p.pid}`, phase: 'Settle', schema: SETTLE_SCHEMA, model: 'sonnet' })
      : Promise.resolve(null)
    return next.then(s => {
      const rulings = s ? (s.rulings || []) : []
      const rows = ids.map(it => {
        const ruling = rulings.find(x => x.id === it.id) || null
        const set = it.id[0] === 'n' ? 'new' : 'old'
        const q = r.qs.find(x => x.id === it.id) || null
        const cell = {}
        for (const tier of ['strong', 'small']) for (const src of ['A', 'B']) {
          cell[tier + '_' + p.sourceOf[src]] = { verdict: verdict(tier, src, it.id),
            answer: ((r.given[tier][src] || []).find(a => a.id === it.id) || {}).answer || 'NOT_STATED' }
        }
        return { id: it.id, set, shape: q ? q.shape : null, answer_type: q ? q.answer_type : null,
          question: q ? q.question : null, truth: q ? q.answer : null, evidence: q ? q.evidence : null,
          why_search_fails: q ? q.why_search_fails : null, writer_doubt: q ? !!q.doubt : null,
          cells: cell, settled: ruling, page_answers: ruling ? ruling.page_answers : true }
      })
      return { pid: p.pid, held: p.held, page_kind: p.kind, questions_written: r.qs.length, rows }
    })
  })

function tally(recs) {
  const cells = {}
  const blank = () => ({ correct: 0, partial: 0, missing: 0, wrong: 0, unmarked: 0 })
  const out = { pages: recs.length, asked: 0, counted: 0, dropped_page_does_not_answer: 0, by_set: {}, by_shape: {}, by_page_kind: {} }
  for (const r of recs) for (const row of r.rows) {
    out.asked++
    if (!row.page_answers) { out.dropped_page_does_not_answer++; continue }
    out.counted++
    for (const key of Object.keys(row.cells)) {
      const c = cells[key] || (cells[key] = blank())
      c[row.cells[key].verdict]++
      const groups = [['by_set', row.set], ['by_page_kind', r.page_kind]]
      if (row.shape) groups.push(['by_shape', row.shape])
      for (const [group, name] of groups) {
        const g = out[group][name] || (out[group][name] = {})
        const gc = g[key] || (g[key] = blank())
        gc[row.cells[key].verdict]++
      }
    }
  }
  out.overall = cells
  return out
}

const done = records.filter(Boolean)
const tuned = done.filter(r => !r.held)
const held = done.filter(r => r.held)
log(`pages finished: tuned-on ${tuned.length}, held out ${held.length}; lost on the way ${pages.length - done.length}`)
return {
  pages_lost: pages.length - done.length,
  tuned_on: { numbers: tally(tuned), records: tuned },
  held_out: { numbers: tally(held), note: 'counts only: no question, answer or page of this half is returned',
    marks_without_words: held.flatMap(r => r.rows
      .filter(row => Object.keys(row.cells).some(k => row.cells[k].verdict !== 'correct') || !row.page_answers)
      .map(row => ({ pid: r.pid, id: row.id, set: row.set, shape: row.shape, answer_type: row.answer_type,
        page_kind: r.page_kind, page_answers: row.page_answers,
        verdicts: Object.fromEntries(Object.keys(row.cells).map(k => [k, row.cells[k].verdict])) }))) },
}
