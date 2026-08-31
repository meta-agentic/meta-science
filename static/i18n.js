/* Interface translations, embedded — no network, no external font or script, so the
   pages stay self-contained (tests/test_container_contract.py asserts that).

   What is NOT translated, deliberately: anything the agent itself sees or produces.
   The world briefs, the observer narratives, the JSON and the receipts stay in
   English because they are the experiment's input and output — anonymisation is
   asserted against an English lexicon, and translating a world would change the
   thing being measured. The interface localises; the science does not. */

const LANGS = {
  en: {name: "English",  dir: "ltr"},
  it: {name: "Italiano", dir: "ltr"},
  fr: {name: "Français", dir: "ltr"},
  es: {name: "Español",  dir: "ltr"},
  de: {name: "Deutsch",  dir: "ltr"},
  ja: {name: "日本語",    dir: "ltr"},
  zh: {name: "中文",      dir: "ltr"},
  ar: {name: "العربية",   dir: "rtl"},
};

const T = {
  lede: {
    en: "An agent that does science on worlds it has never seen — forming hypotheses, designing its own experiments, and being refuted by them — and that improves its own method only when a frozen benchmark proves the improvement real.",
    it: "Un agente che fa scienza su mondi che non ha mai visto — formula ipotesi, progetta i propri esperimenti e ne viene smentito — e che migliora il proprio metodo solo quando un benchmark congelato dimostra che il miglioramento è reale.",
    fr: "Un agent qui fait de la science sur des mondes qu'il n'a jamais vus — il formule des hypothèses, conçoit ses propres expériences et s'y fait réfuter — et qui n'améliore sa méthode que lorsqu'un banc d'essai figé prouve que le gain est réel.",
    es: "Un agente que hace ciencia en mundos que nunca ha visto — formula hipótesis, diseña sus propios experimentos y queda refutado por ellos — y que mejora su método solo cuando un banco de pruebas congelado demuestra que la mejora es real.",
    de: "Ein Agent, der Wissenschaft auf Welten betreibt, die er nie gesehen hat — er bildet Hypothesen, entwirft eigene Experimente und wird von ihnen widerlegt — und verbessert seine Methode nur, wenn ein eingefrorener Benchmark die Verbesserung belegt.",
    ja: "一度も見たことのない世界で科学を行うエージェント。仮説を立て、自ら実験を設計し、その実験に反証される。そして凍結されたベンチマークが改善を証明したときにのみ、自分の手法を改良する。",
    zh: "一个在从未见过的世界中进行科学研究的智能体：提出假设、自行设计实验、并被实验推翻；只有当冻结的基准证明改进属实时，它才会改进自己的方法。",
    ar: "وكيل يمارس العلم في عوالم لم يرها من قبل — يصوغ الفرضيات، ويصمم تجاربه بنفسه، وتدحضه تجاربه — ولا يحسّن منهجه إلا عندما يثبت معيار مجمَّد أن التحسّن حقيقي.",
  },
  world_h: {
    en: "The world under study", it: "Il mondo in esame", fr: "Le monde étudié",
    es: "El mundo en estudio", de: "Die untersuchte Welt", ja: "研究対象の世界",
    zh: "研究中的世界", ar: "العالم قيد الدراسة",
  },
  seed: {en: "seed", it: "seme", fr: "graine", es: "semilla", de: "Seed",
         ja: "シード", zh: "种子", ar: "البذرة"},
  depth: {en: "compound depth", it: "profondità composta", fr: "profondeur composée",
          es: "profundidad compuesta", de: "Verbundtiefe", ja: "複合の深さ",
          zh: "复合深度", ar: "عمق التركيب"},
  complex: {en: "complex variables (z = a + j·b)", it: "variabili complesse (z = a + j·b)",
            fr: "variables complexes (z = a + j·b)", es: "variables complejas (z = a + j·b)",
            de: "komplexe Variablen (z = a + j·b)", ja: "複素変数 (z = a + j·b)",
            zh: "复变量 (z = a + j·b)", ar: "متغيرات مركّبة (z = a + j·b)"},
  banner: {
    en: "this page works on the agent's side of the boundary",
    it: "questa pagina sta dal lato dell'agente rispetto al confine",
    fr: "cette page se tient du côté de l'agent, en deçà de la frontière",
    es: "esta página trabaja del lado del agente respecto al límite",
    de: "diese Seite steht auf der Agentenseite der Grenze",
    ja: "このページは境界のエージェント側にある",
    zh: "本页位于边界的智能体一侧",
    ar: "هذه الصفحة تقع على جانب الوكيل من الحدّ",
  },
  worldnote: {
    en: "Opaque labels, two affordances, no structure — everything below runs against exactly this view. The truth exists, but it is <em>revealed</em>, never used:",
    it: "Etichette opache, due affordance, nessuna struttura — tutto ciò che segue lavora esattamente su questa vista. La verità esiste, ma viene <em>rivelata</em>, mai usata:",
    fr: "Étiquettes opaques, deux affordances, aucune structure — tout ce qui suit s'exécute sur cette vue exacte. La vérité existe, mais elle est <em>révélée</em>, jamais utilisée :",
    es: "Etiquetas opacas, dos affordances, ninguna estructura — todo lo de abajo se ejecuta sobre esta misma vista. La verdad existe, pero se <em>revela</em>, nunca se usa:",
    de: "Undurchsichtige Bezeichnungen, zwei Handlungsmöglichkeiten, keine Struktur — alles Folgende läuft genau gegen diese Sicht. Die Wahrheit existiert, wird aber <em>enthüllt</em>, nie benutzt:",
    ja: "不透明なラベル、二つの操作、構造の情報なし — 以下のすべてはまさにこの視点に対して実行される。真実は存在するが、<em>明かされる</em>だけで、決して使われない:",
    zh: "不透明的标签、两种可用操作、没有结构信息 —— 下面的一切都基于这个视图运行。真相存在，但只会被<em>揭示</em>，绝不被使用：",
    ar: "تسميات مبهمة، إمكانيتان للفعل، ولا بنية — كل ما يلي يعمل على هذا العرض بالضبط. الحقيقة موجودة، لكنها <em>تُكشف</em> ولا تُستخدم أبدًا:",
  },
  inspector: {en: "full inspector →", it: "ispettore completo →", fr: "inspecteur complet →",
              es: "inspector completo →", de: "vollständiger Inspektor →",
              ja: "詳細インスペクタ →", zh: "完整检查器 →", ar: "← الفاحص الكامل"},
  s1: {en: "1 · Run the discovery loop", it: "1 · Esegui il ciclo di scoperta",
       fr: "1 · Lancer la boucle de découverte", es: "1 · Ejecutar el ciclo de descubrimiento",
       de: "1 · Den Entdeckungszyklus starten", ja: "1 · 発見ループを実行",
       zh: "1 · 运行发现循环", ar: "١ · شغّل حلقة الاكتشاف"},
  run: {en: "Run experiments on this world", it: "Esegui esperimenti su questo mondo",
        fr: "Lancer des expériences sur ce monde", es: "Ejecutar experimentos en este mundo",
        de: "Experimente auf dieser Welt ausführen", ja: "この世界で実験を実行",
        zh: "在此世界上运行实验", ar: "شغّل التجارب على هذا العالم"},
  runnote: {
    en: "Each prediction is committed <em>before</em> its experiment. The verdict is a comparison, never a question put to the model.",
    it: "Ogni previsione è depositata <em>prima</em> del suo esperimento. Il verdetto è un confronto, mai una domanda posta al modello.",
    fr: "Chaque prédiction est consignée <em>avant</em> son expérience. Le verdict est une comparaison, jamais une question posée au modèle.",
    es: "Cada predicción se registra <em>antes</em> de su experimento. El veredicto es una comparación, nunca una pregunta hecha al modelo.",
    de: "Jede Vorhersage wird <em>vor</em> ihrem Experiment festgehalten. Das Urteil ist ein Vergleich, nie eine Frage an das Modell.",
    ja: "各予測は実験の<em>前に</em>記録される。判定は比較であり、モデルへの問いかけではない。",
    zh: "每个预测都在其实验<em>之前</em>提交。判定是一次比较，绝不是向模型提出的问题。",
    ar: "كل تنبؤ يُسجَّل <em>قبل</em> تجربته. الحكم مقارنة، وليس سؤالًا يُطرح على النموذج.",
  },
  showdata: {en: "Show the simulation data", it: "Mostra i dati della simulazione",
             fr: "Afficher les données de simulation", es: "Mostrar los datos de la simulación",
             de: "Simulationsdaten anzeigen", ja: "シミュレーションデータを表示",
             zh: "显示模拟数据", ar: "أظهر بيانات المحاكاة"},
  reveal: {en: "Reveal this world's hidden truth", it: "Rivela la verità nascosta di questo mondo",
           fr: "Révéler la vérité cachée de ce monde", es: "Revelar la verdad oculta de este mundo",
           de: "Die verborgene Wahrheit dieser Welt enthüllen", ja: "この世界の隠された真実を明かす",
           zh: "揭示这个世界隐藏的真相", ar: "اكشف الحقيقة الخفية لهذا العالم"},
  bothnote: {en: "— both for the same world the agent just worked blind.",
             it: "— entrambi per lo stesso mondo su cui l'agente ha appena lavorato alla cieca.",
             fr: "— les deux pour le monde même sur lequel l'agent vient de travailler à l'aveugle.",
             es: "— ambos para el mismo mundo en el que el agente acaba de trabajar a ciegas.",
             de: "— beides für dieselbe Welt, an der der Agent gerade blind gearbeitet hat.",
             ja: "— どちらも、エージェントがいま盲目的に扱ったのと同じ世界のもの。",
             zh: "—— 两者都针对智能体刚刚盲目处理的同一个世界。",
             ar: "— كلاهما لنفس العالم الذي عمل عليه الوكيل للتو دون معرفة."},
  s2: {en: "2 · Let it improve its own method", it: "2 · Lascia che migliori il proprio metodo",
       fr: "2 · Laisser l'agent améliorer sa méthode", es: "2 · Deja que mejore su propio método",
       de: "2 · Lass es seine eigene Methode verbessern", ja: "2 · 自らの手法を改良させる",
       zh: "2 · 让它改进自己的方法", ar: "٢ · دعه يحسّن منهجه"},
  evolve: {en: "Propose a change, and rule on it", it: "Proponi una modifica e giudicala",
           fr: "Proposer un changement, puis trancher", es: "Propón un cambio y dictamina",
           de: "Eine Änderung vorschlagen und darüber urteilen", ja: "変更を提案し、判定を下す",
           zh: "提出变更，并对其裁决", ar: "اقترح تغييرًا واحكم عليه"},
  evolvenote: {
    en: "Gemini proposes against 24 held-out worlds — takes a minute. The benchmark is always the frozen real-domain set, whatever the controls above say: history stays comparable.",
    it: "Gemini propone contro 24 mondi tenuti da parte — richiede un minuto. Il benchmark è sempre l'insieme congelato nel dominio reale, qualunque cosa dicano i controlli qui sopra: la storia resta confrontabile.",
    fr: "Gemini propose face à 24 mondes réservés — cela prend une minute. Le banc d'essai reste toujours l'ensemble figé du domaine réel, quels que soient les réglages ci-dessus : l'historique demeure comparable.",
    es: "Gemini propone frente a 24 mundos reservados — tarda un minuto. El banco de pruebas es siempre el conjunto congelado del dominio real, digan lo que digan los controles de arriba: la historia sigue siendo comparable.",
    de: "Gemini schlägt gegen 24 zurückgehaltene Welten vor — dauert eine Minute. Der Benchmark ist stets der eingefrorene Satz im reellen Bereich, was die Regler oben auch sagen: die Historie bleibt vergleichbar.",
    ja: "Gemini は伏せられた 24 の世界に対して提案する — 1 分ほどかかる。上の設定が何であれ、ベンチマークは常に凍結された実数領域の集合であり、履歴は比較可能なままになる。",
    zh: "Gemini 针对 24 个保留世界提出方案 —— 需要约一分钟。无论上方控件如何设置，基准始终是冻结的实数域集合：历史保持可比。",
    ar: "يقترح Gemini في مواجهة ٢٤ عالمًا محجوزًا — يستغرق دقيقة. المعيار هو دائمًا المجموعة المجمَّدة في المجال الحقيقي، مهما قالت الضوابط أعلاه: يبقى السجل قابلًا للمقارنة.",
  },
  s3: {en: "3 · The evidence base", it: "3 · La base di evidenze", fr: "3 · La base de preuves",
       es: "3 · La base de evidencias", de: "3 · Die Evidenzbasis", ja: "3 · 証拠の基盤",
       zh: "3 · 证据基础", ar: "٣ · قاعدة الأدلة"},
  loading: {en: "loading…", it: "caricamento…", fr: "chargement…", es: "cargando…",
            de: "lädt…", ja: "読み込み中…", zh: "加载中…", ar: "…جارٍ التحميل"},
  refresh: {en: "Refresh", it: "Aggiorna", fr: "Actualiser", es: "Actualizar",
            de: "Aktualisieren", ja: "更新", zh: "刷新", ar: "تحديث"},
  evidence: {en: "The evidence — four figures from the frozen study",
             it: "Le evidenze — quattro figure dallo studio congelato",
             fr: "Les preuves — quatre figures de l'étude figée",
             es: "La evidencia — cuatro figuras del estudio congelado",
             de: "Die Belege — vier Abbildungen aus der eingefrorenen Studie",
             ja: "証拠 — 凍結された研究からの 4 つの図",
             zh: "证据 —— 来自冻结研究的四张图",
             ar: "الأدلة — أربعة أشكال من الدراسة المجمَّدة"},
  storednote: {
    en: "Every run here is stored with its seeds, strategy and code commit — enough to recompute the result rather than merely read it.",
    it: "Ogni esecuzione qui è archiviata con i suoi semi, la strategia e il commit del codice — abbastanza per ricalcolare il risultato, non solo per leggerlo.",
    fr: "Chaque exécution est enregistrée avec ses graines, sa stratégie et son commit de code — de quoi recalculer le résultat, et pas seulement le lire.",
    es: "Cada ejecución se almacena con sus semillas, su estrategia y su commit de código — lo suficiente para recomputar el resultado, no solo leerlo.",
    de: "Jeder Lauf wird mit Seeds, Strategie und Code-Commit gespeichert — genug, um das Ergebnis neu zu berechnen, statt es nur zu lesen.",
    ja: "ここでの各実行は、シード・戦略・コードのコミットとともに保存される — 結果を読むだけでなく、再計算できるだけの情報が残る。",
    zh: "此处每次运行都连同其种子、策略与代码提交一并存储 —— 足以重新计算结果，而不仅仅是阅读它。",
    ar: "كل تشغيل هنا يُحفظ مع بذوره واستراتيجيته وإصدار الشيفرة — ما يكفي لإعادة حساب النتيجة لا لقراءتها فحسب.",
  },
  freefor: {en: "— free for everyone, human or AI",
            it: "— libero per tutti, umani o IA",
            fr: "— libre pour tous, humains ou IA",
            es: "— libre para todos, humanos o IA",
            de: "— frei für alle, Mensch oder KI",
            ja: "— 人間にも AI にも、すべての人に自由",
            zh: "—— 对所有人免费，无论人类还是 AI",
            ar: "— حر للجميع، إنسانًا كان أم ذكاءً اصطناعيًا"},
  sciencenote: {
    en: "Interface language only. The agent's own briefs, the world narratives and every receipt stay in English — they are the experiment's input, and translating a world would change what is being measured.",
    it: "Solo la lingua dell'interfaccia. I brief dell'agente, le descrizioni dei mondi e ogni ricevuta restano in inglese: sono l'input dell'esperimento, e tradurre un mondo cambierebbe ciò che viene misurato.",
    fr: "Langue de l'interface uniquement. Les briefs de l'agent, les récits des mondes et chaque reçu restent en anglais : ce sont les entrées de l'expérience, et traduire un monde changerait ce qui est mesuré.",
    es: "Solo el idioma de la interfaz. Los briefs del agente, las narrativas de los mundos y cada recibo permanecen en inglés: son la entrada del experimento, y traducir un mundo cambiaría lo que se mide.",
    de: "Nur die Oberflächensprache. Die Briefings des Agenten, die Weltbeschreibungen und jede Quittung bleiben englisch — sie sind die Eingabe des Experiments, und eine übersetzte Welt wäre eine andere Messung.",
    ja: "インターフェースの言語のみ。エージェントのブリーフ、世界の記述、そしてすべてのレシートは英語のまま — それらは実験の入力であり、世界を翻訳すれば測定対象そのものが変わってしまう。",
    zh: "仅界面语言。智能体的任务说明、世界叙述与每一份凭据都保持英文 —— 它们是实验的输入，翻译世界就会改变被测量的对象。",
    ar: "لغة الواجهة فقط. تبقى إحاطات الوكيل وسرود العوالم وكل إيصال بالإنجليزية — فهي مُدخل التجربة، وترجمة عالمٍ تغيّر ما يجري قياسه.",
  },
};

function pickLang() {
  const q = new URLSearchParams(location.search).get("lang");
  if (q && LANGS[q]) return q;
  try {
    const saved = localStorage.getItem("ms-lang");
    if (saved && LANGS[saved]) return saved;
  } catch (e) { /* private mode: fall through to the browser's own preference */ }
  const nav = (navigator.language || "en").slice(0, 2).toLowerCase();
  return LANGS[nav] ? nav : "en";
}

function applyLang(lang) {
  const dir = LANGS[lang].dir;
  document.documentElement.lang = lang;
  document.documentElement.dir = dir;
  for (const el of document.querySelectorAll("[data-i18n]")) {
    const entry = T[el.getAttribute("data-i18n")];
    if (entry && entry[lang]) el.innerHTML = entry[lang];
  }
  try { localStorage.setItem("ms-lang", lang); } catch (e) { /* ignore */ }
  const sel = document.getElementById("langsel");
  if (sel) sel.value = lang;
}

function mountLangPicker() {
  const sel = document.createElement("select");
  sel.id = "langsel";
  sel.setAttribute("aria-label", "Interface language");
  sel.style.cssText = "font:inherit;font-size:.85rem;padding:.3rem .5rem;border-radius:7px;" +
    "border:1px solid var(--line);background:var(--surface-1);color:var(--ink-1)";
  for (const [code, {name}] of Object.entries(LANGS)) {
    const o = document.createElement("option");
    o.value = code; o.textContent = name;
    sel.append(o);
  }
  sel.onchange = () => applyLang(sel.value);

  const note = document.createElement("span");
  note.className = "note";
  note.setAttribute("data-i18n", "sciencenote");
  note.style.cssText = "margin:0;flex:1;min-width:14rem";

  const bar = document.createElement("div");
  bar.className = "row";
  bar.style.cssText = "margin:0 0 1.2rem;gap:.75rem;align-items:flex-start";
  bar.append(sel, note);

  const main = document.querySelector("main");
  const lede = main && main.querySelector(".lede");
  if (lede) lede.after(bar); else if (main) main.prepend(bar);
}

mountLangPicker();
applyLang(pickLang());
