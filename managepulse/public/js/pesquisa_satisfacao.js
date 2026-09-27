/**
 * ManagePulse — SPA da pesquisa pública de satisfação
 * Fluxo: welcome → serviços → seções (filtradas) → NPS → contato → review → success
 */
(function () {
	"use strict";

	const SCALE = ["Ótimo", "Bom", "Regular", "Ruim"];
	const MAX_COMMENT = 1000;
	const SUCCESS_REDIRECT_SEC = 7;

	const state = {
		boot: window.MP_BOOT || {},
		modelo: null,
		company: "",
		/** @type {string[]} seções/serviços marcados na pergunta 1 */
		servicosSelecionados: [],
		// answers[secao][criterio] = label
		answers: {},
		nps: null,
		comentarios: "",
		desejaContato: 0,
		nome: "",
		telefone: "",
		acompanhante: "",
		// welcome | services | section | nps | contact | review | success | error | loading
		step: "loading",
		sectionIndex: 0,
		error: "",
		sending: false,
		successTimer: null,
	};

	const el = { app: null };

	function $(sel, root) {
		return (root || document).querySelector(sel);
	}

	function esc(s) {
		return String(s == null ? "" : s)
			.replace(/&/g, "&amp;")
			.replace(/</g, "&lt;")
			.replace(/>/g, "&gt;")
			.replace(/"/g, "&quot;");
	}

	/** Seções ativas (só serviços selecionados), na ordem do modelo */
	function activeSecoes() {
		const all = (state.modelo && state.modelo.secoes) || [];
		const set = new Set(state.servicosSelecionados);
		return all.filter((s) => set.has(s.secao));
	}

	/**
	 * Progresso linear por tela do fluxo atual:
	 * serviços → 1 tela por serviço selecionado → NPS → contato? → revisão
	 */
	function flowTotalScreens() {
		// na tela de serviços ainda pode não haver seleção: conta pelo menos 1 slot
		let nSec = activeSecoes().length;
		if (state.step === "services") {
			nSec = Math.max(state.servicosSelecionados.length, 1);
		} else {
			nSec = Math.max(nSec, 1);
		}
		const hasContact = !!(state.modelo && state.modelo.permite_contato);
		// 1 serviços + N seções + 1 nps + (contato) + 1 revisão
		return 1 + nSec + 1 + (hasContact ? 1 : 0) + 1;
	}

	function flowCurrentScreen() {
		const nSec =
			state.step === "services"
				? Math.max(state.servicosSelecionados.length, 1)
				: Math.max(activeSecoes().length, 1);
		const hasContact = !!(state.modelo && state.modelo.permite_contato);
		if (state.step === "services") return 1;
		if (state.step === "section") return 1 + (state.sectionIndex + 1);
		if (state.step === "nps") return 1 + nSec + 1;
		if (state.step === "contact") return 1 + nSec + 1 + 1;
		if (state.step === "review") return 1 + nSec + 1 + (hasContact ? 1 : 0) + 1;
		return 1;
	}

	function progressInfo() {
		const secs = activeSecoes();
		const nSec = secs.length;
		if (
			state.step === "welcome" ||
			state.step === "loading" ||
			state.step === "success" ||
			state.step === "error"
		) {
			return null;
		}
		const total = flowTotalScreens();
		const current = flowCurrentScreen();
		const pct = Math.min(100, Math.max(1, Math.round((current / total) * 100)));

		if (state.step === "services") {
			return { label: "Quais serviços você utilizou?", pct };
		}
		if (state.step === "section") {
			const i = state.sectionIndex;
			const sec = secs[i];
			if (!sec) return { label: "Avaliação", pct };
			return {
				label: `Serviço ${i + 1} de ${nSec} — ${sec.secao}`,
				pct,
			};
		}
		if (state.step === "nps") {
			return { label: "Quase lá — sua nota", pct };
		}
		if (state.step === "contact") {
			return { label: "Último passo — contato", pct };
		}
		if (state.step === "review") {
			return { label: "Revisão", pct: 100 };
		}
		return null;
	}

	function expectedCriteriosCount() {
		return activeSecoes().reduce((n, s) => n + (s.criterios || []).length, 0);
	}

	function answeredCount() {
		let n = 0;
		activeSecoes().forEach((s) => {
			(s.criterios || []).forEach((c) => {
				if (state.answers[s.secao] && state.answers[s.secao][c.criterio]) n += 1;
			});
		});
		return n;
	}

	function sectionComplete(idx) {
		const secs = activeSecoes();
		const sec = secs[idx];
		if (!sec) return false;
		return (sec.criterios || []).every(
			(c) => state.answers[sec.secao] && state.answers[sec.secao][c.criterio]
		);
	}

	function setAnswer(secao, criterio, val) {
		if (!state.answers[secao]) state.answers[secao] = {};
		state.answers[secao][criterio] = val;
		render();
	}

	function toggleServico(nome) {
		nome = (nome || "").trim();
		if (!nome) return;
		const i = state.servicosSelecionados.indexOf(nome);
		if (i >= 0) {
			state.servicosSelecionados.splice(i, 1);
			// limpa respostas daquele serviço
			delete state.answers[nome];
		} else {
			state.servicosSelecionados.push(nome);
		}
		// mantém ordem do modelo (só serviços válidos do modelo)
		const order = ((state.modelo && state.modelo.secoes) || []).map((s) => s.secao);
		const valid = new Set(order);
		state.servicosSelecionados = state.servicosSelecionados
			.filter((s) => valid.has(s))
			.sort((a, b) => order.indexOf(a) - order.indexOf(b));
		render();
	}

	/** Resolve nome do serviço a partir do índice ou do atributo data-servico */
	function resolveServicoFromEl(t) {
		const idx = t.getAttribute("data-servico-idx");
		if (idx !== null && idx !== "") {
			const secoes = (state.modelo && state.modelo.secoes) || [];
			const s = secoes[parseInt(idx, 10)];
			if (s && s.secao) return s.secao;
		}
		return (t.getAttribute("data-servico") || "").trim();
	}

	function csrf() {
		return (
			state.boot.csrf_token ||
			(window.frappe && frappe.csrf_token) ||
			document.querySelector('meta[name="csrf-token"]')?.content ||
			""
		);
	}

	function apiCall(method, args) {
		const body = new URLSearchParams();
		Object.keys(args || {}).forEach((k) => {
			const v = args[k];
			if (v === undefined || v === null) return;
			body.append(k, typeof v === "object" ? JSON.stringify(v) : String(v));
		});
		return fetch(`/api/method/${method}`, {
			method: "POST",
			headers: {
				"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
				"X-Frappe-CSRF-Token": csrf(),
				Accept: "application/json",
			},
			body: body.toString(),
			credentials: "same-origin",
		}).then(async (res) => {
			const data = await res.json().catch(() => ({}));
			if (!res.ok || data.exc_type || (data.exc && !data.message)) {
				let msg =
					(data._server_messages && parseServerMessages(data._server_messages)) ||
					data.message ||
					data.exc ||
					"Não foi possível concluir a solicitação.";
				if (typeof msg !== "string") msg = "Erro ao processar.";
				throw new Error(msg);
			}
			return data.message !== undefined ? data.message : data;
		});
	}

	function parseServerMessages(raw) {
		try {
			const arr = JSON.parse(raw);
			const first = JSON.parse(arr[0]);
			return first.message || first;
		} catch (e) {
			return null;
		}
	}

	function loadModelo() {
		state.step = "loading";
		state.error = "";
		render();
		const slug = state.boot.slug;
		if (!slug) {
			state.step = "error";
			state.error =
				"Link incompleto. Use /pesquisa-satisfacao/<slug-do-modelo>?unidade=Nome da Company";
			render();
			return;
		}
		apiCall(state.boot.api_get || "managepulse.api.public_survey.get_modelo_publico", {
			slug: slug,
			company: state.boot.company || "",
		})
			.then((modelo) => {
				state.modelo = modelo;
				state.company = modelo.company || state.boot.company || "";
				state.step = "welcome";
				render();
			})
			.catch((err) => {
				state.step = "error";
				state.error = err.message || "Pesquisa não encontrada.";
				render();
			});
	}

	function collectItens() {
		const itens = [];
		activeSecoes().forEach((s) => {
			(s.criterios || []).forEach((c) => {
				const av = state.answers[s.secao] && state.answers[s.secao][c.criterio];
				if (av) {
					itens.push({ secao: s.secao, criterio: c.criterio, avaliacao: av });
				}
			});
		});
		return itens;
	}

	function submit() {
		if (state.sending) return;
		if (!state.company) {
			state.error = "Selecione a unidade antes de enviar.";
			render();
			return;
		}
		const secs = activeSecoes();
		if (!secs.length) {
			state.error = "Selecione ao menos um serviço.";
			state.step = "services";
			render();
			return;
		}
		// Garante que todos os critérios dos serviços escolhidos foram respondidos
		// (não exige serviços não selecionados)
		for (let i = 0; i < secs.length; i++) {
			if (!sectionComplete(i)) {
				state.error =
					"Ainda faltam avaliações em: " + (secs[i].secao || "serviço") + ".";
				state.step = "section";
				state.sectionIndex = i;
				render();
				return;
			}
		}
		if (state.nps === null || state.nps === undefined || state.nps === "") {
			state.error = "Informe a nota de indicação (0 a 10).";
			state.step = "nps";
			render();
			return;
		}
		const itens = collectItens();
		if (!itens.length) {
			state.error = "Responda ao menos um item de avaliação antes de enviar.";
			state.step = "section";
			state.sectionIndex = 0;
			render();
			return;
		}
		state.sending = true;
		state.error = "";
		render();
		apiCall(state.boot.api_send || "managepulse.api.public_survey.enviar_resposta", {
			slug: state.modelo.slug,
			company: state.company,
			servicos_utilizados: state.servicosSelecionados.slice(),
			itens: itens,
			nps: state.nps === null ? "" : state.nps,
			comentarios: state.comentarios,
			deseja_contato: state.desejaContato ? 1 : 0,
			nome_contato: state.nome,
			telefone: state.telefone,
			nome_acompanhante: state.acompanhante,
			canal: "Público",
		})
			.then(() => {
				state.sending = false;
				state.step = "success";
				render();
				startSuccessTimer();
			})
			.catch((err) => {
				state.sending = false;
				state.error = err.message || "Falha ao enviar. Tente novamente.";
				render();
			});
	}

	function startSuccessTimer() {
		let left = SUCCESS_REDIRECT_SEC;
		const tick = () => {
			const t = document.getElementById("mp-success-countdown");
			if (t) t.textContent = String(left);
			if (left <= 0) {
				resetSurvey();
				return;
			}
			left -= 1;
			state.successTimer = setTimeout(tick, 1000);
		};
		if (state.successTimer) clearTimeout(state.successTimer);
		tick();
	}

	function resetSurvey() {
		if (state.successTimer) clearTimeout(state.successTimer);
		state.servicosSelecionados = [];
		state.answers = {};
		state.nps = null;
		state.comentarios = "";
		state.desejaContato = 0;
		state.nome = "";
		state.telefone = "";
		state.acompanhante = "";
		state.sectionIndex = 0;
		state.step = "welcome";
		state.error = "";
		render();
		window.scrollTo(0, 0);
	}

	function goNext() {
		state.error = "";
		if (state.step === "welcome") {
			if (!state.company) {
				state.error = "Selecione a unidade para continuar.";
				render();
				return;
			}
			state.step = "services";
		} else if (state.step === "services") {
			if (!state.servicosSelecionados.length) {
				state.error = "Selecione ao menos um serviço que você utilizou.";
				render();
				return;
			}
			// Só avalia os serviços marcados — não é necessário marcar todos
			const secs = activeSecoes();
			if (!secs.length) {
				state.error = "Não foi possível carregar os serviços selecionados. Toque novamente nos botões.";
				state.servicosSelecionados = [];
				render();
				return;
			}
			state.step = "section";
			state.sectionIndex = 0;
		} else if (state.step === "section") {
			if (!sectionComplete(state.sectionIndex)) {
				state.error = "Toque em uma opção para cada item.";
				render();
				return;
			}
			const secs = activeSecoes();
			if (!secs.length) {
				state.step = "services";
				state.sectionIndex = 0;
				state.error = "Selecione ao menos um serviço para continuar.";
				render();
				return;
			}
			if (state.sectionIndex < secs.length - 1) {
				state.sectionIndex += 1;
			} else {
				state.step = "nps";
			}
		} else if (state.step === "nps") {
			if (state.nps === null || state.nps === undefined || state.nps === "") {
				state.error = "Selecione uma nota de 0 a 10.";
				render();
				return;
			}
			state.step = state.modelo.permite_contato ? "contact" : "review";
		} else if (state.step === "contact") {
			if (state.desejaContato) {
				if (!state.nome.trim() || !state.telefone.trim()) {
					state.error = "Informe nome e telefone para retorno.";
					render();
					return;
				}
			}
			state.step = "review";
		}
		render();
		window.scrollTo(0, 0);
	}

	function goBack() {
		state.error = "";
		if (state.step === "services") {
			state.step = "welcome";
		} else if (state.step === "section") {
			if (state.sectionIndex > 0) {
				state.sectionIndex -= 1;
			} else {
				state.step = "services";
			}
		} else if (state.step === "nps") {
			const secs = activeSecoes();
			state.step = "section";
			state.sectionIndex = Math.max(0, secs.length - 1);
		} else if (state.step === "contact") {
			state.step = "nps";
		} else if (state.step === "review") {
			state.step = state.modelo.permite_contato ? "contact" : "nps";
		}
		render();
		window.scrollTo(0, 0);
	}

	function headerHtml() {
		const unit = state.company || state.modelo?.company_label || "Pesquisa de Satisfação";
		const sub =
			state.modelo &&
			(state.modelo.tipo_pesquisa
				? `Pesquisa de Satisfação – ${state.modelo.tipo_pesquisa}`
				: state.modelo.titulo);
		const logoSrc = "/assets/managepulse/images/bhcl-logo.png";
		return `
			<header class="mp-header">
				<div class="mp-logo-wrap">
					<img class="mp-logo" src="${logoSrc}" alt="BHCL — Beneficência Hospitalar de Cesário Lange"
						onerror="this.classList.add('mp-hidden'); this.nextElementSibling.classList.remove('mp-hidden');" />
					<div class="mp-logo-fallback mp-hidden">BHCL</div>
				</div>
				<div class="mp-header-text">
					<h1>${esc(shortUnit(unit))}</h1>
					<p>${esc(sub || "")}</p>
				</div>
			</header>`;
	}

	function shortUnit(name) {
		if (!name) return "";
		const cut = name.split(" - ")[0];
		return cut.length > 42 ? cut.slice(0, 40) + "…" : cut;
	}

	function progressHtml() {
		const p = progressInfo();
		if (!p) return "";
		return `
			<div class="mp-progress-wrap">
				<div class="mp-progress-meta">
					<span class="label">${esc(p.label)}</span>
					<span class="pct">${p.pct}%</span>
				</div>
				<div class="mp-progress-bar"><span style="width:${p.pct}%"></span></div>
			</div>`;
	}

	function actionsHtml(primaryLabel, opts) {
		opts = opts || {};
		const showBack = opts.back !== false;
		const primaryDisabled = opts.disabled ? "disabled" : "";
		return `
			<div class="mp-actions">
				${
					showBack
						? `<button type="button" class="mp-btn mp-btn-secondary" data-action="back">Voltar</button>`
						: ""
				}
				<button type="button" class="mp-btn mp-btn-primary" data-action="next" ${primaryDisabled}>
					${esc(primaryLabel)}
				</button>
			</div>`;
	}

	function errorHtml() {
		if (!state.error) return "";
		return `<div class="mp-error-banner" role="alert">${esc(state.error)}</div>`;
	}

	function footerHtml() {
		return `<footer class="mp-footer">Beneficência Hospitalar de Cesário Lange · ManagePulse</footer>`;
	}

	function renderWelcome() {
		const m = state.modelo;
		const needsSelect = !state.company && m.companies_opcoes && m.companies_opcoes.length;
		const options = (m.companies_opcoes || [])
			.map(
				(c) =>
					`<option value="${esc(c)}" ${c === state.company ? "selected" : ""}>${esc(c)}</option>`
			)
			.join("");
		return `
			${headerHtml()}
			<main class="mp-main">
				${errorHtml()}
				<div class="mp-hero">
					<p class="eyebrow">Sua opinião importa</p>
					<h2>Como foi seu atendimento hoje?</h2>
				</div>
				<p class="mp-lead">Avalie os serviços que você utilizou hoje. Suas respostas são anônimas e ajudam a melhorar o atendimento.</p>
				<div class="mp-meta-row">
					<span aria-hidden="true">🕒</span>
					<span>Leva cerca de 3 minutos</span>
				</div>
				<div class="mp-info-box">
					<strong>Pesquisa anônima.</strong> Você não precisa se identificar. Se quiser um retorno da nossa equipe, poderá deixar seu contato no final — é opcional.
				</div>
				${
					needsSelect
						? `<label class="mp-label" for="mp-company">Unidade</label>
					<select id="mp-company" class="mp-select" data-field="company">
						<option value="">Selecione a unidade…</option>
						${options}
					</select>`
						: state.company
							? ""
							: `<div class="mp-error-banner">Informe a unidade na URL: ?unidade=Nome da Company</div>`
				}
				<button type="button" class="mp-btn mp-btn-primary mp-btn-block" data-action="next"
					${state.company ? "" : "disabled"}>Começar</button>
				<p class="mp-center-note">
					Participação voluntária ·
					<button type="button" class="mp-link" data-action="privacy">Como usamos suas respostas</button>
				</p>
			</main>
			${footerHtml()}`;
	}

	function renderServices() {
		const pergunta =
			(state.modelo && state.modelo.pergunta_servicos) ||
			"Quais serviços você utilizou?";
		const secoes = (state.modelo && state.modelo.secoes) || [];
		const selected = new Set(state.servicosSelecionados);
		const cards = secoes
			.map((s, idx) => {
				const on = selected.has(s.secao);
				return `
					<button type="button" class="mp-service-chip ${on ? "is-selected" : ""}"
						data-action="toggle-servico"
						data-servico-idx="${idx}"
						data-servico="${esc(s.secao)}"
						aria-pressed="${on}">
						<span class="mp-service-check" aria-hidden="true">${on ? "✓" : ""}</span>
						<span class="mp-service-name">${esc(s.secao)}</span>
					</button>`;
			})
			.join("");
		const nSel = state.servicosSelecionados.length;
		return `
			${headerHtml()}
			<main class="mp-main">
				${progressHtml()}
				${errorHtml()}
				<h2 class="mp-section-title">${esc(pergunta)}</h2>
				<p class="mp-section-sub">Toque nos serviços que você usou nesta visita (pode ser só um). Só vamos pedir avaliação dos selecionados.</p>
				<div class="mp-service-list" role="group" aria-label="${esc(pergunta)}">${cards}</div>
				${
					nSel
						? `<p class="mp-center-note" style="margin-top:4px;margin-bottom:0">${nSel} serviço${nSel > 1 ? "s" : ""} selecionado${nSel > 1 ? "s" : ""}</p>`
						: ""
				}
				${actionsHtml("Continuar", { disabled: !nSel })}
			</main>
			${footerHtml()}`;
	}

	function renderSection() {
		const secs = activeSecoes();
		const sec = secs[state.sectionIndex];
		if (!sec) {
			return renderServices();
		}
		const cards = (sec.criterios || [])
			.map((c) => {
				const cur = (state.answers[sec.secao] && state.answers[sec.secao][c.criterio]) || "";
				const buttons = SCALE.map((label) => {
					const sel = cur === label ? "is-selected" : "";
					return `<button type="button" class="mp-scale-btn ${sel}"
						data-action="scale" data-secao="${esc(sec.secao)}" data-criterio="${esc(c.criterio)}" data-val="${esc(label)}">${esc(label)}</button>`;
				}).join("");
				return `
					<div class="mp-criterio">
						<h3>${esc(c.criterio)}</h3>
						<div class="mp-scale">${buttons}</div>
					</div>`;
			})
			.join("");

		return `
			${headerHtml()}
			<main class="mp-main">
				${progressHtml()}
				${errorHtml()}
				<h2 class="mp-section-title">${state.sectionIndex + 1}. ${esc(sec.secao)}</h2>
				<p class="mp-section-sub">Toque em uma opção para cada item.</p>
				${cards}
				${actionsHtml("Continuar")}
			</main>
			${footerHtml()}`;
	}

	function renderNps() {
		const texto =
			state.modelo.texto_nps ||
			"De 0 a 10, o quanto você indicaria esta unidade a um amigo ou familiar?";
		const nums = Array.from({ length: 11 }, (_, i) => {
			const sel = state.nps === i ? "is-selected" : "";
			return `<button type="button" class="mp-nps-btn ${sel}" data-action="nps" data-val="${i}">${i}</button>`;
		}).join("");
		const left = MAX_COMMENT - (state.comentarios || "").length;
		return `
			${headerHtml()}
			<main class="mp-main">
				${progressHtml()}
				${errorHtml()}
				<h2 class="mp-section-title">${esc(texto)}</h2>
				<p class="mp-section-sub">0 = não indicaria · 10 = indicaria com certeza</p>
				<div class="mp-nps-grid">${nums}</div>
				<div class="mp-nps-legend"><span>Não indicaria</span><span>Indicaria com certeza</span></div>
				<label class="mp-label">Críticas, sugestões e elogios <span class="opt">(opcional)</span></label>
				<textarea class="mp-textarea" id="mp-comentarios" maxlength="${MAX_COMMENT}"
					placeholder="Conte como podemos melhorar, ou deixe um elogio para a equipe...">${esc(state.comentarios)}</textarea>
				<div class="mp-charcount">${left} caracteres restantes</div>
				${actionsHtml("Continuar")}
			</main>
			${footerHtml()}`;
	}

	function renderContact() {
		const anonSel = !state.desejaContato ? "is-selected" : "";
		const contactSel = state.desejaContato ? "is-selected" : "";
		return `
			${headerHtml()}
			<main class="mp-main">
				${progressHtml()}
				${errorHtml()}
				<h2 class="mp-section-title">Deseja retorno sobre suas observações?</h2>
				<p class="mp-section-sub">Se preferir, sua resposta continua anônima. Seus dados seriam usados apenas para o retorno da equipe de qualidade.</p>
				<button type="button" class="mp-choice ${anonSel}" data-action="contact-mode" data-val="0">
					<span class="title">Não, quero manter anônimo</span>
					<span class="sub">Nenhum dado pessoal é registrado</span>
				</button>
				<button type="button" class="mp-choice ${contactSel}" data-action="contact-mode" data-val="1">
					<span class="title">Sim, quero receber um retorno</span>
					<span class="sub">Informe nome e telefone abaixo</span>
				</button>
				${
					state.desejaContato
						? `
					<div class="mp-field">
						<label>Seu nome <span class="req">*</span></label>
						<input class="mp-input" id="mp-nome" placeholder="Nome completo" value="${esc(state.nome)}" autocomplete="name" />
					</div>
					<div class="mp-field">
						<label>Telefone <span class="req">*</span></label>
						<input class="mp-input" id="mp-tel" placeholder="(15) 90000-0000" value="${esc(state.telefone)}" inputmode="tel" autocomplete="tel" />
					</div>
					<div class="mp-field">
						<label>Nome do acompanhante <span class="opt">(opcional)</span></label>
						<input class="mp-input" id="mp-acomp" placeholder="Se houver" value="${esc(state.acompanhante)}" />
					</div>`
						: ""
				}
				${actionsHtml("Revisar e enviar")}
			</main>
			${footerHtml()}`;
	}

	function renderReview() {
		const comentario = (state.comentarios || "").trim() ? "Sim" : "Não";
		const retorno = state.desejaContato ? "Com contato" : "Anônimo";
		const servicosTxt = state.servicosSelecionados.length
			? state.servicosSelecionados.join(", ")
			: "—";
		return `
			${headerHtml()}
			<main class="mp-main">
				${progressHtml()}
				${errorHtml()}
				<h2 class="mp-section-title">Tudo certo?</h2>
				<p class="mp-section-sub">Confira um resumo antes de enviar. Nada é enviado até você confirmar.</p>
				<div class="mp-review">
					<div class="mp-review-row"><span>Serviços utilizados</span><strong class="mp-review-wrap">${esc(servicosTxt)}</strong></div>
					<div class="mp-review-row"><span>Itens avaliados</span><strong>${answeredCount()} de ${expectedCriteriosCount()}</strong></div>
					<div class="mp-review-row"><span>Nota de indicação (0–10)</span><strong>${state.nps === null ? "—" : state.nps}</strong></div>
					<div class="mp-review-row"><span>Comentário</span><strong>${esc(comentario)}</strong></div>
					<div class="mp-review-row"><span>Retorno da equipe</span><strong>${esc(retorno)}</strong></div>
				</div>
				<div class="mp-actions">
					<button type="button" class="mp-btn mp-btn-secondary" data-action="back">Voltar</button>
					<button type="button" class="mp-btn mp-btn-primary" data-action="submit" ${state.sending ? "disabled" : ""}>
						${state.sending ? "Enviando…" : "Enviar pesquisa"}
					</button>
				</div>
			</main>
			${footerHtml()}`;
	}

	function renderSuccess() {
		return `
			${headerHtml()}
			<main class="mp-main">
				<div class="mp-success">
					<div class="mp-success-icon" aria-hidden="true">✓</div>
					<h2>Obrigado por participar!</h2>
					<p>Sua opinião ajuda a BHCL a cuidar cada vez melhor de você e da nossa comunidade.</p>
					<button type="button" class="mp-btn mp-btn-secondary" style="flex:none;min-width:200px;margin:0 auto;display:inline-block" data-action="again">
						Enviar outra resposta
					</button>
					<p class="mp-success-timer">Esta tela volta ao início automaticamente em <span id="mp-success-countdown">${SUCCESS_REDIRECT_SEC}</span>s</p>
				</div>
			</main>
			${footerHtml()}`;
	}

	function renderErrorPage() {
		return `
			${headerHtml()}
			<main class="mp-main">
				<div class="mp-error-banner">${esc(state.error || "Erro")}</div>
				<p class="mp-lead">Verifique o link da pesquisa ou fale com a equipe de qualidade da unidade.</p>
			</main>
			${footerHtml()}`;
	}

	function renderLoading() {
		return `
			${headerHtml()}
			<main class="mp-main"><div class="mp-loading">Carregando pesquisa…</div></main>
			${footerHtml()}`;
	}

	function render() {
		if (!el.app) return;
		let html = "";
		switch (state.step) {
			case "loading":
				html = renderLoading();
				break;
			case "welcome":
				html = renderWelcome();
				break;
			case "services":
				html = renderServices();
				break;
			case "section":
				html = renderSection();
				break;
			case "nps":
				html = renderNps();
				break;
			case "contact":
				html = renderContact();
				break;
			case "review":
				html = renderReview();
				break;
			case "success":
				html = renderSuccess();
				break;
			case "error":
				html = renderErrorPage();
				break;
			default:
				html = renderLoading();
		}
		el.app.innerHTML = html;
		bind();
	}

	function bind() {
		el.app.onclick = (ev) => {
			const t = ev.target.closest("[data-action]");
			if (!t) return;
			const action = t.getAttribute("data-action");
			if (action === "next") goNext();
			else if (action === "back") goBack();
			else if (action === "submit") submit();
			else if (action === "again") resetSurvey();
			else if (action === "privacy") openPrivacy();
			else if (action === "toggle-servico") {
				toggleServico(resolveServicoFromEl(t));
			} else if (action === "scale") {
				setAnswer(
					t.getAttribute("data-secao"),
					t.getAttribute("data-criterio"),
					t.getAttribute("data-val")
				);
			} else if (action === "nps") {
				state.nps = parseInt(t.getAttribute("data-val"), 10);
				render();
			} else if (action === "contact-mode") {
				state.desejaContato = t.getAttribute("data-val") === "1" ? 1 : 0;
				if (!state.desejaContato) {
					state.nome = "";
					state.telefone = "";
					state.acompanhante = "";
				}
				render();
			} else if (action === "close-privacy") {
				closePrivacy();
			}
		};

		const company = $("#mp-company", el.app);
		if (company) {
			company.onchange = () => {
				state.company = company.value;
				render();
			};
		}
		const com = $("#mp-comentarios", el.app);
		if (com) {
			com.oninput = () => {
				state.comentarios = com.value.slice(0, MAX_COMMENT);
				const cc = $(".mp-charcount", el.app);
				if (cc) cc.textContent = `${MAX_COMMENT - state.comentarios.length} caracteres restantes`;
			};
		}
		const nome = $("#mp-nome", el.app);
		if (nome) nome.oninput = () => (state.nome = nome.value);
		const tel = $("#mp-tel", el.app);
		if (tel) tel.oninput = () => (state.telefone = tel.value);
		const ac = $("#mp-acomp", el.app);
		if (ac) ac.oninput = () => (state.acompanhante = ac.value);
	}

	function closePrivacy() {
		const m = document.getElementById("mp-privacy-modal");
		if (m) m.remove();
	}

	function openPrivacy() {
		closePrivacy();
		const div = document.createElement("div");
		div.id = "mp-privacy-modal";
		div.className = "mp-modal-backdrop";
		div.innerHTML = `
			<div class="mp-modal" role="dialog" aria-modal="true" aria-labelledby="mp-priv-title">
				<h3 id="mp-priv-title">Como usamos suas respostas</h3>
				<p>As avaliações e comentários são usados pela equipe de qualidade da BHCL para melhorar o atendimento nas unidades.</p>
				<p>Por padrão a pesquisa é <strong>anônima</strong>. Só registramos nome e telefone se você pedir retorno da equipe.</p>
				<p>A participação é voluntária. Não pedimos CPF, prontuário ou login.</p>
				<button type="button" class="mp-btn mp-btn-primary mp-btn-block" data-action="close-privacy" style="margin-top:12px">Entendi</button>
			</div>`;
		div.addEventListener("click", (e) => {
			if (e.target === div) {
				closePrivacy();
				return;
			}
			if (e.target.closest("[data-action='close-privacy']")) closePrivacy();
		});
		document.body.appendChild(div);
	}

	function init() {
		el.app = document.getElementById("mp-app");
		if (!el.app) return;
		state.boot = window.MP_BOOT || {};
		state.company = state.boot.company || "";
		loadModelo();
	}

	if (document.readyState === "loading") {
		document.addEventListener("DOMContentLoaded", init);
	} else {
		init();
	}
})();
