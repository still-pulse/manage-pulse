# Copyright (c) 2026, Still Pulse and contributors
# For license information, please see license.txt

"""API pública (guest) da pesquisa de satisfação."""

from __future__ import annotations

import json
from collections import OrderedDict

import frappe
from frappe import _
from frappe.utils import cint, nowdate, strip_html

from managepulse.managepulse.doctype.resposta_da_pesquisa.resposta_da_pesquisa import (
	AVALIACAO_PARA_VALOR,
)

AVALIACOES_VALIDAS = set(AVALIACAO_PARA_VALOR.keys()) - {"Não Utilizou"}
# UI → DocType (sem "não utilizei" no fluxo novo; mantido por compat)
UI_PARA_AVALIACAO = {
	"Ótimo": "Ótimo",
	"Bom": "Bom",
	"Regular": "Regular",
	"Ruim": "Ruim",
	"Não utilizei este serviço": "Não Utilizou",
	"Não Utilizou": "Não Utilizou",
}


def _rate_limit(action: str, limit: int = 30, seconds: int = 3600):
	ip = getattr(frappe.local, "request_ip", None) or "unknown"
	key = f"managepulse:{action}:{ip}"
	try:
		count = cint(frappe.cache().get_value(key) or 0)
	except Exception:
		return
	if count >= limit:
		frappe.throw(_("Muitas tentativas. Aguarde um momento e tente novamente."))
	try:
		frappe.cache().set_value(key, count + 1, expires_in_sec=seconds)
	except Exception:
		pass


def _get_modelo_ativo(slug: str):
	slug = (slug or "").strip().lower()
	if not slug:
		frappe.throw(_("Modelo não informado."), frappe.ValidationError)

	name = frappe.db.get_value(
		"Modelo de Pesquisa",
		{"slug": slug, "ativo": 1},
		"name",
	)
	if not name:
		frappe.throw(
			_("Pesquisa não encontrada ou inativa."),
			frappe.DoesNotExistError,
		)
	return frappe.get_doc("Modelo de Pesquisa", name)


def _build_secoes(modelo) -> list[dict]:
	"""Agrupa perguntas de escala por seção (= serviço), na ordem."""
	secoes: OrderedDict[str, dict] = OrderedDict()
	for p in modelo.perguntas or []:
		if p.tipo != "Escala":
			continue
		key = (p.secao or "").strip() or "Geral"
		if key not in secoes:
			secoes[key] = {
				"secao": key,
				"servico": key,
				"ordem_secao": cint(p.ordem_secao) or 999,
				"criterios": [],
			}
		secoes[key]["criterios"].append(
			{
				"criterio": p.criterio,
				"obrigatorio": 1 if p.obrigatorio else 0,
			}
		)
	lista = list(secoes.values())
	lista.sort(key=lambda s: (s["ordem_secao"], s["secao"]))
	for i, s in enumerate(lista, start=1):
		s["numero"] = i
	return lista


def _parse_list(value) -> list:
	if value is None or value == "":
		return []
	if isinstance(value, list):
		return value
	if isinstance(value, str):
		try:
			parsed = json.loads(value)
			return parsed if isinstance(parsed, list) else []
		except json.JSONDecodeError:
			return [v.strip() for v in value.split(",") if v.strip()]
	return []


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
def get_modelo_publico(slug: str | None = None, company: str | None = None):
	"""Retorna modelo + seções/serviços para a página pública."""
	_rate_limit("get_modelo", limit=120, seconds=3600)
	modelo = _get_modelo_ativo(slug)

	if company:
		if not frappe.db.exists("Company", company):
			frappe.throw(_("Unidade inválida."), frappe.ValidationError)
		if not modelo.is_company_aplicavel(company):
			frappe.throw(
				_("Esta pesquisa não está disponível para a unidade selecionada."),
				frappe.PermissionError,
			)

	unidades = modelo.get_unidades_aplicaveis()
	if not unidades:
		companies_opcoes = frappe.get_all(
			"Company",
			filters={"is_group": 0},
			pluck="name",
			order_by="name asc",
			limit_page_length=50,
		)
	else:
		companies_opcoes = unidades

	secoes = _build_secoes(modelo)
	return {
		"name": modelo.name,
		"titulo": modelo.titulo,
		"slug": modelo.slug,
		"tipo_pesquisa": modelo.tipo_pesquisa,
		"instrucoes": strip_html(modelo.instrucoes or "") if modelo.instrucoes else "",
		"texto_nps": modelo.texto_nps
		or "Em uma escala de 0 a 10, o quanto você indicaria esta unidade a um amigo ou familiar?",
		"permite_contato": 1 if modelo.permite_contato else 0,
		"company": company or "",
		"company_label": company or "",
		"companies_opcoes": companies_opcoes,
		"exige_company_na_lista": 1 if unidades else 0,
		"secoes": secoes,
		"servicos": [
			{"nome": s["secao"], "ordem": s["ordem_secao"], "numero": s["numero"]}
			for s in secoes
		],
		"total_criterios": sum(len(s["criterios"]) for s in secoes),
		"pergunta_servicos": "Quais serviços você utilizou?",
	}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def enviar_resposta(
	slug: str | None = None,
	company: str | None = None,
	servicos_utilizados: str | list | None = None,
	itens: str | list | None = None,
	nps: int | str | None = None,
	comentarios: str | None = None,
	deseja_contato: int | str | None = None,
	nome_contato: str | None = None,
	telefone: str | None = None,
	nome_acompanhante: str | None = None,
	canal: str | None = None,
):
	"""Cria Resposta da Pesquisa (anônima). Exige ≥1 serviço e avaliações só desses."""
	_rate_limit("enviar_resposta", limit=20, seconds=3600)

	modelo = _get_modelo_ativo(slug)
	company = (company or "").strip()
	if not company:
		frappe.throw(_("Informe a unidade."), frappe.ValidationError)
	if not frappe.db.exists("Company", company):
		frappe.throw(_("Unidade inválida."), frappe.ValidationError)
	if not modelo.is_company_aplicavel(company):
		frappe.throw(
			_("Esta pesquisa não está disponível para a unidade selecionada."),
			frappe.PermissionError,
		)

	servicos_raw = _parse_list(servicos_utilizados)
	secoes = _build_secoes(modelo)
	secoes_validas = {s["secao"]: s for s in secoes}
	# mapa casefold para tolerar pequenas diferenças de grafia no client
	secoes_by_fold = {s["secao"].casefold(): s["secao"] for s in secoes}

	servicos: list[str] = []
	seen = set()
	for s in servicos_raw:
		if isinstance(s, str):
			nome = s.strip()
		elif isinstance(s, dict):
			nome = (s.get("servico") or s.get("nome") or s.get("secao") or "").strip()
		else:
			nome = ""
		if not nome or nome in seen:
			continue
		if nome not in secoes_validas:
			canon = secoes_by_fold.get(nome.casefold())
			if not canon:
				frappe.throw(_("Serviço inválido: {0}").format(nome))
			nome = canon
		if nome in seen:
			continue
		seen.add(nome)
		servicos.append(nome)

	if not servicos:
		frappe.throw(_("Selecione ao menos um serviço utilizado."))

	itens = _parse_list(itens)

	# critérios esperados SOMENTE dos serviços marcados (seleção parcial é válida)
	esperados: set[tuple[str, str]] = set()
	for nome in servicos:
		for c in secoes_validas[nome]["criterios"]:
			crit = (c.get("criterio") if isinstance(c, dict) else c) or ""
			crit = str(crit).strip()
			if crit:
				esperados.add((nome, crit))

	rows = []
	vistos: set[tuple[str, str]] = set()
	for raw in itens:
		if not isinstance(raw, dict):
			continue
		secao = (raw.get("secao") or "").strip()
		criterio = (raw.get("criterio") or "").strip()
		avaliacao_ui = (raw.get("avaliacao") or "").strip()
		if not secao or not criterio:
			continue
		if secao not in seen:
			canon = secoes_by_fold.get(secao.casefold())
			if canon and canon in seen:
				secao = canon
			else:
				# ignora avaliações de serviços não selecionados (não bloqueia envio parcial)
				continue
		if (secao, criterio) not in esperados:
			# tenta casar critério por casefold dentro da seção
			matched = None
			for exp_secao, exp_crit in esperados:
				if exp_secao == secao and exp_crit.casefold() == criterio.casefold():
					matched = exp_crit
					break
			if matched is None:
				continue
			criterio = matched
		avaliacao = UI_PARA_AVALIACAO.get(avaliacao_ui, avaliacao_ui)
		if avaliacao not in AVALIACAO_PARA_VALOR or avaliacao == "Não Utilizou":
			# fluxo novo: só Ótimo–Ruim
			if avaliacao not in ("Ótimo", "Bom", "Regular", "Ruim"):
				frappe.throw(
					_("Avaliação inválida para {0}: {1}").format(criterio, avaliacao_ui)
				)
		ordem = secoes_validas[secao]["ordem_secao"]
		key = (secao, criterio)
		if key in vistos:
			continue
		rows.append(
			{
				"secao": secao,
				"ordem_secao": ordem,
				"criterio": criterio,
				"avaliacao": avaliacao,
			}
		)
		vistos.add(key)

	if not esperados:
		frappe.throw(
			_("Os serviços selecionados não possuem critérios de avaliação."),
			frappe.ValidationError,
		)

	if vistos != esperados:
		faltando = sorted(esperados - vistos)
		amostra = ", ".join(f"{s} / {c}" for s, c in faltando[:5])
		extra = f" (+{len(faltando) - 5})" if len(faltando) > 5 else ""
		frappe.throw(
			_(
				"Responda todos os critérios dos serviços que você utilizou. Faltando: {0}{1}"
			).format(amostra, extra),
			frappe.ValidationError,
		)

	deseja = cint(deseja_contato)
	nps_val = None if nps in (None, "") else cint(nps)
	if nps_val is not None and (nps_val < 0 or nps_val > 10):
		frappe.throw(_("O NPS deve ser entre 0 e 10."))

	canal_val = canal if canal in ("Público", "Totem", "Manual Desk") else "Público"
	servicos_rows = [
		{"servico": nome, "ordem": secoes_validas[nome]["ordem_secao"]} for nome in servicos
	]

	doc_name = None
	original_user = frappe.session.user
	try:
		frappe.set_user("Guest")
		doc = frappe.get_doc(
			{
				"doctype": "Resposta da Pesquisa",
				"modelo": modelo.name,
				"company": company,
				"data_resposta": nowdate(),
				"canal": canal_val,
				"status": "Recebida",
				"nps": nps_val,
				"texto_nps": modelo.texto_nps,
				"comentarios": (comentarios or "").strip()[:1000],
				"deseja_contato": 1 if deseja else 0,
				"nome_contato": (nome_contato or "").strip() if deseja else "",
				"telefone": (telefone or "").strip() if deseja else "",
				"nome_acompanhante": (nome_acompanhante or "").strip() if deseja else "",
				"servicos_utilizados": servicos_rows,
				"itens": rows,
			}
		)
		doc.flags.ignore_permissions = True
		doc.insert(ignore_permissions=True)
		doc_name = doc.name
		frappe.db.set_value(
			"Resposta da Pesquisa",
			doc.name,
			{"owner": "Guest", "modified_by": "Guest"},
			update_modified=False,
		)
	finally:
		frappe.set_user(original_user)

	return {
		"ok": True,
		"name": doc_name,
		"message": _("Obrigado por participar!"),
	}
